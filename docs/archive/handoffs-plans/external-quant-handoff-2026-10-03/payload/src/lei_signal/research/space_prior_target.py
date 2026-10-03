"""Research-only, point-in-time upper-pivot distance features.

The caller supplies daily OHLC and confirmed pivots. This module neither
constructs forward labels nor implies an executable target or risk/reward rule.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

import pandas as pd

from lei_signal.domain.types import Pivot
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.research.a01_index_features import _Segment, WARMUP, _validate as _validate_a01
from lei_signal.research import workflow_inputs as shared
from lei_signal.rules.resistance_b1 import find_b1


def upper_target_features(
    pivots: Sequence[Pivot], *, as_of: date, close: float, atr20: float,
    previous_60_high: float, lookback_days: int = 730,
) -> dict[str, float | str | None]:
    """Return frozen S01 B1 and 60-prior-quote-high distances.

    The B1 finder enforces available_date <= as_of, high > close and the
    pivot-date lookback. The baseline may be negative and is never clipped.
    """
    if close <= 0 or atr20 <= 0:
        raise ValueError("close and ATR20 must be positive")
    if previous_60_high <= 0:
        raise ValueError("previous_60_high must be positive")
    b1 = find_b1(tuple(pivots), as_of=as_of, current_close=close,
                 lookback_days=lookback_days)
    distance = None if b1 is None else (b1.price - close) / atr20
    group = ("no_target" if distance is None else "le_1_atr" if distance <= 1
             else "gt_1_le_3_atr" if distance <= 3 else "gt_3_atr")
    return {
        "target_price": None if b1 is None else b1.price,
        "pivot_date": None if b1 is None else b1.pivot_date.isoformat(),
        "available_date": None if b1 is None else b1.available_date.isoformat(),
        "b1_distance_atr": distance,
        "b1_distance_pct": None if b1 is None else 100 * (b1.price - close) / close,
        "prior_60_high_distance_atr": (previous_60_high - close) / atr20,
        "distance_group": group,
    }


DEFINITION_REF = "research.space.prior_upper_pivot@1.0.0"


def _ready(row: dict) -> bool:
    return (row.get("status") == "quoted" and
            (row.get("action_known") is True or
             (row.get("provider_price_known") is True and
              row.get("price_series") == "provider_index_price")) and
            all(shared._number(row.get(field)) for field in ("open", "high", "low", "close")))


def _pivots_by_segment(rows: list[dict]) -> tuple[Pivot, ...]:
    """Build structures only within contiguous complete real-OHLC runs."""
    segments: list[list[dict]] = []
    current: list[dict] = []
    for row in rows:
        if _ready(row):
            current.append(row)
        else:
            if current:
                segments.append(current)
            current = []
    if current:
        segments.append(current)
    all_pivots: list[Pivot] = []
    for segment in segments:
        frame = pd.DataFrame({"high": [float(r["high"]) for r in segment],
                              "low": [float(r["low"]) for r in segment]},
                             index=pd.DatetimeIndex([r["date"] for r in segment]))
        all_pivots.extend(confirmed_pivots(frame, left=3, right=3))
    return tuple(all_pivots)


def prepare_space_observations(payload: dict, contract: dict, *, compute_labels: bool = True) -> dict:
    """Build all scheduled observations with point-in-time space features.

    With compute_labels=False this does not call the shared future-label
    function or compute outcome values. Full source history is loaded to build
    candidate pivots, then each observation only uses already confirmed ones.
    Eligibility then means feature support, not outcome maturity.
    """
    feature = contract["feature"]
    if (feature.get("kind") != "space_prior_target" or
        feature.get("definition_ref") != DEFINITION_REF or
        feature.get("lookback") != 60 or feature.get("warmup") != WARMUP or
        feature.get("missing_policy") != "segmented"):
        raise ValueError("space feature contract differs from frozen S01 definition")
    # Reuse A01's calendar, OHLC, target and as-of availability checks. Only
    # its feature identity is translated for that validator; the S01 contract
    # above remains authoritative and unchanged.
    validation_contract = {**contract, "feature": {
        **feature, "kind": "a01_signed_band", "definition_ref": "research.a01.signed_band@2.0.0"}}
    calendar, assets, by_key = _validate_a01(payload, validation_contract)
    available_end = max((d for _, d in by_key), default=calendar[0])
    if "decision_at" in payload:
        available_end = min(available_end, shared._available(payload["decision_at"]).date().isoformat())
    question = contract["question"]
    selected = shared._selected(calendar, available_end, question, payload)
    first, last = question["period"]
    index_of = {d: i for i, d in enumerate(calendar)}
    observations = []
    per_asset = {}
    for asset_number, asset in enumerate(assets):
        rows = [dict(by_key.get((asset, d), {"asset": asset, "date": d,
                      "status": "vendor_missing"})) for d in calendar]
        label_rows = [r for r in rows if r["date"] <= available_end]
        pivots = _pivots_by_segment(rows)
        segment = _Segment()
        highs: list[float] = []
        active, episode = False, 0
        counts = {"raw": sum((asset, d) in by_key for d in calendar),
                  "observations": 0, "ready_252": 0, "trend_qualified": 0,
                  "target_available": 0, "eligible": 0}
        for row in rows:
            d = row["date"]
            if d > available_end:
                break
            if _ready(row):
                close, high, low = (float(row[k]) for k in ("close", "high", "low"))
                previous_high = max(highs[-60:]) if len(highs) >= 60 else None
                segment.push(close, high, low)
                highs.append(high)
                base, _, trend = segment.features(asset_number)
            else:
                segment, highs = _Segment(), []
                close = previous_high = None
                base, trend = {}, False
            ready_252 = len(segment.closes) >= WARMUP and segment.atr is not None and segment.atr > 0
            cutoff = (date.fromisoformat(d) - timedelta(days=730)).isoformat()
            # A full calendar-covered 730-day window is required, not merely
            # a 252-quote seed. A missing OHLC anywhere in it invalidates S01.
            # Three preceding quotes are needed to verify a candidate pivot
            # at the first in-window bar (the pivot's left-side comparison).
            in_window_start = next((j for j, x in enumerate(calendar) if x >= cutoff), len(calendar))
            window_quotes = index_of[d] - in_window_start + 1
            history_730 = bool(calendar[0] <= cutoff and in_window_start >= 3 and
                               segment.closes and
                               len(segment.closes) >= window_quotes + 3)
            ready = bool(ready_252 and history_730)
            up = bool(ready and trend)
            if up and not active:
                episode += 1
            active = up
            if d not in selected or not first <= d <= last:
                continue
            target = (upper_target_features(pivots, as_of=date.fromisoformat(d),
                      close=close, atr20=segment.atr, previous_60_high=previous_high,
                      lookback_days=730) if ready and previous_high is not None else None)
            features = {"asset_indicator": asset_number,
                        "prior_high60_atr": None if target is None else target["prior_60_high_distance_atr"],
                        "ret20": base.get("ret20"), "vol20": base.get("vol20"),
                        "distance60_atr": base.get("added"),
                        "added": None if target is None else target["b1_distance_atr"]}
            target_available = bool(target and target["target_price"] is not None)
            feature_reason = ("continuous252_or_price_missing" if not ready_252 else
                              "incomplete_730_day_history" if not history_730 else
                              "sma60_not_up" if not up else
                              "no_confirmed_upper_target" if not target_available else None)
            y, label_end, label_reason = (shared._label(label_rows, index_of[d], contract["target"])
                                          if compute_labels else (None, None, "not_computed"))
            eligible = bool(up and target_available and (y is not None if compute_labels else True))
            counts["observations"] += 1
            counts["ready_252"] += int(ready_252)
            counts["trend_qualified"] += int(up)
            counts["target_available"] += int(up and target_available)
            counts["eligible"] += int(eligible)
            observations.append({"id": f"{asset}|{d}", "asset": asset, "date": d,
                "stratum": f"{asset}|{d[:4]}", "features": features, "eligible": eligible,
                "y": y, "label_end": label_end, "target_label_reason": label_reason,
                "label_reason": feature_reason or label_reason, "feature_reason": feature_reason,
                "trend_qualified": up, "target_available": target_available,
                "distance_group": target["distance_group"] if target else "feature_not_ready",
                "episode_id": f"{asset}-{episode}" if up else None,
                "tested_condition": None, "continuous_real_ohlc": len(segment.closes),
                "ready_252": ready_252, "history_730": history_730,
                "close": close, "atr20": segment.atr,
                "target_price": target["target_price"] if target else None,
                "pivot_date": target["pivot_date"] if target else None,
                "available_date": target["available_date"] if target else None,
                "b1_distance_pct": target["b1_distance_pct"] if target else None,
                "previous_60_high": previous_high,
                "definition_ref": DEFINITION_REF})
        per_asset[asset] = counts
    coverage = {k: sum(v[k] for v in per_asset.values()) for k in
                ("raw", "observations", "ready_252", "trend_qualified", "target_available", "eligible")}
    coverage.update(per_asset=per_asset, definition_ref=DEFINITION_REF)
    return {"observations": observations, "coverage": coverage,
            "warnings": ["供应商指数点位只可做历史价格研究；目标缺失保留在机会母体。"]}
