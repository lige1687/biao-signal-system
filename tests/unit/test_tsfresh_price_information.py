"""Fixed formula, causal population and workflow bindings for two price expressions."""
from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import tsfresh_price_information as tsf


def fixture(n=325):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    prices = [100 * math.exp(.001 * i + .008 * math.sin(i / 5)) for i in range(n)]
    bars = [{"asset": "synthetic-A", "date": day, "status": "quoted", "open": c,
             "high": c + 1, "low": c - 1, "close": c, "volume": 10000,
             "action_known": True} for day, c in zip(days, prices)]
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": tsf.KIND, "definition_ref": tsf.DEFINITION_REFS[0],
                            "definition_refs": list(tsf.DEFINITION_REFS), "lookback": 20,
                            "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "price_measure": "economic_price"},
                "question": {"sampling": "daily", "period": [days[0], days[-1]]},
                "universe": {"assets": ["synthetic-A"]}}
    return payload, contract


def test_independent_21_close_hand_calculation_and_no_label_access(monkeypatch):
    payload, contract = fixture()
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *a, **kw: pytest.fail("future label accessed"))
    rows = tsf.prepare_tsfresh_observations(payload, contract)["observations"]
    assert not rows[250]["ready_252"] and rows[251]["ready_252"]
    assert all(row["y"] is None and row["label_end"] is None for row in rows)
    i = 275
    r = [100 * math.log(payload["bars"][j]["close"] / payload["bars"][j - 1]["close"])
         for j in range(i - 19, i + 1)]
    mean = sum(r) / 20
    var = sum((x - mean) ** 2 for x in r) / 20
    amplitude = sum(abs(x) for x in r) / 20
    ac = sum((r[j] - mean) * (r[j + 1] - mean) for j in range(19)) / (19 * var)
    assert rows[i]["features"]["mean_abs_log_change20"] == pytest.approx(amplitude, abs=1e-10)
    assert rows[i]["features"]["return_autocorrelation20_lag1"] == pytest.approx(ac, abs=1e-10)
    assert rows[i]["tested_condition"] is None
    assert rows[i]["definition_refs"] == list(tsf.DEFINITION_REFS)


def test_future_change_truncation_missing_reset_and_common_finite():
    payload, contract = fixture(540)
    base = tsf.prepare_tsfresh_observations(payload, contract)["observations"]
    changed = deepcopy(payload)
    for key in ("open", "high", "low", "close"):
        changed["bars"][400][key] *= 2
    after = tsf.prepare_tsfresh_observations(changed, contract)["observations"]
    assert base[:400] == after[:400]
    truncated = deepcopy(payload)
    truncated["calendar"] = truncated["calendar"][:380]
    truncated["bars"] = truncated["bars"][:380]
    short_contract = deepcopy(contract)
    short_contract["question"]["period"][1] = truncated["calendar"][-1]
    assert base[:380] == tsf.prepare_tsfresh_observations(truncated, short_contract)["observations"]
    missing = deepcopy(payload)
    missing["bars"][270] = {"asset": "synthetic-A", "date": payload["calendar"][270],
                            "status": "vendor_missing", "action_known": False}
    rows = tsf.prepare_tsfresh_observations(missing, contract)["observations"]
    assert all(not rows[i]["ready_252"] for i in range(270, 522))
    assert rows[522]["ready_252"]
    assert all(row["eligible"] == row["ready_252"] for row in rows)


def test_constant_returns_remain_unknown_for_both_comparisons():
    payload, contract = fixture()
    for i, bar in enumerate(payload["bars"]):
        c = 100 * math.exp(.001 * i)
        bar.update(open=c, high=c + 1, low=c - 1, close=c)
    rows = tsf.prepare_tsfresh_observations(payload, contract)["observations"]
    assert rows[270]["features"]["mean_abs_log_change20"] == pytest.approx(.1)
    assert rows[270]["features"]["return_autocorrelation20_lag1"] is None
    assert rows[270]["eligible"] is False
    assert rows[270]["feature_reason"] == "tsfresh_candidate_unknown"


def test_real_labels_need_both_permissions():
    payload, contract = fixture()
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["universe"]["assets"] = list(tsf.ASSETS)
    contract["question"]["period"] = ["2022-01-04", "2026-06-30"]
    with pytest.raises(ValueError, match="authorization"):
        tsf.prepare_tsfresh_observations(payload, contract, compute_labels=True)
    contract["permissions"] = {"real_labels": True}
    with pytest.raises(ValueError, match="authorization"):
        tsf.prepare_tsfresh_observations(payload, contract, compute_labels=True)


def test_cache_key_binds_calculator_and_license():
    from lei_signal.research.workflow import CODE_PATHS, cache_keys
    _, contract = fixture()
    contract.update(data={"sha256": "data"}, split={"folds": []},
                    evaluator={"kind": "prediction_ols"}, weights={}, dependence={})
    files = {name: name for name in CODE_PATHS}
    files.update({tsf.CALCULATOR_PATH: "calc1", tsf.LICENSE_PATH: "license1",
                  "src/lei_signal/research/tsfresh_price_information.py": "adapter1",
                  "src/lei_signal/research/trend_slope_change_information.py": "slope1"})
    bindings = {"files": files, "data_sha256": "data", "definition_closure": {}}
    base = cache_keys(contract, bindings)
    changed = deepcopy(bindings)
    changed["files"][tsf.CALCULATOR_PATH] = "calc2"
    assert cache_keys(contract, changed)["features"] != base["features"]
    changed = deepcopy(bindings)
    changed["files"][tsf.LICENSE_PATH] = "license2"
    assert cache_keys(contract, changed)["features"] != base["features"]
