#!/usr/bin/env python3
"""因子证据可靠性 v1：独立期望脚本（Task 1 交付，纯标准库）。

目的：不 import 新被测包 ``lei_signal.research.factor_evidence``、不 import 旧
汇总函数（description_core/state_description 等），只用 Python 标准库从
B1 已封存 ``observations.csv`` 与 ``calendar.json`` 独立推导全部关键统计，
输出 ``expectations.json`` 供测试与 Task 5 独立核验对账。

已知全期 1516/590/926 仅作交叉检查，不替代日期与合法集合推导：
观察日轴、合法集合、逐年分组全部从日历与 CSV 标志重新推导。
"""
from __future__ import annotations

import csv
import json
import statistics
from datetime import date
from pathlib import Path

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
B1 = REPO / "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16"
OBS_CSV = B1 / "run-02/observations.csv"
CAL_JSON = B1 / "run-02/input-package/calendar.json"
OUT = REPO / "docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/expectations.json"

WINDOW_START, WINDOW_END = "2019-10-08", "2025-12-31"
COVERAGE_START, COVERAGE_END = "2019-09-02", "2026-02-03"
E_OFFSET, X_OFFSET = 1, 22
SPARSE_ANCHOR, SPARSE_STEP = "2019-10-08", 23


def _strict_date(text: str) -> date:
    d = date.fromisoformat(text)
    assert text == d.isoformat(), f"日期非严格YYYY-MM-DD：{text!r}"
    return d


def main() -> None:
    # ── 日历：推导完整交易日轴与评价窗轴 ──────────────────────────────
    cal = json.loads(CAL_JSON.read_text(encoding="utf-8"))
    days = cal["days"]
    all_trading = sorted(k for k, rec in days.items() if rec["is_trading_day"])
    schedule = [d for d in all_trading if COVERAGE_START <= d <= COVERAGE_END]
    axis = [d for d in schedule if WINDOW_START <= d <= WINDOW_END]
    pos = {d: i for i, d in enumerate(schedule)}
    axis_pos = {d: i for i, d in enumerate(axis)}

    # ── 观察表：严格解析 ──────────────────────────────────────────────
    with OBS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        raw = list(reader)
    assert header == ["session", "state", "e_date", "x_date", "main", "aux",
                      "mature", "reason", "flag_state_known", "flag_main_legal",
                      "flag_mature", "in_comparison", "primary_exclusion"], header
    rows = []
    for r in raw:
        assert len(r) == 13, r
        rec = dict(zip(header, r, strict=True))
        state_txt = rec["state"]
        assert state_txt in ("true", "false", ""), rec
        for flag in ("flag_state_known", "flag_main_legal", "flag_mature",
                     "in_comparison"):
            assert rec[flag] in ("True", "False", ""), rec
        main_txt, aux_txt = rec["main"], rec["aux"]
        main = None if main_txt == "" else float(main_txt)
        aux = None if aux_txt == "" else float(aux_txt)
        if main is not None:
            assert main == main and abs(main) != float("inf"), rec
        if aux is not None:
            assert aux == aux and abs(aux) != float("inf"), rec
        # B1 共同合法集合 = 状态已知 ∧ 主目标合法 ∧ 成熟（in_comparison 交叉核对）
        legal = (rec["flag_state_known"] == "True"
                 and rec["flag_main_legal"] == "True"
                 and rec["flag_mature"] == "True")
        assert (rec["in_comparison"] == "True") == legal, \
            f"in_comparison 与合法集合推导矛盾：{rec}"
        rows.append({
            "session": rec["session"], "state": state_txt,
            "main": main, "aux": aux, "legal": legal,
            "e_date": rec["e_date"] or None, "x_date": rec["x_date"] or None,
        })
    sessions = [r["session"] for r in rows]
    assert len(set(sessions)) == len(sessions), "session 重复"
    assert sessions == axis, "观察日序列 ≠ 日历推导评价窗轴"

    # ── 全期两组统计 ──────────────────────────────────────────────────
    legal_rows = [r for r in rows if r["legal"]]
    true_main = [r["main"] for r in legal_rows if r["state"] == "true"]
    false_main = [r["main"] for r in legal_rows if r["state"] == "false"]
    assert all(m is not None for m in true_main + false_main)

    def _stats(vals: list[float]) -> dict:
        return {
            "n": len(vals),
            "mean": statistics.fmean(vals),
            "median": statistics.median(vals),
            "up": sum(1 for v in vals if v > 0),
            "down": sum(1 for v in vals if v < 0),
            "zero": sum(1 for v in vals if v == 0),
        }

    st, sf = _stats(true_main), _stats(false_main)
    true_aux = [r["aux"] for r in legal_rows
                if r["state"] == "true" and r["aux"] is not None]
    false_aux = [r["aux"] for r in legal_rows
                 if r["state"] == "false" and r["aux"] is not None]
    full = {
        "n_total": len(rows),
        "n_legal": len(legal_rows),
        "true": st, "false": sf,
        "true_up_ratio": st["up"] / st["n"],
        "false_up_ratio": sf["up"] / sf["n"],
        "delta": st["mean"] - sf["mean"],
        "median_diff": st["median"] - sf["median"],
        "up_ratio_diff": st["up"] / st["n"] - sf["up"] / sf["n"],
        "aux": {
            "true": {"n": len(true_aux), "mean": statistics.fmean(true_aux),
                     "worst": min(true_aux)},
            "false": {"n": len(false_aux), "mean": statistics.fmean(false_aux),
                      "worst": min(false_aux)},
        },
    }

    # ── 逐年 / 留一年 / 等权年度差 ────────────────────────────────────
    years = sorted({r["session"][:4] for r in legal_rows})
    yearly = {}
    for y in years:
        yrows = [r for r in legal_rows if r["session"][:4] == y]
        yt = _stats([r["main"] for r in yrows if r["state"] == "true"])
        yf = _stats([r["main"] for r in yrows if r["state"] == "false"])
        yearly[y] = {
            "true": yt, "false": yf,
            "delta": (yt["mean"] - yf["mean"])
            if yt["n"] and yf["n"] else None,
        }
    sign = {"positive": 0, "zero": 0, "negative": 0}
    for y, d in yearly.items():
        if d["delta"] is None:
            continue
        if d["delta"] > 0:
            sign["positive"] += 1
        elif d["delta"] < 0:
            sign["negative"] += 1
        else:
            sign["zero"] += 1
    loo = {}
    for y in years:
        rest_t = [r["main"] for r in legal_rows
                  if r["state"] == "true" and r["session"][:4] != y]
        rest_f = [r["main"] for r in legal_rows
                  if r["state"] == "false" and r["session"][:4] != y]
        loo[y] = {
            "n": len(rest_t) + len(rest_f),
            "true_n": len(rest_t), "false_n": len(rest_f),
            "delta": (statistics.fmean(rest_t) - statistics.fmean(rest_f))
            if rest_t and rest_f else None,
        }
    valid_year_deltas = [d["delta"] for d in yearly.values()
                         if d["delta"] is not None]
    equal_weight = {
        "years": [y for y, d in yearly.items() if d["delta"] is not None],
        "mean_delta": (statistics.fmean(valid_year_deltas)
                       if valid_year_deltas else None),
        "note": "两组都有值年度差的等权均值；另一描述视角，不替代全期结果",
    }

    # ── 区间重叠审计（相邻交易日价格区间，非共同日期点数） ─────────────
    def _label_intervals(r: dict) -> set[int]:
        e_pos, x_pos = pos[r["e_date"]], pos[r["x_date"]]
        assert x_pos - e_pos == X_OFFSET - E_OFFSET, r
        # 区间以右端点在 schedule 的位置标识：(s_{k-1}, s_k]
        return set(range(e_pos + 1, x_pos + 1))

    total_refs = 0
    all_intervals: set[int] = set()
    label_sets = []
    for r in rows:
        ints = _label_intervals(r)
        label_sets.append(ints)
        total_refs += len(ints)
        all_intervals |= ints
    adjacent_shared = []
    for i in range(len(label_sets) - 1):
        adjacent_shared.append(len(label_sets[i] & label_sets[i + 1]))
    from collections import Counter
    adjacent_hist = dict(Counter(adjacent_shared))
    # 稀疏锚点审计：只审原规则（anchor 2019-10-08、步长 23），不扫描其他起点
    sparse_idx = [i for i, d in enumerate(axis)
                  if axis_pos[d] % SPARSE_STEP == axis_pos[SPARSE_ANCHOR]]
    # 等价于从锚点轴位置 0 起步长 23 的全部格点
    sparse_idx = list(range(0, len(axis), SPARSE_STEP))
    sparse_shared = [len(label_sets[a] & label_sets[b])
                     for a, b in zip(sparse_idx, sparse_idx[1:])]
    overlap = {
        "schedule_span": {"start": schedule[0], "end": schedule[-1],
                          "n": len(schedule)},
        "axis_n": len(axis),
        "per_label_intervals": len(label_sets[0]),
        "total_interval_refs": total_refs,
        "unique_intervals": len(all_intervals),
        "reuse_ratio": total_refs / len(all_intervals),
        "adjacent_pairs": len(adjacent_shared),
        "adjacent_shared_histogram": {str(k): v
                                      for k, v in sorted(adjacent_hist.items())},
        "adjacent_shared_ratio": (adjacent_hist.get(20, 0) / len(adjacent_shared)
                                  if adjacent_shared else None),
        "sparse": {
            "anchor": SPARSE_ANCHOR, "step": SPARSE_STEP,
            "grid_points": len(sparse_idx),
            "grid_within_axis": sparse_idx[-1] if sparse_idx else None,
            "adjacent_shared_max": max(sparse_shared) if sparse_shared else None,
            "adjacent_pairs": len(sparse_shared),
        },
    }

    out = {
        "derived_by": "independent stdlib script（不 import 被测包/旧汇总函数）",
        "inputs": {"observations_csv": str(OBS_CSV.relative_to(REPO)),
                   "calendar_json": str(CAL_JSON.relative_to(REPO))},
        "window": {"start": WINDOW_START, "end": WINDOW_END, "axis_n": len(axis)},
        "full_period": full, "yearly": yearly, "year_sign": sign,
        "leave_one_year_out": loo, "equal_weight_year_mean": equal_weight,
        "overlap": overlap,
        "known_cross_checks": {
            "asserted_n_legal_1516": len(legal_rows) == 1516,
            "asserted_true_590": st["n"] == 590,
            "asserted_false_926": sf["n"] == 926,
        },
    }
    assert out["known_cross_checks"] == {
        "asserted_n_legal_1516": True, "asserted_true_590": True,
        "asserted_false_926": True}, out["known_cross_checks"]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("axis_n", len(axis), "legal", len(legal_rows),
          "true", st["n"], "false", sf["n"])
    print("delta", st["mean"] - sf["mean"])
    print("yearly deltas", {y: d["delta"] for y, d in yearly.items()})
    print("sign", sign)
    print("loo", {y: d["delta"] for y, d in loo.items()})
    print("equal_weight", equal_weight["mean_delta"])
    print("overlap", {k: overlap[k] for k in
                      ("total_interval_refs", "unique_intervals",
                       "reuse_ratio", "adjacent_shared_histogram")})
    print("sparse", overlap["sparse"])
    print("wrote", OUT.relative_to(REPO))


if __name__ == "__main__":
    main()
