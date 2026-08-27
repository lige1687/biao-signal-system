"""timing_backtest.strategies 目标仓位纯函数测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.strategies import (
    LadderParams,
    ReversalParams,
    TrendGate,
    apply_gate,
    build_target,
    ladder_target,
    reversal_target,
    trend_gate_cap,
)


def _s(vals: list[float] | np.ndarray) -> pd.Series:
    arr = np.asarray(vals, dtype=float)
    return pd.Series(arr, index=pd.bdate_range("2024-01-01", periods=len(arr)))


def test_ladder_fixed_5bands():
    t = ladder_target(_s([10, 25, 45, 65, 90]), LadderParams(n_bands=5))
    assert list(t) == [1.0, 0.75, 0.5, 0.25, 0.0]


def test_ladder_3bands_edges():
    t = ladder_target(_s([10, 40, 80]), LadderParams(n_bands=3))
    # 3 档边界 33.3/66.7 → 仓位 1.0/0.5/0.0
    assert list(np.round(t, 6)) == [1.0, 0.5, 0.0]


def test_ladder_momentum_flips():
    t = ladder_target(_s([10, 90]), LadderParams(n_bands=5, direction="momentum"))
    assert list(t) == [0.0, 1.0]


def test_ladder_preq_uses_warmup_quantiles():
    warmup = _s(np.arange(0, 100, 0.4))  # 均匀 250 个观测
    t = ladder_target(_s([1, 99]), LadderParams(n_bands=3, edge_mode="preq"), warmup_b=warmup)
    # preq 边界 = warmup 的 1/3、2/3 分位 ≈ 33.3/66.6 → 与 fixed 一致
    assert list(np.round(t, 4)) == [1.0, 0.0]


def test_ladder_preq_insufficient_warmup_falls_back_fixed():
    t = ladder_target(_s([1, 99]), LadderParams(n_bands=3, edge_mode="preq"), warmup_b=_s([5.0] * 10))
    assert list(np.round(t, 4)) == [1.0, 0.0]


def test_reversal_time_batches():
    b = _s([5, 5, 25, 30, 40, 50, 60, 90, 70, 50, 40, 30, 20])
    t = reversal_target(b, ReversalParams(batch_mode="time", batches=4))
    assert t.iloc[0] == 0.0
    assert t.iloc[1] == 0.0            # 尚未触发
    assert t.iloc[2] == pytest.approx(0.25)   # 25 >= 20+5 触发，当日即第一批
    assert t.iloc[3] == pytest.approx(0.5)
    assert t.iloc[6] == 1.0            # 4 批爬满
    assert t.iloc[7] == 1.0            # 90 >= 80 armed，未跌破确认线不动
    # idx8: 70 <= 80-5 触发卖出程序，当日卖第一批
    assert t.iloc[8] == pytest.approx(0.75)
    assert t.iloc[-1] == 0.0


def test_reversal_band_batches():
    b = _s([5, 5, 25, 36, 47, 58])
    t = reversal_target(b, ReversalParams(batch_mode="band", batches=5))
    assert t.iloc[2] == pytest.approx(0.2)   # 触发日第一批
    assert t.iloc[3] == pytest.approx(0.4)   # +11 → 第二批
    assert t.iloc[4] == pytest.approx(0.6)
    assert t.iloc[5] == pytest.approx(0.8)


def test_gate_ma200_and_apply():
    close = _s([100, 100, 90, 80, 200])
    cap = trend_gate_cap(close, TrendGate(mode="ma200", cap=0.0))
    # 只有 5 根，MA200 未成型 → 不设限
    assert list(cap) == [1.0] * 5
    long_close = _s(np.concatenate([np.full(199, 100.0), [80.0, 100.0]]))
    cap2 = trend_gate_cap(long_close, TrendGate(mode="ma200", cap=0.0))
    assert cap2.iloc[199] == 0.0   # close 80 < MA200=100
    assert cap2.iloc[200] == 1.0   # 回到均线上方
    assert list(apply_gate(_s([0.8, 0.5, 0.9]), _s([1.0, 0.3, 0.0]))) == [0.8, 0.3, 0.0]


def test_build_target_combines_gate():
    idx = pd.bdate_range("2023-01-01", periods=300)
    rng = np.random.default_rng(7)
    close = pd.Series(100 + rng.normal(0, 1, 300).cumsum(), index=idx)
    b = pd.Series(np.clip(50 + rng.normal(0, 10, 300).cumsum(), 0, 100), index=idx)
    aligned = pd.DataFrame({"open": close, "close": close, "b20": b, "b50": b, "b200": b})
    t = build_target(aligned, LadderParams(), None, TrendGate(mode="ma200", cap=0.0), None)
    ma = close.rolling(200, min_periods=200).mean()
    capped = t[(close < ma) & ma.notna()]
    assert (capped <= 1e-12).all()
    assert (t >= 0).all() and (t <= 1).all()


def test_ladder_min_weight_floor():
    t = ladder_target(_s([10, 25, 45, 65, 90]), LadderParams(n_bands=5, min_weight=0.5))
    # 档位 [1,0.75,0.5,0.25,0] 压缩到 [1,0.875,0.75,0.625,0.5]
    assert list(np.round(t.to_numpy(), 4)) == [1.0, 0.875, 0.75, 0.625, 0.5]
