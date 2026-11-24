"""Causal and permission tests for the narrow top-invalidation adapter."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import top_invalidation_information as top


def fixture(n=700):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(days):
        c = 100 + .035 * i + 4 * math.sin(i / 8) + .7 * math.sin(i / 2.7)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": c, "high": c + 1.2, "low": c - 1.2, "close": c,
                     "volume": 10000, "action_known": True})
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": "simple_top_invalidation_information",
                            "definition_ref": top.DEFINITION_REF, "lookback": 60,
                            "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "forward_return", "start_offset": 1,
                           "end_offset": 21, "entry_field": "close",
                           "price_measure": "economic_price"},
                "question": {"sampling": "daily", "period": [days[0], days[-1]]},
                "universe": {"assets": ["synthetic-A"]}}
    return payload, contract


def test_default_no_future_and_production_context(monkeypatch):
    payload, contract = fixture()
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *a, **k: pytest.fail("future label touched"))
    rows = top.prepare_invalidation_observations(payload, contract)["observations"]
    assert len(rows) == 700
    assert all(r["y"] is None and r["label_end"] is None for r in rows)
    assert not rows[250]["ready_252"] and rows[251]["ready_252"]
    assert any(r["eligible"] and r["tested_condition"] is True for r in rows)
    assert any(r["eligible"] and r["tested_condition"] is False for r in rows)
    assert list(top.BASELINE_FEATURES) == ["r1", "ret3", "ret20", "vol20",
        "slope60", "ema20_distance", "prior_reference_distance", "age_log1p",
        "asset_510050", "asset_510500", "asset_588000"]
    close = [r["close"] for r in payload["bars"]]
    def sma(i):
        return sum(close[i - 59:i + 1]) / 60
    expected_slope = 100 * 252 / 60 * math.log(sma(300) / sma(240))
    assert rows[300]["features"]["slope60"] == pytest.approx(expected_slope)


def test_prefix_retirement_replacement_strict_boundary_and_missing():
    payload, contract = fixture(320)
    for i in range(255, 267):
        h, l, c = [(110, 108, 109), (109, 107, 108), (108, 106, 107),
                   (109, 106, 108), (110, 108, 109), (112, 110, 111),
                   (111, 109, 110), (110, 108, 109), (111, 109, 110),
                   (112, 110, 111), (113, 111, 112), (112, 110, 111)][i - 255]
        payload["bars"][i].update(open=c, high=h, low=l, close=c)
    for i in range(270, 276):
        h, l, c = [(120, 118, 119), (119, 117, 118), (118, 116, 117),
                   (117, 115, 116), (116, 114, 115), (118, 116, 117)][i - 270]
        payload["bars"][i].update(open=c, high=h, low=l, close=c)
    rows = top.prepare_invalidation_observations(payload, contract)["observations"]
    # Day 257 confirms reference 110; equality at 259 does not break it.
    # Day 260 retires it; day 262 confirms a new reference 112. That top
    # remains at equality on 264, retires at 265, and neither old top revives.
    assert rows[258]["active_before_today"] and rows[258]["tested_condition"] is False
    assert rows[259]["tested_condition"] is False
    assert rows[260]["tested_condition"] is True
    assert rows[261]["active_before_today"] is False
    assert rows[262]["active_before_today"] is False
    assert rows[263]["confirmed_date"] == payload["bars"][262]["date"]
    assert rows[263]["reference_price"] == 112
    assert rows[264]["tested_condition"] is False
    assert rows[265]["tested_condition"] is True
    assert rows[266]["active_before_today"] is False
    # A newly confirmed, lower simple top replaces the still-valid older one.
    assert rows[275]["reference_price"] == 118
    assert rows[275]["tested_condition"] is False
    changed = deepcopy(payload)
    for key in ("open", "high", "low", "close"):
        changed["bars"][300][key] *= 2
    later = top.prepare_invalidation_observations(changed, contract)["observations"]
    assert later[:300] == rows[:300]
    missing = deepcopy(payload)
    missing["bars"][275] = {"asset": "synthetic-A", "date": payload["calendar"][275],
                            "status": "vendor_missing", "action_known": False}
    missed = top.prepare_invalidation_observations(missing, contract)["observations"]
    assert missed[275]["active_before_today"] is False
    assert missed[276]["active_before_today"] is False
    assert missed[-1]["ready_252"] is False
    scaled = deepcopy(payload)
    for r in scaled["bars"]:
        for k in ("open", "high", "low", "close"):
            r[k] *= 7
    scale_rows = top.prepare_invalidation_observations(scaled, contract)["observations"]
    for i in (258, 270, 300):
        assert scale_rows[i]["tested_condition"] == rows[i]["tested_condition"]
        for k in top.BASELINE_FEATURES:
            assert scale_rows[i]["features"][k] == pytest.approx(rows[i]["features"][k])


def test_label_permission_and_complete_synthetic_evaluator():
    from lei_signal.research.workflow_evaluation import evaluate_observations
    payload, contract = fixture()
    rows = top.prepare_invalidation_observations(payload, contract, compute_labels=True)["observations"]
    close = [r["close"] for r in payload["bars"]]
    assert rows[300]["y"] == pytest.approx(100 * (close[321] / close[301] - 1))
    # Four distinct synthetic histories make the frozen identity columns and
    # context rank check meaningful; no real ETF or effect data is involved.
    original = deepcopy(payload["bars"])
    payload["bars"] = []
    for j, asset in enumerate(top.ASSETS):
        for i, source in enumerate(original):
            row = dict(source)
            move = 1.7 * math.sin(i / (6.2 + j)) + .4 * math.sin(i * (1.13 + .07 * j))
            row.update(asset=asset, open=row["open"] + move,
                       high=row["high"] + move, low=row["low"] + move,
                       close=row["close"] + move)
            payload["bars"].append(row)
    contract["universe"]["assets"] = list(top.ASSETS)
    rows = top.prepare_invalidation_observations(payload, contract, compute_labels=True)["observations"]
    contract["target"]["unit"] = "percentage_point"
    contract.update(
        calendar=payload["calendar"],
        split={"label_policy": "purge", "evaluation_label_policy": "contained",
               "folds": [{"train_end": "2023-12-31", "eval_start": "2024-01-01", "eval_end": "2024-11-30"}]},
        weights={"policy": "equal_asset", "comparison": "fixed_common"},
        training_weights="equal_asset",
        dependence={"block_length": 20, "draws": 20, "seed": 1},
        evaluator={"kind": "prediction_ols", "version": "1.0.0", "lambda": 0,
                   "rcond": 1e-12, "baseline_features": list(top.BASELINE_FEATURES),
                   "added_features": ["added"]},
    )
    result = evaluate_observations(rows, contract)
    assert result["execution"]["fits"] == 2
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["question"]["period"] = ["2022-01-04", "2026-06-30"]
    with pytest.raises(ValueError, match="authorization"):
        top.prepare_invalidation_observations(payload, contract, compute_labels=True)
