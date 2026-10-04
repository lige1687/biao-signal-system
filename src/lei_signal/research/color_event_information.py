"""First adjacent non-green to green daily20 event with prior completed-week context."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

import numpy as np

from . import workflow_inputs as shared
from .technical_persistence_information import _segment_features
from .top_structure_information import ASSETS, _known, qualify_top_panel
from .weekly_color_information import _weekly_history, _week
from .trend_slope_change_information import _validate as validate_panel

KIND = "color_event_information"
DEFINITION_REFS = {
    "green": "research.trend.daily20_non_green_to_green_week_context@1.0.0",
    "black": "research.trend.daily20_non_black_to_black_week_context@1.0.0",
}
BASELINE_FEATURES = ("ret20", "ret60", "vol20", "bull_group",
                     "asset_510050", "asset_510500", "asset_588000")
ADDED_FEATURES = ("week20_green", "week20_black")


def _validate(payload, contract):
    f, t = contract["feature"], contract["target"]
    event_color = f.get("event_color")
    if (event_color not in DEFINITION_REFS or f.get("kind") != KIND or
            f.get("definition_ref") != DEFINITION_REFS.get(event_color) or
            contract["question"].get("factor_refs") != [DEFINITION_REFS.get(event_color)] or
            f.get("lookback") != 20 or f.get("warmup") != 252 or
            f.get("week_warmup") != 120 or f.get("week_policy") != "previous_iso_week_only" or
            f.get("missing_policy") != "segmented" or
            contract["question"].get("sampling") != "event"):
        raise ValueError("color event requires adjacent non-green to green, daily252 and prior week120")
    if (t.get("kind") not in {"forward_return", "mae"} or t.get("start_offset") != 1 or
            t.get("end_offset") != 21 or t.get("entry_field") != "close" or
            t.get("path_field", "close") != "close" or t.get("price_measure") != "economic_price"):
        raise ValueError("color event target requires t+1..t+21 economic closes")
    source = deepcopy(contract)
    source["feature"].update(kind="slope_change_information", lookback=60,
                             definition_ref="research.trend.slope_change60_20@1.0.0")
    source["question"]["sampling"] = "daily"
    source["target"] = {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                        "entry_field": "close", "price_measure": "economic_price"}
    return validate_panel(payload, source)


def prepare_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    if compute_labels and payload.get("data_mode") != "synthetic":
        p = contract.get("permissions", {})
        if not (p.get("real_labels") is True and p.get("effect_authorized") is True and
                type(p.get("real_fits")) is int and p["real_fits"] == 4):
            raise ValueError("real labels require effect authorization and four fits per target")
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((day for _, day in by_key), default=calendar[0])
    if "decision_at" in payload:
        from datetime import time
        decision = shared._available(payload["decision_at"])
        day = decision.date().isoformat()
        if decision.time() < time(15):
            day = next((d for d in reversed(calendar) if d < day), "0000-00-00")
        available_end = min(available_end, day)
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    observations, per_asset = [], {}
    for asset in assets:
        event_color = contract["feature"]["event_color"]
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day,
                                               "status": "vendor_missing"})) for day in calendar]
        weekly = _weekly_history(calendar, rows, available_end)
        known, segment = {}, []
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
            elif segment:
                flush()
        if segment:
            flush()
        counts = Counter()
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        for i, day in enumerate(calendar):
            if day > available_end or day not in selected or not first <= day <= last:
                continue
            continuous, item = known.get(i, (0, None))
            prior_continuous, prior = known.get(i - 1, (0, None))
            adjacent = (i > 0 and prior_continuous + 1 == continuous and continuous >= 252 and
                        item is not None and prior is not None and item["features"] is not None and
                        prior["features"] is not None)
            event = (adjacent and item["color20"] == event_color and
                     prior["color20"] in ({"black", "gray"} if event_color == "green" else {"green", "gray"}))
            w = weekly.get(_week(day), {})
            week_state = w.get("week20_state") if w.get("week_continuous", 0) >= 120 else None
            reason = ("daily252_or_adjacent_missing" if not adjacent else
                      "not_target_color_transition" if not event else
                      "previous_week_unknown_or_warmup120" if week_state is None else None)
            values = item["features"] if item is not None and item["features"] is not None else {}
            features = {k: values.get(k) for k in BASELINE_FEATURES[:3]}
            features["bull_group"] = int(item["bull_group"]) if values else None
            for code in ASSETS[1:]:
                features["asset_" + code[:6]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            features.update(week20_green=int(week_state == "green") if week_state else None,
                            week20_black=int(week_state == "black") if week_state else None)
            y, end, label_reason = (shared._label(label_rows, i, contract["target"])
                                    if compute_labels and reason is None else
                                    (None, None, reason or "not_computed"))
            eligible = reason is None and (y is not None if compute_labels else True)
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                "stratum": f"{asset}|{day[:4]}", "features": features,
                "color20": item["color20"] if item else None,
                "prior_color20": prior["color20"] if prior else None,
                "week20_state": week_state, "state": week_state,
                "last_completed_week_date": w.get("last_completed_week_date"),
                "week_continuous": w.get("week_continuous", 0),
                "ready_252": bool(adjacent), "continuous_real_ohlc": continuous,
                "bull_group": item["bull_group"] if item else None,
                "event": bool(event), "event_color": event_color, "eligible": bool(eligible),
                "y": y, "label_end": end, "feature_reason": reason,
                "target_label_reason": label_reason, "label_reason": reason or label_reason,
                "tested_condition": bool(event) if adjacent else None,
                "definition_ref": DEFINITION_REFS[event_color]})
            counts.update(scheduled=1, adjacent_ready=int(adjacent), events=int(event),
                          eligible=int(eligible))
            counts[reason or "feature_ready"] += 1
        per_asset[asset] = dict(counts)
    coverage = {k: sum(v.get(k, 0) for v in per_asset.values()) for k in
                ("scheduled", "adjacent_ready", "events", "eligible", "daily252_or_adjacent_missing",
                 "not_target_color_transition", "previous_week_unknown_or_warmup120")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REFS[contract["feature"]["event_color"]])
    return {"observations": observations, "coverage": coverage,
            "warnings": ["仅日20由其他颜色相邻转为指定颜色的局部代理，非完整入场或退出；缺口不造事件。",
                         "上一已完成ISO周状态使用120周暖启动，当前周永不使用。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_observations(payload, contract, compute_labels=False)
    rows, dates = prepared["observations"], payload["calendar"]
    index = {d: i for i, d in enumerate(dates)}
    ready = [r for r in rows if r["eligible"]]
    def end(r):
        j = index[r["date"]] + 21
        return dates[j] if j < len(dates) else None
    folds = []
    for f in contract["split"]["folds"]:
        tr = [r for r in ready if r["date"] <= f["train_end"] and end(r) and end(r) < f["eval_start"]]
        ev = [r for r in ready if f["eval_start"] <= r["date"] <= f["eval_end"] and
              end(r) and end(r) <= f["eval_end"]]
        folds.append({"fold": f, "train": len(tr), "evaluation": len(ev),
                      "train_states": dict(Counter(r["week20_state"] for r in tr)),
                      "evaluation_states": dict(Counter(r["week20_state"] for r in ev)),
                      "train_bull": dict(Counter(str(r["bull_group"]) for r in tr)),
                      "evaluation_bull": dict(Counter(str(r["bull_group"]) for r in ev))})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "source_quality": source["quality"], "source_warnings": source["warnings"],
            "coverage": prepared["coverage"],
            "counts": {"assets": len(contract["universe"]["assets"]), "observations": len(rows),
                       "dates": len({r["date"] for r in rows}), "episodes": None},
            "scientific_support": {"folds": folds,
                "states": dict(Counter(r["week20_state"] for r in ready)),
                "years": {str(y): dict(Counter(r["week20_state"] for r in ready if r["date"].startswith(str(y))))
                          for y in range(2022, 2027)},
                "note": "Only source, prior features and calendar maturity used; no outcome values."}}
