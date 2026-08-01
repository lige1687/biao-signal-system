"""双均线规则：EMA20 早期转强、共同确认、开口变化。

关键设计：共同确认读取**当前状态**，不要求 EMA20 穿越与 SMA20 确认
发生在同一天。这是修正旧回测「必须同一天共同成立」漏信号的核心。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event


def ema20_reclaim_state(frame: pd.DataFrame) -> pd.Series:
    """EMA20 早期转强逐日布尔。

        前一日 Close <= 前一日 EMA20
        当日 Close > 当日 EMA20
        当日 EMA20 > 前一日 EMA20
    """
    close = frame["close"]
    ema20 = frame["ema20"]
    previous_close = close.shift(1)
    previous_ema = ema20.shift(1)
    ready = frame[["close", "ema20"]].notna().all(axis=1) & previous_ema.notna()
    return (
        ready
        & (previous_close <= previous_ema)
        & (close > ema20)
        & (ema20 > previous_ema)
    ).fillna(False)


def dual_ma_bull_state(frame: pd.DataFrame) -> pd.Series:
    """双均线共同确认逐日布尔（读取当前状态）。

        Close > EMA20 且 Close > SMA20
        EMA20 向上 且 SMA20 向上
        当前颜色为绿色
    """
    required = ("close", "ema20", "sma20", "signal_color")
    for column in required:
        if column not in frame.columns:
            raise ValueError(f"共同确认需要列 {column}")
    ema20 = frame["ema20"]
    sma20 = frame["sma20"]
    ready = frame[["close", "ema20", "sma20"]].notna().all(axis=1)
    ema_rising = ema20 > ema20.shift(1)
    sma_rising = sma20 > sma20.shift(1)
    return (
        ready
        & (frame["close"] > ema20)
        & (frame["close"] > sma20)
        & ema_rising
        & sma_rising
        & frame["signal_color"].eq("green")
    ).fillna(False)


def detect_ema20_reclaim_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """早期转强事件。"""
    spec = get_rule("ema20_reclaim_rising")
    state = ema20_reclaim_state(frame)
    events: list[SignalEvent] = []
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
                direction=Direction.BULLISH,
                severity=Severity.IMPORTANT,
                strength=60,
                reason_cn="收盘价重新站上EMA20，且EMA20开始向上（早期转强）",
                provenance=spec.provenance,
                evidence={
                    "close": float(row["close"]),
                    "ema20": float(row["ema20"]),
                    "previous_close": float(previous["close"]),
                    "previous_ema20": float(previous["ema20"]),
                },
                invalidation={
                    "condition": "收盘重新跌回EMA20之下，或结构触及C",
                },
            )
        )
    return events


def detect_dual_ma_confirm_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """共同确认事件：由不成立转为成立时记录一次，持续期间不重复。"""
    spec = get_rule("dual_ma_bull_confirmed")
    state = dual_ma_bull_state(frame)
    starts = state & ~state.shift(1, fill_value=False)
    events: list[SignalEvent] = []
    for timestamp in frame.index[starts]:
        row = frame.loc[timestamp]
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
                direction=Direction.BULLISH,
                severity=Severity.IMPORTANT,
                strength=70,
                reason_cn="收盘价同时高于EMA20与MA20，且两条均线当前均向上，颜色为绿色（共同确认）",
                provenance=spec.provenance,
                evidence={
                    "close": float(row["close"]),
                    "ema20": float(row["ema20"]),
                    "sma20": float(row["sma20"]),
                    "color": str(row["signal_color"]),
                },
                invalidation={"condition": "任一均线转向下、跌破均线或颜色不再为绿色"},
            )
        )
    return events


def detect_spread_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """双均线开口：交叉、扩大、缩小。辅助信号，不单独决定趋势。"""
    spec = get_rule("dual_ma_spread")
    if "ma_spread" not in frame.columns:
        return []

    events: list[SignalEvent] = []
    change = frame["ma_spread_change"]
    above = frame["ema20_above_sma20"]
    ready = frame["ma_spread"].notna() & change.notna()

    expanding = ready & (change > 0) & (change.shift(1) > 0) & frame["signal_color"].isin(
        ["green", "black"]
    )
    contracting = ready & (change < 0) & (change.shift(1) < 0)
    crossing = ready & above.notna() & above.shift(1).notna() & above.ne(above.shift(1))

    for label, mask, direction, severity, reason in (
        (
            "dual_ma_spread_expanding",
            expanding,
            Direction.NEUTRAL,
            Severity.INFO,
            "EMA20与MA20开口连续两日扩大（辅助信号）",
        ),
        (
            "dual_ma_spread_contracting",
            contracting,
            Direction.NEUTRAL,
            Severity.INFO,
            "EMA20与MA20开口连续两日收窄（辅助信号）",
        ),
        (
            "dual_ma_cross",
            crossing,
            Direction.NEUTRAL,
            Severity.WATCH,
            "EMA20与MA20相对位置发生改变（辅助信号）",
        ),
    ):
        for timestamp in frame.index[mask]:
            row = frame.loc[timestamp]
            trade_date = timestamp.date()
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id=label,
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=direction,
                    severity=severity,
                    strength=30,
                    reason_cn=reason,
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": label,
                        "ma_spread": float(row["ma_spread"]),
                        "ma_spread_change": float(row["ma_spread_change"]),
                        "ema20_above_sma20": bool(row["ema20_above_sma20"]),
                    },
                    invalidation={"condition": "开口方向或相对位置再次改变"},
                )
            )
    return events


__all__ = [
    "detect_dual_ma_confirm_events",
    "detect_ema20_reclaim_events",
    "detect_spread_events",
    "dual_ma_bull_state",
    "ema20_reclaim_state",
]
