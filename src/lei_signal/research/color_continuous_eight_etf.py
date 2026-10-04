"""Eight-ETF extension of the registered continuous color description.

Only the asset panel and identity controls differ from the frozen four-ETF
adapter. This module neither changes color semantics nor certifies live use.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from . import workflow_inputs as shared
from .color_continuous_information import continuous_rows
from .color_continuous_workflow import ADDED_FEATURES

KIND = "color_continuous_eight_etf"
DEFINITION_REF = "research.trend.color_continuous20_bundle@1.1.0"
ASSETS = ("510300.SS", "510050.SS", "510500.SS", "588000.SS",
          "512170.SS", "512400.SS", "512480.SS", "512800.SS")
BASELINE_FEATURES = (
    "ret20", "ret60", "vol20", "color20_green", "color20_black",
    "color60_green", "color60_black", "bull_group", "ema20_up_share20",
    "asset_510050", "asset_510500", "asset_588000", "asset_512170",
    "asset_512400", "asset_512480", "asset_512800",
)


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != KIND or feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 20 or feature.get("warmup") != 252 or
            feature.get("missing_policy") != "segmented" or
            contract["question"].get("sampling") != "daily"):
        raise ValueError("eight-ETF colors require daily continuous20/segmented252")
    if (target.get("kind") not in {"forward_return", "mae"} or
            target.get("start_offset") != 1 or target.get("end_offset") != 21 or
            target.get("entry_field") != "close" or
            target.get("path_field", "close") != "close" or
            target.get("price_measure") != "economic_price"):
        raise ValueError("eight-ETF target requires t+1..t+21 economic closes")
    assets = contract["universe"]["assets"]
    if payload.get("data_mode") != "synthetic":
        if (assets != list(ASSETS) or payload.get("price_series") != "economic_price" or
                contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
            raise ValueError("eight-ETF panel requires frozen identities, period and economic prices")
    elif assets != ["synthetic-A", "synthetic-B"]:
        raise ValueError("eight-ETF synthetic rehearsal requires two fixed identities")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("calendar must contain sorted unique dates")
    for day in calendar:
        shared._date(day)
    by_key = {}
    for row in payload["bars"]:
        asset, day, status = row["asset"], row["date"], row["status"]
        key = asset, day
        if (asset not in assets or day not in calendar or status not in shared.STATUSES or
                key in by_key):
            raise ValueError("duplicate or out-of-scope bar/status")
        if status != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar carries OHLC")
        if status == "quoted":
            prices = [row.get(k) for k in ("open", "high", "low", "close")]
            valid = (row.get("action_known") is True and all(shared._number(v) for v in prices)
                     and row["low"] <= min(row["open"], row["close"]) + 1e-12
                     and max(row["open"], row["close"]) <= row["high"] + 1e-12)
            if not valid:
                raise ValueError("quoted bar requires valid, action-known economic OHLC")
            if "decision_at" in row:
                at = shared._available(row["decision_at"])
                if at.date() < shared._date(day) or (at.date() == shared._date(day) and at.hour < 15):
                    raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def prepare_observations(payload, contract, *, compute_labels=False):
    calendar, assets, by_key = _validate(payload, contract)
    if compute_labels and payload.get("data_mode") != "synthetic":
        permissions = contract.get("permissions", {})
        if not (permissions.get("real_labels") is True and
                permissions.get("effect_authorized") is True and
                type(permissions.get("real_fits")) is int and permissions["real_fits"] == 4):
            raise ValueError("eight-ETF real labels require four-fit authorization")
    end = max((day for _, day in by_key), default=calendar[0])
    if "decision_at" in payload:
        from datetime import time
        decision = shared._available(payload["decision_at"])
        day = decision.date().isoformat()
        if decision.time() < time(15):
            day = next((d for d in reversed(calendar) if d < day), "0000-00-00")
        end = min(end, day)
    # Economic scaling can put a close ~1e-16 above a high. The common color
    # builder's strict OHLC guard would treat that as a missing quote. Repair
    # only this in-memory representation after tolerance validation; the bound
    # input, close series and original source files are unchanged.
    normalized = []
    for bar in payload["bars"]:
        if bar["date"] > end:
            continue
        if bar["status"] == "quoted":
            normalized.append({**bar, "high": max(bar["high"], bar["open"], bar["close"]),
                               "low": min(bar["low"], bar["open"], bar["close"])})
        else:
            normalized.append(bar)
    past = {**payload, "calendar": [d for d in calendar if d <= end], "bars": normalized}
    histories = continuous_rows(past)
    selected = shared._selected(calendar, end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index = {d: i for i, d in enumerate(calendar)}
    price_rows = {a: [by_key.get((a, d), {"asset": a, "date": d, "status": "vendor_missing"})
                      for d in calendar if d <= end] for a in assets}
    observations = []
    for row in histories:
        day, asset = row["date"], row["asset"]
        if day not in selected or not first <= day <= last:
            continue
        reason = ("continuous20_unknown" if any(row.get(k) is None for k in
                  ADDED_FEATURES + ("ema20_up_share20",)) else None)
        features = {k: row.get(k) for k in BASELINE_FEATURES + ADDED_FEATURES}
        for horizon in (20, 60):
            for color in ("green", "black"):
                features[f"color{horizon}_{color}"] = (int(row[f"color{horizon}"] == color)
                    if row["ready_252"] else None)
        features["bull_group"] = int(row["bull_group"]) if row["ready_252"] else None
        for code in ASSETS[1:]:
            features["asset_" + code[:6]] = int(asset == code or
                (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
        y, label_end, label_reason = (shared._label(price_rows[asset], index[day], contract["target"])
            if compute_labels and reason is None else (None, None, reason or "not_computed"))
        observations.append({**row, "features": features, "stratum": f"{asset}|{day[:4]}",
            "state": row["color20"], "tested_condition": None,
            "eligible": reason is None and (y is not None if compute_labels else True),
            "y": y, "label_end": label_end, "feature_reason": reason,
            "target_label_reason": label_reason, "label_reason": reason or label_reason,
            "definition_ref": DEFINITION_REF})
    counts = Counter(r["feature_reason"] or "feature_ready" for r in observations)
    return {"observations": observations,
            "coverage": {"scheduled": len(observations),
                         "eligible": sum(r["eligible"] for r in observations),
                         "reasons": dict(counts)},
            "warnings": ["Eight-ETF colors describe past states, not trade signals.",
                         "Overlapping daily outcomes and sector ETFs are dependent observations."]}


def _read_bound(root, item):
    path = Path(item["path"])
    if not path.is_absolute():
        path = Path(root) / path
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError(f"source binding changed: {item['path']}")
    if "bytes" in item and len(raw) != item["bytes"]:
        raise ValueError(f"source size changed: {item['path']}")
    return raw


def qualify_source(payload, contract, root):
    q = contract["data"].get("qualification", {})
    if q.get("adapter") != "color_eight_etf_economic/1.0":
        raise ValueError("eight-ETF panel requires its own economic source qualifier")
    manifest_path = Path(q["manifest_path"])
    if not manifest_path.is_absolute():
        manifest_path = Path(root) / manifest_path
    if "manifest_sha256" in q:
        manifest = json.loads(_read_bound(root, {"path": str(manifest_path),
                                          "sha256": q["manifest_sha256"]}))
    else:
        manifest = json.loads(manifest_path.read_text())
    if (manifest.get("schema") != "color-eight-etf-source/1.0" or
            manifest.get("scope") != "qualified_retrospective_8_etfs_only" or
            not manifest.get("files")):
        raise ValueError("eight-ETF source manifest scope/schema/bindings invalid")
    input_item = manifest["input"]
    input_bytes = _read_bound(root, input_item)
    contract_path = Path(contract["data"]["path"])
    if not contract_path.is_absolute():
        contract_path = Path(root) / contract_path
    input_path = Path(input_item["path"])
    if not input_path.is_absolute():
        input_path = Path(root) / input_path
    if (contract["data"]["sha256"] != input_item["sha256"] or
            contract_path.resolve() != input_path.resolve()):
        raise ValueError("contract input differs from source manifest")
    if json.loads(input_bytes) != payload:
        raise ValueError("loaded panel differs from bound input")
    for item in manifest["files"]:
        _read_bound(root, item)
    receipt = json.loads(_read_bound(root, manifest["owner_qualification"]))
    if (receipt.get("schema") != "price-volume-universe-qualification/1.0" or
            receipt.get("status") != "qualified_retrospective_8_etfs_only" or
            set(receipt.get("quality", {}).get("broad", {})) != set(ASSETS[:4]) or
            set(receipt.get("quality", {}).get("sector", {})) != set(ASSETS[4:]) or
            receipt.get("workflow_input", {}).get("sha256") != input_item["sha256"] or
            receipt.get("prepared_rows") != len(payload["bars"]) or
            receipt.get("calendar", {}).get("dates") != len(payload["calendar"])):
        raise ValueError("owner qualification does not establish this eight-ETF panel")
    receipt_files = {(Path(item["path"]).name, item["sha256"], item["bytes"])
                     for item in receipt.get("field_evidence", [])}
    manifest_files = {(Path(item["path"]).name, item["sha256"], item["bytes"])
                      for item in manifest["files"]}
    if receipt_files != manifest_files or len(receipt_files) != 11:
        raise ValueError("source files differ from owner field evidence")
    _validate(payload, contract)
    repairs = [max(max(row["open"], row["close"]) - row["high"],
                   row["low"] - min(row["open"], row["close"]), 0.0)
               for row in payload["bars"] if row["status"] == "quoted"]
    repair_count = sum(delta > 0 for delta in repairs)
    repair_max = max(repairs, default=0.0)
    return {"quality": {"request_satisfied": True, "assets": list(ASSETS),
                        "source_files_bound": len(manifest["files"]),
                        "owner_qualification_bound": True,
                        "roundoff_ohlc_rows": repair_count,
                        "roundoff_max_absolute": repair_max},
            "warnings": ["Source and owner qualification are hash-bound; economic prices are retrospective.",
                         f"In-memory OHLC roundoff correction: {repair_count} rows, maximum {repair_max:.17g}; closes and source files unchanged.",
                         "Historical action arrival and tradable results are not certified."],
            "owner_receipt": receipt}


def build_qualification(payload, contract, root):
    source = qualify_source(payload, contract, root)
    prepared = prepare_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    ready = [r for r in rows if r["eligible"]]
    def end(row):
        j = index[row["date"]] + 21
        return calendar[j] if j < len(calendar) else None
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in ready if r["date"] <= fold["train_end"] and end(r)
                 and end(r) < fold["eval_start"]]
        evaluation = [r for r in ready if fold["eval_start"] <= r["date"] <= fold["eval_end"]
                      and end(r) and end(r) <= fold["eval_end"]]
        def count(part):
            return {"rows": len(part), "dates": len({r["date"] for r in part}),
                    "colors": dict(Counter(r["color20"] for r in part)),
                    "color_segments": len({r["color_run_id"] for r in part}),
                    "group_segments": len({r["group_run_id"] for r in part}),
                    "per_asset": {a: dict(Counter(r["color20"] for r in part if r["asset"] == a))
                                  for a in ASSETS}}
        folds.append({"fold": fold, "training": count(train), "evaluation": count(evaluation)})
    return {"data_sha256": contract["data"]["sha256"],
            "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "coverage": prepared["coverage"],
            "scientific_support": {"folds": folds, "independent_episodes": None,
                                   "reason": "color/group runs and overlapping dates are not independent"}}
