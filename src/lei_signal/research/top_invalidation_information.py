"""Research-only first invalidation of the latest simple three-bar top.

This is a narrow, prefix-causal road-sign observation. It is neither the
complete strict_structure grammar nor an exit or re-entry instruction.
"""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import statistics

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.clock_classifier import slope_series
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel

DEFINITION_REF = "research.structure.simple_top3_invalidation@1.0.0"
BASELINE_FEATURES = (
    "r1", "ret3", "ret20", "vol20", "slope60", "ema20_distance",
    "prior_reference_distance", "age_log1p", "asset_510050", "asset_510500",
    "asset_588000",
)
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def _phase(day: str) -> str:
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _validate(payload: dict, contract: dict):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "simple_top_invalidation_information" or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented"):
        raise ValueError("top invalidation requires its exact segmented252 definition")
    if (target.get("kind") != "forward_return" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("target must be t+1 to t+21 economic close return")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("daily sampling required")
    if payload.get("data_mode") != "synthetic":
        if (payload.get("price_series") != "economic_price" or
                tuple(contract["universe"]["assets"]) != ASSETS or
                contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
            raise ValueError("real panel requires four ETF economic OHLC and frozen dates")
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
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar has price")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted OHLC")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def _segment_features(segment: list[dict]) -> list[dict | None]:
    """Production seeded EMA20 and clock slope, plus past-only price context."""
    if not segment:
        return []
    frame = compute_features(pd.DataFrame(segment))
    s60, _ = slope_series(frame)
    closes = frame["close"].astype(float).tolist()
    values: list[dict | None] = []
    for i in range(len(segment)):
        if i + 1 < WARMUP:
            values.append(None)
            continue
        ema = float(frame["ema20"].iloc[i])
        log_returns = [math.log(closes[j] / closes[j - 1]) for j in range(i - 19, i + 1)]
        values.append({
            "r1": 100 * (closes[i] / closes[i - 1] - 1),
            "ret3": 100 * (closes[i] / closes[i - 3] - 1),
            "ret20": 100 * (closes[i] / closes[i - 20] - 1),
            "vol20": statistics.stdev(log_returns) * math.sqrt(252) * 100,
            "slope60": float(s60.iloc[i]) * 100,
            "ema20_distance": 100 * (closes[i] / ema - 1),
        })
    return values


def prepare_invalidation_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Retain all scheduled days; by default never access a future-price label."""
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
        features_at = {}
        segment = []
        resets = 0
        # Each contiguous run is independent, including structure state.
        def flush():
            if not segment:
                return
            computed = _segment_features([r for _, r in segment])
            active = None  # (reference_high, confirmation_segment_index, date)
            for pos, ((calendar_i, row), item) in enumerate(zip(segment, computed)):
                previous = active
                broken = bool(previous is not None and float(row["high"]) > previous[0])
                active_before = previous is not None
                if broken:
                    active = None  # permanent retirement before new close confirmation
                reference = previous[0] if previous else None
                age = pos - previous[1] if previous else None
                features_at[calendar_i] = (pos + 1, item, active_before, broken,
                                           reference, age, previous[2] if previous else None)
                if pos >= 2:
                    a, b, c = (segment[j][1] for j in (pos - 2, pos - 1, pos))
                    if (float(a["high"]) > float(b["high"]) > float(c["high"]) and
                            float(a["low"]) > float(b["low"]) > float(c["low"])):
                        active = (float(a["high"]), pos, row["date"])
        for i, row in enumerate(rows):
            if row["date"] > available_end:
                break
            if _known(row):
                segment.append((i, row))
            else:
                flush()
                segment = []
                resets += 1
        flush()
        counts = Counter()
        for i, day in enumerate(calendar):
            if day > available_end:
                break
            if day not in selected or not first <= day <= last:
                continue
            continuous, item, active_before, broken, reference, age, confirmed = features_at.get(
                i, (0, None, False, False, None, None, None))
            ready = bool(item is not None and all(math.isfinite(item[k]) for k in
                         ("r1", "ret3", "ret20", "vol20", "slope60", "ema20_distance")))
            features = {k: (item[k] if ready else None) for k in BASELINE_FEATURES[:6]}
            features["prior_reference_distance"] = (
                100 * (float(rows[i - 1]["close"]) / reference - 1)
                if ready and active_before and i > 0 and _known(rows[i - 1]) else None)
            features["age_log1p"] = math.log1p(age) if ready and active_before else None
            features["added"] = int(broken) if ready and active_before else None
            for code in ASSETS[1:]:
                features["asset_" + code.split(".")[0]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, label_end, target_reason = (shared._label(label_rows, index_of[day], target=contract["target"])
                                           if compute_labels else (None, None, "not_computed"))
            reason = ("continuous252_or_indicator_missing" if not ready else
                      "no_previous_active_top" if not active_before else None)
            eligible = bool(reason is None and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                                 "stratum": f"{asset}|{day[:4]}", "features": features,
                                 "eligible": eligible, "y": y, "label_end": label_end,
                                 "label_reason": reason or target_reason,
                                 "target_label_reason": target_reason, "feature_reason": reason,
                                 "tested_condition": broken if active_before else None,
                                 "active_before_today": active_before,
                                 "reference_price": reference, "confirmed_date": confirmed,
                                 "continuous_real_ohlc": continuous, "ready_252": ready,
                                 "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["active_before_today"] += int(active_before)
            counts["first_invalidated"] += int(broken)
            counts["eligible"] += int(eligible)
            counts[reason or "feature_ready"] += 1
        counts["price_reset_rows"] = resets
        per_asset[asset] = dict(counts)
    keys = ("observations", "ready_252", "active_before_today", "first_invalidated",
            "eligible", "price_reset_rows", "continuous252_or_indicator_missing",
            "no_previous_active_top", "feature_ready")
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in keys}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["最新最简三根顶部仅为研究代理；失效不是退出或再入场。",
                         "行动资料历史到达时间及完整性尚未认证。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Source recheck and calendar-only counts; no future price effects."""
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_invalidation_observations(payload, contract, compute_labels=False)
    observations = prepared["observations"]
    calendar = payload["calendar"]
    index = {d: i for i, d in enumerate(calendar)}
    def end(row):
        j = index[row["date"]] + 21
        return calendar[j] if j < len(calendar) else None
    phases = {}
    for phase in PHASES:
        rr = [r for r in observations if _phase(r["date"]) == phase]
        active = [r for r in rr if r["eligible"]]
        mature = [r for r in active if end(r) and _phase(end(r)) == phase]
        phases[phase] = {"scheduled": len(rr), "ready_252": sum(r["ready_252"] for r in rr),
                         "active": len(active), "first_invalidated": sum(r["tested_condition"] is True for r in active),
                         "continued": sum(r["tested_condition"] is False for r in active),
                         "calendar_mature_same_phase": len(mature),
                         "mature_first_invalidated": sum(r["tested_condition"] is True for r in mature),
                         "mature_continued": sum(r["tested_condition"] is False for r in mature)}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in observations if r["eligible"] and r["date"] <= fold["train_end"] and
                 end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in observations if r["eligible"] and
              fold["eval_start"] <= r["date"] <= fold["eval_end"] and end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train),
                      "train_true": sum(r["tested_condition"] is True for r in train),
                      "train_false": sum(r["tested_condition"] is False for r in train),
                      "evaluation": len(ev),
                      "evaluation_true": sum(r["tested_condition"] is True for r in ev),
                      "evaluation_false": sum(r["tested_condition"] is False for r in ev)})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "counts": {"assets": len(contract["universe"]["assets"]),
                       "observations": len(observations),
                       "dates": len({r["date"] for r in observations}), "episodes": None},
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "scientific_support": {"phases": phases, "folds": folds,
                                   "model_feature_count": len(BASELINE_FEATURES) + 1,
                                   "unknown_reasons": dict(Counter(r["feature_reason"] for r in observations if r["feature_reason"])),
                                   "note": "Maturity uses calendar dates only, never future prices."}}
