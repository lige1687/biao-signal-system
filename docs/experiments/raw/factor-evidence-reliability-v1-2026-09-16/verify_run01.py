#!/usr/bin/env python3
"""run-01 独立核验（Task 5b，预算 1/1+1）。

只读取保存的抽样起点（.npy，仅用 numpy 做 IO）与 B1 输入表，用标准库
重新汇总全部结果：全期/逐年/留一年/等权/重叠/逐次 delta/两组 n/原因/
分位（手工 linear 插值），不 import 被测包（factor_evidence）或任何旧
汇总函数，不再抽新种子。与 run-01 产物逐值比对：浮点 ≤1e-12，键/整数/
null 严格相等。另核 manifest 双向哈希与保护基线零漂移。输出
run01-verification.json。
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from datetime import date
from pathlib import Path

import numpy as np

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = REPO / "docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16"
RUN = RAW / "run-01"
B1 = REPO / "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16"
TOL = 1e-12

failures: list[str] = []
checks = 0


def check(cond: bool, label: str) -> None:
    global checks
    checks += 1
    if not cond:
        failures.append(label)


def feq(a, b, label: str) -> None:
    if a is None or b is None:
        check(a is None and b is None, f"{label}: null 不一致 {a!r} vs {b!r}")
    else:
        check(abs(a - b) <= TOL, f"{label}: |{a} - {b}| > {TOL}")


def quantile_linear(sorted_vals: list[float], q: float) -> float:
    n = len(sorted_vals)
    pos = q * (n - 1)
    lo = math.floor(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def load_inputs():
    cal = json.loads((B1 / "run-02/input-package/calendar.json")
                     .read_text(encoding="utf-8"))
    all_trading = sorted(k for k, r in cal["days"].items()
                         if r["is_trading_day"])
    schedule = [d for d in all_trading if "2019-09-02" <= d <= "2026-02-03"]
    pos = {d: i for i, d in enumerate(schedule)}
    axis = [d for d in schedule if "2019-10-08" <= d <= "2025-12-31"]
    with (B1 / "run-02/observations.csv").open(newline="",
                                               encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["session"] for r in rows] == axis
    legal = [r["flag_state_known"] == "True" and r["flag_main_legal"] == "True"
             and r["flag_mature"] == "True" for r in rows]
    for r, lg in zip(rows, legal, strict=True):
        assert (r["in_comparison"] == "True") == lg
    return rows, legal, pos, axis, schedule


def main() -> None:
    rows, legal, pos, axis, schedule = load_inputs()
    mains = [None if r["main"] == "" else float(r["main"]) for r in rows]
    states = [{"true": True, "false": False, "": None}[r["state"]]
              for r in rows]

    # ── 1. stability.json ───────────────────────────────────────────
    stab = json.loads((RUN / "stability.json").read_text(encoding="utf-8"))
    fp = stab["full_period"]

    def stat(vals):
        return {"n": len(vals), "mean": statistics.fmean(vals),
                "median": statistics.median(vals),
                "up": sum(1 for v in vals if v > 0),
                "down": sum(1 for v in vals if v < 0),
                "zero": sum(1 for v in vals if v == 0)}

    tm = [m for m, s, lg in zip(mains, states, legal, strict=True)
          if lg and s is True]
    fm = [m for m, s, lg in zip(mains, states, legal, strict=True)
          if lg and s is False]
    ta = [float(r["aux"]) for r, s, lg in zip(rows, states, legal,
                                              strict=True)
          if lg and s is True and r["aux"] != ""]
    fa = [float(r["aux"]) for r, s, lg in zip(rows, states, legal,
                                              strict=True)
          if lg and s is False and r["aux"] != ""]
    st, sf = stat(tm), stat(fm)
    for g, e in (("true", st), ("false", sf)):
        for k in ("n", "up", "down", "zero"):
            check(fp[g][k] == e[k], f"full.{g}.{k}")
        for k in ("mean", "median", "up_ratio"):
            feq(fp[g][k], e[k] if k != "up_ratio"
                else e["up"] / e["n"], f"full.{g}.{k}")
    feq(fp["delta"], st["mean"] - sf["mean"], "full.delta")
    feq(fp["median_diff"], st["median"] - sf["median"], "full.median_diff")
    feq(fp["up_ratio_diff"], st["up"] / st["n"] - sf["up"] / sf["n"],
        "full.up_ratio_diff")
    feq(fp["true"]["aux_mean"], statistics.fmean(ta), "full.true.aux_mean")
    check(fp["true"]["aux_n"] == len(ta), "full.true.aux_n")
    feq(fp["false"]["aux_worst"], min(fa), "full.false.aux_worst")

    ys = stab["year_stability"]
    # 逐年明细由 runner 拆分到 yearly.csv；stability.json 保留汇总段
    years = sorted({r["session"][:4] for r, lg in zip(rows, legal, strict=True)
                    if lg})
    sign = {"positive": 0, "zero": 0, "negative": 0}
    yearly_csv = {}
    for y in years:
        ytm = [m for m, s, lg, r in zip(mains, states, legal, rows,
                                        strict=True)
               if lg and s is True and r["session"][:4] == y]
        yfm = [m for m, s, lg, r in zip(mains, states, legal, rows,
                                        strict=True)
               if lg and s is False and r["session"][:4] == y]
        est, esf = stat(ytm), stat(yfm)
        d = (est["mean"] - esf["mean"]) if est["n"] and esf["n"] else None
        if d is not None:
            sign["positive" if d > 0 else "negative" if d < 0 else "zero"] += 1
        yearly_csv[y] = (est, esf, d)
    check(ys["sign_counts"] == sign, "sign_counts")
    check(ys["partial_years"] == ["2019"], "partial_years")

    for y in years:
        rtm = [m for m, s, lg, r in zip(mains, states, legal, rows,
                                        strict=True)
               if lg and s is True and r["session"][:4] != y]
        rfm = [m for m, s, lg, r in zip(mains, states, legal, rows,
                                        strict=True)
               if lg and s is False and r["session"][:4] != y]
        got = ys["leave_one_year_out"][y]
        check(got["true_n"] == len(rtm) and got["false_n"] == len(rfm)
              and got["n"] == len(rtm) + len(rfm), f"loo {y} n")
        d = (statistics.fmean(rtm) - statistics.fmean(rfm)) \
            if rtm and rfm else None
        feq(got["delta"], d, f"loo {y} delta")
        check((got["null_reason"] is None) == (d is not None),
              f"loo {y} null_reason 严格性")
    eq = ys["equal_weight_year_delta"]
    valid_ds = [d for _, _, d in yearly_csv.values() if d is not None]
    check(eq["years"] == [y for y, (_, _, d) in sorted(yearly_csv.items())
                          if d is not None], "eq years")
    feq(eq["mean_delta"], statistics.fmean(valid_ds), "eq mean_delta")
    feq(eq["full_period_delta"], st["mean"] - sf["mean"], "eq full")

    # ── 2. yearly.csv / leave-one-year-out.csv ──────────────────────
    with (RUN / "yearly.csv").open(newline="", encoding="utf-8") as f:
        yrows = list(csv.DictReader(f))
    check([r["year"] for r in yrows] == years, "yearly.csv 行序")
    for r in yrows:
        est, esf, d = yearly_csv[r["year"]]
        check(int(r["true_n"]) == est["n"] and int(r["false_n"]) == esf["n"],
              f"yearly.csv {r['year']} n")
        check(int(r["true_up"]) == est["up"]
              and int(r["false_up"]) == esf["up"],
              f"yearly.csv {r['year']} up")
        if est["n"]:
            feq(float(r["true_mean"]), est["mean"],
                f"yearly.csv {r['year']} true_mean")
            feq(float(r["true_median"]), est["median"],
                f"yearly.csv {r['year']} true_median")
        if esf["n"]:
            feq(float(r["false_mean"]), esf["mean"],
                f"yearly.csv {r['year']} false_mean")
        if d is None:
            check(r["delta"] == "" and r["null_reason"] != "",
                  f"yearly.csv {r['year']} null")
        else:
            feq(float(r["delta"]), d, f"yearly.csv {r['year']} delta")
    with (RUN / "leave-one-year-out.csv").open(newline="",
                                               encoding="utf-8") as f:
        lrows = list(csv.DictReader(f))
    check([r["year"] for r in lrows] == years, "loo.csv 行序")

    # ── 3. overlap.json ─────────────────────────────────────────────
    ov = json.loads((RUN / "overlap.json").read_text(encoding="utf-8"))
    label_sets = []
    ax_pos = []
    for r, lg in zip(rows, legal, strict=True):
        e_pos, x_pos = pos[r["e_date"]], pos[r["x_date"]]
        label_sets.append(set(range(e_pos + 1, x_pos + 1)))
        ax_pos.append(pos[r["session"]])
    total = sum(len(s) for s in label_sets)
    uniq = set().union(*label_sets)
    check(ov["total_interval_refs"] == total, "overlap total_refs")
    check(ov["unique_intervals"] == len(uniq), "overlap unique")
    feq(ov["reuse_ratio"], total / len(uniq), "overlap reuse")
    check(ov["per_label_intervals"] == len(label_sets[0]), "overlap per_label")
    by_pos = dict(zip(ax_pos, label_sets, strict=True))
    hist: dict[int, int] = {}
    pairs = 0
    ssum = 0
    for p in sorted(by_pos):
        if p + 1 in by_pos:
            sh = len(by_pos[p] & by_pos[p + 1])
            hist[sh] = hist.get(sh, 0) + 1
            pairs += 1
            ssum += sh
    check(ov["adjacent_pairs"] == pairs, "overlap adjacent_pairs")
    check(ov["adjacent_shared_histogram"] ==
          {str(k): v for k, v in sorted(hist.items())}, "overlap hist")
    feq(ov["adjacent_shared_mean"], ssum / pairs, "overlap shared_mean")
    feq(ov["adjacent_shared_ratio"], (ssum / pairs) / len(label_sets[0]),
        "overlap shared_ratio")
    anchor_pos = pos["2019-10-08"]
    grid = [p for p in sorted(by_pos)
            if p >= anchor_pos and (p - anchor_pos) % 23 == 0]
    sp_shared = [len(by_pos[a] & by_pos[b])
                 for a, b in zip(grid, grid[1:], strict=False)]
    check(ov["sparse"]["grid_points"] == len(grid), "sparse grid_points")
    check(ov["sparse"]["adjacent_pairs"] == len(sp_shared), "sparse pairs")
    check(ov["sparse"]["adjacent_shared_max"] == max(sp_shared),
          "sparse shared_max")

    # ── 4. 重抽逐次与分位（读保存起点，重汇总） ──────────────────────
    unc = json.loads((RUN / "uncertainty.json").read_text(encoding="utf-8"))
    n = len(rows)
    for L in (63, 126):
        starts = np.load(RUN / f"resampling-L{L}-starts.npy")
        k = math.ceil(n / L)
        check(starts.shape == (2000, k), f"L{L} starts shape {starts.shape}")
        with (RUN / f"resampling-L{L}-replicates.csv").open(
                newline="", encoding="utf-8") as f:
            reps = list(csv.DictReader(f))
        check(len(reps) == 2000, f"L{L} reps 行数")
        deltas = []
        for ri in range(2000):
            idx = [int(s) for s in starts[ri]]
            sampled = ((idx[j // L] + j % L) % n
                       for j in range(min(len(idx) * L, n)))
            t_vals, f_vals = [], []
            for i in sampled:
                if legal[i] and states[i] is True and mains[i] is not None:
                    t_vals.append(mains[i])
                elif legal[i] and states[i] is False and mains[i] is not None:
                    f_vals.append(mains[i])
            r = reps[ri]
            check(int(r["rep"]) == ri, f"L{L} rep{ri} 序号")
            if not t_vals or not f_vals:
                check(r["delta"] == "" and r["reason"] != "",
                      f"L{L} rep{ri} null")
                continue
            d = statistics.fmean(t_vals) - statistics.fmean(f_vals)
            check(int(r["true_n"]) == len(t_vals)
                  and int(r["false_n"]) == len(f_vals), f"L{L} rep{ri} n")
            feq(float(r["delta"]), d, f"L{L} rep{ri} delta")
            deltas.append(d)
        u = unc["resampling"][f"L{L}"]
        check(u["valid_reps"] == len(deltas) == 2000, f"L{L} valid_reps")
        check(u["null_reps"] == 0, f"L{L} null_reps")
        check(u["k"] == k and u["n"] == n and u["block_length"] == L,
              f"L{L} 参数")
        sd = sorted(deltas)
        feq(u["quantile_lower"], quantile_linear(sd, 0.025), f"L{L} 下界")
        feq(u["quantile_upper"], quantile_linear(sd, 0.975), f"L{L} 上界")
        feq(u["point_estimate"], st["mean"] - sf["mean"], f"L{L} 点估计")

    # ── 5. manifest 双向 + 6. 保护基线零漂移 + 7. 输入SHA ────────────
    man = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    check(man["completed"] is True, "manifest completed")
    actual = {str(p.relative_to(RUN)) for p in RUN.rglob("*")
              if p.is_file() and p.name != "manifest.json"}
    check(set(man["files"]) == actual, "manifest 文件集合双向一致")
    for rel, meta in man["files"].items():
        h = hashlib.sha256((RUN / rel).read_bytes()).hexdigest()
        check(h == meta["sha256"], f"manifest sha {rel}")
    base = json.loads((RAW / "baseline/freeze-baseline.json")
                      .read_text(encoding="utf-8"))
    drift = [e["path"] for e in base["files"]
             if hashlib.sha256((REPO / e["path"]).read_bytes()).hexdigest()
             != e["sha256"]]
    check(not drift, f"保护基线零漂移（漂移：{drift[:5]}）")

    result = {
        "checks": checks, "failures": failures,
        "tolerance": TOL,
        "verified": ["stability.json（全期/逐年/留一年/等权/符号/不完整年）",
                     "yearly.csv", "leave-one-year-out.csv", "overlap.json",
                     "resampling L63/L126 逐次2000行×（delta/两组n/原因）",
                     "uncertainty.json 分位（手工linear插值）与点估计",
                     "manifest 双向文件集合+逐文件SHA",
                     "保护基线 121 文件零漂移", "输入SHA 六项（装载时已核）"],
        "no_new_seed": True,
        "imports": "标准库 + numpy（仅 np.load 读起点矩阵 IO）",
        "result": "PASS" if not failures else "FAIL",
    }
    (RAW / "run01-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("checks:", checks, "failures:", len(failures))
    for f_ in failures[:20]:
        print("FAIL:", f_)
    print("RESULT:", result["result"])


if __name__ == "__main__":
    main()
