"""Classic simple-return volatility, research-only risk information.

Exact classic S/E and simple-return definitions; no annualization or trade rule.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import math

import pandas as pd

from lei_signal.research.factor_lab.benchmarks import local_features
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel

KIND = "classic_volatility_risk_information"
DEFINITION_REF = "etf.reference.volatility20@1.0.0"
BASELINE_FEATURES = ("S", "E", "return20", "asset_510050", "asset_510500", "asset_588000")
ADDED_FEATURES = ("volatility20",)
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def _phase(day):
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != KIND or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 20 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented"):
        raise ValueError("classic volatility requires its exact segmented252 definition")
    if (target.get("kind") != "forward_volatility" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("path_field", "close") != "close" or
            target.get("unit") != "percentage_point" or
            type(target.get("ddof", 1)) is not int or target.get("ddof", 1) != 1 or
            target.get("annualized", False) is not False or
            target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("classic risk target is t+1..t+21 economic close simple-return std in percentage points")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("daily sampling required")
    if payload.get("data_mode") != "synthetic":
        if (payload.get("price_series") != "economic_price" or
                tuple(contract["universe"]["assets"]) != ASSETS or
                contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
            raise ValueError("real panel requires frozen four ETFs, economic price and period")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("ordered unique calendar required")
    for day in calendar:
        shared._date(day)
    assets = contract["universe"]["assets"]
    if not isinstance(assets, list) or not assets or len(assets) != len(set(assets)):
        raise ValueError("ordered unique assets required")
    by_key = {}
    for row in payload["bars"]:
        key = (row["asset"], row["date"])
        if key in by_key or row["asset"] not in assets or row["date"] not in calendar:
            raise ValueError("duplicate or out-of-scope bar")
        if row["status"] not in shared.STATUSES:
            raise ValueError("unknown quote status")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar has price")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted price")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def _segment_features(segment):
    """Reuse classic seeded-EMA, strict SMA state and simple returns exactly."""
    if not segment:
        return []
    frame = local_features(pd.DataFrame({"close": [r["close"] for r in segment]}), 20)
    result = []
    for i, row in frame.iterrows():
        if i + 1 < WARMUP:
            result.append(None)
        else:
            result.append({"S": int(row["S"]), "E": int(row["E"]),
                           "return20": 100 * float(row["hist_return"]),
                           "volatility20": 100 * float(row["volatility"])})
    return result


def prepare_risk_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Return all scheduled observations; default never calls the label reader."""
    if (compute_labels and payload.get("data_mode") != "synthetic" and not
            (contract.get("permissions", {}).get("real_labels") is True and
             contract.get("permissions", {}).get("effect_authorized") is True)):
        raise ValueError("real future labels require explicit effect authorization")
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
        # Recompute each contiguous block independently. A missing or action-unknown
        # date cannot borrow pre-gap history for any of the 252 warmup bars.
        known_feature = {}
        segment = []
        resets = 0
        for i, row in enumerate(rows):
            if row["date"] > available_end:
                break
            if _known(row):
                segment.append((i, row))
            else:
                if segment:
                    values = _segment_features([r for _, r in segment])
                    for pos, ((j, _), item) in enumerate(zip(segment, values), 1):
                        known_feature[j] = (pos, item)
                    segment = []
                resets += 1
        if segment:
            values = _segment_features([r for _, r in segment])
            for pos, ((j, _), item) in enumerate(zip(segment, values), 1):
                known_feature[j] = (pos, item)
        counts = Counter()
        for i, day in enumerate(calendar):
            if day > available_end:
                break
            if day not in selected or not first <= day <= last:
                continue
            continuous, item = known_feature.get(i, (0, None))
            ready = item is not None and all(item[k] is not None and math.isfinite(item[k])
                                             for k in ("S", "E", "return20", "volatility20"))
            features = {key: item[key] if ready else None for key in ("S", "E", "return20")}
            features["volatility20"] = item["volatility20"] if ready else None
            for code in ASSETS[1:]:
                features["asset_" + code.split(".")[0]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, label_end, target_reason = (shared._label(label_rows, index_of[day], target=contract["target"])
                                           if compute_labels else (None, None, "not_computed"))
            reason = None if ready else "continuous252_or_indicator_missing"
            eligible = bool(ready and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                                 "stratum": f"{asset}|{day[:4]}", "features": features,
                                 "eligible": eligible, "y": y, "label_end": label_end,
                                 "label_reason": reason or target_reason,
                                 "target_label_reason": target_reason, "feature_reason": reason,
                                 "tested_condition": None,
                                 "continuous_real_ohlc": continuous, "ready_252": ready,
                                 "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["eligible"] += int(eligible)
            counts[reason or "feature_ready"] += 1
        counts["price_reset_rows"] = resets
        per_asset[asset] = dict(counts)
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in
                ("observations", "ready_252", "eligible", "price_reset_rows",
                 "continuous252_or_indicator_missing", "feature_ready")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["过去20日波动只用于研究未来波动；未授权改变交易规则，行动资料历史到达时间仍未知。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Source qualification, full denominators and calendar-only fold support."""
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_risk_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]
    dates = payload["calendar"]
    index = {d: i for i, d in enumerate(dates)}
    def end(row):
        j = index[row["date"]] + 21
        return dates[j] if j < len(dates) else None
    by_phase = {}
    for phase in PHASES:
        subset = [r for r in rows if _phase(r["date"]) == phase]
        by_phase[phase] = {"scheduled": len(subset), "ready_252": sum(r["ready_252"] for r in subset),
                           "feature_unknown": sum(not r["ready_252"] for r in subset),
                           "calendar_mature_same_phase": sum(bool(r["ready_252"] and end(r) and
                                                              _phase(end(r)) == phase) for r in subset)}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in rows if r["ready_252"] and r["date"] <= fold["train_end"] and
                 end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in rows if r["ready_252"] and fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "train_dates": len({r["date"] for r in train}),
                      "evaluation_dates": len({r["date"] for r in ev})})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "scientific_support": {"phases": by_phase, "folds": folds,
                                   "model_feature_count": len(BASELINE_FEATURES) + 1,
                                   "unknown_reasons": dict(Counter(r["feature_reason"] for r in rows if r["feature_reason"])),
                                   "note": "Future support uses calendar dates only, not future prices."}}
