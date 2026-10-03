"""Past-only EMA persistence and adjacent black-to-green research expressions.

These are information probes, not the full LEI colour trading sequence.
"""
from __future__ import annotations

from collections import Counter
from datetime import time
from pathlib import Path
import math
import statistics

import numpy as np
import pandas as pd

from lei_signal.features.indicators import compute_features
from . import workflow_inputs as shared
from .green_black_state_information import _color
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel
from .trend_slope_change_information import _validate as validate_panel

PERSISTENCE = "ema_direction_persistence_information"
TRANSITION = "bull_green_transition_information"
REFS = {
    PERSISTENCE: "research.trend.ema_direction_persistence20@1.0.0",
    TRANSITION: "research.signal.bull_green_adjacent_black20@1.0.0",
}
BASELINE_PERSISTENCE = (
    "color20_green", "color20_black", "color60_green", "color60_black",
    "ema20_up", "ret20", "ret60", "vol20",
    "asset_510050", "asset_510500", "asset_588000",
)
BASELINE_TRANSITION = (
    "ret20", "ret60", "vol20", "asset_510050", "asset_510500", "asset_588000",
)
ADDED = {PERSISTENCE: "ema20_up_share20", TRANSITION: "adjacent_black20"}
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def _phase(day):
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    kind = feature.get("kind")
    if (kind not in REFS or feature.get("definition_ref") != REFS[kind] or
            contract["question"].get("factor_refs") != [REFS[kind]] or
            feature.get("lookback") != 20 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented" or
            contract["question"].get("sampling") != "daily"):
        raise ValueError("persistence/transition requires its exact daily segmented252 definition")
    if (target.get("kind") not in ({"forward_return", "mae"} if kind == PERSISTENCE else {"mae"}) or
            target.get("start_offset") != 1 or target.get("end_offset") != 21 or
            target.get("entry_field") != "close" or target.get("path_field", "close") != "close" or
            target.get("price_measure") != "economic_price"):
        raise ValueError("technical persistence target requires t+1..t+21 economic closes")
    # Existing source validator owns calendar, OHLC, decision time and four-ETF identity.
    source = {**contract, "feature": {**feature, "kind": "slope_change_information", "lookback": 60,
                                  "definition_ref": "research.trend.slope_change60_20@1.0.0"},
              "target": {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                         "entry_field": "close", "price_measure": "economic_price"}}
    return validate_panel(payload, source)


def _segment_features(segment):
    if not segment:
        return []
    frame = compute_features(pd.DataFrame(segment))
    closes = frame["close"].astype(float).tolist()
    ema20 = frame["ema20"].astype(float).tolist()
    result = []
    for i, close in enumerate(closes):
        if i + 1 < WARMUP:
            result.append(None)
            continue
        values = [float(frame[name].iloc[i]) for name in
                  ("sma20", "ema20", "sma60", "ema60", "close_lag20", "close_lag60")]
        if not all(math.isfinite(v) for v in values) or not all(
                math.isfinite(ema20[j]) for j in range(i - 20, i + 1)):
            result.append(None)
            continue
        sma20, e20, sma60, e60, lag20, lag60 = values
        color20, color60 = _color(close, e20, lag20), _color(close, e60, lag60)
        up_count = sum(ema20[j] > ema20[j - 1] for j in range(i - 19, i + 1))
        vol = statistics.stdev(math.log(closes[j] / closes[j - 1])
                               for j in range(i - 19, i + 1)) * math.sqrt(252) * 100
        features = {"color20_green": int(color20 == "green"),
                    "color20_black": int(color20 == "black"),
                    "color60_green": int(color60 == "green"),
                    "color60_black": int(color60 == "black"),
                    "ema20_up": int(e20 > ema20[i - 1]),
                    "ret20": 100 * (close / closes[i - 20] - 1),
                    "ret60": 100 * (close / closes[i - 60] - 1),
                    "vol20": vol,
                    "ema20_up_share20": up_count / 20,
                    "adjacent_black20": int(_color(closes[i - 1], ema20[i - 1],
                                                     closes[i - 21]) == "black")}
        result.append({"features": features if all(math.isfinite(v) for v in features.values()) else None,
                       "color20": color20, "color60": color60,
                       "bull_group": min(sma20, e20) > max(sma60, e60),
                       "prior_color20": _color(closes[i - 1], ema20[i - 1], closes[i - 21])})
    return result


def prepare_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Schedule every asset/date; feature qualification never reads future prices."""
    kind = contract["feature"]["kind"]
    if compute_labels and payload.get("data_mode") != "synthetic":
        permission = contract.get("permissions", {})
        if (permission.get("real_labels") is not True or
                permission.get("effect_authorized") is not True or
                type(permission.get("real_fits")) is not int or permission["real_fits"] != 4):
            raise ValueError("real labels require explicit effect authorization and four fits")
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((day for _, day in by_key), default=calendar[0])
    if "decision_at" in payload:
        decision = shared._available(payload["decision_at"])
        day = decision.date().isoformat()
        if decision.time() < time(15):
            day = next((d for d in reversed(calendar) if d < day), "0000-00-00")
        available_end = min(available_end, day)
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    date_index = {day: i for i, day in enumerate(calendar)}
    observations, by_asset = [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day,
                                               "status": "vendor_missing"})) for day in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        known, segment, resets = {}, [], 0

        def flush():
            for pos, ((idx, _), item) in enumerate(zip(segment,
                       _segment_features([row for _, row in segment])), 1):
                known[idx] = (pos, item)
            segment.clear()

        for i, row in enumerate(rows):
            if row["date"] > available_end:
                break
            if _known(row):
                segment.append((i, row))
            else:
                if segment:
                    flush()
                resets += 1
        if segment:
            flush()
        counts = Counter()
        for i, day in enumerate(calendar):
            if day > available_end:
                break
            if day not in selected or not first <= day <= last:
                continue
            continuous, item = known.get(i, (0, None))
            ready = item is not None and item["features"] is not None
            condition = ready and item["bull_group"] and item["color20"] == "green"
            feature_reason = ("continuous252_or_indicator_missing" if not ready else
                              "outside_bull_green" if kind == TRANSITION and not condition else None)
            values = item["features"] if ready else {}
            keys = BASELINE_PERSISTENCE if kind == PERSISTENCE else BASELINE_TRANSITION
            features = {key: values.get(key) for key in keys if not key.startswith("asset_")}
            features[ADDED[kind]] = values.get(ADDED[kind]) if feature_reason is None else None
            for code in ASSETS[1:]:
                features["asset_" + code[:6]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, end, target_reason = (shared._label(label_rows, date_index[day], contract["target"])
                                     if compute_labels and feature_reason is None else
                                     (None, None, feature_reason or "not_computed"))
            eligible = feature_reason is None and (y is not None if compute_labels else True)
            observation = {"id": f"{asset}|{day}", "asset": asset, "date": day,
                           "stratum": f"{asset}|{day[:4]}", "features": features,
                           "color20": item["color20"] if ready else None,
                           "color60": item["color60"] if ready else None,
                           "prior_color20": item["prior_color20"] if ready else None,
                           "bull_group": item["bull_group"] if ready else None,
                           "state": item["color20"] if ready else None,
                           "tested_condition": bool(values.get(ADDED[kind])) if feature_reason is None else None,
                           "eligible": bool(eligible), "y": y, "label_end": end,
                           "label_reason": feature_reason or target_reason,
                           "target_label_reason": target_reason, "feature_reason": feature_reason,
                           "ready_252": ready, "continuous_real_ohlc": continuous,
                           "definition_ref": REFS[kind]}
            observations.append(observation)
            counts.update(observations=1, ready_252=int(ready), eligible=int(eligible),
                          bull_green=int(bool(condition)))
            counts[feature_reason or "feature_ready"] += 1
        counts["price_reset_rows"] = resets
        by_asset[asset] = dict(counts)
    names = ("observations", "ready_252", "eligible", "bull_green", "price_reset_rows",
             "continuous252_or_indicator_missing", "outside_bull_green", "feature_ready")
    coverage = {key: sum(v.get(key, 0) for v in by_asset.values()) for key in names}
    coverage.update(per_asset=by_asset, definition_ref=REFS[kind])
    return {"observations": observations, "coverage": coverage,
            "warnings": ["方向比例与相邻变色仅为已知价格表达；排列/变色代理不构成完整交易规则。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Check sources and support from past features and calendar maturity only."""
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_observations(payload, contract, compute_labels=False)
    rows, dates = prepared["observations"], payload["calendar"]
    index = {day: i for i, day in enumerate(dates)}
    def end(row):
        j = index[row["date"]] + 21
        return dates[j] if j < len(dates) else None
    eligible = [r for r in rows if r["eligible"]]
    kind = contract["feature"]["kind"]
    keys = BASELINE_PERSISTENCE if kind == PERSISTENCE else BASELINE_TRANSITION
    added = ADDED[kind]
    def rank(subset, fields):
        return (int(np.linalg.matrix_rank(np.asarray(
            [[1, *(r["features"][name] for name in fields)] for r in subset], dtype=float)))
            if subset else 0)
    phases = {}
    for phase in PHASES:
        subset = [r for r in rows if _phase(r["date"]) == phase]
        qualified = [r for r in subset if r["eligible"]]
        phases[phase] = {"scheduled": len(subset), "ready_252": sum(r["ready_252"] for r in subset),
                         "eligible": len(qualified),
                         "calendar_mature_same_phase": sum(bool(end(r) and _phase(end(r)) == phase)
                                                            for r in qualified),
                         "added_0": sum(r["features"][added] == 0 for r in qualified),
                         "added_1": sum(r["features"][added] == 1 for r in qualified)}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in eligible if r["date"] <= fold["train_end"] and
                 end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in eligible if fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "train_dates": len({r["date"] for r in train}),
                      "evaluation_dates": len({r["date"] for r in ev}),
                      "train_rank_B1": rank(train, keys), "train_rank_B2": rank(train, (*keys, added)),
                      "train_added_0": sum(r["features"][added] == 0 for r in train),
                      "train_added_1": sum(r["features"][added] == 1 for r in train),
                      "eval_added_0": sum(r["features"][added] == 0 for r in ev),
                      "eval_added_1": sum(r["features"][added] == 1 for r in ev)})
    distribution = dict(sorted(Counter(r["features"][added] for r in eligible).items()))
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]),
                       "observations": len(rows), "dates": len({r["date"] for r in rows}),
                       "episodes": None},
            "scientific_support": {"phases": phases, "folds": folds,
                                   "feature_rank": {"B1": rank(eligible, keys),
                                                    "B2": rank(eligible, (*keys, added))},
                                   "model_feature_count": len(keys) + 1,
                                   "added_distribution": distribution,
                                   "unknown_reasons": dict(Counter(r["feature_reason"] for r in rows
                                                                   if r["feature_reason"])),
                                   "note": "Maturity uses dates only; no future result values read."}}
