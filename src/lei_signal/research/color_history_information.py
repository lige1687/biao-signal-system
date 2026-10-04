"""Outcome-free, prefix-only daily colour history for descriptive research.

The segment identifiers mark consecutive descriptions, not independent samples.
All values refer to the close of the row's date; no later resolution is copied
back onto an earlier gray row.
"""
from __future__ import annotations

from collections import deque

import pandas as pd

from lei_signal.features.indicators import compute_features

from .technical_persistence_information import _segment_features
from .top_structure_information import _known

COLORS = ("black", "gray", "green")


def _side(close: float, ema: float, lag: float) -> str:
    """Describe gray geometry; equality is its own boundary, never a trend."""
    a = "above" if close > ema else "below" if close < ema else "equal"
    b = "above" if close > lag else "below" if close < lag else "equal"
    return f"ema_{a}__deduction_{b}"


def _known_segment(asset: str, segment: list[dict]) -> list[dict]:
    items = _segment_features(segment)
    frame = compute_features(pd.DataFrame(segment))
    result: list[dict] = []
    prior_color = prior_group = None
    color_start = group_start = None
    color_age = group_age = gray_age = 0
    gray_origin = None
    last_definite = None
    switches: deque[int] = deque(maxlen=20)
    for i, (bar, item) in enumerate(zip(segment, items)):
        day = bar["date"]
        ready = i + 1 >= 252 and item is not None and item["features"] is not None
        if not ready:
            result.append(_unknown(asset, day, "continuous252_or_indicator_missing", i + 1))
            continue
        close = float(bar["close"])
        e20, e60 = (float(frame[f"ema{k}"].iloc[i]) for k in (20, 60))
        s20, s60 = (float(frame[f"sma{k}"].iloc[i]) for k in (20, 60))
        lag20, lag60 = (float(frame[f"close_lag{k}"].iloc[i]) for k in (20, 60))
        color, color60 = item["color20"], item["color60"]
        group = ("bull" if min(s20, e20) > max(s60, e60) else
                 "bear" if max(s20, e20) < min(s60, e60) else "overlap")
        if color != prior_color:
            color_start, color_age = day, 1
        else:
            color_age += 1
        if group != prior_group:
            group_start, group_age = day, 1
        else:
            group_age += 1
        transition = f"{prior_color}->{color}" if prior_color is not None else None
        switches.append(int(prior_color is not None and prior_color != color))
        resolution = None
        if color == "gray":
            if prior_color != "gray":
                gray_origin, gray_age = last_definite, 1
            else:
                gray_age += 1
        else:
            if prior_color == "gray":
                resolution = f"{gray_origin or 'unknown'}-gray-{color}"
            gray_age = 0
            gray_origin = None
            last_definite = color
        if group == "bull":
            gap = min(s20, e20) - max(s60, e60)
        elif group == "bear":
            gap = max(s20, e20) - min(s60, e60)
        else:
            gap = 0.0
        values = item["features"]
        result.append({
            "id": f"{asset}|{day}", "asset": asset, "date": day,
            "ready_252": True, "continuous_real_ohlc": i + 1, "feature_reason": None,
            "color20": color, "color60": color60,
            "state20": _side(close, e20, lag20), "state60": _side(close, e60, lag60),
            "prior_color20": prior_color, "transition20": transition,
            "group": group, "bull_group": group == "bull", "bear_group": group == "bear",
            "group_run_id": f"{asset}|group|{group_start}", "group_run_age": group_age,
            "color_run_id": f"{asset}|color20|{color_start}", "color_run_age": color_age,
            "gray_origin": gray_origin if color == "gray" else None,
            "last_definite_color": last_definite,
            "gray_age": gray_age if color == "gray" else None,
            "gray_resolution_path": resolution,
            "distance_to_ema20": 100 * (close / e20 - 1),
            "distance_to_deduction20": values["ret20"],
            "sma20": s20, "ema20": e20, "sma60": s60, "ema60": e60,
            "deduction20": lag20, "deduction60": lag60,
            "groupgap_pct": 100 * gap / close,
            "ret20": values["ret20"], "ret60": values["ret60"], "vol20": values["vol20"],
            "switches20": sum(switches) if len(switches) == 20 else None,
        })
        prior_color, prior_group = color, group
    return result


def _unknown(asset: str, day: str, reason: str, continuous: int = 0) -> dict:
    return {"id": f"{asset}|{day}", "asset": asset, "date": day,
            "ready_252": False, "continuous_real_ohlc": continuous,
            "feature_reason": reason, "color20": None, "color60": None,
            "state20": None, "state60": None, "prior_color20": None,
            "transition20": None, "group": None, "bull_group": None,
            "bear_group": None, "group_run_id": None, "group_run_age": None,
            "color_run_id": None, "color_run_age": None, "gray_origin": None,
            "last_definite_color": None,
            "gray_age": None, "gray_resolution_path": None,
            "distance_to_ema20": None, "distance_to_deduction20": None,
            "sma20": None, "ema20": None, "sma60": None, "ema60": None,
            "deduction20": None, "deduction60": None,
            "groupgap_pct": None, "ret20": None, "ret60": None, "vol20": None,
            "switches20": None}


def history_rows(payload: dict) -> list[dict]:
    """Return every asset/calendar row, using only causal quoted OHLC prefixes.

    The input panel's calendar is authoritative. Missing or invalid daily OHLC
    breaks a segment. Unlike result labels, no later date is inspected for an
    individual row's features.
    """
    calendar = payload["calendar"]
    if calendar != sorted(set(calendar)):
        raise ValueError("calendar must be strictly increasing and unique")
    bars = payload["bars"]
    assets = payload.get("assets") or sorted({bar["asset"] for bar in bars})
    by_key = {}
    for bar in bars:
        key = bar["asset"], bar["date"]
        if key in by_key:
            raise ValueError(f"duplicate bar: {key}")
        by_key[key] = bar
    output = []
    for asset in assets:
        segment = []
        for day in calendar:
            bar = by_key.get((asset, day))
            if bar is not None and _known(bar):
                segment.append(bar)
                continue
            if segment:
                output.extend(_known_segment(asset, segment))
                segment = []
            output.append(_unknown(asset, day, "missing_or_invalid_quote"))
        if segment:
            output.extend(_known_segment(asset, segment))
    return sorted(output, key=lambda row: (row["asset"], row["date"]))
