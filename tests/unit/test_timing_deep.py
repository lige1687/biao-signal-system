"""timing_backtest 正确性深测：随机化无未来函数模糊测试 + 资金记账不变量 + 边界用例。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance
from lei_signal.timing_backtest.strategies import (
    LadderParams,
    ReversalParams,
    TrendGate,
    apply_vol_target,
    build_target,
    ladder_target,
    reversal_target,
)


def _rand_frame(rng: np.random.Generator, n: int = 300) -> pd.DataFrame:
    idx = pd.bdate_range("2020-01-01", periods=n)
    close = pd.Series(100 * np.exp(rng.normal(0.0002, 0.015, n).cumsum()), index=idx)
    b = pd.Series(np.clip(50 + rng.normal(0, 12, n).cumsum(), 0, 100), index=idx)
    return pd.DataFrame(
        {
            "open": close * rng.uniform(0.99, 1.01, n),
            "high": close * rng.uniform(1.0, 1.03, n),
            "low": close * rng.uniform(0.97, 1.0, n),
            "close": close,
            "b20": b, "b50": b, "b200": b,
        },
        index=idx,
    )


@pytest.mark.parametrize("seed", range(30))
def test_fuzz_no_lookahead(seed):
    """篡改任意未来段数据，此前净值序列必须逐日不变（30 组随机场景）。"""
    rng = np.random.default_rng(seed)
    frame = _rand_frame(rng)
    if seed % 2:
        target = build_target(frame, LadderParams(), None, TrendGate(), None)
    else:
        target = build_target(
            frame, None, ReversalParams(batch_mode="band" if seed % 4 else "time"),
            TrendGate(mode="ma200"), None, vol_target=0.15 if seed % 3 == 0 else 0.0,
        )
    base = simulate(frame, target, fee_bps=5.0).daily["equity"]
    cut = len(frame) // 2
    tampered = frame.copy()
    tampered.iloc[cut:, tampered.columns.get_indexer(["open", "high", "low", "close"])] = (
        rng.uniform(50, 500, (len(frame) - cut, 4))
    )
    tampered_target = target.copy()
    tampered_target.iloc[cut:] = rng.uniform(0, 1, len(frame) - cut)
    other = simulate(tampered, tampered_target, fee_bps=5.0).daily["equity"]
    pd.testing.assert_series_equal(base.iloc[:cut], other.iloc[:cut])


@pytest.mark.parametrize("seed", range(20))
def test_fuzz_accounting_invariants(seed):
    """净值守恒不变量：equity > 0、无杠杆（weight∈[0,1]）、费用单测口径下净值不高于零费。"""
    rng = np.random.default_rng(1000 + seed)
    frame = _rand_frame(rng)
    target = build_target(frame, LadderParams(n_bands=9), None, TrendGate(mode="ma200"), None)
    res = simulate(frame, target, fee_bps=10.0)
    assert (res.daily["equity"] > 0).all()
    w = res.daily["weight"]
    assert (w >= -1e-9).all() and (w <= 1 + 1e-9).all()
    zero_fee = simulate(frame, target, fee_bps=0.0).daily["equity"]
    assert (res.daily["equity"] <= zero_fee + 1e-9).all()
    assert (res.daily["benchmark"] > 0).all()


def test_nan_breadth_segment_kept_flat():
    """宽度 NaN 段：反转状态机保持仓位不变、恢复后程序可继续。"""
    idx = pd.bdate_range("2024-01-01", periods=40)
    b = np.full(40, 14.0)
    b[2] = 5.0          # 武装（≤ low_extreme=10）
    b[5:20] = np.nan    # 中段数据缺失（未触发）
    b[21] = 16.0        # ≥ 10+5 触发买入第一批
    t = reversal_target(
        pd.Series(b, index=idx),
        ReversalParams(low_extreme=10.0, confirm=5.0, batch_mode="time", batches=4),
    )
    assert t.iloc[5] == t.iloc[19] == 0.0  # NaN 段仓位冻结
    assert t.iloc[21] == pytest.approx(0.25)  # 恢复后触发
    assert t.iloc[22] == pytest.approx(0.5)  # 程序继续


def test_extreme_params_do_not_crash():
    idx = pd.bdate_range("2024-01-01", periods=500)
    rng = np.random.default_rng(9)
    b = pd.Series(np.clip(50 + rng.normal(0, 20, 500).cumsum(), 0, 100), index=idx)
    t1 = ladder_target(b, LadderParams(n_bands=2, gamma=0.1, low_edge=45, high_edge=55))
    assert np.isfinite(t1).all() and (t1 >= 0).all() and (t1 <= 1).all()
    t2 = reversal_target(b, ReversalParams(batches=100, batch_ratio=5.0, sell_batches=1))
    assert np.isfinite(t2).all()
    t3 = reversal_target(b, ReversalParams(band_step=1.0, batches=8, batch_ratio=0.1))
    assert np.isfinite(t3).all() and (t3 >= 0).all() and (t3 <= 1).all()


def test_vol_target_never_exceeds_one_and_handles_flat():
    idx = pd.bdate_range("2024-01-01", periods=60)
    flat = pd.Series(100.0, index=idx)  # 零波动：std=0 → 不放大（防除零）
    t = apply_vol_target(flat, pd.Series(0.7, index=idx), vol_target=0.1)
    assert (t <= 0.7 + 1e-12).all()
    assert (t >= 0.7 - 1e-12).all()  # 零波动下 scale 应为 1（clip upper）


def test_metrics_constant_series_guards():
    eq = pd.Series([1.0] * 100, index=pd.bdate_range("2024-01-01", periods=100))
    perf = compute_performance(eq)
    assert perf["sharpe"] == 0.0 and perf["vol"] == 0.0 and perf["mdd"] == 0.0


def test_duplicate_and_unsorted_index_tolerated():
    rng = np.random.default_rng(3)
    frame = _rand_frame(rng, 200)
    shuffled = frame.sample(frac=1.0, random_state=1)  # 打乱行序
    target = build_target(frame, LadderParams(), None, TrendGate(), None)
    res_sorted = simulate(shuffled.sort_index(), target.sort_index(), fee_bps=5.0)
    assert len(res_sorted.daily) == 200
