"""Causal and label-boundary checks for the research-only green/black state."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pandas as pd
import pytest

from lei_signal.features.indicators import compute_features
from lei_signal.research import green_black_state_information as state


def fixture(n=380, target_kind="forward_return"):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(days):
        close = 100 + .10 * i + 5 * math.sin(i / 7)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted", "open": close,
                     "high": close + 1, "low": close - 1, "close": close,
                     "volume": 10000, "action_known": True})
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": "green_black_state60_information",
                            "definition_ref": state.DEFINITION_REF, "lookback": 60,
                            "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": target_kind, "start_offset": 1, "end_offset": 61,
                           "entry_field": "close", "price_measure": "economic_price",
                           **({"path_field": "close"} if target_kind == "mae" else {})},
                "question": {"sampling": "daily", "period": [days[0], days[-1]],
                             "factor_refs": [state.DEFINITION_REF]},
                "universe": {"assets": ["synthetic-A"]}}
    return payload, contract


def test_strict_color_and_production_ema():
    assert state._color(100, 100, 90) == "gray"
    assert state._color(100, 90, 100) == "gray"
    assert state._color(100, 90, 90) == "green"
    assert state._color(100, 110, 110) == "black"
    assert state._color(100, float("nan"), 90) is None
    payload, contract = fixture()
    rows = state.prepare_state_observations(payload, contract)["observations"]
    frame = compute_features(pd.DataFrame(payload["bars"]))
    for i in (251, 270, 320):
        close = float(frame["close"].iloc[i])
        for period in (20, 60):
            expected = state._color(close, float(frame[f"ema{period}"].iloc[i]),
                                    float(frame[f"close_lag{period}"].iloc[i]))
            assert rows[i][f"color{period}"] == expected
        previous_close = float(frame["close"].iloc[i - 1])
        previous60 = state._color(previous_close, float(frame["ema60"].iloc[i - 1]),
                                  float(frame["close_lag60"].iloc[i - 1]))
        assert rows[i]["first_color60"] == (rows[i]["color60"] != previous60)
        assert rows[i]["features"]["color20_green"] == int(rows[i]["color20"] == "green")
        assert rows[i]["features"]["color60_black"] == int(rows[i]["color60"] == "black")
    assert rows[250]["color60"] is None and not rows[250]["ready_252"]
    assert all(r["y"] is None and r["label_end"] is None for r in rows)


def test_gap_reset_and_prefix_invariance():
    payload, contract = fixture()
    base = state.prepare_state_observations(payload, contract)["observations"]
    changed = deepcopy(payload)
    changed["bars"][330]["close"] += 0.5
    assert base[:330] == state.prepare_state_observations(changed, contract)["observations"][:330]
    gap = deepcopy(payload)
    gap["bars"][275] = {"asset": "synthetic-A", "date": gap["calendar"][275],
                        "status": "vendor_missing", "action_known": False}
    rows = state.prepare_state_observations(gap, contract)["observations"]
    assert rows[275]["color60"] is None and rows[275]["eligible"] is False
    assert rows[276]["color60"] is None and rows[276]["first_color60"] is False
    assert rows[-1]["ready_252"] is False


def test_intraday_decision_excludes_unfinished_daily_close():
    payload, contract = fixture()
    payload['decision_at'] = payload['calendar'][270] + 'T14:59:00+08:00'
    rows = state.prepare_state_observations(payload, contract)['observations']
    assert rows[-1]['date'] == payload['calendar'][269]
    payload['decision_at'] = payload['calendar'][270] + 'T15:00:00+08:00'
    rows = state.prepare_state_observations(payload, contract)['observations']
    assert rows[-1]['date'] == payload['calendar'][270]


@pytest.mark.parametrize("kind", ["forward_return", "mae"])
def test_exact_close_path_label_and_real_authorization(kind):
    payload, contract = fixture(target_kind=kind)
    rows = state.prepare_state_observations(payload, contract, compute_labels=True)["observations"]
    closes = [b["close"] for b in payload["bars"]]
    expected = (100 * (closes[331] / closes[271] - 1) if kind == "forward_return"
                else max(0, 100 * (1 - min(closes[271:332]) / closes[271])))
    assert rows[270]["y"] == pytest.approx(expected)
    assert rows[270]["label_end"] == payload["calendar"][331]
    assert rows[-1]["target_label_reason"] == "immature_label"
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["universe"]["assets"] = list(state.ASSETS)
    contract["question"]["period"] = ["2022-01-04", "2026-06-30"]
    with pytest.raises(ValueError, match="authorization"):
        state.prepare_state_observations(payload, contract, compute_labels=True)
    contract["permissions"] = {"real_labels": True, "effect_authorized": True, "real_fits": 2}
    with pytest.raises(ValueError, match="four fits"):
        state.prepare_state_observations(payload, contract, compute_labels=True)


@pytest.mark.parametrize("kind", ["forward_return", "mae"])
def test_two_model_synthetic_rehearsal(kind):
    from lei_signal.research.workflow import run_rehearsal
    _, contract = fixture(target_kind=kind)
    contract["data"] = {"mode": "synthetic"}
    contract["target"]["unit"] = "percentage_point"
    contract["weights"] = {"policy": "equal_asset", "comparison": "fixed_common"}
    contract["training_weights"] = "equal_asset"
    contract["evaluator"] = {"kind": "prediction_ols", "version": "1.0.0", "lambda": 0,
                             "rcond": 1e-12, "baseline_features": list(state.BASELINE_FEATURES),
                             "added_features": list(state.ADDED_FEATURES)}
    result = run_rehearsal(contract)
    assert result["fits"] == 2 and result["performance"]
