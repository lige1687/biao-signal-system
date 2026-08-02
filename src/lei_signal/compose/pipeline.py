"""分析编排：把行情、特征、规则、结构、状态机与解释串联成单一入口。

界面只调用本模块，不重复实现任何业务规则。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date

import pandas as pd

from lei_signal.compose.interpreter import build_assessment
from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.data.providers import PriceData, PriceProvider, default_provider
from lei_signal.data.validation import DataUnavailableError, detect_unadjusted_gaps
from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.events.log import make_event
from lei_signal.domain.types import (
    DailyAssessment,
    Direction,
    Pivot,
    Severity,
    SignalEvent,
    StructureInstance,
)
from lei_signal.events.log import EventLog
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


# 一次性事件：valid_until = available_date + 1 day，
# 只在触发当日作为 new_events 出现。
_ONE_SHOT_RULES = frozenset(
    {
        "swing_pivots",            # 摆动点是历史事实
        "bullish_engulfing",       # 反转 K 线
        "bullish_outside_reversal",
        "bearish_engulfing",
        "bearish_outside_reversal",
        "volume_proxies",          # 放量/突破/缩量
        "bottom_c_lifecycle",      # C 触及/跌破快照
        "key_wave_black_started",  # 黑色起始
        "key_wave_black_ended",    # 黑色结束
        "top_plus_black",          # 组合状态进入
        "top_plus_black_ended",    # 组合状态退出
        "ema20_reclaim_rising",    # 单次转强（注意：bounding in 状态机再写 valid_until）
        "top_structure",          # 顶部结构事件
        "higher_low_bottom",
        "double_bottom",
        "bullish_reversal_bottom",
    }
)


def _one_shot_valid_until(available_date, last_date):
    """一次性事件的 valid_until：次日凌晨 00:00 之后视为「已结束」。

    若 last_date <= available_date（无后续数据），valid_until = last_date + 1 day。
    否则 valid_until = available_date + 1 day（仅当日作为 new）。
    """
    # 用次日凌晨作为 exclusive 上界：
    # valid_until = available_date + 1 day（exclusive）
    from datetime import timedelta
    candidate = available_date + timedelta(days=1)
    # 限定到数据范围内：valid_until 不能晚于 last_date + 1
    cap = last_date + timedelta(days=1)
    return candidate if candidate <= cap else cap


def _assign_lifecycle_intervals(
    events: list,
    history: list,
    last_date,
) -> list:
    """为状态型事件（颜色/EMA/共同确认）按时间顺序分配 valid_until + lifecycle_id。

    状态型事件的判定：某日当前状态 = 上一日不同 → 生成 start（valid_until=None 临时）；
    状态再次改变 → 写入前一个 start 的 valid_until = 当前日。
    """
    from datetime import timedelta
    from collections import defaultdict

    # 1) 一次性事件先标 valid_until
    updated: list = []
    for event in events:
        if event.rule_id in _ONE_SHOT_RULES:
            updated.append(event)
            continue
        updated.append(event)

    # 2) 状态型事件：颜色 / 共同确认
    #    对每个 rule_id，建立 (available_date, ended_date) 区间。
    #    当前状态可由 state.color.value、state.joint_confirmed_now 计算。
    #    EMA 转强由 state.early_strength_by_structure 决定。
    by_rule: dict[str, list] = defaultdict(list)
    for event in updated:
        if event.rule_id in _ONE_SHOT_RULES:
            continue
        if event.rule_id not in ("lei_color", "dual_ma_bull_confirmed",
                                  "ema20_reclaim_rising"):
            continue
        by_rule[event.rule_id].append(event)

    # 按 available_date 排序每个 rule 的事件
    for rule_id, evts in by_rule.items():
        evts.sort(key=lambda e: (e.available_date, e.event_id))

    # 3) 状态机逐日推进
    #    对于每条事件，找到它的 [start_date, end_date) 区间。
    #    规则：start_date = event.available_date，
    #    end_date = 状态改变的下一日（即下一个相同 rule_id 的 start_date），
    #    如果直到 last_date 状态一直保持 = 该 rule_id 的 start_date 仍有效，则 end_date = last_date + 1。
    history_index = {state.day: state for state in history}
    for rule_id, evts in by_rule.items():
        # 当前 state 值
        def state_value_at(day, rule_id=rule_id):
            state = history_index.get(day)
            if state is None:
                return None
            if rule_id == "lei_color":
                return state.color.value
            if rule_id == "dual_ma_bull_confirmed":
                return bool(state.joint_confirmed_now)
            if rule_id == "ema20_reclaim_rising":
                # EMA 转强：必须检查事件关联的特定结构是否仍 active
                # 不再回退到「任何结构 active」即整体 active
                for event in evts:
                    if event.available_date != day or event.structure_id is None:
                        continue
                    if state.early_strength_by_structure.get(event.structure_id, False):
                        return True
                return False
            return None

        # 重新生成状态型事件的 lifecycle_id 和 valid_until
        # 原始 start 事件：lifecycle_id = unique
        for index, event in enumerate(evts):
            # 找下一个 start：end_date 是 [start, next_start) 这段时间内状态保持，
            # 直到状态改变的那一天（next_start 的 available_date）
            next_start_day = None
            for later in evts[index + 1:]:
                if later is not event and later.available_date > event.available_date:
                    next_start_day = later.available_date
                    break
            if next_start_day is not None:
                event.valid_until = next_start_day
            else:
                # 最后一个 start：end_date 取决于状态在 last_date 是否仍 active
                state = history_index.get(last_date)
                if state is None:
                    event.valid_until = None  # 默认 = 永久
                else:
                    current = state_value_at(last_date)
                    if current:
                        event.valid_until = _add_day(last_date)
                    else:
                        # 状态在 last_date 已不是「active」：找最后一次为 active 的日
                        last_active_day = None
                        for state in history:
                            if (state_value_at(state.day) and state.day >= event.available_date):
                                last_active_day = state.day
                        if last_active_day is not None:
                            event.valid_until = _add_day(last_active_day)
                        else:
                            event.valid_until = event.available_date
            # 设置 lifecycle_id
            if event.lifecycle_id is None:
                event.lifecycle_id = f"{rule_id}:{event.event_id}"

    return updated


def _add_day(d):
    from datetime import timedelta
    return d + timedelta(days=1)


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
        if cache.age_seconds(symbol) is None or cache.age_seconds(symbol) > cache_max_age_seconds:
            raise DataUnavailableError(
                f"{exc}\n且本地缓存不可用或已过期，无法离线回放"
            ) from exc
        cache_age = cache.age_seconds(symbol)
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

    # 成功获取行情：写入 Parquet 缓存（仅在未使用缓存兜底时）
    if cache is not None and not cache_fallback_used:
        try:
            cache.write(price_data.symbol, price_data.bars)
        except Exception:  # noqa: BLE001
            # 缓存写入失败不应阻断分析
            pass

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

    # 持久化到 SQLite
    if sqlite_path is not None:
        try:
            from lei_signal.storage.sqlite_store import connect
            conn = connect(sqlite_path)
            with conn:
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
            conn.close()
        except Exception:  # noqa: BLE001
            # 持久化失败不应阻断主流程
            pass

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

    log.extend(detect_volume_events(frame, symbol, structure_necklines=_build_structure_necklines(bottoms)))
    log.extend(detect_bottom_structure_events(bottoms, symbol))
    log.extend(detect_top_structure_events(tops, symbol))
    # C 生命周期会就地修改结构状态，必须在状态机之前执行
    log.extend(apply_c_lifecycle(frame, bottoms, symbol))
    # Top+Black 需要读取顶部有效性，因此在顶部结构建立之后执行
    log.extend(detect_key_wave_events(frame, symbol, tops=tops))

    # 一次性事件（摆动点、反转 K 线、放量/突破/缩量、EMA 单次、C 触发生成）
    # 立即设置 valid_until = available_date + 1 day，确保只作为当日 new_events。
    events = log.events()
    last_date = frame.index[-1].date()
    for event in events:
        if event.valid_until is not None:
            continue
        if event.rule_id in _ONE_SHOT_RULES:
            event.valid_until = _one_shot_valid_until(
                event.available_date, last_date
            )
    # 状态型事件（颜色/EMA 转强/共同确认/Top+Black/Top结构/底部结构）必须
    # 等待状态机跑完后逐状态机生成 start/end 配对。
    # 先把 EMA 转强事件按「结构失效日 + 1」设置 valid_until（结构失效即关闭）。
    for event in events:
        if event.rule_id == "ema20_reclaim_rising" and event.structure_id:
            struct = next(
                (s for s in bottoms if s.structure_id == event.structure_id),
                None,
            )
            if struct and struct.invalidated_date is not None:
                event.valid_until = _add_day(struct.invalidated_date)
    history = run_state_machine(
        frame, structures, weekly_trend=weekly_trend,
        ema_reclaim_events=events,
    )
    events = _assign_lifecycle_intervals(events, history, last_date)

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
