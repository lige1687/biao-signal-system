"""D01 geometry, causality, missingness and fixed unpenalized evaluator."""
from __future__ import annotations

import copy
from datetime import date, timedelta
import math

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.deduction_box_information import prepare_deduction_observations
from lei_signal.research.workflow_evaluation import EvaluationError, _ols_design, _ols_fit
from lei_signal.research import workflow_evaluation
from lei_signal.research.question_contract import validate_workflow_contract
from pathlib import Path
import json


def _sample():
    dates = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(300)]
    bars = []
    for i, d in enumerate(dates):
        close = 100 + 0.03*i + 3*math.sin(i/7)
        bars.append({"asset": "synthetic-A", "date": d, "status": "quoted",
                     "open": close, "high": close+1, "low": close-1,
                     "close": close, "action_known": True})
    contract = {"feature": {"kind": "future_deduction_box_information",
               "definition_ref": "research.trend.future_deduction_box20_10@1.0.0",
               "lookback": 20, "box_horizon": 10, "warmup": 252,
               "missing_policy": "segmented"},
               "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                          "entry_field": "close", "path_field": "close",
                          "price_measure": "economic_price"},
               "question": {"sampling": "daily", "period": [dates[0], dates[-1]]},
               "universe": {"assets": ["synthetic-A"]}}
    return {"data_mode": "synthetic", "calendar": dates, "bars": bars}, contract


def test_box_exact_indices_and_prefix_causality():
    payload, contract = _sample()
    full = prepare_deduction_observations(payload, contract, compute_labels=False)
    r = full["observations"][260]
    closes = [b["close"] for b in payload["bars"]]
    assert r["box_top"] == max(closes[241:251])
    assert r["features"]["added"] == pytest.approx(100*(closes[260]/max(closes[241:251])-1))
    assert r["features"]["vol20"] == pytest.approx(
        np.std([closes[j]/closes[j-1]-1 for j in range(241, 261)], ddof=1)*np.sqrt(252)*100)
    altered = copy.deepcopy(payload)
    for bar in altered["bars"][261:]:
        bar["close"] *= 2
        bar["open"] *= 2
        bar["high"] *= 2
        bar["low"] *= 2
    later = prepare_deduction_observations(altered, contract, compute_labels=False)
    assert full["observations"][260]["features"] == later["observations"][260]["features"]
    assert all(row["y"] is None for row in later["observations"])
    assert r["tested_condition"] is None  # Continuous added field, not the background gate.


def test_gap_resets_and_duplicate_rejected():
    payload, contract = _sample()
    payload["bars"][260] = {"asset": "synthetic-A", "date": payload["calendar"][260],
                             "status": "vendor_missing", "open": None, "high": None,
                             "low": None, "close": None}
    result = prepare_deduction_observations(payload, contract, compute_labels=False)
    assert result["observations"][261]["features"]["added"] is None
    payload["bars"].append(copy.deepcopy(payload["bars"][10]))
    with pytest.raises(ValueError, match="duplicate"):
        prepare_deduction_observations(payload, contract, compute_labels=False)


def test_ols_duplicate_and_linear_combination_equivalent():
    train = pd.DataFrame([{"asset": "A", "features": {"x": float(i), "dup": float(i), "combo": float(2*i+3)},
                           "y": float(2*i + (i % 3))} for i in range(1, 12)])
    ev = pd.DataFrame([{"asset": "A", "features": {"x": float(i), "dup": float(i), "combo": float(2*i+3)}}
                       for i in range(12, 15)])
    base = _ols_design(train, ev, ["x"], "equal_asset")
    expected, _ = _ols_fit(train, base)
    for cols in (["x", "dup"], ["x", "combo"]):
        design = _ols_design(train, ev, cols, "equal_asset")
        actual, fit = _ols_fit(train, design)
        assert fit["rank"] == 1
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
    bad = copy.deepcopy(ev)
    bad.at[0, "features"] = {"x": 12., "dup": 13., "combo": 27.}
    with pytest.raises(EvaluationError, match="dependence"):
        _ols_design(train, bad, ["x", "dup"], "equal_asset")


def test_ols_zero_variance_is_zero_in_train_and_evaluation():
    train = pd.DataFrame([{"asset": "A", "features": {"x": float(i), "constant": 4.}, "y": float(i)}
                          for i in range(1, 8)])
    ev = pd.DataFrame([{"asset": "A", "features": {"x": 8., "constant": 999.}}])
    design = _ols_design(train, ev, ["x", "constant"], "equal_asset")
    pred, fit = _ols_fit(train, design)
    assert fit["zero_variance"] == ["constant"]
    assert design["ze"][0, 1] == 0
    assert pred[0] == pytest.approx(8)


def test_context_strict_ema_and_inclusive_lag20(monkeypatch):
    payload, contract = _sample()
    # At row 260, set today equal to its t-20 close: this may satisfy the
    # inclusive SMA side, subject to the independently computed EMA side.
    closes = [b["close"] for b in payload["bars"]]
    today = payload["bars"][260]
    today.update(close=closes[240], open=closes[240], high=closes[240]+1, low=closes[240]-1)
    obs = prepare_deduction_observations(payload, contract, compute_labels=False)["observations"][260]
    assert obs["features"]["ret20"] == pytest.approx(0)
    assert obs["context"] is (obs["features"]["ema20_distance"] > 0)
    # Force equality with EMA exactly via a constant price history: > is strict.
    for bar in payload["bars"]:
        bar.update(close=100., open=100., high=101., low=99.)
    equal = prepare_deduction_observations(payload, contract, compute_labels=False)["observations"][260]
    assert equal["context"] is False
    assert equal["features"]["ret20"] == 0


def test_late_fold_rank_failure_prevents_any_fit(monkeypatch):
    days = ["2024-06-01", "2024-07-01", "2024-08-01", "2025-02-01", "2025-03-01", "2026-02-01"]
    ends = ["2024-06-02", "2024-07-02", "2024-08-02", "2025-02-02", "2025-03-02", "2026-02-02"]
    rows = []
    for i, (day, end) in enumerate(zip(days, ends)):
        rows.append({"id": f"A|{day}", "asset": "A", "date": day, "stratum": f"A|{day[:4]}",
                     "features": {"x": float(i), "added": float(i + (1 if i == 5 else 0))},
                     "eligible": True, "y": float(i), "label_end": end,
                     "label_reason": None, "tested_condition": None})
    contract = {"question": {"layer": "factor_information"},
                "target": {"kind": "mae", "unit": "percentage_point"},
                "weights": {"policy": "equal_asset", "comparison": "fixed_common"},
                "training_weights": "equal_asset",
                "dependence": {"block_length": 2, "draws": 2, "seed": 1},
                "calendar": sorted(days+ends),
                "split": {"label_policy": "purge", "evaluation_label_policy": "contained",
                          "folds": [{"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
                                    {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-12-31"}]},
                "evaluator": {"kind": "prediction_ols", "version": "1.0.0",
                              "baseline_features": ["x"], "added_features": ["added"],
                              "lambda": 0, "rcond": 1e-12}}
    called = []
    monkeypatch.setattr(workflow_evaluation, "_ols_fit", lambda *args: called.append(True))
    with pytest.raises(EvaluationError, match="dependence"):
        workflow_evaluation.evaluate_observations(rows, contract)
    assert not called


def test_d01_contract_rejects_method_and_target_drift():
    path = Path(__file__).resolve().parents[2] / "docs/experiments/raw/deduction-box-information-2026-09-30/execution/workflow-draft-suggestion.json"
    draft = json.loads(path.read_text())
    validate_workflow_contract(draft)
    for field, value in (("evaluator", "prediction_ridge"), ("target", "forward_return")):
        bad = copy.deepcopy(draft)
        if field == "evaluator":
            bad["evaluator"]["kind"] = value
            bad["question"]["method"]["name"] = value
        else:
            bad["target"]["kind"] = value
            bad["question"]["target"]["kind"] = value
        with pytest.raises(ValueError):
            validate_workflow_contract(bad)
