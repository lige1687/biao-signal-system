"""Continuous color expressions on a common daily ETF panel.

This is a prefix-known descriptive state, not a trading waiting/reset machine.
"""
from collections import Counter
from copy import deepcopy

from . import workflow_inputs as shared
from .color_continuous_information import continuous_rows as history_rows
from .top_structure_information import ASSETS, qualify_top_panel
from .trend_slope_change_information import _validate as validate_panel

KIND = "color_continuous_workflow"
DEFINITION_REF = "research.trend.color_continuous20_bundle@1.0.0"
BASELINE_FEATURES = (
    "ret20", "ret60", "vol20", "color20_green", "color20_black",
    "color60_green", "color60_black", "bull_group", "ema20_up_share20",
    "asset_510050", "asset_510500", "asset_588000",
)
ADDED_FEATURES = ("green_share20", "switch_frequency20", "distance_to_ema20",)


def prepare_observations(payload, contract, *, compute_labels=False):
    f, t = contract["feature"], contract["target"]
    if (f.get("kind") != KIND or f.get("definition_ref") != DEFINITION_REF or
            f.get("lookback") != 20 or f.get("warmup") != 252 or
            f.get("missing_policy") != "segmented" or contract["question"]["sampling"] != "daily"):
        raise ValueError("continuous colors requires fixed daily20/252 past-only origin definition")
    if (t["kind"] not in {"forward_return", "mae"} or t["start_offset"] != 1 or
            t["end_offset"] != 21 or t["entry_field"] != "close" or
            t.get("path_field", "close") != "close" or t["price_measure"] != "economic_price"):
        raise ValueError("continuous colors target requires t+1..t+21 economic closes")
    if compute_labels and payload.get("data_mode") != "synthetic":
        p = contract.get("permissions", {})
        if not (p.get("real_labels") is True and p.get("effect_authorized") is True and
                type(p.get("real_fits")) is int and p["real_fits"] == 4):
            raise ValueError("continuous colors real labels require four-fit authorization")
    source = deepcopy(contract)
    source["feature"].update(kind="slope_change_information", lookback=60,
                             definition_ref="research.trend.slope_change60_20@1.0.0")
    source["target"] = {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                        "entry_field": "close", "price_measure": "economic_price"}
    calendar, assets, by_key = validate_panel(payload, source)
    end = max((day for _, day in by_key), default=calendar[0])
    if "decision_at" in payload:
        from datetime import time
        decision = shared._available(payload["decision_at"])
        day = decision.date().isoformat()
        if decision.time() < time(15):
            day = next((d for d in reversed(calendar) if d < day), "0000-00-00")
        end = min(end, day)
    past = {**payload, "calendar": [d for d in calendar if d <= end],
            "bars": [r for r in payload["bars"] if r["date"] <= end]}
    histories = history_rows(past)
    index = {d: i for i, d in enumerate(calendar)}
    selected = shared._selected(calendar, end, contract["question"], payload)
    first, last = contract["question"]["period"]
    price_rows = {a: [by_key.get((a, d), {"asset": a, "date": d, "status": "vendor_missing"})
                      for d in calendar if d <= end] for a in assets}
    observations = []
    for row in histories:
        day, asset = row["date"], row["asset"]
        if day not in selected or not first <= day <= last:
            continue
        reason = "continuous20_unknown" if any(row.get(k) is None for k in ADDED_FEATURES + ("ema20_up_share20",)) else None
        features = {k: row.get(k) for k in BASELINE_FEATURES + ADDED_FEATURES}
        for horizon in (20,60):
            for color in ("green","black"):
                features[f"color{horizon}_{color}"] = int(row[f"color{horizon}"] == color) if row["ready_252"] else None
        features["bull_group"] = int(row["bull_group"]) if row["ready_252"] else None
        for code in ASSETS[1:]:
            features["asset_" + code[:6]] = int(asset == code or
                (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
        y, label_end, label_reason = (shared._label(price_rows[asset], index[day], t)
            if compute_labels and reason is None else (None, None, reason or "not_computed"))
        observations.append({**row, "features": features,
            "stratum": f"{asset}|{day[:4]}", "state": row["color20"],
            "tested_condition": None,
            "eligible": reason is None and (y is not None if compute_labels else True),
            "y": y, "label_end": label_end, "feature_reason": reason,
            "target_label_reason": label_reason, "label_reason": reason or label_reason,
            "definition_ref": DEFINITION_REF})
    counts = Counter(r["feature_reason"] or "feature_ready" for r in observations)
    return {"observations": observations,
            "coverage": {"scheduled": len(observations), "eligible": sum(r["eligible"] for r in observations),
                         "reasons": dict(counts)},
            "warnings": ["Continuous representations retain all three colors; no numeric color ordering.",
                         "Color/group segments and overlapping outcomes are not independent opportunities."]}


def build_qualification(payload, contract, root):
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    ready = [r for r in rows if r["eligible"]]
    def end(r):
        j = index[r["date"]] + 21
        return calendar[j] if j < len(calendar) else None
    folds = []
    for f in contract["split"]["folds"]:
        train = [r for r in ready if r["date"] <= f["train_end"] and end(r) and end(r) < f["eval_start"]]
        ev = [r for r in ready if f["eval_start"] <= r["date"] <= f["eval_end"] and end(r) and end(r) <= f["eval_end"]]
        def count(rs):
            return {"rows": len(rs), "dates": len({r["date"] for r in rs}),
                    "colors": dict(Counter(r["color20"] for r in rs)),
                    "color_segments": len({r["color_run_id"] for r in rs}),
                    "group_segments": len({r["group_run_id"] for r in rs}),
                    "per_asset": {a: dict(Counter(r["color20"] for r in rs if r["asset"] == a)) for a in ASSETS}}
        folds.append({"fold": f, "training": count(train), "evaluation": count(ev)})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "coverage": prepared["coverage"], "scientific_support": {"folds": folds,
                "independent_episodes": None, "reason": "descriptive color/group runs are not independent market episodes"}}
