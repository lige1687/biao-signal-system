"""日线与周线长周期背景（EMA60 / EMA120）。

绝对约束：长周期状态只能作为独立背景标签，
**不得**写入底部结构识别器作为硬门槛。这是修正旧回测漏信号的关键。

周线只在本周最后一个已完成交易日后生效（由 data.point_in_time.aggregate_weekly
保证），禁止把周五数据泄漏给周一至周四。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Direction, LongTrendState, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.features.indicators import seeded_ema


def compute_long_trend(frame: pd.DataFrame) -> pd.DataFrame:
    """逐日长周期状态。

    long_bull        EMA60 > EMA120
    long_bear        EMA60 < EMA120
    long_stable_bull EMA60 > EMA120 且两者均不下降
    long_improving   至少一条上升，且 (EMA60-EMA120) 向多头方向改善
    long_deteriorating (EMA60-EMA120) 向空头方向恶化
    """
    for column in ("ema60", "ema120"):
        if column not in frame.columns:
            raise ValueError(f"长周期状态需要列 {column}")

    result = frame.copy()
    ema60 = result["ema60"]
    ema120 = result["ema120"]
    ready = ema60.notna() & ema120.notna()

    gap = ema60 - ema120
    gap_change = gap.diff()
    ema60_rising = ema60.diff() > 0
    ema120_rising = ema120.diff() > 0
    ema60_falling = ema60.diff() < 0
    ema120_falling = ema120.diff() < 0

    bull = ready & (gap > 0)
    stable_bull = bull & ~ema60_falling & ~ema120_falling
    improving = ready & (ema60_rising | ema120_rising) & (gap_change > 0)
    deteriorating = ready & (gap_change < 0)

    # 优先级：稳定多头 > 多头 > 改善中 > 恶化中 > 空头
    result["long_trend"] = np.select(
        [~ready, stable_bull, bull, improving, deteriorating, ready & (gap < 0)],
        [
            LongTrendState.UNKNOWN.value,
            LongTrendState.LONG_STABLE_BULL.value,
            LongTrendState.LONG_BULL.value,
            LongTrendState.LONG_IMPROVING.value,
            LongTrendState.LONG_DETERIORATING.value,
            LongTrendState.LONG_BEAR.value,
        ],
        default=LongTrendState.UNKNOWN.value,
    )
    result["long_gap"] = gap
    result["long_gap_change"] = gap_change
    result["long_is_supportive"] = bull
    result["long_is_improving"] = improving
    return result


def compute_weekly_long_trend(weekly: pd.DataFrame) -> pd.DataFrame:
    """周线长周期状态。

    输入必须来自 aggregate_weekly（已排除进行中的周），
    索引即每周最后一个已完成交易日 = 该周线的 available_date。
    """
    if weekly.empty:
        return weekly.assign(long_trend=[], long_gap=[], long_gap_change=[])
    frame = weekly.copy()
    close = frame["close"].astype(float)
    frame["ema60"] = seeded_ema(close, 60)
    frame["ema120"] = seeded_ema(close, 120)
    # 周线样本少时退化为较短周期，避免整列 NaN 造成「无背景」误读为冲突。
    if frame["ema60"].isna().all():
        frame["ema60"] = seeded_ema(close, min(20, max(2, len(frame) // 3)))
    if frame["ema120"].isna().all():
        frame["ema120"] = seeded_ema(close, min(40, max(3, len(frame) // 2)))
    return compute_long_trend(frame)


def latest_weekly_state(weekly_trend: pd.DataFrame, as_of: pd.Timestamp) -> LongTrendState:
    """取截止 as_of 已经可用的最新周线状态。

    因为索引是「已完成周的最后交易日」，此处的 <= 比较即为无泄漏保证。
    """
    if weekly_trend.empty:
        return LongTrendState.UNKNOWN
    visible = weekly_trend.loc[weekly_trend.index <= pd.Timestamp(as_of)]
    if visible.empty:
        return LongTrendState.UNKNOWN
    return LongTrendState(str(visible["long_trend"].iloc[-1]))


def detect_long_trend_events(
    frame: pd.DataFrame,
    symbol: str,
    *,
    timeframe: str = "1d",
) -> list[SignalEvent]:
    """长周期交叉与背景改善/恶化事件。"""
    spec = get_rule("long_trend")
    if "long_trend" not in frame.columns:
        return []

    events: list[SignalEvent] = []
    gap = frame["long_gap"]
    ready = gap.notna()
    previous_gap = gap.shift(1)
    cross_up = ready & previous_gap.notna() & (previous_gap <= 0) & (gap > 0)
    cross_down = ready & previous_gap.notna() & (previous_gap >= 0) & (gap < 0)

    state = frame["long_trend"]
    previous_state = state.shift(1)
    improved = (
        state.isin([LongTrendState.LONG_IMPROVING.value, LongTrendState.LONG_STABLE_BULL.value])
        & ~previous_state.isin(
            [LongTrendState.LONG_IMPROVING.value, LongTrendState.LONG_STABLE_BULL.value]
        )
        & previous_state.notna()
    )
    deteriorated = (
        state.eq(LongTrendState.LONG_DETERIORATING.value)
        & previous_state.ne(LongTrendState.LONG_DETERIORATING.value)
        & previous_state.notna()
    )

    prefix = "weekly" if timeframe == "1w" else "daily"
    for label, mask, direction, severity, reason in (
        (
            f"{prefix}_long_cross_up",
            cross_up,
            Direction.BULLISH,
            Severity.IMPORTANT,
            f"{'周线' if timeframe == '1w' else '日线'}EMA60上穿EMA120（长周期背景转多）",
        ),
        (
            f"{prefix}_long_cross_down",
            cross_down,
            Direction.BEARISH,
            Severity.IMPORTANT,
            f"{'周线' if timeframe == '1w' else '日线'}EMA60下穿EMA120（长周期背景转空）",
        ),
        (
            "long_context_improved",
            improved,
            Direction.BULLISH,
            Severity.WATCH,
            f"{'周线' if timeframe == '1w' else '日线'}长周期背景转为改善",
        ),
        (
            "long_context_deteriorated",
            deteriorated,
            Direction.BEARISH,
            Severity.WATCH,
            f"{'周线' if timeframe == '1w' else '日线'}长周期背景转为恶化",
        ),
    ):
        for timestamp in frame.index[mask.fillna(False)]:
            row = frame.loc[timestamp]
            trade_date = timestamp.date()
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe=timeframe,
                        available_date=trade_date,
                        source_id=label,
                    ),
                    symbol=symbol,
                    timeframe=timeframe,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=direction,
                    severity=severity,
                    strength=45,
                    reason_cn=reason,
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": label,
                        "ema60": float(row["ema60"]),
                        "ema120": float(row["ema120"]),
                        "long_trend": str(row["long_trend"]),
                    },
                    invalidation={"condition": "长周期状态再次改变"},
                )
            )
    return events


__all__ = [
    "compute_long_trend",
    "compute_weekly_long_trend",
    "detect_long_trend_events",
    "latest_weekly_state",
]
