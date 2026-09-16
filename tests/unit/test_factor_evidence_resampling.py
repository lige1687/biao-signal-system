"""factor_evidence resampling 测试：纯索引 + 成对循环区块重抽。

固定教学例来自任务书 §2.2 与 Task 3；n=4/L=2 全 16 种有序起点对逐值
独立核对；分位数手算常数 linear 2.5%=0.075、97.5%=2.925。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_evidence.resampling import (
    circular_indices,
    linear_quantiles,
    paired_block_deltas,
)

COLS = ["symbol", "session", "state", "main", "aux", "legal",
        "legal_reason", "e_date", "x_date"]


def _frame(states, mains, legal=None):
    n = len(states)
    return pd.DataFrame({
        "symbol": ["510300"] * n,
        "session": [f"2019-10-{8 + i:02d}" if 8 + i <= 31 else
                    f"2019-11-{8 + i - 31:02d}" for i in range(n)],
        "state": list(states),
        "main": list(mains),
        "aux": [0.0] * n,
        "legal": [True] * n if legal is None else list(legal),
        "legal_reason": [None] * n,
        "e_date": [None] * n,
        "x_date": [None] * n,
    }, columns=COLS)


# ── 纯索引函数 ──────────────────────────────────────────────────────

def test_circular_indices_exact_wrap_and_truncation():
    got = circular_indices(5, 3, [4, 1])
    assert got.tolist() == [4, 0, 1, 1, 2]


def test_circular_indices_rejects_bad_params():
    for n, L, starts in ((0, 3, [0]), (5, 0, [0]), (-1, 3, [0]),
                         (5.0, 3, [0]), (5, 3.0, [0]), (True, 3, [0]),
                         (5, True, [0])):
        with pytest.raises(ValueError, match="必须为正|正整数|拒绝"):
            circular_indices(n, L, starts)
    with pytest.raises(ValueError, match="starts|范围"):
        circular_indices(5, 3, [0, 5])
    with pytest.raises(ValueError, match="starts|整数"):
        circular_indices(5, 3, [0.5, 1])


def test_circular_indices_coverage_requirement():
    # 起点数×块长不足以覆盖 n 行时拒绝（截断只发生在尾部）
    with pytest.raises(ValueError, match="覆盖|不足"):
        circular_indices(10, 3, [0, 1])  # 2*3=6 < 10


# ── 成对重抽：固定教学例 ────────────────────────────────────────────

def test_paired_example_delta_point_two():
    frame = _frame([True, False, True, False, True],
                   [0.1, 0.0, 0.2, -0.1, 0.3])
    out = paired_block_deltas(frame, block_length=3, reps=1, seed=7,
                              starts=np.array([[4, 1]]),
                              min_valid_reps=1)
    rep = out["replicates"][0]
    assert rep["delta"] == pytest.approx(0.2, abs=1e-12)
    assert rep["true_n"] == 3 and rep["false_n"] == 2
    # 同一索引同时用于 state/main：true 值 [.3,.1,.2]、false 值 [0,0]
    assert out["starts"].tolist() == [[4, 1]]


def test_paired_exhaustive_n4_l2_all_16_start_pairs():
    states = [True, False, True, False]
    mains = [0.4, -0.2, 0.6, 0.8]
    frame = _frame(states, mains)
    n, L = 4, 2
    starts = np.array([[a, b] for a in range(4) for b in range(4)])
    out = paired_block_deltas(frame, block_length=L, reps=16, seed=1,
                              starts=starts, min_valid_reps=1)
    null_count = 0
    for rep, row in zip(out["replicates"], starts, strict=True):
        idx = ((row[:, None] + np.arange(L)[None, :]) % n).reshape(-1)[:n]
        # 独立重算：同一索引、合法过滤、两组 n 与 delta
        t_vals = [mains[i] for i in idx if states[i] is True]
        f_vals = [mains[i] for i in idx if states[i] is False]
        if not t_vals or not f_vals:
            assert rep["delta"] is None and rep["reason"]
            null_count += 1
        else:
            assert rep["true_n"] == len(t_vals)
            assert rep["false_n"] == len(f_vals)
            assert rep["delta"] == pytest.approx(
                sum(t_vals) / len(t_vals) - sum(f_vals) / len(f_vals),
                abs=1e-12)
    assert out["null_reps"] == null_count
    assert out["valid_reps"] == 16 - null_count


def test_quantile_linear_hand_constants():
    lo, hi = linear_quantiles([0.0, 1.0, 2.0, 3.0], 0.025, 0.975)
    assert lo == pytest.approx(0.075, abs=1e-15)
    assert hi == pytest.approx(2.925, abs=1e-15)
    # 与 numpy linear 方法一致
    vals = [0.3, -1.2, 0.05, 2.0, 0.7, -0.4, 1.1]
    lo, hi = linear_quantiles(vals, 0.025, 0.975)
    assert lo == pytest.approx(np.quantile(vals, 0.025, method="linear"),
                               abs=0)
    assert hi == pytest.approx(np.quantile(vals, 0.975, method="linear"),
                               abs=0)


# ── 行为约定 ────────────────────────────────────────────────────────

def test_same_seed_reproduces_and_target_change_keeps_starts():
    f1 = _frame([True, False] * 5, [0.1, -0.1] * 5)
    f2 = _frame([True, False] * 5, [0.5, 0.2] * 5)
    a = paired_block_deltas(f1, 4, 8, seed=20260916, min_valid_reps=1)
    b = paired_block_deltas(f1, 4, 8, seed=20260916, min_valid_reps=1)
    c = paired_block_deltas(f2, 4, 8, seed=20260916, min_valid_reps=1)
    assert np.array_equal(a["starts"], b["starts"])
    assert a["replicates"] == b["replicates"]
    assert np.array_equal(a["starts"], c["starts"])  # 换目标不改起点
    assert a["replicates"] != c["replicates"]
    assert a["seed"] == 20260916 and b["rng"] == "PCG64"


def test_constant_target_zero_delta_and_zero_spread():
    frame = _frame([True, False, True, False, True, True],
                   [0.05] * 6)
    out = paired_block_deltas(frame, 3, 6, seed=5,
                              starts=np.array([[0, 1]] * 6),
                              min_valid_reps=1)
    for rep in out["replicates"]:
        assert rep["delta"] == pytest.approx(0.0, abs=1e-15)
    assert out["quantile_lower"] == pytest.approx(0.0, abs=1e-15)
    assert out["quantile_upper"] == pytest.approx(0.0, abs=1e-15)


def test_single_group_all_null_and_range_withheld():
    frame = _frame([True] * 6, [0.1] * 6)  # 只有真组
    out = paired_block_deltas(frame, 3, 4, seed=9, min_valid_reps=1)
    assert out["valid_reps"] == 0 and out["null_reps"] == 4
    assert all(r["delta"] is None for r in out["replicates"])
    assert out["quantile_lower"] is None and out["quantile_upper"] is None
    assert out["range_withheld_reason"]
    assert out["point_estimate"] is None  # 全期也缺组


def test_missing_mask_keeps_axis_positions():
    # 第6行非法：保留在轴上参与抽样，但逐次统计剔除
    frame = _frame([True, False, True, False, True, False],
                   [0.1, 0.0, 0.2, -0.1, 0.3, 9.9],
                   legal=[True, True, True, True, True, False])
    out = paired_block_deltas(frame, 3, 1, seed=3,
                              starts=np.array([[0, 3]]), min_valid_reps=1)
    # 索引 [0,1,2,3,4,5]：整轴重排；第 6 行（非法）保留在轴但逐次统计剔除
    rep = out["replicates"][0]
    t_vals = [0.1, 0.2, 0.3]
    f_vals = [0.0, -0.1]
    assert rep["true_n"] == 3 and rep["false_n"] == 2
    assert rep["delta"] == pytest.approx(
        sum(t_vals) / 3 - sum(f_vals) / 2, abs=1e-12)


def test_n_less_than_block_length_not_estimable():
    frame = _frame([True, False] * 3, [0.1] * 6)
    out = paired_block_deltas(frame, 10, 5, seed=1)
    assert out["not_estimable_reason"]
    assert out["quantile_lower"] is None
    assert out["starts"] is None


def test_empty_frame_structured_not_estimable():
    # 主控R2反例：空表是资料不足，不是参数错误——不得抛 ValueError
    out = paired_block_deltas(_frame([], []), 3, 4, seed=1)
    assert out["not_estimable_reason"] == "not_estimable:empty_frame"
    assert out["starts"] is None
    assert out["replicates"] == []
    assert out["valid_reps"] == 0 and out["null_reps"] == 0
    assert out["quantile_lower"] is None and out["quantile_upper"] is None
    assert out["point_estimate"] is None


def test_duplicate_starts_allowed_and_deterministic():
    frame = _frame([True, False, True, False], [0.1, 0.0, 0.2, -0.1])
    out = paired_block_deltas(frame, 2, 2, seed=1,
                              starts=np.array([[2, 2], [0, 0]]),
                              min_valid_reps=1)
    # 起点 [2,2]：索引 [2,3,2,3][:4]=[2,3,2,3] → t=[0.2,0.2] f=[-0.1,-0.1]
    assert out["replicates"][0]["delta"] == pytest.approx(0.3, abs=1e-12)
    # 起点 [0,0]：索引 [0,1,0,1] → t=[0.1,0.1] f=[0.0,0.0]
    assert out["replicates"][1]["delta"] == pytest.approx(0.1, abs=1e-12)


def test_min_valid_reps_quality_gate():
    frame = _frame([True] * 6, [0.1] * 6)  # 全部缺组
    out = paired_block_deltas(frame, 3, 4, seed=9, min_valid_reps=3)
    assert out["valid_reps"] == 0 < out["min_valid_reps"]
    assert out["quantile_lower"] is None
    assert "有效重复不足" in out["range_withheld_reason"]


def test_numpy_version_and_metadata_recorded():
    frame = _frame([True, False] * 5, [0.1, -0.1] * 5)
    out = paired_block_deltas(frame, 4, 8, seed=20260916, min_valid_reps=1)
    assert out["numpy_version"] == np.__version__
    assert out["n"] == 10 and out["k"] == 3
    assert out["starts"].shape == (8, 3)
    assert out["quantile_method"] == "linear"
    assert out["range_name"] == "条件性95%重抽范围"
    assert out["point_estimate"] == pytest.approx(0.2, abs=1e-12)
