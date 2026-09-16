"""timing_backtest.metrics 绩效指标测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.metrics import compute_performance, summarize_run, yearly_returns


def _eq(vals: list[float] | np.ndarray) -> pd.Series:
    arr = np.asarray(vals, dtype=float)
    return pd.Series(arr, index=pd.bdate_range("2020-01-01", periods=len(arr)))


def test_cagr_compound():
    eq = _eq(1.01 ** np.arange(252))  # 日复利 1%，252 日
    perf = compute_performance(eq)
    assert perf["cagr"] == pytest.approx(1.01**252 - 1, rel=1e-9)
    assert perf["mdd"] == pytest.approx(0.0, abs=1e-12)
    assert perf["vol"] == pytest.approx(0.0, abs=1e-12)
    assert perf["sharpe"] == 0.0  # 零波动防除零


def test_mdd_hand_computed():
    eq = _eq([1.0, 1.2, 1.5, 1.0, 0.9, 1.3])
    perf = compute_performance(eq)
    assert perf["mdd"] == pytest.approx(0.9 / 1.5 - 1.0)  # 峰 1.5 → 谷 0.9
    assert perf["calmar"] == pytest.approx(perf["cagr"] / abs(perf["mdd"]))


def test_yearly_returns_groups_by_calendar_year():
    idx = pd.to_datetime(["2022-06-30", "2022-12-30", "2023-06-30", "2023-12-29"])
    eq = pd.Series([1.0, 1.1, 1.21, 1.331], index=idx)
    yr = yearly_returns(eq)
    assert yr.loc[2022] == pytest.approx(0.10)
    assert yr.loc[2023] == pytest.approx(1.331 / 1.1 - 1)


def test_summarize_run_fields():
    idx = pd.bdate_range("2023-01-02", periods=504)
    rng = np.random.default_rng(3)
    close = pd.Series(100 * np.exp(rng.normal(0.0003, 0.01, 504).cumsum()), index=idx)
    daily = pd.DataFrame(
        {
            "open": close, "close": close, "b20": 50.0, "b50": 50.0, "b200": 50.0,
            "equity": np.exp(rng.normal(0.0004, 0.008, 504).cumsum()),
            "benchmark": np.exp(rng.normal(0.0002, 0.009, 504).cumsum()),
            "weight": np.where(np.arange(504) % 2 == 0, 1.0, 0.5),
        },
        index=idx,
    )
    trades = [{"turnover": 0.5}, {"turnover": 0.25}]
    s = summarize_run(daily, trades)
    for key in (
        "strategy_cagr", "benchmark_cagr", "excess_cagr", "strategy_mdd",
        "benchmark_mdd", "calmar", "sharpe", "vol", "avg_weight", "n_trades",
        "total_turnover", "years",
    ):
        assert key in s
    assert s["avg_weight"] == pytest.approx(0.75)
    assert s["n_trades"] == 2
    assert s["total_turnover"] == pytest.approx(0.75)
    assert s["excess_cagr"] == pytest.approx(s["strategy_cagr"] - s["benchmark_cagr"])
