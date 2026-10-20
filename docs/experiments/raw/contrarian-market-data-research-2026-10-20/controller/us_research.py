"""Bounded current-vintage historical comparison; not a live trading backtest."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
PRICE_COLS = ["r63", "r252", "vol63", "drawdown252"]
MODELS = {"mean": [], "prices": PRICE_COLS, "factor": ["x"], "combined": PRICE_COLS + ["x"]}


def read_json(p):
    return json.loads(Path(p).read_text())


def write_json(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def csv_rows(p):
    with Path(p).open() as f:
        return list(csv.DictReader(f))


def csv_write(p, rows):
    with Path(p).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def bound_output():
    plan = read_json(RAW / "storage-plan.json")
    out = Path(plan["output"])
    # Do not fall back to the internal disk if the registered volume disappears.
    if not out.is_dir() or out.stat().st_dev != plan["external_device"]:
        raise RuntimeError("bound external output unavailable or changed")
    return out


def prices():
    meta = read_json(HERE / "price-input-reuse.json")
    p = Path(meta["source"]["path"])
    assert sha(p) == meta["source"]["sha256"]
    data = read_json(p)["chart"]["result"][0]
    values = data["indicators"]["adjclose"][0]["adjclose"]
    dates, closes = [], []
    for epoch, value in zip(data["timestamp"], values):
        if value is None or not np.isfinite(value) or value <= 0:
            raise ValueError("do not compress missing price rows")
        dates.append(dt.datetime.fromtimestamp(epoch, ZoneInfo("America/New_York")).date())
        closes.append(float(value))
    assert dates == sorted(set(dates))
    return dates, np.array(closes)


def analysis_anchor(report_date):
    # Same deterministic research alignment for both sources. NOT available_at.
    # First actual quote strictly after Friday in the report's calendar week.
    monday = report_date - dt.timedelta(days=report_date.weekday())
    return monday + dt.timedelta(days=4)


def risk(values):
    return float(100 * np.max(1 - values / np.maximum.accumulate(values)))


def source_rows(out, name):
    exclusions = []
    if name == "naaim":
        p = out / "naaim/naaim-official-2026-08-19-parsed.csv"
        grouped = {}
        for row in csv_rows(p):
            grouped.setdefault(row["date"], []).append(float(row["mean"]))
        rows = []
        for date, values in sorted(grouped.items()):
            assert max(values) - min(values) <= 0.005, (date, values)
            if date in ("2014-03-18", "2014-03-19"):
                exclusions.append({"date": date, "reason": "unresolved adjacent survey dates"})
                continue
            rows.append({"date": date, "x": values[-1], "source": "official"})
        official_dates = set(grouped)
        for row in csv_rows(out / "naaim/winterresearch-naaim-parsed.csv"):
            if row["date"] in official_dates:
                assert abs(float(row["exposure"]) - grouped[row["date"]][-1]) <= 0.005
            elif row["date"] > max(official_dates):
                rows.append({"date": row["date"], "x": float(row["exposure"]), "source": "public_extension"})
        rows.sort(key=lambda x: x["date"])
    else:
        p = out / "us-cftc/cftc-tff-futures-only-13874A-snapshot-2026-10-20.csv"
        rows = []
        for row in csv_rows(p):
            date = row["report_date_as_yyyy_mm_dd"][:10]
            if date < "2011-01-01":
                exclusions.append({"date": date, "reason": "pre-2011 publication and backcast boundary"})
                continue
            oi = int(row["open_interest_all"])
            assert oi > 0 and row["cftc_contract_market_code"] == "13874A"
            x = 100 * (int(row["asset_mgr_positions_long"]) - int(row["asset_mgr_positions_short"])) / oi
            rows.append({"date": date, "x": x, "source": "official_current_vintage"})
    return rows, exclusions


def known_cftc_exception(date):
    # Conservative calendar masks, not claims that every day in them was delayed.
    windows = [
        ("2013-10-01", "2013-12-31"),
        ("2018-12-24", "2019-03-31"),
        ("2023-01-01", "2023-03-31"),
        ("2025-09-30", "2025-12-31"),
    ]
    return date == "2017-03-28" or any(a <= date <= b for a, b in windows)


def prepare():
    out = bound_output()
    dates, close = prices()
    date_str = np.array([x.isoformat() for x in dates])
    summaries = {}
    source_bindings = []
    for part in ("naaim", "us-cftc"):
        for p in sorted((out / part).glob("*")):
            if p.suffix in (".csv", ".xlsx", ".json") and not p.name.startswith("._"):
                source_bindings.append({"path": str(p), "sha256": sha(p)})
    for name in ("naaim", "cftc"):
        raw, exclusions = source_rows(out, name)
        scheduled, history = [], []
        prev_date, prev_state = None, None
        for item in raw:
            date = dt.date.fromisoformat(item["date"])
            x = item["x"]
            if name == "naaim":
                state = "low" if x <= 40 else "high" if x >= 100 else "middle"
                cut_low, cut_high = 40.0, 100.0
            elif len(history) >= 260:
                cut_low, cut_high = map(float, np.quantile(history[-260:], [0.1, 0.9]))
                state = "low" if x <= cut_low else "high" if x >= cut_high else "middle"
            else:
                cut_low, cut_high, state = None, None, "warmup"
            valid_previous = prev_date is not None and 6 <= (date - prev_date).days <= 8
            entered = state in ("low", "high") and valid_previous and prev_state not in (state, "warmup", None)
            unknown_start = state in ("low", "high") and not valid_previous
            history.append(x)
            prev_date, prev_state = date, state
            if name == "cftc" and known_cftc_exception(item["date"]):
                exclusions.append({"date": item["date"], "reason": "known release/correction risk calendar mask"})
                prev_date, prev_state = None, None
                continue
            friday = analysis_anchor(date)
            anchor = int(np.searchsorted(date_str, friday.isoformat(), side="right"))
            start, end = anchor + 1, anchor + 64
            if anchor >= len(close):
                exclusions.append({"date": item["date"], "reason": "anchor beyond saved quotes"})
                continue
            if anchor < 252:
                exclusions.append({"date": item["date"], "reason": "price background warmup"})
                continue
            # Only past/current values are calculated here; future values are not inspected.
            daily = close[anchor - 63 + 1:anchor + 1] / close[anchor - 63:anchor] - 1
            mature = end < len(close)
            scheduled.append({
                "candidate": name, "report_date": item["date"], "x": x, "source": item["source"],
                "actual_release_at": "", "availability_status": "historical_release_vintage_not_qualified",
                "assumed_alignment_after": friday.isoformat(), "anchor_date": dates[anchor].isoformat(),
                "anchor_index": anchor, "target_start": dates[start].isoformat() if start < len(dates) else "",
                "target_end": dates[end].isoformat() if mature else "", "target_start_index": start,
                "target_end_index": end, "mature": mature,
                "r63": 100 * (close[anchor] / close[anchor - 63] - 1),
                "r252": 100 * (close[anchor] / close[anchor - 252] - 1),
                "vol63": float(np.std(daily, ddof=0) * np.sqrt(252) * 100),
                "drawdown252": 100 * (close[anchor] / max(close[anchor - 251:anchor + 1]) - 1),
                "state": state, "cut_low": cut_low, "cut_high": cut_high,
                "confirmed_entry": entered, "unknown_episode_start": unknown_start,
            })
        p = out / "controller" / f"{name}-schedule.json"
        write_json(p, scheduled)
        support = {}
        for year in range(2015, 2027):
            boundary = f"{year}-01-01"
            train = [x for x in scheduled if x["mature"] and x["target_end"] < boundary]
            test = [x for x in scheduled if x["mature"] and x["anchor_date"][:4] == str(year)]
            support[str(year)] = {"training_rows": len(train), "evaluation_rows": len(test),
                                  "training_end": train[-1]["target_end"] if train else None}
        summaries[name] = {
            "raw_unique_rows_after_identity_cleaning": len(raw),
            "scheduled": len(scheduled), "mature": sum(x["mature"] for x in scheduled),
            "schedule_range": [scheduled[0]["report_date"], scheduled[-1]["report_date"]],
            "source_range": [raw[0]["date"], raw[-1]["date"]],
            "excluded": exclusions, "annual_support": support,
            "full_mature_state_counts": {s: sum(x["mature"] and x["state"] == s for x in scheduled) for s in ["low", "middle", "high", "warmup"]},
            "confirmed_mature_entries": {s: sum(x["mature"] and x["state"] == s and x["confirmed_entry"] for x in scheduled) for s in ["low", "high"]},
            "schedule_file": str(p), "schedule_sha256": sha(p),
        }
    write_json(HERE / "us-qualification.json", {
        "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "future_outcome_values_calculated": False, "sources": source_bindings, "candidates": summaries,
        "native_runner": "sentiment/positioning not supported; explicit independent research prototype",
        "analysis_eligibility": "limited current-vintage retrospective association only",
    })
    print(json.dumps({k: {f: v[f] for f in ["scheduled", "mature", "full_mature_state_counts", "confirmed_mature_entries"]} for k, v in summaries.items()}))


def fit_predict(train, test, columns, lam=0.001):
    y = np.array([r["risk63"] for r in train])
    if not columns:
        return np.repeat(y.mean(), len(test)), {"columns": [], "intercept": float(y.mean())}
    a = np.array([[r[c] for c in columns] for r in train])
    b = np.array([[r[c] for c in columns] for r in test])
    mu, scale = a.mean(0), a.std(0)
    scale = np.where(scale == 0, 1, scale)
    z = np.c_[np.ones(len(a)), (a - mu) / scale]
    zz = np.c_[np.ones(len(b)), (b - mu) / scale]
    penalty = np.diag([0] + [lam * len(a)] * len(columns))
    beta = np.linalg.solve(z.T @ z + penalty, z.T @ y)
    pred = zz @ beta
    return np.maximum(0, pred), {"columns": columns, "mu": mu.tolist(), "scale": scale.tolist(),
                                "beta": beta.tolist(), "negative_before_projection": int(sum(pred < 0))}


def metrics(rows):
    if not rows:
        return None
    ans = {"n": len(rows)}
    for name in MODELS:
        e = np.array([r[f"pred_{name}"] - r["risk63"] for r in rows])
        ans[name] = {"mse": float(np.mean(e ** 2)), "mae_pp": float(np.mean(abs(e)))}
    ans["improvement_pct_vs_prices"] = 100 * (1 - ans["combined"]["mse"] / ans["prices"]["mse"])
    ans["improvement_pct_vs_mean"] = 100 * (1 - ans["combined"]["mse"] / ans["mean"]["mse"])
    return ans


def block_intervals(rows, block, seed):
    dates = [dt.date.fromisoformat(r["anchor_date"]) for r in rows]
    first = min(dates)
    weeks = np.array([(d - first).days // 7 for d in dates])
    width = int(max(weeks)) + 1
    losses_b = np.array([(r["pred_prices"] - r["risk63"]) ** 2 for r in rows])
    losses_x = np.array([(r["pred_combined"] - r["risk63"]) ** 2 for r in rows])
    rng = np.random.default_rng(seed)
    values, high_differences, high_residual_differences = [], [], []
    high = np.array([r["state"] == "high" for r in rows])
    middle = np.array([r["state"] == "middle" for r in rows])
    actual = np.array([r["risk63"] for r in rows])
    residual = np.array([r["risk63"] - r["pred_prices"] for r in rows])
    for _ in range(2000):
        starts = rng.integers(0, width - block + 1, size=int(np.ceil(width / block)))
        sampled_calendar = (starts[:, None] + np.arange(block)).ravel()[:width]
        weights = np.bincount(sampled_calendar, minlength=width)[weeks]
        denominator = np.sum(weights * losses_b)
        if denominator > 0:
            values.append(100 * (1 - np.sum(weights * losses_x) / denominator))
        wh, wm = weights * high, weights * middle
        if wh.sum() > 0 and wm.sum() > 0:
            high_differences.append(float(np.sum(wh * actual) / wh.sum() - np.sum(wm * actual) / wm.sum()))
            high_residual_differences.append(float(np.sum(wh * residual) / wh.sum() - np.sum(wm * residual) / wm.sum()))
    return {"block_calendar_weeks": block, "draws": len(values),
            "interval_95_pct": list(map(float, np.quantile(values, [0.025, 0.975]))),
            "high_minus_middle_risk_pp_interval": list(map(float, np.quantile(high_differences, [0.025, 0.975]))),
            "high_minus_middle_price_residual_pp_interval": list(map(float, np.quantile(high_residual_differences, [0.025, 0.975]))),
            "tail_difference_valid_draws": len(high_differences)}


def run():
    out = bound_output()
    freeze = read_json(HERE / "us-freeze.json")
    for item in freeze["files"]:
        assert sha(item["path"]) == item["sha256"], item["path"]
    target_dir = out / "controller/us-analysis-v1"
    target_dir.mkdir(exist_ok=False)
    dates, close = prices()
    summaries, total_fits = {}, 0
    for name in ("naaim", "cftc"):
        schedule = read_json(out / "controller" / f"{name}-schedule.json")
        observations = []
        for item in schedule:
            if not item["mature"]:
                continue
            a, b = item["target_start_index"], item["target_end_index"]
            segment = close[a:b + 1]
            assert len(segment) == 64
            observations.append(item | {"risk63": risk(segment),
                                        "return63": float(100 * (segment[-1] / segment[0] - 1)),
                                        "loss_from_start63": float(100 * max(0, 1 - min(segment) / segment[0]))})
        predictions, fits = [], []
        for year in range(2015, 2027):
            train = [r for r in observations if r["target_end"] < f"{year}-01-01"]
            test = [r.copy() for r in observations if r["anchor_date"][:4] == str(year)]
            if not test:
                continue
            assert len(train) >= 150
            for model, columns in MODELS.items():
                values, fit = fit_predict(train, test, columns)
                total_fits += 1
                fits.append({"year": year, "model": model, "n_train": len(train),
                             "latest_train_target_end": max(r["target_end"] for r in train), **fit})
                for row, value in zip(test, values):
                    row["pred_" + model] = float(value)
            predictions.extend(test)
        groups = {}
        for scope, collection in (("full_mature_history", observations), ("same_evaluation_dates", predictions)):
            groups[scope] = {}
            for state in ("low", "middle", "high", "warmup"):
                subset = [r for r in collection if r["state"] == state]
                if subset:
                    groups[scope][state] = {"n": len(subset),
                        "confirmed_entries": sum(r["confirmed_entry"] for r in subset),
                        "risk63_mean_pct": float(np.mean([r["risk63"] for r in subset])),
                        "return63_mean_pct": float(np.mean([r["return63"] for r in subset])),
                        "return63_median_pct": float(np.median([r["return63"] for r in subset])),
                        "positive_return_fraction": float(np.mean([r["return63"] > 0 for r in subset])),
                        "loss_from_start63_mean_pct": float(np.mean([r["loss_from_start63"] for r in subset]))}
                    if scope == "same_evaluation_dates":
                        groups[scope][state]["risk_residual_vs_prices_mean_pp"] = float(np.mean([r["risk63"] - r["pred_prices"] for r in subset]))
        periods = {}
        for label, first, last in [("2015-2019", "2015", "2019"), ("2020-2022", "2020", "2022"), ("2023-2026partial", "2023", "2026")]:
            periods[label] = metrics([r for r in predictions if first <= r["anchor_date"][:4] <= last])
        improvements = np.array([(r["pred_prices"] - r["risk63"]) ** 2 - (r["pred_combined"] - r["risk63"]) ** 2 for r in predictions])
        largest = np.argsort(improvements)[-5:][::-1]
        removed = set(largest.tolist())
        summaries[name] = {
            "evaluation_range": [predictions[0]["anchor_date"], predictions[-1]["anchor_date"]],
            "evaluation_target_end": predictions[-1]["target_end"],
            "full_mature_range": [observations[0]["anchor_date"], observations[-1]["anchor_date"]],
            "performance": metrics(predictions), "groups": groups, "periods": periods,
            "intervals": [block_intervals(predictions, b, 20261020 + b + (0 if name == "naaim" else 100)) for b in (26, 13)],
            "leave_year_out": {str(year): metrics([r for r in predictions if r["anchor_date"][:4] != str(year)]) for year in range(2015, 2027)},
            "largest_five_improvement_dates": [predictions[i]["report_date"] for i in largest],
            "largest_five_contribution_share": float(improvements[largest].sum() / improvements.sum()) if improvements.sum() != 0 else None,
            "without_largest_five": metrics([r for i, r in enumerate(predictions) if i not in removed]),
            "factor_slope_in_combined_by_year": {str(f["year"]): f["beta"][-1] for f in fits if f["model"] == "combined"},
            "fits": len(fits), "source_release_status": "current-vintage historical association, NOT validated live predictor",
        }
        csv_write(target_dir / f"{name}-observations.csv", observations)
        csv_write(target_dir / f"{name}-predictions.csv", predictions)
        csv_write(target_dir / f"{name}-confirmed-extreme-entries.csv", [r for r in observations if r["confirmed_entry"]])
        write_json(target_dir / f"{name}-fits.json", fits)
    write_json(target_dir / "results.json", {"total_annual_model_fits": total_fits, "candidates": summaries})
    write_json(HERE / "us-results-summary.json", {"result_file": str(target_dir / "results.json"),
                                               "result_sha256": sha(target_dir / "results.json"),
                                               "total_annual_model_fits": total_fits,
                                               "candidates": summaries})
    print(json.dumps({k: v["performance"] for k, v in summaries.items()}))


def synthetic():
    assert abs(risk(np.array([100.0, 110.0, 99.0])) - 10) < 1e-12
    assert risk(np.array([100.0, 101.0, 102.0])) == 0
    assert analysis_anchor(dt.date(2026, 10, 14)) == dt.date(2026, 10, 16)
    a = [{"x": float(i), "risk63": 2 + 3 * float(i)} for i in range(20)]
    b = [{"x": 21.0}, {"x": 22.0}]
    p, f = fit_predict(a, b, ["x"])
    assert np.max(abs(p - [65.0, 68.0])) < 0.05
    assert f["mu"] == [9.5]  # Test-period values must not influence standardization.
    z, _ = fit_predict(a, b, [])
    assert list(z) == [30.5, 30.5]
    assert known_cftc_exception("2019-03-26")
    assert not known_cftc_exception("2019-04-02")
    write_json(HERE / "synthetic-check.json", {"passed": True, "checks": [
        "future peak-to-trough distinct from initial-price loss",
        "nondecreasing path zero risk", "fixed calendar alignment",
        "ridge known linear fixture", "train-only scale", "mean baseline",
        "known CFTC exception masks"], "market_outcomes_used": False})
    print("synthetic checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "synthetic", "run"])
    mode = parser.parse_args().mode
    {"prepare": prepare, "synthetic": synthetic, "run": run}[mode]()
