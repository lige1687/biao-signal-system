"""factor_evidence 成对循环区块重抽（固定方法，纯计算）。

- ``circular_indices``：纯索引函数——``(start+j) % n, j=0..L-1`` 按块拼接后
  截到 n 行；不含任何随机性，起点由调用方提供。
- ``paired_block_deltas``：固定长度循环区块重抽（Circular Block
  Bootstrap）。每种 L 新建 ``numpy.random.Generator(PCG64(seed))``，一次性
  ``integers(0, n, size=(reps, k))`` 抽全部起点（k=ceil(n/L)），起点矩阵
  全部保存；**同一索引用于 state/main/合法性三列**，绝不分别抽两组。
  n 为完整评价日期轴长度（不压缩缺行）；逐次统计先按合法性过滤再分组，
  缺任一组则 delta=null+原因，不补抽。
- ``linear_quantiles``：``numpy.quantile(method='linear')`` 的薄封装，输出
  「条件性95%重抽范围」。范围只在有效重复数达到质量约定时输出；它只是
  假设条件下的历史敏感性诊断，不是有效概率、显著通过或独立样本数。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

RANGE_NAME = "条件性95%重抽范围"


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _require_count(x, name: str) -> int:
    if isinstance(x, bool) or not isinstance(x, (int, np.integer)):
        raise ValueError(f"{name} 必须是正整数（拒绝布尔/浮点：{x!r}）")
    x = int(x)
    _require(x > 0, f"{name} 必须为正（收到 {x}）")
    return x


def _require_starts(starts, n: int, k: int) -> np.ndarray:
    arr = np.asarray(starts)
    _require(arr.ndim == 2 and arr.shape[1] == k,
             f"starts 必须是形状 (reps, k={k}) 的整数矩阵（收到 {arr.shape}）")
    if arr.dtype.kind not in "iu":
        raise ValueError(f"starts 必须是整数（收到 dtype {arr.dtype}）")
    _require(arr.min() >= 0 and arr.max() < n,
             f"starts 起点必须在 [0, n={n}) 范围内")
    return arr.astype(np.int64, copy=False)


def circular_indices(n: int, block_length: int, starts) -> np.ndarray:
    """把 k 个起点展开为截到 n 行的循环区块索引（纯函数，无随机）。"""
    n = _require_count(n, "n")
    block_length = _require_count(block_length, "block_length")
    s = np.asarray(starts)
    if s.ndim == 0:
        s = s.reshape(1)
    if s.dtype.kind not in "iu":
        raise ValueError(f"starts 必须是整数数组（收到 dtype {s.dtype}）")
    _require(s.min() >= 0 and s.max() < n,
             f"starts 起点必须在 [0, n={n}) 范围内（收到 [{s.min()}, {s.max()}]）")
    k = int(s.size)
    _require(k * block_length >= n,
             f"起点数×块长不足以覆盖 n 行（{k}×{block_length} < {n}）；"
             "截断只发生在拼接尾部")
    offsets = np.arange(block_length)
    idx = (s[:, None] + offsets[None, :]) % n
    return idx.reshape(-1)[:n]


def linear_quantiles(values, lower: float, upper: float):
    """numpy linear 分位（任务书固定口径）；values 为空抛 ValueError。"""
    arr = np.asarray(list(values), dtype=float)
    _require(arr.size > 0, "分位数需要至少一个有效值")
    return (float(np.quantile(arr, lower, method="linear")),
            float(np.quantile(arr, upper, method="linear")))


def _axis_arrays(frame: pd.DataFrame):
    states = np.array([None if s is None or (isinstance(s, float)
                                             and math.isnan(s)) else bool(s)
                       for s in frame["state"].tolist()], dtype=object)
    mains = pd.to_numeric(frame["main"], errors="coerce").to_numpy(dtype=float)
    legals = np.array([bool(v) for v in frame["legal"].tolist()], dtype=bool)
    return states, mains, legals


def paired_block_deltas(frame: pd.DataFrame, block_length: int, reps: int,
                        seed: int, *, starts=None,
                        min_valid_reps: int | None = None) -> dict:
    """成对循环区块重抽；返回起点矩阵、逐次结果与条件性范围。

    frame 必须是完整评价日期轴上的规范观察表（一行一格，经
    validate_observations / load_b1_observations 产生）；n=len(frame)。
    starts 显式提供时逐行作为各次重复的起点（测试与独立核验用），
    否则用 PCG64(seed) 一次性 integers(0, n, size=(reps, k)) 生成。
    """
    n_raw = len(frame)
    block_length = _require_count(block_length, "block_length")
    reps = _require_count(reps, "reps")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError(f"seed 必须是整数（收到 {seed!r}）")
    seed = int(seed)
    if min_valid_reps is None:
        min_valid_reps = math.ceil(0.95 * reps)
    base = {
        "n": n_raw, "block_length": block_length,
        "k": math.ceil(n_raw / block_length) if n_raw else 0,
        "reps": reps, "seed": seed, "rng": "PCG64",
        "start_draw": ("integers(0, n, size=(reps, k)) 单次调用；"
                       "每重复 k=ceil(n/L) 个起点，均匀于 [0,n)"),
        "index_rule": "(start+j) % n, j=0..L-1，按块拼接后截到 n 行；"
                      "同一索引用于 state/main/合法性",
        "numpy_version": np.__version__,
        "quantile_method": "linear",
        "range_name": RANGE_NAME,
        "min_valid_reps": int(min_valid_reps),
        "interpretation": ("只作为假设条件下的历史敏感性诊断；"
                           "不是有效概率/显著通过/独立样本数，"
                           "不用过零作机械采纳判决"),
    }
    if n_raw == 0:
        # 空表是资料不足，不是参数错误：结构化 not_estimable，不抛异常
        return {**base, "starts": None, "replicates": [],
                "valid_reps": 0, "null_reps": 0,
                "point_estimate": None, "valid_deltas": [],
                "quantile_lower": None, "quantile_upper": None,
                "not_estimable_reason": "not_estimable:empty_frame",
                "range_withheld_reason": None}
    n = _require_count(n_raw, "n(len(frame))")
    k = math.ceil(n / block_length)

    if n < block_length:
        return {**base, "starts": None, "replicates": [],
                "valid_reps": 0, "null_reps": 0,
                "point_estimate": None, "quantile_lower": None,
                "quantile_upper": None, "valid_deltas": [],
                "not_estimable_reason":
                    f"not_estimable:n_lt_block_length({n}<{block_length})",
                "range_withheld_reason": None}

    if starts is None:
        rng = np.random.Generator(np.random.PCG64(seed))
        starts_matrix = rng.integers(0, n, size=(reps, k)).astype(np.int64)
    else:
        starts_matrix = _require_starts(starts, n, k)
        _require(starts_matrix.shape[0] == reps,
                 f"starts 行数必须等于 reps={reps}（收到 {starts_matrix.shape[0]}）")

    states, mains, legals = _axis_arrays(frame)
    known_t = legals & (states == True) & ~np.isnan(mains)  # noqa: E712
    known_f = legals & (states == False) & ~np.isnan(mains)  # noqa: E712
    if known_t.sum() and known_f.sum():
        point = float(mains[known_t].mean() - mains[known_f].mean())
    else:
        point = None

    replicates: list[dict] = []
    valid_deltas: list[float] = []
    for r in range(reps):
        idx = circular_indices(n, block_length, starts_matrix[r])
        t_mask = known_t[idx]
        f_mask = known_f[idx]
        tn, fn = int(t_mask.sum()), int(f_mask.sum())
        if tn == 0 or fn == 0:
            reason = []
            if tn == 0:
                reason.append("true_group_empty")
            if fn == 0:
                reason.append("false_group_empty")
            replicates.append({"rep": r, "delta": None,
                               "true_n": tn, "false_n": fn,
                               "reason": "not_estimable:" + ",".join(reason)})
            continue
        delta = float(mains[idx][t_mask].mean() - mains[idx][f_mask].mean())
        replicates.append({"rep": r, "delta": delta, "true_n": tn,
                           "false_n": fn, "reason": None})
        valid_deltas.append(delta)

    withheld = None
    lo = hi = None
    if len(valid_deltas) >= max(1, min_valid_reps):
        lo, hi = linear_quantiles(valid_deltas, 0.025, 0.975)
    else:
        withheld = (f"有效重复不足 {min_valid_reps}/{reps}（本轮质量约定；"
                    f"实际有效 {len(valid_deltas)}"
                    + ("，每次都缺组）" if len(valid_deltas) == 0 else "）")
                    + "，不输出区间")

    return {**base, "starts": starts_matrix, "replicates": replicates,
            "valid_reps": len(valid_deltas),
            "null_reps": reps - len(valid_deltas),
            "point_estimate": point, "valid_deltas": valid_deltas,
            "quantile_lower": lo, "quantile_upper": hi,
            "not_estimable_reason": None,
            "range_withheld_reason": withheld}
