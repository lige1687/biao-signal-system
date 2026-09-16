"""日线信号后的次级别确认（日线代理）门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.rules.low_level_confirmation import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_WATCH,
    detect_low_level_confirmation_events,
)


def _feature_frame(rows: int = 80) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=rows)
    positions = pd.Series(range(rows), index=index, dtype=float)
    sma120 = 80.0 + positions * 0.05
    sma60 = 90.0 + positions * 0.08
    sma20 = 100.0 + positions * 0.12
    ema20 = sma20
    close = sma20
    frame = pd.DataFrame(
        {
            "open": close + 0.1,  # 默认阴线（close<open），不触发
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000_000.0,
            "atr14": 2.0,
            "signal_color": "gray",
            "sma20": sma20,
            "sma60": sma60,
            "sma120": sma120,
            "sma20_slope": sma20.diff(),
            "sma60_slope": sma60.diff(),
            "sma120_slope": sma120.diff(),
            "ema20": ema20,
            "ema20_slope": ema20.diff(),
        },
        index=index,
    )
    frame.loc[index[10]:, "signal_color"] = "green"
    return frame


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_trigger_then_intraday_reclaim_confirms() -> None:
    frame = _feature_frame()
    index = frame.index
    target = 45
    sma20_next = float(frame.loc[index[target + 1], "sma20"])
    # 触发日：收阳且站上 EMA20/SMA20，但当日不出现盘中收回或反转 K 线。
    s_target = float(frame.loc[index[target], "sma20"])
    frame.loc[index[target], ["open", "high", "low", "close"]] = [
        s_target + 0.05,
        s_target + 0.5,
        s_target * 1.01,
        s_target + 0.1,
    ]
    # 确认日：盘中刺穿参考支撑（SMA20）后收盘收回上方。
    frame.loc[index[target + 1], ["open", "high", "low", "close"]] = [
        sma20_next,
        sma20_next * 1.02,
        sma20_next * 1.003,
        sma20_next * 1.01,
    ]
    events = detect_low_level_confirmation_events(frame, "TEST")
    assert [_sub(e) for e in events] == [SUB_RULE_WATCH, SUB_RULE_CONFIRMED]
    assert events[0].available_date == index[target].date()
    assert events[1].available_date == index[target + 1].date()


def test_trigger_without_confirmation_signal_stays_watch() -> None:
    frame = _feature_frame()
    index = frame.index
    target = 45
    s_target = float(frame.loc[index[target], "sma20"])
    frame.loc[index[target], ["open", "high", "low", "close"]] = [
        s_target + 0.05,
        s_target + 0.5,
        s_target * 1.01,
        s_target + 0.1,
    ]
    # 之后几天既不盘中收回也不出现反转 K 线（保持阳线但 low 远离参考支撑）。
    for offset in range(1, 3):
        s = float(frame.loc[index[target + offset], "sma20"])
        frame.loc[index[target + offset], ["open", "high", "low", "close"]] = [
            s,
            s * 1.03,
            s * 1.01,
            s * 1.02,
        ]
    events = detect_low_level_confirmation_events(frame, "TEST")
    assert [_sub(e) for e in events] == [SUB_RULE_WATCH]


def test_appending_future_bars_does_not_change_past_events() -> None:
    frame = _feature_frame(100)
    index = frame.index
    target = 45
    sma20_next = float(frame.loc[index[target + 1], "sma20"])
    frame.loc[index[target], ["open", "high", "low", "close"]] = [
        float(frame.loc[index[target], "sma20"]) - 0.1,
        float(frame.loc[index[target], "sma20"]) + 0.5,
        float(frame.loc[index[target], "sma20"]) - 0.5,
        float(frame.loc[index[target], "sma20"]) + 0.1,
    ]
    frame.loc[index[target + 1], ["open", "high", "low", "close"]] = [
        sma20_next,
        sma20_next * 1.02,
        sma20_next * 1.003,
        sma20_next * 1.01,
    ]
    cutoff = 70
    early = detect_low_level_confirmation_events(frame.iloc[:cutoff], "TEST")
    full = detect_low_level_confirmation_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]
