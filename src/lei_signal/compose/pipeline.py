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
from lei_signal.data.calendar import TradingCalendar
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
from lei_signal.rules.dense_breakout import detect_dense_breakout_events
from lei_signal.rules.dual_ma import detect_dual_ma_confirm_events, detect_spread_events
from lei_signal.rules.ema_reclaim_tiers import detect_structure_bound_ema_reclaim
from lei_signal.rules.exit_ema20_costbasis import detect_exit_ema20_costbasis_events
from lei_signal.rules.false_breakout_reclaim import detect_false_breakout_reclaim_events
from lei_signal.rules.false_breakout_reclaim_short import (
    detect_false_breakout_reclaim_short_events,
)
from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events
from lei_signal.rules.key_wave import detect_key_wave_events
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import (
    compute_long_trend,
    compute_weekly_long_trend,
    detect_long_trend_events,
)
from lei_signal.rules.low_level_confirmation import detect_low_level_confirmation_events
from lei_signal.rules.ma_full_alignment import detect_ma_alignment_events
from lei_signal.rules.module_d_false_breakout import detect_module_d_events
from lei_signal.rules.resistance_b1 import B1Resistance, find_b1
from lei_signal.rules.reversals import detect_reversal_events
from lei_signal.rules.top_structure import detect_top_structure_events, detect_top_structures
from lei_signal.rules.two_b_reversal import detect_two_b_reversal_events
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
    # 研究库持久化状态：None=未配置/未尝试，True=成功，False=失败（失败须可见，不静默）
    sqlite_persisted: bool | None = None

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
    calendar: TradingCalendar | None = None,
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

    参数
    ----
    calendar:
        交易所日历（Round 3 修复 D5）。透传给 ``analyze_bars`` →
        ``aggregate_weekly``，使节假日短周能在其最后一个交易日收盘后
        立即形成完整周线。留空时使用 ``DEFAULT_TRADING_CALENDAR``
        （周一至周五、无节假日表），保守且永不提前完成周线。
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
            # 必须显式记录来源：缓存文件名只由 symbol 决定，
            # 不带来源标记的缓存无法与合成/夹具数据区分（见 cache.py 模块注释）。
            cache.write(
                price_data.symbol,
                price_data.bars,
                provider=price_data.report.provider,
            )

    result = analyze_bars(
        price_data.symbol,
        bars,
        display_name=price_data.display_name,
        price_data=price_data,
        build_history=build_history,
        calendar=calendar,
    )
    # 标记是否用了缓存兜底
    if cache_fallback_used:
        result.cache_fallback_used = True
        result.cache_age_seconds = cache_age

    # 持久化到 SQLite。落库失败（磁盘满、库被锁、路径不可写）不应阻断分析结果返回，
    # 但失败必须**可见**——用显式 try/except 捕获后写入 result.sqlite_persisted=False，
    # 由 UI 明确提示，而不是静默吞掉让用户以为已持久化。
    # 只捕获 sqlite3.Error / OSError；其他异常说明是真的写错了数据，必须抛出。
    # 用 closing 包住连接：中途抛错时仍会关闭连接，避免泄漏。
    if sqlite_path is not None:
        from lei_signal.storage.sqlite_store import (
            connect,
            write_event_lifecycles,
        )

        try:
            with closing(connect(sqlite_path)) as conn:
                write_events(conn, result.events, run_id=run_id)
                write_structures(conn, result.structures)
                write_assessment(conn, result.assessment)
                # Round 3 修复 D3：同时把生命周期字段（valid_until / lifecycle_id /
                # ended_event_id）写入 ``event_lifecycle_snapshots`` 表，按
                # ``(event_id, run_id, as_of)`` 主键幂等覆盖（同一分析内一致）。
                # 多次增量分析会得到多条快照，``read_latest_lifecycle`` 按 as_of
                # 降序取最新——保留历史演变过程，不抹掉「当时我们以为它什么时候结束」。
                if run_id is not None:
                    as_of = result.frame.index[-1].date()
                    write_event_lifecycles(
                        conn, result.events, run_id=run_id, as_of=as_of
                    )
                    record_run(
                        conn,
                        run_id=run_id,
                        symbol=result.symbol,
                        started_at=datetime.now(UTC).isoformat(),
                        ruleset_version=result.assessment.rule_ruleset_version,
                        provider=price_data.report.provider,
                        last_data_date=as_of,
                        event_count=len(result.events),
                    )
            result.sqlite_persisted = True
        except (sqlite3.Error, OSError):
            result.sqlite_persisted = False

    return result


def analyze_bars(
    symbol: str,
    bars: pd.DataFrame,
    *,
    display_name: str | None = None,
    price_data: PriceData | None = None,
    build_history: bool = False,
    calendar: TradingCalendar | None = None,
) -> AnalysisResult:
    """对已获取的行情执行完整分析。便于测试与离线复算。

    参数
    ----
    calendar:
        交易所日历（Round 3 修复 D5）。透传给 ``aggregate_weekly``，
        与底层测试使用同一注入口径——不允许「底层能注入、生产注不进」。
        留空时 ``aggregate_weekly`` 使用 ``DEFAULT_TRADING_CALENDAR``。
    """
    if len(bars) < MIN_BARS:
        raise DataUnavailableError(f"{symbol} 只有 {len(bars)} 根日K线，至少需要 {MIN_BARS} 根")

    # 特征与逐日状态
    frame = compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))
    weekly_trend = compute_weekly_long_trend(aggregate_weekly(bars, calendar=calendar))
    pivots = confirmed_pivots(frame)

    # 原子事件
    log = EventLog()
    log.extend(detect_color_events(frame, symbol))
    # EMA 早期转强事件延后到 bottoms 构建完成后，绑定到具体底部结构
    log.extend(detect_dual_ma_confirm_events(frame, symbol))
    log.extend(detect_spread_events(frame, symbol))
    # 用户交易笔记的研究代理：完整多头趋势成立后，分别识别 SMA20/60/120
    # 的首次回撤。严格前向推进，不能由旧 Streamlit 泛化文案代替。
    log.extend(detect_first_ma_pullback_events(frame, symbol))
    # 模块 B 均线密集区突破：横盘密集区识别 -> 突破确认 -> 跌回失效（研究代理）。
    log.extend(detect_dense_breakout_events(frame, symbol))
    # 模块 C 2B/破底翻：L1/L2 结构 -> 破底翻三版本确认 -> 跌破 L2 失效（研究代理）。
    log.extend(detect_two_b_reversal_events(frame, symbol))
    # 模块 D 假跌破反转（V2 正式口径，§15 第三轮；与 false_breakout_reclaim 分组不合并）
    log.extend(detect_module_d_events(frame, symbol))
    # P2.1 假突破快速收回：突破前高/结构位后被打回，窗口内快速收回且不破坏趋势。
    log.extend(detect_false_breakout_reclaim_events(frame, symbol))
    # 模块 D2 做空镜像骨架：突破压力位后拉回 + sma20_slope<0 + 空头排列 -> 做空方向事件。
    log.extend(detect_false_breakout_reclaim_short_events(frame, symbol))
    # P2.3 完整均线排列成立/破坏 + EMA 斜率加速度（研究代理确认维度）。
    log.extend(detect_ma_alignment_events(frame, symbol))
    # P2.2 日线做多信号后的次级别确认（日线 OHLC 代理，系统未接 60 分钟）。
    log.extend(detect_low_level_confirmation_events(frame, symbol))
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

    # EMA 早期转强必须绑定到底部结构，且按档位分层：
    # candidate 期只进 early_watch（不构成结构确认或买入），确认后逐级升级。
    # 原始「全局」事件不再产生。
    log.extend(detect_structure_bound_ema_reclaim(frame, symbol, bottoms))

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
    # A6① 抵扣价退出（研究代理）：收盘同时跌破 EMA20 与 20 日抵扣价即触发退出事件。
    # 只依赖当日及此前已完成日 K，无未来泄漏；与黑色定义同构但独立成事件、可回测。
    log.extend(detect_exit_ema20_costbasis_events(frame, symbol))

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
