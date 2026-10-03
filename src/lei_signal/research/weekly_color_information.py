"""Previous completed ISO-week colour as a delayed, past-only research feature."""
from __future__ import annotations

from collections import Counter
from datetime import date, time
from pathlib import Path
import math

import numpy as np

from . import workflow_inputs as shared
from .technical_persistence_information import _segment_features, _phase, PHASES
from .top_structure_information import ASSETS, _known, qualify_top_panel
from .trend_slope_change_information import _validate as validate_panel
from .green_black_state_information import _color

KIND = "weekly_color_information"
DEFINITION_REF = "research.trend.completed_week_color20@1.0.0"
BASELINE_FEATURES = (
    "color20_green", "color20_black", "color60_green", "color60_black",
    "ema20_up", "ret20", "ret60", "vol20", "week_ret20", "week_ret60",
    "asset_510050", "asset_510500", "asset_588000",
)
ADDED_FEATURES = ("week20_green", "week20_black")
WEEK_WARMUP = 120


def _week(day):
    return date.fromisoformat(day).isocalendar()[:2]


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != KIND or feature.get("definition_ref") != DEFINITION_REF or
            contract["question"].get("factor_refs") != [DEFINITION_REF] or
            feature.get("lookback") != 20 or feature.get("warmup") != 252 or
            feature.get("week_warmup") != WEEK_WARMUP or
            feature.get("week_policy") != "previous_iso_week_only" or
            feature.get("bar_frequency") != "daily_quote" or
            feature.get("missing_policy") != "segmented" or
            contract["question"].get("sampling") != "daily"):
        raise ValueError("weekly colour requires previous ISO week, segmented daily252 and weekly120")
    if (target.get("kind") not in {"forward_return", "mae"} or
            target.get("start_offset") != 1 or target.get("end_offset") != 21 or
            target.get("entry_field") != "close" or target.get("path_field", "close") != "close" or
            target.get("price_measure") != "economic_price"):
        raise ValueError("weekly colour target requires t+1..t+21 economic closes")
    source = {**contract, "feature": {**feature, "kind": "slope_change_information", "lookback": 60,
                                      "definition_ref": "research.trend.slope_change60_20@1.0.0"},
              "target": {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                         "entry_field": "close", "price_measure": "economic_price"}}
    return validate_panel(payload, source)


def _weekly_history(calendar, rows, available_end):
    """Map each ISO week to the previous week's state; final open week is never consumed."""
    groups = []
    for i, day in enumerate(calendar):
        if day > available_end:
            break
        key = _week(day)
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(i)
    prior = {}
    closes, count, ema = [], 0, None
    for gi, (key, positions) in enumerate(groups):
        if gi == len(groups) - 1:  # no following ISO week proves completion
            break
        valid = all(_known(rows[i]) for i in positions)
        # The first calendar week can start after Monday because of a truncated input.
        if gi == 0 and date.fromisoformat(calendar[positions[0]]).weekday() != 0:
            valid = False
        if not valid:
            closes, count, ema = [], 0, None
            state = {"week20_state": None, "week_continuous": 0,
                     "last_completed_week_date": calendar[positions[-1]],
                     "week_ret20": None, "week_ret60": None}
        else:
            close = float(rows[positions[-1]]["close"])
            closes.append(close)
            count += 1
            if count == 20:
                ema = sum(closes[:20]) / 20
            elif count > 20:
                ema = (2 / 21) * close + (19 / 21) * ema
            color = _color(close, ema, closes[-21]) if count >= 21 else None
            state = {"week20_state": color if count >= WEEK_WARMUP else None,
                     "week_continuous": count,
                     "last_completed_week_date": calendar[positions[-1]],
                     "week_ret20": 100 * (close / closes[-21] - 1) if count >= 21 else None,
                     "week_ret60": 100 * (close / closes[-61] - 1) if count >= 61 else None}
        prior[groups[gi + 1][0]] = state
    return prior


def prepare_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    if compute_labels and payload.get("data_mode") != "synthetic":
        permission = contract.get("permissions", {})
        if not (permission.get("real_labels") is True and permission.get("effect_authorized") is True and
                type(permission.get("real_fits")) is int and permission["real_fits"] == 4):
            raise ValueError("real labels require effect authorization and four fits per target")
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
    index = {day: i for i, day in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day,
                                               "status": "vendor_missing"})) for day in calendar]
        weekly = _weekly_history(calendar, rows, available_end)
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        known, segment, resets = {}, [], 0
        def flush():
            for pos, ((idx, _), item) in enumerate(zip(segment,
                    _segment_features([r for _, r in segment])), 1):
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
            daily_ready = item is not None and item["features"] is not None
            w = weekly.get(_week(day), {})
            week_ready = w.get("week20_state") is not None and w.get("week_continuous", 0) >= WEEK_WARMUP
            reason = ("continuous252_or_indicator_missing" if not daily_ready else
                      "previous_week_unknown_or_warmup120" if not week_ready else None)
            values = item["features"] if daily_ready else {}
            features = {key: values.get(key) for key in BASELINE_FEATURES[:8]}
            features.update(week_ret20=w.get("week_ret20"), week_ret60=w.get("week_ret60"))
            features.update(week20_green=int(w["week20_state"] == "green") if week_ready else None,
                            week20_black=int(w["week20_state"] == "black") if week_ready else None)
            for code in ASSETS[1:]:
                features["asset_" + code[:6]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, end, target_reason = (shared._label(label_rows, index[day], contract["target"])
                                     if compute_labels and reason is None else
                                     (None, None, reason or "not_computed"))
            eligible = reason is None and (y is not None if compute_labels else True)
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                "stratum": f"{asset}|{day[:4]}", "features": features,
                "color20": item["color20"] if daily_ready else None,
                "color60": item["color60"] if daily_ready else None,
                "week20_state": w.get("week20_state"),
                "state": w.get("week20_state"),
                "last_completed_week_date": w.get("last_completed_week_date"),
                "week_continuous": w.get("week_continuous", 0),
                "week_count_unit": "observed_trading_weeks; empty calendar weeks skipped",
                "ready_252": daily_ready, "continuous_real_ohlc": continuous,
                "eligible": bool(eligible), "y": y, "label_end": end,
                "feature_reason": reason, "target_label_reason": target_reason,
                "label_reason": reason or target_reason,
                "tested_condition": (w.get("week20_state") == "green") if week_ready else None,
                "definition_ref": DEFINITION_REF})
            counts.update(observations=1, ready_252=int(daily_ready),
                          week_ready120=int(week_ready), eligible=int(eligible))
            counts[reason or "feature_ready"] += 1
        counts["price_reset_rows"] = resets
        per_asset[asset] = dict(counts)
    keys = ("observations", "ready_252", "week_ready120", "eligible", "price_reset_rows",
            "continuous252_or_indicator_missing", "previous_week_unknown_or_warmup120", "feature_ready")
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in keys}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["周色仅用上一已完成ISO周；本周即使周五也不使用。这是保守延迟代理，不构成交易过滤。",
                         "无交易的日历周不伪造报价；连续周数按有报价的交易周计数。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_observations(payload, contract, compute_labels=False)
    rows, dates = prepared["observations"], payload["calendar"]
    index = {d: i for i, d in enumerate(dates)}
    def end(row):
        j = index[row["date"]] + 21
        return dates[j] if j < len(dates) else None
    ready = [r for r in rows if r["eligible"]]
    def rank(subset, fields):
        return int(np.linalg.matrix_rank(np.asarray(
            [[1, *(r["features"][name] for name in fields)] for r in subset], dtype=float))) if subset else 0
    phases = {}
    for phase in PHASES:
        subset = [r for r in rows if _phase(r["date"]) == phase]
        qualified = [r for r in subset if r["eligible"]]
        phases[phase] = {"scheduled": len(subset), "ready_252": sum(r["ready_252"] for r in subset),
                         "week_ready120": sum(r["week_continuous"] >= WEEK_WARMUP for r in subset),
                         "eligible": len(qualified),
                         "calendar_mature_same_phase": sum(bool(end(r) and _phase(end(r)) == phase) for r in qualified),
                         "states": dict(Counter(r["week20_state"] for r in qualified))}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in ready if r["date"] <= fold["train_end"] and
                 end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in ready if fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "train_dates": len({r["date"] for r in train}),
                      "evaluation_dates": len({r["date"] for r in ev}),
                      "train_rank_B1": rank(train, BASELINE_FEATURES),
                      "train_rank_B2": rank(train, (*BASELINE_FEATURES, *ADDED_FEATURES)),
                      "train_states": dict(Counter(r["week20_state"] for r in train)),
                      "evaluation_states": dict(Counter(r["week20_state"] for r in ev))})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "scientific_support": {"phases": phases, "folds": folds,
                "feature_rank": {"B1": rank(ready, BASELINE_FEATURES),
                                 "B2": rank(ready, (*BASELINE_FEATURES, *ADDED_FEATURES))},
                "model_feature_count": len(BASELINE_FEATURES) + len(ADDED_FEATURES),
                "added_distribution": dict(Counter(r["week20_state"] for r in ready)),
                "unknown_reasons": dict(Counter(r["feature_reason"] for r in rows if r["feature_reason"])),
                "note": "Only source, past features and calendar label maturity used; no outcome values."}}
