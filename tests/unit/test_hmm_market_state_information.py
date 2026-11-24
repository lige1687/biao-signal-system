"""Numerical and identity checks for the frozen HMM research adapter."""

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest
from hmmlearn.hmm import GaussianHMM

from lei_signal.research.hmm_market_state_information import (
    MODEL_PATH, MODEL_SHA256, FOLD, DEFINITION_REF, ADDED_FEATURES,
    anchor_probabilities, forward_step, load_saved_model, validate_feature_contract,
)
from lei_signal.research.price_volume_path_information import BASELINE_FEATURES, IDENTITY


ROOT = Path(__file__).resolve().parents[2]
TRIAL = ROOT / "docs/experiments/raw/douyin-system-increment-2026-10-07/hmm-time-trial"
FEATURE = {"model_path": MODEL_PATH, "model_sha256": MODEL_SHA256,
           "model_fit_end": "2024-12-31"}


def test_saved_probability_matches_all_2025_prefix_rows():
    model, _, _ = load_saved_model(FEATURE)
    with (TRIAL / "fixed-model-inputs.csv").open() as file:
        inputs = list(csv.DictReader(file))
    with (TRIAL / "2025-comparison.csv").open() as file:
        expected = list(csv.DictReader(file))
    by_date = {}
    p = None
    for row in inputs:
        p = forward_step(model, [float(row["scaled_return"]), float(row["scaled_log_vol20"])], p)
        by_date[row["date"]] = p
    assert len(expected) >= 240
    for row in expected:
        np.testing.assert_allclose(by_date[row["date"]],
            [float(row[f"causal_prefix_state{i}"]) for i in range(3)], atol=1e-10, rtol=0)


def test_toy_forward_and_prefix_stability():
    model = GaussianHMM(n_components=3, covariance_type="diag", init_params="", params="")
    model.n_features = 2
    model.startprob_ = np.array([0.6, 0.3, 0.1])
    model.transmat_ = np.array([[0.8, 0.1, 0.1], [0.2, 0.7, 0.1], [0.1, 0.2, 0.7]])
    model.means_ = np.array([[0., 0.], [2., 0.], [0., 2.]])
    model.covars_ = np.ones((3, 2))
    model._check()
    x = [0.1, 0.2]
    p = forward_step(model, x)
    weights = model.startprob_ * np.exp(-.5*np.sum((model.means_ - x)**2, axis=1))
    np.testing.assert_allclose(p, weights/weights.sum(), atol=1e-12)
    first = p.copy()
    for observation in ([0., 2.], [2., 0.], [0.5, 0.5]):
        p = forward_step(model, observation, p)
        assert math.isclose(sum(p), 1, abs_tol=1e-12)
    np.testing.assert_allclose(first, forward_step(model, x), atol=0)


def test_identity_and_bad_inputs_fail():
    with pytest.raises(ValueError, match="hash"):
        load_saved_model({**FEATURE, "model_sha256": "bad"})
    with pytest.raises(ValueError, match="fit end"):
        load_saved_model({**FEATURE, "model_fit_end": "2025-01-01"})
    model, _, _ = load_saved_model(FEATURE)
    with pytest.raises(ValueError, match="observation"):
        forward_step(model, [float("nan"), 0])
    with pytest.raises(ValueError, match="probabilities"):
        forward_step(model, [0., 0.], [0.5, 0.5, 0.5])
    model.transmat_[0] = [0.7, 0.7, 0.7]
    with pytest.raises(ValueError, match="sum to 1"):
        # The saved-source loader checks stochastic rows before calculation.
        model._check()


def test_anchor_uses_only_past_and_resets_missing_quote():
    model, center, scale = load_saved_model(FEATURE)
    dates = [f"2022-02-{i:02d}" for i in range(1, 26)]
    rows = [{"status": "quoted", "action_known": True, "close": 100 + i + (i % 3)}
            for i in range(25)]
    prefix = anchor_probabilities(dates[:22], rows[:22], model, center, scale)
    extended = anchor_probabilities(dates, rows, model, center, scale)
    for date, probability in prefix.items():
        np.testing.assert_allclose(probability, extended[date], atol=0)
    rows[21] = {"status": "vendor_missing"}
    assert dates[-1] not in anchor_probabilities(dates, rows, model, center, scale)


def test_exact_comparison_modes():
    source = ROOT / "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/range-mean20-frozen/contract.json"
    contract = json.loads(source.read_text())
    contract["question"]["factor_refs"] = [DEFINITION_REF]
    contract["split"]["folds"] = [FOLD]
    contract["feature"] = {"kind": "hmm_market_state_information", "definition_ref": DEFINITION_REF,
        "lookback": 20, "warmup": 252, "missing_policy": "segmented", "bar_frequency": "daily_quote",
        "anchor_asset": "510300.SS", **FEATURE}
    contract["evaluator"]["added_features"] = list(ADDED_FEATURES)
    for mode, baseline in (("full_price", BASELINE_FEATURES), ("identity_only", IDENTITY)):
        contract["feature"]["comparison_mode"] = mode
        contract["evaluator"]["baseline_features"] = list(baseline)
        validate_feature_contract(contract)
    contract["evaluator"]["baseline_features"] = ["return1"]
    with pytest.raises(ValueError, match="fixed saved model"):
        validate_feature_contract(contract)


def test_rehearsal_marks_only_its_copy_as_synthetic(monkeypatch):
    from lei_signal.research.workflow import run_rehearsal
    from lei_signal.research import workflow_inputs
    draft = ROOT / "docs/experiments/raw/douyin-system-increment-2026-10-07/hmm-risk-trial/full_price-draft.json"
    contract = json.loads(draft.read_text())
    original_mode = contract["data"]["mode"]

    class ReachedSyntheticInput(Exception):
        pass

    def inspect_input(payload, copied):
        assert payload["data_mode"] == copied["data"]["mode"] == "synthetic"
        assert copied["feature"]["anchor_asset"] == "synthetic-A"
        validate_feature_contract(copied)
        raise ReachedSyntheticInput

    monkeypatch.setattr(workflow_inputs, "prepare_observations", inspect_input)
    with pytest.raises(ReachedSyntheticInput):
        run_rehearsal(contract)
    assert contract["data"]["mode"] == original_mode
    assert contract["feature"]["anchor_asset"] == "510300.SS"
