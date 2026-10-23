"""Independent, read-only recomputation of the frozen historical price association.

Uses the bound formation input and original qfq prices. Does not import the effect runner.
"""

import calendar as monthcal
import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).parent
FREEZE = json.loads((ROOT / "history-effect-freeze.json").read_text())
PRICE = json.loads((ROOT / "price-qualification.json").read_text())
ADJUST = json.loads((ROOT / "adjusted-history-comparison.json").read_text())
REPORTED = json.loads((ROOT / "history-effect-summary.json").read_text())
OUT = Path(REPORTED["out"])
METHODS = ["fixed_jiashi", "fixed_huaxia", "report_redemption", "adjusted_redemption"]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def close(x, y, tol=1e-11):
    if x is None or y is None:
        assert x is y, (x, y)
    else:
        assert math.isclose(float(x), float(y), rel_tol=tol, abs_tol=tol), (x, y)


def fractional_top(scores):
    """Take 30% of names, splitting a tied boundary evenly across tied names."""
    scores = np.asarray(scores, dtype=float)
    result = np.zeros(len(scores), dtype=float)
    quota = len(scores) * .30
    for score in np.unique(scores)[::-1]:
        at = np.where(scores == score)[0]
        assigned = min(quota, len(at))
        if assigned <= 0:
            break
        result[at] = assigned / len(at)
        quota -= assigned
    assert abs(result.sum() - len(scores) * .30) < 1e-8
    return result


def rank_corr(x, y):
    if len(x) < 2:
        return None
    x = pd.Series(x).rank(method="average").to_numpy(dtype=float)
    y = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    x -= x.mean()
    y -= y.mean()
    norm = math.sqrt(float(x @ x) * float(y @ y))
    return float(x @ y / norm) if norm > 0 else None


def add_six_months(d):
    m = d.month + 6
    y = d.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, min(d.day, monthcal.monthrange(y, m)[1]))


def mean(xs):
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def main():
    # Validate exact bound sources before looking at outcomes.
    for path, expected in FREEZE["bindings"].items():
        assert digest(path) == expected, path
    assert digest(ROOT / "history-effect-summary.json") == digest(OUT / "summary.json")
    forms = pd.read_parquet(PRICE["formations_path"])
    assert len(forms) == 2689 and forms[["period", "code"]].duplicated().sum() == 0
    present = sorted(set(forms.loc[forms.column_present, "code"]))
    prices = pd.read_parquet(PRICE["price_source"], columns=["date"] + present)
    if "date" in prices.columns:
        prices = prices.set_index("date")
    prices.index = pd.to_datetime(prices.index)
    assert prices.index.is_unique
    cal = json.loads(Path(PRICE["calendar_source"]).read_text())["days"]
    trade = sorted(date.fromisoformat(k) for k, v in cal.items() if v["is_trading_day"])
    directives = {r["period"]: r for r in ADJUST["periods"]}
    qualifications = {r["period"]: r for r in PRICE["periods"]}
    report_rows = {(r["period"], r["method"]): r for r in REPORTED["per_period"]}
    selection = {(r["period"], r["method"], r["code"]): r for r in csv.DictReader((OUT / "selection-weights.csv").open())}
    assert len(report_rows) == 13 * 4 and len(selection) == 2689 * 4
    checks = []
    weights_checked = 0
    known_count = 0
    unknown_count = 0
    endpoint_examples = []
    for period, group in forms.groupby("period", sort=True):
        q = qualifications[period]
        directive = directives[period]
        group = group.sort_values("code")
        assert len(group) == q["universe"]
        public = date.fromisoformat(q["public_date"])
        entry = next(d for d in trade if d > public)
        target = add_six_months(entry)
        possible_exits = [d for d in trade if d >= target]
        exit_date = possible_exits[0] if possible_exits else None
        assert entry.isoformat() == q["entry"] and target.isoformat() == q["requested_exit_on_or_after"]
        assert (exit_date.isoformat() if exit_date else None) == q["exit"]
        assert group.entry.iloc[0].date() == entry
        assert (group.exit.iloc[0].date() if pd.notna(group.exit.iloc[0]) else None) == exit_date
        y = []
        for row in group.itertuples():
            start = prices.at[row.entry, row.code] if row.column_present and row.entry in prices.index else np.nan
            end = prices.at[row.exit, row.code] if row.column_present and pd.notna(row.exit) and row.exit in prices.index else np.nan
            has_start = bool(np.isfinite(start) and start > 0)
            has_end = bool(np.isfinite(end) and end > 0)
            assert has_start == row.entry_price_available and has_end == row.exit_price_available, (period, row.code)
            value = float(end / start - 1) if has_start and has_end else np.nan
            y.append(value)
            if np.isfinite(value) and len(endpoint_examples) < 6 and period in ["2019H2", "2020H1", "2020H2", "2021H1", "2024H2", "2025H1"] and not any(e["period"] == period for e in endpoint_examples):
                endpoint_examples.append({"period": period, "code": row.code, "entry": str(row.entry.date()), "entry_qfq": float(start),
                                          "exit": str(row.exit.date()), "exit_qfq": float(end), "recomputed_change": value})
        y = np.asarray(y)
        known = np.isfinite(y)
        known_count += int(known.sum())
        unknown_count += int((~known).sum())
        assert int(known.sum()) == q["both_available"]
        a = group.a.to_numpy(dtype=float)
        raw_dir = directive["raw_direction"]
        adj_dir = directive["adjusted_direction"]
        for method, direction in [("fixed_jiashi", 1), ("fixed_huaxia", -1), ("report_redemption", raw_dir), ("adjusted_redemption", adj_dir)]:
            active = method.startswith("fixed") or direction != 0
            w = fractional_top(direction * a) if active else np.zeros(len(a))
            score = direction * a
            ic = rank_corr(score[known], y[known]) if active else None
            observed_weight = float(w[known].sum())
            high = float(w[known] @ y[known] / observed_weight) if observed_weight > 0 else None
            whole = float(np.mean(y[known])) if known.any() else None
            unknown_weight = float(w[~known].sum())
            reported = report_rows[(period, method)]
            for key, actual in [("direction", adj_dir), ("active", active), ("universe", len(group)), ("known", int(known.sum())), ("unknown", int((~known).sum()))]:
                assert reported[key] == actual, (period, method, key)
            for key, actual in [("ic", ic), ("high_price_change_known", high), ("whole_price_change_known", whole),
                                ("high_minus_whole_known", high - whole if high is not None and whole is not None else None),
                                ("selected_weight", float(w.sum())), ("unknown_selected_weight", unknown_weight),
                                ("unknown_selected_fraction", unknown_weight / w.sum() if w.sum() else None)]:
                close(reported[key], actual)
            for code, wi, yi in zip(group.code, w, y):
                other = selection[(period, method, code)]
                close(float(other["selected_weight"]), wi)
                assert (other["future_known"] == "True") == bool(np.isfinite(yi))
                weights_checked += 1
            checks.append({"period": period, "method": method, "direction": direction, "active": active, "universe": len(group),
                           "known": int(known.sum()), "unknown": int((~known).sum()), "ic": ic, "high": high,
                           "whole": whole, "high_minus_whole": high - whole if high is not None and whole is not None else None,
                           "selected_weight": float(w.sum()), "unknown_selected_weight": unknown_weight,
                           "unknown_selected_fraction": unknown_weight / w.sum() if w.sum() else None,
                           "fractional_boundary_names": int(((w > 0) & (w < 1)).sum()),
                           "fractional_boundary_weight_each": float(w[(w > 0) & (w < 1)][0]) if ((w > 0) & (w < 1)).any() else None,
                           "entry": entry.isoformat(), "requested_exit": target.isoformat(), "exit": exit_date.isoformat() if exit_date else None})
    assert known_count == 2453 and unknown_count == 236 and weights_checked == 10756
    common = sorted({x["period"] for x in checks if x["method"] == "adjusted_redemption" and x["ic"] is not None}
                    & {x["period"] for x in checks if x["method"] == "report_redemption" and x["ic"] is not None})
    assert common == REPORTED["common_periods"] and len(common) == 10
    metrics = {}
    for method in METHODS:
        rows = [x for x in checks if x["method"] == method and x["period"] in common]
        metrics[method] = {"periods": len(rows), "mean_ic": mean([x["ic"] for x in rows]),
                           "mean_high": mean([x["high"] for x in rows]), "mean_whole": mean([x["whole"] for x in rows]),
                           "mean_high_minus_whole": mean([x["high_minus_whole"] for x in rows]),
                           "max_unknown_selected_fraction": max(x["unknown_selected_fraction"] for x in rows)}
        report = REPORTED["performance"][method]
        for key, old in [("periods", report["periods"]), ("mean_ic", report["mean_ic"]),
                         ("mean_high", report["mean_high_price_change_known"]), ("mean_whole", report["mean_whole_price_change_known"]),
                         ("mean_high_minus_whole", report["mean_high_minus_whole_known"]),
                         ("max_unknown_selected_fraction", report["max_unknown_selected_fraction"])]:
            close(metrics[method][key], old)
    increment = {}
    for opponent in ["fixed_jiashi", "fixed_huaxia"]:
        paired = [next(x["high"] for x in checks if x["period"] == p and x["method"] == "adjusted_redemption") -
                  next(x["high"] for x in checks if x["period"] == p and x["method"] == opponent) for p in common]
        ic_paired = [next(x["ic"] for x in checks if x["period"] == p and x["method"] == "adjusted_redemption") -
                     next(x["ic"] for x in checks if x["period"] == p and x["method"] == opponent) for p in common]
        increment[opponent] = {"mean_high_difference": mean(paired), "mean_ic_difference": mean(ic_paired),
                               "positive_periods": sum(v > 1e-12 for v in paired), "negative_periods": sum(v < -1e-12 for v in paired),
                               "identical_periods": sum(abs(v) <= 1e-12 for v in paired),
                               "leave_one_out_range": [min(mean(paired[:i] + paired[i + 1:]) for i in range(len(paired))),
                                                       max(mean(paired[:i] + paired[i + 1:]) for i in range(len(paired)))]}
        report = REPORTED["increment"][opponent]
        for k, old in [("mean_high_difference", report["mean_high_price_change_difference"]),
                       ("mean_ic_difference", report["mean_ic_difference"]), ("positive_periods", report["positive_periods"]),
                       ("negative_periods", report["negative_periods"]), ("identical_periods", report["identical_periods"])]:
            close(increment[opponent][k], old)
    changed = [x["period"] for x in ADJUST["periods"] if x["raw_direction"] != x["adjusted_direction"] and x["period"] in qualifications]
    assert changed == ["2019H2", "2021H2"]
    same_selection = []
    for p in common:
        raw = [float(selection[(p, "report_redemption", c)]["selected_weight"]) for c in forms.loc[forms.period == p, "code"]]
        adj = [float(selection[(p, "adjusted_redemption", c)]["selected_weight"]) for c in forms.loc[forms.period == p, "code"]]
        if all(abs(x - y) < 1e-12 for x, y in zip(raw, adj)):
            same_selection.append(p)
    assert len(same_selection) == 8
    result = {"status": "passed", "bindings_verified": len(FREEZE["bindings"]), "formations": len(forms), "known": known_count,
              "unknown": unknown_count, "selection_rows_verified": weights_checked, "periods_formable": len(qualifications),
              "no_rank_due_to_both_zero": [p for p in qualifications if directives[p]["adjusted_direction"] == 0],
              "future_source_gap": [p for p in qualifications if not qualifications[p]["source_covers_exit"]],
              "paired_periods": common, "raw_adjusted_direction_changed": changed, "same_selection_periods": same_selection,
              "metrics": metrics, "increment_vs_fixed": increment, "per_period": checks,
              "original_price_endpoint_pairs": endpoint_examples,
              "calendar_roll_examples": [{"period": p, "target": qualifications[p]["requested_exit_on_or_after"], "exit": qualifications[p]["exit"]}
                                         for p in ["2019H2", "2020H1", "2022H2", "2024H2", "2025H1", "2025H2"]],
              "differences_from_frozen_summary": [],
              "limits": "QFQ close changes in known price slices only; not dividend-inclusive, not tradable/net returns; unresolved exit, delisting and historical identity remain unknown."}
    (ROOT / "history-effect-independent.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    markdown = f"""# A股历史持仓价格关联独立核算（2026-10-23）

## 一句话结论（大白话）
按同一批已知价格重新算，扣除红利再投后的赎回强弱只比固定选择华夏持仓平均高约 {increment['fixed_huaxia']['mean_high_difference']*100:.2f} 个百分点；10期中有5期两者选的股票完全相同，且部分股票没有完整价格，暂不足以作为交易规则。

原价重算与冻结摘要逐项相符，差异为零。13个可形成期中，2期两家都没有净赎回、无法按压力排序，2025年下半年尚无半年后价格；只对剩下10期比较。2,689个股票与期次记录中，2,453个有首尾价格，236个保持未知。全部10,756行选择权重读回相符，同分边界由并列股票平分30%名额。

扣除再投口径的平均排序相关为 {metrics['adjusted_redemption']['mean_ic']:.4f}，选中股票的已知价格平均变化为 {metrics['adjusted_redemption']['mean_high']*100:.2f}%，同池已知股票为 {metrics['adjusted_redemption']['mean_whole']*100:.2f}%。原报告申赎口径分别为 {metrics['report_redemption']['mean_ic']:.4f} 和 {metrics['report_redemption']['mean_high']*100:.2f}%。两口径仅2019年下半年、2021年下半年选股方向不同，其余8个共同期选择权重相同。

与固定嘉实和固定华夏的已知价格变化差分别为 {increment['fixed_jiashi']['mean_high_difference']*100:.2f}、{increment['fixed_huaxia']['mean_high_difference']*100:.2f} 个百分点。固定华夏对照的逐期差为3正、2负、5相同；剔除任一期后平均差范围为 {increment['fixed_huaxia']['leave_one_out_range'][0]*100:.2f} 至 {increment['fixed_huaxia']['leave_one_out_range'][1]*100:.2f} 个百分点，方向并不稳定。

这是事后复权收盘价变化的描述，不含分红、手续费、真实可交易状态或退市终值。价格缺失的股票保留在原名单与权重中，展示的均值仅针对价格已知部分；不能把未知当作零或把结果称为基金收益。
"""
    (ROOT / "history-effect-independent.md").write_text(markdown)
    print(json.dumps({"status": "passed", "formations": len(forms), "known": known_count, "unknown": unknown_count,
                      "paired_periods": len(common), "adjusted_ic": metrics["adjusted_redemption"]["mean_ic"],
                      "adjusted_high": metrics["adjusted_redemption"]["mean_high"],
                      "delta_huaxia": increment["fixed_huaxia"]["mean_high_difference"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
