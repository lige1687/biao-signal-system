"""Synthetic boundaries for confirmed, adjacent MA-layer pullback cycles."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import pullback_layer_change_information as pullback


def fixture(n=500):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(days):
        close = 100 + .3 * i + 4 * math.sin(i / 5)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "action_known": True, "open": close, "high": close + 1,
                     "low": close - 1, "close": close, "volume": 1000})
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": "pullback_layer_change_information",
                            "definition_ref": pullback.DEFINITION_REF, "lookback": 60,
                            "warmup": 252, "missing_policy": "segmented"},
                "question": {"sampling": "daily", "period": [days[0], days[-1]]},
                "universe": {"assets": ["synthetic-A"]},
                "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "path_field": "close",
                           "price_measure": "economic_price"}}
    return payload, contract


def test_rank_distinguishes_touch_from_strict_below_all():
    d = {"groups": {20: 110, 60: 100, 120: 90}, "min_all_six": 88}
    assert pullback._touch_rank(88, d)["rank"] == 3
    assert pullback._touch_rank(87.999, d)["rank"] == 4
    assert pullback._touch_rank(110, d)["rank"] == 1
    assert pullback._touch_rank(111, d)["rank"] == 0


def test_confirmed_events_use_prior_cycles_and_are_prefix_causal(monkeypatch):
    payload, contract = fixture()
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *a, **k: pytest.fail("future label read"))
    base = pullback.prepare_pullback_observations(payload, contract)
    assert len(base["observations"]) == 500
    assert base["coverage"]["ready_252"] == 249
    assert base["coverage"]["events"] >= 3
    for row in base["observations"]:
        assert row["y"] is None and row["label_end"] is None
        if row["features"]["added"] is not None:
            prior, current = row["previous_cycle"], row["current_cycle"]
            assert prior["low_confirm_date"] < current["low_confirm_date"] == row["date"]
            assert prior["road_id"] == current["road_id"] == row["road_id"]
            assert prior["low_center_index"] < current["high_center_index"] < current["low_center_index"]
            assert row["features"]["added"] == prior["level"] - current["level"]
    changed = deepcopy(payload)
    for key in ("open", "high", "low", "close"):
        changed["bars"][450][key] *= 1.2
    assert base["observations"][:450] == pullback.prepare_pullback_observations(changed, contract)["observations"][:450]
    shorter = deepcopy(payload)
    shorter["calendar"] = shorter["calendar"][:400]
    shorter["bars"] = shorter["bars"][:400]
    assert base["observations"][:400] == pullback.prepare_pullback_observations(shorter, contract)["observations"]


def test_missing_resets_and_same_center_conflict():
    payload, contract = fixture()
    missing = deepcopy(payload)
    missing["bars"][320] = {"asset": "synthetic-A", "date": payload["calendar"][320],
                            "status": "vendor_missing", "action_known": False}
    rows = pullback.prepare_pullback_observations(missing, contract)["observations"]
    assert rows[320]["event_reason"] == "missing_real_ohlc_reset"
    assert all(not r["ready_252"] for r in rows[320:])
    conflict = deepcopy(payload)
    conflict["bars"][350]["high"] = 1000
    conflict["bars"][350]["low"] = 1
    prepared = pullback.prepare_pullback_observations(conflict, contract)
    conflict_pivots = [p for p in prepared["pivots"] if p["center_index"] == 350]
    assert {p["kind"] for p in conflict_pivots} == {"high", "low"}
    assert all(p["status"] == "same_center_high_low_conflict" for p in conflict_pivots)


def test_unordered_middle_cycle_blocks_next_pair_without_skipping(monkeypatch):
    payload, contract = fixture()
    base = pullback.prepare_pullback_observations(payload, contract)
    assert len(base["cycles"]) >= 4
    middle = base["cycles"][2]
    affected = middle["high_center_index"] + 1
    original = pullback._segment_info
    def disrupt(segment, indices):
        info, pivots = original(segment, indices)
        if affected in info:
            info[affected]["ordered"] = False
        return info, pivots
    monkeypatch.setattr(pullback, "_segment_info", disrupt)
    after = pullback.prepare_pullback_observations(payload, contract)
    cycle = next(c for c in after["cycles"] if c["low_confirm_date"] == middle["low_confirm_date"])
    assert cycle["comparable"] is False and cycle["level"] is None
    next_cycle = next(c for c in after["cycles"] if c["low_confirm_date"] > middle["low_confirm_date"])
    row = next(r for r in after["observations"] if r["date"] == next_cycle["low_confirm_date"])
    assert row["event_reason"] == "previous_cycle_unordered"
    assert row["features"]["added"] is None


def test_real_future_labels_require_both_permissions():
    payload, contract = fixture()
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["universe"]["assets"] = list(pullback.ASSETS)
    contract["question"]["period"] = ["2022-01-04", "2026-06-30"]
    with pytest.raises(ValueError, match="authorization"):
        pullback.prepare_pullback_observations(payload, contract, compute_labels=True)
