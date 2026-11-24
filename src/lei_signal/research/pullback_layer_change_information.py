"""Research-only adjacent confirmed pullback MA-layer change.

All identities become usable on their confirmation close. This neither defines
the full LEI structure nor changes Module A entry/exit rules.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from pathlib import Path
import statistics

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.clock_classifier import slope_series
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel

DEFINITION_REF = "research.pullback.ma_layer_change@1.0.0"
BASELINE_FEATURES = ("ret20", "vol20", "slope60", "distance60_atr",
                     "current_level", "depth_pct", "asset_510050",
                     "asset_510500", "asset_588000")
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def _phase(day):
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "pullback_layer_change_information" or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented"):
        raise ValueError("exact pullback-layer definition and segmented252 required")
    if (target.get("kind") != "mae" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("path_field", "close") != "close" or
            target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("target freezes future t+1..t+21 close-path MAE")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("daily schedule required")
    if payload.get("data_mode") != "synthetic":
        if (payload.get("price_series") != "economic_price" or
                tuple(contract["universe"]["assets"]) != ASSETS or
                contract["question"].get("period") != ["2022-01-04", "2026-06-30"]):
            raise ValueError("real scope freezes four ETFs and economic price")
    calendar, assets = payload["calendar"], contract["universe"]["assets"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("ordered unique calendar required")
    for day in calendar:
        shared._date(day)
    if not isinstance(assets, list) or not assets or len(assets) != len(set(assets)):
        raise ValueError("ordered unique assets required")
    by_key = {}
    for row in payload["bars"]:
        key = row["asset"], row["date"]
        if key in by_key or row["asset"] not in assets or row["date"] not in calendar:
            raise ValueError("duplicate/out-of-scope bar")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar has prices")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted price")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def _segment_info(segment, global_indices):
    frame = compute_features(pd.DataFrame(segment))
    slope, _ = slope_series(frame)
    piv_frame = frame.set_index(pd.to_datetime(frame["date"]))
    pivots = confirmed_pivots(piv_frame, left=3, right=3)
    centers = defaultdict(set)
    for p in pivots:
        centers[p.index].add(p.kind)
    by_confirm = defaultdict(list)
    for p in pivots:
        by_confirm[global_indices[p.confirmed_index]].append({
            "kind": p.kind, "center_index": global_indices[p.index],
            "center_date": segment[p.index]["date"], "confirm_index": global_indices[p.confirmed_index],
            "confirm_date": segment[p.confirmed_index]["date"], "price": float(p.price),
            "conflict": len(centers[p.index]) == 2})
    info = {}
    closes = frame["close"].astype(float).tolist()
    for pos, index in enumerate(global_indices):
        ready = pos + 1 >= WARMUP
        sma_order = ready and float(frame["sma20"].iloc[pos]) > float(frame["sma60"].iloc[pos]) > float(frame["sma120"].iloc[pos])
        ema_order = ready and float(frame["ema20"].iloc[pos]) > float(frame["ema60"].iloc[pos]) > float(frame["ema120"].iloc[pos])
        atr = float(frame["atr14"].iloc[pos]) if ready else None
        vol = (statistics.stdev(math.log(closes[j] / closes[j-1]) for j in range(pos-19, pos+1))
               * math.sqrt(252) * 100) if ready else None
        info[index] = {"ready": ready and atr is not None and atr > 0,
                       "continuous_real_ohlc": pos + 1,
                       "sma_order": bool(sma_order), "ema_order": bool(ema_order),
                       "ordered": bool(sma_order and ema_order),
                       "sma120": float(frame["sma120"].iloc[pos]) if ready else None,
                       "direction60": bool(closes[pos] > closes[pos-60]) if ready else False,
                       "ret20": 100 * (closes[pos] / closes[pos-20] - 1) if ready else None,
                       "vol20": vol, "slope60": 100 * float(slope.iloc[pos]) if ready else None,
                       "distance60_atr": (closes[pos] - float(frame["sma60"].iloc[pos])) / atr if ready and atr and atr > 0 else None,
                       "groups": {n: max(float(frame[f"sma{n}"].iloc[pos]), float(frame[f"ema{n}"].iloc[pos]))
                                  for n in (20, 60, 120)} if ready else None,
                       "min_all_six": min(float(frame[f"{kind}{n}"].iloc[pos])
                                          for kind in ("sma", "ema") for n in (20, 60, 120)) if ready else None}
    return info, by_confirm


def _touch_rank(day_low, detail):
    flags = {f"touch_{n}": day_low <= detail["groups"][n] for n in (20, 60, 120)}
    below_all = day_low < detail["min_all_six"]
    rank = (4 if below_all else 3 if flags["touch_120"] else
            2 if flags["touch_60"] else 1 if flags["touch_20"] else 0)
    return {**flags, "below_all_six": below_all, "rank": rank}


def prepare_pullback_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    if compute_labels and payload.get("data_mode") != "synthetic" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real future labels require separate effect authorization")
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((day for _, day in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    idx = {day: i for i, day in enumerate(calendar)}
    observations, all_cycles, all_pivots, per_asset = [], [], [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day, "status": "vendor_missing"})) for day in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        info, pivots_by_confirm = {}, defaultdict(list)
        segment, indices = [], []
        for i, row in enumerate(rows):
            if row["date"] > available_end:
                break
            if _known(row):
                segment.append(row); indices.append(i)
            else:
                if segment:
                    part, piv = _segment_info(segment, indices)
                    info.update(part)
                    for key, values in piv.items():
                        pivots_by_confirm[key].extend(values)
                segment, indices = [], []
        if segment:
            part, piv = _segment_info(segment, indices)
            info.update(part)
            for key, values in piv.items():
                pivots_by_confirm[key].extend(values)
        active = False
        sequence = 0
        road_at = {}
        pending = previous = None
        counts = Counter()
        for i, day in enumerate(calendar):
            if day > available_end:
                break
            row, d = rows[i], info.get(i)
            reason, road = "no_event", None
            event, completed = None, None
            if d is None or not d["ready"]:
                if active or pending or previous:
                    counts["road_or_pair_reset"] += 1
                active = False; pending = previous = None
                reason = "missing_real_ohlc_reset" if d is None else "continuous252_or_indicator_missing"
            elif active and (not d["sma_order"] or float(row["close"]) < d["sma120"]):
                active = False; pending = previous = None
                counts["road_ended"] += 1
                reason = "road_ended_no_same_day_reopen"
            elif not active:
                if d["sma_order"] and d["ema_order"] and d["direction60"]:
                    sequence += 1; active = True
                    counts["road_opened"] += 1
                    reason = "road_opened"
                else:
                    reason = "no_active_road"
            if active:
                road = f"{asset}|road-{sequence}"
            road_at[i] = road
            for pivot in pivots_by_confirm.get(i, []):
                entry = {"asset": asset, "road_id": road, **pivot}
                if pivot["conflict"]:
                    entry["status"] = "same_center_high_low_conflict"
                elif road is None or road_at.get(pivot["center_index"]) != road:
                    entry["status"] = "center_or_confirmation_outside_road"
                elif pivot["kind"] == "high":
                    if previous and pivot["center_index"] <= previous["low_center_index"]:
                        entry["status"] = "high_not_after_previous_low"
                    else:
                        entry["status"] = "pending_high_replaced" if pending else "pending_high"
                        pending = pivot
                else:
                    if pending is None:
                        entry["status"] = "low_without_new_high"
                    elif pivot["center_index"] <= pending["center_index"] or (previous and pivot["center_index"] <= previous["low_center_index"]):
                        entry["status"] = "low_order_conflict"
                    else:
                        high = pending
                        interval = range(high["center_index"], pivot["center_index"] + 1)
                        comparable = all(road_at.get(j) == road and info[j]["ordered"] for j in interval)
                        level = None
                        touch_trace = []
                        if comparable:
                            for j in interval:
                                day_low = float(rows[j]["low"])
                                touch_trace.append({"date": rows[j]["date"], "low": day_low,
                                                    **_touch_rank(day_low, info[j])})
                            level = max(item["rank"] for item in touch_trace)
                        depth = 100 * (high["price"] - min(float(rows[j]["low"]) for j in interval)) / high["price"]
                        completed = {"asset": asset, "road_id": road,
                                     "high_center_index": high["center_index"], "high_center_date": high["center_date"],
                                     "high_confirm_date": high["confirm_date"],
                                     "low_center_index": pivot["center_index"], "low_center_date": pivot["center_date"],
                                     "low_confirm_date": day, "level": level, "depth_pct": depth,
                                     "comparable": comparable, "touch_trace": touch_trace,
                                     "previous_low_confirm_date": previous["low_confirm_date"] if previous else None}
                        all_cycles.append(completed)
                        pending = None
                        counts["cycles_completed"] += 1
                        counts["cycles_unordered"] += int(not comparable)
                        if previous is None:
                            reason = "completed_no_previous_cycle"
                        elif not previous["comparable"]:
                            reason = "previous_cycle_unordered"
                        elif not comparable:
                            reason = "current_cycle_unordered"
                        else:
                            reason = "paired_event"
                            event = {"previous": previous, "current": completed,
                                     "added": previous["level"] - level}
                        previous = completed
                        entry["status"] = "cycle_completed"
                all_pivots.append(entry)
            if day not in selected or not first <= day <= last:
                continue
            features = {name: d[name] if d and d["ready"] else None for name in BASELINE_FEATURES[:4]}
            features["current_level"] = completed["level"] if event else None
            features["depth_pct"] = completed["depth_pct"] if event else None
            for code in ASSETS[1:]:
                features["asset_" + code.split(".")[0]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            features["added"] = event["added"] if event else None
            y, label_end, target_reason = (shared._label(label_rows, idx[day], contract["target"])
                                           if compute_labels else (None, None, "not_computed"))
            eligible = event is not None and (y is not None if compute_labels else True)
            label_reason = (None if eligible and compute_labels else
                            target_reason if event else reason)
            observation = {"id": f"{asset}|{day}", "asset": asset, "date": day,
                           "stratum": f"{asset}|{day[:4]}", "features": features,
                           "eligible": bool(eligible), "y": y, "label_end": label_end,
                           "label_reason": label_reason, "target_label_reason": target_reason,
                           "tested_condition": (event["added"] > 0) if event else None,
                           "feature_reason": None if event else reason,
                           "event_reason": reason, "road_id": road,
                           "continuous_real_ohlc": (0 if d is None else d["continuous_real_ohlc"]),
                           "ready_252": bool(d and d["ready"]),
                           "previous_cycle": event["previous"] if event else None,
                           "current_cycle": completed,
                           "definition_ref": DEFINITION_REF}
            observations.append(observation)
            counts["scheduled"] += 1
            counts["ready_252"] += int(observation["ready_252"])
            counts["events"] += int(event is not None)
            counts["event_positive"] += int(event is not None and event["added"] > 0)
            counts["event_nonpositive"] += int(event is not None and event["added"] <= 0)
            counts["reason:" + reason] += 1
        per_asset[asset] = dict(counts)
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in
                ("scheduled", "ready_252", "events", "event_positive", "event_nonpositive",
                 "cycles_completed", "cycles_unordered", "road_opened", "road_ended", "road_or_pair_reset")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage, "cycles": all_cycles,
            "pivots": all_pivots,
            "warnings": ["3/3已确认摆动和两轮层级是固定窄研究代理；只在低点确认收盘后可见。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_pullback_observations(payload, contract, compute_labels=False)
    rows = prepared["observations"]
    calendar = payload["calendar"]
    idx = {day: i for i, day in enumerate(calendar)}
    def end(row):
        position = idx[row["date"]] + 21
        return calendar[position] if position < len(calendar) else None
    by_phase = {}
    for phase in PHASES:
        subset = [r for r in rows if _phase(r["date"]) == phase]
        events = [r for r in subset if r["features"]["added"] is not None]
        by_phase[phase] = {"scheduled": len(subset), "ready_252": sum(r["ready_252"] for r in subset),
                           "events": len(events), "positive": sum(r["features"]["added"] > 0 for r in events),
                           "zero": sum(r["features"]["added"] == 0 for r in events),
                           "negative": sum(r["features"]["added"] < 0 for r in events),
                           "mature_20_same_phase": sum(bool(end(r) and _phase(end(r)) == phase) for r in events),
                           "by_asset": {a: {"events": sum(r["asset"] == a for r in events),
                                            "mature": sum(bool(r["asset"] == a and end(r) and _phase(end(r)) == phase) for r in events)}
                                        for a in contract["universe"]["assets"]}}
    folds = []
    for fold in contract["split"]["folds"]:
        events = [r for r in rows if r["features"]["added"] is not None]
        train = [r for r in events if r["date"] <= fold["train_end"] and end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in events if fold["eval_start"] <= r["date"] <= fold["eval_end"] and end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "train_dates": len({r["date"] for r in train}),
                      "evaluation_dates": len({r["date"] for r in ev})})
    return {"outcome_values_used_for_design": False, "data_sha256": contract["data"]["sha256"],
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "coverage": prepared["coverage"],
            "scientific_support": {"phases": by_phase, "folds": folds,
                                   "event_reasons": dict(Counter(r["event_reason"] for r in rows)),
                                   "note": "Only calendar endpoints counted; no later price values opened for labels."},
            "observations": rows, "cycles": prepared["cycles"], "pivots": prepared["pivots"]}
