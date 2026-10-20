"""Bounded current-vintage positioning change research (not a trading rule).

``prepare`` writes only source/feature qualification and future endpoint dates.
``synthetic`` checks arithmetic/time invariants without market outcomes.
``run`` is deliberately gated by a controller-written freeze manifest; it must
not be invoked until input qualification and method are frozen separately.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
OLD = RAW.parent / "contrarian-market-data-research-2026-10-20"
DESIGN = RAW / "controller/design-final.json"
OLD_PLAN = OLD / "storage-plan.json"
NEW_PLAN = RAW / "storage-plan.json"
OLD_PRICE = OLD / "controller/price-input-reuse.json"
PRICE_BASE = ["r4w", "r63", "r252", "vol63", "drawdown252", "trend"]
MODEL_NAMES = ("mean", "prices", "position", "level", "change", "context")
COMPARISONS = (("context", "level"), ("change", "level"),
               ("context", "change"), ("context", "prices"),
               ("context", "mean"))
NAAIM_ANOMALIES = {"2018-08-08", "2021-04-07", "2022-06-22"}
CFTC_MASKS = (("2013-10-01", "2013-12-31"),
              ("2018-12-24", "2019-03-31"),
              ("2023-01-01", "2023-03-31"),
              ("2025-09-30", "2025-12-31"))


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2,
                                     allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def csv_write(path, rows):
    if not rows:
        raise ValueError("cannot write empty CSV without schema")
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def bound_output():
    plan = read_json(NEW_PLAN)
    output = Path(plan["output"])
    mount = Path(plan["external_mount"])
    if (not output.is_dir() or not mount.is_dir()
            or output.stat().st_dev != int(plan["external_device"])
            or mount.stat().st_dev != int(plan["external_device"])):
        raise RuntimeError("bound external result is unavailable or on a different device")
    if not output.is_relative_to(mount):
        raise RuntimeError("external output escaped registered mount")
    return output


def old_sources():
    old = read_json(OLD_PLAN)
    root = Path(old["output"])
    if not root.is_dir() or root.stat().st_dev != int(old["external_device"]):
        raise RuntimeError("bound old source device unavailable")
    return {
        "naaim_official": root / "naaim/naaim-official-2026-08-19-parsed.csv",
        "naaim_extension": root / "naaim/winterresearch-naaim-parsed.csv",
        "cftc": root / "us-cftc/cftc-tff-futures-only-13874A-snapshot-2026-10-20.csv",
    }


def prices():
    """Exact saved adjusted-close parser; never omit a missing quote row."""
    meta = read_json(OLD_PRICE)["source"]
    path = Path(meta["path"])
    if digest(path) != meta["sha256"]:
        raise ValueError("saved SPY price hash changed")
    item = read_json(path)["chart"]["result"][0]
    raw = item["indicators"]["adjclose"][0]["adjclose"]
    timestamps = item["timestamp"]
    if len(raw) != len(timestamps):
        raise ValueError("SPY timestamp/close mismatch")
    dates, closes = [], []
    for epoch, value in zip(timestamps, raw):
        if value is None or not math.isfinite(float(value)) or float(value) <= 0:
            raise ValueError("nonpositive/missing adjusted close; no compression")
        dates.append(dt.datetime.fromtimestamp(epoch, ZoneInfo("America/New_York")).date())
        closes.append(float(value))
    if dates != sorted(set(dates)):
        raise ValueError("SPY dates must be unique and increasing")
    return dates, np.asarray(closes), path


def anchor_after_report_week(report_date, dates):
    """First actual quote strictly after Friday of report week."""
    friday = report_date + dt.timedelta(days=4 - report_date.weekday())
    import bisect
    return bisect.bisect_right(dates, friday), friday


def masked_cftc(date):
    value = date.isoformat() if isinstance(date, dt.date) else str(date)
    return value == "2017-03-28" or any(a <= value <= b for a, b in CFTC_MASKS)


def source_rows():
    paths = old_sources()
    # The parsed official Mean is authoritative. Duplicate values reflect
    # workbook display precision and must agree to 0.005 pp.
    grouped = {}
    for row in csv_rows(paths["naaim_official"]):
        grouped.setdefault(row["date"], []).append(float(row["mean"]))
    if not grouped or any(max(x) - min(x) > 0.005 for x in grouped.values()):
        raise ValueError("official Mean duplicates conflict")
    official_end = max(grouped)
    naaim = []
    for date, vals in sorted(grouped.items()):
        if date in ("2014-03-18", "2014-03-19"):
            continue
        naaim.append({"date": date, "level": vals[-1], "source": "official_mean",
                      "number_mean_anomaly": date in NAAIM_ANOMALIES})
    for row in csv_rows(paths["naaim_extension"]):
        date, value = row["date"], float(row["exposure"])
        if date in grouped:
            if abs(value - grouped[date][-1]) > 0.005:
                raise ValueError("extension conflicts with official Mean")
        elif date > official_end:
            naaim.append({"date": date, "level": value, "source": "public_extension",
                          "number_mean_anomaly": False})
    naaim.sort(key=lambda x: x["date"])
    cftc = []
    for row in csv_rows(paths["cftc"]):
        date = row["report_date_as_yyyy_mm_dd"][:10]
        if date < "2011-01-01":
            continue
        if row["cftc_contract_market_code"] != "13874A":
            raise ValueError("unexpected CFTC contract")
        oi = int(row["open_interest_all"])
        if oi <= 0:
            raise ValueError("nonpositive CFTC open interest")
        long, short = int(row["asset_mgr_positions_long"]), int(row["asset_mgr_positions_short"])
        spread = int(row["asset_mgr_positions_spread"])
        if min(long, short, spread) < 0:
            raise ValueError("negative position")
        cftc.append({"date": date, "long": long, "short": short,
                     "spread": spread, "oi": oi, "source": "official_current_vintage"})
    for name, rows in (("naaim", naaim), ("cftc", cftc)):
        days = [r["date"] for r in rows]
        if days != sorted(set(days)):
            raise ValueError(f"{name} source dates not unique and increasing")
    return {"naaim": naaim, "cftc": cftc}, paths


def valid_five(rows, name):
    dates = [dt.date.fromisoformat(r["date"]) for r in rows]
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    return (len(rows) == 5 and 26 <= (dates[-1] - dates[0]).days <= 30
            and all(6 <= gap <= 8 for gap in gaps)
            and (name != "cftc" or (dates[0].year >= 2011
                                     and not any(masked_cftc(day) for day in dates))))


def position_features(first, last, name):
    if name == "naaim":
        return {"level": last["level"], "change": last["level"] - first["level"],
                "number_mean_anomaly_window": False}
    old_oi, new_oi = first["oi"], last["oi"]
    dl = 100 * (last["long"] - first["long"]) / old_oi
    ds = -100 * (last["short"] - first["short"]) / old_oi
    result = {"level": 100 * (last["long"] - last["short"]) / new_oi,
              "change": dl + ds, "delta_long_old_oi": dl,
              "minus_delta_short_old_oi": ds,
              "delta_oi_old_oi": 100 * (new_oi - old_oi) / old_oi,
              "delta_spread_old_oi": 100 * (last["spread"] - first["spread"]) / old_oi}
    if not math.isclose(result["change"], dl + ds, abs_tol=1e-12):
        raise AssertionError("CFTC attribution identity")
    return result


def past_price_features(close, current, lagged):
    if min(current, lagged) < 252:
        raise ValueError("price warmup incomplete")
    daily = close[current - 62:current + 1] / close[current - 63:current] - 1
    r252 = 100 * (close[current] / close[current - 252] - 1)
    return {"r4w": 100 * (close[current] / close[lagged] - 1),
            "r63": 100 * (close[current] / close[current - 63] - 1),
            "r252": r252,
            "vol63": float(np.std(daily, ddof=0) * math.sqrt(252) * 100),
            "drawdown252": 100 * (close[current] / max(close[current - 251:current + 1]) - 1),
            "trend": int(np.sign(r252))}


def build_schedule(name, rows, dates, close):
    """No future close, future return, or risk value is read here."""
    result, reasons, structural_pairs = [], {}, 0
    for i in range(4, len(rows)):
        five = rows[i - 4:i + 1]
        if not valid_five(five, name):
            reasons["invalid_five_report_window"] = reasons.get("invalid_five_report_window", 0) + 1
            continue
        structural_pairs += 1
        first, last = five[0], five[-1]
        current, friday = anchor_after_report_week(dt.date.fromisoformat(last["date"]), dates)
        lagged, _ = anchor_after_report_week(dt.date.fromisoformat(first["date"]), dates)
        if current >= len(dates) or lagged >= len(dates):
            reasons["anchor_beyond_saved_price"] = reasons.get("anchor_beyond_saved_price", 0) + 1
            continue
        if min(current, lagged) < 252:
            reasons["price_warmup"] = reasons.get("price_warmup", 0) + 1
            continue
        start, end = current + 1, current + 64
        feature = position_features(first, last, name)
        if name == "naaim":
            feature["number_mean_anomaly_window"] = any(r["number_mean_anomaly"] for r in five)
        feature.update(past_price_features(close, current, lagged))
        feature["interaction"] = feature["trend"] * feature["change"]
        result.append({"candidate": name, "report_date": last["date"],
                       "lag_report_date": first["date"], "source": last["source"],
                       "actual_release_at": None,
                       "availability_status": "historical_release_vintage_not_qualified",
                       "assumed_alignment_after": friday.isoformat(),
                       "anchor_date": dates[current].isoformat(), "anchor_index": current,
                       "lag_anchor_date": dates[lagged].isoformat(), "lag_anchor_index": lagged,
                       "target_start_index": start, "target_end_index": end,
                       "target_start": dates[start].isoformat() if start < len(dates) else None,
                       "target_end": dates[end].isoformat() if end < len(dates) else None,
                       "mature": end < len(dates), **feature})
    return result, reasons, structural_pairs


def model_columns(candidate):
    base = PRICE_BASE + (["delta_oi_old_oi"] if candidate == "cftc" else [])
    return {"mean": [], "prices": base, "position": ["level", "change"],
            "level": base + ["level"], "change": base + ["level", "change"],
            "context": base + ["level", "change", "interaction"]}


def support(schedule, candidate):
    mature = [r for r in schedule if r["mature"]]
    annual = {}
    columns = model_columns(candidate)
    for year in range(2015, 2027):
        training = [r for r in mature if r["target_end"] < f"{year}-01-01"]
        evaluation = [r for r in mature if r["anchor_date"][:4] == str(year)]
        annual[str(year)] = {"train_n": len(training), "eval_n": len(evaluation),
                             "max_slope_parameters": max(len(c) for c in columns.values()),
                             "latest_train_target_end": max((r["target_end"] for r in training), default=None)}
    return annual


def prepare():
    output = bound_output()
    sources, paths = source_rows()
    dates, close, price_path = prices()
    schedule_dir = output / "implementation"
    schedule_dir.mkdir(exist_ok=True)
    summary = {"mode": "input_only", "future_outcome_values_calculated": False,
               "actual_release_at": None, "source_vintage": "current_saved_version",
               "price": {"path": str(price_path), "sha256": digest(price_path), "rows": len(dates)},
               "source_files": {name: {"path": str(path), "sha256": digest(path)}
                                for name, path in paths.items()}, "candidates": {}}
    for name in ("naaim", "cftc"):
        schedule, reasons, structural_pairs = build_schedule(name, sources[name], dates, close)
        destination = schedule_dir / f"{name}-schedule.json"
        write_json(destination, schedule)
        counts = {}
        for row in schedule:
            cell = f"trend_{row['trend']}_change_{int(np.sign(row['change']))}"
            counts[cell] = counts.get(cell, 0) + 1
        summary["candidates"][name] = {
            "source_rows": len(sources[name]), "structural_four_week_pairs": structural_pairs,
            "price_scheduled_pairs": len(schedule),
            "mature_target_endpoints": sum(r["mature"] for r in schedule),
            "rejected": reasons, "cell_counts_all_scheduled": counts,
            "zero_trend": sum(r["trend"] == 0 for r in schedule),
            "zero_change": sum(r["change"] == 0 for r in schedule),
            "number_mean_anomaly_windows": sum(r.get("number_mean_anomaly_window", False) for r in schedule),
            "annual_support": support(schedule, name), "schedule": str(destination),
            "schedule_sha256": digest(destination)}
    write_json(HERE / "input-qualification.json", summary)
    print(json.dumps({k: {"structural_pairs": v["structural_four_week_pairs"],
                          "price_scheduled_pairs": v["price_scheduled_pairs"],
                          "mature_endpoints": v["mature_target_endpoints"]}
                      for k, v in summary["candidates"].items()}))


def fit_predict(train, test, columns, penalty=0.001):
    """Training-standardized ridge; objective mean MSE + penalty*slopes^2."""
    if len(train) <= len(columns):
        raise ValueError("training rows must exceed slope parameter count")
    y = np.asarray([r["return63"] for r in train], dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("nonfinite target")
    if not columns:
        return np.full(len(test), y.mean()), {"columns": [], "intercept": float(y.mean())}
    a = np.asarray([[r[c] for c in columns] for r in train], dtype=float)
    b = np.asarray([[r[c] for c in columns] for r in test], dtype=float)
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("nonfinite feature")
    mean, scale = a.mean(axis=0), a.std(axis=0, ddof=0)
    scale = np.where(scale == 0, 1, scale)
    za = np.c_[np.ones(len(train)), (a - mean) / scale]
    zb = np.c_[np.ones(len(test)), (b - mean) / scale]
    ridge = np.diag([0] + [penalty * len(train)] * len(columns))
    beta = np.linalg.solve(za.T @ za + ridge, za.T @ y)
    return zb @ beta, {"columns": columns, "mean": mean.tolist(),
                       "scale": scale.tolist(), "beta": beta.tolist()}


def risk63(close):
    return float(100 * max(1 - close / np.maximum.accumulate(close)))


def outcomes(schedule, close, dates):
    result = []
    for row in schedule:
        if not row["mature"]:
            continue
        a, b = row["target_start_index"], row["target_end_index"]
        segment = close[a:b + 1]
        if len(segment) != 64 or dates[a].isoformat() != row["target_start"] or dates[b].isoformat() != row["target_end"]:
            raise ValueError("future endpoint drift")
        result.append(row | {"return63": float(100 * (segment[-1] / segment[0] - 1)),
                             "risk63": risk63(segment)})
    return result


def annual_predictions(rows, candidate):
    predictions, fits = [], []
    columns = model_columns(candidate)
    for year in range(2015, 2027):
        train = [r for r in rows if r["target_end"] < f"{year}-01-01"]
        test = [r.copy() for r in rows if r["anchor_date"][:4] == str(year)]
        if not test:
            continue
        if len(train) <= max(map(len, columns.values())):
            # Structural support is reported by prepare; never fabricate a fit.
            continue
        for model in MODEL_NAMES:
            values, details = fit_predict(train, test, columns[model])
            fits.append({"year": year, "model": model, "candidate": candidate,
                         "train_n": len(train),
                         "latest_train_target_end": max(r["target_end"] for r in train),
                         **details})
            for row, value in zip(test, values):
                row[f"pred_{model}"] = float(value)
        predictions.extend(test)
    return predictions, fits


def metrics(rows):
    if not rows:
        return None
    actual = np.asarray([r["return63"] for r in rows])
    models = {}
    for model in MODEL_NAMES:
        error = np.asarray([r[f"pred_{model}"] for r in rows]) - actual
        models[model] = {"mse_pp2": float(np.mean(error ** 2)),
                         "mae_pp": float(np.mean(np.abs(error)))}
    increments = {}
    for newer, older in COMPARISONS:
        base = models[older]["mse_pp2"]
        difference = base - models[newer]["mse_pp2"]
        increments[f"{newer}_vs_{older}"] = {
            "mse_reduction_pp2": difference,
            "mse_reduction_pct": 100 * difference / base if base > 0 else None}
    return {"n": len(rows), "models": models, "increments": increments}


def _episode_summary(rows):
    episodes = []
    previous = None
    for row in rows:
        cell = (int(row["trend"]), int(np.sign(row["change"])))
        date = dt.date.fromisoformat(row["report_date"])
        # A rejected report window also breaks continuity; use source dates,
        # not consecutive positions after filtering.
        if previous is None or cell != previous[0] or not 6 <= (date - previous[1]).days <= 8:
            episodes.append({"cell": f"trend_{cell[0]}_change_{cell[1]}",
                             "first": row["report_date"], "last": row["report_date"], "n": 1})
        else:
            episodes[-1]["last"] = row["report_date"]
            episodes[-1]["n"] += 1
        previous = (cell, date)
    return episodes


def cells(rows):
    result = {}
    for trend in (-1, 0, 1):
        for direction in (-1, 0, 1):
            name = f"trend_{trend}_change_{direction}"
            subset = [r for r in rows if r["trend"] == trend and int(np.sign(r["change"])) == direction]
            if not subset:
                result[name] = {"n": 0, "episodes": 0, "return_mean_pct": None,
                                "risk_mean_pct": None, "price_residual_mean_pp": None}
                continue
            pieces = _episode_summary(subset)
            result[name] = {"n": len(subset), "episodes": len(pieces),
                            "return_mean_pct": float(np.mean([r["return63"] for r in subset])),
                            "risk_mean_pct": float(np.mean([r["risk63"] for r in subset])),
                            "price_residual_mean_pp": float(np.mean([r["return63"] - r["pred_prices"] for r in subset]))}
    return result


def cell_contrasts(rows):
    """Within the same nonzero trend, observed positive minus negative change."""
    results = {}
    for trend in (-1, 1):
        positive = [r for r in rows if r["trend"] == trend and r["change"] > 0]
        negative = [r for r in rows if r["trend"] == trend and r["change"] < 0]
        key = f"trend_{trend}_positive_minus_negative"
        results[key] = {"positive_n": len(positive), "negative_n": len(negative)}
        for name, extractor in (
            ("return_mean_pct", lambda r: r["return63"]),
            ("risk_mean_pct", lambda r: r["risk63"]),
            ("price_residual_mean_pp", lambda r: r["return63"] - r["pred_prices"]),
        ):
            results[key][name] = (float(np.mean([extractor(r) for r in positive])
                                        - np.mean([extractor(r) for r in negative]))
                                  if positive and negative else None)
    return results


def block_intervals(rows, weeks, seed, reps=2000):
    """Paired calendar-week blocks; missing weeks remain empty positions."""
    if not rows:
        return None
    dates = [dt.date.fromisoformat(r["anchor_date"]) for r in rows]
    first = min(dates)
    origin = first - dt.timedelta(days=first.weekday())
    slot = np.asarray([(day - origin).days // 7 for day in dates], dtype=int)
    width = int(max(slot)) + 1
    rng = np.random.default_rng(seed)
    errors = {name: np.asarray([(r[f"pred_{name}"] - r["return63"]) ** 2 for r in rows])
              for name in MODEL_NAMES}
    block_count = math.ceil(width / weeks)
    draws = {f"{a}_vs_{b}": [] for a, b in COMPARISONS}
    cell_names = [f"trend_{t}_change_{c}" for t in (-1, 0, 1) for c in (-1, 0, 1)]
    cell_draws = {name: {measure: [] for measure in ("return_mean_pct", "risk_mean_pct", "price_residual_mean_pp")}
                  for name in cell_names}
    paired_cell_draws = {f"trend_{trend}_positive_minus_negative":
                         {measure: [] for measure in ("return_mean_pct", "risk_mean_pct", "price_residual_mean_pp")}
                         for trend in (-1, 1)}
    cell_masks = {f"trend_{t}_change_{c}": np.asarray([r["trend"] == t and int(np.sign(r["change"])) == c for r in rows])
                  for t in (-1, 0, 1) for c in (-1, 0, 1)}
    cell_values = {
        "return_mean_pct": np.asarray([r["return63"] for r in rows]),
        "risk_mean_pct": np.asarray([r["risk63"] for r in rows]),
        "price_residual_mean_pp": np.asarray([r["return63"] - r["pred_prices"] for r in rows]),
    }
    for _ in range(reps):
        # Circular time blocks preserve literal missing weeks without filling.
        starts = rng.integers(0, width, size=block_count)
        sampled = ((starts[:, None] + np.arange(weeks)) % width).ravel()[:width]
        weights = np.bincount(sampled, minlength=width)[slot]
        if not weights.sum():
            continue
        for a, b in COMPARISONS:
            draws[f"{a}_vs_{b}"].append(float(np.average(errors[b] - errors[a], weights=weights)))
        for name, mask in cell_masks.items():
            local_weights = weights * mask
            if local_weights.sum():
                for measure, values in cell_values.items():
                    cell_draws[name][measure].append(float(np.average(values, weights=local_weights)))
        for trend in (-1, 1):
            positive = weights * cell_masks[f"trend_{trend}_change_1"]
            negative = weights * cell_masks[f"trend_{trend}_change_-1"]
            if positive.sum() and negative.sum():
                label = f"trend_{trend}_positive_minus_negative"
                for measure, values in cell_values.items():
                    paired_cell_draws[label][measure].append(
                        float(np.average(values, weights=positive)
                              - np.average(values, weights=negative)))
    return {"calendar_weeks": weeks, "calendar_origin_monday": origin.isoformat(),
            "calendar_slots": width, "resamples_requested": reps,
            "descriptive_95pct_mse_reduction_pp2": {
                key: {"valid_draws": len(values),
                      "interval": list(map(float, np.quantile(values, [0.025, 0.975]))) if values else None}
                for key, values in draws.items()},
            "descriptive_95pct_cells": {
                name: {measure: {"valid_draws": len(values),
                                 "interval": list(map(float, np.quantile(values, [0.025, 0.975]))) if values else None}
                       for measure, values in measures.items()}
                for name, measures in cell_draws.items()},
            "descriptive_95pct_paired_positive_minus_negative": {
                name: {measure: {"valid_draws": len(values),
                                 "interval": list(map(float, np.quantile(values, [0.025, 0.975]))) if values else None}
                       for measure, values in measures.items()}
                for name, measures in paired_cell_draws.items()}}


def robustness(predictions):
    periods = {"2015-2019": (2015, 2019), "2020-2022": (2020, 2022),
               "2023-2026partial": (2023, 2026)}
    base = np.asarray([(r["pred_level"] - r["return63"]) ** 2
                       - (r["pred_context"] - r["return63"]) ** 2 for r in predictions])
    top = np.argsort(base)[-5:][::-1]
    removed = set(top.tolist())
    return {"periods": {label: metrics([r for r in predictions
                                        if first <= int(r["anchor_date"][:4]) <= last])
                        for label, (first, last) in periods.items()},
            "leave_year_out_saved_errors": {str(year): metrics([r for r in predictions
                                                                 if int(r["anchor_date"][:4]) != year])
                                             for year in range(2015, 2027)},
            "largest_five_context_vs_level_contribution_dates": [predictions[i]["report_date"] for i in top],
            "without_largest_five_saved_errors": metrics([r for i, r in enumerate(predictions) if i not in removed])}


def run(freeze_path):
    freeze = read_json(freeze_path)
    if freeze.get("run_authorized") is not True:
        raise RuntimeError("controller freeze has not authorized effects")
    qualification = read_json(HERE / "input-qualification.json")
    required = {HERE / "positioning_context.py", DESIGN,
                HERE / "input-qualification.json",
                Path(qualification["price"]["path"])}
    required.update(Path(item["path"]) for item in qualification["source_files"].values())
    required.update(Path(item["schedule"]) for item in qualification["candidates"].values())
    bound_paths = {Path(item["path"]) for item in freeze["files"]}
    if not required.issubset(bound_paths):
        raise ValueError("freeze lacks code, design, qualification, source, price or schedule hashes")
    for binding in freeze["files"]:
        if digest(binding["path"]) != binding["sha256"]:
            raise ValueError(f"frozen file changed: {binding['path']}")
    output = bound_output()
    target = output / "implementation/effects-v1"
    if target.exists():
        raise FileExistsError(target)
    schedules = {}
    for name in ("naaim", "cftc"):
        info = qualification["candidates"][name]
        if digest(info["schedule"]) != info["schedule_sha256"]:
            raise ValueError("schedule changed after preparation")
        schedules[name] = read_json(info["schedule"])
    dates, close, _ = prices()
    # No outcome is read until all freeze and schedule checks have passed.
    all_results, all_files, total_fits = {}, {}, 0
    target.mkdir(parents=True, exist_ok=False)
    for name, schedule in schedules.items():
        observations = outcomes(schedule, close, dates)
        predictions, fits = annual_predictions(observations, name)
        total_fits += len(fits)
        if total_fits > 144:
            raise RuntimeError("annual fit budget exceeded")
        if not predictions:
            raise RuntimeError(f"{name}: no eligible annual evaluation")
        data_files = {}
        for label, rows in (("observations", observations), ("predictions", predictions)):
            path = target / f"{name}-{label}.csv"
            csv_write(path, rows)
            data_files[label] = {"path": str(path), "sha256": digest(path)}
        fit_file = target / f"{name}-fits.json"
        write_json(fit_file, fits)
        data_files["fits"] = {"path": str(fit_file), "sha256": digest(fit_file)}
        all_files[name] = data_files
        all_results[name] = {"performance": metrics(predictions),
                             "cells": cells(predictions),
                             "same_trend_positive_minus_negative": cell_contrasts(predictions),
                             "episodes": _episode_summary(predictions),
                             "intervals": [block_intervals(predictions, length, 20261020 + length + (100 if name == "cftc" else 0))
                                           for length in (26, 13)],
                             "robustness": robustness(predictions),
                             "fit_n": len(fits),
                             "first_train_n": fits[0]["train_n"],
                             "max_slope_parameters": max(len(m) for m in model_columns(name).values())}
    result = {"candidate_results": all_results, "total_annual_fits": total_fits,
              "output_files": all_files, "source_release_status": "current-vintage retrospective association only",
              "not_full_lei_or_cash_account": True}
    result_path = target / "results.json"
    write_json(result_path, result)
    print(json.dumps({"results": str(result_path), "sha256": digest(result_path),
                      "total_annual_fits": total_fits}))


def synthetic():
    # No saved market source is loaded by this mode.
    assert anchor_after_report_week(dt.date(2026, 10, 14),
                                    [dt.date(2026, 10, 16), dt.date(2026, 10, 19)])[0] == 1
    base = [{"date": (dt.date(2026, 1, 1) + dt.timedelta(days=7 * i)).isoformat(),
             "level": float(i)} for i in range(5)]
    assert valid_five(base, "naaim")
    assert position_features(base[0], base[-1], "naaim")["change"] == 4
    broken = [dict(x) for x in base]
    broken[3]["date"] = "2026-01-29"
    assert not valid_five(broken, "naaim")
    old = {"oi": 1000, "long": 400, "short": 200, "spread": 10}
    new = {"oi": 500, "long": 390, "short": 170, "spread": 12}
    cf = position_features(old, new, "cftc")
    assert cf["change"] == 2 and cf["delta_long_old_oi"] == -1
    assert cf["minus_delta_short_old_oi"] == 3 and cf["delta_oi_old_oi"] == -50
    assert cf["level"] == 44  # denominator changed; do not call this buying
    prices_ = np.full(400, 100.0)
    features = past_price_features(prices_, 300, 280)
    assert features["r4w"] == 0 and features["trend"] == 0
    prices_[301:] = 500
    assert past_price_features(prices_, 300, 280) == features
    train = [{"x": float(i), "return63": -10 + 2 * i} for i in range(25)]
    pred, detail = fit_predict(train, [{"x": 26.0}], ["x"])
    assert detail["mean"] == [12.0] and abs(pred[0] - 42) < 0.1
    zero, _ = fit_predict(train, [{"x": 26.0}], [])
    assert zero[0] == 14
    negative, _ = fit_predict([{"x": float(i), "return63": -20.0} for i in range(25)],
                              [{"x": 26.0}], ["x"])
    assert negative[0] < 0  # Return predictions are never clipped to zero.
    assert math.isclose(risk63(np.asarray([100., 110., 99.])), 10, abs_tol=1e-12)
    assert model_columns("cftc")["context"] == PRICE_BASE + ["delta_oi_old_oi", "level", "change", "interaction"]
    assert all("delta_oi_old_oi" in model_columns("cftc")[name]
               for name in ("prices", "level", "change", "context"))
    # One row can never become a fit by including its own unfinished target.
    toy = [{"anchor_date": "2015-01-05", "target_end": "2015-04-06", "return63": 1}]
    assert not [r for r in toy if r["target_end"] < "2015-01-01"]
    # A calendar hole must remain a zero-count slot, not become an adjacent
    # observation in uncertainty resampling.
    block_rows = [
        {"anchor_date": "2020-01-01", "return63": 3.0, "risk63": 5.0,
         "trend": 1, "change": 3.0},
        {"anchor_date": "2020-01-08", "return63": 1.0, "risk63": 3.0,
         "trend": 1, "change": -3.0},
        {"anchor_date": "2020-01-29", "return63": -1.0, "risk63": 5.0,
         "trend": -1, "change": 3.0},
        {"anchor_date": "2020-02-05", "return63": -3.0, "risk63": 3.0,
         "trend": -1, "change": -3.0},
    ]
    for row in block_rows:
        row.update({f"pred_{m}": 0.0 for m in MODEL_NAMES})
    assert cell_contrasts(block_rows)["trend_1_positive_minus_negative"]["return_mean_pct"] == 2
    blocks = block_intervals(block_rows, 2, 7, reps=100)
    assert blocks["calendar_origin_monday"] == "2019-12-30"
    assert blocks["calendar_slots"] == 6  # Empty Jan 13 and Jan 20 weeks remain.
    assert blocks["calendar_weeks"] == 2 and blocks["resamples_requested"] == 100
    assert "trend_1_change_1" in blocks["descriptive_95pct_cells"]
    paired = blocks["descriptive_95pct_paired_positive_minus_negative"]
    for trend in (-1, 1):
        item = paired[f"trend_{trend}_positive_minus_negative"]
        assert item["return_mean_pct"]["valid_draws"] > 0
        assert np.allclose(item["return_mean_pct"]["interval"], [2, 2])
        assert np.allclose(item["risk_mean_pct"]["interval"], [2, 2])
    write_json(HERE / "synthetic-check.json", {
        "passed": True, "market_outcomes_used": False,
        "checks": ["Friday plus next quote", "five consecutive source dates",
                   "NAAIM four-week Mean change", "CFTC old-OI quantity decomposition",
                   "zero price trend retained", "future price mutation leaves features fixed",
                   "ridge training-only scaling", "mean baseline", "path risk arithmetic",
                   "CFTC denominator control in every price model",
                   "year-start target maturity", "unclipped negative prediction",
                   "Monday calendar origin and uncompressed gaps",
                   "same-trend positive-minus-negative paired blocks"]})
    print("synthetic checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "synthetic", "run"))
    parser.add_argument("--freeze", type=Path, help="controller-written run freeze manifest")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "synthetic":
        synthetic()
    else:
        if args.freeze is None:
            parser.error("run requires --freeze")
        run(args.freeze)
