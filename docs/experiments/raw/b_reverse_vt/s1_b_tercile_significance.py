#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 S1：B 模块高波 vs 低波三分位 r_net 差异的统计显著性检验（2026-09-02）。

===========================================================================
任务定位（必读，Prompt S 阶段一）
===========================================================================
任务 R（全池复验）第五节下一步方向第 3 条记录了一处未深入的观察：三个
入场模块的 RV20 高波组表现方向不一致——A -1.106R（高波亏损）、B +0.330R
（高波盈利）、C -0.073R（接近零）。K/R 任务两次测了"vt 缩放对 B 模块
无效"（B 7 档 falsified），但两次都是**同方向**——用波动率去**减仓**。
如果 B 的"高波信号盈利"是真的，"vt 对 B 无效"这个证伪的真实原因可能
不是"B 不需要按波动率调整"，而是"调整方向错了"。

**本任务 S1（必做，决定是否进入 S2）**：先验证 B 高波 vs 低波 r_net 差异
是否统计显著（不是三分位切分下的噪音）。S2（反向 vt 规则测试）**仅当
S1 显著才执行**——按 Prompt S 收口条款："如果置信区间含零或样本量不足，
直接归档'反差不显著，可能是三分位切分下的噪音，不构成机制假设'，
**不进入第二步**。"

===========================================================================
数据源（与任务 R 完全一致，5 层锚定 100% 对齐 §0.3）
===========================================================================
- trades：`docs/experiments/raw/backtest-runs-snapshot-2026-08-31/20260831-231715-1bb6f2.json`
  （B 模块，563 raw / 552 closed / 79 结构止损 + 473 抵扣价 + 11 剔除）
- K线：`docs/experiments/raw/pool-snapshot-2026-08-25/` 内 175 per_symbol 标的
- 用 per_symbol 集合做标的子集筛选（不是 177 全量减 2）

===========================================================================
判定标准（事前固化，跑后不得调整）
===========================================================================
**主判定**：
- S1.P1：分层 bootstrap（高波组 vs 低波组独立重采样）10000 次，
  RandomState(20260902)，Δμ = mean(high_r) − mean(low_r) 的
  95% percentile CI 下界 > 0。
- S1.P2：高波组 n ≥ 30（与 M 任务 P0 功效门槛同源）。
- S1.P3：高波组 mean r_net 必须**绝对大于** 0（不只是大于低波组——
  反向 vt 规则要求 E>1 的标的本身是赚钱的，否则加仓只是放亏）。
- 反差不显著 = 上述任一不满足；进入 S2 必须 3/3 全过。

**阴性对照**（稳健性，非主判定）：
- 把 RV20 标签随机打乱（RandomState(20260902)，独立种子）后重新切三分
  位，重算 Δμ_shuffle 1000 次。S1 通过要求"真实 Δμ 显著大于 Δμ_shuffle
  分布的 95 分位"——若真实 Δμ 与随机 Δμ 分布重叠，说明反差可由切分噪音
  解释。

===========================================================================
安全约束
===========================================================================
只读研究：不改 src/、不 push、不删文件；新增产出仅
docs/experiments/raw/b_reverse_vt/。

===========================================================================
复现
===========================================================================
解释器：/Users/liyongbiao/Desktop/biao-signal-system/.venv/bin/python。
PYTHONHASHSEED=0 / 42 各跑一次 --dump-hash，md5 一致才入档。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RUNS_DIR = REPO / "docs" / "experiments" / "raw" / "backtest-runs-snapshot-2026-08-31"
POOL_DIR = REPO / "docs" / "experiments" / "raw" / "pool-snapshot-2026-08-25"

B_RUN_FILE = "20260831-231715-1bb6f2.json"
EXCLUDED_REASONS = ("invalid_nonpositive_risk", "skipped_limit_up_at_entry")
EXCLUDE_FROM_POOL = ("159165.SZ", "560390.SS")
BOOT_N = 10_000
SHUFFLE_N = 1_000
BOOT_SEED = 20_260_902
SHUFFLE_SEED = 20_260_902


def vol_at(closes, signal_date):
    rets = closes.pct_change(fill_method=None)
    vol = rets.rolling(20).std() * np.sqrt(252.0)
    ts = pd.Timestamp(signal_date)
    if ts not in vol.index:
        return None
    v = float(vol.loc[ts])
    return v if np.isfinite(v) else None


def two_independent_bootstrap_ci(a, b, n, seed):
    rng = np.random.RandomState(seed)
    n_a, n_b = len(a), len(b)
    deltas = np.empty(n)
    ma = np.empty(n)
    mb = np.empty(n)
    for i in range(n):
        ia = rng.randint(0, n_a, n_a)
        ib = rng.randint(0, n_b, n_b)
        ma[i] = a[ia].mean()
        mb[i] = b[ib].mean()
        deltas[i] = ma[i] - mb[i]
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(deltas.mean()), float(lo), float(hi), float(a.mean()), float(b.mean())


def anchor_check():
    out = {}
    pool_files = sorted(POOL_DIR.glob("*.bars.parquet"))
    pool_syms = {p.name.replace(".bars.parquet", "") for p in pool_files}
    d = json.loads((RUNS_DIR / B_RUN_FILE).read_text(encoding="utf-8"))
    per_sym_run = {p["symbol"] for p in d["per_symbol"]}
    raw_count = len(d["trades"])

    c = {}
    for t in d["trades"]:
        c[t.get("exit_reason")] = c.get(t.get("exit_reason"), 0) + 1
    target = pool_syms - set(EXCLUDE_FROM_POOL)

    out["per_symbol_count"] = len(per_sym_run)
    out["raw_count"] = raw_count
    out["pool_minus_2_count"] = len(target)
    out["per_symbol_equals_pool_minus_2"] = (per_sym_run == target)
    out["exit_reason_breakdown"] = c
    out["expected_exit_reason"] = {
        "exit_a6_1_costbasis": 473, "structure_stop_C": 79,
        "invalid_nonpositive_risk": 5, "skipped_limit_up_at_entry": 1,
        "open_at_end": 5,
    }
    out["exit_reason_match"] = all(
        c.get(k, 0) == v for k, v in out["expected_exit_reason"].items()
    )
    out["anchor_pass"] = bool(
        out["per_symbol_count"] == 175
        and out["raw_count"] == 563
        and out["per_symbol_equals_pool_minus_2"]
        and out["exit_reason_match"]
    )
    return out


def main():
    anchor = anchor_check()
    if not anchor["anchor_pass"]:
        print("!! 锚定校验失败，先停（按 Prompt S 收口条款）：")
        print(json.dumps(anchor, ensure_ascii=False, indent=1))
        sys.exit(2)
    print("锚定校验通过：")
    print(json.dumps({k: v for k, v in anchor.items() if k != "anchor_pass"},
                     ensure_ascii=False, indent=1))

    per_sym_set = {p["symbol"] for p in json.loads(
        (RUNS_DIR / B_RUN_FILE).read_text(encoding="utf-8"))["per_symbol"]}

    print("\n== 加载 B 模块 552 笔 closed trades ==", flush=True)
    d = json.loads((RUNS_DIR / B_RUN_FILE).read_text(encoding="utf-8"))
    closed = [t for t in d["trades"]
              if t.get("r_net") is not None
              and t.get("exit_date") is not None
              and t.get("exit_reason") not in EXCLUDED_REASONS
              and t["symbol"] in per_sym_set]
    print(f"  closed trades: {len(closed)}（期望 552）", flush=True)

    print("\n== RV20 标注 ==", flush=True)
    recs = []
    missing = 0
    for t in closed:
        sym, sd = t["symbol"], t["signal_date"]
        pq = POOL_DIR / f"{sym}.bars.parquet"
        if not pq.exists():
            missing += 1
            continue
        df = pd.read_parquet(pq)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        closes = df["close"].dropna()
        r20 = vol_at(closes, sd)
        if r20 is None:
            missing += 1
            continue
        recs.append({"symbol": sym, "signal_date": sd,
                     "r_net": float(t["r_net"]), "rv20": r20})
    print(f"  RV20 可得: {len(recs)} / {len(closed)}（缺 {missing}）", flush=True)
    if missing:
        print(f"  缺 RV20 率: {missing/len(closed):.2%}（应<5%）")

    rs = np.array([x["r_net"] for x in recs])
    rv = np.array([x["rv20"] for x in recs])

    print("\n== RV20 三分位切分 ==", flush=True)
    order = np.argsort(rv, kind="stable")
    n = order.size
    t1 = order[: n // 3]
    t2 = order[n // 3: 2 * n // 3]
    t3 = order[2 * n // 3:]

    low_r = rs[t1]
    mid_r = rs[t2]
    high_r = rs[t3]
    low_rv = rv[t1]
    mid_rv = rv[t2]
    high_rv = rv[t3]
    print(f"  低波组 n={len(low_r)}  RV20 区间 [{low_rv.min():.3f}, {low_rv.max():.3f}]  mean_r={low_r.mean():+.4f}R")
    print(f"  中波组 n={len(mid_r)}  RV20 区间 [{mid_rv.min():.3f}, {mid_rv.max():.3f}]  mean_r={mid_r.mean():+.4f}R")
    print(f"  高波组 n={len(high_r)} RV20 区间 [{high_rv.min():.3f}, {high_rv.max():.3f}]  mean_r={high_r.mean():+.4f}R")
    delta_mean = float(high_r.mean() - low_r.mean())
    print(f"  Δμ (高−低) 点估计: {delta_mean:+.4f}R")

    print("\n== S1.P1 独立样本 bootstrap 95% CI ==", flush=True)
    delta_boot, ci_lo, ci_hi, mean_h, mean_l = two_independent_bootstrap_ci(
        high_r, low_r, BOOT_N, BOOT_SEED
    )
    p1_pass = bool(ci_lo > 0)
    print(f"  delta (boot mean): {delta_boot:+.4f}R")
    print(f"  95% CI: [{ci_lo:+.4f}, {ci_hi:+.4f}]")
    print(f"  S1.P1 (CI 下界 > 0): {'PASS' if p1_pass else 'FAIL'}")

    p2_pass = bool(len(high_r) >= 30)
    print(f"\n== S1.P2 高波组 n ≥ 30 ==")
    print(f"  高波组 n = {len(high_r)}, 阈值 30: {'PASS' if p2_pass else 'FAIL'}")

    p3_pass = bool(high_r.mean() > 0)
    print(f"\n== S1.P3 高波组 mean r_net > 0 ==")
    print(f"  高波组 mean r_net = {high_r.mean():+.4f}R: {'PASS' if p3_pass else 'FAIL'}")

    print("\n== 阴性对照：shuffle RV20 标签 ==", flush=True)
    shuffle_rng = np.random.RandomState(SHUFFLE_SEED)
    shuffled_deltas = np.empty(SHUFFLE_N)
    for i in range(SHUFFLE_N):
        rv_shuf = shuffle_rng.permutation(rv)
        order_s = np.argsort(rv_shuf, kind="stable")
        h_s = rs[order_s[2 * n // 3:]]
        l_s = rs[order_s[: n // 3]]
        shuffled_deltas[i] = h_s.mean() - l_s.mean()
    shuf_lo, shuf_med, shuf_hi = np.percentile(shuffled_deltas, [2.5, 50, 97.5])
    shuf_95 = np.percentile(shuffled_deltas, 95)
    real_above_shuf_95 = bool(delta_mean > shuf_95)
    print(f"  1000 次 shuffle Δμ 分布: 中位 {shuf_med:+.4f}R, "
          f"95% [{shuf_lo:+.4f}, {shuf_hi:+.4f}]")
    print(f"  真实 Δμ = {delta_mean:+.4f}R vs shuffle 95 分位 = {shuf_95:+.4f}R: "
          f"{'真实 Δμ 显著 > shuffle 95 分位' if real_above_shuf_95 else '真实 Δμ 在 shuffle 95 分位内（含噪音可能性）'}")

    s1_pass = bool(p1_pass and p2_pass and p3_pass and real_above_shuf_95)
    print(f"\n=== S1 综合判定 ===")
    print(f"  P1 (CI > 0): {p1_pass}")
    print(f"  P2 (n≥30): {p2_pass}")
    print(f"  P3 (mean>0): {p3_pass}")
    print(f"  阴性对照 (真实 Δμ > shuffle 95 分位): {real_above_shuf_95}")
    print(f"  S1 综合: {'PASS' if s1_pass else 'FAIL'} → "
          f"{'进入 S2 反向 vt 规则测试' if s1_pass else '归档为噪音，不进入 S2'}")

    results = {
        "task": "S1: B 模块高波 vs 低波 r_net 差异显著性检验",
        "anchor": anchor,
        "data": {
            "b_run_file": B_RUN_FILE,
            "n_closed": len(closed),
            "n_with_rv20": len(recs),
            "rv20_missing": missing,
        },
        "terciles": {
            "low":  {"n": int(len(low_r)),  "rv20_range": [float(low_rv.min()),  float(low_rv.max())],  "mean_r": float(low_r.mean())},
            "mid":  {"n": int(len(mid_r)),  "rv20_range": [float(mid_rv.min()),  float(mid_rv.max())],  "mean_r": float(mid_r.mean())},
            "high": {"n": int(len(high_r)), "rv20_range": [float(high_rv.min()), float(high_rv.max())], "mean_r": float(high_r.mean())},
        },
        "delta_point_estimate": delta_mean,
        "s1_p1_bootstrap": {
            "delta_boot_mean": delta_boot,
            "ci95": [ci_lo, ci_hi],
            "ci_lower_gt_0": p1_pass,
        },
        "s1_p2_sample_size": {"high_n": int(len(high_r)), "ge_30": p2_pass},
        "s1_p3_high_positive": {"high_mean_r": float(high_r.mean()), "gt_0": p3_pass},
        "negative_control_shuffle": {
            "n_shuffles": SHUFFLE_N,
            "shuf_median": float(shuf_med),
            "shuf_ci95": [float(shuf_lo), float(shuf_hi)],
            "shuf_95_percentile": float(shuf_95),
            "real_above_shuf_95": real_above_shuf_95,
        },
        "s1_pass": s1_pass,
    }
    payload = json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True,
                         default=float)
    out_path = HERE / "s1_b_tercile_significance.json"
    out_path.write_text(payload, encoding="utf-8")
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()
    print(f"\n落盘: {out_path}")
    print(f"md5(canonical json) = {digest}")

    if "--dump-hash" in sys.argv:
        print("HASH", digest)


if __name__ == "__main__":
    main()
