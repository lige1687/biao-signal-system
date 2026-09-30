"""B3-b 单测：trend.ma_cluster_width 最小实现（factor_lab/b3b_ma_cluster_width）。

期望值为闭式推导常数（同 docs/experiments/raw/factor-b3b-2026-09-20/
ma-cluster-width/hand-expectations.json，实现对照前固定）。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.research.factor_lab.b3b_ma_cluster_width import (
    ma_cluster_width,
    six_moving_averages,
)

G = 1.01


def _uptrend(n: int = 130, c0: float = 100.0) -> pd.Series:
    return pd.Series([c0 * G**i for i in range(n)])


def test_locked_ma_set_ordering_uptrend():
    mas = six_moving_averages(_uptrend())
    row = mas.iloc[129]
    assert list(row.index) == ["ema20", "sma20", "ema60", "sma60", "ema120", "sma120"]
    # 上行趋势排序：SMA120 ≤ EMA120 ≤ SMA60 ≤ EMA60 ≤ SMA20 ≤ EMA20
    assert row["sma120"] <= row["ema120"] <= row["sma60"] <= row["ema60"] <= row["sma20"] <= row["ema20"]


def test_width_matches_closed_form():
    width = ma_cluster_width(_uptrend())
    for t, expected in [(119, 0.55805547), (120, 0.55805548), (125, 0.55805551), (129, 0.55805552)]:
        assert abs(width.iloc[t] - expected) <= 2e-6, t


def test_constant_series_zero_width():
    width = ma_cluster_width(pd.Series([100.0] * 130))
    assert width.iloc[:119].isna().all()
    assert abs(width.iloc[119]) <= 2e-6
    assert abs(width.iloc[129]) <= 2e-6


def test_warmup_all_nan_no_partial_compute():
    # 50 根：SMA/EMA20 已成形但 60/120 未成形——任一均线缺即 NaN，
    # 不允许拿已成形均线部分计算（回归：pandas max/min 默认 skipna 曾致误出值）
    width = ma_cluster_width(_uptrend(50))
    assert width.isna().all()


def test_midseries_gap_pollutes_width():
    closes = [100.0 * G**i for i in range(130)]
    closes[125] = float("nan")
    width = ma_cluster_width(pd.Series(closes))
    assert width.iloc[124] == width.iloc[124]  # 缺口前仍有值
    assert width.iloc[125:].isna().all()  # 缺失日起持续 NaN（EMA 递推污染）


def test_ema_matches_system_seeded_ema():
    from lei_signal.features.indicators import seeded_ema

    s = _uptrend()
    for window in (20, 60, 120):
        pd.testing.assert_series_equal(
            six_moving_averages(s)[f"ema{window}"], seeded_ema(s, window)
        )
