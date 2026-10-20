"""Frozen matched-pair diagnostic runner. No network access is used."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import plistlib
import random
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from lei_signal.research.annual_profitability import operating_profitability_after_da

METHODS = ("profitability", "higher_momentum", "lower_momentum")
MONTHS = tuple(f"{year:04d}-{month:02d}" for year in range(2015, 2025) for month in range(1, 13))
SEED = 20261020
DEFINITION_REF = "research.fundamental.annual_operating_profitability_after_da@1.0.0"
OUTPUT_WHITELIST = (
    "formation-with-feature.csv", "pairs.csv", "policy-choices.csv", "monthly.csv", "yearly.csv",
    "period-summary.json", "uncertainty.json", "sign-cells.csv", "coverage.json",
    "odd-omissions.csv",
)


def _finite(value):
    try:
        x = float(value)
        return math.isfinite(x)
    except (TypeError, ValueError, OverflowError):
        return False


def _json(value, default=None):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _rank(values):
    ordered = sorted((v, i) for i, v in enumerate(values))
    result = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        avg = ((i + 1) + j) / 2
        for _, ix in ordered[i:j]:
            result[ix] = avg
        i = j
    return result


def _corr(x, y):
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    rx, ry = _rank(x), _rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    sx = math.sqrt(sum((v - mx) ** 2 for v in rx))
    sy = math.sqrt(sum((v - my) ** 2 for v in ry))
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def make_pairs(rows, month_index):
    """Return adjacent momentum pairs and an optional omitted odd-ranked row."""
    ordered = sorted(rows, key=lambda r: (float(r["momentum"]), r["ticker"]))
    omitted = None
    if len(ordered) % 2:
        n = len(ordered)
        rank_1based = 1 + 2 * (month_index % ((n + 1) // 2))
        omitted = ordered.pop(rank_1based - 1)
    pairs = [(ordered[i], ordered[i + 1]) for i in range(0, len(ordered), 2)]
    return pairs, omitted


def make_choices(month, rows, month_index):
    """Create feature-only decisions; deliberately never reads outcome fields."""
    usable = [r for r in rows if r.get("admit") is True and
              _finite(r.get("momentum")) and _finite(r.get("op"))]
    tickers = [r["ticker"] for r in usable]
    if len(tickers) != len(set(tickers)):
        raise ValueError(f"duplicate admitted ticker in {month}")
    ciks = [str(r.get("candidate_cik", r.get("cik", ""))).strip() for r in usable]
    ciks = [x for x in ciks if x]
    if len(ciks) != len(set(ciks)):
        raise ValueError(f"duplicate admitted issuer CIK in {month}")
    pairs, omitted = make_pairs(usable, month_index)
    choices = []
    for ix, (a, b) in enumerate(pairs):
        if float(a["momentum"]) > float(b["momentum"]):
            high, low = a, b
        elif float(a["momentum"]) < float(b["momentum"]):
            high, low = b, a
        else:
            high = low = min((a, b), key=lambda r: r["ticker"])
        if float(a["op"]) > float(b["op"]):
            profit = a
        elif float(a["op"]) < float(b["op"]):
            profit = b
        else:
            profit = high
        op_tie = float(a["op"]) == float(b["op"])
        op_high, op_low = (None, None) if op_tie else (
            (a, b) if float(a["op"]) > float(b["op"]) else (b, a))
        choices.append({
            "target_month": month, "pair_index": ix + 1,
            "ticker_a": a["ticker"], "ticker_b": b["ticker"],
            "momentum_gap": abs(float(a["momentum"]) - float(b["momentum"])),
            "op_a": float(a["op"]), "op_b": float(b["op"]),
            "op_rank_a": _rank([float(x["op"]) for x in usable])[usable.index(a)],
            "op_rank_b": _rank([float(x["op"]) for x in usable])[usable.index(b)],
            "op_tie": op_tie,
            "op_high_ticker": op_high["ticker"] if op_high else None,
            "op_low_ticker": op_low["ticker"] if op_low else None,
            "op_high_minus_low": abs(float(a["op"]) - float(b["op"])) if not op_tie else None,
            "profitability_ticker": profit["ticker"],
            "higher_momentum_ticker": high["ticker"],
            "lower_momentum_ticker": low["ticker"],
        })
    return choices, omitted


def connect_outcomes(choices, outcomes, outcome_reasons=None):
    """Join labels only after choices are fixed; keep unknowns as None."""
    result = []
    for choice in choices:
        row = dict(choice)
        for method in METHODS:
            ticker = row[f"{method}_ticker"]
            raw = outcomes.get(ticker)
            row[f"{method}_return"] = raw if _finite(raw) and float(raw) >= -1 else None
            if raw is not None and row[f"{method}_return"] is None:
                row[f"{method}_return_reason"] = "invalid_or_below_minus100pct_return"
            else:
                reason = (outcome_reasons or {}).get((row.get("target_month"), ticker), "outcome_unknown")
                row[f"{method}_return_reason"] = "" if raw is not None else reason
        if row.get("op_high_ticker") is None or row.get("op_low_ticker") is None:
            row["op_high_minus_low_return_delta"] = None
            row["op_high_minus_low_return_delta_reason"] = "op_tie"
        else:
            high_return = outcomes.get(row["op_high_ticker"])
            low_return = outcomes.get(row["op_low_ticker"])
            if _finite(high_return) and _finite(low_return) and high_return >= -1 and low_return >= -1:
                row["op_high_minus_low_return_delta"] = high_return - low_return
                row["op_high_minus_low_return_delta_reason"] = ""
            else:
                row["op_high_minus_low_return_delta"] = None
                row["op_high_minus_low_return_delta_reason"] = "one_or_both_op_ranked_labels_unknown"
        result.append(row)
    return result


def _delta_summary(rows, method, opponent):
    k = len(rows)
    known, loss_parts, upside_parts, losses = [], [], [], []
    cells = defaultdict(lambda: {"count": 0, "delta_sum": 0.0})
    bounds = []
    for row in rows:
        ta, tb = row[f"{method}_ticker"], row[f"{opponent}_ticker"]
        ra, rb = row[f"{method}_return"], row[f"{opponent}_return"]
        if ta == tb:
            delta = 0.0
            known.append(delta)
            loss_parts.append(0.0)
            upside_parts.append(0.0)
            if ra is not None:
                losses.append((int(ra < 0), int(rb < 0)))
                cell = ("profitability_negative_opponent_nonnegative" if ra < 0 <= rb else
                        "profitability_nonnegative_opponent_negative" if rb < 0 <= ra else
                        "both_negative" if ra < 0 and rb < 0 else "both_nonnegative")
                cells[cell]["count"] += 1
                cells[cell]["delta_sum"] += delta
            else:
                losses.append((None, None))
        elif ra is not None and rb is not None:
            delta = ra - rb
            known.append(delta)
            da = min(ra, 0.0) - min(rb, 0.0)
            db = max(ra, 0.0) - max(rb, 0.0)
            loss_parts.append(da)
            upside_parts.append(db)
            cell = ("profitability_negative_opponent_nonnegative" if ra < 0 <= rb else
                    "profitability_nonnegative_opponent_negative" if rb < 0 <= ra else
                    "both_negative" if ra < 0 and rb < 0 else "both_nonnegative")
            cells[cell]["count"] += 1
            cells[cell]["delta_sum"] += delta
            losses.append((int(ra < 0), int(rb < 0)))
        else:
            delta = None
            # Same security has exact zero difference; different security is unbounded for returns.
            losses.append((int(ra < 0) if ra is not None else None,
                           int(rb < 0) if rb is not None else None))
        bounds.append((ta == tb, ra, rb))
    known_count = len(known)
    out = {
        "pairs": k, "known_delta_pairs": known_count,
        "unknown_delta_pairs": k - known_count,
        "unknown_delta_weight": (k - known_count) / k if k else None,
        "known_delta_sum": sum(known),
        "known_original_weight_contribution": sum(known) / k if k else None,
        "known_identifiable_mean": statistics.mean(known) if known else None,
        "known_delta_min": min(known) if known else None,
        "known_delta_max": max(known) if known else None,
        "known_delta_positive": sum(x > 0 for x in known),
        "known_delta_zero": sum(x == 0 for x in known),
        "known_delta_negative": sum(x < 0 for x in known),
        "known_loss_part_sum": sum(loss_parts),
        "known_upside_part_sum": sum(upside_parts),
        "known_loss_part_original_weight_contribution": sum(loss_parts) / k if k else None,
        "known_upside_part_original_weight_contribution": sum(upside_parts) / k if k else None,
        "known_loss_part_identifiable_mean": statistics.mean(loss_parts) if loss_parts else None,
        "known_upside_part_identifiable_mean": statistics.mean(upside_parts) if upside_parts else None,
        "sign_cells": {k: {**v, "delta_mean": v["delta_sum"] / v["count"] if v["count"] else None}
                       for k, v in sorted(cells.items())},
    }
    # Paired loss-event difference bounds honor common-security cancellation.
    lo = hi = 0.0
    known_loss_pairs = 0
    own_method_lo = own_op_lo = 0
    own_method_hi = own_op_hi = 0
    for same, ra, rb in bounds:
        if same:
            if ra is not None:
                own_method_lo += int(ra < 0); own_method_hi += int(ra < 0)
                own_op_lo += int(ra < 0); own_op_hi += int(ra < 0)
                known_loss_pairs += 1
            else:
                own_method_hi += 1; own_op_hi += 1
            continue
        if ra is None:
            own_method_hi += 1
        else:
            own_method_lo += int(ra < 0); own_method_hi += int(ra < 0)
        if rb is None:
            own_op_hi += 1
        else:
            own_op_lo += int(rb < 0); own_op_hi += int(rb < 0)
        if ra is not None and rb is not None:
            d = int(ra < 0) - int(rb < 0); lo += d; hi += d; known_loss_pairs += 1
        else:
            a_values = [int(ra < 0)] if ra is not None else [0, 1]
            b_values = [int(rb < 0)] if rb is not None else [0, 1]
            lo += min(a_values) - max(b_values)
            hi += max(a_values) - min(b_values)
    out.update({
        "loss_probability_method_bounds": [own_method_lo / k, own_method_hi / k] if k else None,
        "loss_probability_opponent_bounds": [own_op_lo / k, own_op_hi / k] if k else None,
        "paired_loss_probability_delta_bounds": [lo / k, hi / k] if k else None,
        "known_paired_loss_comparisons": known_loss_pairs,
    })
    return out


def monthly_result(month, pair_rows, formed_rows):
    result = {"target_month": month, "pair_count": len(pair_rows), "formed_count": len(formed_rows)}
    observed = [r for r in formed_rows if r.get("target_return") is not None]
    result["observed_formed_count"] = len(observed)
    result["op_return_spearman_n"] = len(observed)
    result["op_return_spearman"] = _corr([float(r["op"]) for r in observed],
                                          [float(r["target_return"]) for r in observed])
    feature = [r for r in formed_rows if _finite(r.get("op")) and _finite(r.get("momentum"))]
    result["op_momentum_rank_n"] = len(feature)
    result["op_momentum_rank_correlation"] = _corr([float(r["op"]) for r in feature],
                                                    [float(r["momentum"]) for r in feature])
    result["distinct_annual_filings"] = len({r.get("adsh") for r in formed_rows if r.get("adsh")})
    result["median_pair_momentum_gap"] = statistics.median([r["momentum_gap"] for r in pair_rows]) if pair_rows else None
    result["max_pair_momentum_gap"] = max([r["momentum_gap"] for r in pair_rows], default=None)
    for m in METHODS:
        values = [r[f"{m}_return"] for r in pair_rows]
        known = [v for v in values if v is not None]
        result[f"{m}_known_return_count"] = len(known)
        result[f"{m}_unknown_return_count"] = len(values) - len(known)
        result[f"{m}_mean_identifiable"] = statistics.mean(known) if known else None
        method_complete = bool(pair_rows) and len(known) == len(pair_rows)
        result[f"{m}_complete_month_loss_part_mean"] = statistics.mean([min(v, 0.0) for v in known]) if method_complete else None
        result[f"{m}_complete_month_upside_part_mean"] = statistics.mean([max(v, 0.0) for v in known]) if method_complete else None
        result[f"{m}_complete_month_loss_probability"] = sum(v < 0 for v in known) / len(known) if method_complete else None
    for m, opp in (("profitability", "higher_momentum"), ("profitability", "lower_momentum")):
        s = _delta_summary(pair_rows, m, opp)
        prefix = f"{m}_minus_{opp}"
        for key, val in s.items():
            if key != "sign_cells":
                result[f"{prefix}_{key}"] = val
        result[f"{prefix}_sign_cells"] = s["sign_cells"]
    all_known = bool(pair_rows) and all(result[f"{m}_unknown_return_count"] == 0 for m in METHODS)
    result["all_methods_complete"] = all_known
    if all_known and pair_rows:
        for m in METHODS:
            result[f"{m}_complete_month_mean"] = result[f"{m}_mean_identifiable"]
    else:
        for m in METHODS:
            result[f"{m}_complete_month_mean"] = None
    return result


def period_stats(months):
    out = {"calendar_months": len(months)}
    common = [m for m in months if m["all_methods_complete"]]
    out["all_methods_complete_months"] = len(common)
    for method in METHODS:
        vals = [m[f"{method}_complete_month_mean"] for m in common
                if m[f"{method}_complete_month_mean"] is not None]
        loss = [m[f"{method}_complete_month_loss_part_mean"] for m in common
                if m[f"{method}_complete_month_loss_part_mean"] is not None]
        upside = [m[f"{method}_complete_month_upside_part_mean"] for m in common
                  if m[f"{method}_complete_month_upside_part_mean"] is not None]
        loss_prob = [m[f"{method}_complete_month_loss_probability"] for m in common
                     if m[f"{method}_complete_month_loss_probability"] is not None]
        out[method] = {
            "mean_monthly_return": statistics.mean(vals) if vals else None,
            "sample_std_monthly_return": statistics.stdev(vals) if len(vals) > 1 else None,
            "worst_decile_mean": (statistics.mean(sorted(vals)[:math.ceil(.1 * len(vals))]) if vals else None),
            "mean_monthly_loss_part": statistics.mean(loss) if loss else None,
            "mean_monthly_upside_part": statistics.mean(upside) if upside else None,
            "mean_monthly_loss_probability": statistics.mean(loss_prob) if loss_prob else None,
        }
    for opp in ("higher_momentum", "lower_momentum"):
        vals = [m[f"profitability_minus_{opp}_known_original_weight_contribution"] for m in months
                if m[f"profitability_minus_{opp}_known_original_weight_contribution"] is not None]
        out[f"profitability_minus_{opp}"] = {
            "mean_known_original_weight_contribution": statistics.mean(vals) if vals else None,
            "months_with_known_contribution": len(vals),
        }
        for label, suffix in (("loss_part", "loss"), ("upside_part", "upside")):
            weighted_key = f"profitability_minus_{opp}_known_{suffix}_part_original_weight_contribution"
            weighted = [m[weighted_key] for m in months if m[weighted_key] is not None]
            identifiable_key = f"profitability_minus_{opp}_known_{suffix}_part_identifiable_mean"
            identifiable = [m[identifiable_key] for m in months if m[identifiable_key] is not None]
            out[f"profitability_minus_{opp}"][f"mean_{label}_original_weight_contribution"] = (
                statistics.mean(weighted) if weighted else None)
            out[f"profitability_minus_{opp}"][f"mean_{label}_identifiable_pair_difference"] = (
                statistics.mean(identifiable) if identifiable else None)
        idvals = [m[f"profitability_minus_{opp}_known_identifiable_mean"] for m in months
                  if m[f"profitability_minus_{opp}_known_identifiable_mean"] is not None]
        out[f"profitability_minus_{opp}"]["mean_known_identifiable_pair_difference"] = (
            statistics.mean(idvals) if idvals else None)
        out[f"profitability_minus_{opp}"]["months_with_identifiable_pair_difference"] = len(idvals)
    return out


def block_bootstrap(monthly, replications=2000, seed=SEED):
    """Resample all fixed calendar positions jointly in circular 12-month blocks."""
    n = len(monthly)
    if n == 0:
        return {}
    rng = random.Random(seed)
    blocks = math.ceil(n / 12)
    stats = defaultdict(list)
    for _ in range(replications):
        ids = []
        for _b in range(blocks):
            start = rng.randrange(n)
            ids.extend((start + j) % n for j in range(12))
        sample = [monthly[i] for i in ids[:n]]
        for opp in ("higher_momentum", "lower_momentum"):
            prefix = f"profitability_minus_{opp}_"
            for metric, suffix in {
                "delta_original_weight": "known_original_weight_contribution",
                "delta_identifiable_mean": "known_identifiable_mean",
                "loss_part": "known_loss_part_original_weight_contribution",
                "upside_part": "known_upside_part_original_weight_contribution",
                "loss_part_identifiable_mean": "known_loss_part_identifiable_mean",
                "upside_part_identifiable_mean": "known_upside_part_identifiable_mean",
            }.items():
                key = prefix + suffix
                vals = [m[key] for m in sample if m.get(key) is not None]
                stats[f"{opp}_{metric}"].append(statistics.mean(vals) if vals else None)
            for bound_name in ("loss_probability_method_bounds", "loss_probability_opponent_bounds",
                               "paired_loss_probability_delta_bounds"):
                key = prefix + bound_name
                for side in (0, 1):
                    vals = [m[key][side] for m in sample if m.get(key) is not None]
                    stats[f"{opp}_{bound_name}_{side}"].append(statistics.mean(vals) if vals else None)
    output = {}
    for key, vals in stats.items():
        finite = sorted(v for v in vals if v is not None and math.isfinite(v))
        def pct(p):
            if not finite:
                return None
            pos = (len(finite) - 1) * p
            lo, hi = math.floor(pos), math.ceil(pos)
            return finite[lo] + (finite[hi] - finite[lo]) * (pos - lo)
        output[key] = {"replications": replications, "seed": seed,
                       "percentile_2_5": pct(.025), "percentile_97_5": pct(.975),
                       "valid_replications": len(finite)}
    return output


def compute_effect(formed, outcomes, replications=2000, choices_by_month=None, outcome_reasons=None):
    """Pure calculation entrypoint shared by synthetic tests and CLI."""
    formed_by_month = defaultdict(list)
    for row in formed:
        if row.get("admit") is True and _finite(row.get("momentum")) and _finite(row.get("op")):
            formed_by_month[row["target_month"]].append(row)
    choices_by_month = dict(choices_by_month or {})
    pair_outcomes, omitted_by_month = {}, {}
    feature_rows, all_pair_rows = [], []
    for ti, month in enumerate(MONTHS):
        rows = formed_by_month.get(month, [])
        if month not in choices_by_month:
            choices, omitted = make_choices(month, rows, ti)
            choices_by_month[month] = choices
            omitted_by_month[month] = omitted
        else:
            choices = choices_by_month[month]
        connected = connect_outcomes(choices, outcomes.get(month, {}), outcome_reasons)
        pair_outcomes[month] = connected
        all_pair_rows.extend(connected)
        for row in rows:
            val = outcomes.get(month, {}).get(row["ticker"])
            if val is not None and (not _finite(val) or float(val) < -1):
                reason = "invalid_or_below_minus100pct_return"
                val = None
            else:
                reason = (outcome_reasons or {}).get((month, row["ticker"]), "" if val is not None else "outcome_unknown")
            row["target_return"] = float(val) if val is not None else None
            row["target_return_reason"] = reason
            feature_rows.append(dict(month=row["target_month"], **row))
    monthly = [monthly_result(m, pair_outcomes[m], formed_by_month.get(m, [])) for m in MONTHS]
    prior_weights = {method: {} for method in METHODS}
    for ti, (month, mrow) in enumerate(zip(MONTHS, monthly)):
        choices = choices_by_month[month]
        for method in METHODS:
            names = [x[f"{method}_ticker"] for x in choices]
            weights = defaultdict(float)
            if names:
                for name in names:
                    weights[name] += 1 / len(names)
            prev = prior_weights[method]
            mrow[f"{method}_selected_count"] = len(names)
            mrow[f"{method}_target_weight_change"] = (None if ti == 0 else
                0.5 * sum(abs(weights.get(k, 0) - prev.get(k, 0))
                          for k in set(weights) | set(prev)))
            prior_weights[method] = dict(weights)
        mrow["profitability_agrees_higher_momentum_fraction"] = (
            sum(x["profitability_ticker"] == x["higher_momentum_ticker"] for x in choices) / len(choices)
            if choices else None)
        mrow["profitability_switches_from_higher_momentum"] = sum(
            x["profitability_ticker"] != x["higher_momentum_ticker"] for x in choices)
        if ti == 0:
            mrow["changed_report_tickers_from_prior_month"] = None
        else:
            prev_reports = {r["ticker"]: r.get("adsh") for r in formed_by_month.get(MONTHS[ti - 1], [])}
            now_reports = {r["ticker"]: r.get("adsh") for r in formed_by_month.get(month, [])}
            mrow["changed_report_tickers_from_prior_month"] = sum(
                prev_reports[t] != now_reports[t] for t in set(prev_reports) & set(now_reports))
    periods = {"full_2015_2024": period_stats(monthly)}
    for label, months in (("2015_2019", MONTHS[:60]), ("2020_2024", MONTHS[60:])):
        periods[label] = period_stats([m for m in monthly if m["target_month"] in months])
    uncertainty = block_bootstrap(monthly, replications=replications)
    return {"formed": feature_rows, "choices": choices_by_month, "pairs": all_pair_rows,
            "monthly": monthly, "periods": periods, "uncertainty": uncertainty,
            "omitted": omitted_by_month}


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_binding(binding):
    p = Path(binding["path"])
    digest = binding["sha256"]
    if (not p.is_absolute() or not isinstance(digest, str) or len(digest) != 64 or
            any(c not in "0123456789abcdef" for c in digest) or not p.is_file() or _sha(p) != digest):
        raise ValueError(f"input binding absent/hash mismatch: {p}")
    return p


def _verify_contract_bindings(contract):
    if contract.get("schema") != "matched-effect-execution-contract/1":
        raise ValueError("unsupported execution contract schema")
    bindings = contract.get("inputs")
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("contract must contain SHA-bound bindings")
    resolved = {}
    for name, binding in bindings.items():
        path = _verify_binding(binding)
        resolved[name] = path
    runner = resolved.get("runner")
    if runner is None or runner.resolve() != Path(__file__).resolve():
        raise ValueError("contract runner binding must identify this script")
    expected_design = Path(__file__).with_name("matched-effect-design.json").resolve()
    if resolved.get("design", Path("/missing")).resolve() != expected_design:
        raise ValueError("contract design binding must identify the frozen design")
    for required in ("design", "adapter", "definition_snapshot", "tests", "accounting_candidates", "filings", "admission"):
        if required not in resolved:
            raise ValueError(f"contract input binding missing: {required}")
    adapter = (Path(__file__).resolve().parents[4] / "src/lei_signal/research/annual_profitability.py").resolve()
    if resolved["adapter"].resolve() != adapter:
        raise ValueError("contract adapter binding must identify the formal adapter")
    snapshot = json.loads(resolved["definition_snapshot"].read_text(encoding="utf-8"))
    target = [o for o in snapshot.get("objects", []) if o.get("id") == "research.fundamental.annual_operating_profitability_after_da"
              and o.get("version") == "1.0.0"]
    if len(target) != 1:
        raise ValueError("definition snapshot does not uniquely contain the fixed definition")
    return resolved


def _verify_storage(storage, out_path):
    mount = Path(storage["mount"])
    if not mount.is_dir() or os.stat(mount).st_dev != int(storage["device"]):
        raise ValueError("external storage mount/device mismatch")
    expected_uuid = storage.get("uuid")
    if not expected_uuid:
        raise ValueError("frozen external storage UUID missing")
    info = subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)],
                          check=True, capture_output=True).stdout
    actual_uuid = plistlib.loads(info).get("VolumeUUID")
    if actual_uuid != expected_uuid:
        raise ValueError("external storage UUID mismatch")
    try:
        if os.path.commonpath((str(mount.resolve()), str(out_path.resolve()))) != str(mount.resolve()):
            raise ValueError("output path is outside bound external mount")
    except ValueError as exc:
        raise ValueError("output path is outside bound external mount") from exc
    if "reserve_bytes" not in storage:
        raise ValueError("frozen external storage reserve missing")
    minimum = int(storage.get("minimum_free_bytes", storage["reserve_bytes"]))
    if minimum and os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize < minimum:
        raise ValueError("external storage below frozen free-space requirement")


def _load_jsonl(path):
    rows = {}
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if row["adsh"] in rows:
                    raise ValueError(f"duplicate filing accession in JSONL: {row['adsh']}")
                rows[row["adsh"]] = row
    return rows


def _filing_op(filing):
    if filing.get("sourcequalified") is not True or filing.get("automatic_scoring_eligible") is not True:
        return None
    facts = filing.get("source_facts", {})
    oi = facts.get("operating_income")
    interest = facts.get("interest")
    equity = facts.get("inclusive_equity")
    if not all(isinstance(x, list) and len(x) == 1 for x in (oi, interest, equity)):
        return None
    fact = [x[0] for x in (oi, interest, equity)]
    if any(x.get("uom") != "USD" or x.get("segments") or x.get("coreg") or
           not str(x.get("version", "")).startswith("us-gaap/") for x in fact):
        return None
    if fact[0].get("tag") != "OperatingIncomeLoss" or fact[2].get("tag") != \
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest":
        return None
    if fact[0].get("ddate") != fact[1].get("ddate") or fact[0].get("ddate") != fact[2].get("ddate"):
        return None
    if fact[0].get("qtrs") != "4" or fact[1].get("qtrs") != "4" or fact[2].get("qtrs") != "0":
        return None
    if fact[1].get("tag") not in {"InterestExpense", "InterestExpenseNonOperating"}:
        return None
    # Confirm that the interest line is separately presented below OI on the same IS report.
    oi_lines = {(str(p.get("report")), int(p["line"])) for p in fact[0].get("presentation", [])
                if p.get("stmt") == "IS" and str(p.get("line", "")).isdigit()}
    int_lines = {(str(p.get("report")), int(p["line"])) for p in fact[1].get("presentation", [])
                 if p.get("stmt") == "IS" and str(p.get("line", "")).isdigit()}
    if not any(report == report2 and line2 > line for report, line in oi_lines for report2, line2 in int_lines):
        return None
    values = [x.get("value") for x in fact]
    if not all(_finite(value) for value in values):
        return None
    return operating_profitability_after_da(*(float(value) for value in values), financials_qualified=True)


def _admission_map(data):
    items = data if isinstance(data, list) else data.get("rows", [])
    if not isinstance(items, list):
        raise ValueError("final admission rows must be a list")
    result = {}
    for row in items:
        if not isinstance(row, dict) or type(row.get("admit")) is not bool or type(row.get("outcome_pending")) is not bool:
            raise ValueError("final admission row missing boolean admit/outcome_pending")
        key = (row.get("target_month"), row.get("ticker"), row.get("candidate_cik", row.get("cik")), row.get("adsh", ""))
        if not all(key) or key in result:
            raise ValueError("final admission row has incomplete/duplicate identity")
        result[key] = row
    return result


def _load_inputs(contract):
    inputs = contract["inputs"]
    paths = {key: _verify_binding(binding) for key, binding in inputs.items() if isinstance(binding, dict) and "path" in binding}
    with paths["accounting_candidates"].open(encoding="utf-8", newline="") as stream:
        panel = list(csv.DictReader(stream))
    filings = _load_jsonl(paths["filings"])
    admission = json.loads(paths["admission"].read_text(encoding="utf-8"))
    if admission.get("schema") != "annual-op-admission/1":
        raise ValueError("unsupported final admission schema")
    amap = _admission_map(admission)
    formed, label_rows, panel_keys = [], [], set()
    for row in panel:
        key = (row["target_month"], row["ticker"], row["candidate_cik"], row["adsh"])
        if key in panel_keys:
            raise ValueError(f"duplicate accounting candidate key: {key}")
        panel_keys.add(key)
        admitted = amap.get(key, {})
        # Future outcome status only controls the label join, never selection membership.
        formation_quote = _json(row.get("formation_quote_detail_json"), {}) or {}
        valid_mom = row.get("mom_all_12_endpoints_qualified") == "True" and _finite(row.get("mom_11_month_adjusted_price_change"))
        admit = (admitted.get("admit") is True and row.get("sourcequalified") == "True" and
                 row.get("automatic_scoring_eligible") == "True" and valid_mom and
                 row.get("formation_quote_qualified") == "True" and _finite(formation_quote.get("adj_close")) and
                 float(formation_quote["adj_close"]) > 0)
        op = _filing_op(filings.get(row["adsh"], {}))
        if op is None:
            admit = False
        formed.append({**row, "admit": admit, "op": op,
                       "momentum": float(row["mom_11_month_adjusted_price_change"]) if valid_mom else None})
        label_rows.append((row, admitted))
        if admitted.get("admit") is True and not admit:
            raise ValueError(f"final-admitted row failed runner revalidation: {key}")
    missing = [key for key, item in amap.items() if item.get("admit") is True and key not in panel_keys]
    if missing:
        raise ValueError(f"admitted identities missing from accounting candidate CSV: {len(missing)}")
    return formed, label_rows, paths, amap


def _load_outcomes(label_rows, formed):
    """Read target labels only after feature-only choices have been persisted."""
    formed_keys = {(r["target_month"], r["ticker"], r.get("candidate_cik"), r.get("adsh"))
                   for r in formed if r.get("admit") is True}
    candidates = defaultdict(list)
    reasons = {}
    for row, admitted in label_rows:
        key = (row["target_month"], row["ticker"], row.get("candidate_cik"), row.get("adsh"))
        if key not in formed_keys:
            continue
        target_q = _json(row.get("target_month_end_quote_detail_json"), {}) or {}
        status = admitted.get("outcome_status")
        outcome_status_known = ((admitted.get("outcome_pending") is False and not admitted.get("outcome_reasons")) or
                                admitted.get("outcome_qualified") is True or status in ("qualified", "known"))
        outcome_ok = (outcome_status_known and
                      row.get("target_month_end_quote_present_and_qualified") == "True" and
                      target_q.get("qualified") is True and _finite(target_q.get("adj_close")) and float(target_q["adj_close"]) > 0)
        if outcome_ok:
            form_q = _json(row.get("formation_quote_detail_json"), {}) or {}
            if _finite(form_q.get("adj_close")) and float(form_q["adj_close"]) > 0:
                candidates[(row["target_month"], row["ticker"])].append(
                    float(target_q["adj_close"]) / float(form_q["adj_close"]) - 1)
            else:
                reasons[(row["target_month"], row["ticker"])] = "formation_price_invalid"
        else:
            recorded = admitted.get("outcome_reasons") or []
            reasons[(row["target_month"], row["ticker"])] = (
                ";".join(str(x) for x in recorded) if recorded else
                str(row.get("target_quote_reason") or ("outcome_pending" if admitted.get("outcome_pending") else
                                                       "target_quote_unqualified")))
    outcomes = defaultdict(dict)
    for (month, ticker), values in candidates.items():
        if len(values) == 1:
            outcomes[month][ticker] = values[0]
        else:
            reasons[(month, ticker)] = "duplicate_admitted_target_quote_rows"
    return outcomes, reasons


def _write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def run(contract_path, out_path):
    contract_path, out_path = Path(contract_path), Path(out_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("execution_authorized") is not True:
        raise ValueError("execution_authorized must be true")
    if contract.get("definition_ref") != DEFINITION_REF:
        raise ValueError("contract definition_ref mismatch")
    bindings = _verify_contract_bindings(contract)
    frozen_out = contract.get("output_directory", contract.get("output_path"))
    if frozen_out and Path(frozen_out) != out_path:
        raise ValueError("--out differs from frozen output directory")
    if out_path.exists():
        raise ValueError("output directory already exists")
    storage = contract["storage"]
    _verify_storage(storage, out_path)
    formed, label_rows, input_paths, _admission = _load_inputs(contract)
    expected = contract.get("expected_counts")
    if not isinstance(expected, dict) or set(expected) != {"admitted_rows", "unique_ciks", "months"}:
        raise ValueError("frozen expected_counts missing")
    admitted_rows = [row for row in _admission.values() if row.get("admit") is True]
    actual_counts = {
        "admitted_rows": len(admitted_rows),
        "unique_ciks": len({str(row.get("candidate_cik")) for row in admitted_rows}),
        "months": len(MONTHS),
    }
    if actual_counts != {key: expected.get(key) for key in actual_counts}:
        raise ValueError(f"final admission counts differ from frozen expectation: {actual_counts}")
    admitted_months = {row.get("target_month") for row in admitted_rows}
    if admitted_months != set(MONTHS):
        raise ValueError("final admission does not cover all 120 frozen calendar months")
    runner_eligible = [r for r in formed if r.get("admit") is True]
    eligible_counts = {"admitted_rows": len(runner_eligible),
                       "unique_ciks": len({str(r.get("candidate_cik")) for r in runner_eligible})}
    if eligible_counts != {"admitted_rows": expected["admitted_rows"], "unique_ciks": expected["unique_ciks"]}:
        raise ValueError(f"runner admission revalidation count mismatch: {eligible_counts}")
    out_path.mkdir(parents=True)
    # Freeze and persist every feature-only pair and selection before joining any target quote.
    choices_by_month, omitted = {}, {}
    for ti, month in enumerate(MONTHS):
        choices_by_month[month], omitted[month] = make_choices(
            month, [r for r in formed if r["target_month"] == month], ti)
    choice_rows = [r for month in MONTHS for r in choices_by_month[month]]
    omission_rows = []
    for month in MONTHS:
        omitted_row = omitted[month]
        if omitted_row is not None:
            ordered = sorted([r for r in formed if r["target_month"] == month and r.get("admit") is True
                              and _finite(r.get("momentum")) and _finite(r.get("op"))],
                             key=lambda r: (float(r["momentum"]), r["ticker"]))
            omission_rows.append({"target_month": month, "original_momentum_rank": ordered.index(omitted_row) + 1,
                                  "ticker": omitted_row["ticker"], "candidate_cik": omitted_row.get("candidate_cik"),
                                  "adsh": omitted_row.get("adsh"), "momentum": omitted_row["momentum"],
                                  "op": omitted_row["op"]})
    _write_csv(out_path / "odd-omissions.csv", omission_rows,
               ["target_month", "original_momentum_rank", "ticker", "candidate_cik", "adsh", "momentum", "op"])
    _write_csv(out_path / "policy-choices.csv", choice_rows,
               ["target_month", "pair_index", "ticker_a", "ticker_b", "momentum_gap", "op_a", "op_b",
                "op_rank_a", "op_rank_b", "op_tie", "op_high_ticker", "op_low_ticker", "op_high_minus_low",
                "profitability_ticker", "higher_momentum_ticker", "lower_momentum_ticker"])
    outcomes, outcome_reasons = _load_outcomes(label_rows, formed)
    result = compute_effect(formed, outcomes, replications=2000, choices_by_month=choices_by_month,
                            outcome_reasons=outcome_reasons)
    _write_csv(out_path / "formation-with-feature.csv", result["formed"],
               ["month", "target_month", "ticker", "candidate_cik", "adsh", "admit", "momentum", "op",
                "target_return", "target_return_reason"])
    _write_csv(out_path / "pairs.csv", result["pairs"], list(result["pairs"][0]) if result["pairs"] else
               ["target_month", "pair_index"])
    _write_csv(out_path / "monthly.csv", result["monthly"], list(result["monthly"][0]))
    yearly = []
    for year in range(2015, 2025):
        ms = [x for x in result["monthly"] if x["target_month"].startswith(str(year))]
        yearly.append({"year": year, "months": 12, **period_stats(ms)})
    _write_csv(out_path / "yearly.csv", yearly, list(yearly[0]))
    summary = {"periods": result["periods"], "months": len(result["monthly"]),
               "formed_rows": len(result["formed"]), "pair_rows": len(result["pairs"]),
               "method": "adjacent momentum pairs; fixed odd omission; no outcome-based pairing"}
    (out_path / "period-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    (out_path / "uncertainty.json").write_text(json.dumps(result["uncertainty"], indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    cells = []
    cell_names = ("both_nonnegative", "both_negative", "profitability_negative_opponent_nonnegative",
                  "profitability_nonnegative_opponent_negative")
    for month in result["monthly"]:
        for opp in ("higher_momentum", "lower_momentum"):
            cell_json = month[f"profitability_minus_{opp}_sign_cells"]
            for name in cell_names:
                val = cell_json.get(name, {"count": 0, "delta_sum": 0.0, "delta_mean": None})
                cells.append({"target_month": month["target_month"], "opponent": opp, "cell": name, **val})
    _write_csv(out_path / "sign-cells.csv", cells, ["target_month", "opponent", "cell", "count", "delta_sum", "delta_mean"])
    admission_reasons = defaultdict(int)
    for row in _admission.values():
        for reason in row.get("reasons", []):
            admission_reasons[str(reason)] += 1
    coverage = {"calendar_months": 120,
                "admission_rows": len(_admission),
                "admitted_rows": sum(row.get("admit") is True for row in _admission.values()),
                "admission_reason_counts": dict(sorted(admission_reasons.items())),
                "admitted_rows_with_pending_outcome": sum(row.get("admit") is True and row.get("outcome_pending") is True
                                                          for row in _admission.values()),
                "months_with_any_formed_candidates": sum(
                    any(r["target_month"] == m for r in result["formed"]) for m in MONTHS),
                "formation_count_by_month": {m: sum(r.get("admit") is True and r["target_month"] == m for r in result["formed"]) for m in MONTHS},
                "observed_target_labels_by_month": {m: sum(r.get("target_return") is not None and r["target_month"] == m
                                                           for r in result["formed"]) for m in MONTHS},
                "future_unknowns_never_removed_from_feature_pool": True}
    (out_path / "coverage.json").write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + "\n")
    missing_outputs = [name for name in OUTPUT_WHITELIST if not (out_path / name).is_file()]
    if missing_outputs:
        raise ValueError(f"expected output files missing: {missing_outputs}")
    outputs = {name: {"sha256": _sha(out_path / name), "bytes": (out_path / name).stat().st_size}
               for name in OUTPUT_WHITELIST}
    manifest = {"schema": "matched-effect-manifest/1", "status": "completed", "output_files": outputs,
                "input_hashes": {k: _sha(v) for k, v in input_paths.items()},
                "contract_bindings": {k: _sha(v) for k, v in bindings.items()},
                "definition": DEFINITION_REF,
                "storage": {"mount": storage["mount"], "device": storage["device"], "uuid": storage["uuid"]},
                "network_requests": 0, "real_outcome_diagnostic": True,
                "new_strategy_backtest": False, "calendar_months": 120,
                "bootstrap": {"blocks": "circular_12_calendar_month", "replications": 2000, "seed": SEED}}
    (out_path / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    manifest = run(args.contract, args.out)
    print(json.dumps({"status": manifest["status"], "manifest": str(Path(args.out) / "manifest.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
