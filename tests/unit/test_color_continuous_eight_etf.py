"""Eight-ETF extension keeps the four-ETF color meaning and binds its source."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.research import color_continuous_eight_etf as eight
from lei_signal.research import color_continuous_workflow as four

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "docs/experiments/raw/color-sector-extension-2026-10-05"


def _actual():
    path = RAW / "workflow-input.local.json"
    payload = json.loads(path.read_text())
    contract = {
        "data": {"mode": "real", "path": str(path.relative_to(ROOT)),
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "qualification": {"adapter": "color_eight_etf_economic/1.0",
                                   "manifest_path": str((RAW / "source-manifest.json").relative_to(ROOT))}},
        "universe": {"assets": list(eight.ASSETS)},
        "question": {"sampling": "daily", "period": ["2022-01-04", "2026-06-30"]},
        "feature": {"kind": eight.KIND, "definition_ref": eight.DEFINITION_REF,
                    "lookback": 20, "warmup": 252, "missing_policy": "segmented"},
        "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                   "entry_field": "close", "path_field": "close", "price_measure": "economic_price"},
        "split": {"folds": [
            {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
            {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}]},
    }
    return payload, contract


def test_source_binding_and_roundoff_scope(tmp_path):
    payload, contract = _actual()
    quality = eight.qualify_source(payload, contract, ROOT)["quality"]
    assert quality["source_files_bound"] == 11
    assert quality["roundoff_ohlc_rows"] == 13
    assert quality["roundoff_max_absolute"] < 1e-12
    bad = deepcopy(payload)
    bad["bars"][0]["close"] *= 1.01
    with pytest.raises(ValueError, match="loaded panel"):
        eight.qualify_source(bad, contract, ROOT)
    changed = deepcopy(contract)
    changed["data"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="contract input"):
        eight.qualify_source(payload, changed, ROOT)
    manifest = json.loads((RAW / "source-manifest.json").read_text())
    manifest["files"][0]["sha256"] = "0" * 64
    local = tmp_path / "manifest.json"
    local.write_text(json.dumps(manifest))
    changed = deepcopy(contract)
    changed["data"]["qualification"]["manifest_path"] = str(local)
    with pytest.raises(ValueError, match="source binding changed"):
        eight.qualify_source(payload, changed, ROOT)


def test_bad_ohlc_and_duplicate_rejected():
    payload, contract = _actual()
    bad = deepcopy(payload)
    bad["bars"][0]["high"] = bad["bars"][0]["close"] - 1e-4
    with pytest.raises(ValueError, match="valid, action-known"):
        eight.prepare_observations(bad, contract)
    bad = deepcopy(payload)
    bad["bars"].append(bad["bars"][0])
    with pytest.raises(ValueError, match="duplicate"):
        eight.prepare_observations(bad, contract)


def test_first_four_identical_and_all_eight_indicators():
    payload, contract = _actual()
    new = eight.prepare_observations(payload, contract)
    assert new["coverage"]["scheduled"] > 8000
    assert all(row["y"] is None for row in new["observations"])
    assert set(row["asset"] for row in new["observations"]) == set(eight.ASSETS)
    assert len(eight.BASELINE_FEATURES) == 16
    for row in new["observations"]:
        if row["eligible"]:
            assert all(row["features"][f"asset_{code[:6]}"] == int(row["asset"] == code)
                       for code in eight.ASSETS[1:])
    subset = {**payload, "bars": [r for r in payload["bars"] if r["asset"] in eight.ASSETS[:4]]}
    old_contract = deepcopy(contract)
    old_contract["universe"]["assets"] = list(eight.ASSETS[:4])
    old_contract["feature"]["kind"] = four.KIND
    old_contract["feature"]["definition_ref"] = four.DEFINITION_REF
    old = four.prepare_observations(subset, old_contract)
    existing = {(r["asset"], r["date"]): r for r in old["observations"]}
    for row in new["observations"]:
        if row["asset"] not in eight.ASSETS[:4]:
            continue
        prior = existing[(row["asset"], row["date"])]
        assert row["eligible"] == prior["eligible"]
        assert row["feature_reason"] == prior["feature_reason"]
        assert {k: row["features"][k] for k in four.BASELINE_FEATURES + four.ADDED_FEATURES} == prior["features"]
    # A missing sector quote is an unknown day and restarts the continuous window.
    missing = next(r for r in new["observations"] if r["asset"] == "512480.SS"
                   and r["date"] == "2021-03-26") if any(
                       r["date"] == "2021-03-26" for r in new["observations"]) else None
    if missing is not None:
        assert not missing["eligible"]


def test_qualification_is_x_only(monkeypatch):
    payload, contract = _actual()
    def no_labels(*args, **kwargs):
        raise AssertionError("qualification must not read outcome labels")
    monkeypatch.setattr(eight.shared, "_label", no_labels)
    result = eight.build_qualification(payload, contract, ROOT)
    assert result["outcome_values_used_for_design"] is False
    assert len(result["scientific_support"]["folds"]) == 2
    assert result["source_quality"]["roundoff_ohlc_rows"] == 13
