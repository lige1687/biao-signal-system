"""Past-only and source-bound checks for the SMA60 slope-change adapter."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import trend_slope_change_information as trend


def fixture(n=320):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(days):
        c = 100 + .12 * i + 3 * math.sin(i / 8)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": c, "high": c + 1, "low": c - 1, "close": c,
                     "volume": 10000, "action_known": True})
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": "slope_change_information", "definition_ref": trend.DEFINITION_REF,
                            "lookback": 60, "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "price_measure": "economic_price"},
                "question": {"sampling": "daily", "period": [days[0], days[-1]]},
                "universe": {"assets": ["synthetic-A"]}}
    return payload, contract


def test_order_units_and_future_isolation(monkeypatch):
    payload, contract = fixture()
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *a, **k: pytest.fail("future label touched"))
    rows = trend.prepare_slope_observations(payload, contract)["observations"]
    assert list(trend.BASELINE_FEATURES) == ["r1", "ret3", "ret20", "vol20", "slope60",
                                            "ema20_distance", "sma60_atr_distance",
                                            "asset_510050", "asset_510500", "asset_588000"]
    assert not rows[250]["ready_252"] and rows[251]["ready_252"]
    assert all(r["y"] is None and r["label_end"] is None for r in rows)
    close = [r["close"] for r in payload["bars"]]
    def sma(i):
        return sum(close[i-59:i+1]) / 60
    def slope(i):
        return 100 * 252/60 * math.log(sma(i) / sma(i-60))
    f = rows[270]["features"]
    assert f["slope60"] == pytest.approx(slope(270))
    assert f["added"] == pytest.approx(slope(270) - slope(250))
    assert list(f) == list(trend.BASELINE_FEATURES[:7]) + ["added"] + list(trend.BASELINE_FEATURES[7:])


def test_prefix_missing_and_scale_invariance():
    payload, contract = fixture()
    base = trend.prepare_slope_observations(payload, contract)["observations"]
    changed = deepcopy(payload)
    for key in ("open", "high", "low", "close"):
        changed["bars"][290][key] *= 2
    after = trend.prepare_slope_observations(changed, contract)["observations"]
    assert base[:290] == after[:290]
    truncated = deepcopy(payload)
    truncated["calendar"] = truncated["calendar"][:280]
    truncated["bars"] = truncated["bars"][:280]
    truncated_contract = deepcopy(contract)
    truncated_contract["question"]["period"][1] = truncated["calendar"][-1]
    assert base[:280] == trend.prepare_slope_observations(truncated, truncated_contract)["observations"]
    scaled = deepcopy(payload)
    for bar in scaled["bars"]:
        for key in ("open", "high", "low", "close"):
            bar[key] *= 7
    scaled_rows = trend.prepare_slope_observations(scaled, contract)["observations"]
    for i in (251, 270, 300):
        for key in (*trend.BASELINE_FEATURES, "added"):
            assert scaled_rows[i]["features"][key] == pytest.approx(base[i]["features"][key])
    missing = deepcopy(payload)
    missing["bars"][275] = {"asset": "synthetic-A", "date": payload["calendar"][275],
                            "status": "vendor_missing", "action_known": False}
    missed = trend.prepare_slope_observations(missing, contract)["observations"]
    assert missed[275]["feature_reason"] == "continuous252_or_indicator_missing"
    assert missed[-1]["ready_252"] is False


def test_real_label_permission_and_synthetic_target_start():
    payload, contract = fixture()
    rows = trend.prepare_slope_observations(payload, contract, compute_labels=True)["observations"]
    c = [b["close"] for b in payload["bars"]]
    assert rows[270]["y"] == pytest.approx(100 * (c[291] / c[271] - 1))
    assert rows[-1]["target_label_reason"] == "immature_label"
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["universe"]["assets"] = list(trend.ASSETS)
    contract["question"]["period"] = ["2022-01-04", "2026-06-30"]
    with pytest.raises(ValueError, match="authorization"):
        trend.prepare_slope_observations(payload, contract, compute_labels=True)


def test_complete_evaluator_interface_with_one_synthetic_fold():
    from lei_signal.research.workflow_evaluation import evaluate_observations
    payload, contract = fixture(700)
    rows = trend.prepare_slope_observations(payload, contract, compute_labels=True)["observations"]
    assert all(row["tested_condition"] in (True, False, None) for row in rows)
    assert any(row["tested_condition"] is True for row in rows)
    assert any(row["tested_condition"] is False for row in rows)
    contract["target"]["unit"] = "percentage_point"
    contract.update(
        calendar=payload["calendar"],
        split={"label_policy": "purge", "evaluation_label_policy": "contained",
               "folds": [{"train_end": "2023-12-31", "eval_start": "2024-01-01", "eval_end": "2024-11-30"}]},
        weights={"policy": "equal_asset", "comparison": "fixed_common"},
        training_weights="equal_asset",
        dependence={"block_length": 20, "draws": 20, "seed": 1},
        evaluator={"kind": "prediction_ols", "version": "1.0.0", "lambda": 0,
                   "rcond": 1e-12, "baseline_features": list(trend.BASELINE_FEATURES),
                   "added_features": ["added"]},
    )
    result = evaluate_observations(rows, contract)
    assert result["execution"]["fits"] == 2  # synthetic B1 and B2 only
    assert result["predictions"]
