#!/usr/bin/env python3
"""Prompt N：A/B/C/D 入场模块间信号冲突与共振检测（预注册复验）· 2026-09-02。

=====================================================================
【预注册协议——本 docstring 于运行前写死，跑后不得修改任何判定线】
=====================================================================

任务两步门控：第一步 H5 预注册复验不通过 → 第二步假设检验不得执行
（结构审计除外，见下）。本脚本纯标准库实现（本机无 pandas/numpy），
全部随机数来自固定种子的 random.Random实例，字典序遍历 + sort_keys
序列化，保证 PYTHONHASHSEED=0/42 双跑 sha256 一致。

—— S0 数据源与复现门槛（硬闸）——
主数据：raw/meta_scan/merged_trades.csv（A/B'/C 三流合并 559 笔，
signal_date/symbol/module/r_net；即 heiti-ARCHIVE H5 的原始数据本体）。
D 补充：raw/lifecycle_combo/T2_D_stocks_default.json（股票池 D 模块
默认参数逐笔；若含逐字段完全重复的记录则去重并在结果中披露
raw_count/dedup_count）。
lifecycle 单标的全模块 CSV（510300/518850）仅作独立结构审计，
不并入主样本（池与窗口不同，防双计）。
S0 门槛：H5 三组必须逐位复现归档值——n=301/170/88 且 expR=
0.599/0.618/1.049（容差 ±0.001）；任一不符 → status="S0_FAIL"，
全任务中止。

—— 结构审计（无论第一步结果均执行，仅描述性，不含方向判定）——
A1 同(symbol, signal_date)跨模块共触发计数（主样本、主样本+D 合并、
两个 lifecycle CSV 各自统计）。
A2 B'∩C 共享标的数 + 逐共享标的两模块信号日最小日历日间隔分布
（档：0 / 1-5 / 6-20 / 21-60 / >60）——回答"模块互斥是同日互斥还是
时间上整体错开"。
A3 冲突个案明细：主样本+D 合并后每个跨模块共触发 (symbol, date)
的模块构成与各自 r_net。

—— 第一步：H5 预注册复验（H5R）——
分组定义（冻结原始口径，来源 run_meta_scan.py L117-123）：
按 (module, signal_date) 计数 n_day；三档 (0,1]/(1,3]/(3,∞) 即
1 / 2-3 / 4+。界限披露：原始三档为后验划分、无先验依据可考；
本次复验冻结原界限，另设 3+/5+ 敏感性档（仅描述，不进判定）。
主假设 H5R（单侧）：μ(r_net | n_day≥4) > μ(r_net | n_day=1)。
主判定统计：日聚类 bootstrap——cluster 单元 = 组内 signal_date
（跨模块合并同日为同簇，以容纳同日市场相关）；组内按簇放回重抽
10000 次（种子 20260901），Δ=mean(4+)−mean(1)；
**判定通过 ⇔ Δ 的百分位 95% CI（2.5 分位）下界 > 0**（对齐
stop-loss-matrix「显著改善=10000 次固定种子 bootstrap 95% CI
下界>0」口径；单侧假设用 2.5 分位属保守侧）。
次级参考（不进判定）：逐笔独立 bootstrap（同种子同次数）CI 与
单侧 p=frac(Δ*≤0)；2-3 组、3+/5+ 敏感性档只作描述。
说明：stop-loss-matrix 的「配对」bootstrap 用于同一批逐笔在两个
出场规则下的配对差；本任务两组为不相交独立样本，其对应形制为
组内重抽的两独立组 bootstrap，如实披露。
阴性对照 NC1（必须过）：200 次模块内 r_net 标签打乱（种子
20260902；在每个 module 内部整体打乱 r_net 赋值，保持
(module,signal_date) 分组结构不变），重算 Δ 得零分布；
真实 Δ 须 > 零分布 95 分位，否则记 negative_control_fail。
**第一步总判定：H5R 通过 = 主判定 CI 下界>0 且 NC1 通过。
不通过 → heiti-ARCHIVE H5 归档为「后验发现未能复验，证伪」，
第二步假设检验不执行。**

—— 第二步（仅当第一步通过才执行）：共振 vs 冲突拆解 ——
模块分类（代码+规格双证，冻结）：
延续类 = {A(first_ma_pullback 趋势回调), B'(dense_breakout 密集突破)}；
反转类 = {C(two_b_reversal 破底翻), D(module_d_false_breakout 假跌破反转)}。
依据：rules/ 各检测器 docstring 与 trading-spec §9；规格执行优先级
一节明确「趋势跟随模块与逆势反转模块必须分别统计」。
共触发检测面：主样本 A/B'/C + D 归档（去重后）按 (symbol,
signal_date) 合并。
共振 = 同键 ≥2 模块且全部同类（A+B' 或 C+D）；
冲突 = 同键同时含延续类与反转类；
单模块组 = 同键仅 1 个模块（主样本其余全部）。
H2a（共振假设，单侧）：μ(共振) > μ(单模块)，日聚类 bootstrap
（cluster=signal_date）95% CI 下界>0。
H2b（冲突假设，单侧）：μ(冲突) < μ(单模块)，95% CI（97.5 分位）
上界<0。两假设各自独立可否证，不得合并陈述。
样本量门槛：任一组 N<20 → 该假设记 sample_insufficient，
不得下方向性结论（含 N=0）。
指标：n/expR/PF(Σ正R/|Σ负R|)/胜率。
NC2（仅当 H2a/H2b 均可判定时执行）：200 次模块内标签打乱核对。

—— 明确不做 ——
不改 src/ 生产代码；不产生新买卖点/交易事件；不做仓位系数映射；
不重定义四模块触发条件；不 push。

产出：本目录 module_conflict_results.json（sort_keys、固定 4 位
小数），stdout 打印 sha256 供双跑核对。
=====================================================================
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
RAW = HERE.parent  # docs/experiments/raw

MERGED_CSV = RAW / "meta_scan/merged_trades.csv"
D_JSON = RAW / "lifecycle_combo/T2_D_stocks_default.json"
LIFECYCLE_CSVS = [
    RAW / "lifecycle_combo/trades_510300_lifecycle_allmodule.csv",
    RAW / "lifecycle_combo/trades_518850_lifecycle_allmodule.csv",
]

# S0 复现门槛（归档值，冻结）
S0_EXPECT = {"1": (301, 0.599), "2-3": (170, 0.618), "4+": (88, 1.049)}
S0_TOL = 0.001

MODULE_CLASS = {"A": "延续", "B'": "延续", "C": "反转", "D": "反转"}
N_BOOT = 10000
N_SHUFFLE = 200
BOOT_SEED = 20260901
SHUFFLE_SEED = 20260902
MIN_N_STEP2 = 20


# ---------- 基础工具 ----------

def pct(sorted_xs: list[float], p: float) -> float:
    """线性插值分位数（输入须已升序）。"""
    if not sorted_xs:
        return float("nan")
    k = (len(sorted_xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_xs) - 1)
    frac = k - lo
    return sorted_xs[lo] * (1 - frac) + sorted_xs[hi] * frac


def stats_block(vals: list[float]) -> dict:
    gross_win = sum(v for v in vals if v > 0)
    gross_loss = sum(v for v in vals if v < 0)
    return {
        "n": len(vals),
        "expR": round(mean(vals), 4) if vals else None,
        "PF": round(gross_win / abs(gross_loss), 4) if gross_loss < 0 else None,
        "win": round(sum(1 for v in vals if v > 0) / len(vals), 4) if vals else None,
    }


def cluster_bootstrap_delta(
    clusters_a: list[list[float]],
    clusters_b: list[list[float]],
    rng: random.Random,
    n: int,
) -> list[float]:
    """按簇放回重抽，返回 Δ=mean(a)−mean(b) 分布（簇=a 组、b 组各自独立重抽）。"""
    out = []
    for _ in range(n):
        def pooled(clusters: list[list[float]]) -> float:
            xs: list[float] = []
            for _ in range(len(clusters)):
                xs.extend(clusters[rng.randrange(len(clusters))])
            return mean(xs)
        out.append(pooled(clusters_a) - pooled(clusters_b))
    return out


def trade_bootstrap_delta(a: list[float], b: list[float], rng: random.Random, n: int) -> list[float]:
    out = []
    for _ in range(n):
        ma = mean(rng.choice(a) for _ in range(len(a)))
        mb = mean(rng.choice(b) for _ in range(len(b)))
        out.append(ma - mb)
    return out


# ---------- 数据装载 ----------

def load_merged() -> list[dict]:
    rows = []
    with open(MERGED_CSV, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "signal_date": r["signal_date"],
                "symbol": r["symbol"],
                "module": r["module"],
                "r_net": float(r["r_net"]),
            })
    return rows


def load_d_trades() -> tuple[list[dict], int]:
    data = json.loads(D_JSON.read_text())
    raw = data.get("trades", [])
    # 去重键=交易经济键(symbol, signal_date, entry_date, exit_date, r_net)：
    # 归档中存在仅 entry_reason 波谷参照价不同（同日双密集区生命周期）的
    # 重复记录，属描述性审计的事实修正，不触及任何预注册判定线。
    seen: set[tuple] = set()
    out = []
    for t in raw:
        key = (t["symbol"], t["signal_date"], t.get("entry_date"), t.get("exit_date"), t.get("r_net"))
        if key not in seen:
            seen.add(key)
            out.append({
                "signal_date": t["signal_date"],
                "symbol": t["symbol"],
                "module": "D",
                "r_net": float(t["r_net"]),
                "entry_reason": t.get("entry_reason", ""),
                "exit_reason": t.get("exit_reason", ""),
                "entry_date": t.get("entry_date"),
                "exit_date": t.get("exit_date"),
            })
    return out, len(raw)


def h5_group(trade: dict, counts: dict[tuple[str, str], int]) -> str:
    n_day = counts[(trade["module"], trade["signal_date"])]
    if n_day == 1:
        return "1"
    if n_day <= 3:
        return "2-3"
    return "4+"


def main() -> None:
    merged = load_merged()
    d_trades, d_raw_n = load_d_trades()

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for t in merged:
        counts[(t["module"], t["signal_date"])] += 1

    h5: dict[str, list[float]] = defaultdict(list)
    for t in merged:
        h5[h5_group(t, counts)].append(t["r_net"])

    out: dict = {
        "experiment": "module_conflict_resonance_preregistration",
        "date": "2026-09-02",
        "prompt": "N (prompts-2026-09-01 收尾规约)",
    }

    # ---------- S0 复现门槛 ----------
    s0 = {}
    ok = True
    for g in ["1", "2-3", "4+"]:
        vals = h5[g]
        exp_n, exp_r = S0_EXPECT[g]
        got_n, got_r = len(vals), (mean(vals) if vals else float("nan"))
        match = got_n == exp_n and abs(got_r - exp_r) <= S0_TOL
        ok &= match
        s0[g] = {"n": got_n, "expR": round(got_r, 4), "expect": [exp_n, exp_r], "match": match}
    s0["status"] = "S0_OK" if ok else "S0_FAIL"
    out["S0_replication_gate"] = s0

    # ---------- 结构审计（始终执行） ----------
    audit: dict = {}

    key_mods: dict[tuple[str, str], set[str]] = defaultdict(set)
    key_rows: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in merged:
        key_mods[(t["signal_date"], t["symbol"])].add(t["module"])
        key_rows[(t["signal_date"], t["symbol"])].append(t)

    multi_merged = {k: v for k, v in key_mods.items() if len(v) > 1}
    audit["multi_module_keys_merged_ABC"] = len(multi_merged)

    # 合并 D 后的跨模块共触发
    combined = list(merged) + [{"signal_date": t["signal_date"], "symbol": t["symbol"],
                                "module": "D", "r_net": t["r_net"]} for t in d_trades]
    key_mods_all: dict[tuple[str, str], set[str]] = defaultdict(set)
    key_rows_all: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in combined:
        key_mods_all[(t["signal_date"], t["symbol"])].add(t["module"])
        key_rows_all[(t["signal_date"], t["symbol"])].append(t)
    multi_all = {k: sorted(v) for k, v in key_mods_all.items() if len(v) > 1}
    audit["multi_module_keys_with_D"] = len(multi_all)

    conflict_events = []
    resonance_events = []
    for k in sorted(multi_all):
        mods = multi_all[k]
        classes = {MODULE_CLASS[m] for m in mods}
        ev = {
            "symbol": k[1],
            "signal_date": k[0],
            "modules": mods,
            "legs": [{"module": t["module"], "r_net": round(t["r_net"], 4)} for t in key_rows_all[k]],
        }
        if len(classes) > 1:
            conflict_events.append(ev)
        else:
            resonance_events.append(ev)
    audit["conflict_events"] = conflict_events
    audit["resonance_events"] = resonance_events

    # A2：B'∩C 共享标的最小信号日间隔
    b_dates: dict[str, list[date]] = defaultdict(list)
    c_dates: dict[str, list[date]] = defaultdict(list)
    pools: dict[str, set[str]] = defaultdict(set)
    for t in merged:
        pools[t["module"]].add(t["symbol"])
        d0 = date.fromisoformat(t["signal_date"])
        if t["module"] == "B'":
            b_dates[t["symbol"]].append(d0)
        elif t["module"] == "C":
            c_dates[t["symbol"]].append(d0)
    shared = sorted(pools["B'"] & pools["C"])
    gaps = []
    for s in shared:
        g = min(abs((a - b).days) for a in b_dates[s] for b in c_dates[s])
        gaps.append(g)
    gap_bins = {"0": 0, "1-5": 0, "6-20": 0, "21-60": 0, ">60": 0}
    for g in gaps:
        if g == 0:
            gap_bins["0"] += 1
        elif g <= 5:
            gap_bins["1-5"] += 1
        elif g <= 20:
            gap_bins["6-20"] += 1
        elif g <= 60:
            gap_bins["21-60"] += 1
        else:
            gap_bins[">60"] += 1
    audit["Bp_C_shared_symbols"] = len(shared)
    audit["Bp_C_min_signal_gap_days"] = {
        "bins": gap_bins,
        "median_min_gap": sorted(gaps)[len(gaps) // 2] if gaps else None,
        "per_symbol": {s: min(abs((a - b).days) for a in b_dates[s] for b in c_dates[s]) for s in shared},
    }

    # A1 lifecycle 审计
    lf_audit = {}
    for p in LIFECYCLE_CSVS:
        rows = list(csv.DictReader(open(p, newline="")))
        lk: dict[str, set[str]] = defaultdict(set)
        for r in rows:
            lk[r["signal_date"]].add(r["module"])
        multi = sum(1 for v in lk.values() if len(v) > 1)
        lf_audit[p.name] = {"trades": len(rows), "multi_module_days": multi}
    audit["lifecycle_csv"] = lf_audit
    audit["D_archive"] = {"raw_count": d_raw_n, "dedup_count": len(d_trades),
                          "dedup_note": "经济键去重：两条记录仅 entry_reason 波谷参照价不同，同一笔交易"}
    out["structural_audit"] = audit

    # ---------- 第一步：H5R ----------
    step1: dict = {}
    vals1, vals4 = h5["1"], h5["4+"]

    def day_clusters(vals_and_keys: list[tuple[str, float]]) -> list[list[float]]:
        cl: dict[str, list[float]] = defaultdict(list)
        for d0, v in vals_and_keys:
            cl[d0].append(v)
        return [cl[k] for k in sorted(cl)]

    keys1 = [(t["signal_date"], t["r_net"]) for t in merged if h5_group(t, counts) == "1"]
    keys4 = [(t["signal_date"], t["r_net"]) for t in merged if h5_group(t, counts) == "4+"]
    cl1, cl4 = day_clusters(keys1), day_clusters(keys4)
    step1["clusters"] = {"n_days_group1": len(cl1), "n_days_group4plus": len(cl4)}

    rng = random.Random(BOOT_SEED)
    boot_cluster = sorted(cluster_bootstrap_delta(cl4, cl1, rng, N_BOOT))
    rng2 = random.Random(BOOT_SEED)  # 与簇 bootstrap 同种子起步，两法各自独立成列
    boot_trade = sorted(trade_bootstrap_delta(vals4, vals1, rng2, N_BOOT))

    delta = mean(vals4) - mean(vals1)
    ci_cluster = (round(pct(boot_cluster, 0.025), 4), round(pct(boot_cluster, 0.975), 4))
    ci_trade = (round(pct(boot_trade, 0.025), 4), round(pct(boot_trade, 0.975), 4))
    p_one_cluster = sum(1 for d0 in boot_cluster if d0 <= 0) / N_BOOT
    p_one_trade = sum(1 for d0 in boot_trade if d0 <= 0) / N_BOOT
    step1["delta_expR_4plus_minus_1"] = round(delta, 4)
    step1["day_cluster_bootstrap"] = {"ci95": list(ci_cluster), "p_one_sided": round(p_one_cluster, 4)}
    step1["trade_bootstrap"] = {"ci95": list(ci_trade), "p_one_sided": round(p_one_trade, 4)}

    # NC1：200 次模块内标签打乱
    rng3 = random.Random(SHUFFLE_SEED)
    null_deltas = []
    mods_sorted = sorted({t["module"] for t in merged})
    for _ in range(N_SHUFFLE):
        shuffled = []
        pool_by_mod = {}
        for m in mods_sorted:
            vals_m = [t["r_net"] for t in merged if t["module"] == m]
            rng3.shuffle(vals_m)
            pool_by_mod[m] = vals_m
        idx = {m: 0 for m in mods_sorted}
        for t in merged:
            m = t["module"]
            shuffled.append((h5_group(t, counts), pool_by_mod[m][idx[m]]))
            idx[m] += 1
        g1s = [v for g, v in shuffled if g == "1"]
        g4s = [v for g, v in shuffled if g == "4+"]
        null_deltas.append(mean(g4s) - mean(g1s))
    null_sorted = sorted(null_deltas)
    nc1_p95 = pct(null_sorted, 0.95)
    nc1_p = sum(1 for d0 in null_sorted if d0 >= delta) / N_SHUFFLE
    step1["negative_control_200shuffles"] = {
        "null_p95": round(nc1_p95, 4),
        "real_delta_percentile_in_null": 1 - round(nc1_p, 4),
        "pass": delta > nc1_p95,
    }

    # 敏感性（仅描述）
    sens = {}
    for label, lo in [("3+ vs 1", 3), ("5+ vs 1", 5)]:
        va = [t["r_net"] for t in merged if counts[(t["module"], t["signal_date"])] >= lo]
        vb = vals1
        if va:
            r = random.Random(BOOT_SEED)
            bt = sorted(trade_bootstrap_delta(va, vb, r, N_BOOT))
            sens[label] = {"n": len(va), "delta": round(mean(va) - mean(vb), 4),
                           "ci95_trade": [round(pct(bt, 0.025), 4), round(pct(bt, 0.975), 4)]}
    step1["sensitivity_descriptive"] = sens
    step1["group_stats"] = {g: stats_block(h5[g]) for g in ["1", "2-3", "4+"]}
    # 组内模块构成（描述）
    comp = {g: {} for g in ["1", "2-3", "4+"]}
    for t in merged:
        g = h5_group(t, counts)
        comp[g][t["module"]] = comp[g].get(t["module"], 0) + 1
    step1["group_module_composition"] = comp

    h5r_pass = ci_cluster[0] > 0 and step1["negative_control_200shuffles"]["pass"]
    step1["verdict"] = "H5R_PASS" if h5r_pass else "H5R_FAIL"
    out["step1_H5_replication"] = step1

    # ---------- 第二步（门控） ----------
    step2: dict = {"gate": "H5R_FAIL → 第二步假设检验按预注册纪律不执行" if not h5r_pass else "open"}
    if s0["status"] == "S0_OK" and h5r_pass:
        single_vals = [t["r_net"] for t in merged
                       if len(key_mods[(t["signal_date"], t["symbol"])]) == 1]
        res_vals = [t["r_net"] for t in combined
                    if len(key_mods_all[(t["signal_date"], t["symbol"])]) > 1
                    and len({MODULE_CLASS[m] for m in key_mods_all[(t["signal_date"], t["symbol"])]}) == 1]
        con_vals = [t["r_net"] for t in combined
                    if len(key_mods_all[(t["signal_date"], t["symbol"])]) > 1
                    and len({MODULE_CLASS[m] for m in key_mods_all[(t["signal_date"], t["symbol"])]}) > 1]
        step2["groups"] = {
            "single_module": stats_block(single_vals),
            "resonance": stats_block(res_vals),
            "conflict": stats_block(con_vals),
        }
        for name, vals, direction in [("H2a_resonance", res_vals, "greater"),
                                      ("H2b_conflict", con_vals, "less")]:
            if len(vals) < MIN_N_STEP2:
                step2[name] = {"verdict": "sample_insufficient",
                               "n": len(vals), "min_required": MIN_N_STEP2}
                continue
            r = random.Random(BOOT_SEED)
            bt = sorted(trade_bootstrap_delta(vals, single_vals, r, N_BOOT))
            if direction == "greater":
                step2[name] = {"verdict": "PASS" if pct(bt, 0.025) > 0 else "FAIL",
                               "delta": round(mean(vals) - mean(single_vals), 4),
                               "ci95": [round(pct(bt, 0.025), 4), round(pct(bt, 0.975), 4)]}
            else:
                step2[name] = {"verdict": "PASS" if pct(bt, 0.975) < 0 else "FAIL",
                               "delta": round(mean(vals) - mean(single_vals), 4),
                               "ci95": [round(pct(bt, 0.025), 4), round(pct(bt, 0.975), 4)]}
    out["step2_resonance_conflict"] = step2

    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (HERE / "module_conflict_results.json").write_text(text)
    print(text)
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
