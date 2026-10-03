"""Research-only interaction of an existing simple top and today's dual break.

Both component identities come from their frozen research adapters.  This
module neither changes those identities nor issues a trading instruction.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import workflow_inputs as shared
from .key_fluctuation_information import (
    DEFINITION_REF as K_REF, prepare_key_observations,
)
from .top_invalidation_information import (
    DEFINITION_REF as T_REF, prepare_invalidation_observations,
)
from .top_structure_information import ASSETS, WARMUP, qualify_top_panel

DEFINITION_REF = "research.interaction.prior_top_dual_break20@1.0.0"
BASELINE_FEATURES = (
    "r1", "ret3", "ret20", "vol20", "ema20_distance",
    "prior_top_active", "dual_break", "asset_510050", "asset_510500",
    "asset_588000",
)
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def _phase(day: str) -> str:
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _component_contract(contract: dict, *, key: bool) -> dict:
    copied = deepcopy(contract)
    copied["feature"] = {
        "kind": "key_fluctuation_information" if key else "simple_top_invalidation_information",
        "definition_ref": K_REF if key else T_REF,
        "lookback": 60, "warmup": WARMUP, "missing_policy": "segmented",
    }
    copied["target"] = ({"kind": "mae", "start_offset": 1,
                         "end_offset": 21, "entry_field": "close", "path_field": "close",
                         "price_measure": "economic_price"} if key else
                        {"kind": "forward_return", "start_offset": 1,
                         "end_offset": 21, "entry_field": "close",
                         "price_measure": "economic_price"})
    return copied


def _validate(payload: dict, contract: dict) -> None:
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "prior_top_dual_break_information" or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented"):
        raise ValueError("combination requires its exact segmented252 definition")
    if (target.get("kind") != "mae" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("path_field", "close") != "close" or
            target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("target must be t+1..t+21 economic close MAE")
    if payload.get("data_mode") != "synthetic":
        if (tuple(contract["universe"]["assets"]) != ASSETS or
                contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
            raise ValueError("real study requires frozen four ETF universe and period")


def prepare_combination_observations(payload: dict, contract: dict,
                                     *, compute_labels: bool = False) -> dict:
    """Keep every scheduled day; default path never requests future prices."""
    if (compute_labels and payload.get("data_mode") != "synthetic" and
            not (contract.get("permissions", {}).get("real_labels") is True and
                 contract.get("permissions", {}).get("effect_authorized") is True)):
        raise ValueError("real future labels require explicit effect authorization")
    _validate(payload, contract)
    k_rows = prepare_key_observations(payload, _component_contract(contract, key=True))["observations"]
    t_rows = prepare_invalidation_observations(payload, _component_contract(contract, key=False))["observations"]
    top_by_id = {row["id"]: row for row in t_rows}
    if len(top_by_id) != len(t_rows) or {r["id"] for r in k_rows} != set(top_by_id):
        raise ValueError("component observations do not share the same scheduled rows")
    calendar = payload["calendar"]
    index_of = {day: i for i, day in enumerate(calendar)}
    available_end = max((row["date"] for row in payload["bars"]), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    bar_by_key = {(r["asset"], r["date"]): r for r in payload["bars"]} if compute_labels else None
    by_asset = ({asset: [bar_by_key.get((asset, day),
                                      {"asset": asset, "date": day, "status": "vendor_missing"})
                        for day in calendar if day <= available_end]
                 for asset in contract["universe"]["assets"]} if compute_labels else None)
    observations = []
    per_asset: dict[str, Counter] = {asset: Counter() for asset in contract["universe"]["assets"]}
    for k in k_rows:
        t = top_by_id[k["id"]]
        if k["ready_252"] != t["ready_252"]:
            raise ValueError("component warmup identities disagree")
        ready = k["ready_252"]
        # T01 marks a previous top as active_before_today even when today's
        # high breaks it.  The interaction needs the still-active state after
        # today's invalidation check, before any new top may enter tomorrow.
        prior_top = bool(t["active_before_today"] and t["tested_condition"] is False)
        dual_break = bool(k["critical_down20"]) if ready else False
        state = f"{int(prior_top)}{int(dual_break)}" if ready else None
        features = {name: k["features"][name] for name in BASELINE_FEATURES[:5]}
        features["prior_top_active"] = int(prior_top) if ready else None
        features["dual_break"] = int(dual_break) if ready else None
        for name in BASELINE_FEATURES[7:]:
            features[name] = k["features"][name]
        features["added"] = int(prior_top and dual_break) if ready else None
        reason = ("continuous252_or_economic_price_missing" if not ready else
                  "sma60_not_rising" if k["sma60_up"] is not True else None)
        y, label_end, label_reason = (shared._label(by_asset[k["asset"]], index_of[k["date"]],
                                                     target=contract["target"])
                                      if compute_labels else (None, None, "not_computed"))
        eligible = reason is None and (y is not None if compute_labels else True)
        row = {"id": k["id"], "asset": k["asset"], "date": k["date"],
               "stratum": k["stratum"], "features": features, "eligible": eligible,
               "y": y, "label_end": label_end, "target_label_reason": label_reason,
               "label_reason": reason or label_reason, "feature_reason": reason,
               "tested_condition": (prior_top and dual_break) if ready else None,
               "state": state, "prior_top_active": prior_top if ready else None,
               "dual_break": dual_break if ready else None,
               "top_active_at_previous_close": t["active_before_today"],
               "top_invalidated_today": t["tested_condition"] is True,
               "top_reference_price": t["reference_price"],
               "top_confirmed_date": t["confirmed_date"],
               "sma60_up": k["sma60_up"],
               "continuous_real_ohlc": k["continuous_real_ohlc"],
               "ready_252": ready, "definition_ref": DEFINITION_REF}
        observations.append(row)
        counter = per_asset[k["asset"]]
        counter["scheduled"] += 1
        counter["ready_252"] += int(ready)
        counter["trend_up"] += int(k["sma60_up"] is True)
        counter["eligible"] += int(eligible)
        if eligible:
            counter["state_" + state] += 1
        else:
                counter["reason:" + (reason or "target_unavailable")] += 1
    keys = ("scheduled", "ready_252", "trend_up", "eligible", "state_00", "state_10",
            "state_01", "state_11", "reason:continuous252_or_economic_price_missing",
            "reason:sma60_not_rising")
    coverage = {name: sum(v[name] for v in per_asset.values()) for name in keys}
    coverage["per_asset"] = {asset: {name: counter[name] for name in keys}
                             for asset, counter in per_asset.items()}
    coverage["definition_ref"] = DEFINITION_REF
    return {"observations": observations, "coverage": coverage,
            "warnings": ["T and K are retained separately; their product is only a risk-information expression.",
                         "A prior top broken by today's high is not active today; today's new top enters no earlier than tomorrow."]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Recheck source provenance and count calendar maturity without labels."""
    if contract.get("permissions", {}).get("real_labels") is True or contract.get("permissions", {}).get("effect_authorized") is True:
        raise ValueError("qualification requires real labels and effects disabled")
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_combination_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]
    calendar = payload["calendar"]
    index = {day: i for i, day in enumerate(calendar)}
    def end(row):
        j = index[row["date"]] + 21
        return calendar[j] if j < len(calendar) else None
    def counts(group):
        state_counts = Counter(r["state"] for r in group if r["eligible"])
        return {s: state_counts[s] for s in ("00", "10", "01", "11")}
    phases = {}
    for phase in PHASES:
        section = [r for r in rows if _phase(r["date"]) == phase]
        eligible = [r for r in section if r["eligible"]]
        mature = [r for r in eligible if end(r) and _phase(end(r)) == phase]
        phases[phase] = {"scheduled": len(section), "ready_252": sum(r["ready_252"] for r in section),
                         "eligible": len(eligible), "states": counts(eligible),
                         "mature_20_same_phase": len(mature), "mature_states": counts(mature),
                         "per_asset": {asset: {"eligible": len([r for r in eligible if r["asset"] == asset]),
                                                "states": counts([r for r in eligible if r["asset"] == asset]),
                                                "mature_20_same_phase": len([r for r in mature if r["asset"] == asset]),
                                                "mature_states": counts([r for r in mature if r["asset"] == asset])}
                                       for asset in contract["universe"]["assets"]}}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in rows if r["eligible"] and r["date"] <= fold["train_end"] and
                 end(r) and end(r) < fold["eval_start"]]
        evaluation = [r for r in rows if r["eligible"] and
                      fold["eval_start"] <= r["date"] <= fold["eval_end"] and
                      end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "train_states": counts(train),
                      "train_has_all_four_states": all(counts(train).values()),
                      "evaluation": len(evaluation), "evaluation_states": counts(evaluation)})
    # An episode is a maximal consecutive-calendar run of eligible 11 days.
    episodes = []
    for asset in contract["universe"]["assets"]:
        ordered = sorted((r for r in rows if r["asset"] == asset), key=lambda r: index[r["date"]])
        active = None
        for row in ordered:
            if row["eligible"] and row["state"] == "11":
                if active is None:
                    active = {"asset": asset, "start": row["date"], "end": row["date"], "days": 1}
                else:
                    active["end"] = row["date"]
                    active["days"] += 1
            elif active is not None:
                episodes.append(active)
                active = None
        if active is not None:
            episodes.append(active)
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "counts": {"assets": len(contract["universe"]["assets"]),
                       "observations": len(rows), "dates": len({r["date"] for r in rows}),
                       "episodes": len(episodes)},
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "scientific_support": {"phases": phases, "folds": folds,
                                   "episodes": episodes,
                                   "episode_count_by_asset": dict(Counter(e["asset"] for e in episodes)),
                                   "model_feature_count": len(BASELINE_FEATURES) + 1,
                                   "note": "Maturity is calendar-position only; no later OHLC or target values read."}}
