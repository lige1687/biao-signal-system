"""Research-only daily abnormal ETF volume and same-day price background.

All features are available only after the observation close. A volume source
gap or known share-unit break restarts its 20-quote window; it never becomes a
false anomaly. Future labels are optional and absent in qualification mode.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

from . import workflow_inputs as shared

DEFINITION_REF = "research.volume.abnormal20@1.0.0"
WARMUP = 252
LOOKBACK = 20


def qualify_volume_panel(payload: dict, contract: dict, root: Path) -> dict:
    """Recheck the saved economic/volume assembly and raw-response bindings."""
    root = Path(root)
    q = contract["data"].get("qualification", {})
    if q.get("adapter") != "volume_etf_economic/1.0":
        raise ValueError("V01 panel requires its actual source qualifier")
    def load(path):
        p = root / path
        return json.loads(p.read_text()), hashlib.sha256(p.read_bytes()).hexdigest()
    manifest, _ = load(q["manifest_path"])
    source, source_hash = load(manifest["source_qualification"]["path"])
    if source_hash != manifest["source_qualification"]["sha256"] or not manifest["bindings"]:
        raise ValueError("source qualification or manifest changed")
    for item in manifest["bindings"]:
        p = root / item["path"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"source binding changed: {item['path']}")
    if contract["data"]["sha256"] != manifest["panel_sha256"]:
        raise ValueError("panel differs from source manifest")
    assets = contract["universe"]["assets"]
    if assets != manifest["assets"] or len(payload["bars"]) != manifest["panel_rows"]:
        raise ValueError("panel assets or rows differ from verified assembly")
    if not set(assets) <= set(source["products"]):
        raise ValueError("source qualification omits an ETF")
    from .definitions import economic_index
    import pandas as pd
    actions, actions_hash = load(manifest["economic_actions"]["path"])
    if actions_hash != manifest["economic_actions"]["sha256"] or manifest["economic_actions"].get("effective_date_field") != "close_effective_date":
        raise ValueError("economic action binding or effective date mapping changed")
    if manifest["economic_actions"].get("historical_available_at") is not None or not manifest["economic_actions"].get("mathematical_reconstruction_assumption"):
        raise ValueError("unknown historical action arrival must remain explicitly unclaimed")
    max_error = 0.0
    for asset in assets:
        info = source["products"][asset]
        if info["field_difference_count"] or not info["qualification"].startswith("historical_volume_ratio_candidate"):
            raise ValueError(f"unqualified raw volume: {asset}")
        if len([r for r in payload["bars"] if r["asset"] == asset]) != info["nominal_rows"]:
            raise ValueError(f"panel length differs from qualified nominal source: {asset}")
        nominal_path = root / info["nominal_path"]
        if nominal_path.suffix == ".parquet":
            raw = pd.read_parquet(nominal_path)
            if not isinstance(raw.index, pd.DatetimeIndex):
                raw.index = pd.DatetimeIndex(raw.index)
        else:
            raw = pd.read_csv(nominal_path, parse_dates=["date"]).set_index("date")
        actual = [r for r in payload["bars"] if r["asset"] == asset]
        dates = pd.DatetimeIndex([r["date"] for r in actual])
        if not raw.index.is_unique or not dates.isin(raw.index).all():
            raise ValueError(f"nominal quotes do not cover panel: {asset}")
        raw = raw.loc[dates]
        for i, row in enumerate(actual):
            if row.get("volume_source_known") is not True or not math.isclose(float(row.get("volume", float("nan"))), float(raw["volume"].iloc[i]), rel_tol=0, abs_tol=1e-6):
                raise ValueError(f"panel volume differs from raw-checked nominal source: {asset}|{row['date']}")
            expected_break = asset == "510500.SS" and row["date"] == "2022-08-29"
            if row.get("volume_break") is not expected_break:
                raise ValueError(f"volume unit break marker differs: {asset}|{row['date']}")
        if (info["unknown_split_crossing_rows"] != (19 if asset == "510500.SS" else 0)):
            raise ValueError(f"unexpected source split-crossing qualification: {asset}")
        mapped = []
        for event in actions["included"]:
            if event["symbol"] != asset:
                continue
            day = event["close_effective_date"]
            # This is an explicit retrospective mathematical assumption, not
            # an assertion about historical announcement/arrival time.
            entry = {"event_id": event["event_id"], "type": event["type"],
                     "effective_date": day, "available_at": day + "T00:00:00+08:00"}
            entry.update({"cash": event["cash"]} if event["type"] == "cash_dividend" else
                         {"ratio": event["ratio"]} if event["type"] == "split" else {})
            mapped.append(entry)
        economic = economic_index(raw["close"], mapped)
        by_day = {}
        for event in mapped:
            by_day.setdefault(event["effective_date"], []).append(event)
        for i, row in enumerate(actual):
            d = row["date"]
            day_actions = sorted(by_day.get(d, []), key=lambda e: (e["effective_date"], e["event_id"]))
            mult, cash = 1.0, 0.0
            for event in reversed(day_actions):
                if event["type"] == "split":
                    mult *= float(event["ratio"])
                    cash *= float(event["ratio"])
                else:
                    cash += float(event["cash"])
            factor = 1.0 / float(raw["close"].iloc[0]) if i == 0 else float(economic.iloc[i-1]) / float(raw["close"].iloc[i-1])
            for field in ("open", "high", "low", "close"):
                expected = (float(raw[field].iloc[i]) * mult + cash) * factor
                error = abs(expected - float(row[field]))
                max_error = max(max_error, error)
                if not math.isclose(expected, float(row[field]), rel_tol=1e-10, abs_tol=1e-12):
                    raise ValueError(f"economic {field} differs from nominal/action reconstruction: {asset}|{d}")
            if not math.isclose(float(economic.iloc[i]), float(row["close"]), rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(f"economic close differs from formal economic_index: {asset}|{d}")
    _validate(payload, contract)
    return {"quality": {"request_satisfied": True, "assets": assets,
                        "raw_response_field_differences": 0,
                        "economic_ohlc_max_absolute_difference": max_error},
            "warnings": ["逐行原响应与名义报价/行动重算只支持回顾性经济价格和单ETF量比；行动历史到达时间与绝对成交量单位未认证。"]}


def _known_price(row):
    return (row.get("status") == "quoted" and row.get("action_known") is True and
            all(shared._number(row.get(k)) for k in ("open", "high", "low", "close")) and
            row["low"] <= min(row["open"], row["close"]) <= max(row["open"], row["close"]) <= row["high"])


def _known_volume(row):
    v = row.get("volume")
    return (row.get("volume_source_known") is True and isinstance(v, (int, float)) and
            not isinstance(v, bool) and math.isfinite(v) and v > 0)


def _validate(payload, contract):
    f = contract["feature"]
    if (f.get("kind") != "volume_anomaly_information" or f.get("definition_ref") != DEFINITION_REF or
        f.get("lookback") != LOOKBACK or f.get("warmup") != WARMUP or f.get("missing_policy") != "segmented"):
        raise ValueError("V01 requires exact research card, inclusive volume20 and real OHLC252")
    if payload.get("price_series") != "economic_price" and payload.get("data_mode") != "synthetic":
        raise ValueError("V01 requires a certified economic-price panel")
    calendar = payload["calendar"]
    if not isinstance(calendar, list) or not calendar or calendar != sorted(set(calendar)):
        raise ValueError("calendar must be ordered unique dates")
    for d in calendar:
        shared._date(d)
    assets = contract["universe"]["assets"]
    if not isinstance(assets, list) or not assets or len(set(assets)) != len(assets):
        raise ValueError("assets must be ordered unique codes")
    by_key = {}
    for row in payload["bars"]:
        d = row["date"]
        shared._date(d)
        if d not in calendar or row["asset"] not in assets or row["status"] not in shared.STATUSES:
            raise ValueError("row outside calendar/universe or bad status")
        key = row["asset"], d
        if key in by_key:
            raise ValueError("duplicate asset-date")
        if row["status"] != "quoted" and any(row.get(k) is not None for k in ("open", "high", "low", "close", "volume")):
            raise ValueError("nonquoted row carries OHLC or volume")
        if row["status"] == "quoted":
            if any(row.get(k) is not None and not shared._number(row[k]) for k in ("open", "high", "low", "close")):
                raise ValueError("invalid economic OHLC")
            if _known_price(row) and "decision_at" in row:
                if shared._available(row["decision_at"]).date() < shared._date(d):
                    raise ValueError("close used before session date")
                if shared._available(row["decision_at"]).date() == shared._date(d) and shared._available(row["decision_at"]).hour < 15:
                    raise ValueError("close used before session end")
        by_key[key] = row
    target = contract["target"]
    if (target.get("kind") != "downside_event" or target.get("start_offset") != 1 or
        target.get("end_offset") != 21 or target.get("entry_field") != "close" or
        target.get("threshold") != 5 or target.get("price_measure", "economic_price") != "economic_price"):
        raise ValueError("V01 freezes t+1 to t+21 close and a 5% loss event")
    if contract["question"].get("sampling") != "daily":
        raise ValueError("V01 keeps all daily observations")
    return calendar, assets, by_key


def prepare_volume_observations(payload: dict, contract: dict, *, compute_labels: bool = True) -> dict:
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    first, last = contract["question"]["period"]
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    index_of = {d: i for i, d in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset_number, asset in enumerate(assets):
        rows = [dict(by_key.get((asset, d), {"asset": asset, "date": d, "status": "vendor_missing"})) for d in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        closes, volumes = [], []
        counts = Counter()
        for row in rows:
            d = row["date"]
            if d > available_end:
                break
            if _known_price(row):
                closes.append(float(row["close"]))
            else:
                closes = []
                counts["price_reset_rows"] += 1
            if row.get("volume_break") is True:
                volumes = []
                counts["volume_reset_rows"] += 1
            if not _known_volume(row):
                volumes = []
                counts["volume_reset_rows"] += 1
            else:
                volumes.append(float(row["volume"]))
            ratio = sum(volumes[-LOOKBACK:]) / LOOKBACK if len(volumes) >= LOOKBACK else None
            ratio = volumes[-1] / ratio if ratio and ratio > 0 else None
            ready = len(closes) >= WARMUP
            if d not in selected or not first <= d <= last:
                continue
            vol20 = (statistics.stdev([math.log(closes[i] / closes[i-1]) for i in range(len(closes)-20, len(closes))]) * math.sqrt(252) * 100
                     if ready else None)
            r1 = 100 * (closes[-1] / closes[-2] - 1) if ready else None
            price_up = r1 >= 0 if r1 is not None else None
            r1_group = (0 if r1 < -1 else 1 if r1 < 0 else 2 if r1 < 1 else 3) if r1 is not None else None
            volatility_high = vol20 >= 20 if vol20 is not None else None
            trend_up = sum(closes[-60:]) > sum(closes[-65:-5]) if ready else None
            state = (asset_number * 16 + r1_group * 4 + int(volatility_high) * 2 + int(trend_up)
                     if ready else None)
            anomaly = float(ratio >= 2) if ratio is not None else None
            features = {"existing_state": state, "added": anomaly, "volume_ratio20": ratio,
                        "r1": r1, "r1_group": r1_group, "price_up": price_up,
                        "vol20": vol20, "vol20_ge_20": volatility_high,
                        "sma60_up": trend_up, "asset_indicator": asset_number}
            y, label_end, label_reason = (shared._label(label_rows, index_of[d], contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            eligible = bool(ready and anomaly is not None and (y is not None if compute_labels else True))
            feature_reason = "continuous252_or_economic_price_missing" if not ready else "volume_unknown" if anomaly is None else None
            observations.append({"id": f"{asset}|{d}", "asset": asset, "date": d,
                "stratum": f"{asset}|{d[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": feature_reason or label_reason, "feature_reason": feature_reason,
                "tested_condition": anomaly, "volume_group": "unknown" if anomaly is None else "abnormal" if anomaly else "ordinary",
                "background": state, "continuous_real_ohlc": len(closes), "continuous_volume": len(volumes),
                "ready_252": ready, "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["abnormal"] += int(ready and anomaly == 1)
            counts["ordinary"] += int(ready and anomaly == 0)
            counts["unknown"] += int(ready and anomaly is None)
            counts["eligible"] += int(eligible)
        per_asset[asset] = dict(counts)
    coverage = {k: sum(v.get(k, 0) for v in per_asset.values()) for k in
                ("observations", "ready_252", "abnormal", "ordinary", "unknown", "eligible", "price_reset_rows", "volume_reset_rows")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["全天成交量仅收盘后已知；未知量比保留为未知。背景含同ETF、当天涨跌四组、20日波动和60日均线方向。"]}
