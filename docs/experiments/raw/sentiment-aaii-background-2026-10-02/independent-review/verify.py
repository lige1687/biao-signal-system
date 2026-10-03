#!/usr/bin/env python3
"""Independent, bounded verification of the frozen AAII 20-survey study.

This script does not import the study adapter or its OLS helpers. It uses only
the frozen protocol, saved observations/predictions, and the two frozen inputs.
It runs exactly the 12 OLS fits declared by the independent review contract.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "docs/experiments/raw/sentiment-aaii-background-2026-10-02"
OLD = ROOT / "docs/experiments/raw/sentiment-aaii-extremes-increment-2026-09-29/inputs"
OUT = RAW / "independent-review"
YEARS = (2010, 2020, 2026)
MODELS = ("I", "B", "X", "BX")
MODEL_FEATURES = {
    "I": [],
    "B": ["r20", "r63", "dma200", "dd252", "rv20", "x"],
    "X": ["m20"],
    "BX": ["r20", "r63", "dma200", "dd252", "rv20", "x", "m20"],
}
PRED_COLUMNS = {m: f"pred_{m}" for m in MODELS}
TOL = 1e-9


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=True)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def bool_col(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().map({"true": True, "false": False}).fillna(False)


def mse_rmse(frame: pd.DataFrame, prediction_columns: dict[str, str]) -> dict:
    y = frame["y"].to_numpy(float)
    out = {}
    for model, col in prediction_columns.items():
        err = y - frame[col].to_numpy(float)
        mse = float(np.mean(err * err))
        out[model] = {"mse": mse, "rmse": math.sqrt(mse)}
    return out


def first_price_index(prices: pd.DataFrame, assumed_availability: date) -> int:
    # First saved price date strictly later than the assumed +7-day boundary.
    price_dates = pd.to_datetime(prices["Date"]).dt.date.to_list()
    lo, hi = 0, len(price_dates)
    while lo < hi:
        mid = (lo + hi) // 2
        if price_dates[mid] <= assumed_availability:
            lo = mid + 1
        else:
            hi = mid
    return lo


def main() -> None:
    protocol = json.loads((RAW / "protocol.json").read_text())
    definition = json.loads((RAW / "definition.json").read_text())
    results = json.loads((RAW / "run-01/results.json").read_text())
    source = read_csv(OLD / "aaii-candidate-values.csv")
    prices = read_csv(OLD / "px_SPY.csv")
    observations = read_csv(RAW / "run-01/observations.csv")
    predictions = read_csv(RAW / "run-01/predictions.csv")

    # Frozen calendar-week mean: a 20-row window is valid only if its endpoint
    # week is exactly 19 weeks after its start week.
    source_dates = pd.to_datetime(source["date"])
    source_weeks = source_dates.dt.to_period("W-SUN")
    week_ord = source_weeks.astype("int64").to_numpy()
    x = pd.to_numeric(source["spread_pp"]).to_numpy(float)
    ma_stored = pd.to_numeric(source["ma20_pp"], errors="coerce").to_numpy(float)
    ma_calc = np.full(len(source), np.nan)
    for i in range(19, len(source)):
        if week_ord[i] - week_ord[i - 19] == 19:
            ma_calc[i] = float(np.mean(x[i - 19:i + 1]))
    ma_equal = np.isclose(ma_calc, ma_stored, atol=TOL, rtol=0)
    assert int(np.isfinite(ma_calc).sum()) == 1962, "unexpected complete survey-window count"
    assert int(np.isfinite(ma_stored).sum()) == 2019, "unexpected stored MA count"
    assert int((np.isfinite(ma_stored) & ~np.isfinite(ma_calc)).sum()) == 57
    assert bool(np.all(ma_equal[np.isfinite(ma_calc)])), "stored ma20_pp differs on calendar-complete windows"

    # Enumerate all missing calendar survey weeks and every unavailable window.
    unique_week_set = set(week_ord.tolist())
    all_weeks = list(range(int(week_ord[0]), int(week_ord[-1]) + 1))
    missing_week_ord = [w for w in all_weeks if w not in unique_week_set]
    missing_calendar_weeks = []
    for w in missing_week_ord:
        # Resolve Monday from the first observed calendar week and ordinal gap.
        first_monday = source_weeks.iloc[0].start_time.date()
        monday = first_monday + timedelta(weeks=w - int(week_ord[0]))
        missing_calendar_weeks.append({"week_ordinal": int(w), "monday": monday.isoformat(),
                                       "sunday": (monday + timedelta(days=6)).isoformat()})
    invalid_windows = []
    for i in range(19, len(source)):
        if week_ord[i] - week_ord[i - 19] != 19:
            in_window = [w for w in missing_week_ord if week_ord[i - 19] <= w <= week_ord[i]]
            invalid_windows.append({
                "source_row_index": i,
                "source_start_date": source["date"].iloc[i - 19],
                "source_end_date": source["date"].iloc[i],
                "window_start_week": int(week_ord[i - 19]),
                "window_end_week": int(week_ord[i]),
                "missing_week_ordinals": [int(w) for w in in_window],
            })
    assert len(missing_week_ord) == 3, f"expected 3 missing calendar weeks, got {len(missing_week_ord)}"
    assert len(invalid_windows) == 57, f"expected 57 post-gap windows, got {len(invalid_windows)}"

    # Headline metrics and coverage counts reaggregated from saved rows.
    pred = predictions.copy()
    obs = observations.copy()
    for col in ("t", "target_end"):
        obs[col] = pd.to_datetime(obs[col], errors="coerce")
    for col in ("date",):
        pred[col] = pd.to_datetime(pred[col], errors="coerce")
    obs_eligible = bool_col(obs["eligible"])
    base_eligible = bool_col(obs["base_eligible"])
    eval_mask = obs_eligible & obs["t"].ge(pd.Timestamp("2010-01-01")) & obs["t"].le(pd.Timestamp("2026-06-30"))
    assert int(base_eligible.sum()) == 1615
    assert int(obs_eligible.sum()) == 1558
    assert int(eval_mask.sum()) == 816
    assert len(pred) == 816
    assert pred["date"].is_unique
    saved_eval = pred.merge(obs.loc[eval_mask, ["t", "y"]], left_on="date", right_on="t", how="outer", indicator=True)
    assert saved_eval["_merge"].eq("both").all(), "prediction dates do not match eligible evaluation observations"
    headline_metrics = mse_rmse(pred, PRED_COLUMNS)
    headline_differences = {}
    for model in MODELS:
        for metric in ("mse", "rmse"):
            saved = float(results["overall"][metric][model])
            recomputed = headline_metrics[model][metric]
            headline_differences[f"{model}.{metric}"] = recomputed - saved
            assert abs(recomputed - saved) <= TOL, f"headline mismatch {model}.{metric}"

    # Direct input checks for earliest eligible evaluation observation in each
    # declared audit year, including raw 20-week mean and raw 120-quote target.
    source_row_by_date = {str(row.date): int(i) for i, row in source.iterrows()}
    px_dates = pd.to_datetime(prices["Date"]).dt.date.to_list()
    close = pd.to_numeric(prices["Close"], errors="coerce").to_numpy(float)
    direct_checks = []
    for year in YEARS:
        year_rows = obs.loc[eval_mask & obs["t"].dt.year.eq(year)].sort_values("t")
        assert len(year_rows), f"no eligible evaluation observations in {year}"
        row = year_rows.iloc[0]
        source_index = int(row["source_row"])
        source_rec = source.iloc[source_index]
        reported = pd.Timestamp(source_rec["date"]).date()
        k = first_price_index(prices, reported + timedelta(days=7))
        assert k == int(row["t_index"])
        assert px_dates[k] == row["t"].date()
        start_i, end_i = k + 1, k + 121
        assert end_i < len(close)
        direct_y = 100 * (close[end_i] / close[start_i] - 1)
        assert px_dates[start_i] == pd.Timestamp(row["target_start"]).date()
        assert px_dates[end_i] == pd.Timestamp(row["target_end"]).date()
        assert abs(direct_y - float(row["y"])) <= TOL
        start_week = week_ord[source_index]
        expected_mean = float(np.mean(x[source_index - 19:source_index + 1]))
        assert start_week - week_ord[source_index - 19] == 19
        assert abs(expected_mean - float(row["m20"])) <= TOL
        # Independently recompute five price-background features at t.
        c_t = close[k]
        r20 = 100 * (c_t / close[k - 20] - 1)
        r63 = 100 * (c_t / close[k - 63] - 1)
        dma200 = 100 * (c_t / np.mean(close[k - 199:k + 1]) - 1)
        dd252 = 100 * (c_t / np.max(close[k - 251:k + 1]) - 1)
        rets = close[k - 19:k + 1] / close[k - 20:k] - 1
        rv20 = 100 * np.std(rets, ddof=1) * math.sqrt(20)
        direct_features = {"r20": r20, "r63": r63, "dma200": dma200, "dd252": dd252, "rv20": rv20}
        feature_differences = {name: value - float(row[name]) for name, value in direct_features.items()}
        assert max(abs(v) for v in feature_differences.values()) <= TOL
        direct_checks.append({
            "year": year,
            "source_date": reported.isoformat(),
            "observation_date": px_dates[k].isoformat(),
            "mean20_source_dates": [str(source["date"].iloc[source_index - 19]), str(source["date"].iloc[source_index])],
            "mean20_sum_pp": float(np.sum(x[source_index - 19:source_index + 1])),
            "mean20_recomputed_pp": expected_mean,
            "mean20_saved_pp": float(row["m20"]),
            "target_start_index": start_i,
            "target_end_index": end_i,
            "target_start_date": px_dates[start_i].isoformat(),
            "target_start_close": float(close[start_i]),
            "target_end_date": px_dates[end_i].isoformat(),
            "target_end_close": float(close[end_i]),
            "target120_recomputed_pp": direct_y,
            "target120_saved_pp": float(row["y"]),
            "price_feature_differences_from_observation": feature_differences,
        })

    # Counterexample requested: remove 2020 eval predictions only, no fit.
    no_2020 = pred.loc[pred["date"].dt.year.ne(2020)].copy()
    no_2020_metrics = mse_rmse(no_2020, PRED_COLUMNS)
    delete_2020 = {
        "rows_removed": int(len(pred) - len(no_2020)),
        "remaining_rows": len(no_2020),
        "metrics": no_2020_metrics,
        "difference_from_full_mse": {
            m: no_2020_metrics[m]["mse"] - headline_metrics[m]["mse"] for m in MODELS
        },
        "fits_used": 0,
    }

    # Prepare exactly 12 predeclared direct least-squares fits. Each attempt is
    # persisted as running before np.linalg.lstsq is called.
    ledger_path = OUT / "trials.json"
    ledger = {"contracted_fit_limit": 12, "trials": [], "completed_fit_count": 0,
              "state": "prepared", "fits_started": 0}
    write_json(ledger_path, ledger)
    selected_fit_results = []
    all_max_mature_t = None
    all_max_mature_end = None
    prediction_differences = []
    for year in YEARS:
        cutoff = pd.Timestamp(f"{year}-01-01")
        train_mask = obs_eligible & obs["t"].lt(cutoff) & obs["target_end"].lt(cutoff)
        eval_year_mask = eval_mask & obs["t"].dt.year.eq(year)
        train = obs.loc[train_mask].copy()
        eval_rows = obs.loc[eval_year_mask].copy()
        assert len(train) >= 100
        assert len(eval_rows) == int(pred["date"].dt.year.eq(year).sum())
        assert train["target_end"].max() < cutoff
        assert train["t"].max() < cutoff
        max_t = train["t"].max().date().isoformat()
        max_end = train["target_end"].max().date().isoformat()
        all_max_mature_t = max(all_max_mature_t or max_t, max_t)
        all_max_mature_end = max(all_max_mature_end or max_end, max_end)

        for model in MODELS:
            features = MODEL_FEATURES[model]
            trial_id = f"{year}-{model}"
            trial = {"trial_id": trial_id, "year": year, "model": model,
                     "status": "running_before_fit", "fit_call_count": 0,
                     "training_rows": len(train), "evaluation_rows": len(eval_rows),
                     "train_t_max": max_t, "train_target_end_max": max_end}
            ledger["trials"].append(trial)
            ledger["state"] = "running"
            ledger["fits_started"] += 1
            write_json(ledger_path, ledger)

            y_train = train["y"].to_numpy(float)
            if features:
                raw_train = train[features].to_numpy(float)
                means = raw_train.mean(axis=0)
                stds = raw_train.std(axis=0, ddof=0)
                if not np.isfinite(stds).all() or np.any(stds <= 0):
                    raise ValueError(f"invalid training scale in {trial_id}")
                z_train = (raw_train - means) / stds
                z_eval = (eval_rows[features].to_numpy(float) - means) / stds
            else:
                means = np.array([], dtype=float)
                stds = np.array([], dtype=float)
                z_train = np.empty((len(train), 0), dtype=float)
                z_eval = np.empty((len(eval_rows), 0), dtype=float)
            # Exactly one direct fit call for this declared year/model pair.
            design_train = np.column_stack([np.ones(len(train)), z_train])
            design_eval = np.column_stack([np.ones(len(eval_rows)), z_eval])
            coef, residuals, rank, singular = np.linalg.lstsq(design_train, y_train, rcond=None)
            trial["fit_call_count"] = 1
            trial["status"] = "fit_complete"
            trial["rank"] = int(rank)
            trial["columns_including_intercept"] = design_train.shape[1]
            trial["max_abs_training_residual"] = float(np.max(np.abs(design_train @ coef - y_train)))
            ledger["completed_fit_count"] += 1
            write_json(ledger_path, ledger)

            direct = design_eval @ coef
            key = eval_rows[["t", "y"]].copy()
            key["direct"] = direct
            saved_cols = pred[["date", PRED_COLUMNS[model]]].copy()
            saved = key.merge(saved_cols, left_on="t", right_on="date", how="left", validate="one_to_one")
            assert saved[PRED_COLUMNS[model]].notna().all(), f"missing saved prediction in {trial_id}"
            deltas = saved["direct"].to_numpy(float) - saved[PRED_COLUMNS[model]].to_numpy(float)
            max_abs = float(np.max(np.abs(deltas)))
            prediction_differences.append(max_abs)
            assert max_abs <= TOL, f"direct predictions differ beyond tolerance in {trial_id}: {max_abs}"
            direct_mse = float(np.mean((key["y"].to_numpy(float) - direct) ** 2))
            saved_mse = float(np.mean((saved["y"].to_numpy(float) - saved[PRED_COLUMNS[model]].to_numpy(float)) ** 2))
            mse_delta = direct_mse - saved_mse
            assert abs(mse_delta) <= TOL, f"annual score mismatch in {trial_id}"
            selected_fit_results.append({
                "trial_id": trial_id, "status": "fit_complete",
                "train_rows": len(train), "eval_rows": len(eval_rows),
                "train_t_max": max_t, "train_target_end_max": max_end,
                "max_abs_prediction_difference": max_abs,
                "direct_eval_mse": direct_mse, "saved_eval_mse": saved_mse,
                "mse_difference": mse_delta,
                "intercept": float(coef[0]),
                "standardization_mean": means.tolist(),
                "standardization_population_std": stds.tolist(),
            })

    assert ledger["fits_started"] == 12 and ledger["completed_fit_count"] == 12
    ledger["state"] = "complete"
    write_json(ledger_path, ledger)
    report = {
        "status": "verified",
        "scope": "Independent arithmetic, row counts, raw-input examples, saved-score checks, and exactly 12 direct least-squares fits",
        "fit_budget": {"limit": 12, "started": ledger["fits_started"], "completed": ledger["completed_fit_count"],
                       "models": list(MODELS), "years": list(YEARS), "intercept_included_in_every_fit": True},
        "calendar_mean": {
            "source_rows": len(source), "unique_calendar_weeks": len(unique_week_set),
            "first_date": str(source["date"].iloc[0]), "last_date": str(source["date"].iloc[-1]),
            "missing_calendar_weeks": missing_calendar_weeks,
            "prefix_unavailable_windows": [
                {"source_row_index": i, "source_date": str(source["date"].iloc[i])} for i in range(19)
            ],
            "post_gap_unavailable_window_count": len(invalid_windows),
            "post_gap_unavailable_windows": invalid_windows,
            "complete_calendar_windows": int(np.isfinite(ma_calc).sum()),
            "stored_ma_values": int(np.isfinite(ma_stored).sum()),
            "max_abs_difference_on_complete_windows": float(np.nanmax(np.abs(ma_calc - ma_stored))),
        },
        "reaggregated_coverage": {
            "observations_rows": len(obs), "base_eligible": int(base_eligible.sum()),
            "common_eligible": int(obs_eligible.sum()), "common_evaluation": int(eval_mask.sum()),
            "evaluation_first": pred["date"].min().date().isoformat(),
            "evaluation_last": pred["date"].max().date().isoformat(),
        },
        "overall_scores_recomputed_from_predictions": headline_metrics,
        "overall_score_difference_recomputed_minus_saved": headline_differences,
        "manual_raw_input_checks": direct_checks,
        "maturity_boundary": {
            "maximum_training_observation_date_across_fits": all_max_mature_t,
            "maximum_training_target_end_date_across_fits": all_max_mature_end,
            "all_training_target_endpoints_strictly_before_year_cutoff": True,
            "selected_fits": [{k: r[k] for k in ("trial_id", "train_t_max", "train_target_end_max", "train_rows", "eval_rows")} for r in selected_fit_results],
        },
        "selected_fit_prediction_and_score_differences": selected_fit_results,
        "maximum_absolute_prediction_difference": max(prediction_differences),
        "delete_2020_counterexample_no_fits": delete_2020,
        "all_contract_checks_passed": True,
        "notes": [
            "Direct fits use explicit ones-column intercept and np.linalg.lstsq; no project adapter or workflow OLS helper is imported.",
            "For the prediction comparison, saved rows are matched by evaluation date and original target.",
            "Historical release and adjusted-price vintages remain unknown as stated in the frozen protocol."
        ],
    }
    write_json(OUT / "review.json", report)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    main()
