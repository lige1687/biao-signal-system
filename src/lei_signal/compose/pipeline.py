"""分析编排：把行情、特征、规则、结构、状态机与解释串联成单一入口。

界面只调用本模块，不重复实现任何业务规则。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lei_signal.compose.interpreter import build_assessment
from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.data.providers import PriceData, PriceProvider, default_provider
from lei_signal.data.validation import DataUnavailableError, detect_unadjusted_gaps
from lei_signal.domain.types import (
    DailyAssessment,
    Pivot,
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
    detect_ema20_reclaim_events,
    detect_spread_events,
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
) -> AnalysisResult:
    """完整分析。

    as_of 用于点位回放（无未来函数测试）；build_history=True 时
    额外为每一天构造解释快照，用于研究与时间轴。
    """
    price_provider = provider or default_provider()
    price_data = price_provider.fetch(symbol, min_rows=MIN_BARS)
    bars = price_data.bars
    if as_of is not None:
        bars = bars.loc[bars.index <= pd.Timestamp(as_of)]
        if len(bars) < MIN_BARS:
            raise DataUnavailableError(
                f"{price_data.symbol} 截止 {as_of} 只有 {len(bars)} 根日K线，至少需要 {MIN_BARS} 根"
            )

    return analyze_bars(
        price_data.symbol,
        bars,
        display_name=price_data.display_name,
        price_data=price_data,
        build_history=build_history,
    )


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
    log.extend(detect_ema20_reclaim_events(frame, symbol))
    log.extend(detect_dual_ma_confirm_events(frame, symbol))
    log.extend(detect_spread_events(frame, symbol))
    log.extend(detect_long_trend_events(frame, symbol, timeframe="1d"))
    if not weekly_trend.empty:
        log.extend(detect_long_trend_events(weekly_trend, symbol, timeframe="1w"))
    reversal_events = detect_reversal_events(frame, symbol)
    log.extend(reversal_events)
    log.extend(detect_volume_events(frame, symbol))
    log.extend(_pivot_events(pivots, symbol))

    # 结构
    bottoms = (
        detect_higher_low_bottoms(frame, pivots, symbol)
        + detect_double_bottoms(frame, pivots, symbol)
        + detect_reversal_bottoms(frame, symbol, reversal_events)
    )
    tops = detect_top_structures(frame, pivots, symbol)
    structures = [*bottoms, *tops]

    log.extend(detect_bottom_structure_events(bottoms, symbol))
    log.extend(detect_top_structure_events(tops, symbol))
    # C 生命周期会就地修改结构状态，必须在状态机之前执行
    log.extend(apply_c_lifecycle(frame, bottoms, symbol))
    # Top+Black 需要读取顶部有效性，因此在顶部结构建立之后执行
    log.extend(detect_key_wave_events(frame, symbol, tops=tops))

    events = log.events()

    # 状态机
    history = run_state_machine(frame, structures, weekly_trend=weekly_trend)

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
