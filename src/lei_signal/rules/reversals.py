"""反转 K 线：阳线/阴线反包与外包反转。

全部标注 research_proxy —— 除非后续逐帧核对视频证明与 LEI 原定义一致。

关键约束：这些事件必须独立保存，即使 EMA60 < EMA120、周线尚未改善，
也**不得**被长周期趋势 Block。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event


def bullish_engulfing_state(frame: pd.DataFrame) -> pd.Series:
    """阳线反包。

        前一日 Close < Open
        当日 Close > Open
        当日 Open <= 前一日 Close
        当日 Close >= 前一日 Open
    """
    open_, close = frame["open"], frame["close"]
    previous_open, previous_close = open_.shift(1), close.shift(1)
    return (
        (previous_close < previous_open)
        & (close > open_)
        & (open_ <= previous_close)
        & (close >= previous_open)
    ).fillna(False)


def bullish_outside_reversal_state(frame: pd.DataFrame) -> pd.Series:
    """阳线外包反转。

        当日 Low <= 前一日 Low
        当日 Close >= 前一日 High
        当日 Close > 当日 Open
    """
    return (
        (frame["low"] <= frame["low"].shift(1))
        & (frame["close"] >= frame["high"].shift(1))
        & (frame["close"] > frame["open"])
    ).fillna(False)


def bearish_engulfing_state(frame: pd.DataFrame) -> pd.Series:
    """阴线反包（阳线反包的镜像）。"""
    open_, close = frame["open"], frame["close"]
    previous_open, previous_close = open_.shift(1), close.shift(1)
    return (
        (previous_close > previous_open)
        & (close < open_)
        & (open_ >= previous_close)
        & (close <= previous_open)
    ).fillna(False)


def bearish_outside_reversal_state(frame: pd.DataFrame) -> pd.Series:
    """阴线外包反转。

        当日 High >= 前一日 High
        当日 Close <= 前一日 Low
        当日 Close < 当日 Open
    """
    return (
        (frame["high"] >= frame["high"].shift(1))
        & (frame["close"] <= frame["low"].shift(1))
        & (frame["close"] < frame["open"])
    ).fillna(False)


_RULES = (
    ("bullish_engulfing", bullish_engulfing_state, Direction.BULLISH, Severity.IMPORTANT),
    (
        "bullish_outside_reversal",
        bullish_outside_reversal_state,
        Direction.BULLISH,
        Severity.IMPORTANT,
    ),
    ("bearish_engulfing", bearish_engulfing_state, Direction.BEARISH, Severity.IMPORTANT),
    (
        "bearish_outside_reversal",
        bearish_outside_reversal_state,
        Direction.BEARISH,
        Severity.IMPORTANT,
    ),
)

_REASONS = {
    "bullish_engulfing": "阳线反包：当日阳线完全反包前一日阴线实体（研究代理规则）",
    "bullish_outside_reversal": (
        "阳线外包反转：最低价触及或跌破前一日最低价后，收盘反超前一日最高价（研究代理规则）"
    ),
    "bearish_engulfing": "阴线反包：当日阴线完全反包前一日阳线实体（研究代理规则）",
    "bearish_outside_reversal": (
        "阴线外包反转：最高价触及或超过前一日最高价后，收盘跌破前一日最低价（研究代理规则）"
    ),
}


def detect_reversal_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """全部四类反转事件。不受长周期趋势影响。"""
    events: list[SignalEvent] = []
    for rule_id, detector, direction, severity in _RULES:
        spec = get_rule(rule_id)
        state = detector(frame)
        for timestamp in frame.index[state]:
            row = frame.loc[timestamp]
            position = frame.index.get_loc(timestamp)
            previous = frame.iloc[position - 1]
            trade_date = timestamp.date()
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=direction,
                    severity=severity,
                    strength=55,
                    reason_cn=_REASONS[rule_id],
                    provenance=spec.provenance,
                    evidence={
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "previous_open": float(previous["open"]),
                        "previous_high": float(previous["high"]),
                        "previous_low": float(previous["low"]),
                        "previous_close": float(previous["close"]),
                    },
                    invalidation={
                        "condition": (
                            "跌破本K线最低价（看多）或突破本K线最高价（看空）"
                        )
                    },
                )
            )
    return events


__all__ = [
    "bearish_engulfing_state",
    "bearish_outside_reversal_state",
    "bullish_engulfing_state",
    "bullish_outside_reversal_state",
    "detect_reversal_events",
]
