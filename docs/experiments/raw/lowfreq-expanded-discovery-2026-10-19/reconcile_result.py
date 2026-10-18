"""Independent arithmetic from saved stock/month rows; never imports evaluator."""
import argparse
import collections
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


def average(v):
    return math.fsum(v) / len(v) if v else None


def chunks(items, count):
    q, r = divmod(len(items), count)
    out, at = [], 0
    for i in range(count):
        size = q + (i < r)
        out.append(items[at:at + size])
        at += size
    return out


def run(result, output):
    root = Path(result)
    manifest = json.loads((root / "manifest.json").read_text())
    for name, expected in manifest["outputs"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
    perf = json.loads((root / "performance.json").read_text())
    monthly = {r["month"]: r for r in csv.DictReader((root / "monthly.csv").open())}
    panel = collections.defaultdict(list)
    for row in csv.DictReader((root / "per_stock_month.csv").open()):
        panel[row["month"]].append(row)
    assert len(panel) == 132 and all(len(v) == 600 for v in panel.values())
    checks = 0
    by_method, by_condition = collections.defaultdict(list), collections.defaultdict(list)
    outcomes = collections.Counter()
    group_support = collections.defaultdict(list)
    halt_weights = collections.defaultdict(list)
    spans = []
    unknown_members = []
    for month, rows in sorted(panel.items()):
        expected = json.loads(monthly[month]["methods"])
        eligible = [r for r in rows if r["eligibility_reason"] == "eligible"]
        if monthly[month]["status"] != "evaluated":
            continue
        ranked = sorted(eligible, key=lambda r: (-float(r["momentum"]), r["code"]))
        expected_top = {r["code"] for r in ranked[:math.ceil(len(ranked) / 5)]}
        actual_top = {r["code"] for r in rows if float(r["weight_momentum_top20"])}
        assert expected_top == actual_top
        checks += 1
        for method in perf["methods"]:
            chosen = [r for r in rows if float(r["weight_" + method])]
            weights = [float(r["weight_" + method]) for r in chosen]
            assert abs(math.fsum(weights) - 1) < 1e-12
            known = math.fsum(float(r["weight_" + method]) * float(r["future_return"])
                             for r in chosen if r["future_return"] != "")
            unknown = math.fsum(float(r["weight_" + method]) for r in chosen if r["future_return"] == "")
            for key, value in (("scenario_zero", known), ("scenario_minus100", known - unknown)):
                assert abs(expected[method][key] - value) < 1e-12
                by_method[(method, key)].append(value)
                checks += 1
            halt = math.fsum(float(r["weight_" + method]) for r in chosen if r["either_halt"] == "True")
            assert abs(halt - expected[method]["either_halt_weight"]) < 1e-12
            halt_weights[method].append(halt)
        for row in eligible:
            outcomes[row["outcome_reason"]] += 1
            spans.append(int(row["momentum_252_calendar_days"]))
            if row["future_return"] == "":
                unknown_members.append({k: row[k] for k in ("month", "code", "outcome_reason", "weight_pool_equal", "weight_momentum_top20")})
        for short, label in ((False, "vol_amount_9"), (True, "vol_amount_short_27")):
            cells = []
            for vg in chunks(sorted(eligible, key=lambda r: (float(r["vol60"]), r["code"])), 3):
                for ag in chunks(sorted(vg, key=lambda r: (float(r["amount20"]), r["code"])), 3):
                    cells.extend(chunks(sorted(ag, key=lambda r: (float(r["short"]), r["code"])), 3) if short else [ag])
            group_support[label].extend(len(c) for c in cells)
            for scenario, unknown_return in (("scenario_zero", 0), ("scenario_minus100", -1)):
                delta = 0
                for cell in cells:
                    if not cell:
                        continue
                    strongest = sorted(cell, key=lambda r: (-float(r["momentum"]), r["code"]))[:math.ceil(len(cell) / 5)]
                    def value(row):
                        return float(row["future_return"]) if row["future_return"] != "" else unknown_return
                    delta += len(cell) / len(eligible) * (average([value(r) for r in strongest]) - average([value(r) for r in cell]))
                by_condition[(label, scenario)].append(delta)
    summary = {"checks": checks, "market_rerun": False, "evaluator_imported": False,
               "actual_months": len(next(iter(by_method.values()))),
               "all_132_month_stock_panels_have_600": True,
               "method_means_pct": {}, "conditional_means_pct": {}}
    for (method, scenario), values in by_method.items():
        result = 100 * average(values)
        assert abs(result - perf["methods"][method]["mean_pct"][scenario]) < 1e-10
        summary["method_means_pct"][method + ":" + scenario] = result
        if len(values) == 132:
            risk = perf["methods"][method]["scenarios"][scenario]
            wealth, peak, drawdown = 1, 1, 0
            for value in values:
                wealth *= 1 + value
                peak = max(peak, wealth)
                drawdown = max(drawdown, 1 - wealth / peak)
            independent = {"monthly_std": statistics.stdev(values),
                           "worst_month": min(values),
                           "mean_worst10pct_months": average(sorted(values)[:math.ceil(len(values) / 10)]),
                           "marked_price_cumulative": wealth - 1,
                           "marked_price_max_drawdown": drawdown}
            for key, value in independent.items():
                assert abs(value - risk[key]) < 1e-10, (method, scenario, key)
                checks += 1
    for (method, scenario), values in by_condition.items():
        result = 100 * average(values)
        assert abs(result - perf["conditional_increment_mean_pct"][method][scenario]) < 1e-10
        summary["conditional_means_pct"][method + ":" + scenario] = result
    summary["conditional_group_support_min_max"] = {k: [min(v), max(v)] for k, v in group_support.items()}
    summary["eligible_outcome_reasons"] = dict(outcomes)
    summary["unknown_eligible_stock_months"] = unknown_members
    summary["momentum_252_calendar_days"] = {"min": min(spans), "median": statistics.median(spans),
                                               "max": max(spans), "over_450_fraction": sum(v > 450 for v in spans) / len(spans)}
    summary["method_mean_halt_weight"] = {k: average(v) for k, v in halt_weights.items()}
    summary["checks"] = checks
    with Path(output).open("x") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({"checks": checks, "actual_months": summary["actual_months"], "result": "passed"}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--result", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    run(a.result, a.out)
