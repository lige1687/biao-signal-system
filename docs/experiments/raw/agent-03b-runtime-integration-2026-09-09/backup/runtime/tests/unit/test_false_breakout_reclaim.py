"""假突破快速收回前向状态机门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.rules.false_breakout_reclaim import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_FAILED,
    SUB_RULE_WATCH,
    detect_false_breakout_reclaim_events,
)


def _feature_frame(rows: int = 80) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=rows)
    positions = pd.Series(range(rows), index=index, dtype=float)
    sma120 = 80.0 + positions * 0.05
    sma60 = 90.0 + positions * 0.08
    sma20 = 100.0 + positions * 0.12
    close = sma20
    frame = pd.DataFrame(
        {
            "open": close - 0.2,
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
        },
        index=index,
    )
    frame.loc[index[10]:, "signal_color"] = "green"
    return frame


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def _reference_at(frame: pd.DataFrame, position: int, lookback: int = 20) -> float:
    return float(frame["high"].rolling(window=lookback).max().shift(1).iloc[position])


def test_breakout_then_shake_then_reclaim_confirms() -> None:
    frame = _feature_frame()
    index = frame.index
    target = 45
    ref = _reference_at(frame, target)
    # 突破日：收盘明显超过参考位，且当日未盘中刺穿参考位。
    frame.loc[index[target], ["open", "high", "low", "close"]] = [
        ref * 1.0,
        ref * 1.03,
        ref * 1.02,
        ref * 1.02,
    ]
    # 被打回日：盘中刺穿参考位，收盘收回上方。
    frame.loc[index[target + 1], ["open", "high", "low", "close"]] = [
        ref * 0.99,
        ref * 1.02,
        ref * 0.98,
        ref * 1.01,
    ]
    events = detect_false_breakout_reclaim_events(frame, "TEST")
    assert [_sub(e) for e in events] == [SUB_RULE_WATCH, SUB_RULE_CONFIRMED]
    assert events[0].available_date == index[target + 1].date()
    assert events[1].available_date == index[target + 1].date()


def test_breakout_then_real_breakdown_fails() -> None:
    frame = _feature_frame()
    index = frame.index
    target = 45
    ref = _reference_at(frame, target)
    frame.loc[index[target], ["open", "high", "low", "close"]] = [
        ref * 1.0,
        ref * 1.03,
        ref * 1.02,
        ref * 1.02,
    ]
    # 真跌破：收盘低于参考位 fail_breakdown_pct(1%)。
    frame.loc[index[target + 1], ["open", "high", "low", "close"]] = [
        ref * 0.97,
        ref * 0.99,
        ref * 0.95,
        ref * 0.97,
    ]
    events = detect_false_breakout_reclaim_events(frame, "TEST")
    assert [_sub(e) for e in events] == [SUB_RULE_WATCH, SUB_RULE_FAILED]
    assert "真跌破参考位" in str(events[-1].evidence["failure_reason"])


def test_clean_breakout_without_shake_is_not_a_scenario() -> None:
    frame = _feature_frame()
    index = frame.index
    target = 45
    ref = _reference_at(frame, target)
    # 突破后一路向上，从不盘中刺穿参考位（>=ref 始终成立，未被打回）。
    for offset in range(1, 4):
        frame.loc[index[target + offset], ["open", "high", "low", "close"]] = [
            ref * 1.02,
            ref * 1.05,
            ref * 1.01,
            ref * 1.04,
        ]
    events = detect_false_breakout_reclaim_events(frame, "TEST")
    assert events == []


def test_appending_future_bars_does_not_change_past_events() -> None:
    frame = _feature_frame(100)
    index = frame.index
    target = 45
    ref = _reference_at(frame, target)
    frame.loc[index[target], ["open", "high", "low", "close"]] = [
        ref * 1.0,
        ref * 1.03,
        ref * 0.99,
        ref * 1.02,
    ]
    frame.loc[index[target + 1], ["open", "high", "low", "close"]] = [
        ref * 0.99,
        ref * 1.02,
        ref * 0.98,
        ref * 1.01,
    ]
    cutoff = 70
    early = detect_false_breakout_reclaim_events(frame.iloc[:cutoff], "TEST")
    full = detect_false_breakout_reclaim_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]
