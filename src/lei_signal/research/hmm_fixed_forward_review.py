"""Score a dated continuation with the already frozen HMM and ridge fits.

This is a research helper, not a new workflow contract or a model fit. Its
caller must separately qualify the appended economic prices and actions.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pandas as pd

from lei_signal.research import workflow_inputs as shared
from lei_signal.research.factor_lab.benchmarks import local_features
from lei_signal.research.hmm_market_state_information import (
    ADDED_FEATURES, DEFINITION_REF, anchor_probabilities,
    load_saved_model, validate_feature_contract,
)
from lei_signal.research.price_volume_path_information import (
    ASSETS, BASELINE_FEATURES, IDENTITY, day_values,
)
from lei_signal.research.risk_shape_information import baseline_values
from lei_signal.research.session_composition_information import candidate_values as session_values

ROOT = Path(__file__).resolve().parents[3]
PREFIX_END = "2026-06-30"
PREFIX_DATES = 1337
PREFIX_SHA256 = "aaf497e345404bacd0bc3db3899928de4ba5767fc10b332af5351dd13340c00d"


def _check_prefix(payload, contract, review_end):
    if payload.get("data_mode") != "historical_reconstruction" or payload.get("price_series") != "economic_price":
        raise ValueError("fixed review requires real historical economic prices")
    if contract["data"]["sha256"] != PREFIX_SHA256:
        raise ValueError("original contract does not bind the frozen June input")
    old_path = ROOT / contract["data"]["path"]
    old_bytes = old_path.read_bytes()
    if hashlib.sha256(old_bytes).hexdigest() != PREFIX_SHA256:
        raise ValueError("frozen June input bytes changed")
    old = json.loads(old_bytes)
    old_dates, dates = old["calendar"], payload.get("calendar")
    if (len(old_dates) != PREFIX_DATES or old_dates[-1] != PREFIX_END or
        not isinstance(dates, list) or dates[:PREFIX_DATES] != old_dates or
        dates != sorted(set(dates)) or review_end < PREFIX_END or
        any(not PREFIX_END < d <= review_end for d in dates[PREFIX_DATES:])):
        raise ValueError("appended calendar changed the frozen prefix or review boundary")
    old_rows = {(r["asset"], r["date"]): r for r in old["bars"]}
    bars = payload.get("bars")
    if not isinstance(bars, list):
        raise ValueError("appended bars missing")
    before = {(r["asset"], r["date"]): r for r in bars if r["date"] <= PREFIX_END}
    if before != old_rows or len(before) != len([r for r in bars if r["date"] <= PREFIX_END]):
        raise ValueError("appended input changed an old quote")
    return dates


def prepare_fixed_extension(payload, original_contract, review_end="2026-09-28", compute_labels=False):
    """Recompute identical 28+2 daily fields across old and appended dates.

    A price/action qualification must precede use of appended observations.
    Default X-only mode does not inspect future target prices.
    """
    validate_feature_contract(original_contract)
    if original_contract["feature"]["comparison_mode"] != "full_price":
        raise ValueError("fixed extension needs the original full-price contract")
    if compute_labels and not (original_contract.get("permissions", {}).get("real_labels") is True and
                               original_contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real outcome calculation has no contract authorization")
    calendar = _check_prefix(payload, original_contract, review_end)
    model, center, scale = load_saved_model(original_contract["feature"])
    by_key = {}
    for row in payload["bars"]:
        key = row["asset"], row["date"]
        if key in by_key or key[0] not in ASSETS or key[1] not in calendar:
            raise ValueError("duplicate or out-of-scope quote")
        if row.get("status") == "quoted" and not all(shared._number(row.get(k)) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted OHLC")
        by_key[key] = row
    anchor_rows = [by_key.get((ASSETS[0], date)) for date in calendar]
    probabilities = anchor_probabilities(calendar, anchor_rows, model, center, scale, earliest="2022-01-01")
    observations, counts, per_asset = [], Counter(), {}
    for asset in ASSETS:
        rows = [by_key.get((asset, date), {"asset": asset, "date": date, "status": "vendor_missing"}) for date in calendar]
        states, segment = {}, []
        def commit_segment():
            if segment:
                frame = local_features(pd.DataFrame({"close": [r["close"] for _, r in segment]}), 20)
                for (j, _), (_, state) in zip(segment, frame.iterrows()):
                    states[j] = state
                segment.clear()
        for j, (own, anchor) in enumerate(zip(rows, anchor_rows)):
            if (own and anchor and own.get("status") == anchor.get("status") == "quoted" and
                own.get("action_known") is True and anchor.get("action_known") is True):
                segment.append((j, own))
            else:
                commit_segment()
        commit_segment()
        own_close, own_open, market_close, days = [], [], [], []
        tr_ema, acount = None, Counter()
        for i, date in enumerate(calendar):
            own, anchor = rows[i], anchor_rows[i]
            quoted = bool(own and anchor and own.get("status") == anchor.get("status") == "quoted" and
                own.get("action_known") is True and anchor.get("action_known") is True)
            if quoted:
                previous_close = own_close[-1] if own_close else None
                own_close.append(float(own["close"])); own_open.append(float(own["open"])); market_close.append(float(anchor["close"]))
                day = day_values(own, previous_close)
                if day is not None:
                    days.append(day)
                    if len(days) > 60: days.pop(0)
                    if tr_ema is None and len(days) >= 20:
                        tr_ema = math.fsum(d["true_range"] for d in days[-20:]) / 20
                    elif tr_ema is not None:
                        tr_ema = (2/21)*day["true_range"] + (19/21)*tr_ema
            else:
                own_close, own_open, market_close, days, tr_ema = [], [], [], [], None
            if not "2022-01-04" <= date <= review_end: continue
            counts["scheduled"] += 1; acount["scheduled"] += 1
            base = (baseline_values(own_close, market_close, states.get(i))
                    if len(own_close) >= 252 and tr_ema is not None else None)
            feature = None
            if base is not None and days and date in probabilities:
                direction = math.fsum(int(b>a)-int(b<a) for a,b in zip(own_close[-21:-1],own_close[-20:]))/20
                overnight = session_values(own_close, own_open)["overnight_minus_intraday20"]
                today = days[-1]
                feature = {**base, "direction20": direction,
                    "overnight_minus_intraday20": overnight,
                    "atr20_fraction": tr_ema/own_close[-1],
                    "today_range": today["range"], "today_close_location": today["close_location"],
                    **{name: int(asset == code) for name, code in zip(IDENTITY, ASSETS[1:])},
                    "market_hmm_p0": float(probabilities[date][0]),
                    "market_hmm_p1": float(probabilities[date][1])}
            common = bool(feature and all(isinstance(feature.get(name), (int, float)) and
                math.isfinite(feature[name]) for name in BASELINE_FEATURES + ADDED_FEATURES))
            y, label_end, target_reason = (shared._label(rows, i, target=original_contract["target"])
                if compute_labels else (None, None, "not_computed"))
            reason = None if common else "background_or_hmm_unavailable"
            if common: counts["feature_ready"] += 1; acount["feature_ready"] += 1
            eligible = bool(common and (y is not None if compute_labels else True))
            if eligible: counts["eligible"] += 1; acount["eligible"] += 1
            observations.append({"id": f"{asset}|{date}", "asset": asset, "date": date,
                "stratum": f"{asset}|{date[:4]}", "features": feature or {}, "eligible": eligible,
                "y": y, "label_end": label_end, "label_reason": reason or target_reason,
                "feature_reason": reason, "target_label_reason": target_reason,
                "tested_condition": None, "definition_ref": DEFINITION_REF})
        per_asset[asset] = dict(acount)
    return {"observations": observations, "coverage": {**counts, "per_asset": per_asset},
        "warnings": ["New-period source and action qualification is a separate prerequisite; no HMM or ridge refit was performed."]}


def predict_saved(rows, fit_details):
    """Apply the two previously saved ridge fits to X rows; no fitting."""
    if isinstance(fit_details, dict) and "fit_details" in fit_details:
        fit_details = fit_details["fit_details"]
    if not isinstance(fit_details, list) or len(fit_details) != 2:
        raise ValueError("expected exactly two saved ridge fits")
    fits = {f.get("model"): f for f in fit_details}
    if set(fits) != {"B1", "B2"}:
        raise ValueError("saved B1/B2 fit identities missing")
    expected = {"B1": list(BASELINE_FEATURES), "B2": list(BASELINE_FEATURES + ADDED_FEATURES)}
    for key, f in fits.items():
        fields = f.get("features")
        if (f.get("fold") != "0" or f.get("lambda") != 1.0 or
            f.get("training_rows") != 5536 or fields != expected[key] or
            any(not isinstance(f.get(field), list) or len(f[field]) != len(fields)
                for field in ("mean", "std", "coef")) or
            any(not isinstance(v, (int, float)) or not math.isfinite(v)
                for field in ("mean", "std", "coef") for v in f[field]) or
            any(v <= 0 for v in f["std"]) or
            not isinstance(f.get("intercept"), (int, float)) or not math.isfinite(f["intercept"])):
            raise ValueError(f"saved {key} coefficients changed or invalid")
    if not math.isclose(fits["B1"]["intercept"], fits["B2"]["intercept"], abs_tol=1e-10):
        raise ValueError("saved intercepts do not share one training population")
    output = []
    for row in rows:
        feature = row["features"]
        if not all(isinstance(feature.get(name), (int, float)) and math.isfinite(feature[name])
                   for name in BASELINE_FEATURES + ADDED_FEATURES):
            raise ValueError(f"missing fixed feature at {row.get('id')}")
        values = {}
        for key, fit in fits.items():
            values[key] = fit["intercept"] + math.fsum(
                (feature[name] - mean) / std * coef for name, mean, std, coef in
                zip(fit["features"], fit["mean"], fit["std"], fit["coef"]))
        output.append({"id": row["id"], "asset": row["asset"], "date": row["date"],
            "B0": fits["B1"]["intercept"], **values})
    return output
