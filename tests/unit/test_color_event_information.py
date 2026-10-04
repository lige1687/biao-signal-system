"""Causal identity checks for the bounded daily color transition adapter."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

from lei_signal.research.color_event_information import DEFINITION_REFS, prepare_observations


def _fixture(color):
    days, day = [], date(2020, 1, 2)
    while len(days) < 1200:
        if day.weekday() < 5:
            days.append(day.isoformat())
        day += timedelta(days=1)
    bars = []
    for j, asset in enumerate(("synthetic-A", "synthetic-B")):
        for i, d in enumerate(days):
            close = 120 + j + 0.025 * i + 8 * math.sin(i / 7) + 5 * math.sin(i / 2.3)
            bars.append({"asset": asset, "date": d, "status": "quoted", "close": close,
                         "open": close, "high": close * 1.01, "low": close - 0.8,
                         "action_known": True, "volume": 100.0})
    contract = {"feature": {"kind": "color_event_information", "lookback": 20,
                            "warmup": 252, "week_warmup": 120,
                            "week_policy": "previous_iso_week_only", "missing_policy": "segmented",
                            "event_color": color, "definition_ref": DEFINITION_REFS[color]},
                "question": {"sampling": "event", "factor_refs": [DEFINITION_REFS[color]],
                             "period": [days[0], days[-1]]},
                "target": {"kind": "forward_return", "start_offset": 1,
                           "end_offset": 21, "entry_field": "close", "path_field": "close",
                           "price_measure": "economic_price"},
                "universe": {"assets": ["synthetic-A", "synthetic-B"]}}
    return {"data_mode": "synthetic", "calendar": days, "bars": bars}, contract


def test_both_colors_have_adjacent_events_and_no_future_feature_dependence():
    for color in ("green", "black"):
        payload, contract = _fixture(color)
        full = prepare_observations(payload, contract)["observations"]
        eligible = [r for r in full if r["eligible"]]
        assert len(eligible) >= 20
        assert all(r["color20"] == color and r["prior_color20"] != color for r in eligible)
        assert all(r["last_completed_week_date"] < r["date"] for r in eligible)
        cutoff = payload["calendar"][1049]
        truncated = {**payload, "bars": [r for r in payload["bars"] if r["date"] <= cutoff]}
        shorter = prepare_observations(truncated, contract)["observations"]
        expected = {r["id"]: (r["features"], r["eligible"]) for r in full if r["date"] <= cutoff}
        found = {r["id"]: (r["features"], r["eligible"]) for r in shorter if r["date"] <= cutoff}
        assert found == expected


def test_missing_previous_quote_never_creates_an_event():
    payload, contract = _fixture("black")
    eligible = [r for r in prepare_observations(payload, contract)["observations"] if r["eligible"]]
    event = eligible[0]
    days = payload["calendar"]
    prior_date = days[days.index(event["date"]) - 1]
    changed = deepcopy(payload)
    for bar in changed["bars"]:
        if bar["asset"] == event["asset"] and bar["date"] == prior_date:
            bar["status"] = "vendor_missing"
            for field in ("open", "high", "low", "close"):
                bar[field] = None
            break
    new = {r["id"]: r for r in prepare_observations(changed, contract)["observations"]}
    assert not new[event["id"]]["eligible"]
    assert new[event["id"]]["feature_reason"] == "daily252_or_adjacent_missing"
