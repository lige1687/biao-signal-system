"""Research-only, close-known daily volume-profile overhead information.

The production profile formula is reused unchanged. This wrapper requires a
full known window and keeps split-crossing quantity windows unknown. It never
claims that the daily proxy is the distribution of actual holder costs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from pathlib import Path
import statistics

import pandas as pd

from lei_signal.features.volume_profile import compute_volume_profile
from . import workflow_inputs as shared
from .top_structure_information import ASSETS, WARMUP, _known

DEFINITION_REF = "research.volume_profile.overhead120@1.0.0"
WINDOW = 120
BINS = 50
VALUE_AREA = .70
SUPPORT_ZONE_PCT = .05
BASELINE_FEATURES = ("r1", "ret3", "ret20", "vol20", "ema20_distance",
                     "sma60_atr_distance", "prior20_high_atr_distance",
                     "prior120_high_atr_distance", "price_only_overhead_ratio",
                     "asset_510050", "asset_510500", "asset_588000")
PHASES = ("early_2022_2024", "eval_2025", "eval_2026H1")


def phase(day: str) -> str:
    return PHASES[0] if day <= "2024-12-31" else PHASES[1] if day <= "2025-12-31" else PHASES[2]


def _quantity_known(row: dict) -> bool:
    value = row.get("volume")
    return (row.get("volume_source_known") is True and
            isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(float(value)) and value >= 0 and row.get("volume_break") is False)


def _price_known(row: dict) -> bool:
    return (_known(row) and all(float(row[k]) > 0 for k in ("open", "high", "low", "close")))


def _validate(payload: dict, contract: dict):
    feature, target = contract["feature"], contract["target"]
    if (feature.get("kind") != "profile_overhead_information" or
            feature.get("definition_ref") != DEFINITION_REF or
            feature.get("lookback") != WINDOW or feature.get("warmup") != WARMUP or
            feature.get("missing_policy") != "segmented" or
            contract["question"].get("sampling") != "daily"):
        raise ValueError("P01 requires exact daily overhead120 card and segmented OHLC252")
    if (target.get("kind") != "forward_return" or target.get("start_offset") != 1 or
            target.get("end_offset") != 21 or target.get("entry_field") != "close" or
            target.get("price_measure") != "economic_price"):
        raise ValueError("P01 freezes t+1 to t+21 closing return")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("ordered unique calendar required")
    for day in calendar:
        shared._date(day)
    assets = contract["universe"]["assets"]
    if not assets or len(assets) != len(set(assets)):
        raise ValueError("ordered unique assets required")
    if payload.get("data_mode") != "synthetic":
        if tuple(assets) != ASSETS or contract["question"].get("period") != ["2022-01-04", "2026-06-30"]:
            raise ValueError("P01 freezes four qualified domestic ETFs and their observed period")
        if payload.get("price_series") != "economic_price":
            raise ValueError("P01 requires qualified economic OHLCV")
    by_key = {}
    for row in payload["bars"]:
        key = (row["asset"], row["date"])
        if key in by_key or row["asset"] not in assets or row["date"] not in calendar:
            raise ValueError("duplicate or out-of-scope bar")
        if row.get("status") != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close", "volume")):
            raise ValueError("nonquoted bar carries OHLCV")
        if _price_known(row) and "decision_at" in row:
            at = shared._available(row["decision_at"])
            if at.date() < shared._date(row["date"]) or (at.date() == shared._date(row["date"]) and at.hour < 15):
                raise ValueError("close used before session end")
        by_key[key] = row
    return calendar, assets, by_key


def _atr20(rows: list[dict]) -> float:
    ranges = []
    for i in range(len(rows)-20, len(rows)):
        bar, previous = rows[i], rows[i-1]
        high, low, close = float(bar["high"]), float(bar["low"]), float(previous["close"])
        ranges.append(max(high-low, abs(high-close), abs(low-close)))
    return statistics.mean(ranges)


def _profile_pair(window: list[dict]):
    if len(window) != WINDOW or not all(_price_known(r) and _quantity_known(r) for r in window):
        return None, None
    frame = pd.DataFrame(window)[["open", "high", "low", "close", "volume"]]
    observed = compute_volume_profile(frame, window=WINDOW, bins=BINS,
                                      value_area=VALUE_AREA, support_zone_pct=SUPPORT_ZONE_PCT)
    geometry = frame.copy()
    geometry["volume"] = 1.0
    price_only = compute_volume_profile(geometry, window=WINDOW, bins=BINS,
                                        value_area=VALUE_AREA, support_zone_pct=SUPPORT_ZONE_PCT)
    return observed, price_only


def prepare_profile_observations(payload: dict, contract: dict, *, compute_labels: bool = False) -> dict:
    """Build scheduled rows. Default path never reads a future price row."""
    if compute_labels and payload.get("data_mode") != "synthetic" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True):
        raise ValueError("real future labels require separate authorization")
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index = {d: i for i, d in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset in assets:
        rows = [dict(by_key.get((asset, day), {"asset": asset, "date": day, "status": "vendor_missing"}))
                for day in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        segment = []
        ema20 = None
        counts = Counter()
        for bar in rows:
            day = bar["date"]
            if day > available_end:
                break
            if _price_known(bar):
                segment.append(bar)
                close = float(bar["close"])
                ema20 = close if ema20 is None else (2*close + 19*ema20)/21
            else:
                segment, ema20 = [], None
                counts["price_reset_rows"] += 1
            if day not in selected or not first <= day <= last:
                continue
            ready = len(segment) >= WARMUP
            up = None
            features = {name: None for name in BASELINE_FEATURES}
            features["added"] = None
            reason = None
            overhead = price_only_ratio = None
            if ready:
                closes = [float(r["close"]) for r in segment]
                high = [float(r["high"]) for r in segment]
                atr = _atr20(segment)
                up = sum(closes[-60:]) > sum(closes[-65:-5])
                if atr <= 0 or not math.isfinite(atr):
                    raise ValueError("P01 has no positive ATR20 for its fixed distance baseline")
                features.update(r1=100*(closes[-1]/closes[-2]-1),
                                ret3=100*(closes[-1]/closes[-4]-1),
                                ret20=100*(closes[-1]/closes[-21]-1),
                                vol20=statistics.stdev([math.log(closes[i]/closes[i-1])
                                    for i in range(len(closes)-20,len(closes))])*math.sqrt(252)*100,
                                ema20_distance=100*(closes[-1]/ema20-1),
                                sma60_atr_distance=(closes[-1]-statistics.mean(closes[-60:]))/atr,
                                prior20_high_atr_distance=(max(high[-21:-1])-closes[-1])/atr,
                                prior120_high_atr_distance=(max(high[-121:-1])-closes[-1])/atr)
                observed, price_only = _profile_pair(segment[-WINDOW:])
                if observed is None or price_only is None:
                    window = segment[-WINDOW:]
                    reason = ("volume_break_in_full120_window" if any(r.get("volume_break") is True for r in window)
                              else "unknown_or_zero_total_quantity_in_full120_window")
                else:
                    overhead = observed.overhead_supply_ratio
                    price_only_ratio = price_only.overhead_supply_ratio
                    features["price_only_overhead_ratio"] = price_only_ratio
                    features["added"] = overhead
                for code in ASSETS[1:]:
                    features["asset_" + code.split(".")[0]] = int(asset == code or
                        (payload.get("data_mode") == "synthetic" and asset == "synthetic-B" and code == ASSETS[1]))
            else:
                reason = "continuous252_economic_ohlc_missing"
            y, label_end, label_reason = (shared._label(label_rows, index[day], target=contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            eligible = bool(ready and up and overhead is not None and (y is not None if compute_labels else True))
            observations.append({"id": f"{asset}|{day}", "asset": asset, "date": day,
                "stratum": f"{asset}|{day[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": reason or ("sma60_not_rising" if ready and not up else label_reason),
                "feature_reason": reason, "tested_condition": overhead <= .30 if overhead is not None else None,
                "sma60_up": up, "profile_known": overhead is not None,
                "overhead_supply_ratio": overhead, "price_only_overhead_ratio": price_only_ratio,
                "continuous_real_ohlc": len(segment), "ready_252": ready,
                "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["trend_up"] += int(bool(up))
            counts["profile_known"] += int(overhead is not None)
            counts["profile_unknown"] += int(overhead is None)
            counts["eligible"] += int(eligible)
            if reason:
                counts[reason] += 1
        per_asset[asset] = dict(counts)
    names = ("observations", "ready_252", "trend_up", "profile_known", "profile_unknown",
             "eligible", "price_reset_rows", "volume_break_in_full120_window")
    coverage = {name: sum(v.get(name, 0) for v in per_asset.values()) for name in names}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["日线成交量均匀分箱是研究代理，不是真实成交价或持有人成本。"]}


def qualify_profile_panel(payload: dict, contract: dict, root: Path) -> dict:
    from .volume_information import qualify_volume_panel
    source_contract = {"data": {**contract["data"], "qualification": {
        "adapter": "volume_etf_economic/1.0",
        "manifest_path": contract["data"]["qualification"]["manifest_path"]}},
        "universe": contract["universe"],
        "feature": {"kind": "volume_anomaly_information", "definition_ref":
                    "research.volume.abnormal20@1.0.0", "lookback": 20,
                    "warmup": 252, "missing_policy": "segmented"},
        "target": {"kind": "downside_event", "start_offset": 1,
                   "end_offset": 21, "entry_field": "close", "threshold": 5,
                   "price_measure": "economic_price"},
        "question": {"sampling": "daily"}}
    checked = qualify_volume_panel(payload, source_contract, root)
    return {"quality": checked["quality"], "warnings": [
        "名义OHLCV、行动与经济价格已逐行复核；历史到达时间未认证。"]}


def build_qualification(payload: dict, contract: dict, root: Path) -> dict:
    source = qualify_profile_panel(payload, contract, root)
    prepared = prepare_profile_observations(payload, contract, compute_labels=False)
    observations = prepared["observations"]
    counts = {"assets": len(contract["universe"]["assets"]), "observations": len(observations),
              "dates": len({r["date"] for r in observations}), "episodes": None}
    phases = {p: {"scheduled": len(rr), "sma60_up": sum(r["sma60_up"] is True for r in rr),
                  "profile_known": sum(r["profile_known"] for r in rr),
                  "eligible": sum(r["eligible"] for r in rr)}
              for p in PHASES for rr in [[r for r in observations if phase(r["date"]) == p]]}
    calendar = payload["calendar"]
    index = {day: i for i, day in enumerate(calendar)}
    folds = []
    for fold in contract["split"]["folds"]:
        train = [r for r in observations if r["eligible"] and index[r["date"]] + 21 < len(calendar)
                 and r["date"] <= fold["train_end"] and
                 calendar[index[r["date"]] + 21] < fold["eval_start"]]
        ev = [r for r in observations if r["eligible"] and index[r["date"]] + 21 < len(calendar)
              and fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              calendar[index[r["date"]] + 21] <= fold["eval_end"]]
        folds.append({"fold": fold, "train": len(train), "evaluation": len(ev)})
    return {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
            "counts": counts, "scientific_support": {"phases": phases, "folds": folds,
                "baseline_features": list(BASELINE_FEATURES), "model_feature_count": 13,
                "tested_condition_threshold": .30, "effectiveness": "not_evaluated"},
            "coverage": prepared["coverage"], "source_quality": source["quality"],
            "source_warnings": source["warnings"]}
