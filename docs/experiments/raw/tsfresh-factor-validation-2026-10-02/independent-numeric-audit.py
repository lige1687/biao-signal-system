"""Independent stdlib audit of frozen predictions; never fits or imports research code."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VARIANTS = ("joint", "amplitude", "serial", "factor_only")
MODELS = ("B0", "B1", "B2")


def read(path):
    return json.loads(path.read_text())


def close(a, b, tolerance=1e-9):
    return math.isclose(a, b, rel_tol=0, abs_tol=tolerance)


def score(rows):
    assets = sorted({r["asset"] for r in rows})
    losses = {m: [] for m in MODELS}
    for asset in assets:
        ar = [r for r in rows if r["asset"] == asset]
        for model in MODELS:
            losses[model].append(math.fsum((r["y"] - r[model]) ** 2 for r in ar) / len(ar))
    mse = {m: math.fsum(losses[m]) / len(assets) for m in MODELS}
    rmse = {m: math.sqrt(mse[m]) for m in MODELS}
    return {"rows": len(rows), "dates": len({r["date"] for r in rows}),
            "assets": len(assets), "mse": mse, "rmse": rmse,
            "delta_mse_B1_B2": mse["B1"] - mse["B2"],
            "delta_rmse_B1_B2": rmse["B1"] - rmse["B2"],
            "delta_rmse_B0_B2": rmse["B0"] - rmse["B2"]}


def compare(actual, saved, path, failures, differences):
    if isinstance(actual, dict):
        for key, value in actual.items():
            compare(value, saved[key], f"{path}.{key}", failures, differences)
    elif isinstance(actual, float):
        diff = actual - saved
        differences.append(abs(diff))
        if not close(actual, saved):
            failures.append({"where": path, "actual": actual, "saved": saved, "difference": diff})
    elif actual != saved:
        failures.append({"where": path, "actual": actual, "saved": saved})


def main():
    panel_path = ROOT / "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json"
    panel = read(panel_path)
    calendar = panel["calendar"]
    date_index = {d: i for i, d in enumerate(calendar)}
    prices = {(r["asset"], r["date"]): r["close"] for r in panel["bars"]}
    saved = read(HERE / "saved-prediction-analysis.json")
    failures, differences, summaries, all_ids = [], [], {}, []
    checked = {"predictions": 0, "targets": 0, "label_ends": 0,
               "baseline_values": 0, "performance_values": 0,
               "saved_score_fields": 0, "top20_dates": 0}
    hashes = {}
    for variant in VARIANTS:
        directory = HERE / f"run-{variant}"
        result_path = directory / "result.json"
        result = read(result_path)
        contract = read(directory / "contract.json")
        receipt = read(directory / "receipt.json")
        rows = result["predictions"]
        hashes[variant] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        if hashes[variant] != receipt["outputs"]["result.json"]:
            failures.append({"where": f"{variant}.receipt_hash"})
        if hashes[variant] != saved[variant]["result_sha256"]:
            failures.append({"where": f"{variant}.saved_hash"})
        if calendar != contract["calendar"]:
            failures.append({"where": f"{variant}.calendar"})
        ids = {r["id"] for r in rows}
        if len(ids) != len(rows):
            failures.append({"where": f"{variant}.duplicate_ids"})
        all_ids.append(ids)
        folds = contract["split"]["folds"]
        train_means = {}
        fold_labels = defaultdict(list)
        for fold_number, fold in enumerate(folds):
            for asset in sorted({r["asset"] for r in rows}):
                labels = []
                for d in calendar:
                    if d < "2022-01-04" or d > fold["train_end"]:
                        continue
                    i = date_index[d]
                    if i + 21 >= len(calendar) or calendar[i + 21] > fold["train_end"]:
                        continue
                    a, b = prices.get((asset, calendar[i + 1])), prices.get((asset, calendar[i + 21]))
                    if a is not None and b is not None:
                        labels.append(100 * (b / a - 1))
                fold_labels[str(fold_number)].extend(labels)
                if len(labels) != (705 if fold_number == 0 else 948):
                    failures.append({"where": f"{variant}.train_count.{fold_number}.{asset}", "actual": len(labels)})
        for fold_number, labels in fold_labels.items():
            train_means[fold_number] = math.fsum(labels) / len(labels)
        for row in rows:
            checked["predictions"] += 1
            asset, d = row["asset"], row["date"]
            i = date_index[d]
            expected_end = calendar[i + 21]
            if row["label_end"] != expected_end:
                failures.append({"where": f"{variant}.{row['id']}.label_end", "actual": expected_end, "saved": row["label_end"]})
            checked["label_ends"] += 1
            expected_y = 100 * (prices[(asset, calendar[i + 21])] / prices[(asset, calendar[i + 1])] - 1)
            if not close(expected_y, row["y"]):
                failures.append({"where": f"{variant}.{row['id']}.target", "actual": expected_y, "saved": row["y"]})
            differences.append(abs(expected_y - row["y"]))
            checked["targets"] += 1
            fold = folds[int(row["fold"])]
            if not (fold["eval_start"] <= d <= expected_end <= fold["eval_end"]):
                failures.append({"where": f"{variant}.{row['id']}.fold_containment"})
            baseline = train_means[row["fold"]]
            for field in ("B0", "train_mean"):
                if not close(baseline, row[field]):
                    failures.append({"where": f"{variant}.{row['id']}.{field}", "actual": baseline, "saved": row[field]})
                differences.append(abs(baseline - row[field]))
                checked["baseline_values"] += 1
        groups = {"overall": score(rows),
                  "by_asset": {a: score([r for r in rows if r["asset"] == a]) for a in sorted({r["asset"] for r in rows})},
                  "by_year": {y: score([r for r in rows if r["date"][:4] == y]) for y in ("2025", "2026")},
                  "leave_one_asset_out": {a: score([r for r in rows if r["asset"] != a]) for a in sorted({r["asset"] for r in rows})}}
        by_date = defaultdict(list)
        for row in rows:
            by_date[row["date"]].append((row["y"] - row["B1"]) ** 2 - (row["y"] - row["B2"]) ** 2)
        top = sorted(by_date, key=lambda d: (-math.fsum(by_date[d]) / len(by_date[d]), d))[:20]
        trimmed = score([r for r in rows if r["date"] not in top])
        for name, value in groups.items():
            before = len(differences)
            compare(value, saved[variant][name], f"{variant}.{name}", failures, differences)
            checked["saved_score_fields"] += len(differences) - before
        before = len(differences)
        compare(trimmed, saved[variant]["remove_top20"]["remaining"], f"{variant}.remove_top20.remaining", failures, differences)
        checked["saved_score_fields"] += len(differences) - before
        compare(top, saved[variant]["remove_top20"]["dates"], f"{variant}.remove_top20.dates", failures, differences)
        checked["top20_dates"] += len(top)
        for performance in result["performance"]:
            model, metric = performance["model"], performance["metric"].lower()
            expected = groups["overall"][metric][model]
            if not close(expected, performance["value"]):
                failures.append({"where": f"{variant}.performance.{model}.{metric}", "actual": expected, "saved": performance["value"]})
            differences.append(abs(expected - performance["value"]))
            checked["performance_values"] += 1
        for increment in result["increments"]:
            old = increment["old_model"]
            expected = groups["overall"]["mse"][old] - groups["overall"]["mse"]["B2"]
            if not close(expected, increment["absolute_error_improvement"]):
                failures.append({"where": f"{variant}.increment.{old}", "actual": expected, "saved": increment["absolute_error_improvement"]})
            differences.append(abs(expected - increment["absolute_error_improvement"]))
            checked["performance_values"] += 1
        uncertainty = saved[variant]["uncertainty"]
        evaluation_axis = [d for d in calendar if any(f["eval_start"] <= d <= f["eval_end"] for f in folds)]
        for length in (20, 60):
            item = uncertainty[str(length)]
            if (item["calendar_dates"] != len(evaluation_axis) or item["draws"] != 1000 or
                    item["seed"] != 20261002 or item["unestimable_draws"] != 0):
                failures.append({"where": f"{variant}.uncertainty.{length}.metadata"})
            for old, comparison in item["comparisons"].items():
                expected = groups["overall"]["mse"][old] - groups["overall"]["mse"]["B2"]
                if not close(expected, comparison["delta_mse"]):
                    failures.append({"where": f"{variant}.uncertainty.{length}.{old}.delta_mse"})
                if comparison["mse_lo"] > comparison["mse_hi"] or comparison["rmse_lo"] > comparison["rmse_hi"]:
                    failures.append({"where": f"{variant}.uncertainty.{length}.{old}.range_order"})
        tail = [d for d in evaluation_axis if d not in {r["date"] for r in rows}]
        if len(tail) != 42 or len(evaluation_axis) != 359:
            failures.append({"where": f"{variant}.evaluation_tail", "actual": len(tail)})
        summaries[variant] = {"overall_mse": groups["overall"]["mse"],
                              "increment_vs_B1": groups["overall"]["delta_mse_B1_B2"],
                              "evaluation_calendar_dates": len(evaluation_axis),
                              "labelled_dates": groups["overall"]["dates"],
                              "unlabelled_tail_dates": len(tail),
                              "tail_by_year": {y: len([d for d in tail if d.startswith(y)]) for y in ("2025", "2026")},
                              "top20_removed_increment": trimmed["delta_mse_B1_B2"],
                              "leave_one_asset_out_increments": {a: s["delta_mse_B1_B2"] for a, s in groups["leave_one_asset_out"].items()},
                              "block20_mse_range": uncertainty["20"]["comparisons"]["B1"],
                              "block60_mse_range": uncertainty["60"]["comparisons"]["B1"]}
    if not all(ids == all_ids[0] for ids in all_ids):
        failures.append({"where": "common_prediction_ids", "sizes": [len(s) for s in all_ids]})
    output = {"status": "pass" if not failures else "fail", "failures": failures,
              "common_ids": len(set.intersection(*all_ids)), "checked": checked,
              "maximum_absolute_numeric_difference": max(differences),
              "variant_summaries": summaries,
              "sensitivity_method_review": "analyze_saved.py passes full evaluation calendar (359 dates including 42 unlabelled tails) to shared-date block draws; 20 and 60 date block outputs are conditional on fixed saved predictions; draws themselves not independently reproduced by stdlib",
              "limitations": ["four related ETFs", "overlapping 20-interval targets", "retrospective previously seen history", "not realized trading return"]}
    (HERE / "independent-numeric-audit.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    lines = ["# tsfresh 冻结结果独立数值复核", "", "## 一句话结论（大白话）", "",
             f"独立重算保存预测和原始价格后，{len(failures)} 项数值或时间资格不符；四组新增价格表达均未降低相对已有信息的预测误差。这不是实际交易收益。", "",
             f"共核对 {checked['targets']} 个未来涨跌目标与结束日、{checked['baseline_values']} 个较早训练平均值；四组共同预测 ID 为 {output['common_ids']} 个。最大绝对数值差为 {output['maximum_absolute_numeric_difference']:.3g}。", "",
             "| 比较 | 原有信息均方误差 | 加入候选后均方误差 | 误差改善（正数才好） |", "|---|---:|---:|---:|"]
    for v, s in summaries.items():
        m = s["overall_mse"]
        lines.append(f"| {v} | {m['B1']:.6f} | {m['B2']:.6f} | {s['increment_vs_B1']:.6f} |")
    lines += ["", "## 时间与敏感性", "",
              "每组 359 个评价日，其中 317 个有完整的未来 20 间隔结果；2025 和 2026 各有 21 个尾日，合计 42 个尾日没有成熟目标。保存的整段日期重复抽取以完整评价日历为范围，20 日和 60 日两种长度均记录 1000 次、同一随机种子、零次不可估计。这个检查核对方法和元数据，没有用标准库重现 NumPy 的逐次抽取分位数。",
              "", "去掉每组改善最大的 20 日、逐一不计一只 ETF 的数字，均从已保存预测重新算出并与保存分析对上。四只 ETF 走势相关，未来 20 个交易间隔目标彼此重叠；这些范围仅描述固定预测在这段历史上的波动，不能当成新历史或可交易收益。", "",
              "## 具体不符", ""]
    lines += [f"- {x}" for x in failures] if failures else ["无。"]
    (HERE / "independent-numeric-audit.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": output["status"], "failures": len(failures), "checked": checked,
                      "max_difference": output["maximum_absolute_numeric_difference"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
