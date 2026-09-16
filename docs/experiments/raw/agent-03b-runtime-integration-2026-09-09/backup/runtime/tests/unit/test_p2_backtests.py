"""P2 三项研究代理回测口径门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.research.alignment_backtest import build_alignment_backtest
from lei_signal.research.false_breakout_backtest import build_false_breakout_backtest
from lei_signal.research.low_level_backtest import build_low_level_backtest
from lei_signal.rules.false_breakout_reclaim import detect_false_breakout_reclaim_events
from lei_signal.rules.low_level_confirmation import detect_low_level_confirmation_events
from lei_signal.rules.ma_full_alignment import detect_ma_alignment_events


def _base_frame(rows: int = 120, bearish: bool = False) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=rows)
    positions = pd.Series(range(rows), index=index, dtype=float)
    if not bearish:
        sma120 = 80.0 + positions * 0.03
        sma60 = 90.0 + positions * 0.06
        sma20 = 100.0 + positions * 0.12
        ema20 = sma20 + 1.0
        signal = "green"
    else:
        sma20 = 80.0 + positions * 0.03
        sma60 = 90.0 + positions * 0.06
        sma120 = 100.0 + positions * 0.12
        ema20 = sma20 - 1.0
        signal = "black"
    close = ema20
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000_000.0,
            "atr14": 2.0,
            "signal_color": signal,
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


def test_false_breakout_backtest_has_horizons_and_rule_exit() -> None:
    frame = _base_frame()
    index = frame.index
    target = 45
    ref = float(frame["high"].rolling(window=20).max().shift(1).iloc[target])
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
    events = detect_false_breakout_reclaim_events(frame, "TEST")
    report = build_false_breakout_backtest(frame, events)
    assert report is not None
    assert len(report.sides) == 1
    side = report.sides[0]
    assert side.total_signals >= 1
    labels = {stat.label_cn for stat in side.stats}
    assert "5日" in labels and "120日" in labels and "规则退出" in labels


def test_alignment_backtest_groups_by_direction() -> None:
    frame = _base_frame()
    index = frame.index
    frame.loc[index[80], "sma20"] = float(frame.loc[index[80], "sma60"]) - 0.1
    frame.loc[index[80], "sma20_slope"] = -0.1
    events = detect_ma_alignment_events(frame, "TEST")
    report = build_alignment_backtest(frame, events)
    assert report is not None
    keys = {side.key for side in report.sides}
    assert "bullish" in keys
    assert report.sides[0].total_signals >= 1


def test_low_level_backtest_runs() -> None:
    frame = _base_frame()
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
    events = detect_low_level_confirmation_events(frame, "TEST")
    report = build_low_level_backtest(frame, events)
    assert report is not None
    assert report.sides[0].total_signals >= 1
    labels = {stat.label_cn for stat in report.sides[0].stats}
    assert "规则退出" in labels
