"""Fixed 20-session signed-volume direction excess, for research only."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import math

import pandas as pd

from lei_signal.research.factor_lab.benchmarks import local_features
from . import workflow_inputs as shared
from .risk_shape_information import baseline_values
from .top_structure_information import ASSETS, _known, qualify_top_panel

KIND = "volume_direction_information"
ANCHOR = ASSETS[0]
REFS = {"direction_excess20": "research.volume.direction_excess20@1.0.0"}
BASELINE_FEATURES = ("S", "E", "return1", "return20", "return60", "volatility5",
    "volatility20", "volatility60", "market_return20", "market_volatility20", "beta60",
    "relative_return20", "negative_fraction60", "downside_rms60", "return_autocorr1_60",
    "current_negative_run", "asset_510500", "asset_588000", "direction20")
SOLO_FEATURES = ("asset_510500", "asset_588000", "direction20")
FOLDS = [
    {"train_end": "2024-12-31", "eval_start": "2025-01-02", "eval_end": "2025-12-31"},
    {"train_end": "2025-12-31", "eval_start": "2026-01-05", "eval_end": "2026-06-30"},
]


def candidate_values(closes, volumes):
    """Twenty aligned price intervals and current-session nominal volumes.

    There are exactly 21 economic closes and 20 paired, positive volumes.
    The first volume weights the change from closes[0] to closes[1].
    """
    empty = {"direction_excess20": None, "direction20": None}
    if len(closes) != 21 or len(volumes) != 20:
        return empty
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
           not math.isfinite(x) or x <= 0 for x in (*closes, *volumes)):
        return empty
    signs = [int(b > a) - int(b < a) for a, b in zip(closes[:-1], closes[1:])]
    direction = math.fsum(signs) / 20
    total_volume = math.fsum(volumes)
    # Ratios preserve the result if every day's volume unit is multiplied alike.
    weighted = math.fsum(s * (v / total_volume) for s, v in zip(signs, volumes))
    return {"direction_excess20": weighted - direction, "direction20": direction}


def _known_volume(row):
    v = row.get("volume")
    return (row.get("volume_source_known") is True and isinstance(v, (int, float))
            and not isinstance(v, bool) and math.isfinite(v) and v > 0)


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != KIND or feature.get("definition_ref") != REFS["direction_excess20"] or
        feature.get("candidate") != "direction_excess20" or feature.get("lookback") != 20 or
        feature.get("warmup") != 252 or feature.get("missing_policy") != "segmented" or
        feature.get("comparison_mode") not in {"main", "solo"} or
        feature.get("anchor_asset") != contract["universe"]["assets"][0]):
        raise ValueError("volume direction requires exact fixed20, segmented252 card")
    if (target.get("kind") != "mae" or target.get("start_offset") != 1 or
        target.get("end_offset") != 21 or target.get("entry_field") != "close" or
        target.get("path_field") != "close" or target.get("unit") != "percentage_point" or
        target.get("price_measure") != "economic_price"):
        raise ValueError("volume direction freezes t+1..t+21 closing MAE")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("daily sampling required")
    assets = contract["universe"]["assets"]
    if payload.get("data_mode") != "synthetic" and (assets != list(ASSETS) or
        payload.get("price_series") != "economic_price" or
        contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
        raise ValueError("real source requires frozen four ETFs, period and economic prices")
    if not isinstance(assets, list) or len(assets) < 2 or len(assets) != len(set(assets)):
        raise ValueError("unique ordered assets required")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("ordered unique calendar required")
    for day in calendar:
        shared._date(day)
    by_key = {}
    for row in payload["bars"]:
        key = (row["asset"], row["date"])
        if key in by_key or key[0] not in assets or key[1] not in calendar or row.get("status") not in shared.STATUSES:
            raise ValueError("duplicate, unknown or out-of-scope quote")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close", "volume")):
            raise ValueError("nonquote has price or volume")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid price")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close observed before session end")
        by_key[key] = row
    return assets, calendar, by_key


def prepare_volume_direction_observations(payload, contract, *, compute_labels=False):
    if compute_labels and payload.get("data_mode") != "synthetic" and not (
        contract.get("permissions", {}).get("real_labels") is True and
        contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real future labels require explicit effect authorization")
    assets, calendar, by_key = _validate(payload, contract)
    anchor = assets[0]
    end = max((date for _, date in by_key), default=calendar[0])
    if "decision_at" in payload:
        end = min(end, shared._available(payload["decision_at"]).date().isoformat())
    selected = shared._selected(calendar, end, contract["question"], payload)
    first, last = contract["question"]["period"]
    rows_by_asset = {asset: [dict(by_key.get((asset, d), {"asset": asset, "date": d,
        "status": "vendor_missing"})) for d in calendar] for asset in assets}
    label_rows = {asset: [r for r in rows if r["date"] <= end] for asset, rows in rows_by_asset.items()} if compute_labels else None
    observations = []; counts = Counter(); per_asset = {}
    for asset in assets:
        asset_counts = Counter(); states = {}; segment = []
        def commit_segment():
            if segment:
                frame = local_features(pd.DataFrame({"close": [r["close"] for _, r in segment]}), 20)
                for (j, _), (_, state) in zip(segment, frame.iterrows()):
                    states[j] = state
                segment.clear()
        for j, day in enumerate(calendar):
            if day > end: break
            own = rows_by_asset[asset][j]; market = rows_by_asset[anchor][j]
            if _known(own) and _known(market): segment.append((j, own))
            else: commit_segment()
        commit_segment()
        own_close = []; anchor_close = []; paired = []; run = 0
        for i, day in enumerate(calendar):
            if day > end: break
            own = rows_by_asset[asset][i]; market = rows_by_asset[anchor][i]
            if _known(own) and _known(market):
                previous = own_close[-1] if own_close else None
                current = float(own["close"])
                own_close.append(current); anchor_close.append(float(market["close"])); run += 1
                if own.get("volume_break") is True:
                    paired = []; counts["volume_break_rows"] += 1
                if not _known_volume(own):
                    paired = []; counts["volume_missing_rows"] += 1
                elif previous is not None:
                    paired.append((previous, current, float(own["volume"])))
                    if len(paired) > 20: paired.pop(0)
            else:
                own_close = []; anchor_close = []; paired = []; run = 0
                counts["gap_rows"] += 1
            if day not in selected or not first <= day <= last: continue
            price_ready = run >= 252
            volume_ready = len(paired) >= 20
            base = baseline_values(own_close, anchor_close, states[i]) if price_ready else None
            candidate = candidate_values([paired[0][0]] + [p[1] for p in paired],
                [p[2] for p in paired]) if volume_ready else {"direction_excess20": None, "direction20": None}
            common = base is not None and all(v is not None and math.isfinite(v) for v in candidate.values())
            features = {k: (base[k] if common else None) for k in BASELINE_FEATURES
                        if not k.startswith("asset_") and k != "direction20"}
            for code in ASSETS[2:]:
                features["asset_" + code.split(".")[0]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[2]))
            features.update({name: (value if common else None) for name, value in candidate.items()})
            excluded = asset == anchor
            y, label_end, target_reason = (shared._label(label_rows[asset], i, target=contract["target"])
                if compute_labels and not excluded else (None, None, "anchor_excluded" if excluded else "not_computed"))
            reason = ("anchor_excluded" if excluded else None if common else
                "joint_252_or_feature_missing" if not price_ready or base is None else "volume_window_incomplete")
            eligible = bool(not excluded and common and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                "stratum": f"{asset}|{day[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "label_reason": reason or target_reason,
                "feature_reason": reason, "target_label_reason": target_reason,
                "tested_condition": None, "continuous_real_ohlc": run,
                "continuous_volume_pairs": len(paired), "ready_252": common,
                "definition_ref": contract["feature"]["definition_ref"]})
            counts["scheduled"] += 1; counts["anchor_excluded"] += int(excluded)
            counts["price_ready_252"] += int(price_ready and not excluded)
            counts["volume_ready_20"] += int(volume_ready and not excluded)
            counts["common_ready"] += int(common and not excluded)
            counts["eligible"] += int(eligible)
            asset_counts["scheduled"] += 1; asset_counts["anchor_excluded"] += int(excluded)
            asset_counts["price_ready_252"] += int(price_ready and not excluded)
            asset_counts["volume_ready_20"] += int(volume_ready and not excluded)
            asset_counts["common_ready"] += int(common and not excluded)
            asset_counts["eligible"] += int(eligible)
            if reason != "anchor_excluded": asset_counts[reason or "feature_ready"] += 1
        per_asset[asset] = dict(asset_counts)
    return {"observations": observations, "coverage": {**counts, "per_asset": per_asset},
        "warnings": ["成交量方向仅作回顾性研究；经济价格行动历史到达与成交量单位完整性未知。"]}


def build_qualification(payload, contract, root: Path):
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_volume_direction_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]; calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    def label_end(row):
        j = index[row["date"]] + 21
        return calendar[j] if j < len(calendar) else None
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in rows if r["eligible"] and r["date"] <= fold["train_end"] and
                 label_end(r) and label_end(r) < fold["eval_start"]]
        evaluation = [r for r in rows if r["eligible"] and fold["eval_start"] <= r["date"] <= fold["eval_end"] and
                      label_end(r) and label_end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(evaluation),
            "train_dates": len({r["date"] for r in train}),
            "evaluation_dates": len({r["date"] for r in evaluation})})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
        "source_quality": source["quality"], "source_warnings": source["warnings"],
        "coverage": prepared["coverage"], "counts": {"assets": len(contract["universe"]["assets"]),
            "observations": len(rows), "dates": len({r["date"] for r in rows}), "episodes": None},
        "scientific_support": {"folds": folds, "model_feature_count":
            len(BASELINE_FEATURES if contract["feature"]["comparison_mode"] == "main" else SOLO_FEATURES) + 1,
            "unknown_reasons": dict(Counter(r["feature_reason"] for r in rows if r["feature_reason"])),
            "note": "Only current features and calendar maturity; future price outcomes unread."}}
