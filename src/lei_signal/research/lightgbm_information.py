"""Fixed shallow-tree research comparator; no parameter search or trade rules."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

PACKAGE_VERSION = "4.6.0"
PARAMETERS = {
    "objective": "regression", "boosting_type": "gbdt", "learning_rate": 0.05,
    "num_leaves": 4, "max_depth": 2, "min_data_in_leaf": 20,
    "lambda_l2": 1.0, "feature_fraction": 1.0, "bagging_fraction": 1.0,
    "bagging_freq": 0, "max_bin": 31, "num_threads": 1,
    "seed": 20261004, "deterministic": True, "force_col_wise": True,
    "verbosity": -1,
}
NUM_BOOST_ROUND = 40


def runtime_fingerprint():
    import lightgbm as lgb
    from lightgbm.libpath import _find_lib_path
    if lgb.__version__ != PACKAGE_VERSION:
        raise ValueError("LightGBM research requires frozen version 4.6.0")
    binary = Path(_find_lib_path()[0])
    return {"package_version": lgb.__version__,
            "native_library_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}


def validate_evaluator(evaluator):
    if (evaluator.get("parameters") != PARAMETERS or
            evaluator.get("num_boost_round") != NUM_BOOST_ROUND or
            evaluator.get("package_version") != PACKAGE_VERSION):
        raise ValueError("LightGBM requires the fixed shallow-tree research settings")
    if evaluator.get("runtime") != runtime_fingerprint():
        raise ValueError("LightGBM runtime fingerprint differs from frozen comparator")


def fit_predict(train, evaluation, cols, normalized_weights, evaluator):
    import lightgbm as lgb
    validate_evaluator(evaluator)
    x = np.array([[r[c] for c in cols] for r in train.features], dtype=float)
    xe = np.array([[r[c] for c in cols] for r in evaluation.features], dtype=float)
    y = train.y.to_numpy(float)
    w = np.asarray(normalized_weights, dtype=float)
    if (not np.isfinite(x).all() or not np.isfinite(xe).all() or
            not np.isfinite(y).all() or not np.isfinite(w).all() or
            np.any(w <= 0) or not np.isclose(w.sum(), 1.0)):
        raise ValueError("LightGBM needs finite paired inputs and normalized positive weights")
    # Same relative asset weights as the linear comparator, mean sample weight 1.
    # Tree regularization is explicitly frozen at this scale; no rescaling search.
    data = lgb.Dataset(x, label=y, weight=w * len(train), feature_name=cols,
                       free_raw_data=False)
    model = lgb.train(dict(PARAMETERS), data, num_boost_round=NUM_BOOST_ROUND)
    prediction = model.predict(xe, num_threads=1)
    model_text = model.model_to_string()
    return prediction, {
        "features": cols, "training_rows": len(train),
        "weight_sum": float(w.sum()), "native_weight_sum": float(len(train)),
        "parameters": dict(PARAMETERS), "requested_rounds": NUM_BOOST_ROUND,
        "actual_rounds": model.current_iteration(), "runtime": runtime_fingerprint(),
        "model_text": model_text,
        "model_sha256": hashlib.sha256(model_text.encode()).hexdigest(),
        "zero_variance": [c for j, c in enumerate(cols) if np.ptp(x[:, j]) == 0],
        "negative_prediction_rows": int(np.sum(prediction < 0)),
        "raw_min": float(prediction.min()), "raw_max": float(prediction.max()),
        "clipped_rows": 0,
    }
