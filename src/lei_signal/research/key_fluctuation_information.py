"""Research-only dual-break information, observed after a completed close.

K is a deterministic expression of known prices, not a production exit rule.
The EMA seed and log-return volatility intentionally follow the T01 adapter.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import math
import random
import statistics

from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel

DEFINITION_REF = "research.key_fluctuation.dual_break20@1.0.0"
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def phase(day: str) -> str:
    if day <= "2024-12-31":
        return PHASES[0]
    if day <= "2025-12-31":
        return PHASES[1]
    return PHASES[2]


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "key_fluctuation_information" or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented"):
        raise ValueError("K01 requires dual-break N20, SMA60 and segmented252")
    if (target.get("kind") != "mae" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("path_field", "close") != "close" or
            target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("K01 freezes t+1..t+21 closing-path MAE")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("K01 retains scheduled daily observations")
    if payload.get("data_mode") != "synthetic" and contract["question"].get("period") != ["2022-01-04", "2026-06-30"]:
        raise ValueError("K01 freezes the qualified four-ETF historical period")
    if payload.get("data_mode") != "synthetic" and payload.get("price_series") != "economic_price":
        raise ValueError("K01 needs qualified economic OHLC")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or calendar != sorted(set(calendar)):
        raise ValueError("ordered unique calendar required")
    for d in calendar:
        shared._date(d)
    assets = contract["universe"]["assets"]
    if not isinstance(assets, list) or len(assets) != len(set(assets)) or not assets:
        raise ValueError("ordered unique assets required")
    if payload.get("data_mode") != "synthetic" and tuple(assets) != ASSETS:
        raise ValueError("K01 freezes four domestic ETF identities")
    by_key = {}
    for row in payload["bars"]:
        key = (row["asset"], row["date"])
        if key in by_key or row["asset"] not in assets or row["date"] not in calendar:
            raise ValueError("duplicate/out-of-scope bar")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar has price")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid OHLC")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def prepare_key_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """The default path never indexes future price rows or calls a labeler."""
    if (compute_labels and payload.get("data_mode") != "synthetic" and
            not (contract.get("permissions", {}).get("real_labels") is True and
                 contract.get("permissions", {}).get("effect_authorized") is True)):
        raise ValueError("real future labels require separate explicit authorization")
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index_of = {d: i for i, d in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, d), {"asset": asset, "date": d, "status": "vendor_missing"})) for d in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        closes, ema20 = [], None
        counts = Counter()
        for row in rows:
            d = row["date"]
            if d > available_end:
                break
            if _known(row):
                close = float(row["close"])
                closes.append(close)
                ema20 = close if ema20 is None else (2 * close + 19 * ema20) / 21
            else:
                closes, ema20 = [], None
                counts["price_reset_rows"] += 1
            if d not in selected or not first <= d <= last:
                continue
            ready = len(closes) >= WARMUP
            up = sum(closes[-60:]) > sum(closes[-65:-5]) if ready else None
            k = (closes[-1] < ema20 and closes[-1] < closes[-21]) if ready else None
            r1 = 100 * (closes[-1] / closes[-2] - 1) if ready else None
            ret3 = 100 * (closes[-1] / closes[-4] - 1) if ready else None
            ret20 = 100 * (closes[-1] / closes[-21] - 1) if ready else None
            vol20 = (statistics.stdev([math.log(closes[i] / closes[i-1]) for i in range(len(closes)-20, len(closes))])
                     * math.sqrt(252) * 100) if ready else None
            ema20_distance = 100 * (closes[-1] / ema20 - 1) if ready else None
            features = {"r1": r1, "ret3": ret3, "ret20": ret20, "vol20": vol20,
                        "ema20_distance": ema20_distance, "added": int(k) if ready else None}
            for code in ASSETS[1:]:
                features["asset_" + code.split(".")[0]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, label_end, label_reason = (shared._label(label_rows, index_of[d], target=contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            reason = None if ready else "continuous252_or_economic_price_missing"
            eligible = bool(ready and up and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{d}", "asset": asset, "date": d,
                "stratum": f"{asset}|{d[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": reason or ("sma60_not_rising" if ready and not up else label_reason),
                "feature_reason": reason, "tested_condition": k, "sma60_up": up,
                "critical_down20": k, "r1": r1, "ret3": ret3, "ret20": ret20,
                "vol20": vol20, "ema20_distance": ema20_distance,
                "continuous_real_ohlc": len(closes), "ready_252": ready,
                "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["trend_up"] += int(bool(up))
            counts["k_true"] += int(bool(k and up))
            counts["k_false"] += int(bool(k is False and up))
            counts["eligible"] += int(eligible)
        per_asset[asset] = dict(counts)
    keys = ("observations", "ready_252", "trend_up", "k_true", "k_false", "eligible", "price_reset_rows")
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in keys}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["K为已知价格的确定组合；这里仅研究风险信息，不实施卖出。"]}


def match_known_features(observations, calendar):
    """Match using only completed-time covariates, with reusable controls."""
    index = {d: i for i, d in enumerate(calendar)}
    controls = defaultdict(list)
    for row in observations:
        if row["ready_252"] and row["sma60_up"] and row["critical_down20"] is False:
            controls[(row["asset"], phase(row["date"]))].append(row)
    pairs, support = [], []
    for focal in observations:
        if not (focal["ready_252"] and focal["sma60_up"] and focal["critical_down20"] is True):
            continue
        candidates = []
        for control in controls[(focal["asset"], phase(focal["date"]))]:
            dt = abs(index[focal["date"]] - index[control["date"]])
            dr = abs(focal["r1"] - control["r1"])
            d3 = abs(focal["ret3"] - control["ret3"])
            d20 = abs(focal["ret20"] - control["ret20"])
            dv = abs(focal["vol20"] - control["vol20"])
            if dt <= 60 and dr <= .5 and d3 <= 1 and d20 <= 3 and dv <= 5:
                distance = dr/.5 + d3 + d20/3 + dv/5
                candidates.append((distance, dt, control["date"], control))
        chosen = sorted(candidates, key=lambda z: z[:3])[:3]
        support.append({"id": focal["id"], "asset": focal["asset"],
                        "phase": phase(focal["date"]), "matched": bool(chosen),
                        "controls": len(chosen)})
        for rank, item in enumerate(chosen, 1):
            pairs.append({"event_id": focal["id"], "control_id": item[3]["id"],
                          "rank": rank, "distance": item[0]})
    return pairs, support


def qualify_key_panel(payload: dict, contract: dict, root: Path) -> dict:
    return qualify_top_panel(payload, contract, root)


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    source = qualify_key_panel(payload, contract, root)
    prepared = prepare_key_observations(payload, contract, compute_labels=False)
    observations = prepared["observations"]
    pairs, support = match_known_features(observations, payload["calendar"])
    by_phase = {}
    for p in PHASES:
        events = [r for r in support if r["phase"] == p]
        group = [r for r in observations if phase(r["date"]) == p]
        by_phase[p] = {"scheduled": len(group), "trend_up": sum(r["sma60_up"] is True for r in group),
                       "k_true": len(events), "k_false": sum(r["critical_down20"] is False and r["sma60_up"] is True for r in group),
                       "matched": sum(r["matched"] for r in events), "unmatched": sum(not r["matched"] for r in events)}
    counts = {"assets": len(contract["universe"]["assets"]),
              "observations": len(observations),
              "dates": len({r["date"] for r in observations}), "episodes": None}
    folds = []
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    for fold in contract["split"]["folds"]:
        train = [r for r in observations if r["sma60_up"] is True and
                 index[r["date"]] + 21 < len(calendar) and
                 r["date"] <= fold["train_end"] and
                 calendar[index[r["date"]] + 21] < fold["eval_start"]]
        ev = [r for r in observations if r["sma60_up"] is True and
              fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              index[r["date"]] + 21 < len(calendar) and
              calendar[index[r["date"]] + 21] <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "train_true": sum(r["critical_down20"] is True for r in train),
                      "train_false": sum(r["critical_down20"] is False for r in train),
                      "evaluation": len(ev), "evaluation_true": sum(r["critical_down20"] is True for r in ev),
                      "evaluation_false": sum(r["critical_down20"] is False for r in ev)})
    return {"qualification": {"outcome_values_used_for_design": False,
        "data_sha256": contract["data"]["sha256"], "source_quality": source["quality"],
        "source_warnings": source["warnings"], "coverage": prepared["coverage"],
        "counts": counts, "scientific_support": {"phases": by_phase, "folds": folds,
                    "matched": sum(r["matched"] for r in support),
                    "unmatched": sum(not r["matched"] for r in support),
                    "pairs": len(pairs), "distinct_controls": len({r["control_id"] for r in pairs}),
                    "model_feature_count": 9,
                    "note": "Present and past values only; date positions establish possible maturity without reading future prices."}},
        "pairs": pairs, "match_support": support}


def _path_values(rows, start, end):
    if end >= len(rows):
        return None
    path = rows[start:end+1]
    if any(not _known(r) for r in path):
        return None
    return [float(r["close"]) for r in path]


def describe_paths(payload, observations, pairs, *, horizon=20):
    """Effects are deliberately callable only by an explicit separate run."""
    if horizon not in (5, 10, 20, 60, 120):
        raise ValueError("unfrozen horizon")
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    by_id = {r["id"]: r for r in observations}
    by_asset = defaultdict(dict)
    for r in payload["bars"]:
        by_asset[r["asset"]][r["date"]] = r
    paths = {}
    for key in {p["event_id"] for p in pairs} | {p["control_id"] for p in pairs}:
        row = by_id[key]
        i = index[row["date"]]
        end = i + horizon + 1
        if end >= len(calendar) or phase(calendar[end]) != phase(row["date"]):
            continue
        asset_rows = [by_asset[row["asset"]].get(d, {"status": "vendor_missing"}) for d in calendar]
        values = _path_values(asset_rows, i+1, end)
        if values is None:
            continue
        entry = values[0]
        mae = 100 * max(0, 1 - min(values)/entry)
        mfe = 100 * max(0, max(values)/entry - 1)
        peak, mdd = entry, 0.0
        for v in values:
            peak = max(peak, v)
            mdd = max(mdd, 100 * (1-v/peak))
        paths[key] = {"mae": mae, "mfe": mfe, "return": 100*(values[-1]/entry-1), "mdd": mdd,
                      "loss5": int(mae >= 5), "loss10": int(mae >= 10), "loss15": int(mae >= 15)}
    grouped = defaultdict(list)
    for p in pairs:
        if p["event_id"] in paths and p["control_id"] in paths:
            grouped[p["event_id"]].append(paths[p["control_id"]])
    by_asset_differences = defaultdict(list)
    for key, cc in grouped.items():
        a = paths[key]
        diffs = {metric: a[metric] - statistics.mean(c[metric] for c in cc) for metric in a}
        by_asset_differences[by_id[key]["asset"]].append((by_id[key]["date"], diffs))
    return {"matched_mature": sum(map(len, by_asset_differences.values())),
            "by_asset_differences": dict(by_asset_differences), "paths": paths}


def summarize_paired_effects(description, *, block_lengths=(20, 60), draws=1000, seed=20261001):
    """Equal-weight assets after averaging controls within each focal K day.

    Resampling uses one shared date axis for all ETFs. It is a sensitivity range,
    not independent evidence, and is never invoked by no-label qualification.
    """
    rows = [(asset, day, diff) for asset, items in description["by_asset_differences"].items()
            for day, diff in items]
    if not rows:
        return {"matched_mature": 0, "status": "no_mature_pairs"}
    metrics = tuple(rows[0][2])

    def aggregate(selected):
        per_asset = defaultdict(list)
        for asset, _, diff in selected:
            per_asset[asset].append(diff)
        if not per_asset:
            return None
        return {metric: statistics.mean(statistics.mean(r[metric] for r in rr)
                                        for rr in per_asset.values()) for metric in metrics}

    by_asset = {asset: aggregate([r for r in rows if r[0] == asset])
                for asset in sorted({r[0] for r in rows})}
    by_phase = {p: aggregate([r for r in rows if phase(r[1]) == p])
                for p in PHASES}
    axis = sorted({day for _, day, _ in rows})
    date_rows = defaultdict(list)
    for row in rows:
        date_rows[row[1]].append(row)
    rng = random.Random(seed)
    uncertainty = {}
    for length in block_lengths:
        if length < 1:
            raise ValueError("block length must be positive")
        samples = {metric: [] for metric in metrics}
        for _ in range(draws):
            sampled = []
            while len(sampled) < len(axis):
                start = rng.randrange(len(axis))
                sampled.extend(axis[(start + j) % len(axis)] for j in range(length))
            chosen = [row for day in sampled[:len(axis)] for row in date_rows[day]]
            result = aggregate(chosen)
            if result is not None:
                for metric in metrics:
                    samples[metric].append(result[metric])
        def percentile(values, q):
            ordered = sorted(values)
            pos = q * (len(ordered) - 1)
            lo = int(pos)
            return ordered[lo] + (ordered[min(lo + 1, len(ordered) - 1)] - ordered[lo]) * (pos - lo)
        uncertainty[str(length)] = {metric: [percentile(values, .025), percentile(values, .975)]
                                    for metric, values in samples.items() if values}
    overall = aggregate(rows)
    return {"matched_mature": len(rows), "overall_equal_asset": overall,
            "by_asset": by_asset, "by_phase_equal_asset": by_phase,
            "asset_counterexamples": {asset: value["mae"] <= 0 for asset, value in by_asset.items()},
            "uncertainty_sensitivity": uncertainty, "resampling": {
                "shared_date_axis": True, "block_lengths": list(block_lengths),
                "draws": draws, "seed": seed, "control_reuse": "allowed and not independent"}}
