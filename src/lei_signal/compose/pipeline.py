"""分析编排：把行情、特征、规则、结构、状态机与解释串联成单一入口。

界面只调用本模块，不重复实现任何业务规则。
"""
from __future__ import annotations

import sqlite3
from contextlib import closing, suppress
from dataclasses import dataclass, field
from datetime import UTC, date

import pandas as pd

from lei_signal.compose.interpreter import build_assessment
from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.data.providers import PriceData, PriceProvider, default_provider
from lei_signal.data.validation import DataUnavailableError, detect_unadjusted_gaps
from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import (
    DailyAssessment,
    Direction,
    Pivot,
    Severity,
    SignalEvent,
    StructureInstance,
)
from lei_signal.events.lifecycle import assign_lifecycles
from lei_signal.events.log import EventLog, make_event
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.features.volume_profile import VolumeProfileProxy, compute_volume_profile
from lei_signal.rules.bottom_structure import (
    apply_c_lifecycle,
    detect_bottom_structure_events,
    detect_double_bottoms,
    detect_higher_low_bottoms,
    detect_reversal_bottoms,
)
from lei_signal.rules.color_events import detect_color_events
from lei_signal.rules.dual_ma import (
    detect_dual_ma_confirm_events,
    detect_spread_events,
    ema20_reclaim_state,
)
from lei_signal.rules.key_wave import detect_key_wave_events
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import (
    compute_long_trend,
    compute_weekly_long_trend,
    detect_long_trend_events,
)
from lei_signal.rules.resistance_b1 import B1Resistance, find_b1
from lei_signal.rules.reversals import detect_reversal_events
from lei_signal.rules.top_structure import detect_top_structure_events, detect_top_structures
from lei_signal.rules.volume import compute_volume_labels, detect_volume_events
from lei_signal.state.machine import DayState, run_state_machine

MIN_BARS = 21


def _build_structure_necklines(
    bottoms: list[StructureInstance],
) -> dict[pd.Timestamp, dict]:
    """从已确认的底部结构构建「该日附近可用的颈线」映射，供放量突破事件使用。

    简化策略：每个已确认结构的 confirmed_date 之后、失效之前，
    都将结构颈线作为可用颈线。这样能稳定捕获「放量突破颈线」事件。
    """
    necklines: dict[pd.Timestamp, dict] = {}
    for structure in bottoms:
        if structure.status.value == "invalidated" or structure.confirmed_date is None:
            continue
        if structure.neckline is None:
            continue
        necklines[pd.Timestamp(structure.confirmed_date)] = {
            "neckline": structure.neckline,
            "structure_id": structure.structure_id,
        }
    return necklines


def _detect_structure_bound_ema_reclaim(
    frame: pd.DataFrame,
    symbol: str,
    bottoms: list[StructureInstance],
) -> list[SignalEvent]:
    """修复 3：为每个底部结构生成**结构关联**的 EMA 早期转强事件。

    规则：
      - 全局 EMA20 重新站上日（即 ema20_reclaim_state=True），
        且该日**有至少一个底部结构已 confirmed** 时，
        为该日 + 该结构生成一个 ema20_reclaim_rising 结构关联事件。
      - 同一结构 + 不同 reclaim 日 = 不同 lifecycle_id。
      - 同一日 + 多个结构 = 多对多关联。
      - 关联事件的 valid_until 在「结构失效日 + 1」或「转黑日 + 1」中较早者。
    """
    spec = get_rule("ema20_reclaim_rising")
    state = ema20_reclaim_state(frame)
    events: list[SignalEvent] = []
    # 按时间排序
    sorted_bottoms = sorted(
        bottoms,
        key=lambda s: s.confirmed_date or s.detected_date,
    )
    for ts in frame.index:
        if not bool(state.loc[ts]):
            continue
        trade_date = ts.date()
        row = frame.loc[ts]
        position = frame.index.get_loc(ts)
        previous = frame.iloc[position - 1] if position > 0 else row
        for structure in sorted_bottoms:
            confirmed = structure.confirmed_date
            if confirmed is None or trade_date < confirmed:
                continue  # 结构尚未确认
            invalidated = structure.invalidated_date
            if invalidated is not None and trade_date >= invalidated:
                continue  # 结构已失效
            # 同一结构在同一日的事件 ID 是确定的
            event_id = make_event_id(
                rule_id=spec.rule_id,
                rule_version=spec.version,
                symbol=symbol,
                timeframe="1d",
                available_date=trade_date,
                source_id=f"structure:{structure.structure_id}",
            )
            lifecycle_id = f"{spec.rule_id}:{structure.structure_id}:{trade_date.isoformat()}"
            events.append(
                make_event(
                    event_id=event_id,
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BULLISH,
                    severity=Severity.IMPORTANT,
                    strength=60,
                    reason_cn=(
                        f"EMA 早期转强（结构关联）：收盘价重新站上 EMA20 且 EMA20 向上，"
                        f"关联底部 {structure.structure_type} C={structure.c_price:.4f}"
                    ),
                    provenance=spec.provenance,
                    structure_id=structure.structure_id,
                    lifecycle_id=lifecycle_id,
                    evidence={
                        "close": float(row["close"]),
                        "ema20": float(row["ema20"]),
                        "previous_close": float(previous["close"]),
                        "previous_ema20": float(previous["ema20"]),
                    },
                    invalidation={
                        "condition": "关联底部触及 C 失效，或颜色转黑",
                    },
                )
            )
    return events


@dataclass
class AnalysisResult:
    """完整分析结果。"""

    symbol: str
    display_name: str
    frame: pd.DataFrame
    weekly_trend: pd.DataFrame
    events: list[SignalEvent]
    structures: list[StructureInstance]
    pivots: tuple[Pivot, ...]
    history: list[DayState]
    assessment: DailyAssessment
    b1: B1Resistance | None
    profile: VolumeProfileProxy | None
    price_data: PriceData
    suspicious_gaps: tuple[pd.Timestamp, ...] = ()
    assessments_by_date: dict[date, DailyAssessment] = field(default_factory=dict)
    # 修复 8：行情获取失败时是否使用了本地缓存兜底
    cache_fallback_used: bool = False
    cache_age_seconds: float | None = None

    @property
    def bottoms(self) -> list[StructureInstance]:
        return [s for s in self.structures if s.side == "bottom"]

    @property
    def tops(self) -> list[StructureInstance]:
        return [s for s in self.structures if s.side == "top"]

    @property
    def event_frame(self) -> pd.DataFrame:
        log = EventLog()
        log.extend(self.events)
        return log.to_frame()


def analyze(
    symbol: str,
    *,
    provider: PriceProvider | None = None,
    as_of: date | None = None,
    build_history: bool = False,
    cache_root: str | None = None,
    cache_max_age_seconds: float = 86400.0,
    sqlite_path: str | None = None,
    run_id: str | None = None,
) -> AnalysisResult:
    """完整分析（修复 8：行情成功获取后写入 Parquet 缓存 + SQLite 持久化）。

    流程：
      1. 用 provider 获取行情；
      2. 写入 Parquet 缓存（仅成功获取时）；
      3. 运行完整分析；
      4. 事件、结构、评估、运行元数据写入 SQLite（同 event_id 幂等忽略）。

    网络失败时（provider.fetch 抛 DataUnavailableError）：
      - 如果存在近期缓存且未过期 → 读取缓存并显示陈旧警告。
      - 否则继续抛出原异常，提示用户重试或导入本地数据。
    """
    from datetime import datetime

    from lei_signal.data.cache import ParquetCache
    from lei_signal.storage.sqlite_store import (
        record_run,
        write_assessment,
        write_events,
        write_structures,
    )

    price_provider = provider or default_provider()
    cache = ParquetCache(cache_root) if cache_root else None
    cache_fallback_used = False
    cache_age = None

    try:
        price_data = price_provider.fetch(symbol, min_rows=MIN_BARS)
    except DataUnavailableError as exc:
        if cache is None:
            raise
        cached = cache.read(symbol, kind="bars", required_columns=("open", "close"))
        if cached is None:
            raise
        # 只取一次缓存年龄：原写法连调三次 age_seconds，
        # 既多做磁盘 stat，也可能在三次调用之间读到不同的值。
        cached_age = cache.age_seconds(symbol)
        if cached_age is None or cached_age > cache_max_age_seconds:
            raise DataUnavailableError(
                f"{exc}\n且本地缓存不可用或已过期，无法离线回放"
            ) from exc
        cache_age = cached_age
        cache_fallback_used = True
        # 用缓存构造一个 PriceData-like 对象
        from lei_signal.data.providers import PriceData
        from lei_signal.data.symbols import resolve_symbol
        from lei_signal.data.validation import ValidationReport
        report = ValidationReport(
            rows=len(cached),
            first_date=cached.index[0],
            last_date=cached.index[-1],
            adjusted=True,
            provider="parquet_cache",
            duplicates_removed=0,
            warnings=("cache_stale", f"cache age {cache_age:.0f}s"),
        )
        info = resolve_symbol(symbol)
        price_data = PriceData(
            symbol=info.symbol,
            display_name=info.symbol,
            bars=cached,
            report=report,
            info=info,
        )

    bars = price_data.bars
    if as_of is not None:
        bars = bars.loc[bars.index <= pd.Timestamp(as_of)]
        if len(bars) < MIN_BARS:
            raise DataUnavailableError(
                f"{price_data.symbol} 截止 {as_of} 只有 {len(bars)} 根日K线，至少需要 {MIN_BARS} 根"
            )

    # 成功获取行情：写入 Parquet 缓存（仅在未使用缓存兜底时）。
    # 只吞掉「写缓存本身」会遇到的错误：磁盘/权限（OSError）、
    # 缺少 pyarrow（ImportError）、列结构不合法（ValueError）。
    # 不用裸 except：真正的逻辑缺陷必须暴露出来，而不是被缓存分支静默吃掉。
    if cache is not None and not cache_fallback_used:
        with suppress(OSError, ImportError, ValueError):
            cache.write(price_data.symbol, price_data.bars)

    result = analyze_bars(
        price_data.symbol,
        bars,
        display_name=price_data.display_name,
        price_data=price_data,
        build_history=build_history,
    )
    # 标记是否用了缓存兜底
    if cache_fallback_used:
        result.cache_fallback_used = True
        result.cache_age_seconds = cache_age

    # 持久化到 SQLite。落库失败（磁盘满、库被锁、路径不可写）不应阻断分析结果返回，
    # 但只吞 sqlite3.Error / OSError；其他异常说明是真的写错了数据，必须抛出。
    # 用 closing 包住连接：原写法在中途抛错时会跳过 conn.close() 造成连接泄漏。
    if sqlite_path is not None:
        from lei_signal.storage.sqlite_store import connect

        with (
            suppress(sqlite3.Error, OSError),
            closing(connect(sqlite_path)) as conn,
            conn,
        ):
            write_events(conn, result.events, run_id=run_id)
            write_structures(conn, result.structures)
            write_assessment(conn, result.assessment)
            if run_id is not None:
                record_run(
                    conn,
                    run_id=run_id,
                    symbol=result.symbol,
                    started_at=datetime.now(UTC).isoformat(),
                    ruleset_version=result.assessment.rule_ruleset_version,
                    provider=price_data.report.provider,
                    last_data_date=result.frame.index[-1].date(),
                    event_count=len(result.events),
                )

    return result


def analyze_bars(
    symbol: str,
    bars: pd.DataFrame,
    *,
    display_name: str | None = None,
    price_data: PriceData | None = None,
    build_history: bool = False,
) -> AnalysisResult:
    """对已获取的行情执行完整分析。便于测试与离线复算。"""
    if len(bars) < MIN_BARS:
        raise DataUnavailableError(f"{symbol} 只有 {len(bars)} 根日K线，至少需要 {MIN_BARS} 根")

    # 特征与逐日状态
    frame = compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))
    weekly_trend = compute_weekly_long_trend(aggregate_weekly(bars))
    pivots = confirmed_pivots(frame)

    # 原子事件
    log = EventLog()
    log.extend(detect_color_events(frame, symbol))
    # EMA 早期转强事件延后到 bottoms 构建完成后，绑定到具体底部结构
    log.extend(detect_dual_ma_confirm_events(frame, symbol))
    log.extend(detect_spread_events(frame, symbol))
    log.extend(detect_long_trend_events(frame, symbol, timeframe="1d"))
    if not weekly_trend.empty:
        log.extend(detect_long_trend_events(weekly_trend, symbol, timeframe="1w"))
    reversal_events = detect_reversal_events(frame, symbol)
    log.extend(reversal_events)
    log.extend(_pivot_events(pivots, symbol))

    # 结构
    bottoms = (
        detect_higher_low_bottoms(frame, pivots, symbol)
        + detect_double_bottoms(frame, pivots, symbol)
        + detect_reversal_bottoms(frame, symbol, reversal_events)
    )
    tops = detect_top_structures(frame, pivots, symbol)
    structures = [*bottoms, *tops]

    # 修复 3：EMA 早期转强必须绑定到底部结构。
    # 原始「全局」事件不再产生；改用结构关联的派生事件。
    log.extend(_detect_structure_bound_ema_reclaim(frame, symbol, bottoms))

    log.extend(
        detect_volume_events(
            frame,
            symbol,
            structure_necklines=_build_structure_necklines(bottoms),
        )
    )
    log.extend(detect_bottom_structure_events(bottoms, symbol))
    log.extend(detect_top_structure_events(tops, symbol))
    # C 生命周期会就地修改结构状态，必须在状态机之前执行
    log.extend(apply_c_lifecycle(frame, bottoms, symbol))
    # Top+Black 需要读取顶部有效性，因此在顶部结构建立之后执行
    log.extend(detect_key_wave_events(frame, symbol, tops=tops))

    events = log.events()
    last_date = frame.index[-1].date()
    history = run_state_machine(
        frame, structures, weekly_trend=weekly_trend,
        ema_reclaim_events=events,
    )
    # 生命周期分配集中在 events.lifecycle：pipeline 只负责编排，
    # 「事件何时结束」属于事件域自身的规则。执行后不再有 valid_until=None。
    events = assign_lifecycles(events, structures, history, last_date)

    # 重新排序与回填
    log = EventLog()
    log.extend(events)

    # 最新一天的解释
    last_state = history[-1]
    previous_state = history[-2] if len(history) >= 2 else None
    last_close = float(frame["close"].iloc[-1])
    primary_c = (
        last_state.primary_bottom.c_price if last_state.primary_bottom is not None else None
    )
    b1 = find_b1(
        pivots,
        as_of=last_state.day,
        current_close=last_close,
        c_price=primary_c,
    )
    profile = compute_volume_profile(frame)

    assessment = build_assessment(
        symbol=symbol,
        frame=frame,
        day_state=last_state,
        previous_state=previous_state,
        events=events,
        structures=structures,
        b1=b1,
        profile=profile,
    )

    assessments: dict[date, DailyAssessment] = {assessment.as_of: assessment}
    if build_history:
        for index, state in enumerate(history):
            if state.day == assessment.as_of:
                continue
            previous = history[index - 1] if index > 0 else None
            day_close = float(frame["close"].loc[pd.Timestamp(state.day)])
            day_c = (
                state.primary_bottom.c_price if state.primary_bottom is not None else None
            )
            assessments[state.day] = build_assessment(
                symbol=symbol,
                frame=frame,
                day_state=state,
                previous_state=previous,
                events=events,
                structures=structures,
                b1=find_b1(
                    pivots,
                    as_of=state.day,
                    current_close=day_close,
                    c_price=day_c,
                ),
                profile=None,
            )

    return AnalysisResult(
        symbol=symbol,
        display_name=display_name or symbol,
        frame=frame,
        weekly_trend=weekly_trend,
        events=events,
        structures=structures,
        pivots=pivots,
        history=history,
        assessment=assessment,
        b1=b1,
        profile=profile,
        price_data=price_data,  # type: ignore[arg-type]
        suspicious_gaps=detect_unadjusted_gaps(bars),
        assessments_by_date=assessments,
    )


def _pivot_events(pivots: tuple[Pivot, ...], symbol: str) -> list[SignalEvent]:
    """摆动点确认事件：event_date 是拐点日，available_date 是确认日。"""
    from lei_signal.domain.canonical import make_event_id
    from lei_signal.domain.rules_config import get_rule
    from lei_signal.domain.types import Direction, Severity
    from lei_signal.events.log import make_event

    spec = get_rule("swing_pivots")
    events: list[SignalEvent] = []
    for pivot in pivots:
        label = "swing_low_confirmed" if pivot.kind == "low" else "swing_high_confirmed"
        events.append(
            make_event(
                event_id=make_event_id(
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    symbol=symbol,
                    timeframe="1d",
                    available_date=pivot.available_date,
                    source_id=f"{label}:{pivot.pivot_date}:{pivot.price:.6f}",
                ),
                symbol=symbol,
                event_date=pivot.pivot_date,        # 形态实际发生日
                available_date=pivot.available_date,  # 三左三右确认后才可用
                rule_id=spec.rule_id,
                rule_version=spec.version,
                direction=Direction.BULLISH if pivot.kind == "low" else Direction.BEARISH,
                severity=Severity.INFO,
                strength=40,
                reason_cn=(
                    f"确认{'摆动低点' if pivot.kind == 'low' else '摆动高点'}"
                    f"{pivot.price:.4f}（拐点{pivot.pivot_date}，"
                    f"三左三右于{pivot.available_date}确认）"
                ),
                provenance=spec.provenance,
                evidence={
                    "sub_rule": label,
                    "kind": pivot.kind,
                    "price": pivot.price,
                    "pivot_date": str(pivot.pivot_date),
                    "left": spec.param("left", 3),
                    "right": spec.param("right", 3),
                },
                invalidation={"condition": "摆动点一经确认不再变更"},
            )
        )
    return events


__all__ = ["MIN_BARS", "AnalysisResult", "analyze", "analyze_bars"]
