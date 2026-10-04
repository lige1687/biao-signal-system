import copy

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.lightgbm_information import (
    PARAMETERS, NUM_BOOST_ROUND, PACKAGE_VERSION, fit_predict, runtime_fingerprint,
    validate_evaluator,
)


def configuration():
    return {"parameters": dict(PARAMETERS), "num_boost_round": NUM_BOOST_ROUND,
            "package_version": PACKAGE_VERSION, "runtime": runtime_fingerprint()}


def test_shallow_model_uses_only_training_and_saved_model_reproduces():
    import lightgbm as lgb
    train = pd.DataFrame({"features": [{"x": float(i)} for i in range(100)],
                          "y": [float(i > 49) for i in range(100)]})
    first = pd.DataFrame({"features": [{"x": 10.}, {"x": 90.}]})
    second = pd.concat([first, pd.DataFrame({"features": [{"x": 1e9}]})], ignore_index=True)
    w = np.ones(100) / 100
    a, detail = fit_predict(train, first, ["x"], w, configuration())
    b, other = fit_predict(train, second, ["x"], w, configuration())
    assert detail["model_sha256"] == other["model_sha256"]
    assert np.allclose(a, b[:2], rtol=0, atol=1e-12)
    assert a[0] < a[1]
    saved = lgb.Booster(model_str=detail["model_text"])
    assert np.allclose(a, saved.predict(np.array([[10.], [90.]]), num_threads=1))
    assert detail["actual_rounds"] <= 40


def test_reject_changed_parameters_and_runtime():
    c = configuration()
    wrong = copy.deepcopy(c)
    wrong["parameters"]["num_leaves"] = 8
    with pytest.raises(ValueError, match="fixed shallow"):
        validate_evaluator(wrong)
    c["runtime"]["native_library_sha256"] = "wrong"
    with pytest.raises(ValueError, match="fingerprint"):
        validate_evaluator(c)
