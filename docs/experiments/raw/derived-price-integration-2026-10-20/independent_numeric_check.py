"""Independently reconstruct fixed target lists and arithmetic, not a new study."""
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    spec = json.loads((HERE / "execution-contract.json").read_text())
    out = Path(spec["output"])
    receipt = json.loads((HERE / "execution-receipt.json").read_text())
    for item in receipt["outputs"]:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"]
    with (out / "per_stock_month.csv").open() as f:
        rows = list(csv.DictReader(f))
    months = defaultdict(list)
    for row in rows:
        months[row["month"]].append(row)
    saved = {r["month"]: r for r in json.loads((out / "defensive-monthly.json").read_text())}
    perf = json.loads((out / "defensive-performance.json").read_text())
    maximum = 0.0
    compared = 0
    previous = {}
    independent_returns = defaultdict(list)
    for month, panel in sorted(months.items()):
        eligible = [r for r in panel if r["eligibility_reason"] == "eligible"]
        n = math.ceil(len(eligible) * .2)
        mom = sorted(eligible, key=lambda r: (-float(r["momentum"]), r["code"]))
        low = sorted(eligible, key=lambda r: (float(r["vol60"]), r["code"]))
        combo = sorted(mom[:2*n], key=lambda r: (float(r["vol60"]), r["code"]))[:n]
        choices = {"pool_equal": eligible, "momentum_top20": mom[:n],
                   "momentum75": mom[:n], "lowvol_top20": low[:n], "momentum_lowvol": combo}
        for method, choice in choices.items():
            scale = .75 if method == "momentum75" else 1.
            weights = {r["code"]: scale / len(choice) for r in choice}
            actual = saved[month]["methods"][method]
            assert actual["selected_names"] == sorted(weights)
            unknown = sum(weights[r["code"]] for r in choice if r["future_return"] == "")
            observed = sum(weights[r["code"]] * float(r["future_return"]) for r in choice
                           if r["future_return"] != "")
            for field, expected in [
                ("scenario_zero", observed), ("scenario_minus100", observed - unknown),
                ("unknown_weight", unknown), ("target_weight_sum", scale),
                ("negative_component_scenario_zero", min(observed, 0)),
                ("positive_component_scenario_zero", max(observed, 0)),
                ("negative_component_scenario_minus100", min(observed - unknown, 0)),
                ("positive_component_scenario_minus100", max(observed - unknown, 0))]:
                maximum = max(maximum, abs(actual[field] - expected))
                assert math.isclose(actual[field], expected, rel_tol=1e-12, abs_tol=1e-12)
                compared += 1
            if method in previous:
                turnover = .5 * sum(abs(weights.get(c, 0) - previous[method].get(c, 0))
                                    for c in set(weights) | set(previous[method]))
                maximum = max(maximum, abs(actual["target_replacement_turnover"] - turnover))
                assert math.isclose(actual["target_replacement_turnover"], turnover, abs_tol=1e-12)
                compared += 1
            previous[method] = weights
            independent_returns[method].append(observed)
    for method, values in independent_returns.items():
        expected = {"mean_total_monthly_price_change": statistics.fmean(values),
                    "mean_negative_component": statistics.fmean(min(x, 0) for x in values),
                    "mean_positive_component": statistics.fmean(max(x, 0) for x in values),
                    "monthly_standard_deviation": statistics.stdev(values), "worst_month": min(values)}
        for field, value in expected.items():
            got = perf["methods"][method]["all_months"]["scenario_zero"][field]
            maximum = max(maximum, abs(got - value))
            assert math.isclose(got, value, rel_tol=1e-12, abs_tol=1e-12)
            compared += 1
    for right in ("momentum_top20", "momentum75", "lowvol_top20"):
        a, b = independent_returns["momentum_lowvol"], independent_returns[right]
        for field, delta in [
            ("mean_total_increment", [x-y for x, y in zip(a, b)]),
            ("mean_negative_component_increment", [min(x, 0)-min(y, 0) for x, y in zip(a, b)]),
            ("mean_positive_component_increment", [max(x, 0)-max(y, 0) for x, y in zip(a, b)])]:
            got = perf["primary_increment"]["momentum_lowvol_minus_" + right]["scenario_zero"][field]
            assert math.isclose(got, statistics.fmean(delta), abs_tol=1e-12)
            compared += 1
    # Check P1 mean values from saved actual target weights and outcomes.
    p1 = json.loads((out / "p1-performance.json").read_text())
    for method in p1["methods"]:
        values = []
        losses = []
        for panel in months.values():
            observed = sum(float(r["weight_" + method]) * float(r["future_return"])
                           for r in panel if r["future_return"] != "")
            unknown = sum(float(r["weight_" + method]) for r in panel if r["future_return"] == "")
            values.append(observed)
            losses.append(observed - unknown)
        for scenario, series in (("scenario_zero", values), ("scenario_minus100", losses)):
            got = p1["methods"][method]["mean_pct"][scenario] / 100
            maximum = max(maximum, abs(got - statistics.fmean(series)))
            assert math.isclose(got, statistics.fmean(series), abs_tol=1e-12)
            compared += 1
    result = {"status": "passed", "rows": len(rows), "months": len(months),
              "independently_rebuilt_defensive_lists": len(months) * 5,
              "numeric_comparisons": compared, "maximum_absolute_error": maximum,
              "source": "new CSV; no old research helper imported",
              "uncertainty": "not rerun; frozen statistical algorithm/code and sample support reviewed separately",
              "market_experiments_added": 0}
    with (HERE / "independent-numeric-check.json").open("x") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
