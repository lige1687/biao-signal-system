"""Independent arithmetic review of one frozen positioning batch; never import candidate code."""
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "controller"
OUT = Path(__file__).with_name("verification.json")
summary = json.loads((CTRL / "results-summary.json").read_text())
result_path = Path(summary["source_result"]["path"])
result = json.loads(result_path.read_text())
base = result_path.parent
freeze = json.loads((CTRL / "freeze.json").read_text())
source_paths = {Path(x["path"]).name: Path(x["path"]) for x in freeze["files"]}


def rows(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def number(x):
    return float(x)


def close(a, b, tol=1e-8):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), abs_tol=tol, rel_tol=tol)


checks = []


def check(name, actual, saved, tol=1e-8):
    passed = close(actual, saved, tol) if isinstance(actual, (int, float)) or actual is None else actual == saved
    checks.append({"name": name, "pass": bool(passed), "actual": actual, "saved": saved})


assert hashlib.sha256(result_path.read_bytes()).hexdigest() == summary["source_result"]["sha256"]
for binding in freeze["files"]:
    path = Path(binding["path"])
    check("frozen_sha:" + path.name, hashlib.sha256(path.read_bytes()).hexdigest(), binding["sha256"])

spy = json.loads(source_paths["SPY.json"].read_text())["chart"]["result"][0]
dates = [dt.datetime.fromtimestamp(int(s), ZoneInfo("America/New_York")).date().isoformat()
         for s in spy["timestamp"]]
prices = np.asarray(spy["indicators"]["adjclose"][0]["adjclose"], dtype=float)
assert len(dates) == len(prices) and np.isfinite(prices).all() and (prices > 0).all()
naaim_raw = rows(source_paths["naaim-official-2026-08-19-parsed.csv"])
naaim_by_date = {r["date"]: r for r in naaim_raw}
cftc_raw = rows(source_paths["cftc-tff-futures-only-13874A-snapshot-2026-10-20.csv"])
cftc_by_date = {r["report_date_as_yyyy_mm_dd"][:10]: r for r in cftc_raw}


def error_stats(subset):
    if not subset:
        return None
    models = {}
    for model in ("mean", "prices", "position", "level", "change", "context"):
        errors = [number(r["pred_" + model]) - number(r["return63"]) for r in subset]
        models[model] = {"mse_pp2": sum(e * e for e in errors) / len(errors),
                         "mae_pp": sum(abs(e) for e in errors) / len(errors)}
    pairs = [("context", "level"), ("change", "level"), ("context", "change"),
             ("context", "prices"), ("context", "mean")]
    increments = {}
    for new, old in pairs:
        base_mse = models[old]["mse_pp2"]
        delta = base_mse - models[new]["mse_pp2"]
        increments[new + "_vs_" + old] = {"mse_reduction_pp2": delta,
                                           "mse_reduction_pct": 100 * delta / base_mse}
    return {"n": len(subset), "models": models, "increments": increments}


def compare_metrics(prefix, actual, saved):
    check(prefix + ":n", actual["n"], saved["n"])
    for model in actual["models"]:
        for measure in ("mse_pp2", "mae_pp"):
            check(prefix + ":" + model + ":" + measure,
                  actual["models"][model][measure], saved["models"][model][measure])
    for name in actual["increments"]:
        for measure in ("mse_reduction_pp2", "mse_reduction_pct"):
            check(prefix + ":" + name + ":" + measure,
                  actual["increments"][name][measure], saved["increments"][name][measure])


details = {}
predictions = {}
observations = {}
fits = {}
for source in ("naaim", "cftc"):
    pred = rows(base / f"{source}-predictions.csv")
    obs = rows(base / f"{source}-observations.csv")
    fit = json.loads((base / f"{source}-fits.json").read_text())
    predictions[source], observations[source], fits[source] = pred, obs, fit
    saved = result["candidate_results"][source]
    check(source + ":unique_report_dates", len(set(r["report_date"] for r in pred)), len(pred))
    check(source + ":fitted_records", len(fit), saved["fit_n"])
    check(source + ":six_models_same_rows", len(pred) * 6, len(pred) * 6 if all(
        all(r["pred_" + m] != "" for m in ("mean", "prices", "position", "level", "change", "context"))
        for r in pred) else -1)
    compare_metrics(source + ":all", error_stats(pred), saved["performance"])
    for name, span in (("2015-2019", (2015, 2019)), ("2020-2022", (2020, 2022)),
                       ("2023-2026partial", (2023, 2026))):
        group = [r for r in pred if span[0] <= int(r["anchor_date"][:4]) <= span[1]]
        compare_metrics(source + ":period:" + name, error_stats(group), saved["robustness"]["periods"][name])
    for year in range(2015, 2027):
        group = [r for r in pred if int(r["anchor_date"][:4]) != year]
        compare_metrics(source + ":leave_year:" + str(year), error_stats(group),
                        saved["robustness"]["leave_year_out_saved_errors"][str(year)])
    # Four nonzero sign cells plus five zero cells, including separate episodes.
    counts = {}
    episode_rows = []
    prior = None
    for r in pred:
        trend = int(r["trend"])
        direction = (number(r["change"]) > 0) - (number(r["change"]) < 0)
        key = f"trend_{trend}_change_{direction}"
        date = dt.date.fromisoformat(r["report_date"])
        if prior is None or prior[0] != key or not 6 <= (date - prior[1]).days <= 8:
            episode_rows.append({"cell": key, "first": r["report_date"], "last": r["report_date"], "n": 1})
        else:
            episode_rows[-1]["last"] = r["report_date"]
            episode_rows[-1]["n"] += 1
        prior = (key, date)
        counts[key] = counts.get(key, 0) + 1
    check(source + ":episodes", episode_rows, saved["episodes"])
    check(source + ":four_plus_zero_total", sum(counts.values()), len(pred))
    for trend in (-1, 0, 1):
        for direction in (-1, 0, 1):
            key = f"trend_{trend}_change_{direction}"
            sub = [r for r in pred if int(r["trend"]) == trend and
                   ((number(r["change"]) > 0) - (number(r["change"]) < 0)) == direction]
            v = saved["cells"][key]
            check(source + ":cell:" + key + ":n", len(sub), v["n"])
            check(source + ":cell:" + key + ":episodes", sum(e["cell"] == key for e in episode_rows), v["episodes"])
            for measure, extractor in (("return_mean_pct", lambda r: number(r["return63"])),
                                       ("risk_mean_pct", lambda r: number(r["risk63"])),
                                       ("price_residual_mean_pp", lambda r: number(r["return63"]) - number(r["pred_prices"]))):
                actual = sum(map(extractor, sub)) / len(sub) if sub else None
                check(source + ":cell:" + key + ":" + measure, actual, v[measure])
    for trend in (-1, 1):
        key = f"trend_{trend}_positive_minus_negative"
        pos = [r for r in pred if int(r["trend"]) == trend and number(r["change"]) > 0]
        neg = [r for r in pred if int(r["trend"]) == trend and number(r["change"]) < 0]
        v = saved["same_trend_positive_minus_negative"][key]
        check(source + ":contrast:" + key + ":positive_n", len(pos), v["positive_n"])
        check(source + ":contrast:" + key + ":negative_n", len(neg), v["negative_n"])
        for measure, extract in (("return_mean_pct", lambda r: number(r["return63"])),
                                 ("risk_mean_pct", lambda r: number(r["risk63"])),
                                 ("price_residual_mean_pp", lambda r: number(r["return63"]) - number(r["pred_prices"]))):
            actual = (sum(map(extract, pos)) / len(pos) - sum(map(extract, neg)) / len(neg)) if pos and neg else None
            check(source + ":contrast:" + key + ":" + measure, actual, v[measure])
    for r in pred:
        year = int(r["anchor_date"][:4])
        target_end = dt.date.fromisoformat(r["target_end"])
        check(source + ":mature_test:" + r["report_date"], target_end < dt.date(2027, 1, 1), True)
        if r["actual_release_at"] != "":
            check(source + ":release_null:" + r["report_date"], r["actual_release_at"], "")
    for f in fit:
        year = f["year"]
        training = [r for r in obs if r["mature"] == "True" and r["target_end"] < f"{year}-01-01"]
        check(source + f":fit_train_n:{year}:{f['model']}", len(training), f["train_n"])
        check(source + f":fit_maturity:{year}:{f['model']}", max(r["target_end"] for r in training), f["latest_train_target_end"])
    details[source] = {"prediction_rows": len(pred), "observation_rows": len(obs), "fit_records": len(fit),
                       "cell_counts": counts, "years": {str(y): sum(int(r["anchor_date"][:4]) == y for r in pred)
                                                 for y in range(2015, 2027)}}

# Independent raw-input and adjusted-price samples: first 2015 row, a 2020 row per source.
for source in ("naaim", "cftc"):
    pred = predictions[source]
    chosen = [pred[0], next(r for r in pred if r["anchor_date"].startswith("2020"))]
    samples = []
    for r in chosen:
        old, new = r["lag_report_date"], r["report_date"]
        if source == "naaim":
            old_level = number(naaim_by_date[old]["mean"])
            new_level = number(naaim_by_date[new]["mean"])
            check(source + ":raw_level:" + new, new_level, number(r["level"]))
            check(source + ":raw_change:" + new, new_level - old_level, number(r["change"]))
            source_values = {"old_mean": old_level, "new_mean": new_level}
        else:
            a, b = cftc_by_date[old], cftc_by_date[new]
            oi0, oi1 = number(a["open_interest_all"]), number(b["open_interest_all"])
            l0, l1 = number(a["asset_mgr_positions_long"]), number(b["asset_mgr_positions_long"])
            s0, s1 = number(a["asset_mgr_positions_short"]), number(b["asset_mgr_positions_short"])
            sp0, sp1 = number(a["asset_mgr_positions_spread"]), number(b["asset_mgr_positions_spread"])
            expected = {"level": 100 * (l1 - s1) / oi1, "change": 100 * ((l1 - s1) - (l0 - s0)) / oi0,
                        "delta_long_old_oi": 100 * (l1 - l0) / oi0,
                        "minus_delta_short_old_oi": -100 * (s1 - s0) / oi0,
                        "delta_oi_old_oi": 100 * (oi1 - oi0) / oi0,
                        "delta_spread_old_oi": 100 * (sp1 - sp0) / oi0}
            for key, value in expected.items():
                check(source + ":raw:" + new + ":" + key, value, number(r[key]))
            source_values = {"old_oi": oi0, "new_oi": oi1, "old_long": l0, "new_long": l1,
                             "old_short": s0, "new_short": s1}
        anchor, lag = int(r["anchor_index"]), int(r["lag_anchor_index"])
        start, end = int(r["target_start_index"]), int(r["target_end_index"])
        check(source + ":anchor_date:" + new, dates[anchor], r["anchor_date"])
        check(source + ":target_start:" + new, dates[start], r["target_start"])
        check(source + ":target_end:" + new, dates[end], r["target_end"])
        check(source + ":target_span:" + new, end - start, 63)
        for key, val in {"r4w": 100 * (prices[anchor] / prices[lag] - 1),
                         "r63": 100 * (prices[anchor] / prices[anchor - 63] - 1),
                         "r252": 100 * (prices[anchor] / prices[anchor - 252] - 1),
                         "drawdown252": 100 * (prices[anchor] / max(prices[anchor - 251:anchor + 1]) - 1),
                         "return63": 100 * (prices[end] / prices[start] - 1)}.items():
            check(source + ":raw_price:" + new + ":" + key, float(val), number(r[key]))
        daily = prices[anchor - 62:anchor + 1] / prices[anchor - 63:anchor] - 1
        check(source + ":raw_price:" + new + ":vol63", float(np.std(daily) * math.sqrt(252) * 100), number(r["vol63"]))
        peak = prices[start]
        risk = 0.0
        for price in prices[start:end + 1]:
            peak = max(peak, price)
            risk = max(risk, 100 * (1 - price / peak))
        check(source + ":raw_price:" + new + ":risk63", risk, number(r["risk63"]))
        check(source + ":trend:" + new, (number(r["r252"]) > 0) - (number(r["r252"]) < 0), int(r["trend"]))
        check(source + ":interaction:" + new, int(r["trend"]) * number(r["change"]), number(r["interaction"]))
        samples.append({"report_date": new, "lag_report_date": old, "anchor_date": r["anchor_date"],
                        "target_start": r["target_start"], "target_end": r["target_end"],
                        "source_values": source_values, "target_return_pct": float(100 * (prices[end] / prices[start] - 1)),
                        "target_peak_to_trough_pct": risk})
    details[source]["raw_samples"] = samples

# Exactly one independent augmented least-squares solve per source, year 2020 context.
for source in ("naaim", "cftc"):
    annual = next(f for f in fits[source] if f["year"] == 2020 and f["model"] == "context")
    training = [r for r in observations[source] if r["mature"] == "True" and r["target_end"] < "2020-01-01"]
    test = [r for r in predictions[source] if r["anchor_date"].startswith("2020")]
    columns = annual["columns"]
    x = np.asarray([[number(r[c]) for c in columns] for r in training])
    y = np.asarray([number(r["return63"]) for r in training])
    mu, sigma = x.mean(axis=0), x.std(axis=0)
    sigma[sigma == 0] = 1
    z = np.column_stack((np.ones(len(x)), (x - mu) / sigma))
    p = z.shape[1]
    penalty = np.zeros((p - 1, p))
    penalty[:, 1:] = math.sqrt(0.001 * len(x)) * np.eye(p - 1)
    coefficients = np.linalg.lstsq(np.vstack((z, penalty)), np.r_[y, np.zeros(p - 1)], rcond=None)[0]
    for j, value in enumerate(coefficients):
        check(source + f":independent_lstsq_2020_context_beta:{j}", float(value), annual["beta"][j], 1e-7)
    for r in test:
        zrow = np.r_[1, [(number(r[c]) - mu[j]) / sigma[j] for j, c in enumerate(columns)]]
        check(source + ":independent_lstsq_2020_context_prediction:" + r["report_date"],
              float(zrow @ coefficients), number(r["pred_context"]), 1e-7)
    details[source]["independent_solve"] = {"year": 2020, "model": "context", "train_n": len(training),
                                             "test_n": len(test), "method": "augmented_numpy_lstsq_no_normal_equations",
                                             "max_beta_abs_difference": float(np.max(np.abs(coefficients - annual["beta"])))}

# Paired circular calendar-week resampling, independently implemented from frozen seed and output.
for source in ("naaim", "cftc"):
    pred = predictions[source]
    anchors = [dt.date.fromisoformat(r["anchor_date"]) for r in pred]
    origin = min(anchors) - dt.timedelta(days=min(anchors).weekday())
    slots = np.asarray([(d - origin).days // 7 for d in anchors], dtype=int)
    width = int(max(slots) + 1)
    loss_gap = np.asarray([(number(r["pred_level"]) - number(r["return63"])) ** 2 -
                           (number(r["pred_context"]) - number(r["return63"])) ** 2 for r in pred])
    seed = 20261020 + 26 + (100 if source == "cftc" else 0)
    generator = np.random.default_rng(seed)
    estimates = []
    for _ in range(2000):
        starts = generator.integers(0, width, size=math.ceil(width / 26))
        sampled = np.concatenate([(s + np.arange(26)) % width for s in starts])[:width]
        counts = np.bincount(sampled, minlength=width)[slots]
        if counts.sum():
            estimates.append(float(np.dot(counts, loss_gap) / counts.sum()))
    q = np.quantile(estimates, [0.025, 0.975])
    saved = result["candidate_results"][source]["intervals"][0]
    check(source + ":block26:origin", origin.isoformat(), saved["calendar_origin_monday"])
    check(source + ":block26:slots", width, saved["calendar_slots"])
    check(source + ":block26:draws", len(estimates), saved["descriptive_95pct_mse_reduction_pp2"]["context_vs_level"]["valid_draws"])
    for i in (0, 1):
        check(source + f":block26:interval:{i}", float(q[i]),
              saved["descriptive_95pct_mse_reduction_pp2"]["context_vs_level"]["interval"][i], 1e-7)
    details[source]["block26_context_vs_level"] = {"interval": q.tolist(), "draws": len(estimates)}

check("total_saved_fits", sum(len(v) for v in fits.values()), result["total_annual_fits"])
check("summary_total_fits", result["total_annual_fits"], summary["total_annual_fits"])
check("source_release_status", result["source_release_status"], "current-vintage retrospective association only")
check("all_actual_release_unknown", sum(r["actual_release_at"] != "" for source in predictions for r in predictions[source]), 0)
report = {"status": "pass" if all(x["pass"] for x in checks) else "fail",
          "checked_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
          "source_results_path": str(result_path),
          "source_results_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
          "freeze_file_bindings_actual": len(freeze["files"]),
          "frozen_old_bindings_boolean_only": freeze["old_freeze_22_bindings_unchanged"],
          "checks_total": len(checks), "checks_failed": [x for x in checks if not x["pass"]],
          "independent_parameter_solves": 2, "additional_model_searches": 0,
          "details": details,
          "boundary": "Numerical saved-vintage audit only; missing actual_release_at prevents historical trade-time qualification."}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"status": report["status"], "checks_total": len(checks),
                  "failures": report["checks_failed"][:5], "details": details}, ensure_ascii=False))
