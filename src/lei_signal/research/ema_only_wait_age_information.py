"""Research-only, prefix-causal age of the current EMA-only waiting state.

No waiting outcome or future price is inspected during feature preparation by default.
The EMA starts at the first qualified close, matching the D01 research baseline.
"""
from __future__ import annotations

from collections import Counter
from datetime import time
import math
import statistics

import numpy as np

from . import workflow_inputs as shared
from . import deduction_box_information as d01

DEFINITION_REF = "research.trend.ema_only_wait_age20@1.0.0"
BASELINE_FEATURES = (*d01.BASELINE, "deduction_box_distance")
WARMUP = 252


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "ema_only_wait_age_information" or
        feature.get("definition_ref") != DEFINITION_REF or
        feature.get("warmup") != WARMUP or
        feature.get("missing_policy") != "segmented" or
        feature.get("lookback", 20) != 20 or
        feature.get("ema_seed", "first_close") != "first_close" or
        feature.get("sma_lag", 20) != 20 or
        feature.get("age_transform", "log1p") != "log1p" or
        feature.get("censor_policy", "left_censor_unknown_start") != "left_censor_unknown_start"):
        raise ValueError("fixed EMA-only age definition and 252-day segmented warmup required")
    if (target.get("kind") != "forward_return" or target.get("start_offset") != 1 or
        target.get("end_offset") != 21 or target.get("entry_field") != "close" or
        target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("fixed t+1 to t+21 closing return required")
    source_contract = {**contract, "feature": {"kind": "future_deduction_box_information",
        "definition_ref": d01.DEFINITION_REF, "lookback": 20, "box_horizon": 10,
        "warmup": WARMUP, "missing_policy": "segmented"},
        "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                   "entry_field": "close", "path_field": "close", "price_measure": "economic_price"}}
    calendar, assets, keyed = d01._validate(payload, source_contract)
    return calendar, assets, keyed, source_contract


def prepare_sequence_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Keep every scheduled day; X uses only qualified closes through that day."""
    if compute_labels and payload.get("data_mode") != "synthetic":
        permissions = contract.get("permissions", {})
        if permissions.get("real_labels") is not True or permissions.get("effect_authorized") is not True:
            raise ValueError("real labels require real_labels and effect_authorized")
    calendar, assets, keyed, _ = _validate(payload, contract)
    available_end = max((d for _, d in keyed), default=calendar[0])
    if "decision_at" in payload:
        decision = shared._available(payload["decision_at"])
        decision_day = decision.date().isoformat()
        if decision.time() < time(15):
            prior = [d for d in calendar if d < decision_day]
            decision_day = prior[-1] if prior else "0000-00-00"
        available_end = min(available_end, decision_day)
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index = {d: i for i, d in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset in assets:
        rows = [dict(keyed.get((asset, d), {"asset": asset, "date": d, "status": "vendor_missing"})) for d in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        closes, ema = [], None
        age, censored = 0, False
        previous_only = None
        counts = Counter()
        for row in rows:
            day = row["date"]
            if day > available_end:
                break
            known = d01._known(row)
            if known:
                close = float(row["close"])
                closes.append(close)
                ema = close if ema is None else (2 * close + 19 * ema) / 21
            else:
                closes, ema = [], None
                age, censored, previous_only = 0, False, None
                counts["price_reset_rows"] += 1
            e = close > ema if known else None
            s = close > closes[-21] if len(closes) >= 21 else None
            only = bool(e and s is False) if s is not None else None
            if only is True:
                if previous_only is True:
                    age += 1
                else:
                    age = 1
                    censored = previous_only is None
                    counts["waiting_segments"] += 1
                    counts["left_censored_segments"] += int(censored)
                    if day in selected and first <= day <= last:
                        counts["waiting_segments_formal"] += 1
                        counts["left_censored_segments_formal"] += int(censored)
            else:
                age, censored = 0, False
            previous_only = only
            if day not in selected or not first <= day <= last:
                continue
            ready = len(closes) >= WARMUP
            features = {name: None for name in (*BASELINE_FEATURES, "added")}
            if ready:
                daily = [closes[i] / closes[i-1] - 1 for i in range(len(closes)-20, len(closes))]
                features.update(prior20high_distance=100*(close/max(closes[-21:-1])-1),
                    ret20=100*(close/closes[-21]-1), ema20_distance=100*(close/ema-1),
                    r1=100*(close/closes[-2]-1),
                    vol20=statistics.stdev(daily)*math.sqrt(252)*100,
                    sma60_up=int(sum(closes[-60:]) > sum(closes[-65:-5])),
                    deduction_box_distance=100*(close/max(closes[-20:-10])-1))
                for code in d01.ASSETS[1:]:
                    features["asset_" + code[:6]] = int(asset == code or
                        (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == d01.ASSETS[1]))
            if ready and only and not censored:
                features["added"] = math.log1p(age)
            y, label_end, label_reason = (shared._label(label_rows, index[day], target=contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            reason = ("continuous252_or_economic_price_missing" if not ready else
                      "state_unknown" if only is None else
                      "outside_current_E_only" if not only else
                      "left_censored_wait" if censored else None)
            eligible = bool(reason is None and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                "stratum": f"{asset}|{day[:4]}", "features": features, "eligible": eligible,
                "E": e, "S": s, "E_only": only, "wait_age": age if only else None,
                "left_censored": censored if only else None, "ready_252": ready,
                "continuous_real_ohlc": len(closes), "feature_reason": reason,
                "label_reason": reason or label_reason, "target_label_reason": label_reason,
                "y": y, "label_end": label_end, "tested_condition": only,
                "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["E_only"] += int(only is True)
            counts["eligible"] += int(eligible)
        per_asset[asset] = dict(counts)
    keys = ("observations", "ready_252", "E_only", "eligible", "price_reset_rows",
            "waiting_segments", "left_censored_segments",
            "waiting_segments_formal", "left_censored_segments_formal")
    coverage = {key: sum(x.get(key, 0) for x in per_asset.values()) for key in keys}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["EMA uses first-qualified-close seed for D01 comparability; production SMA seed differs."]}


def _phase(day):
    return "early_2022_2024" if day <= "2024-12-31" else "eval_2025" if day <= "2025-12-31" else "eval_2026H1"


def _rank(rows, columns):
    if not rows:
        return {"rows": 0, "rank": 0, "nonzero_columns": [], "zero_variance": list(columns)}
    x = np.asarray([[r["features"][c] for c in columns] for r in rows], dtype=float)
    assets = [r["asset"] for r in rows]
    w = np.asarray([1 / assets.count(a) for a in assets])
    w /= w.sum()
    mean = w @ x
    std = np.sqrt(w @ ((x - mean) ** 2))
    zero = std < 1e-12
    z = (x - mean) / np.where(zero, 1, std)
    z[:, zero] = 0
    singular = np.linalg.svd(np.sqrt(w)[:, None] * z, compute_uv=False)
    rank = int(sum(singular > (singular[0] * 1e-12 if len(singular) else 0)))
    return {"rows": len(rows), "rank": rank,
            "nonzero_columns": [c for c, q in zip(columns, zero) if not q],
            "zero_variance": [c for c, q in zip(columns, zero) if q],
            "singular_values": singular.tolist()}


def build_qualification(payload: dict, contract: dict, root) -> dict:
    """Recheck source, then count support using current/past X and calendar dates only."""
    _, _, _, source_contract = _validate(payload, contract)
    source = d01.qualify_deduction_panel(payload, source_contract, root)
    prepared = prepare_sequence_observations(payload, contract, compute_labels=False)
    observations = prepared["observations"]
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    features = []
    for obs in observations:
        day = obs["date"]
        row = {**obs, "phase": _phase(day)}
        for horizon in (5, 10, 20, 60, 120):
            j = index[day] + horizon + 1
            end = calendar[j] if j < len(calendar) else None
            row[f"h{horizon}_end"] = end
            row[f"h{horizon}_mature"] = bool(end and _phase(end) == _phase(day))
        features.append(row)
    support = {}
    for phase in ("early_2022_2024", "eval_2025", "eval_2026H1"):
        rr = [r for r in features if r["phase"] == phase]
        support[phase] = {"observations": len(rr), "ready_252": sum(r["ready_252"] for r in rr),
            "E_only": sum(r["E_only"] is True for r in rr),
            "eligible": sum(r["eligible"] for r in rr),
            "mature20_eligible": sum(r["eligible"] and r["h20_mature"] for r in rr),
            "age1": sum(r["eligible"] and r["wait_age"] == 1 for r in rr),
            "age2plus": sum(r["eligible"] and r["wait_age"] >= 2 for r in rr),
            "left_censored": sum(r["left_censored"] is True for r in rr)}
    per_asset = {asset: {"observations": sum(r["asset"] == asset for r in features),
        "eligible": sum(r["asset"] == asset and r["eligible"] for r in features),
        "age1": sum(r["asset"] == asset and r["eligible"] and r["wait_age"] == 1 for r in features),
        "age2plus": sum(r["asset"] == asset and r["eligible"] and r["wait_age"] >= 2 for r in features)}
        for asset in contract["universe"]["assets"]}
    folds, ranks = [], []
    for fold in contract["split"]["folds"]:
        train = [r for r in features if r["eligible"] and r["h20_end"] and
                 r["date"] <= fold["train_end"] and r["h20_end"] < fold["eval_start"]]
        evaluation = [r for r in features if r["eligible"] and
                      fold["eval_start"] <= r["date"] <= fold["eval_end"] and
                      r["h20_end"] and r["h20_end"] <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(evaluation),
            "train_age1": sum(r["wait_age"] == 1 for r in train),
            "train_age2plus": sum(r["wait_age"] >= 2 for r in train),
            "evaluation_age1": sum(r["wait_age"] == 1 for r in evaluation),
            "evaluation_age2plus": sum(r["wait_age"] >= 2 for r in evaluation)})
        for model, cols in (("B1", BASELINE_FEATURES), ("B2", (*BASELINE_FEATURES, "added"))):
            ranks.append({"fold": fold, "model": model, **_rank(train, cols),
                          "evaluation_rows": len(evaluation)})
    qualification = {"data_sha256": contract["data"]["sha256"],
        "source_manifest_path": contract["data"]["qualification"]["manifest_path"],
        "outcome_values_used_for_design": False,
        "counts": {"assets": len(contract["universe"]["assets"]),
                   "observations": len(features), "dates": len({r["date"] for r in features}),
                   "episodes": None,
                   "continuous_waiting_segments": prepared["coverage"]["waiting_segments_formal"],
                   "prehistory_and_formal_waiting_segments": prepared["coverage"]["waiting_segments"]},
        "scientific_support": {"periods": support, "per_asset": per_asset, "folds": folds,
                               "model_feature_count": len(BASELINE_FEATURES) + 1},
        "source_quality": source["quality"], "source_warnings": source["warnings"],
        "coverage": prepared["coverage"]}
    return {"observations": features, "qualification": qualification,
            "input_rank": {"outcome_values_used": False, "fold_models": ranks}}
