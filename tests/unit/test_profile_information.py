"""Synthetic qualification tests for the research-only profile adapter."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import profile_information as profile


def _fixture(n=280):
    calendar = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for i, day in enumerate(calendar):
        close = 100 + .12 * i + 2 * math.sin(i / 7)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "action_known": True, "volume_source_known": True,
                     "volume_break": False, "open": close, "high": close + 1,
                     "low": close - 1, "close": close, "volume": 1.0})
    payload = {"data_mode": "synthetic", "calendar": calendar, "bars": bars}
    contract = {"feature": {"kind": "profile_overhead_information",
                            "definition_ref": profile.DEFINITION_REF, "lookback": 120,
                            "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "forward_return", "start_offset": 1,
                           "end_offset": 21, "entry_field": "close",
                           "price_measure": "economic_price"},
                "question": {"sampling": "daily", "period": [calendar[0], calendar[-1]]},
                "universe": {"assets": ["synthetic-A"]}}
    return payload, contract


def test_no_label_prefix_and_constant_quantity_equals_price_only(monkeypatch):
    payload, contract = _fixture()
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *a, **kw: pytest.fail("future accessed"))
    rows = profile.prepare_profile_observations(payload, contract)["observations"]
    assert rows[250]["ready_252"] is False
    assert rows[251]["ready_252"] is True
    assert all(r["y"] is None for r in rows)
    for row in rows[251:]:
        assert row["profile_known"] is True
        assert row["overhead_supply_ratio"] == pytest.approx(row["price_only_overhead_ratio"])


def test_uniform_volume_scaling_is_invariant_and_future_change_cannot_rewrite_past():
    payload, contract = _fixture()
    before = profile.prepare_profile_observations(payload, contract)["observations"]
    scaled = deepcopy(payload)
    for row in scaled["bars"]:
        row["volume"] *= 13
    after = profile.prepare_profile_observations(scaled, contract)["observations"]
    assert [r["overhead_supply_ratio"] for r in before[251:]] == pytest.approx(
        [r["overhead_supply_ratio"] for r in after[251:]])
    changed = deepcopy(payload)
    changed["bars"][275]["volume"] *= 100
    assert before[:275] == profile.prepare_profile_observations(changed, contract)["observations"][:275]


def test_inclusive_break_window_marks_exactly_120_rows_unknown():
    payload, contract = _fixture(400)
    payload["bars"][260]["volume_break"] = True
    rows = profile.prepare_profile_observations(payload, contract)["observations"]
    assert all(rows[i]["profile_known"] is False for i in range(260, 380))
    assert rows[259]["profile_known"] is True
    assert rows[380]["profile_known"] is True
    assert sum("volume_break" in (r["feature_reason"] or "") for r in rows) == 120


def test_unknown_quantity_and_missing_price_are_not_shortened_windows():
    payload, contract = _fixture(400)
    payload["bars"][260]["volume_source_known"] = False
    rows = profile.prepare_profile_observations(payload, contract)["observations"]
    assert all(rows[i]["profile_known"] is False for i in range(260, 380))
    missing = deepcopy(payload)
    missing["bars"][260] = {"asset": "synthetic-A", "date": payload["calendar"][260],
                            "status": "vendor_missing"}
    rows = profile.prepare_profile_observations(missing, contract)["observations"]
    assert rows[260]["ready_252"] is False
    assert rows[-1]["ready_252"] is False


def test_real_label_path_requires_permission():
    payload, contract = _fixture()
    payload.update(data_mode="historical_reconstruction", price_series="economic_price")
    contract["universe"]["assets"] = list(profile.ASSETS)
    with pytest.raises(ValueError, match="authorization"):
        profile.prepare_profile_observations(payload, contract, compute_labels=True)


def test_workflow_gate_and_exact_profile_contract():
    import json
    from pathlib import Path
    from lei_signal.research.question_contract import QuestionContractError, validate_workflow_contract
    from lei_signal.research.workflow import WorkflowBlocked, preflight
    root = Path(__file__).resolve().parents[2]
    draft = json.loads((root / "docs/experiments/raw/profile-information-2026-10-02/adapter/workflow-draft.json").read_text())
    validate_workflow_contract(draft)
    with pytest.raises(WorkflowBlocked, match="P01 preparation has no real-label/effect authorization"):
        preflight(draft, root, require_frozen=False)
    for section, key, value in [
        ("feature", "bins", 49),
        ("evaluator", "baseline_features", ["r1"]),
        ("target", "end_offset", 20),
    ]:
        changed = deepcopy(draft)
        changed[section][key] = value
        with pytest.raises(QuestionContractError):
            validate_workflow_contract(changed)
    changed = deepcopy(draft)
    changed["data"]["qualification"]["adapter"] = "top_etf_economic/1.0"
    with pytest.raises(QuestionContractError):
        validate_workflow_contract(changed)


def test_k_and_profile_adapter_hashes_invalidate_feature_and_label_cache():
    import json
    from pathlib import Path
    from lei_signal.research.workflow import CODE_PATHS, cache_keys
    root = Path(__file__).resolve().parents[2]
    for folder, adapter, dependency in [
        ("key-fluctuation-information-2026-10-01", "key_fluctuation_information.py", None),
        ("profile-information-2026-10-02/adapter", "profile_information.py", "src/lei_signal/features/volume_profile.py"),
    ]:
        contract = json.loads((root / f"docs/experiments/raw/{folder}/workflow-draft.json").read_text())
        adapter_path = "src/lei_signal/research/" + adapter
        files = {name: name for name in CODE_PATHS}
        files[adapter_path] = "adapter-v1"
        if dependency:
            files[dependency] = "production-v1"
        bindings = {"data_sha256": "data", "definition_closure": {}, "files": files}
        first = cache_keys(contract, bindings)
        changed = deepcopy(bindings)
        changed["files"][adapter_path] = "adapter-v2"
        second = cache_keys(contract, changed)
        assert second["features"] != first["features"]
        assert second["labels"] != first["labels"]
        if dependency:
            changed = deepcopy(bindings)
            changed["files"][dependency] = "production-v2"
            assert cache_keys(contract, changed)["features"] != first["features"]
