"""Independent, saved-result-only audit of prior-month index-state labels."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

W = Path(__file__).resolve().parent
CONTRACT = json.loads((W / "contract.json").read_text())
SOURCES = CONTRACT["sources"]
PERIODS = CONTRACT["periods"]
MONTHS = pd.period_range(*CONTRACT["months"], freq="M").astype(str).tolist()
TOL = 2e-12


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound(ref: dict) -> Path:
    p = Path(ref["path"])
    if not p.is_file() or sha(p) != ref["sha256"]:
        raise RuntimeError(f"source missing or SHA mismatch: {p}")
    return p


def mean(xs):
    return float(np.mean(xs)) if len(xs) else None


def calc_state(holding_month: str, prices: dict, monthends: dict):
    prev = str(pd.Period(holding_month, "M") - 1)
    window = [str(pd.Period(prev, "M") - i) for i in reversed(range(10))]
    if any(m not in monthends or monthends[m] not in prices for m in window):
        return {"state": "unknown", "formationMonth": prev, "calculationCutoff": None,
                "indexClose": None, "sma10": None}
    if any(prices[monthends[m]][0] != monthends[m] for m in window):
        return {"state": "unknown", "formationMonth": prev, "calculationCutoff": None,
                "indexClose": None, "sma10": None}
    vals = [float(prices[monthends[m]][1]) for m in window]
    if not all(math.isfinite(v) and v > 0 for v in vals):
        return {"state": "unknown", "formationMonth": prev, "calculationCutoff": None,
                "indexClose": None, "sma10": None}
    close, sma = vals[-1], float(np.mean(vals))
    return {"state": "strong" if close > sma else "weak", "formationMonth": prev,
            "calculationCutoff": monthends[prev], "indexClose": close, "sma10": sma}


def compare(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= TOL
    return a == b


def state_of(month, state_map):
    return state_map[month]


def point_map(stream):
    return {p[0][:7]: p for p in stream["points"]}


def legacy_cell(stream, period, label):
    return stream["period"][period]["monthly"],


def cell_metrics(stream, pool, period, selected_months, labels):
    monthly = stream["period"][period]["monthly"]
    base = pool["period"][period]["monthly"]
    pts, bpts = point_map(stream), point_map(pool)
    r = [float(monthly[m]) for m in selected_months]
    b = [float(base[m]) for m in selected_months]
    d = [x-y for x, y in zip(r, b)]
    ups = [i for i, x in enumerate(b) if x > 0]
    downs = [i for i, x in enumerate(b) if x < 0]
    return {
        "months": len(r),
        "factorMeanReturn": mean(r), "poolMeanReturn": mean(b), "pairedDifferenceMean": mean(d),
        "factorLossMonthFraction": mean([x < 0 for x in r]),
        "poolLossMonthFraction": mean([x < 0 for x in b]),
        "factorUnderperformMonthFraction": mean([x < 0 for x in d]),
        "benchmarkUpMonths": len(ups), "benchmarkDownMonths": len(downs),
        "meanDifferenceWhenPoolUp": mean([d[i] for i in ups]),
        "meanDifferenceWhenPoolDown": mean([d[i] for i in downs]),
        "factorMonthEndCashMean": mean([float(pts[m][3]) for m in selected_months]),
        "poolMonthEndCashMean": mean([float(bpts[m][3]) for m in selected_months]),
        "factorMonthEndUnknownMean": mean([float(pts[m][2]) for m in selected_months]),
        "poolMonthEndUnknownMean": mean([float(bpts[m][2]) for m in selected_months]),
        "factorMeanOfMonthlyPeakUnknownFraction": mean([float(pts[m][5]) for m in selected_months]),
        "poolMeanOfMonthlyPeakUnknownFraction": mean([float(bpts[m][5]) for m in selected_months]),
    }


def hac(y, states):
    x = np.asarray([[1.0 if states[m] == s else 0.0 for s in ("strong", "weak")]
                    for m in MONTHS], dtype=float)
    y = np.asarray(y, dtype=float)
    xtx_inv = np.linalg.inv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    g = x * resid[:, None]
    meat = g.T @ g
    lag_sums = []
    for lag in range(1, 4):
        cross = g[lag:].T @ g[:-lag]
        weight = 1.0 - lag / 4.0
        meat += weight * (cross + cross.T)
        lag_sums.append({"lag": lag, "bartlettWeight": weight})
    cov = xtx_inv @ meat @ xtx_inv
    c = np.asarray([1.0, -1.0])
    contrast = float(c @ beta)
    contrast_se = math.sqrt(max(0.0, float(c @ cov @ c)))
    output = {}
    for i, label in enumerate(("strong", "weak")):
        se = math.sqrt(max(0.0, float(cov[i, i])))
        output[label] = {"n": int(x[:, i].sum()), "mean": float(beta[i]), "se": se,
                         "range196": [float(beta[i] - 1.96*se), float(beta[i] + 1.96*se)]}
    output["strongMinusWeak"] = {"estimate": contrast, "se": contrast_se,
                                 "range196": [contrast-1.96*contrast_se, contrast+1.96*contrast_se]}
    output["method"] = {"design": "two state indicators, no intercept", "months": len(y),
                        "chronological": True, "bartlettL": 3, "finiteSampleScaling": False,
                        "lagWeights": lag_sums, "descriptiveOnly": True}
    return output


def main():
    # Verify the exact frozen source set before parsing or creating any output.
    bound_paths = {name: bound(ref) for name, ref in SOURCES.items()}
    if (W / "audit-result.json").exists() or (W / "failure.json").exists():
        raise RuntimeError("output path already exists; refusing overwrite")

    prior = json.loads(bound_paths["prior_contract"].read_text())
    cal_ref = prior["calendar"]
    calendar_path = Path(cal_ref["path"])
    if not calendar_path.is_file() or sha(calendar_path) != cal_ref["sha256"]:
        raise RuntimeError(f"calendar missing or SHA mismatch: {calendar_path}")
    calendar_obj = json.loads(calendar_path.read_text())
    trading = [row[0] for row in calendar_obj["data"] if row[1] == "1"]
    monthends = {}
    for date in trading:
        monthends[date[:7]] = date

    price_df = pd.read_parquet(bound_paths["index"])
    price_df = price_df.reset_index()
    if "date" not in price_df.columns or "close" not in price_df.columns:
        raise RuntimeError("index parquet missing date/close")
    price_df["date"] = pd.to_datetime(price_df["date"]).dt.strftime("%Y-%m-%d")
    if price_df["date"].duplicated().any() or (price_df["close"] <= 0).any():
        raise RuntimeError("invalid index dates/prices")
    price_df = price_df.sort_values("date")
    prices = {r.date: (r.date, float(r.close)) for r in price_df[["date", "close"]].itertuples(index=False)}
    monthly = []
    for month in MONTHS:
        computed = calc_state(month, prices, monthends)
        monthly.append({"month": month, **computed})
    if len(monthly) != 132 or len({m["month"] for m in monthly}) != 132:
        raise RuntimeError("expected 132 unique monthly labels")
    legacy = json.loads(bound_paths["regimes"].read_text())
    old_months = legacy["monthly"]
    if [m["month"] for m in old_months] != MONTHS:
        raise RuntimeError("legacy labels do not cover contract months in order")
    state_map = {m["month"]: m["state"] for m in monthly}
    label_diffs = []
    max_close_diff = max_sma_diff = 0.0
    for new, old in zip(monthly, old_months):
        for key in ("state", "formationMonth", "calculationCutoff"):
            if new[key] != old[key]:
                label_diffs.append({"month": new["month"], "field": key,
                                    "computed": new[key], "saved": old[key]})
        for key, tracker in (("indexClose", "close"), ("sma10", "sma")):
            if new[key] is None or old[key] is None:
                if new[key] != old[key]:
                    label_diffs.append({"month": new["month"], "field": key})
            else:
                delta = abs(float(new[key]) - float(old[key]))
                if tracker == "close": max_close_diff = max(max_close_diff, delta)
                else: max_sma_diff = max(max_sma_diff, delta)
                if delta > 1e-9:
                    label_diffs.append({"month": new["month"], "field": key, "absDiff": delta})
    if label_diffs:
        raise RuntimeError(f"independent label reconciliation failed: {label_diffs[:5]}")

    prefix_failures = []
    for row in monthly:
        cutoff = row["calculationCutoff"]
        prefix_prices = {d: v for d, v in prices.items() if cutoff is not None and d <= cutoff}
        before = calc_state(row["month"], prefix_prices, monthends)
        if before["state"] != row["state"] or before["indexClose"] != row["indexClose"] or before["sma10"] != row["sma10"]:
            prefix_failures.append(row["month"])
    if prefix_failures:
        raise RuntimeError(f"prefix-only invariance failed: {prefix_failures[:5]}")

    # Small synthetic edge cases for the exact declared rule.
    sample_month = "2015-01"
    prev = str(pd.Period(sample_month, "M") - 1)
    win = [str(pd.Period(prev, "M") - i) for i in reversed(range(10))]
    synthetic_ends = {m: f"{m}-28" for m in win}
    equal_prices = {synthetic_ends[m]: (synthetic_ends[m], 100.0) for m in win}
    equal_case = calc_state(sample_month, equal_prices, synthetic_ends)["state"]
    missing_prices = dict(equal_prices)
    missing_prices.pop(synthetic_ends[win[4]])
    missing_case = calc_state(sample_month, missing_prices, synthetic_ends)["state"]
    if equal_case != "weak" or missing_case != "unknown":
        raise RuntimeError("synthetic equal-price or missing-month case failed")

    summary = json.loads(bound_paths["summary"].read_text())
    if len(summary["streams"]) != 84 or set(summary["streams"]) != set(legacy["statistics"]):
        raise RuntimeError("expected exact 84 legacy streams and matching projections")
    legacy_fields = ("months", "meanReturn", "meanBenchmarkDifference", "lossMonthFraction",
                     "benchmarkUpMonths", "benchmarkDownMonths", "meanUpBenchmarkDifference",
                     "meanDownBenchmarkDifference", "meanMonthlyPeakUnknown")
    recon = {"cells": 0, "fields": 0, "mismatches": [], "maxAbsDifference": 0.0}
    all_metrics = {}
    for stream_id, stream in summary["streams"].items():
        parts = stream_id.split("__")
        if len(parts) == 3:  # common-pool stream has no G1..G5 segment
            universe, factor, fee_tag = parts
        elif len(parts) == 4:
            universe, factor, _group, fee_tag = parts
        else:
            raise RuntimeError(f"unexpected stream id shape: {stream_id}")
        pool_id = f"{universe}__pool__{fee_tag}"
        pool = summary["streams"].get(pool_id)
        if pool is None:
            raise RuntimeError(f"missing pool stream {pool_id}")
        point_months = set(point_map(stream))
        for period in ("all", "early", "middle", "late"):
            period_months = list(stream["period"][period]["monthly"])
            if period_months != list(pool["period"][period]["monthly"]):
                raise RuntimeError(f"factor/pool monthly date mismatch: {stream_id} {period}")
            for label in ("strong", "weak", "unknown"):
                selected = [m for m in period_months if state_map[m] == label]
                m = cell_metrics(stream, pool, period, selected, state_map)
                all_metrics[(stream_id, period, label)] = m
                saved = legacy["statistics"][stream_id][period][label]
                checks = {
                    "months": m["months"], "meanReturn": m["factorMeanReturn"],
                    "meanBenchmarkDifference": m["pairedDifferenceMean"],
                    "lossMonthFraction": m["factorLossMonthFraction"],
                    "benchmarkUpMonths": m["benchmarkUpMonths"],
                    "benchmarkDownMonths": m["benchmarkDownMonths"],
                    "meanUpBenchmarkDifference": m["meanDifferenceWhenPoolUp"],
                    "meanDownBenchmarkDifference": m["meanDifferenceWhenPoolDown"],
                    "meanMonthlyPeakUnknown": m["factorMeanOfMonthlyPeakUnknownFraction"],
                }
                recon["cells"] += 1
                for field in legacy_fields:
                    recon["fields"] += 1
                    a, b = checks[field], saved[field]
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        delta = abs(float(a)-float(b))
                        recon["maxAbsDifference"] = max(recon["maxAbsDifference"], delta)
                        ok = delta <= TOL
                    else:
                        ok = a == b
                    if not ok:
                        recon["mismatches"].append({"stream": stream_id, "period": period,
                                                    "state": label, "field": field,
                                                    "recomputed": a, "saved": b})
                if saved["selectedMonths"] != selected:
                    recon["mismatches"].append({"stream": stream_id, "period": period,
                                                "state": label, "field": "selectedMonths"})
    if recon["cells"] != 1008 or recon["mismatches"]:
        raise RuntimeError(f"legacy cell reconciliation failed: {recon['mismatches'][:5]}")

    # Every G5 whole-period average must equal the month-count-weighted state means.
    weighted_checks = {"count": 0, "maxAbsDifference": 0.0, "mismatches": []}
    for universe in CONTRACT["universes"]:
        for factor in CONTRACT["factors"]:
            for fee_tag in ("fee0", "fee25"):
                sid = f"{universe}__{factor}__G5__{fee_tag}"
                for period in ("all", "early", "middle", "late"):
                    whole = summary["streams"][sid]["period"][period]["monthly"]
                    n = len(whole)
                    for metric, stream_id in (("factorMeanReturn", sid),
                                              ("poolMeanReturn", f"{universe}__pool__{fee_tag}"),
                                              ("pairedDifferenceMean", sid)):
                        strong = all_metrics[(stream_id, period, "strong")]
                        weak = all_metrics[(stream_id, period, "weak")]
                        if metric == "pairedDifferenceMean":
                            observed = mean([float(whole[m])-float(summary["streams"][f"{universe}__pool__{fee_tag}"]["period"][period]["monthly"][m]) for m in whole])
                        else:
                            target_stream = summary["streams"][stream_id]
                            observed = mean(list(map(float, target_stream["period"][period]["monthly"].values())))
                        expected = ((strong[metric] or 0.0)*strong["months"] +
                                    (weak[metric] or 0.0)*weak["months"]) / n if n else None
                        delta = abs(observed-expected) if observed is not None and expected is not None else 0.0
                        weighted_checks["count"] += 1
                        weighted_checks["maxAbsDifference"] = max(weighted_checks["maxAbsDifference"], delta)
                        if delta > TOL:
                            weighted_checks["mismatches"].append({"stream": sid, "period": period,
                                                                  "metric": metric, "delta": delta})
    if weighted_checks["mismatches"]:
        raise RuntimeError(f"state weighting failed: {weighted_checks['mismatches'][:5]}")

    primary = {}
    for universe in CONTRACT["universes"]:
        for factor in CONTRACT["factors"]:
            key = f"{universe}__{factor}__G5"
            fee_results = {}
            for fee_tag in ("fee25", "fee0"):
                sid = f"{key}__{fee_tag}"
                pool = summary["streams"][f"{universe}__pool__{fee_tag}"]
                stream = summary["streams"][sid]
                all_period = {}
                for period in ("all", "early", "middle", "late"):
                    all_period[period] = {label: all_metrics[(sid, period, label)]
                                          for label in ("strong", "weak", "unknown")}
                # HAC requires the full original 132-month chronological vector.
                y = [float(stream["period"]["all"]["monthly"][m]) -
                     float(pool["period"]["all"]["monthly"][m]) for m in MONTHS]
                if fee_tag == "fee25":
                    fee_results[fee_tag] = {
                        "byPeriodAndState": all_period,
                        "hacAll132": hac(y, state_map),
                        "pairedMonthlyDifferenceAll132": y,
                    }
                else:
                    fee_results[fee_tag] = {"stateMeansByPeriod": {
                        period: {label: {field: all_period[period][label][field]
                                         for field in ("months", "factorMeanReturn", "poolMeanReturn",
                                                       "pairedDifferenceMean")}
                                   for label in ("strong", "weak", "unknown")}
                        for period in ("all", "early", "middle", "late")}}
            primary[key] = fee_results

    episodes = legacy["episodes"]
    if len(episodes) != 19:
        raise RuntimeError(f"expected 19 contiguous episodes, got {len(episodes)}")
    ep_summary = []
    for i, ep in enumerate(episodes):
        ep_months = [m for m in MONTHS if ep["startMonth"] <= m <= ep["endMonth"]]
        ep_summary.append({"episode": i+1, "state": ep["state"], "startMonth": ep["startMonth"],
                           "endMonth": ep["endMonth"], "months": len(ep_months),
                           "period": next((p for p, (a,b) in PERIODS.items() if a <= ep["startMonth"] and ep["endMonth"] <= b), "crosses_period"),
                           "factorResults": {}})
        for key in primary:
            universe, factor, _ = key.split("__")
            fstream = summary["streams"][f"{universe}__{factor}__G5__fee25"]
            pstream = summary["streams"][f"{universe}__pool__fee25"]
            fr = [float(fstream["period"]["all"]["monthly"][m]) for m in ep_months]
            pr = [float(pstream["period"]["all"]["monthly"][m]) for m in ep_months]
            fp, pp = point_map(fstream), point_map(pstream)
            ep_summary[-1]["factorResults"][key] = {
                "factorMeanReturn": mean(fr), "poolMeanReturn": mean(pr),
                "pairedDifferenceMean": mean([a-b for a,b in zip(fr,pr)]),
                "pairedDifferenceContributionSum": float(sum(a-b for a,b in zip(fr,pr))),
                "factorMonthEndCashMean": mean([float(fp[m][3]) for m in ep_months]),
                "poolMonthEndCashMean": mean([float(pp[m][3]) for m in ep_months]),
                "factorMonthEndUnknownMean": mean([float(fp[m][2]) for m in ep_months]),
                "poolMonthEndUnknownMean": mean([float(pp[m][2]) for m in ep_months]),
                "factorMeanOfMonthlyPeakUnknownFraction": mean([float(fp[m][5]) for m in ep_months]),
                "poolMeanOfMonthlyPeakUnknownFraction": mean([float(pp[m][5]) for m in ep_months]),
            }

    delete_episode = {}
    for key in primary:
        universe, factor, _ = key.split("__")
        stream = summary["streams"][f"{universe}__{factor}__G5__fee25"]
        pool = summary["streams"][f"{universe}__pool__fee25"]
        y = {m: float(stream["period"]["all"]["monthly"][m])-
             float(pool["period"]["all"]["monthly"][m]) for m in MONTHS}
        full = {s: mean([y[m] for m in MONTHS if state_map[m] == s]) for s in ("strong", "weak")}
        full["strongMinusWeak"] = full["strong"] - full["weak"]
        deltas = {s: [] for s in ("strong", "weak", "strongMinusWeak")}
        sign_changes = {s: 0 for s in deltas}
        deletion_rows = []
        for i, ep in enumerate(episodes):
            removed = set(m for m in MONTHS if ep["startMonth"] <= m <= ep["endMonth"])
            kept = [m for m in MONTHS if m not in removed]
            vals = {s: mean([y[m] for m in kept if state_map[m] == s]) for s in ("strong", "weak")}
            vals["strongMinusWeak"] = vals["strong"] - vals["weak"]
            for s in deltas:
                delta = vals[s] - full[s]
                deltas[s].append(delta)
                if full[s] != 0 and vals[s] != 0 and (full[s] > 0) != (vals[s] > 0):
                    sign_changes[s] += 1
            deletion_rows.append({"episode": i+1, "strongMean": vals["strong"],
                                  "weakMean": vals["weak"], "strongMinusWeak": vals["strongMinusWeak"]})
        delete_episode[key] = {
            "fullMeans": full,
            "leaveOneEpisodeOutMeansRange": {s: [min([full[s]+x for x in deltas[s]]),
                                                   max([full[s]+x for x in deltas[s]])] for s in deltas},
            "changeFromFullRange": {s: [min(deltas[s]), max(deltas[s])] for s in deltas},
            "signChangeCountVsFull": sign_changes,
            "deletions": deletion_rows,
        }

    source_hashes = {name: {"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}
                     for name, path in bound_paths.items()}
    source_hashes["calendar"] = {"path": str(calendar_path), "sha256": sha(calendar_path),
                                  "bytes": calendar_path.stat().st_size}
    output = {
        "schema": "saved-factor-universe-regime-audit-result/1",
        "contract_sha256": sha(W / "contract.json"),
        "sources": source_hashes,
        "scope": "recompute of previously saved results only; no account simulation or factor sorting",
        "qualification": {
            "months": len(monthly), "firstMonth": MONTHS[0], "lastMonth": MONTHS[-1],
            "stateCounts": {s: sum(m["state"] == s for m in monthly) for s in ("strong", "weak", "unknown")},
            "legacyLabelReconciliation": {"passed": True, "maxCloseAbsDifference": max_close_diff,
                                           "maxSmaAbsDifference": max_sma_diff},
            "prefixOnlyInvariantAll132": True,
            "syntheticEqualPriceIsWeak": equal_case == "weak",
            "syntheticMissingMonthIsUnknown": missing_case == "unknown",
            "legacyAggregationReconciliation": recon,
            "g5WeightedStateReconciliation": weighted_checks,
            "episodes": len(episodes),
        },
        "statesChronological132": monthly,
        "primaryG5": primary,
        "episodes": ep_summary,
        "episodeDeletionSensitivity": delete_episode,
        "periods": {p: {"firstMonth": a, "lastMonth": b, "months": len(pd.period_range(a,b,freq="M"))}
                    for p,(a,b) in PERIODS.items()},
        "interpretationBoundary": [
            "All 2015-2025 history was previously examined; state episodes and two pools are dependent.",
            "HAC ranges use no finite-sample scaling and are descriptive only; no significance claim.",
            "The stored account values are adjusted-quote proxies with prior execution and missing-price limitations.",
            "Index source vintage availability, supplier revisions and point-in-time fund/stock data are not established.",
        ],
    }
    dest = W / "audit-result.json"
    payload = json.dumps(output, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    if len(payload.encode("utf-8")) >= 250_000:
        raise RuntimeError(f"result too large: {len(payload.encode('utf-8'))}")
    with dest.open("x") as f:
        f.write(payload)
    print(json.dumps({"result": str(dest), "bytes": dest.stat().st_size,
                      "months": len(monthly), "streams": len(summary["streams"]),
                      "cells": recon["cells"], "episodes": len(episodes),
                      "maxLegacyAbsDiff": recon["maxAbsDifference"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
