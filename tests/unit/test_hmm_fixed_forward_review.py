"""No-fit continuation agrees with the sealed June HMM research run."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from lei_signal.research.hmm_fixed_forward_review import (
    prepare_fixed_extension, predict_saved,
)


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "docs/experiments/raw/douyin-system-increment-2026-10-07/hmm-risk-trial/full_price-run"
SOURCE = ROOT / "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/workflow-input.json"


def inputs():
    return (json.loads(SOURCE.read_text()), json.loads((RUN / "contract.json").read_text()),
            json.loads((RUN / "preflight.json").read_text()), json.loads((RUN / "result.json").read_text()))


def test_frozen_prefix_features_match_every_saved_row():
    payload, contract, saved, _ = inputs()
    calculated = prepare_fixed_extension(payload, contract)
    assert len(calculated["observations"]) == len(saved["observations"]) == 8680
    for key in ("scheduled", "feature_ready"):
        assert calculated["coverage"][key] == saved["coverage"][key]
    for actual, expected in zip(calculated["observations"], saved["observations"]):
        assert actual["id"] == expected["id"]
        assert actual["features"] == expected["features"]
        assert actual["y"] is None


def test_saved_coefficients_reconstruct_old_predictions_without_fit():
    _, _, saved, result = inputs()
    rows = {r["id"]: r for r in saved["observations"]}
    selected = [rows[p["id"]] for p in result["predictions"]]
    computed = predict_saved(selected, result["execution"]["fit_details"])
    for current, previous in zip(computed, result["predictions"]):
        assert current["id"] == previous["id"]
        for field in ("B0", "B1", "B2"):
            assert current[field] == pytest.approx(previous[field], abs=1e-12)


def test_rejects_changed_model_and_calendar_and_coefficients():
    payload, contract, _, result = inputs()
    changed = deepcopy(contract)
    changed["feature"]["model_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="fixed saved model"):
        prepare_fixed_extension(payload, changed)
    bad_calendar = {**payload, "calendar": list(payload["calendar"])}
    bad_calendar["calendar"][-1] = "2026-07-01"
    with pytest.raises(ValueError, match="calendar"):
        prepare_fixed_extension(bad_calendar, contract)
    bad_fit = deepcopy(result["execution"]["fit_details"])
    bad_fit[0]["training_rows"] = 5535
    with pytest.raises(ValueError, match="coefficients"):
        predict_saved([], bad_fit)
