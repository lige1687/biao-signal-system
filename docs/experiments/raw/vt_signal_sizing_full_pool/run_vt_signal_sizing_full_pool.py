#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 R2：K 任务 vt 单笔缩放——**全池 175 标的复验**（2026-09-02）。

===========================================================================
任务定位（与原 K 任务一字不差，仅换数据源）
===========================================================================
原 K 任务（`docs/experiments/raw/vt_signal_sizing/run_vt_signal_sizing.py`）
核心发现：A 模块在 12.5%-20% 四档 passed（20% 锚点 ΔexpR +0.102R，CI 下界
+0.014），B/C 模块证伪；A 模块的增益来自高波动信号是亏损主力
（三分位 ρ=−0.089, p=0.025）。但样本 A_cn 是 ETF 池 641 笔，
**不是 175 全池**——存在样本构成偏差的可能。

本任务 R2 即用 8-31 矩阵三个 a6_1_costbasis 基准 run 的 **175 per_symbol
全池**（A 1521 / B 563 / C 225 笔）复算 K 任务同一套预注册协议，回答：
1. ETF 池 A_cn 的"高波信号亏损主力"机制在全池 A 是否同样成立？
2. A 全池最优带是否仍在 12.5-20%（样本内最优端警示）？
3. B 全池是否仍 falsified（ΔexpR CI 全含 0）？
4. C 全池是否仍"经济一票否决"（retention 地板）？
5. 估计器敏感性（rv20 vs ewma97）的 5 倍缩水是否复现？

**判定标准 J1/J2/J3、F2 模块非对称预注册、目标网格 7 档、估计器 2 种、
bootstrap 10000 次、RandomState(20260902)——全部逐字复用 K 任务
docstring 的定义**（已写死在下方「判定标准」节）。本任务是补充复验
不是替代——不删除/修改原 K 任务 `vt-signal-driven-sizing-ARCHIVE-2026-09-02.md`，
只在结论上与原 K 任务对齐或对比。

===========================================================================
数据源切换（与原 K 任务的差异，仅 1 项）
===========================================================================
- 原 K 用仓库内 6 个 git 归档 run（breadth_overlay A_cn 641 笔 +
  lifecycle_combo B_cn 100 笔 + C_cn 172 笔 + stage_b200 A_us 95 笔 +
  B_us 37 笔 + A_cn_shrink 275 笔——**5 个独立样本，跨池**）。
- 本任务用 8-31 矩阵 a6_1_costbasis 3 个 run（A 1521 / B 563 / C 225
  笔），**全部来自 175 per_symbol 全池同一扫描**——自然只对应
  3 个样本 {A, B, C}，对齐 stop_loss_matrix-ARCHIVE 模块口径。
- 行情：原 K 任务用腾讯 fqkline 联网抓取（与归档时点的 8-25 池不同
  源），本任务直接用 `docs/experiments/raw/pool-snapshot-2026-08-25/`
  内 .bars.parquet 读 RV20/ewma97——**与 8-31 引擎读取的池同源**，
  无需 G2 年代核对（已经在 stop_loss_matrix-ARCHIVE 中逐笔锚定 0 失配）。
  本任务的 G2 退化为：每模块 ≥98% 已入场笔满足 |重取开盘(entry_date)
  − 归档 entry_price|/entry_price ≤ 0.35%（保留 K 任务原协议作为
  健全性检查，不作为 G2 FAIL 阻断门槛——以原 K 任务"G2 FAIL → 解读
  层降档但保留结论"为准）。

===========================================================================
锚定校验（必须 100% 通过才跑判定统计，参照 Prompt R 收口条款）
===========================================================================
- 175 标的清单：A/B/C 三个 run 的 per_symbol 完全一致（各 175）。
  pool-snapshot 目录（177 标的）减 159165.SZ + 560390.SS = 175。
- 笔数锚定：A 1521 / B 563 / C 225 = 8-31 三个 run 的 trades 长度。

===========================================================================
机制假设（与原 K 一字不差）
===========================================================================
每笔信号触发时，用该标的**信号日 T 收盘（含 T）**的 RV20 计算单笔
仓位系数 **E = clip(目标/RV20, 0.25, 1)**，缩放该笔头寸；T+1 数据
不可用（无前视，对齐 vt-grid"t 收盘计算、t+1 执行"）。自变量=**波动率**，
非宽度/利率分位（与已判负 8 项的 b50/b200 宽度变量不同类，红线逐一
自查见原 K 任务冲突发现①）。

===========================================================================
判定标准（事前写死，跑后不得调整——与原 K 一字不差）
===========================================================================
有效性门槛（任一不通过 → 整份结果作废，不得解读）：
  G1 基线复现：A/B/C 自算等权基线（n/expR/PF）必须与 8-31 run JSON
     trades 自算一致——证明逐笔记录未损坏且指标口径与引擎
     compute_metrics(net=True) 一致。
  G2 健全性核对（健全性检查，不作 FAIL 阻断；与原 K 任务"G2 FAIL →
     解读降档"同处理）：每模块 ≥98% 已入场笔满足 |重取开盘(entry_date)
     − 归档 entry_price| / entry_price ≤ 0.35%；中位偏离应≈舍入量级。
     本任务的 K 线来自 8-25 池快照，与 8-31 引擎读取的池同源，预计
     中位偏离 ≈ 0；若 G2 失败则报告层如实披露，不阻断主判定。
  G3 RV20 可得：因历史不足 21 根收盘而丢弃的笔 <5%/模块。

主判定 Q1（主样本 = A，主锚点 target=20%，主估计器 = rv20）：
  J1 风险效率改善：ΔexpR = expR_w − expR_0（expR_w = Σ(E·r)/Σ(E)，
     expR_0 = mean(r)，同一已平仓集合）的逐笔配对 bootstrap
     （10000 次，numpy RandomState(20260902)）95% percentile CI 下界 > 0；
  J2 绝对收益保留：retention = Σ(E·r)/Σ(r) ≥ 0.80（Σ(r)≤0 时该条不判
     只记录）；
  J3 PF 不劣化：PF_w ≥ PF_0 − 0.05。
  verdict：passed = J1∧J2∧J3；watch = ΔexpR 点估计>0 但 CI 含 0 且
  J2/J3 成立；falsified = 其余。
  参数稳健：target ∈ {12.5,15,17.5,20,22.5,30,40}%（7 档全报）；
  「方向稳健」= ≥5/7 档 ΔexpR>0。估计器稳健：锚点 20% 用 ewma97 复算
  （仅作敏感性披露）。

副判定 Q2（F2 的 C 排除问题，锚点 20%/rv20，逐模块 A/B/C）：
  报 ΔexpR + bootstrap CI + RV20 三分位组（低/中/高波）mean r_net 与
  高−低差 + Spearman(RV20, r_net)。
  「C 应排除于 vt（非对称成立）」= A 过 J1（CI 下界>0）且 C 的
  ΔexpR CI 上界 ≤ +0.05R；
  「C 同样适用」= C CI 下界 > 0；
  其余 = 不确定。

===========================================================================
安全约束
===========================================================================
只读研究：不改 src/、不 push、不删文件；产出仅
docs/experiments/raw/vt_signal_sizing_full_pool/。

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
REPO = HERE.parents[3]  # HERE = docs/experiments/raw/vt_signal_sizing_full_pool/ → REPO = repo root
RUNS_DIR = REPO / "docs" / "experiments" / "raw" / "backtest-runs-snapshot-2026-08-31"
POOL_DIR = REPO / "docs" / "experiments" / "raw" / "pool-snapshot-2026-08-25"

#: ── 预注册参数（与原 K 任务一字不差）────────────────────
TARGETS = (0.125, 0.15, 0.175, 0.20, 0.225, 0.30, 0.40)
ANCHOR = 0.20
ESTIMATORS = ("rv20", "ewma97")
E_FLOOR, E_CAP = 0.25, 1.0
BOOT_N = 10_000
BOOT_SEED = 20_260_902
RETENTION_MIN = 0.80
PF_TOLERANCE = 0.05
G2_RATE_TOL, G2_SHARE_MIN = 0.0035, 0.98
G3_MISSING_MAX = 0.05
CI_C_EXCLUSION_UB = 0.05  # Q2：C 排除判定的 CI 上界线

#: 8-31 矩阵 a6_1_costbasis 三个基准 run
RUN_FILES = [
    ("A", "20260831-231254-88cb12.json"),
    ("B", "20260831-231715-1bb6f2.json"),
    ("C", "20260831-231944-b87a6b.json"),
]
#: raw trades 锚定（与 Prompt R 一致）
ANCHOR_RAW_TRADES = {"A": 1521, "B": 563, "C": 225}
#: closed trades 锚定（去 EXCLUDED_REASONS 后，与 stop-loss-matrix-ARCHIVE:36-38
#: 报告口径 1469/552/224 一致；这也是 K 任务 G1 baseline 应匹配的数值）
ANCHOR_CLOSED_TRADES = {"A": 1469, "B": 552, "C": 224}
#: canonical 8-31 baseline 指标（自算应匹配 stop-loss-matrix-ARCHIVE 报告，
#: 用作 G1 健全性核对——"自算 vs 8-31 引擎 compute_metrics" 等价）
CANONICAL_BASELINE = {
    "A": {"n": 1469, "expR": 1.179227803, "PF": 1.966303330,
          "source": "stop-loss-matrix-ARCHIVE-2026-09-01.md:36-38 + 8-31 run JSON 自算"},
    "B": {"n": 552, "expR": 0.358532989, "PF": 1.578290335,
          "source": "stop-loss-matrix-ARCHIVE-2026-09-01.md:36-38 + 8-31 run JSON 自算"},
    "C": {"n": 224, "expR": 0.127747708, "PF": 1.382214464,
          "source": "stop-loss-matrix-ARCHIVE-2026-09-01.md:36-38 + 8-31 run JSON 自算"},
}
EXCLUDE_FROM_POOL = ("159165.SZ", "560390.SS")
EXCLUDED_REASONS = ("invalid_nonpositive_risk", "skipped_limit_up_at_entry")


# ---------------------------------------------------------------- 工具
def equal_metrics(rs: np.ndarray) -> dict:
    n = int(rs.size)
    wins, losses = rs[rs > 0], rs[rs <= 0]
    return {
        "n": n,
        "expR": float(rs.mean()) if n else None,
        "PF": (float(wins.sum() / abs(losses.sum()))
               if n and losses.sum() != 0 else None),
        "total_r": float(rs.sum()) if n else None,
        "win_rate": float((rs > 0).mean()) if n else None,
    }


def sized_metrics(rs: np.ndarray, es: np.ndarray) -> dict:
    wr = rs * es
    n = int(rs.size)
    wins, losses = wr[wr > 0], wr[wr <= 0]
    return {
        "n": n,
        "expR_w": float(wr.sum() / es.sum()) if n else None,
        "PF_w": (float(wins.sum() / abs(losses.sum()))
                 if n and losses.sum() != 0 else None),
        "total_r_w": float(wr.sum()) if n else None,
        "mean_E": float(es.mean()) if n else None,
        "median_E": float(np.median(es)) if n else None,
        "share_E_floor": float((es <= E_FLOOR + 1e-12).mean()) if n else None,
        "share_E_cap": float((es >= E_CAP - 1e-12).mean()) if n else None,
    }


def e_of(rv20: np.ndarray, target: float) -> np.ndarray:
    return np.clip(target / rv20, E_FLOOR, E_CAP)


def paired_bootstrap(rs: np.ndarray, es: np.ndarray) -> tuple[float, float]:
    rng = np.random.RandomState(BOOT_SEED)
    n = rs.size
    deltas = np.empty(BOOT_N)
    for b in range(BOOT_N):
        idx = rng.randint(0, n, n)
        r, e = rs[idx], es[idx]
        deltas[b] = (r * e).sum() / e.sum() - r.mean()
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(lo), float(hi)


def vol_at(closes: pd.Series, signal_date: str, estimator: str) -> float | None:
    rets = closes.pct_change(fill_method=None)
    if estimator == "rv20":
        vol = rets.rolling(20).std() * np.sqrt(252.0)
    elif estimator == "ewma97":
        vol = rets.ewm(alpha=0.03, min_periods=20).std() * np.sqrt(252.0)
    else:
        raise ValueError(estimator)
    ts = pd.Timestamp(signal_date)
    if ts not in vol.index:
        return None
    v = float(vol.loc[ts])
    return v if np.isfinite(v) else None


# ---------------------------------------------------------------- 锚定校验
def anchor_check() -> dict:
    out = {}
    pool_files = sorted(POOL_DIR.glob("*.bars.parquet"))
    pool_syms = {p.name.replace(".bars.parquet", "") for p in pool_files}
    per_sym_sets = {}
    raw_trade_counts = {}
    for module, fname in RUN_FILES:
        d = json.loads((RUNS_DIR / fname).read_text(encoding="utf-8"))
        per_sym_sets[module] = {p["symbol"] for p in d["per_symbol"]}
        raw_trade_counts[module] = len(d["trades"])
    out["per_symbol_counts"] = {k: len(v) for k, v in per_sym_sets.items()}
    out["per_symbol_identical"] = (
        per_sym_sets["A"] == per_sym_sets["B"] == per_sym_sets["C"]
    )
    out["raw_trade_counts"] = raw_trade_counts
    out["raw_trade_counts_match_anchor"] = (raw_trade_counts == ANCHOR_RAW_TRADES)
    target = pool_syms - set(EXCLUDE_FROM_POOL)
    out["pool_minus_2_size"] = len(target)
    out["per_symbol_A_size"] = len(per_sym_sets["A"])
    out["pool_minus_2_equals_per_symbol_A"] = (target == per_sym_sets["A"])
    out["anchor_pass"] = bool(
        out["per_symbol_identical"]
        and out["raw_trade_counts_match_anchor"]
        and out["pool_minus_2_equals_per_symbol_A"]
    )
    return out


# ---------------------------------------------------------------- 主流程
def main() -> None:
    anchor = anchor_check()
    if not anchor["anchor_pass"]:
        print("!! 锚定校验失败，先停（按 Prompt R 收口条款）：")
        print(json.dumps(anchor, ensure_ascii=False, indent=1))
        sys.exit(2)
    print("锚定校验通过：")
    print(json.dumps({k: v for k, v in anchor.items() if k != "anchor_pass"},
                     ensure_ascii=False, indent=1))

    per_sym_set = {p["symbol"] for p in json.loads(
        (RUNS_DIR / RUN_FILES[0][1]).read_text(encoding="utf-8"))["per_symbol"]}

    print("\n== 加载 K 线 ==", flush=True)
    pool_bars: dict[str, pd.Series] = {}
    pool_close_for_vol: dict[str, pd.Series] = {}
    for sym in sorted(per_sym_set):
        pq = POOL_DIR / f"{sym}.bars.parquet"
        if not pq.exists():
            print(f"  ! 缺 K 线: {sym}", flush=True)
            continue
        df = pd.read_parquet(pq)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        df = df[~df.index.duplicated(keep="last")]
        pool_bars[sym] = df["open"]
        pool_close_for_vol[sym] = df["close"].astype(float)
    print(f"  K 线加载完成: {len(pool_bars)} 标的", flush=True)

    g1: dict = {}
    g2: dict = {}
    samples: dict[str, dict] = {}
    g3: dict = {}
    g2_mismatch: dict[str, list] = {}
    g3_missing_detail: dict[str, list] = {}

    for module, fname in RUN_FILES:
        d = json.loads((RUNS_DIR / fname).read_text(encoding="utf-8"))
        closed = [t for t in d["trades"]
                  if t.get("r_net") is not None
                  and t.get("exit_date") is not None
                  and t.get("exit_reason") not in EXCLUDED_REASONS
                  and t["symbol"] in per_sym_set]
        rs_eq = np.array([t["r_net"] for t in closed])
        m = equal_metrics(rs_eq)
        canon = CANONICAL_BASELINE[module]
        # G1: closed trades count + expR + PF 都要与 stop-loss-matrix-ARCHIVE 报告对齐
        n_ok = m["n"] == canon["n"]
        expr_ok = m["expR"] is not None and abs(m["expR"] - canon["expR"]) < 1e-6
        pf_ok = m["PF"] is not None and abs(m["PF"] - canon["PF"]) < 1e-6
        g1[module] = {
            "n": m["n"], "expR": m["expR"], "PF": m["PF"],
            "expected_n": canon["n"], "expected_expR": canon["expR"],
            "expected_PF": canon["PF"],
            "pass": bool(n_ok and expr_ok and pf_ok),
            "source": canon["source"],
        }
        print(f"  {module} G1: n={m['n']} expR={m['expR']:.9f} PF={m['PF']:.9f}"
              f" expected n={canon['n']} expR={canon['expR']:.9f} PF={canon['PF']:.9f}"
              f" -> {'OK' if g1[module]['pass'] else 'FAIL'}", flush=True)

        devs, checked = [], 0
        bad = []
        for t in closed:
            sym, ed, ep = t["symbol"], t.get("entry_date"), t.get("entry_price")
            if sym not in pool_bars or not ed or not ep:
                continue
            ts = pd.Timestamp(ed)
            if ts not in pool_bars[sym].index:
                continue
            o = float(pool_bars[sym].loc[ts])
            if o > 0 and ep > 0:
                dev = abs(o / float(ep) - 1.0)
                devs.append(dev); checked += 1
                if dev > G2_RATE_TOL:
                    bad.append({"symbol": sym, "entry_date": ed,
                                "archived_entry_price": float(ep),
                                "fetched_open": o, "dev": float(dev)})
        devs_a = np.array(devs)
        share_ok = float((devs_a <= G2_RATE_TOL).mean()) if checked else 0.0
        g2[module] = {
            "checked": checked,
            "median_dev": float(np.median(devs_a)) if checked else None,
            "max_dev": float(devs_a.max()) if checked else None,
            "share_within_tol": share_ok,
            "pass_strict": bool(checked > 0 and share_ok >= G2_SHARE_MIN),
            "robustness_check_not_blocking": True,
        }
        g2_mismatch[module] = bad
        med = g2[module]["median_dev"]
        med_s = f"{med:.5%}" if med is not None else "NA"
        print(f"  {module} G2: 核对 {checked} 笔，中位 {med_s}，"
              f"≤{G2_RATE_TOL:.2%} 占比 {share_ok:.1%}", flush=True)

        recs = []
        missing = 0
        g3_missing_detail[module] = []
        for t in closed:
            sym, sd = t["symbol"], t["signal_date"]
            if sym not in pool_close_for_vol:
                missing += 1
                g3_missing_detail[module].append(
                    {"symbol": sym, "signal_date": sd,
                     "cause": "symbol_not_in_pool_bars"})
                continue
            s = pool_close_for_vol[sym].dropna()
            r20 = vol_at(s, sd, "rv20")
            e97 = vol_at(s, sd, "ewma97")
            if r20 is None or e97 is None:
                missing += 1
                g3_missing_detail[module].append(
                    {"symbol": sym, "signal_date": sd,
                     "cause": "signal_date_not_in_series_or_vol_nan"})
                continue
            recs.append({"symbol": sym, "signal_date": sd,
                         "r_net": float(t["r_net"]), "rv20": r20,
                         "ewma97": e97})
        miss_rate = missing / max(len(closed), 1)
        g3[module] = {"closed": len(closed), "rv20_missing": missing,
                      "missing_rate": miss_rate,
                      "pass": bool(miss_rate < G3_MISSING_MAX)}
        samples[module] = {
            "recs": recs,
            "rs": np.array([x["r_net"] for x in recs]),
            "rv": np.array([x["rv20"] for x in recs]),
            "ewma97": np.array([x["ewma97"] for x in recs]),
        }
        n_valid = len(recs)
        med_rv = float(np.median(samples[module]["rv"])) if n_valid else float("nan")
        print(f"  {module} G3: 已平仓 {len(closed)}, RV20 可得 {n_valid}"
              f"（缺 {missing}, {miss_rate:.1%}）, RV20 中位 {med_rv:.1%}",
              flush=True)

    g1_all = all(v["pass"] for v in g1.values())
    g3_all = all(v["pass"] for v in g3.values())

    print("\n== 主检验网格 ==", flush=True)
    grid: dict = {}
    for module in sorted(samples):
        s = samples[module]
        if not s["rs"].size:
            continue
        base = equal_metrics(s["rs"])
        grid[module] = {"baseline": base, "cells": {}}
        for est in ESTIMATORS:
            rv = s["rv"] if est == "rv20" else s["ewma97"]
            for tgt in TARGETS:
                es = e_of(rv, tgt)
                sm = sized_metrics(s["rs"], es)
                d_expR = sm["expR_w"] - base["expR"]
                retention = (sm["total_r_w"] / base["total_r"]
                             if base["total_r"] and base["total_r"] > 0 else None)
                pf_ok = (bool(sm["PF_w"] >= base["PF"] - PF_TOLERANCE)
                         if sm["PF_w"] is not None and base["PF"] is not None
                         else None)
                ret_ok = (None if retention is None
                          else bool(retention >= RETENTION_MIN))
                lo = hi = None
                if est == "rv20" or (est == "ewma97" and tgt == ANCHOR):
                    lo, hi = paired_bootstrap(s["rs"], es)
                j1 = bool(lo is not None and lo > 0)
                verdict = None
                if est == "rv20":
                    if j1 and ret_ok is not False and pf_ok is not False:
                        verdict = "passed"
                    elif d_expR > 0 and ret_ok is not False and pf_ok is not False:
                        verdict = "watch"
                    else:
                        verdict = "falsified"
                grid[module]["cells"][f"{est}|{tgt:g}"] = {
                    **sm, "delta_expR": d_expR, "retention": retention,
                    "pf_ok": pf_ok, "ret_ok": ret_ok,
                    "boot_ci_lo": lo, "boot_ci_hi": hi, "verdict": verdict,
                }
        n_pos = sum(1 for tgt in TARGETS
                    if grid[module]["cells"][f"rv20|{tgt:g}"]["delta_expR"] > 0)
        grid[module]["n_pos_targets"] = int(n_pos)
        grid[module]["direction_robust_5of7"] = bool(n_pos >= 5)
        c20 = grid[module]["cells"][f"rv20|{ANCHOR:g}"]
        print(f"  {module}: 基线 expR={base['expR']:.3f} PF={base['PF']:.2f} | "
              f"20%档 ΔexpR={c20['delta_expR']:+.4f} "
              f"CI[{c20['boot_ci_lo']:+.4f},{c20['boot_ci_hi']:+.4f}] "
              f"E均值{c20['mean_E']:.2f} 地板率{c20['share_E_floor']:.0%} "
              f"ret={c20['retention']} verdict={c20['verdict']}",
              flush=True)

    print("\n== Q2 模块非对称（F2）==", flush=True)
    f2: dict = {}
    for module in sorted(samples):
        s = samples[module]
        if not s["rs"].size:
            continue
        rv, rs = s["rv"], s["rs"]
        order = np.argsort(rv, kind="stable")
        n = order.size
        t1, t2, t3 = order[: n // 3], order[n // 3: 2 * n // 3], order[2 * n // 3:]
        terciles = {
            "n_low_mid_high": [int(t1.size), int(t2.size), int(t3.size)],
            "low_vol_mean_r": float(rs[t1].mean()),
            "mid_vol_mean_r": float(rs[t2].mean()),
            "high_vol_mean_r": float(rs[t3].mean()),
            "high_minus_low": float(rs[t3].mean() - rs[t1].mean()),
        }
        cell = grid[module]["cells"][f"rv20|{ANCHOR:g}"]
        try:
            from scipy.stats import spearmanr
            rho, pval = spearmanr(rv, rs)
            rho, pval = float(rho), float(pval)
        except Exception:  # noqa: BLE001
            rho = pval = None
        f2[module] = {
            "terciles": terciles,
            "spearman_rv20_r": rho, "spearman_p": pval,
            "median_rv20": float(np.median(rv)),
            "delta_expR": cell["delta_expR"],
            "boot_ci": [cell["boot_ci_lo"], cell["boot_ci_hi"]],
        }
        rho_s = "NA" if rho is None else f"{rho:+.3f}"
        print(f"  {module}: 高−低波组 Δr={terciles['high_minus_low']:+.3f}R "
              f"rho={rho_s} ΔexpR={cell['delta_expR']:+.4f} "
              f"CI[{cell['boot_ci_lo']:+.4f},{cell['boot_ci_hi']:+.4f}]",
              flush=True)

    a_cell = grid["A"]["cells"][f"rv20|{ANCHOR:g}"]
    c_cell = grid["C"]["cells"][f"rv20|{ANCHOR:g}"]
    a_j1 = bool(a_cell["boot_ci_lo"] is not None and a_cell["boot_ci_lo"] > 0)
    if a_j1 and c_cell["boot_ci_hi"] is not None \
            and c_cell["boot_ci_hi"] <= CI_C_EXCLUSION_UB:
        f2_verdict = "C 应排除于 vt（非对称成立）"
    elif c_cell["boot_ci_lo"] is not None and c_cell["boot_ci_lo"] > 0:
        f2_verdict = "C 同样适用 vt"
    else:
        f2_verdict = "不确定（CI 不支持任一方向）"

    results = {
        "protocol": {
            "task": "R2: K 全池 175 标的复验",
            "script": "docs/experiments/raw/vt_signal_sizing_full_pool/run_vt_signal_sizing_full_pool.py",
            "date": "2026-09-02",
            "targets": list(TARGETS), "anchor": ANCHOR,
            "estimators": list(ESTIMATORS),
            "E_formula": "clip(target/RV20_signal_date_close, 0.25, 1)",
            "boot": {"n": BOOT_N, "seed": BOOT_SEED},
            "retention_min": RETENTION_MIN, "pf_tolerance": PF_TOLERANCE,
            "g2": {"rate_tol": G2_RATE_TOL, "share_min": G2_SHARE_MIN,
                   "note": "本任务 G2 退化为健全性核对（与 8-25 池同源，预计≈0），不阻断主判定"},
            "g3_missing_max": G3_MISSING_MAX,
            "ci_c_exclusion_ub": CI_C_EXCLUSION_UB,
        },
        "anchor": anchor,
        "gates": {
            "G1_baseline": g1, "G1_pass": bool(g1_all),
            "G2_vintage_sanity": g2,
            "G2_pass_strict": all(v["pass_strict"] for v in g2.values()),
            "G2_note": "健全性核对，不作 FAIL 阻断",
            "G3_rv20": g3, "G3_pass": bool(g3_all),
            "all_pass_blocking": bool(g1_all and g3_all),
        },
        "g2_mismatch_trades": g2_mismatch,
        "g3_missing_trades": g3_missing_detail,
        "grid": grid,
        "f2": f2,
        "f2_verdict": f2_verdict,
        "red_line_self_check": (
            "仓位系数 E 的输入仅 (target, RV20/ewma97)；全程未使用 b50/b200/宽度/"
            "利率分位——与已判负 8 项（宽度/利率→仓位系数）自变量不同类。"),
    }
    payload = json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True,
                         default=float)
    out_path = HERE / "vt_signal_sizing_full_pool_results.json"
    out_path.write_text(payload, encoding="utf-8")
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()
    print(f"\n落盘: {out_path}")
    print(f"md5(canonical json) = {digest}")
    print(f"门槛: G1={g1_all} G2_sanity={all(v['pass_strict'] for v in g2.values())} G3={g3_all}")
    print(f"F2 判定: {f2_verdict}")

    if "--dump-hash" in sys.argv:
        print("HASH", digest)


if __name__ == "__main__":
    main()
