"""Small correctness tests; these never start the search comparison."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402


def test_generated_splits_and_hashes():
    p = run.read_protocol()
    inputs, fingerprints = run.output_data(p)
    assert set(inputs) == set(run.SPLITS)
    for split in run.SPLITS:
        x0 = inputs[split]["additive"]["x"]
        assert x0.shape == (p["data"]["rows"][split], 4)
        assert all(np.array_equal(x0, inputs[split][task]["x"]) for task in run.TASKS)
        assert np.all(np.isfinite(x0))
        if split == "outside_range":
            assert np.all(np.any(np.abs(x0) > 2, axis=1))
        else:
            assert np.all(np.abs(x0) <= 2)
        for task in run.TASKS:
            record = inputs[split][task]
            assert record["y"].shape == (len(x0),)
            assert fingerprints[split][task]["y_sha256"] == run.array_hash(record["y"])


def test_restricted_formula_and_invalid_policy():
    x = np.array([[2.0, 0.0, -1.0, 0.0], [3.0, 2.0, 1.0, 0.0]])
    assert np.array_equal(run.formula_predict("protected_divide(x0, x1)", x), [1.0, 1.5])
    assert np.array_equal(run.formula_predict("add(x0, mul(x1, 1.0))", x), [2.0, 5.0])
    for expression in ("__import__('os')", "x0.__class__", "x0[0]", "x4", "1e9", "x0+x1"):
        with pytest.raises(ValueError):
            run.formula_predict(expression, x)
    assert run.mse(np.zeros(2), np.array([0.0, np.inf])) == run.INVALID_SCORE
    assert run.mse(np.zeros(2), np.array([0.0, 1e7])) == run.INVALID_SCORE


def test_direct_baseline_has_interactions_and_rational_terms():
    specs = run.feature_specs()
    assert any(s["kind"] == "monomial" and s["powers"] == (1, 1, 0, 0) for s in specs)
    assert any(s["kind"] == "monomial" and s["powers"] == (1, 1, 1, 0) for s in specs)
    assert any(s == {"kind": "rational", "i": 0, "j": 1} for s in specs)
    rng = np.random.default_rng(5)
    x = rng.uniform(-2, 2, size=(96, 4))
    train = {"x": x[:64], "y": x[:64, 0] / (1 + x[:64, 1] ** 2) + x[:64, 2]}
    val = {"x": x[64:], "y": x[64:, 0] / (1 + x[64:, 1] ** 2) + x[64:, 2]}
    model, details = run.direct_baseline(train, val)
    assert run.mse(val["y"], run.direct_predict(val["x"], model)) < 1e-20
    assert details["fit_count"] > 4
    assert "omp_4" in details["variants_validation_mse"]


def test_check_existing_requires_archive_and_does_not_import_deap(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "deap", None)
    with pytest.raises(FileNotFoundError):
        run.check_existing(tmp_path)
    assert "deap" not in run.__dict__


def test_protocol_hash_fixed():
    assert run.digest_bytes(run.PROTOCOL.read_bytes()) == run.EXPECTED_PROTOCOL_SHA
    assert json.loads(run.PROTOCOL.read_text())["budget"]["market_fits"] == 0


def test_deap_compile_and_independent_ast_agree_on_one_tree():
    gp = pytest.importorskip("deap.gp")
    pset = run.make_pset(gp)
    tree = gp.PrimitiveTree.from_string("add(x0, protected_divide(x1, 1.0))", pset)
    x = np.array([[1.0, 2.0, 3.0, 4.0], [-1.0, 0.0, 2.0, 3.0]])
    compiled = gp.compile(tree, pset)
    actual = compiled(*(x[:, i] for i in range(4)))
    assert np.array_equal(actual, run.formula_predict(str(tree), x))
