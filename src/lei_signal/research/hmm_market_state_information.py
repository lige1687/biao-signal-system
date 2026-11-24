"""Retrospective ETF risk feature from a saved 510300 Gaussian HMM.

The state numbers are unnamed. This module never fits a model or uses a
backward-smoothed probability. The fitted model was available only after
2024-12-31, so earlier representations are training history, not live signals.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np
import pandas as pd

from lei_signal.research import workflow_inputs as shared
from lei_signal.research.factor_lab.benchmarks import local_features
from lei_signal.research.price_volume_path_information import (
    ASSETS, BASELINE_FEATURES, IDENTITY, day_values,
)
from lei_signal.research.risk_shape_information import baseline_values
from lei_signal.research.session_composition_information import candidate_values as session_values

KIND = "hmm_market_state_information"
DEFINITION_REF = "research.market.hmm_anchor_probability@1.0.0"
ADDED_FEATURES = ("market_hmm_p0", "market_hmm_p1")
MODEL_SHA256 = "4fb8ae6ed7d0a75efa59432388f38ce5f9e8cddb3919ac0d999f4e5ee2ea9be4"
MODEL_PATH = "docs/experiments/raw/douyin-system-increment-2026-10-07/hmm-time-trial/model-parameters.json"
FOLD = {"train_end": "2024-12-31", "eval_start": "2025-01-02", "eval_end": "2026-06-30"}
ROOT = Path(__file__).resolve().parents[3]


def validate_feature_contract(contract):
    """Check the fixed feature, source identity, sample and risk target."""
    f, q, t = contract["feature"], contract["question"], contract["target"]
    mode = f.get("comparison_mode")
    expected_baseline = BASELINE_FEATURES if mode == "full_price" else IDENTITY
    if (f.get("kind") != KIND or f.get("definition_ref") != DEFINITION_REF or
        mode not in {"full_price", "identity_only"} or
        contract["evaluator"].get("baseline_features") != list(expected_baseline) or
        contract["evaluator"].get("added_features") != list(ADDED_FEATURES) or
        f.get("anchor_asset") != contract["universe"]["assets"][0] or f.get("lookback") != 20 or
        f.get("warmup") != 252 or f.get("missing_policy") != "segmented" or
        f.get("bar_frequency") != "daily_quote" or
        f.get("model_path") != MODEL_PATH or f.get("model_sha256") != MODEL_SHA256 or
        f.get("model_fit_end") != FOLD["train_end"] or
        q.get("factor_refs") != [DEFINITION_REF] or q.get("sampling") != "daily" or
        (contract["data"]["mode"] != "synthetic" and (
            q.get("period") != ["2022-01-04", "2026-06-30"] or
            contract["universe"]["assets"] != list(ASSETS) or
            contract["split"]["folds"] != [FOLD])) or
        t.get("kind") != "mae" or t.get("start_offset") != 1 or
        t.get("end_offset") != 21 or t.get("entry_field") != "close" or
        t.get("path_field") != "close" or t.get("unit") != "percentage_point" or
        t.get("price_measure") != "economic_price"):
        raise ValueError("HMM feature requires the fixed saved model, eight ETFs, fold and closing risk target")


def load_saved_model(feature, *, root=ROOT):
    """Verify saved bytes and restore an actual GaussianHMM, without fitting."""
    if (feature.get("model_path") != MODEL_PATH or
        feature.get("model_sha256") != MODEL_SHA256 or
        feature.get("model_fit_end") != FOLD["train_end"]):
        raise ValueError("HMM model path, hash or fit end changed")
    path = Path(root) / MODEL_PATH
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MODEL_SHA256:
        raise ValueError("HMM model hash mismatch")
    saved = json.loads(raw)
    import hmmlearn
    from hmmlearn.hmm import GaussianHMM
    if (saved.get("method") != "hmmlearn.hmm.GaussianHMM" or
        saved.get("hmmlearn_version") != "0.3.3" or hmmlearn.__version__ != "0.3.3" or
        saved.get("scaler", {}).get("fit_end") != FOLD["train_end"] or
        saved.get("fit", {}).get("market_fits") != 1):
        raise ValueError("HMM model identity, runtime or training boundary mismatch")
    start = _array(saved.get("startprob"), (3,), "startprob", nonnegative=True)
    trans = _array(saved.get("transmat"), (3, 3), "transmat", nonnegative=True)
    means = _array(saved.get("means"), (3, 2), "means")
    variances = _array(saved.get("variances"), (3, 2), "variances", positive=True)
    center = _array(saved["scaler"].get("mean"), (2,), "scaler mean")
    scale = _array(saved["scaler"].get("std"), (2,), "scaler std", positive=True)
    if not np.isclose(start.sum(), 1, atol=1e-10) or not np.allclose(trans.sum(axis=1), 1, atol=1e-10):
        raise ValueError("invalid HMM probability matrix")
    model = GaussianHMM(n_components=3, covariance_type="diag", init_params="", params="", implementation="log")
    model.n_features = 2
    model.startprob_, model.transmat_, model.means_, model.covars_ = start, trans, means, variances
    if type(model) is not GaussianHMM or model.covariance_type != "diag":
        raise ValueError("wrong HMM model method")
    model._check()
    return model, center, scale


def _array(value, shape, name, *, nonnegative=False, positive=False):
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric {name}") from exc
    if arr.shape != shape or not np.isfinite(arr).all() or (nonnegative and (arr < 0).any()) or (positive and (arr <= 0).any()):
        raise ValueError(f"invalid {name}")
    return arr


def _logsumexp(values):
    m = max(values)
    if not math.isfinite(m):
        raise ValueError("nonfinite HMM likelihood")
    return m + math.log(math.fsum(math.exp(x - m) for x in values))


def forward_step(model, observation, previous=None):
    """P(state at t | observations through t), with log-space normalization."""
    x = _array(observation, (2,), "HMM observation")
    if previous is None:
        prior = model.startprob_
    else:
        p = _array(previous, (3,), "previous state probability", nonnegative=True)
        if not math.isclose(float(p.sum()), 1, abs_tol=1e-10):
            raise ValueError("previous HMM probabilities do not sum to one")
        prior = p @ model.transmat_
    v = np.diagonal(model.covars_, axis1=1, axis2=2)
    log_emission = -0.5 * (np.log(2 * math.pi * v).sum(axis=1) + (((x - model.means_) ** 2) / v).sum(axis=1))
    log_weight = [math.log(p) + float(e) if p > 0 else -math.inf for p, e in zip(prior, log_emission)]
    normalizer = _logsumexp(log_weight)
    result = np.array([math.exp(w - normalizer) for w in log_weight])
    if not np.isfinite(result).all() or (result < 0).any() or (result > 1).any() or not math.isclose(float(result.sum()), 1, abs_tol=1e-10):
        raise ValueError("invalid filtered HMM probability")
    return result


def anchor_probabilities(calendar, anchor_rows, model, center, scale, *, earliest="2022-01-01"):
    """Build probabilities from 2022 onward; gaps reset the running filter."""
    output, closes, returns, previous = {}, [], [], None
    for date, row in zip(calendar, anchor_rows):
        if not row or row.get("status") != "quoted" or row.get("action_known") is not True or not shared._number(row.get("close")):
            closes, returns, previous = [], [], None
            continue
        close = float(row["close"])
        if closes:
            returns.append(100 * math.log(close / closes[-1]))
        closes.append(close)
        if len(returns) < 20 or date < earliest:
            continue
        window = returns[-20:]
        volatility = statistics.stdev(window)
        if not math.isfinite(volatility) or volatility <= 0:
            previous = None
            continue
        x = (np.array([returns[-1], math.log(volatility)]) - center) / scale
        previous = forward_step(model, x, previous)
        output[date] = previous
    return output


def prepare_observations(payload, contract, *, compute_labels=False):
    validate_feature_contract(contract)
    if payload.get("data_mode") != "synthetic" and payload.get("price_series") != "economic_price":
        raise ValueError("HMM feature requires qualified economic prices")
    if compute_labels and payload.get("data_mode") != "synthetic" and not (
        contract.get("permissions", {}).get("real_labels") is True and
        contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real labels require effect authorization")
    model, center, scale = load_saved_model(contract["feature"])
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("calendar must be ordered unique")
    by_key = {}
    for row in payload["bars"]:
        key = row["asset"], row["date"]
        if key in by_key or key[0] not in contract["universe"]["assets"] or key[1] not in calendar:
            raise ValueError("duplicate or out-of-scope quote")
        if row.get("status") == "quoted" and not all(shared._number(row.get(k)) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted OHLC")
        by_key[key] = row
    assets = contract["universe"]["assets"]
    anchor_rows = [by_key.get((assets[0], date)) for date in calendar]
    probabilities = anchor_probabilities(calendar, anchor_rows, model, center, scale,
        earliest="0000-01-01" if payload.get("data_mode") == "synthetic" else "2022-01-01")
    observations, counts, per_asset = [], Counter(), {}
    first, last = contract["question"]["period"]
    for asset in assets:
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
            if not first <= date <= last: continue
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
            y, label_end, target_reason = (shared._label(rows, i, target=contract["target"])
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
        "warnings": ["固定模型仅在2024-12-31拟合后可用；此前概率只作训练表示。历史资料到达时间未证实，不解释为实盘信号。"]}


def qualify_hmm_panel(payload, contract, root):
    """Recheck saved eight-ETF source bytes and feature support, without labels."""
    if payload.get("data_mode") == "synthetic":
        ready = prepare_observations(payload, contract, compute_labels=False)
        return {"data_sha256": contract["data"]["sha256"],
            "outcome_values_used_for_design": False, "coverage": ready["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]),
                "observations": len(ready["observations"]), "dates": len({row["date"] for row in ready["observations"]}), "episodes": None},
            "scientific_support": {"model_feature_count": len(contract["evaluator"]["baseline_features"])+len(ADDED_FEATURES),
                "folds": []}, "source_warnings": ready["warnings"]}
    validate_feature_contract(contract)
    qpath = Path(root) / contract["data"]["qualification"]["manifest_path"]
    q = json.loads(qpath.read_text())
    if (q.get("status") != "qualified_retrospective_8_etfs_only" or
        q.get("workflow_input", {}).get("sha256") != contract["data"]["sha256"] or
        q.get("prepared_rows") != len(payload["bars"]) or
        len(q.get("field_evidence", [])) != 11):
        raise ValueError("eight-ETF qualification or prepared input mismatch")
    for entry in q["field_evidence"]:
        source = Path(root) / entry["path"]
        if source.stat().st_size != entry["bytes"] or hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("source evidence changed: " + entry["path"])
    ready = prepare_observations(payload, contract, compute_labels=False)
    calendar = payload["calendar"]
    positions = {d: i for i, d in enumerate(calendar)}
    horizon = contract["target"]["end_offset"]
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in ready["observations"] if r["eligible"] and
            r["date"] <= fold["train_end"] and positions[r["date"]]+horizon < len(calendar) and
            calendar[positions[r["date"]]+horizon] < fold["eval_start"]]
        evaluation = [r for r in ready["observations"] if r["eligible"] and
            fold["eval_start"] <= r["date"] <= fold["eval_end"] and
            positions[r["date"]]+horizon < len(calendar) and
            calendar[positions[r["date"]]+horizon] <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(evaluation),
            "train_dates": len({r["date"] for r in train}),
            "evaluation_dates": len({r["date"] for r in evaluation})})
    return {"data_sha256": contract["data"]["sha256"],
        "outcome_values_used_for_design": False, "source_quality": q.get("quality"),
        "coverage": ready["coverage"], "counts": {"assets": len(ASSETS),
            "observations": len(ready["observations"]), "dates": len({row["date"] for row in ready["observations"]}), "episodes": None},
        "scientific_support": {"folds": folds,
            "model_feature_count": len(contract["evaluator"]["baseline_features"])+len(ADDED_FEATURES),
            "unknown_reasons": dict(Counter(r["feature_reason"] for r in ready["observations"] if r["feature_reason"])),
            "note": "Calendar maturity and present features only; future target values were not read."},
        "source_warnings": ready["warnings"]}
