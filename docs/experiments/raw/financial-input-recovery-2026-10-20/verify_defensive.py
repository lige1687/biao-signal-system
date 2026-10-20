"""Independent saved-output arithmetic; never launches or changes a strategy."""
from pathlib import Path
from collections import defaultdict
import csv
import datetime as dt
import hashlib
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
METHODS = ("pool_equal", "momentum_top20", "momentum75", "lowvol_top20", "momentum_lowvol")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    return None if value in ("", None) else float(value)


def close(left, right):
    assert (left is None) == (right is None), (left, right)
    if left is not None:
        assert math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-12), (left, right)


def main():
    target = HERE / "defensive-controller-review.json"
    assert not target.exists()
    contract = json.loads((HERE / "defensive-execution-contract.json").read_text())
    receipt = json.loads((HERE / "defensive-execution-receipt.json").read_text())
    assert receipt["exit_code"] == 0 and receipt["status"] == "execution_completed_needs_controller_review"
    for item in list(contract["bindings"].values()) + list(contract["additional_bindings"].values()) + receipt["outputs"]:
        assert sha(item["path"]) == item["sha256"], item["path"]
    output = Path(contract["output_directory"])
    monthly = json.loads((output / "per_month.json").read_text())
    performance = json.loads((output / "performance.json").read_text())
    audit = json.loads(Path(contract["bindings"]["source_integrity"]["path"]).read_text())
    blocked = set(audit["combined_blocked_months"])
    weights = defaultdict(list)
    with (output / "new_weights.csv").open() as handle:
        for row in csv.DictReader(handle):
            weights[row["month"]].append(row)
    assert len(monthly) == len(weights) == 132
    assert sum(len(rows) for rows in weights.values()) == 79200
    original = {}
    with Path(contract["bindings"]["input"]["path"]).open() as handle:
        for row in csv.DictReader(handle):
            original[(row["month"], row["code"])] = row
    series = {m: {"scenario_zero": [], "scenario_minus100": []} for m in METHODS}
    nonempty_dates, pairs = [], {m: 0 for m in METHODS}
    maximum_arithmetic_difference = 0.0
    for month in monthly:
        date = month["month"]
        assert month["combined_blocked"] == (date in blocked)
        assert not month["original_full_month_blocked"]
        rows = weights[date]
        assert len(rows) == 600 and len({r["code"] for r in rows}) == 600
        for row in rows:
            old = original[(date, row["code"])]
            assert row["eligibility_reason"] == old["eligibility_reason"]
            for field in ("momentum", "vol60", "future_return", "suspension_marked_price_proxy"):
                close(number(row[field]), number(old[field]))
        if date not in blocked:
            nonempty_dates.append(date)
        for method in METHODS:
            result = month["methods"][method]
            selected = [r for r in rows if float(r["weight_" + method]) > 0]
            if date in blocked:
                assert not selected and result["empty_selection"]
                assert result["observed_best_decile_name_share_selected"] is None
                assert result["target_replacement_turnover"] is None
                for scenario in series[method]:
                    assert result[scenario] is None
                continue
            assert selected and all(r["eligibility_reason"] == "eligible" for r in selected)
            assert sorted(r["code"] for r in selected) == result["selected_names"]
            close(math.fsum(float(r["weight_" + method]) for r in rows), .75 if method == "momentum75" else 1.)
            observed = math.fsum(float(r["weight_" + method]) * float(r["future_return"])
                                 for r in selected if r["future_return"] != "")
            unknown = math.fsum(float(r["weight_" + method]) for r in selected if r["future_return"] == "")
            close(result["unknown_weight"], unknown)
            for scenario, value in (("scenario_zero", observed), ("scenario_minus100", observed - unknown)):
                close(result[scenario], value)
                maximum_arithmetic_difference = max(maximum_arithmetic_difference, abs(result[scenario] - value))
                close(result["negative_component_" + scenario], min(value, 0.))
                close(result["positive_component_" + scenario], max(value, 0.))
                series[method][scenario].append(value)
            pairs[method] += result["target_replacement_turnover"] is not None
        if date not in blocked:
            close(month["methods"]["momentum75"]["scenario_zero"], .75 * month["methods"]["momentum_top20"]["scenario_zero"])
            close(month["methods"]["momentum75"]["observed_best_decile_name_share_selected"],
                  month["methods"]["momentum_top20"]["observed_best_decile_name_share_selected"])
    assert nonempty_dates == audit["retained_evaluable_months"] and len(nonempty_dates) == 69
    assert set(pairs.values()) == {67}
    for method in METHODS:
        for scenario, values in series[method].items():
            saved = performance["methods"][method]["all_months"][scenario]
            assert len(values) == saved["defined_months"] == 69
            close(saved["mean_total_monthly_price_change"], statistics.fmean(values))
            close(saved["mean_negative_component"], statistics.fmean(min(v, 0) for v in values))
            close(saved["mean_positive_component"], statistics.fmean(max(v, 0) for v in values))
            close(saved["monthly_standard_deviation"], statistics.stdev(values))
            close(saved["worst_month"], min(values))
            close(saved["mean_worst10pct_months"], statistics.fmean(sorted(values)[:7]))
    for comparator in ("momentum_top20", "momentum75", "lowvol_top20"):
        for scenario in ("scenario_zero", "scenario_minus100"):
            a, b = series["momentum_lowvol"][scenario], series[comparator][scenario]
            actual = performance["primary_increment"]["momentum_lowvol_minus_" + comparator][scenario]
            close(actual["mean_total_increment"], statistics.fmean(x-y for x, y in zip(a, b)))
            close(actual["mean_negative_component_increment"], statistics.fmean(min(x, 0)-min(y, 0) for x, y in zip(a, b)))
            close(actual["mean_positive_component_increment"], statistics.fmean(max(x, 0)-max(y, 0) for x, y in zip(a, b)))
    record = {
        "schema": "independent-defensive-output-audit/1",
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "status": "arithmetic_and_bound_sources_verified_scientific_verdict_separate",
        "rows": 79200, "calendar_months": 132, "common_blocked_months": 63,
        "evaluable_months": 69, "adjacent_target_replacement_pairs": pairs,
        "input_fields_preserved": True, "output_and_input_hashes_match": True,
        "all_methods_common_date_support": True, "blocked_hit_rates_are_null": True,
        "monthly_price_change_and_components_independently_recomputed": True,
        "all_three_increment_contrasts_independently_recomputed": True,
        "maximum_monthly_reconciliation_error": maximum_arithmetic_difference,
        "output": str(output), "performance_sha256": sha(output / "performance.json"),
        "new_effect_experiment_runs_in_verifier": 0,
        "limitations": ["Numerical consistency is not evidence of a viable strategy.",
                       "No fills, fees, full decade, all-market membership or new market data verified.",
                       "Uncertainty helper reused with fixed seed and date axis; this audit does not rerun the resampling."],
    }
    with target.open("x") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
