"""Synthetic checks for the prior-top by dual-break research interaction."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import key_fluctuation_information as key
from lei_signal.research import prior_top_dual_break_information as combo
from lei_signal.research import top_invalidation_information as top


def fixture(n=650):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(days):
        close = 100 + .06 * i + 5 * math.sin(i / 7) + 1.2 * math.sin(i / 2.3)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": close, "high": close + 1, "low": close - 1,
                     "close": close, "action_known": True, "volume": 10000})
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": "prior_top_dual_break_information",
                            "definition_ref": combo.DEFINITION_REF, "lookback": 60,
                            "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "path_field": "close",
                           "price_measure": "economic_price"},
                "question": {"sampling": "daily", "period": [days[0], days[-1]]},
                "universe": {"assets": ["synthetic-A"]},
                "permissions": {"real_labels": False, "effect_authorized": False}}
    return payload, contract


def test_components_four_states_and_no_future_label(monkeypatch):
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *a, **k: pytest.fail("future label read"))
    payload, contract = fixture()
    rows = combo.prepare_combination_observations(payload, contract)["observations"]
    k_contract = combo._component_contract(contract, key=True)
    t_contract = combo._component_contract(contract, key=False)
    k_rows = key.prepare_key_observations(payload, k_contract)["observations"]
    t_rows = top.prepare_invalidation_observations(payload, t_contract)["observations"]
    assert list(combo.BASELINE_FEATURES) == ["r1", "ret3", "ret20", "vol20",
        "ema20_distance", "prior_top_active", "dual_break", "asset_510050",
        "asset_510500", "asset_588000"]
    assert not rows[250]["ready_252"] and rows[251]["ready_252"]
    assert all(r["y"] is None and r["label_end"] is None for r in rows)
    for r, k, t in zip(rows, k_rows, t_rows):
        assert r["id"] == k["id"] == t["id"]
        if r["ready_252"]:
            expected_t = t["active_before_today"] and t["tested_condition"] is False
            expected_k = k["critical_down20"]
            assert r["prior_top_active"] is expected_t
            assert r["dual_break"] is expected_k
            assert r["features"]["added"] == int(expected_t and expected_k)
            assert r["state"] == f"{int(expected_t)}{int(expected_k)}"
            assert r["features"]["ema20_distance"] == pytest.approx(k["ema20_distance"])
    assert {r["state"] for r in rows if r["eligible"]} >= {"00", "10", "11"}
    # A high above the still-known reference retires T, while the close can
    # remain below both K thresholds: retain the otherwise sparse 01 cell.
    focal = next(i for i, r in enumerate(rows) if r["eligible"] and r["state"] == "11")
    modified = deepcopy(payload)
    modified["bars"][focal]["high"] = max(modified["bars"][focal]["high"],
                                            rows[focal]["top_reference_price"] + .01)
    changed = combo.prepare_combination_observations(modified, contract)["observations"]
    assert changed[focal]["state"] == "01"


def test_top_previous_close_invalidation_replacement_and_prefix():
    payload, contract = fixture(350)
    for i in range(255, 267):
        h, l, c = [(110, 108, 109), (109, 107, 108), (108, 106, 107),
                   (109, 106, 108), (110, 108, 109), (112, 110, 111),
                   (111, 109, 110), (110, 108, 109), (111, 109, 110),
                   (112, 110, 111), (113, 111, 112), (112, 110, 111)][i - 255]
        payload["bars"][i].update(open=c, high=h, low=l, close=c)
    rows = combo.prepare_combination_observations(payload, contract)["observations"]
    assert rows[258]["prior_top_active"] is True
    assert rows[258]["top_confirmed_date"] == payload["calendar"][257]
    assert rows[259]["prior_top_active"] is True  # equal reference high
    assert rows[260]["top_invalidated_today"] is True
    assert rows[260]["prior_top_active"] is False  # strictly greater retires first
    assert rows[261]["prior_top_active"] is False  # no revival
    assert rows[262]["prior_top_active"] is False  # replacement confirmed today
    assert rows[263]["prior_top_active"] is True
    changed = deepcopy(payload)
    for field in ("open", "high", "low", "close"):
        changed["bars"][310][field] *= 2
    later = combo.prepare_combination_observations(changed, contract)["observations"]
    assert rows[:310] == later[:310]
    missing = deepcopy(payload)
    missing["bars"][275] = {"asset": "synthetic-A", "date": payload["calendar"][275],
                            "status": "vendor_missing", "action_known": False}
    missed = combo.prepare_combination_observations(missing, contract)["observations"]
    assert missed[275]["ready_252"] is False
    assert missed[276]["prior_top_active"] is None
    assert missed[-1]["ready_252"] is False


def test_real_label_permission_gate_and_synthetic_target():
    payload, contract = fixture()
    rows = combo.prepare_combination_observations(payload, contract, compute_labels=True)["observations"]
    closes = [r["close"] for r in payload["bars"]]
    path = closes[301:322]
    assert rows[300]["y"] == pytest.approx(100 * max(0, 1 - min(path) / path[0]))
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["universe"]["assets"] = list(combo.ASSETS)
    contract["question"]["period"] = ["2022-01-04", "2026-06-30"]
    with pytest.raises(ValueError, match="authorization"):
        combo.prepare_combination_observations(payload, contract, compute_labels=True)


def test_optional_synthetic_labels_stop_at_declared_decision_time():
    payload, contract = fixture()
    payload["decision_at"] = payload["calendar"][420] + "T16:00:00+08:00"
    rows = combo.prepare_combination_observations(payload, contract, compute_labels=True)["observations"]
    assert rows[-1]["date"] == payload["calendar"][420]
    assert rows[390]["y"] is not None
    assert rows[410]["y"] is None
    assert rows[410]["target_label_reason"] == "immature_label"
