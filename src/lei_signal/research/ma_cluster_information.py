"""Research-only six-line width on continuous, known index-price OHLC.

The width is a same-day cost-line description, not a complete consolidation
zone or a trading trigger. Qualification can run without reading future prices.
"""
from __future__ import annotations

from collections import Counter
from .a01_index_features import _Segment, _distance, _mean, _source_known, _validate as _validate_a01
from . import workflow_inputs as shared

DEFINITION_REF = "research.trend.ma_cluster_width@1.0.0"
PERIODS = (20, 60, 120)
WARMUP = 252


def _validate(payload: dict, contract: dict):
    feature = contract["feature"]
    if (feature.get("kind") != "ma_cluster_information" or
        feature.get("definition_ref") != DEFINITION_REF or
        feature.get("lookback") != 120 or feature.get("warmup") != WARMUP or
        feature.get("missing_policy") != "segmented"):
        raise ValueError("six-line research definition, N120 and segmented OHLC252 are required")
    if payload.get("price_series") != "provider_index_price" and payload.get("data_mode") != "synthetic":
        raise ValueError("research width requires declared provider index prices")
    validation = {**contract, "feature": {**feature, "kind": "a01_signed_band",
                                        "lookback": 60,
                                        "definition_ref": "research.a01.signed_band@2.0.0"}}
    return _validate_a01(payload, validation)


def prepare_ma_cluster_observations(payload: dict, contract: dict, *, compute_labels: bool = True) -> dict:
    """Preserve every complete-week observation; no outcome access when disabled."""
    calendar, assets, by_key = _validate(payload, contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    selected = shared._selected(calendar, available_end, contract["question"], payload)
    first, last = contract["question"]["period"]
    index_of = {d: i for i, d in enumerate(calendar)}
    observations, per_asset = [], {}
    for asset_number, asset in enumerate(assets):
        rows = [dict(by_key.get((asset, d), {"asset": asset, "date": d,
                      "status": "vendor_missing"})) for d in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end] if compute_labels else None
        segment = _Segment()
        active, episode = False, 0
        counts = Counter()
        for row in rows:
            d = row["date"]
            if d > available_end:
                break
            complete = (row["status"] == "quoted" and _source_known(row) and
                        all(shared._number(row.get(k)) for k in ("open", "high", "low", "close")))
            if complete:
                segment.push(float(row["close"]), float(row["high"]), float(row["low"]))
            else:
                segment = _Segment()
                counts["reset_rows"] += 1
            c = segment.closes
            width = None
            if len(c) >= 120 and all(segment.emas[n] is not None for n in PERIODS):
                lines = [_mean(c[-n:]) for n in PERIODS] + [segment.emas[n] for n in PERIODS]
                if min(lines) > 0:
                    width = max(lines) / min(lines) - 1
            ready = len(c) >= WARMUP and width is not None and segment.atr is not None and segment.atr > 0
            trend = bool(ready and _mean(c[-60:]) > _mean(c[-65:-5]))
            if trend and not active:
                episode += 1
            active = trend
            if d not in selected or not first <= d <= last:
                continue
            base = segment.features(asset_number)[0] if complete else {}
            features = {"asset_indicator": asset_number,
                        "ret20": base.get("ret20"), "vol20": base.get("vol20"),
                        "width": width, "added": None if width is None else 100 * width}
            for n in PERIODS:
                features[f"distance{n}_atr"] = None
                if ready:
                    features[f"distance{n}_atr"] = _distance(c[-1], _mean(c[-n:]),
                                                              segment.emas[n], segment.atr)[0]
            y, label_end, label_reason = (shared._label(label_rows, index_of[d], contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            eligible = bool(trend and (y is not None if compute_labels else True))
            reason = ("continuous252_or_price_missing" if not ready else
                      "sma60_not_up" if not trend else label_reason)
            group = ("lt_2pct" if width < .02 else "ge_2pct") if width is not None else "feature_not_ready"
            observations.append({"id": f"{asset}|{d}", "asset": asset, "date": d,
                "stratum": f"{asset}|{d[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": reason, "feature_reason": None if trend else reason,
                "trend_qualified": trend, "episode_id": f"{asset}-{episode}" if trend else None,
                "distance_group": group, "tested_condition": None,
                "continuous_real_ohlc": len(c), "ready_252": ready,
                "definition_ref": DEFINITION_REF})
            counts["observations"] += 1
            counts["ready_252"] += int(ready)
            counts["trend_qualified"] += int(trend)
            counts["eligible"] += int(eligible)
        per_asset[asset] = dict(counts)
    coverage = {k: sum(v.get(k, 0) for v in per_asset.values()) for k in
                ("observations", "ready_252", "trend_qualified", "eligible", "reset_rows")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["供应商指数点位只用于历史信息研究；六线宽度不是完整密集区，也不是交易触发。"]}
