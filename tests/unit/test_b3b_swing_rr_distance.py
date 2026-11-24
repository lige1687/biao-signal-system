"""B3-b 单测：mixed.swing_rr_distance 最小实现（factor_lab/b3b_swing_rr_distance）。

覆盖：手算常数比对（同 docs/experiments/raw/factor-b3b-2026-09-20/
swing-rr-distance/hand-expectations.json，实现对照前固定）、零后视回填、
NaN 三分支、与系统既有 confirmed_pivots 口径的集成。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.types import Pivot
from lei_signal.research.factor_lab.b3b_swing_rr_distance import (
    swing_rr_distance,
    swing_rr_frame,
    swing_rr_from_bars,
)


def _bars(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame(
        {
            "date": [date(2026, 2, i + 1) for i in range(n)],
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
        }
    )


PIVOTS = (
    Pivot("low", 3, date(2026, 2, 4), 95.0, 6, date(2026, 2, 7)),
    Pivot("low", 8, date(2026, 2, 9), 97.0, 11, date(2026, 2, 12)),
    Pivot("high", 10, date(2026, 2, 11), 110.0, 13, date(2026, 2, 14)),
)


def test_hand_values_latest_pivot_replaces():
    closes = [99, 98, 97, 95, 96, 97, 98, 99, 97, 101, 110, 109, 101, 108, 100, 102.5]
    closes += [103, 104, 105, 106]
    frame = swing_rr_frame(_bars(closes), PIVOTS)
    assert frame.iloc[12]["value"] != frame.iloc[12]["value"]  # 高点未确认
    assert frame.iloc[12]["missing_reason"] == "structure_not_confirmed"
    assert abs(frame.iloc[13]["value"] - 2 / 11) <= 1e-6  # L_conf 已被 97 取代
    assert abs(frame.iloc[14]["value"] - 10 / 3) <= 1e-6
    assert abs(frame.iloc[15]["value"] - 7.5 / 5.5) <= 1e-6


def test_zero_hindsight_no_backfill_on_pivot_day():
    pivots = (
        Pivot("low", 2, date(2026, 2, 3), 96.0, 5, date(2026, 2, 6)),
        Pivot("high", 10, date(2026, 2, 11), 110.0, 13, date(2026, 2, 14)),
    )
    closes = [97, 96, 96, 97, 98, 99, 100, 100, 100, 100, 100, 100, 100, 100, 98]
    closes += [98, 99, 100, 101, 102]
    values = swing_rr_distance(_bars(closes), pivots)
    for t in (9, 10, 11, 12):  # 含拐点当日 t=10：确认日前一律不可见
        assert values.iloc[t] != values.iloc[t], t
    assert abs(values.iloc[13] - 10 / 4) <= 1e-6  # 确认日当日可见
    assert abs(values.iloc[14] - 12 / 2) <= 1e-6


def test_invalid_range_and_no_structure_branches():
    closes = [99, 98, 97, 95, 96, 97, 98, 99, 97, 100, 110, 109, 101, 108, 104, 94, 95]
    frame = swing_rr_frame(_bars(closes), PIVOTS)
    assert frame.iloc[15]["missing_reason"] == "invalid_range"  # close 94 < L_conf 97
    assert frame.iloc[16]["missing_reason"] == "invalid_range"  # 分母为负
    empty = swing_rr_frame(_bars([100.0] * 20), ())
    assert empty["value"].isna().all()
    assert (empty["missing_reason"] == "structure_not_confirmed").all()


def test_close_above_high_is_invalid_range():
    pivots = (
        Pivot("low", 2, date(2026, 2, 3), 96.0, 5, date(2026, 2, 6)),
        Pivot("high", 10, date(2026, 2, 11), 110.0, 13, date(2026, 2, 14)),
    )
    closes = [100.0] * 20
    closes[15] = 111.0  # 越过已确认高点：目标不可计算
    frame = swing_rr_frame(_bars(closes), pivots)
    assert frame.iloc[15]["missing_reason"] == "invalid_range"


def test_integration_with_confirmed_pivots():
    # 用系统既有 swing 口径（三左三右）真实识别，再逐日算距离比：
    # 摆动点确认前 NaN、确认后进入计算
    highs = [10, 11, 12, 11, 10, 9, 8, 8, 8, 9, 10, 11, 12, 12, 12] + [11, 10, 9, 8, 8]
    lows = [h - 2 for h in highs]
    closes = [h - 1 for h in highs]
    bars = _bars(closes)
    bars["high"] = highs
    bars["low"] = lows
    frame = swing_rr_from_bars(bars)
    assert frame["value"].isna().any()  # 前段无已确认结构
    valid = frame["value"].dropna()
    assert (valid > 0).all()
