"""Independent source-to-result arithmetic audit; does not import the runner."""
from pathlib import Path
from decimal import Decimal
import argparse
import hashlib
import json
import math
import random
import numpy as np
import pandas as pd


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--audit-output", required=True)
    args = parser.parse_args()
    contract = json.loads(Path(args.contract).read_text())
    out = Path(contract["output_directory"])
    inputs = contract["inputs"]
    manifest = json.loads((out / "manifest.json").read_text())
    for name, rec in manifest["output_files"].items():
        assert sha(out / name) == rec["sha256"], name
    admission = json.loads(Path(inputs["admission"]["path"]).read_text())["rows"]
    admitted = {(a["target_month"], a["ticker"]): a for a in admission if a["admit"]}
    panel = pd.read_csv(inputs["accounting_candidates"]["path"], dtype=str, keep_default_na=False)
    records = {(r["target_month"], r["ticker"]): r for r in panel.to_dict("records")}
    filings = {}
    with Path(inputs["filings"]["path"]).open() as stream:
        for line in stream:
            f = json.loads(line)
            filings[f["adsh"]] = f
    formed = pd.read_csv(out / "formation-with-feature.csv", dtype={"candidate_cik": str})
    monthly = pd.read_csv(out / "monthly.csv")
    pairs = pd.read_csv(out / "pairs.csv")
    choices = pd.read_csv(out / "policy-choices.csv")
    omitted = pd.read_csv(out / "odd-omissions.csv")
    uncertainty = json.loads((out / "uncertainty.json").read_text())
    periods = json.loads((out / "period-summary.json").read_text())["periods"]
    assert set(zip(formed.target_month, formed.ticker)) == set(admitted)
    max_formula_error = 0.0
    checked_returns = 0
    for row in formed.to_dict("records"):
        key = (row["target_month"], row["ticker"])
        a, raw = admitted[key], records[key]
        f = filings[row["adsh"]]["source_facts"]
        op = float((Decimal(f["operating_income"][0]["value"]) -
                    Decimal(f["interest"][0]["value"])) / Decimal(f["inclusive_equity"][0]["value"]))
        max_formula_error = max(max_formula_error, abs(op - row["op"]))
        assert math.isclose(op, row["op"], rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(float(raw["mom_11_month_adjusted_price_change"]),
                            row["momentum"], rel_tol=1e-12, abs_tol=1e-12)
        if a["outcome_pending"]:
            assert pd.isna(row["target_return"]), key
        else:
            p0 = json.loads(raw["formation_quote_detail_json"])["adj_close"]
            p1 = json.loads(raw["target_month_end_quote_detail_json"])["adj_close"]
            expected = p1 / p0 - 1
            assert math.isclose(expected, row["target_return"], rel_tol=1e-12, abs_tol=1e-12), key
            checked_returns += 1
    expected_months = [f"{y:04}-{m:02}" for y in range(2015, 2025) for m in range(1, 13)]
    assert monthly.target_month.to_list() == expected_months
    for t, month in enumerate(expected_months):
        frame = formed[formed.target_month == month].sort_values(["momentum", "ticker"]).reset_index(drop=True)
        if len(frame) % 2:
            ix = 2 * (t % ((len(frame) + 1) // 2))
            saved = omitted[omitted.target_month == month].iloc[0]
            assert saved.ticker == frame.iloc[ix].ticker
            assert saved.original_momentum_rank == ix + 1
            frame = frame.drop(index=ix)
        else:
            assert len(omitted[omitted.target_month == month]) == 0
        frame = frame.reset_index(drop=True)
        saved = choices[choices.target_month == month].sort_values("pair_index")
        assert len(frame) == 2 * len(saved)
        for j, chosen in enumerate(saved.to_dict("records")):
            a, b = frame.iloc[2*j], frame.iloc[2*j+1]
            assert (a.ticker, b.ticker) == (chosen["ticker_a"], chosen["ticker_b"])
            if a.momentum == b.momentum:
                high = low = min(a.ticker, b.ticker)
            else:
                high, low = b.ticker, a.ticker
            profit = a.ticker if a.op > b.op else b.ticker if b.op > a.op else high
            assert (profit, high, low) == (chosen["profitability_ticker"],
                                         chosen["higher_momentum_ticker"], chosen["lower_momentum_ticker"])
    # Independently derive differences and components, then compare month summaries.
    arrays = {}
    comparison = {}
    for opponent in ["higher_momentum", "lower_momentum"]:
        own = pairs.profitability_return.to_numpy(float)
        other = pairs[f"{opponent}_return"].to_numpy(float)
        same = (pairs.profitability_ticker == pairs[f"{opponent}_ticker"]).to_numpy()
        metrics = {
            "delta_identifiable_mean": np.where(same, 0.0, own-other),
            "loss_part_identifiable_mean": np.where(same, 0.0, np.minimum(own, 0)-np.minimum(other, 0)),
            "upside_part_identifiable_mean": np.where(same, 0.0, np.maximum(own, 0)-np.maximum(other, 0)),
        }
        q = pairs[["target_month"]].copy()
        for k, arr in metrics.items():
            q[k] = arr
        g = q.groupby("target_month", sort=True)
        table = g.mean(numeric_only=True).reindex(expected_months)
        orig = g.sum(numeric_only=True).reindex(expected_months).div(g.size().reindex(expected_months), axis=0)
        assert np.allclose(table.delta_identifiable_mean,
                           table.loss_part_identifiable_mean + table.upside_part_identifiable_mean)
        runner_keys = {
            "delta_identifiable_mean": "known_identifiable_mean",
            "loss_part_identifiable_mean": "known_loss_part_identifiable_mean",
            "upside_part_identifiable_mean": "known_upside_part_identifiable_mean",
        }
        for k in metrics:
            assert np.allclose(table[k], monthly[f"profitability_minus_{opponent}_{runner_keys[k]}"], atol=1e-12)
            arrays[f"{opponent}_{k}"] = table[k].to_numpy()
        assert np.allclose(orig.delta_identifiable_mean,
                           monthly[f"profitability_minus_{opponent}_known_original_weight_contribution"], atol=1e-12)
        means = table.mean().to_dict()
        comparison[opponent] = {"identified_monthly_means": means,
                               "original_weight_known_contribution": orig.mean().to_dict(),
                               "different_choice_pairs": int((~same).sum()),
                               "unknown_difference_pairs": int(np.isnan(metrics["delta_identifiable_mean"]).sum()),
                               "unchanged_choice_pairs": int(same.sum())}
        assert math.isclose(means["delta_identifiable_mean"],
                            periods["full_2015_2024"][f"profitability_minus_{opponent}"]["mean_known_identifiable_pair_difference"],
                            abs_tol=1e-12)
        loss_a = np.where(np.isnan(own), np.nan, (own < 0).astype(float))
        loss_b = np.where(np.isnan(other), np.nan, (other < 0).astype(float))
        bounds = np.column_stack([
            np.where(same, 0, np.nan_to_num(loss_a, nan=0)-np.nan_to_num(loss_b, nan=1)),
            np.where(same, 0, np.nan_to_num(loss_a, nan=1)-np.nan_to_num(loss_b, nan=0)),
        ])
        expected_bounds = pd.DataFrame(bounds, columns=["low", "high"]).assign(
            month=pairs.target_month).groupby("month").mean().reindex(expected_months).to_numpy()
        saved_bounds = np.array([json.loads(x) for x in monthly[
            f"profitability_minus_{opponent}_paired_loss_probability_delta_bounds"]])
        assert np.allclose(expected_bounds, saved_bounds, atol=1e-12)
    rng = random.Random(20261020)
    indices = np.asarray([[(s+j) % 120 for s in [rng.randrange(120) for _ in range(10)] for j in range(12)]
                          for _ in range(2000)], dtype=int)
    for k, values in arrays.items():
        estimates = np.nanmean(values[indices], axis=1)
        interval = np.quantile(estimates, [.025, .975])
        assert np.allclose(interval, [uncertainty[k]["percentile_2_5"],
                                      uncertainty[k]["percentile_97_5"]], atol=1e-12), k
    # Report-only descriptive summaries; no parameter choice or new market run.
    company_counts = formed.groupby(["ticker", "candidate_cik"]).size().sort_values(ascending=False)
    years = []
    for year in range(2015, 2025):
        f = formed[formed.target_month.str.startswith(str(year))]
        n = f.groupby("target_month").size()
        p = pairs[pairs.target_month.str.startswith(str(year))]
        years.append({"year": year, "company_months": len(f), "companies": f.candidate_cik.nunique(),
                      "monthly_min": int(n.min()), "monthly_max": int(n.max()),
                      "pairs": len(p), "unknown_stock_months": int(f.target_return.isna().sum())})
    cells = pd.read_csv(out / "sign-cells.csv")
    cell_rows = []
    for (opponent, name), f in cells.groupby(["opponent", "cell"]):
        count = int(f["count"].sum())
        cell_rows.append({"opponent": opponent, "cell": name, "count": count,
                          "mean_difference": float(f.delta_sum.sum()/count) if count else None})
    methods = {}
    for method in ["profitability", "higher_momentum", "lower_momentum"]:
        changes = monthly[f"{method}_target_weight_change"].dropna()
        counts = choices[f"{method}_ticker"].value_counts()
        methods[method] = {"target_weight_change_mean": changes.mean(),
                           "target_weight_change_median": changes.median(),
                           "observed_transitions": len(changes),
                           "selected_distinct_tickers": int(len(counts)),
                           "top5_name_counts": {str(k): int(v) for k, v in counts.head().items()}}
        full = monthly[monthly.all_methods_complete]
        selected = pairs[pairs.target_month.isin(full.target_month)]
        x = selected.groupby("target_month")[f"{method}_return"].mean().to_numpy()
        stats = periods["full_2015_2024"][method]
        assert math.isclose(float(x.mean()), stats["mean_monthly_return"], abs_tol=1e-12)
        assert math.isclose(float(x.std(ddof=1)), stats["sample_std_monthly_return"], abs_tol=1e-12)
        assert math.isclose(float(np.sort(x)[:math.ceil(.1*len(x))].mean()),
                            stats["worst_decile_mean"], abs_tol=1e-12)
    lower_col = "profitability_minus_higher_momentum_paired_loss_probability_delta_bounds"
    loss_bounds = {}
    for opponent in comparison:
        prefix = f"profitability_minus_{opponent}_"
        loss_bounds[opponent] = {
            suffix: np.mean([json.loads(x) for x in monthly[prefix+suffix]], axis=0).tolist()
            for suffix in ["paired_loss_probability_delta_bounds",
                           "loss_probability_method_bounds", "loss_probability_opponent_bounds"]}
    summary = {
        "status": "passed", "purpose": "Independent arithmetic audit of fixed result, no new efficacy experiment",
        "contract_sha256": sha(args.contract), "manifest_sha256": sha(out/"manifest.json"),
        "formula_rows": len(formed), "formula_max_abs_error": max_formula_error,
        "price_return_rows": checked_returns, "unknown_stock_months": int(formed.target_return.isna().sum()),
        "all_choices_verified": len(choices), "odd_omission_months": len(omitted),
        "comparison": comparison, "confidence_interval_components_verified": len(arrays),
        "loss_probability_bounds_independently_verified": True,
        "complete_month_mean_std_worst_decile_independently_verified": True,
        "financial_reports_used": int(formed.adsh.nunique()), "annual_coverage": years,
        "rank_ic_monthly_mean": float(monthly.op_return_spearman.mean()),
        "rank_ic_monthly_median": float(monthly.op_return_spearman.median()),
        "op_momentum_rank_correlation_mean": float(monthly.op_momentum_rank_correlation.mean()),
        "pair_gap_quantiles": {str(k): float(v) for k, v in pairs.momentum_gap.quantile([.5,.9,.95,1]).items()},
        "loss_probability_bounds_monthly_average": loss_bounds,
        "four_cells": cell_rows, "operations": methods,
        "company_months_by_ticker": [{"ticker": idx[0], "cik":idx[1], "months":int(count)}
                                   for idx, count in company_counts.items()],
        "inputs_or_results_modified": False, "network_requests": 0,
    }
    Path(args.audit_output).write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k: summary[k] for k in ["status", "formula_rows", "price_return_rows",
                                             "all_choices_verified", "unknown_stock_months"]}))


if __name__ == "__main__":
    main()
