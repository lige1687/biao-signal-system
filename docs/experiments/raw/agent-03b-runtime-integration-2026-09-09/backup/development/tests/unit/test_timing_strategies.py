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


def test_batch_weights_pyramid_and_reverse():
    from lei_signal.timing_backtest.strategies import _batch_weights
    w = _batch_weights(3, 2.0)   # 金字塔：首批重
    assert list(np.round(w, 4)) == [0.5714, 0.2857, 0.1429]
    assert w.sum() == pytest.approx(1.0)
    w2 = _batch_weights(3, 0.5)  # 递增：越跌买越多
    assert w2[0] < w2[1] < w2[2] and w2.sum() == pytest.approx(1.0)


def test_reversal_pyramid_ratio_time():
    b = _s([5, 5, 25, 30, 40])
    t = reversal_target(b, ReversalParams(batch_mode="time", batches=3, batch_ratio=2.0))
    # w=[4/7,2/7,1/7]：触发日 0.571 → 0.857 → 1.0
    assert t.iloc[2] == pytest.approx(4 / 7)
    assert t.iloc[3] == pytest.approx(6 / 7)
    assert t.iloc[4] == 1.0


def test_reversal_sell_batches_independent():
    b = _s([5, 5, 25, 35, 45, 90, 70, 60])
    t = reversal_target(
        b, ReversalParams(batch_mode="time", batches=3, batch_ratio=1.0, sell_batches=1)
    )
    assert t.iloc[4] == 1.0            # 3 批买满
    assert t.iloc[5] == 1.0            # armed_high，未确认不动
    assert t.iloc[6] == 0.0            # 卖出 1 批 → 直接清仓
    assert t.iloc[7] == 0.0


def test_reversal_band_step():
    b = _s([5, 5, 25, 31, 37, 43])
    t = reversal_target(b, ReversalParams(batch_mode="band", batches=2, band_step=5.0))
    assert t.iloc[2] == pytest.approx(0.5)  # 触发日第一批
    assert t.iloc[3] == pytest.approx(1.0)  # +6 ≥ 5 → 第二批
    assert t.iloc[4] == 1.0 and t.iloc[5] == 1.0


def test_ladder_edge_shrink_and_gamma():
    t = ladder_target(
        _s([10, 35, 50, 65, 90, 86]),
        LadderParams(n_bands=5, low_edge=15.0, high_edge=85.0),
    )
    # 边界 29/43/57/71：B=10→1.0, 35→0.75, 50→0.5, 65→0.25, 90→0.0
    assert list(np.round(t.to_numpy(), 4)) == [1.0, 0.75, 0.5, 0.25, 0.0, 0.0]
    t2 = ladder_target(_s([10, 25, 45, 65, 90]), LadderParams(n_bands=5, gamma=2.0))
    # contrarian 档位 [1,.75,.5,.25,0] 经 gamma=2 → [1,.5625,.25,.0625,0]
    assert list(np.round(t2.to_numpy(), 4)) == [1.0, 0.5625, 0.25, 0.0625, 0.0]


def test_vol_target_scales_down_high_vol_only():
    idx = pd.bdate_range("2024-01-01", periods=60)
    rng = np.random.default_rng(5)
    calm = pd.Series(100 * np.exp(rng.normal(0, 0.002, 60).cumsum()), index=idx)
    wild = pd.Series(100 * np.exp(rng.normal(0, 0.03, 60).cumsum()), index=idx)
    target = pd.Series(1.0, index=idx)
    from lei_signal.timing_backtest.strategies import apply_vol_target
    t_calm = apply_vol_target(calm, target, vol_target=0.15)
    t_wild = apply_vol_target(wild, target, vol_target=0.15)
    assert t_calm.iloc[-1] == pytest.approx(1.0)          # 低波动不缩
    assert 0.0 < t_wild.iloc[-1] < 1.0                    # 高波动缩仓
    assert t_calm.iloc[10] == pytest.approx(1.0)          # 窗口未成型不缩


def test_trigger_immediate_buys_on_entry_and_deeper():
    # B: 30 → 18（进底区当天即买第一批）→ 12（再跌 band_step=6 → 第二批）
    b = _s([30, 18, 12, 40])
    t = reversal_target(
        b, ReversalParams(low_extreme=20, high_extreme=80, confirm=5.0,
                          batch_mode="band", batches=2, band_step=6.0,
                          trigger_mode="immediate"))
    assert t.iloc[0] == 0.0
    assert t.iloc[1] == pytest.approx(0.5)   # 进区即第一批
    assert t.iloc[2] == pytest.approx(1.0)   # 再跌 6 点 → 第二批
    assert t.iloc[3] == 1.0


def test_trigger_immediate_sell_on_rise():
    b = _s([60, 82, 88, 50])
    t = reversal_target(
        b, ReversalParams(low_extreme=20, high_extreme=80, confirm=5.0,
                          batch_mode="band", batches=2, band_step=5.0,
                          trigger_mode="immediate", sell_batches=1))
    assert t.iloc[0] == 0.0 and t.iloc[1] == 0.0  # 无持仓时顶部不产生卖出
    # 先构造持仓：手动跑一段买入
    b2 = _s([30, 18, 12, 82, 87, 50])
    t2 = reversal_target(
        b2, ReversalParams(low_extreme=20, high_extreme=80, confirm=5.0,
                           batch_mode="band", batches=2, band_step=6.0,
                           trigger_mode="immediate", sell_batches=1))
    assert t2.iloc[2] == 1.0        # 买满
    assert t2.iloc[3] == 0.0        # 进顶区当天即触发、sell_batches=1 当日清仓
    assert t2.iloc[4] == 0.0


def test_trigger_extreme_confirm_earlier_than_rebound():
    # 反弹模式：砸到 5 也要回升到 25 才买；extreme_confirm：从 5 回升 5 点（10）即买
    b = _s([30, 5, 11, 15])
    t_rb = reversal_target(
        b, ReversalParams(low_extreme=20, high_extreme=80, confirm=5.0,
                          batch_mode="time", batches=2, trigger_mode="rebound"))
    t_ec = reversal_target(
        b, ReversalParams(low_extreme=20, high_extreme=80, confirm=5.0,
                          batch_mode="time", batches=2, trigger_mode="extreme_confirm"))
    assert t_rb.iloc[2] == 0.0      # 11 < 25 未触发
    assert t_ec.iloc[2] == pytest.approx(0.5)  # 11 ≥ 5+5 触发第一批
    assert t_rb.iloc[3] == 0.0


def test_trigger_linger_waits_days_in_zone():
    # 在底区连续停留 confirm=3 日后才触发
    b = _s([30, 15, 15, 15, 15])
    t = reversal_target(
        b, ReversalParams(low_extreme=20, high_extreme=80, confirm=3.0,
                          batch_mode="time", batches=2, trigger_mode="linger"))
    assert t.iloc[1] == 0.0 and t.iloc[2] == 0.0  # 停留 1、2 日
    assert t.iloc[3] == pytest.approx(0.5)        # 第 3 日触发
    assert t.iloc[4] == pytest.approx(1.0)
