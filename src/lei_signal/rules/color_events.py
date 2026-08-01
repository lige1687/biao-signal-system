"""三色状态事件：区段起始事件，而不是每日重复提醒。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

_COLOR_EVENT = {
    "green": ("lei_color_green_started", Direction.BULLISH, Severity.IMPORTANT, "转为绿色"),
    "gray": ("lei_color_gray_started", Direction.NEUTRAL, Severity.WATCH, "转为灰色"),
    "black": ("lei_color_black_started", Direction.BEARISH, Severity.IMPORTANT, "转为黑色"),
}


def detect_color_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """颜色区段起始事件。

    连续绿色只产生一次开始事件（研究要求的事件去重口径），
    黑色持续期间也不每天重复提醒。
    """
    spec = get_rule("lei_color")
    events: list[SignalEvent] = []
    if frame.empty or "signal_color" not in frame.columns:
        return events

    colors = frame["signal_color"]
    previous = colors.shift(1)
    # 起始条件：与前一日不同，且当日已就绪（unknown 不产生事件）
    starts = frame[colors.ne(previous) & colors.isin(_COLOR_EVENT.keys())]

    for timestamp, row in starts.iterrows():
        color = str(row["signal_color"])
        source_id, direction, severity, label = _COLOR_EVENT[color]
        trade_date = timestamp.date()
        prior = str(previous.loc[timestamp]) if pd.notna(previous.loc[timestamp]) else "unknown"
        events.append(
            make_event(
                event_id=make_event_id(
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    symbol=symbol,
                    timeframe="1d",
                    available_date=trade_date,
                    source_id=source_id,
                ),
                symbol=symbol,
                event_date=trade_date,
                available_date=trade_date,   # 收盘即可知
                rule_id=spec.rule_id,
                rule_version=spec.version,
                direction=direction,
                severity=severity,
                strength=_strength(row),
                reason_cn=f"{label}：{row['signal_reason']}",
                provenance=spec.provenance,
                evidence={
                    "sub_rule": source_id,
                    "color": color,
                    "previous_color": prior,
                    "close": float(row["close"]),
                    "ema20": float(row["ema20"]),
                    "close_lag20": float(row["close_lag20"]),
                },
                invalidation={"condition": "颜色再次改变时本区段结束"},
            )
        )
    return events


def _strength(row: pd.Series) -> int:
    """同一规则内部强弱：收盘价偏离 EMA20 的幅度，截断到 0..100。"""
    close = float(row["close"])
    ema20 = float(row["ema20"])
    if ema20 <= 0:
        return 50
    deviation = abs(close - ema20) / ema20
    return int(min(100.0, deviation * 1000.0))


__all__ = ["detect_color_events"]
