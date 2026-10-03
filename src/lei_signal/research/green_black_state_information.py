"""Past-only research expression of the existing 20/60 green-black clock state."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from datetime import time
import math
import statistics

import numpy as np
import pandas as pd

from lei_signal.features.indicators import compute_features
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known, qualify_top_panel
from .trend_slope_change_information import _validate as validate_slope_panel

DEFINITION_REF = "research.trend.green_black60_state@1.0.0"
BASELINE_FEATURES = ("color20_green", "color20_black", "ret20", "ret60", "vol20",
                     "asset_510050", "asset_510500", "asset_588000")
ADDED_FEATURES = ("color60_green", "color60_black")
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def _phase(day):
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "green_black_state60_information" or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented" or
            contract["question"].get("factor_refs", [DEFINITION_REF]) != [DEFINITION_REF]):
        raise ValueError("green-black state requires its exact segmented252 definition")
    if (target.get("kind") not in {"forward_return", "mae"} or
            target.get("start_offset") != 1 or target.get("end_offset") != 61 or
            target.get("entry_field") != "close" or
            target.get("price_measure") != "economic_price" or
            target.get("path_field", "close") != "close"):
        raise ValueError("green-black target requires t+1 through t+61 economic closes")
    # Reuse source and timing validation; its feature/target values are placeholders
    # for validation only and no slope feature or future label is calculated.
    source = deepcopy(contract)
    source["feature"].update(kind="slope_change_information",
                             definition_ref="research.trend.slope_change60_20@1.0.0")
    source["target"] = {"kind": "forward_return", "start_offset": 1,
                        "end_offset": 21, "entry_field": "close", "price_measure": "economic_price"}
    return validate_slope_panel(payload, source)


def _color(close, ema, lag):
    if not all(math.isfinite(v) for v in (close, ema, lag)):
        return None
    if close > ema and close > lag:
        return "green"
    if close < ema and close < lag:
        return "black"
    return "gray"


def _segment_features(segment):
    if not segment:
        return []
    frame = compute_features(pd.DataFrame(segment))
    closes = frame["close"].astype(float).tolist()
    result = []
    previous60 = None
    for i, close in enumerate(closes):
        colors = {}
        for period in (20, 60):
            ema, lag = float(frame[f"ema{period}"].iloc[i]), float(frame[f"close_lag{period}"].iloc[i])
            colors[period] = _color(close, ema, lag)
        first = colors[60] is not None and previous60 is not None and colors[60] != previous60
        previous60 = colors[60]
        if i + 1 < WARMUP:
            result.append({"color20": colors[20], "color60": colors[60], "first_color60": first,
                           "features": None})
            continue
        vol = statistics.stdev(math.log(closes[j] / closes[j - 1])
                               for j in range(i - 19, i + 1)) * math.sqrt(252) * 100
        features = {"color20_green": int(colors[20] == "green"),
                    "color20_black": int(colors[20] == "black"),
                    "ret20": 100 * (close / closes[i - 20] - 1),
                    "ret60": 100 * (close / closes[i - 60] - 1), "vol20": vol,
                    "color60_green": int(colors[60] == "green"),
                    "color60_black": int(colors[60] == "black")}
        if colors[20] is None or colors[60] is None or not all(math.isfinite(v) for v in features.values()):
            features = None
        result.append({"color20": colors[20], "color60": colors[60],
                       "first_color60": first, "features": features})
    return result


def prepare_state_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Build scheduled observations; the default never accesses future prices."""
    if compute_labels and payload.get("data_mode") != "synthetic":
        permissions = contract.get("permissions", {})
        if (permissions.get("real_labels") is not True or
                permissions.get("effect_authorized") is not True or
                type(permissions.get("real_fits")) is not int or permissions["real_fits"] != 4):
            raise ValueError("real labels require effect authorization and four fits")
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        decision = shared._available(payload["decision_at"])
        day = decision.date().isoformat()
        if decision.time() < time(15):
            day = next((d for d in reversed(calendar) if d < day), "0000-00-00")
        available_end = min(available_end, day)
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index = {d: i for i, d in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day, "status": "vendor_missing"}))
                for day in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        known = {}
        segment = []
        resets = 0
        def flush():
            for pos, ((idx, _), item) in enumerate(zip(segment, _segment_features([r for _, r in segment])), 1):
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
            values = item["features"] if ready else None
            features = {key: values[key] if ready else None for key in (*BASELINE_FEATURES[:5], *ADDED_FEATURES)}
            for code in ASSETS[1:]:
                features["asset_" + code[:6]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, end, target_reason = (shared._label(label_rows, index[day], contract["target"])
                                     if compute_labels else (None, None, "not_computed"))
            reason = None if ready else "continuous252_or_indicator_missing"
            eligible = bool(ready and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                                 "stratum": f"{asset}|{day[:4]}", "features": features,
                                 "color20": item["color20"] if ready else None,
                                 "color60": item["color60"] if ready else None,
                                 "first_color60": item["first_color60"] if ready else False,
                                 "state": item["color60"] if ready else None,
                                 "eligible": eligible, "y": y, "label_end": end,
                                 "label_reason": reason or target_reason,
                                 "target_label_reason": target_reason, "feature_reason": reason,
                                 "tested_condition": (item["color60"] == "green") if ready else None,
                                 "ready_252": ready, "continuous_real_ohlc": continuous,
                                 "definition_ref": DEFINITION_REF})
            counts.update(observations=1, ready_252=int(ready), eligible=int(eligible))
            counts[reason or "feature_ready"] += 1
        counts["price_reset_rows"] = resets
        per_asset[asset] = dict(counts)
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in
                ("observations", "ready_252", "eligible", "price_reset_rows",
                 "continuous252_or_indicator_missing", "feature_ready")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["绿黑状态仅表示已知价格关系，不代表交易触发；行动资料历史到达时间仍未知。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """Source and past-feature checks with calendar-only future maturity counts."""
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_state_observations(payload, contract)
    rows, dates = prepared["observations"], payload["calendar"]
    index = {day: i for i, day in enumerate(dates)}
    def end(row):
        j = index[row["date"]] + 61
        return dates[j] if j < len(dates) else None
    ready = [r for r in rows if r["ready_252"]]
    by_date = {}
    for row in ready:
        by_date.setdefault(row["date"], set()).add(row["asset"])
    common = {day for day, members in by_date.items() if members == set(ASSETS)}
    by_phase = {}
    for phase in PHASES:
        subset = [r for r in rows if _phase(r["date"]) == phase]
        by_phase[phase] = {"scheduled": len(subset), "ready_252": sum(r["ready_252"] for r in subset),
                           "calendar_mature_same_phase": sum(bool(r["ready_252"] and end(r) and
                                                            _phase(end(r)) == phase) for r in subset),
                           "common_four_etf_dates": sum(_phase(d) == phase for d in common),
                           "color20x60": dict(Counter(f"{r['color20']}|{r['color60']}" for r in subset if r["ready_252"]))}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in ready if r["date"] <= fold["train_end"] and end(r) and end(r) < fold["eval_start"]]
        ev = [r for r in ready if fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              end(r) and end(r) <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev),
                      "train_dates": len({r["date"] for r in train}),
                      "evaluation_dates": len({r["date"] for r in ev}),
                      "train_common_four_etf_dates": len({r["date"] for r in train} & common),
                      "evaluation_common_four_etf_dates": len({r["date"] for r in ev} & common)})
    def rank(keys):
        return int(np.linalg.matrix_rank(np.asarray([[1, *(r["features"][k] for k in keys)]
                                                     for r in ready], dtype=float))) if ready else 0
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "scientific_support": {"phases": by_phase, "folds": folds,
                                   "common_four_etf_dates": len(common),
                                   "feature_rank": {"B1": rank(BASELINE_FEATURES),
                                                    "B2": rank((*BASELINE_FEATURES, *ADDED_FEATURES))},
                                   "model_feature_count": len(BASELINE_FEATURES) + len(ADDED_FEATURES),
                                   "unknown_reasons": dict(Counter(r["feature_reason"] for r in rows if r["feature_reason"])),
                                   "note": "Future support uses calendar dates only, not future prices."}}
