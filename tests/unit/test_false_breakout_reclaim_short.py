"""假突破做空镜像骨架（模块 D2 骨架，方向=short）门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import Direction
from lei_signal.rules.false_breakout_reclaim_short import (
    SUB_RULE_SHORT_CONFIRMED,
    SUB_RULE_SHORT_FAILED,
    SUB_RULE_SHORT_WATCH,
    detect_false_breakout_reclaim_short_events,
)


def _frame(rows: int = 160) -> pd.DataFrame:
    index = pd.bdate_range("2023-01-02", periods=rows)
    close = [100.0 + i * 0.2 for i in range(rows)]
    return pd.DataFrame(
        {
            "open": [c - 0.2 for c in close],
            "high": [c + 0.6 for c in close],
            "low": [c - 0.6 for c in close],
            "close": close,
            "volume": 1_000_000.0,
            "atr14": 2.0,
            "signal_color": "green",
            "sma20": [c - 0.5 for c in close],
            "sma60": [c - 1.0 for c in close],
            "sma120": [c - 1.5 for c in close],
            "sma20_slope": 0.1,
        },
        index=index,
    )


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_breakout_then_reject_confirms_short() -> None:
    frame = _frame()
    index = frame.index
    target = 100
    for offset in range(target - 20, target):
        frame.loc[index[offset], "high"] = 140.0
    ref = float(frame["high"].iloc[target - 20: target].max())
    frame.loc[index[target], ["open", "high", "low", "close"]] = [ref, ref + 3, ref, ref + 2]
    reject = target + 1
    frame.loc[index[reject], ["open", "high", "low", "close"]] = [ref - 1, ref - 0.5, ref - 2, ref - 1.5]
    frame.loc[index[reject], "sma20_slope"] = -0.5
    frame.loc[index[reject], "sma20"] = ref - 3.0
    frame.loc[index[reject], "sma60"] = ref - 1.0
    frame.loc[index[reject], "sma120"] = ref
    events = detect_false_breakout_reclaim_short_events(frame, "TEST")
    assert any(_sub(e) == SUB_RULE_SHORT_WATCH for e in events)
    assert any(_sub(e) == SUB_RULE_SHORT_CONFIRMED for e in events)
    confirmed = next(e for e in events if _sub(e) == SUB_RULE_SHORT_CONFIRMED)
    assert confirmed.direction is Direction.BEARISH
    assert confirmed.evidence["direction_side"] == "short"
    assert confirmed.evidence["arrangement_holds"] is True
    assert confirmed.evidence["sma20_slope"] < 0


def test_sma20_slope_non_negative_blocks_short() -> None:
    frame = _frame()
    index = frame.index
    target = 100
    for offset in range(target - 20, target):
        frame.loc[index[offset], "high"] = 140.0
    ref = float(frame["high"].iloc[target - 20: target].max())
    frame.loc[index[target], ["open", "high", "low", "close"]] = [ref, ref + 3, ref, ref + 2]
    reject = target + 1
    frame.loc[index[reject], ["open", "high", "low", "close"]] = [ref - 1, ref - 0.5, ref - 2, ref - 1.5]
    events = detect_false_breakout_reclaim_short_events(frame, "TEST")
    assert not any(_sub(e) == SUB_RULE_SHORT_CONFIRMED for e in events)


def test_short_failed_when_window_expires() -> None:
    frame = _frame()
    index = frame.index
    target = 100
    for offset in range(target - 20, target):
        frame.loc[index[offset], "high"] = 140.0
    ref = float(frame["high"].iloc[target - 20: target].max())
    frame.loc[index[target], ["open", "high", "low", "close"]] = [ref, ref + 3, ref, ref + 2]
    for offset in range(target + 1, target + 5):
        frame.loc[index[offset], "close"] = ref + 2.0
        frame.loc[index[offset], "high"] = ref + 3.0
        frame.loc[index[offset], "low"] = ref + 1.5
    events = detect_false_breakout_reclaim_short_events(frame, "TEST")
    failed = [e for e in events if _sub(e) == SUB_RULE_SHORT_FAILED]
    assert failed, "窗口耗尽应产出 failed 事件"
    assert failed[-1].direction is Direction.NEUTRAL


def test_appending_future_bars_does_not_change_past_short_events() -> None:
    frame = _frame(200)
    index = frame.index
    target = 100
    for offset in range(target - 20, target):
        frame.loc[index[offset], "high"] = 140.0
    ref = float(frame["high"].iloc[target - 20: target].max())
    frame.loc[index[target], ["open", "high", "low", "close"]] = [ref, ref + 3, ref, ref + 2]
    reject = target + 1
    frame.loc[index[reject], ["open", "high", "low", "close"]] = [ref - 1, ref - 0.5, ref - 2, ref - 1.5]
    frame.loc[index[reject], "sma20_slope"] = -0.5
    frame.loc[index[reject], "sma20"] = ref - 3.0
    frame.loc[index[reject], "sma60"] = ref - 1.0
    frame.loc[index[reject], "sma120"] = ref
    cutoff = reject + 2
    early = detect_false_breakout_reclaim_short_events(frame.iloc[:cutoff], "TEST")
    full = detect_false_breakout_reclaim_short_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]


def test_missing_columns_returns_empty() -> None:
    frame = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.bdate_range("2025-01-02", periods=2))
    assert detect_false_breakout_reclaim_short_events(frame, "TEST") == []
