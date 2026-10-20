"""Bounded, read-only arithmetic review of the saved US result artifacts."""

import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "controller"
SUMMARY = json.loads((ROOT / "us-results-summary.json").read_text())
METHOD = json.loads((ROOT / "us-method-final.json").read_text())
FREEZE = json.loads((ROOT / "us-freeze.json").read_text())
BASE = Path(SUMMARY["result_file"]).parent
OUT = Path(SUMMARY["result_file"]).parents[2]
PRICE_META = json.loads((ROOT / "price-input-reuse.json").read_text())["source"]


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qr_augmented(train, columns, penalty=0.001):
    """Modified Gram-Schmidt on augmented least-squares rows, not normal equations."""
    n = len(train)
    mu = [mean(float(r[c]) for r in train) for c in columns]
    sd = []
    for c, m in zip(columns, mu):
        v = math.sqrt(mean((float(r[c]) - m) ** 2 for r in train))
        sd.append(v or 1.0)
    p = len(columns) + 1
    x = [[1.0] + [(float(r[c]) - m) / s for c, m, s in zip(columns, mu, sd)] for r in train]
    x += [[0.0] + [math.sqrt(penalty * n) if j == k else 0.0 for j in range(1, p)] for k in range(1, p)]
    y = [float(r["risk63"]) for r in train] + [0.0] * (p - 1)
    cols = [[row[j] for row in x] for j in range(p)]
    q, upper = [], [[0.0] * p for _ in range(p)]
    for j in range(p):
        v = cols[j][:]
        for _ in range(2):
            for k in range(j):
                proj = sum(a * b for a, b in zip(q[k], v))
                upper[k][j] += proj
                v = [a - proj * b for a, b in zip(v, q[k])]
        norm = math.sqrt(sum(a * a for a in v))
        if norm == 0:
            raise ValueError("rank deficient augmented design")
        upper[j][j] = norm
        q.append([a / norm for a in v])
    rhs = [sum(a * b for a, b in zip(v, y)) for v in q]
    beta = [0.0] * p
    for j in reversed(range(p)):
        beta[j] = (rhs[j] - sum(upper[j][k] * beta[k] for k in range(j + 1, p))) / upper[j][j]
    return beta, mu, sd


def main():
    assert sha(SUMMARY["result_file"]) == SUMMARY["result_sha256"]
    frozen = {Path(x["path"]).name: sha(x["path"]) == x["sha256"] for x in FREEZE["files"]}
    assert all(frozen.values())
    assert sha(PRICE_META["path"]) == PRICE_META["sha256"]
    raw_price = json.loads(Path(PRICE_META["path"]).read_text())["chart"]["result"][0]
    dates = [dt.datetime.fromtimestamp(t, ZoneInfo("America/New_York")).date() for t in raw_price["timestamp"]]
    closes = raw_price["indicators"]["adjclose"][0]["adjclose"]
    assert len(dates) == len(closes) == 6114
    report = {
        "scope": "Independent arithmetic/read-back of saved US candidates, no new outcome fit grid or source request",
        "status": "pass",
        "freeze_sha_match": frozen,
        "result_sha_match": True,
        "price_sha_match": True,
        "model_solve_count": 2,
        "new_market_fits": 0,
        "candidate_reviews": {},
        "failures": [],
    }
    candidate_sources = {
        "naaim": {r["date"]: r for r in read_csv(OUT / "naaim/naaim-combined-input-only.csv")},
        "cftc": {r["report_date_as_yyyy_mm_dd"][:10]: r for r in read_csv(OUT / "us-cftc/cftc-tff-futures-only-13874A-snapshot-2026-10-20.csv")},
    }
    max_metric_delta = 0.0
    for candidate in ("naaim", "cftc"):
        obs = read_csv(BASE / f"{candidate}-observations.csv")
        pred = read_csv(BASE / f"{candidate}-predictions.csv")
        fits = json.loads((BASE / f"{candidate}-fits.json").read_text())
        summary = json.loads(Path(SUMMARY["result_file"]).read_text())["candidates"][candidate]
        annual = METHOD["input_support"][candidate]["annual"]
        review = {"observations": len(obs), "predictions": len(pred), "fits_saved": len(fits), "metrics": {}, "annual": {}, "sample_labels": [], "source_formula_checks": {}}
        assert len(fits) == 48 and len(pred) == summary["performance"]["n"]
        for model in ("mean", "prices", "factor", "combined"):
            errors = [float(r[f"pred_{model}"]) - float(r["risk63"]) for r in pred]
            mse = math.fsum(v * v for v in errors) / len(errors)
            mae = math.fsum(abs(v) for v in errors) / len(errors)
            dm = max(abs(mse - summary["performance"][model]["mse"]), abs(mae - summary["performance"][model]["mae_pp"]))
            max_metric_delta = max(max_metric_delta, dm)
            review["metrics"][model] = {"mse": mse, "mae_pp": mae, "max_abs_delta": dm}
        price_mse = review["metrics"]["prices"]["mse"]
        both_mse = review["metrics"]["combined"]["mse"]
        avg_mse = review["metrics"]["mean"]["mse"]
        review["increment_pct_vs_prices"] = 100 * (1 - both_mse / price_mse)
        review["increment_pct_vs_mean"] = 100 * (1 - both_mse / avg_mse)
        assert abs(review["increment_pct_vs_prices"] - summary["performance"]["improvement_pct_vs_prices"]) < 1e-9
        assert abs(review["increment_pct_vs_mean"] - summary["performance"]["improvement_pct_vs_mean"]) < 1e-9
        years = {year: [r for r in pred if r["anchor_date"].startswith(year)] for year in annual}
        for year, rows in years.items():
            train = [r for r in obs if r["target_end"] < f"{year}-01-01"]
            assert len(rows) == annual[year]["evaluation_rows"]
            assert len(train) == annual[year]["training_rows"]
            latest = max((r["target_end"] for r in train), default=None)
            assert latest == annual[year]["training_end"]
            assert all(r["target_end"] < f"{year}-01-01" for r in train)
            assert all(r["target_end"] <= dates[-1].isoformat() for r in train + rows)
            review["annual"][year] = {"n_train": len(train), "n_evaluation": len(rows), "latest_mature_train_label": latest}
        # Four distinct label windows, including 2020 and the most recent mature year.
        for target in ("2015-01-", "2020-02-", "2020-03-", "2026-07-"):
            row = next((r for r in obs if r["report_date"].startswith(target)), None)
            if row is None:
                row = next((r for r in obs if r["report_date"][:4] == target[:4]), None)
            assert row is not None
            a, b = int(row["target_start_index"]), int(row["target_end_index"])
            anchor = int(row["anchor_index"])
            assert a == anchor + 1 and b == a + 63 and b < len(closes)
            assert dates[a].isoformat() == row["target_start"] and dates[b].isoformat() == row["target_end"]
            path = closes[a:b + 1]
            # Direct all-pairs peak-to-later-trough calculation, independent of cumulative-max implementation.
            risk = 100 * max(1 - path[j] / path[i] for i in range(64) for j in range(i, 64))
            initial_loss = 100 * max(0, 1 - min(path) / path[0])
            ret = 100 * (path[-1] / path[0] - 1)
            r63 = 100 * (closes[anchor] / closes[anchor - 63] - 1)
            r252 = 100 * (closes[anchor] / closes[anchor - 252] - 1)
            daily = [closes[i] / closes[i - 1] - 1 for i in range(anchor - 62, anchor + 1)]
            mu_daily = mean(daily)
            vol = math.sqrt(mean((x - mu_daily) ** 2 for x in daily)) * math.sqrt(252) * 100
            dd252 = 100 * (closes[anchor] / max(closes[anchor - 251:anchor + 1]) - 1)
            deltas = {k: abs(v - float(row[k])) for k, v in (("risk63", risk), ("loss_from_start63", initial_loss), ("return63", ret), ("r63", r63), ("r252", r252), ("vol63", vol), ("drawdown252", dd252))}
            assert max(deltas.values()) < 1e-9
            assert risk + 1e-9 >= initial_loss
            review["sample_labels"].append({"report_date": row["report_date"], "target_start": row["target_start"], "target_end": row["target_end"], "n_closes": len(path), "risk63": risk, "loss_from_start63": initial_loss, "return63": ret, "max_abs_difference": max(deltas.values())})
        source_errors, state_errors = [], []
        for row in obs:
            src = candidate_sources[candidate][row["report_date"]]
            if candidate == "naaim":
                value = float(src["mean"])
                state = "low" if value <= 40 else "high" if value >= 100 else "middle"
                if abs(value - float(row["x"])) > 1e-9: source_errors.append(row["report_date"])
                if state != row["state"]: state_errors.append(row["report_date"])
            else:
                value = 100 * (int(src["asset_mgr_positions_long"]) - int(src["asset_mgr_positions_short"])) / int(src["open_interest_all"])
                if abs(value - float(row["x"])) > 1e-9: source_errors.append(row["report_date"])
            assert row["actual_release_at"] == ""
            assert row["availability_status"] == "historical_release_vintage_not_qualified"
        assert not source_errors and not state_errors
        review["source_formula_checks"] = {"rows_checked": len(obs), "source_mismatches": source_errors, "threshold_mismatches": state_errors, "actual_release_populated": 0}
        if candidate == "naaim":
            official = {r["date"]: r for r in read_csv(OUT / "naaim/naaim-official-2026-08-19-parsed.csv")}
            missing, value_mismatch, threshold_mismatch = [], [], []
            for row in obs:
                src = official.get(row["report_date"])
                if src is None:
                    missing.append(row["report_date"])
                    continue
                value = float(src["mean"])
                if abs(value - float(row["x"])) > 0.00501:
                    value_mismatch.append(row["report_date"])
                state = "low" if value <= 40 else "high" if value >= 100 else "middle"
                if state != row["state"]:
                    threshold_mismatch.append(row["report_date"])
            assert not (missing or value_mismatch or threshold_mismatch)
            review["official_parsed_crosscheck"] = {"rows_checked": len(obs), "source": "naaim-official-2026-08-19-parsed.csv", "allowed_rounding_pp": 0.00501, "missing_dates": missing, "value_mismatches": value_mismatch, "threshold_mismatches": threshold_mismatch}
        report["candidate_reviews"][candidate] = review
    report["max_headline_metric_abs_difference"] = max_metric_delta
    # Exactly two alternative numerical solves on already-fixed annual training sets.
    for candidate, year in (("naaim", 2025), ("cftc", 2020)):
        rows = read_csv(BASE / f"{candidate}-observations.csv")
        train = [r for r in rows if r["target_end"] < f"{year}-01-01"]
        fit = next(f for f in json.loads((BASE / f"{candidate}-fits.json").read_text()) if f["year"] == year and f["model"] == "combined")
        beta, mu, sd = qr_augmented(train, fit["columns"])
        d = max(abs(a - b) for a, b in zip(beta, fit["beta"]))
        report["candidate_reviews"][candidate]["independent_augmented_qr_solve"] = {"year": year, "model": "combined", "n_train": len(train), "max_beta_abs_difference": d, "max_mu_abs_difference": max(abs(a - b) for a, b in zip(mu, fit["mu"])), "max_sd_abs_difference": max(abs(a - b) for a, b in zip(sd, fit["scale"]))}
        assert d < 1e-7
    path = HERE / "independent-results-review.json"
    assert not path.exists()
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "file": str(path), "max_metric_delta": max_metric_delta, "solves": 2, "samples_each": 4}, ensure_ascii=False))


if __name__ == "__main__":
    main()
