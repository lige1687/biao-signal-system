"""Run one frozen external-mechanism study, never a production strategy."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.definitions import resolve
from lei_signal.research.month_end_rebalancing import (
    build_events, circular_block_mean_interval, expanding_predictions,
)

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric_summary(values, interval=True):
    a = np.asarray(values, dtype=float)
    assert np.isfinite(a).all()
    if not len(a):
        return {"n": 0, "mean": None, "median": None, "positive_n": 0,
                "negative_n": 0, "worst": None, "best": None, "mean_95_range": None}
    return {
        "n": len(a), "mean": float(a.mean()), "median": float(np.median(a)),
        "positive_n": int((a > 0).sum()), "negative_n": int((a < 0).sum()),
        "worst": float(a.min()), "best": float(a.max()),
        # Very short series cannot support a 12-month block assessment.
        "mean_95_range": (list(circular_block_mean_interval(a)) if interval and len(a) >= 24
                          else None),
    }


def calendar_interaction(events):
    """Same-month pairs: separate fixed calendar return from reversal slope."""
    # Within each month: placebo then end-of-month, always sampled together.
    x0 = events.placebo_relative_log.to_numpy()
    x1 = events.relative_log.to_numpy()
    features = np.stack([
        np.column_stack([np.ones(len(events)), np.zeros(len(events)), x0, np.zeros(len(events))]),
        np.column_stack([np.ones(len(events)), np.ones(len(events)), x1, x1]),
    ], axis=1)
    outcomes = np.stack([events.placebo_y.to_numpy(), events.y.to_numpy()], axis=1)

    def fit(indices):
        return np.linalg.lstsq(features[indices].reshape(-1, 4),
                               outcomes[indices].reshape(-1), rcond=None)[0]

    n = len(events)
    coefficients = fit(np.arange(n))
    interval = None
    if n >= 24:
        rng = np.random.default_rng(20261020)
        draws = []
        for _ in range(5000):
            starts = rng.integers(0, n, size=(n + 11) // 12)
            indices = ((starts[:, None] + np.arange(12)) % n).ravel()[:n]
            draws.append(fit(indices)[3])
        interval = list(np.quantile(draws, [0.025, 0.975]))
    return {
        "n_month_pairs": n,
        "formula": "y ~ intercept + EOM + relative_log + EOM*relative_log",
        "coefficients": dict(zip(["intercept", "EOM", "relative_log", "EOM*relative_log"],
                                 map(float, coefficients))),
        "interaction_95_range": interval,
        "unit": "return fraction per unit log return; same pair sampled together",
        "identity": "retrospective association, not causal identification or future prediction",
    }


def analyze(events, predictions, design):
    rows = events.copy()
    rows["signed_y"] = -np.sign(rows.drift) * rows.y
    rows["signed_y_open"] = -np.sign(rows.drift) * rows.y_open
    rows["placebo_signed_y"] = -np.sign(rows.placebo_drift) * rows.placebo_y
    periods = {"all": [design["period"]["start"], design["period"]["end"]],
               **design["period_groups"]}
    result = {"event_groups": {}, "prediction_groups": {}}
    for name, (start, end) in periods.items():
        part = rows.loc[rows.label_end.between(start, end)]
        if part.empty:
            continue
        y = part.signed_y.to_numpy()
        x = part.drift.to_numpy()
        beta = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), part.y, rcond=None)[0]
        result["event_groups"][name] = {
            "signed_y": numeric_summary(y), "signed_y_open": numeric_summary(part.signed_y_open),
            "placebo_signed_y": numeric_summary(part.placebo_signed_y),
            "end_minus_placebo": numeric_summary(part.signed_y - part.placebo_signed_y),
            "equity_overweight": numeric_summary(part.loc[part.drift > 0, "y"], False),
            "equity_underweight": numeric_summary(part.loc[part.drift < 0, "y"], False),
            "slope_y_per_drift": float(beta[1]),
            "intercept": float(beta[0]),
            "calendar_control": calendar_interaction(part),
        }
        pred = predictions.loc[predictions.label_end.between(start, end)].copy()
        if pred.empty:
            continue
        errors = {name: (pred.y - pred[f"pred_{name}"]) ** 2
                  for name in ["mean", "stock_log", "relative_log", "drift"]}
        result["prediction_groups"][name] = {
            "n": len(pred),
            "first": str(pred.signal_date.min().date()),
            "last": str(pred.signal_date.max().date()),
            "mse": {key: float(value.mean()) for key, value in errors.items()},
            "rmse": {key: float(np.sqrt(value.mean())) for key, value in errors.items()},
            "drift_vs_relative_log": numeric_summary(errors["relative_log"] - errors["drift"]),
            "relative_log_vs_stock_only": numeric_summary(errors["stock_log"] - errors["relative_log"]),
            "drift_vs_historical_mean": numeric_summary(errors["mean"] - errors["drift"]),
        }
    kept = rows.loc[~rows.label_end.dt.year.isin([2008, 2020])]
    result["exclude_2008_2020"] = {
        "signed_y": numeric_summary(kept.signed_y, False),
        "end_minus_placebo": numeric_summary(kept.signed_y - kept.placebo_signed_y, False),
        "interval": "not estimated on gapped dates",
    }
    result["worst_events"] = rows.nsmallest(5, "signed_y")[
        ["month", "drift", "y", "signed_y", "signed_y_open"]].to_dict("records")
    result["best_events"] = rows.nlargest(5, "signed_y")[
        ["month", "drift", "y", "signed_y", "signed_y_open"]].to_dict("records")
    result["price_identity"] = {
        "same_sign_months": int((np.sign(rows.drift) == np.sign(rows.relative_log)).sum()),
        "total_months": len(rows),
        "max_formula_difference": float(np.max(np.abs(
            rows.drift - (0.6 * np.exp(rows.relative_log) /
                          (0.6 * np.exp(rows.relative_log) + 0.4) - 0.6)))),
    }
    return result, rows


def main():
    frozen = json.loads((HERE / "freeze.json").read_text())
    for item in frozen["files"]:
        assert sha(item["path"]) == item["sha256"], f"source changed: {item['path']}"
    assert frozen["market_runs_before_freeze"] == 0
    binding = json.loads((HERE / "definition-binding.json").read_text())
    registry = json.loads((ROOT / binding["snapshot_path"]).read_text())
    card = resolve(registry, binding["reference"], "comparison")
    assert card["definition"]["parameters"] == {"w": 0.6}
    for source in card["sources"]:
        item = registry["sources"][source]
        assert sha(ROOT / item["path"]) == item["sha256"]
    plan = json.loads((HERE / "storage-plan.json").read_text())
    out = Path(plan["output"])
    assert out.stat().st_dev == plan["external_device"], "wrong output device"
    destination = out / "analysis-v1"
    destination.mkdir(exist_ok=False)
    attempt = {
        "started": datetime.now(timezone.utc).isoformat(), "market_run": 1,
        "destination": str(destination), "freeze_sha256": sha(HERE / "freeze.json"),
        "status": "running",
    }
    (HERE / "attempt.json").write_text(json.dumps(attempt, indent=2))
    design = json.loads((HERE / "design.json").read_text())
    qualification = json.loads((HERE / "qualification.json").read_text())
    panel = pd.read_csv(qualification["panel_path"], index_col="date", parse_dates=["date"])
    events = build_events(panel, **design["period"])
    assert len(events) == qualification["planned_event_months"]
    assert events.placebo_y.notna().all()
    predictions = expanding_predictions(events, min_train=60)
    result, rows = analyze(events, predictions, design)
    events.to_csv(destination / "events.csv", index=False, float_format="%.17g")
    predictions.to_csv(destination / "predictions.csv", index=False, float_format="%.17g")
    rows.to_csv(destination / "scored-events.csv", index=False, float_format="%.17g")
    adjusted = panel.copy()
    for s in ("SPY", "IEF"):
        adjusted[f"{s}_open"] *= adjusted[f"{s}_adjusted_close"] / adjusted[f"{s}_close"]
        adjusted[f"{s}_close"] = adjusted[f"{s}_adjusted_close"]
        adjusted[f"{s}_dividend"] = 0.0
    sensitivity = build_events(adjusted, **design["period"])
    assert sensitivity.month.equals(events.month)
    signed_adjusted = -np.sign(sensitivity.drift) * sensitivity.y
    result["adjustment_sensitivity"] = {
        "signed_y": numeric_summary(signed_adjusted),
        "different_signal_signs": int((np.sign(sensitivity.drift) != np.sign(events.drift)).sum()),
        "max_event_y_difference": float(np.max(np.abs(sensitivity.y - events.y))),
        "mean_signed_y_difference": float(np.mean(signed_adjusted - rows.signed_y)),
        "not_an_account": True,
    }
    sensitivity.to_csv(destination / "adjusted-sensitivity-events.csv", index=False, float_format="%.17g")
    result["coverage"] = {
        "common_daily_rows": len(panel), "events": len(events), "predictions": len(predictions),
        "first_event": events.month.iloc[0], "last_event": events.month.iloc[-1],
        "training_months_excluded_from_prediction": 60,
        "immature_calendar_month": "2026-10",
    }
    result["units"] = {"returns": "fraction", "mse": "fraction squared", "capital_return": False}
    result["prediction_fits"] = len(predictions) * 3
    result["actual_account_performance"] = "not evaluated"
    (destination / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    manifests = [{"name": p.name, "path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)}
                 for p in sorted(destination.iterdir()) if p.is_file()]
    attempt.update(status="completed_computation_not_reviewed",
                   ended=datetime.now(timezone.utc).isoformat(), files=manifests,
                   market_runs=1, variant_policy="one prespecified adjusted-price sensitivity")
    (HERE / "attempt.json").write_text(json.dumps(attempt, ensure_ascii=False, indent=2))
    (HERE / "results-summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
