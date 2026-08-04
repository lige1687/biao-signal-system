"""完整均线排列 + EMA 斜率加速度门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.rules.ma_full_alignment import (
    SUB_RULE_BEARISH_START,
    SUB_RULE_BROKEN,
    SUB_RULE_BULLISH_START,
    detect_ma_alignment_events,
    ema_slope_accel_for_frame,
)


def _aligned_frame(rows: int = 80, bearish: bool = False) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=rows)
    positions = pd.Series(range(rows), index=index, dtype=float)
    if not bearish:
        sma120 = 80.0 + positions * 0.03
        sma60 = 90.0 + positions * 0.06
        sma20 = 100.0 + positions * 0.12
        ema20 = sma20 + 1.0
    else:
        sma20 = 100.0 - positions * 0.12
        sma60 = 110.0 - positions * 0.06
        sma120 = 120.0 - positions * 0.03
        ema20 = sma20 - 1.0
    frame = pd.DataFrame(
        {
            "open": ema20 - 0.2,
            "high": ema20 + 0.5,
            "low": ema20 - 0.5,
            "close": ema20,
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
    return frame


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_bullish_alignment_start_then_broken() -> None:
    frame = _aligned_frame()
    index = frame.index
    # 第 50 根破坏排列：让 SMA20 低于 SMA60。
    frame.loc[index[50], "sma20"] = float(frame.loc[index[50], "sma60"]) - 0.1
    frame.loc[index[50], "sma20_slope"] = -0.1
    events = detect_ma_alignment_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_BULLISH_START in subs
    assert SUB_RULE_BROKEN in subs
    # 成立事件早于破坏事件。
    assert subs.index(SUB_RULE_BULLISH_START) < subs.index(SUB_RULE_BROKEN)


def test_bearish_alignment_start() -> None:
    frame = _aligned_frame(bearish=True)
    events = detect_ma_alignment_events(frame, "TEST")
    assert [_sub(e) for e in events] == [SUB_RULE_BEARISH_START]


def test_ema_slope_accel_available() -> None:
    frame = _aligned_frame()
    result = ema_slope_accel_for_frame(frame)
    assert result is not None
    assert "ema20_slope_pct" in result
    assert "ema20_accel_pct" in result
    assert result["ema20_slope_pct"] > 0


def test_appending_future_bars_does_not_change_past_events() -> None:
    frame = _aligned_frame(100)
    index = frame.index
    frame.loc[index[50], "sma20"] = float(frame.loc[index[50], "sma60"]) - 0.1
    frame.loc[index[50], "sma20_slope"] = -0.1
    cutoff = 70
    early = detect_ma_alignment_events(frame.iloc[:cutoff], "TEST")
    full = detect_ma_alignment_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]
