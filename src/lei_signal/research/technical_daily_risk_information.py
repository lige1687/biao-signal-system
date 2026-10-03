"""Research-only close-path risk uses of two existing technical expressions.

The source adapters compute X with their frozen return contracts and never read
future prices. Only this wrapper attaches the separately authorized MAE label.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import time

from . import workflow_inputs as shared


RISK_SOURCES = {
    "slope_change_risk_information": (
        "research.risk.slope_change60_20@1.0.0",
        "research.trend.slope_change60_20@1.0.0",
    ),
    "ema_only_wait_age_risk_information": (
        "research.risk.ema_only_wait_age20@1.0.0",
        "research.trend.ema_only_wait_age20@1.0.0",
    ),
}


def prepare_risk_observations(payload: dict, contract: dict) -> dict:
    """Reuse only past features, then label next-close through t+21 close."""
    kind = contract["feature"]["kind"]
    if kind not in RISK_SOURCES:
        raise ValueError("unsupported technical daily risk adapter")
    risk_ref, source_ref = RISK_SOURCES[kind]
    feature, target = contract["feature"], contract["target"]
    if (feature.get("definition_ref") != risk_ref or
            contract["question"].get("factor_refs") != [risk_ref] or
            target.get("kind") != "mae" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("path_field") != "close" or
            target.get("price_measure") != "economic_price"):
        raise ValueError("risk adapter requires exact registered definition and 21-close MAE")
    if payload.get("data_mode") != "synthetic" or contract.get("data", {}).get("mode") != "synthetic":
        permissions = contract.get("permissions", {})
        if (permissions.get("real_labels") is not True or
                permissions.get("effect_authorized") is not True or
                type(permissions.get("real_fits")) is not int or
                permissions["real_fits"] != 4):
            raise ValueError("real risk labels require explicit effect and four-fit authorization")

    source_contract = deepcopy(contract)
    source_feature = source_contract["feature"]
    source_feature["kind"] = ("slope_change_information" if kind == "slope_change_risk_information"
                              else "ema_only_wait_age_information")
    source_feature["definition_ref"] = source_ref
    source_contract["question"]["factor_refs"] = [source_ref]
    source_contract["target"] = {"kind": "forward_return", "start_offset": 1,
                                 "end_offset": 21, "entry_field": "close",
                                 "price_measure": "economic_price"}
    if kind == "slope_change_risk_information":
        from .trend_slope_change_information import prepare_slope_observations
        prepared = prepare_slope_observations(payload, source_contract, compute_labels=False)
    else:
        from .ema_only_wait_age_information import prepare_sequence_observations
        prepared = prepare_sequence_observations(payload, source_contract, compute_labels=False)

    calendar = payload["calendar"]
    index = {day: i for i, day in enumerate(calendar)}
    keyed = {(bar["asset"], bar["date"]): bar for bar in payload["bars"]}
    available_end = max((day for _, day in keyed), default=calendar[0])
    if "decision_at" in payload:
        decision = shared._available(payload["decision_at"])
        decision_day = decision.date().isoformat()
        if decision.time() < time(15):
            prior = [day for day in calendar if day < decision_day]
            decision_day = prior[-1] if prior else "0000-00-00"
        available_end = min(available_end, decision_day)
    observations = prepared["observations"]
    for asset in contract["universe"]["assets"]:
        asset_rows = [keyed.get((asset, day), {"asset": asset, "date": day,
                                            "status": "vendor_missing"}) for day in calendar
                      if day <= available_end]
        for row in observations:
            if row["asset"] != asset:
                continue
            y, end, reason = shared._label(asset_rows, index[row["date"]], target)
            row["y"], row["label_end"], row["target_label_reason"] = y, end, reason
            row["label_reason"] = row["feature_reason"] or reason
            row["eligible"] = bool(row["feature_reason"] is None and y is not None)
            row["definition_ref"] = risk_ref
    counts = Counter(row["asset"] for row in observations if row["eligible"])
    coverage = prepared["coverage"]
    coverage["eligible"] = sum(counts.values())
    coverage["definition_ref"] = risk_ref
    for asset in contract["universe"]["assets"]:
        coverage["per_asset"][asset]["eligible"] = counts[asset]
    return prepared
