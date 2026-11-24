"""Synthetic structural checks; these are not return or mechanism tests."""

import hashlib
import json

import pytest

from lei_signal.research.factor_combinations import assess_candidate, main, CHECK_FIELDS, RULE_FIELDS
from lei_signal.research.mechanism_review import review_mechanism


def _attachment(root, **changes):
    source = root / "source.txt"
    source.write_text("synthetic citation", encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    document = {
        "schema": "strategy-mechanism/1",
        "identity": {"candidate_id": "case", "component_keys": ["object:x@1"],
                     "scope": {"market": "CN", "universe_id": "u", "frequency": "monthly",
                               "currency": "CNY", "asset_type": "stock", "purpose": "comparison"}},
        "claim": {"type": "relative_return", "increment_measure": "percentage points per month",
                  "return_sources": ["risk_compensation"]},
        "benchmark": {"id": "index", "role": "parent_index", "universe_id": "u",
                      "selection_reason": "predeclared parent", "selected_before_results": True,
                      "currency": "CNY", "return_basis": "gross_total_return",
                      "cost_basis": "gross, without fees", "investability_evidence": "not claimed"},
        "mechanism": {"participants_constraints": "forced allocation", "compensation_or_service": "risk bearing",
                      "persistence": "constraint remains", "signal_link": "measured proxy",
                      "competing_explanation": "sector exposure", "distinguishing_prediction": "within sector",
                      "falsifier": "vanishes after control", "evidence_stage": "hypothesis"},
        "universe": {"fit_reason": "same pool", "membership_basis": "point_in_time",
                     "negative_control": "unrelated stocks"},
        "timing": {"created_at": "2026-10-31T10:00:00+08:00", "information_available": "at close",
                   "earliest_execution": "next open", "history_status": "already_seen",
                   "prior_attempts": "old trial"},
        "controls": {"strongest_simple_comparator": "parent index", "risk_exposure_comparator": "beta matched",
                     "cost_capacity_plan": "quote commissions", "uncertainty_plan": "future holdout"},
        "sources": [{"id": "s", "path": "source.txt", "sha256": sha,
                     "locator": "paragraph 1", "reading_scope": "description only"}],
        "source_refs": ["s"], "open_questions": [],
    }
    document.update(changes)
    path = root / "mechanism.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, document


def test_complete_only_for_manual_review(tmp_path, capsys):
    path, doc = _attachment(tmp_path)
    result = review_mechanism(tmp_path, path, expected_candidate={"id": "case", **doc["identity"]})
    assert result["status"] == "complete_for_manual_review"
    assert result["warnings"] and result["source_bindings"]
    assert not result["economic_mechanism_verified"]
    assert not result["alpha_verified"]
    assert not result["independent_validation_verified"]
    assert not result["forward_eligible"]
    main(["mechanism-review", "--root", str(tmp_path), "--request", str(path)])
    assert json.loads(capsys.readouterr().out)["status"] == "complete_for_manual_review"


def test_unknown_history_and_identity_conflict(tmp_path, capsys):
    path, doc = _attachment(tmp_path)
    doc["mechanism"]["falsifier"] = None
    doc["benchmark"]["selected_before_results"] = None
    doc["timing"]["history_status"] = "protected_unseen_claimed"
    path.write_text(json.dumps(doc), encoding="utf-8")
    result = review_mechanism(tmp_path, path)
    assert result["status"] == "incomplete"
    assert not result["independent_validation_verified"]
    with pytest.raises(SystemExit) as incomplete_exit:
        main(["mechanism-review", "--root", str(tmp_path), "--request", str(path)])
    assert incomplete_exit.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "incomplete"
    expected = {"id": "different", "component_keys": ["object:y@1"],
                "scope": {**doc["identity"]["scope"], "universe_id": "other"}}
    assert review_mechanism(tmp_path, path, expected)["status"] == "invalid"
    doc["benchmark"]["currency"] = "USD"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "invalid"
    with pytest.raises(SystemExit) as invalid_exit:
        main(["mechanism-review", "--root", str(tmp_path), "--request", str(path)])
    assert invalid_exit.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


def test_declared_unknown_is_incomplete_and_symlink_cannot_escape(tmp_path):
    path, doc = _attachment(tmp_path)
    doc["benchmark"]["return_basis"] = "unknown"
    doc["universe"]["membership_basis"] = "unknown"
    doc["timing"]["history_status"] = "unknown"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "incomplete"
    doc["benchmark"]["return_basis"] = "gross_total_return"
    doc["universe"]["membership_basis"] = "point_in_time"
    doc["timing"]["history_status"] = "already_seen"
    outside = tmp_path.parent / "outside-synthetic-source.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(outside)
    doc["sources"][0]["path"] = "link.txt"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "invalid"


def test_source_drift_unbound_reference_and_escape(tmp_path):
    path, doc = _attachment(tmp_path)
    doc["source_refs"] = ["unknown"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "invalid"
    doc["source_refs"] = ["s"]
    path.write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / "source.txt").write_text("drift", encoding="utf-8")
    assert any("drift" in x["message"] for x in review_mechanism(tmp_path, path)["issues"])
    doc["sources"][0]["path"] = "../outside.txt"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "invalid"


def test_net_claim_needs_net_investable_comparator(tmp_path):
    path, doc = _attachment(tmp_path)
    doc["claim"]["type"] = "net_relative_return"
    doc["benchmark"].update(role="market_reference", return_basis="price_return",
                            cost_basis=None, investability_evidence=None)
    doc["universe"]["membership_basis"] = "current_constituents_backcast"
    path.write_text(json.dumps(doc), encoding="utf-8")
    result = review_mechanism(tmp_path, path)
    assert result["status"] == "incomplete"
    assert any(x["field"] == "benchmark.return_basis" for x in result["issues"])
    doc["benchmark"]["return_basis"] = "invented_basis"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "invalid"


def test_same_universe_control_requires_exact_universe_id(tmp_path):
    path, doc = _attachment(tmp_path)
    doc["benchmark"]["universe_id"] = "different-pool"
    doc["benchmark"]["role"] = "same_universe_control"
    path.write_text(json.dumps(doc), encoding="utf-8")
    result = review_mechanism(tmp_path, path)
    assert result["status"] == "invalid"
    assert any(x["field"] == "benchmark.universe_id" for x in result["issues"])
    for role in ("parent_index", "market_reference", "investable_alternative"):
        doc["benchmark"]["role"] = role
        path.write_text(json.dumps(doc), encoding="utf-8")
        assert review_mechanism(tmp_path, path)["status"] == "complete_for_manual_review"


def test_not_checked_and_malformed_declared_source(tmp_path):
    assert review_mechanism(tmp_path, None)["status"] == "not_checked"
    path, doc = _attachment(tmp_path)
    doc["claim"]["return_sources"] = [["risk_compensation"]]
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert review_mechanism(tmp_path, path)["status"] == "invalid"


def test_candidate_review_requires_old_inputs_and_mechanism(tmp_path):
    path, doc = _attachment(tmp_path)
    key = "object:x@1"
    catalog = {"root": str(tmp_path), "cards": {key: {
        "market": ["CN"], "assets": ["stock"], "uses": ["comparison"],
        "family": "synthetic", "financial_meaning": "hypothesis", "horizon": "monthly",
        "source_bindings": []}}}
    candidate = {"id": "case", "component_keys": [key], "mode": "joint_selection",
                 "financial_hypothesis": "possible risk premium", "competing_explanation": "sector",
                 "scope": doc["identity"]["scope"],
                 "rules": {field: "specified" for field in RULE_FIELDS}}
    bound = {"path": "source.txt", "sha256": doc["sources"][0]["sha256"]}
    evidence = {"checks": {field: True for field in CHECK_FIELDS},
                "check_bindings": {field: [bound] for field in CHECK_FIELDS}}
    result = assess_candidate(catalog, candidate, evidence, mechanism_path=path)
    assert result["state"] == "qualified_for_research_design"
    assert result["new_research_status"] == "ready_for_manual_review"
    assert result["mechanism_review"]["candidate_consistency"] == "matched"
    evidence["checks"]["point_in_time"] = None
    blocked = assess_candidate(catalog, candidate, evidence, mechanism_path=path)
    assert blocked["state"] == "blocked_inputs"
    assert blocked["mechanism_review"]["status"] == "complete_for_manual_review"
    assert blocked["new_research_status"] != "ready_for_manual_review"
