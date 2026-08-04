"""趋势后首次回撤 SMA20/60/120 的前向状态机门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.rules.first_ma_pullback import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_FAILED,
    SUB_RULE_TOUCHED,
    detect_first_ma_pullback_events,
)


def _feature_frame(rows: int = 70) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=rows)
    positions = pd.Series(range(rows), index=index, dtype=float)
    sma120 = 80.0 + positions * 0.05
    sma60 = 90.0 + positions * 0.08
    sma20 = 100.0 + positions * 0.12
    close = sma20 + 5.0
    frame = pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.8,
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
        },
        index=index,
    )
    frame.loc[index[10]:, "signal_color"] = "green"
    return frame


def _sub_rule(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def _period_events(frame: pd.DataFrame, period: int) -> list:
    return [
        event
        for event in detect_first_ma_pullback_events(frame, "TEST")
        if event.evidence["ma_period"] == period
    ]


def test_first_touch_requires_prior_separation_then_confirms() -> None:
    frame = _feature_frame()
    index = frame.index
    ma = float(frame.loc[index[20], "sma20"])
    frame.loc[index[20], ["open", "high", "low", "close"]] = [
        ma + 0.8,
        ma + 1.0,
        ma - 0.3,
        ma + 0.2,
    ]
    next_ma = float(frame.loc[index[21], "sma20"])
    frame.loc[index[21], ["open", "high", "low", "close"]] = [
        next_ma - 0.1,
        next_ma + 1.0,
        next_ma - 0.2,
        next_ma + 0.6,
    ]

    events = _period_events(frame, 20)
    assert [_sub_rule(event) for event in events] == [SUB_RULE_TOUCHED, SUB_RULE_CONFIRMED]
    assert events[0].available_date == index[20].date()
    assert events[1].available_date == index[21].date()
    assert events[0].lifecycle_id == events[1].lifecycle_id
    assert events[1].provenance.value == "research_proxy"
    assert events[1].evidence["trend_anchor_date"] == index[10].date().isoformat()


def test_second_pullback_in_same_trend_is_not_called_first_again() -> None:
    frame = _feature_frame()
    index = frame.index
    for position in (20, 35):
        ma = float(frame.loc[index[position], "sma20"])
        frame.loc[index[position], ["open", "high", "low", "close"]] = [
            ma - 0.1,
            ma + 1.0,
            ma - 0.3,
            ma + 0.7,
        ]

    events = _period_events(frame, 20)
    assert [_sub_rule(event) for event in events] == [SUB_RULE_TOUCHED, SUB_RULE_CONFIRMED]
    assert events[0].available_date == index[20].date()


def test_confirmation_window_expiry_consumes_first_touch() -> None:
    frame = _feature_frame()
    index = frame.index
    for position in (20, 21, 22):
        ma = float(frame.loc[index[position], "sma20"])
        frame.loc[index[position], ["open", "high", "low", "close"]] = [
            ma + 0.8,
            ma + 1.0,
            ma - 0.2,
            ma + 0.1,
        ]

    events = _period_events(frame, 20)
    assert [_sub_rule(event) for event in events] == [SUB_RULE_TOUCHED, SUB_RULE_FAILED]
    assert events[-1].available_date == index[22].date()
    assert "确认窗口耗尽" in str(events[-1].evidence["failure_reason"])


def test_new_trend_lifecycle_can_count_a_new_first_pullback() -> None:
    frame = _feature_frame()
    index = frame.index
    first_ma = float(frame.loc[index[20], "sma20"])
    frame.loc[index[20], ["open", "high", "low", "close"]] = [
        first_ma - 0.1,
        first_ma + 1.0,
        first_ma - 0.3,
        first_ma + 0.7,
    ]
    frame.loc[index[30], "signal_color"] = "black"
    frame.loc[index[31]:index[34], "signal_color"] = "gray"
    frame.loc[index[35]:, "signal_color"] = "green"
    second_ma = float(frame.loc[index[45], "sma20"])
    frame.loc[index[45], ["open", "high", "low", "close"]] = [
        second_ma - 0.1,
        second_ma + 1.0,
        second_ma - 0.3,
        second_ma + 0.7,
    ]

    events = _period_events(frame, 20)
    touches = [event for event in events if _sub_rule(event) == SUB_RULE_TOUCHED]
    confirms = [event for event in events if _sub_rule(event) == SUB_RULE_CONFIRMED]
    assert [event.available_date for event in touches] == [index[20].date(), index[45].date()]
    assert len(confirms) == 2
    assert touches[0].lifecycle_id != touches[1].lifecycle_id


def test_appending_future_bars_does_not_change_past_pullback_events() -> None:
    frame = _feature_frame(90)
    index = frame.index
    ma = float(frame.loc[index[20], "sma20"])
    frame.loc[index[20], ["open", "high", "low", "close"]] = [
        ma - 0.1,
        ma + 1.0,
        ma - 0.3,
        ma + 0.7,
    ]
    cutoff = 55
    early = detect_first_ma_pullback_events(frame.iloc[:cutoff], "TEST")
    full = detect_first_ma_pullback_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [event for event in full if event.available_date <= cutoff_date]
    assert [event.event_id for event in early] == [event.event_id for event in visible]
    assert [event.evidence for event in early] == [event.evidence for event in visible]
