"""Research-only, prefix-causal three-bar descending-high/low pattern.

This is a strict simple-top subset, dated at the third completed close. It is
not the production top detector and does not imply a trading exit.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from . import workflow_inputs as shared

DEFINITION_REF = "research.structure.simple_top3@1.0.0"
WARMUP = 252
ASSETS = ("510300.SS", "510050.SS", "510500.SS", "588000.SS")


def qualify_top_panel(payload: dict, contract: dict, root):
    """Recheck full nominal OHLC/action provenance through the source-only V01 path.

    V01's event, volume features, outcome labels and fitted results are never
    used. Its source routine independently rebuilds all four economic OHLC
    fields and checks every saved raw-response binding.
    """
    from .volume_information import qualify_volume_panel
    source_contract = {
        "data": {**contract["data"], "qualification": {
            "adapter": "volume_etf_economic/1.0",
            "manifest_path": contract["data"]["qualification"]["manifest_path"],
        }},
        "universe": contract["universe"],
        "feature": {"kind": "volume_anomaly_information", "definition_ref":
                    "research.volume.abnormal20@1.0.0", "lookback": 20,
                    "warmup": 252, "missing_policy": "segmented"},
        "target": {"kind": "downside_event", "start_offset": 1,
                   "end_offset": 21, "entry_field": "close", "threshold": 5,
                   "price_measure": "economic_price"},
        "question": {"sampling": "daily"},
    }
    checked = qualify_volume_panel(payload, source_contract, root)
    return {"quality": checked["quality"], "warnings": [
        "逐行名义OHLC和行动重建已重新核对；V01量仅在源资格例程内核对，未进入T01特征。",
        "行动历史到达时间及完整性仍未知；这些是回顾性经济价格观察。",
    ]}


def _known(row):
    return (row.get("status") == "quoted" and row.get("action_known") is True
            and all(shared._number(row.get(k)) for k in ("open", "high", "low", "close"))
            and row["low"] <= min(row["open"], row["close"])
            <= max(row["open"], row["close"]) <= row["high"])


def _validate(payload, contract):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "simple_top3_information" or
        feature.get("definition_ref") != DEFINITION_REF or
        feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
        feature.get("missing_policy") != "segmented"):
        raise ValueError("T01 requires its exact card and OHLC252 segmented warmup")
    if (target.get("kind") != "mae" or target.get("start_offset") != 1 or
        target.get("end_offset") != 21 or target.get("entry_field") != "close" or
        target.get("path_field", "close") != "close" or
        target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("T01 freezes t+1..t+21 closing-path MAE")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("T01 retains all scheduled daily observations")
    if payload.get("data_mode") != "synthetic" and payload.get("price_series") != "economic_price":
        raise ValueError("T01 needs qualified economic OHLC")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("calendar must be ordered unique dates")
    for d in calendar:
        shared._date(d)
    assets = contract["universe"]["assets"]
    if not isinstance(assets, list) or not assets or len(set(assets)) != len(assets):
        raise ValueError("assets must be ordered unique codes")
    if payload.get("data_mode") != "synthetic" and tuple(assets) != ASSETS:
        raise ValueError("T01 freezes four domestic broad ETF identities")
    by_key = {}
    for row in payload["bars"]:
        key = (row["asset"], row["date"])
        if key in by_key or row["asset"] not in assets or row["date"] not in calendar:
            raise ValueError("duplicate or out-of-scope bar")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close")):
            raise ValueError("nonquoted bar carries OHLC")
        if row["status"] == "quoted" and any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
            raise ValueError("invalid quoted OHLC")
        if _known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def prepare_top_observations(payload: dict, contract: dict, *, compute_labels: bool = True) -> dict:
    """Build all observations using only present/past OHLC when labels are off."""
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
        closes, highs, lows = [], [], []
        ema20 = None
        counts = Counter()
        for row in rows:
            d = row["date"]
            if d > available_end:
                break
            if _known(row):
                closes.append(float(row["close"])); highs.append(float(row["high"])); lows.append(float(row["low"]))
                ema20 = closes[-1] if ema20 is None else (2 * closes[-1] + 19 * ema20) / 21
            else:
                closes, highs, lows, ema20 = [], [], [], None
                counts["price_reset_rows"] += 1
            if d not in selected or not first <= d <= last:
                continue
            ready = len(closes) >= WARMUP
            up = (sum(closes[-60:]) > sum(closes[-65:-5])) if ready else None
            top = (highs[-1] < highs[-2] < highs[-3] and lows[-1] < lows[-2] < lows[-3]) if ready else None
            r1 = 100 * (closes[-1] / closes[-2] - 1) if ready else None
            ret3 = 100 * (closes[-1] / closes[-4] - 1) if ready else None
            ret20 = 100 * (closes[-1] / closes[-21] - 1) if ready else None
            vol20 = (statistics.stdev([math.log(closes[i] / closes[i-1]) for i in range(len(closes)-20, len(closes))])
                     * math.sqrt(252) * 100) if ready else None
            black20 = (closes[-1] < ema20 and closes[-1] < closes[-21]) if ready else None
            features = {"r1": r1, "ret3": ret3, "ret20": ret20, "vol20": vol20,
                        "black20": int(black20) if ready else None, "added": int(top) if ready else None}
            for code in ASSETS[1:]:
                features["asset_" + code.split(".")[0]] = int(asset == code or
                    (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            y, label_end, label_reason = (shared._label(label_rows, index_of[d], target=contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            feature_reason = None if ready else "continuous252_or_economic_price_missing"
            eligible = bool(ready and up and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{d}", "asset": asset, "date": d,
                "stratum": f"{asset}|{d[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": feature_reason or ("sma60_not_rising" if ready and not up else label_reason),
                "feature_reason": feature_reason, "tested_condition": top,
                "sma60_up": up, "simple_top3": top, "r1": r1, "ret3": ret3,
                "ret20": ret20, "vol20": vol20, "black20": black20,
                "continuous_real_ohlc": len(closes), "ready_252": ready,
                "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["trend_up"] += int(bool(up))
            counts["top_all"] += int(bool(top))
            counts["top_in_uptrend"] += int(bool(top and up))
            counts["eligible"] += int(eligible)
        per_asset[asset] = dict(counts)
    coverage = {key: sum(v.get(key, 0) for v in per_asset.values()) for key in
                ("observations", "ready_252", "trend_up", "top_all", "top_in_uptrend", "eligible", "price_reset_rows")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["严格三日形态仅为原文简单顶部的窄子集；收盘后已知，不代表立即退出。"]}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _phase(day):
    return "early_2022_2024" if day <= "2024-12-31" else "eval_2025" if day <= "2025-12-31" else "eval_2026H1"


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    """No labels or future-price values; dates only establish maturity."""
    root = Path(root)
    source = qualify_top_panel(payload, contract, root)
    prepared = prepare_top_observations(payload, contract, compute_labels=False)
    calendar = payload["calendar"]
    index_of = {d: i for i, d in enumerate(calendar)}
    features = []
    for obs in prepared["observations"]:
        d = obs["date"]
        row = {"id": obs["id"], "asset": obs["asset"], "date": d,
               "phase": _phase(d), "calendar_index": index_of[d],
               "sma60_up": obs["sma60_up"], "simple_top3": obs["simple_top3"],
               "r1": obs["r1"], "ret3": obs["ret3"], "ret20": obs["ret20"],
               "vol20": obs["vol20"], "black20": obs["black20"],
               "ready_252": obs["ready_252"], "reason": obs["feature_reason"]}
        for horizon in (5, 10, 20, 60, 120):
            end_index = index_of[d] + horizon + 1
            end = calendar[end_index] if end_index < len(calendar) else None
            row[f"h{horizon}_end"] = end
            row[f"h{horizon}_mature"] = end is not None and _phase(end) == _phase(d)
        features.append(row)
    pairs, support = [], []
    for event in features:
        if not (event["sma60_up"] and event["simple_top3"] and event["h20_mature"]):
            continue
        candidates = []
        for control in features:
            if (control["asset"] != event["asset"] or control["phase"] != event["phase"] or
                not control["sma60_up"] or control["simple_top3"] or
                not control["h20_mature"] or control["black20"] != event["black20"]):
                continue
            dt = abs(event["calendar_index"] - control["calendar_index"])
            dr = abs(event["r1"] - control["r1"])
            d3 = abs(event["ret3"] - control["ret3"])
            dv = abs(event["vol20"] - control["vol20"])
            if dt <= 60 and dr <= .5 and d3 <= 1 and dv <= 5:
                candidates.append((dr / .5 + d3 + dv / 5, dt, control["date"], control))
        chosen = sorted(candidates, key=lambda item: item[:3])[:3]
        for rank, item in enumerate(chosen, 1):
            pairs.append({"event_id": event["id"], "control_id": item[3]["id"],
                          "rank": rank, "distance": item[0]})
        support.append({"id": event["id"], "asset": event["asset"], "phase": event["phase"],
                        "matched": bool(chosen), "controls": len(chosen)})
    counts = {"assets": len(contract["universe"]["assets"]),
              "observations": len(features), "dates": len({r["date"] for r in features}),
              "episodes": None}
    periods = {}
    for phase in ("early_2022_2024", "eval_2025", "eval_2026H1"):
        rr = [r for r in features if r["phase"] == phase]
        ss = [r for r in support if r["phase"] == phase]
        periods[phase] = {"observations": len(rr), "trend_up": sum(r["sma60_up"] is True for r in rr),
                          "top_mature": len(ss), "matched": sum(s["matched"] for s in ss),
                          "unmatched": sum(not s["matched"] for s in ss),
                          "ordinary_mature": sum(r["sma60_up"] is True and r["simple_top3"] is False and r["h20_mature"] for r in rr)}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in features if r["sma60_up"] is True and r["h20_end"] and
                 r["date"] <= fold["train_end"] and r["h20_end"] < fold["eval_start"]]
        ev = [r for r in features if r["sma60_up"] is True and
              fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              r["h20_end"] and r["h20_end"] <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "train_true": sum(r["simple_top3"] is True for r in train),
                      "train_false": sum(r["simple_top3"] is False for r in train),
                      "evaluation": len(ev), "evaluation_true": sum(r["simple_top3"] is True for r in ev),
                      "evaluation_false": sum(r["simple_top3"] is False for r in ev)})
    return {"features": features, "matches": pairs, "match_support": support,
            "qualification": {"data_sha256": contract["data"]["sha256"],
                              "outcome_values_used_for_design": False, "counts": counts,
                              "scientific_support": {"periods": periods, "folds": folds,
                                  "matched": sum(s["matched"] for s in support),
                                  "unmatched": sum(not s["matched"] for s in support),
                                  "pairs": len(pairs),
                                  "distinct_controls": len({p["control_id"] for p in pairs}),
                                  "model_feature_count": 9,
                                  "note": "All scheduled observations retained; matching uses present/past values and calendar positions only."},
                              "source_quality": source["quality"], "source_warnings": source["warnings"],
                              "coverage": prepared["coverage"]}}


def write_qualification(result: dict, out_dir: Path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("features.csv", result["features"]), ("matches.csv", result["matches"])):
        with (out_dir / name).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    for name, value in (("qualification.json", result["qualification"]),
                        ("match-support.json", result["match_support"])):
        with (out_dir / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
