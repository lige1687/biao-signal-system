"""Regression checks for the AI preparation entry, without live-registry fixtures."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lei_signal.research.preparation import build_context


def test_history_only_survives_unavailable_definition_registry(tmp_path):
    study = tmp_path / "study"
    study.mkdir()
    (study / "completion.json").write_text(json.dumps({
        "status": "blocked", "conclusion": "Input qualification incomplete",
        "reopen_conditions": ["Obtain dated historical membership"],
    }))
    result = build_context(tmp_path, studies=["study"], practice_only=True)
    assert result["definition_status"] == "not_evaluated_practice_only"
    assert result["execution_authorized"] is False
    history = result["practice_context"]["history"]
    assert history["matched"]
    serialized = json.dumps(history)
    assert "Obtain dated historical membership" in serialized
    assert "Input qualification incomplete" in serialized


def test_regular_preparation_also_includes_prior_context(tmp_path, monkeypatch):
    standards = tmp_path / "docs/research/current-standards.json"
    standards.parent.mkdir(parents=True)
    standards.write_text(json.dumps({"definition_registry": "registry.json"}))
    (tmp_path / "registry.json").write_text("{}")
    monkeypatch.setattr("lei_signal.research.preparation.definitions.load_registry",
                        lambda _: {"research_references": [], "sources": {}})
    result = build_context(tmp_path, terms=["risk"])
    assert result["practice_context"]["history"]["query"]["terms"] == ["risk"]
    assert result["definition_status"] == "idea_definition_only"


def test_history_only_cli_reads_existing_study_without_writing_it(tmp_path):
    (tmp_path / "study").mkdir()
    source = tmp_path / "study/completion.json"
    source.write_text(json.dumps({"status": "blocked", "conclusion": "no qualified inputs"}))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    process = subprocess.run([sys.executable, "-m", "lei_signal.research.preparation",
                              "--root", str(tmp_path), "--study", "study", "--practice-only"],
                             capture_output=True, text=True, env=env)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["practice_context"]["history"]["matched"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_diagnosis_request_path_must_stay_inside_root(tmp_path):
    with pytest.raises(ValueError, match="inside|outside|relative"):
        build_context(tmp_path, terms=["risk"], practice_only=True,
                      diagnosis_file="../outside.json")


def test_missing_diagnosis_is_visible_and_not_a_planned_experiment(tmp_path):
    result = build_context(tmp_path, terms=["risk"], practice_only=True,
                           diagnosis_file="absent.json")
    diagnosis = result["practice_context"]["diagnosis"]
    assert diagnosis["status"] == "blocked"
    assert diagnosis["run_authorized"] is False


def test_ordinary_definition_failure_is_not_silently_bypassed(tmp_path):
    with pytest.raises(ValueError, match="current standards"):
        build_context(tmp_path, terms=["risk"])


def test_diagnosis_only_preserves_unqueried_history(tmp_path):
    result = build_context(tmp_path, practice_only=True, diagnosis_file="absent.json")
    assert result["practice_context"]["history"]["status"] == "not_requested"
    assert result["practice_context"]["diagnosis"]["status"] == "blocked"


def test_practice_only_cannot_silently_drop_requested_definitions(tmp_path):
    with pytest.raises(ValueError, match="cannot resolve"):
        build_context(tmp_path, practice_only=True, definition_refs=["exact@1.0.0"])


def test_llm_review_only_uses_existing_preparation_entry(tmp_path):
    request = tmp_path / "llm-request.json"
    request.write_text(json.dumps({"schema": "llm-output-review/1",
                                   "timing": {"schema": "llm-timing-review/1"}}))
    result = build_context(tmp_path, practice_only=True, llm_review_file="llm-request.json")
    review = result["practice_context"]["llm_output_review"]
    assert review["status"] == "blocked"
    assert review["execution_authorized"] is False
    assert review["request_binding"]["path"] == "llm-request.json"
    assert result["definition_status"] == "not_evaluated_practice_only"


def test_missing_llm_request_does_not_become_no_problem(tmp_path):
    result = build_context(tmp_path, practice_only=True, llm_review_file="absent.json")
    review = result["practice_context"]["llm_output_review"]
    assert review["status"] == "blocked"
    assert review["model_called"] is False


def test_optional_handoff_preserves_history_and_contract(tmp_path):
    (tmp_path / "study").mkdir()
    (tmp_path / "study/completion.json").write_text(json.dumps({
        "status": "blocked", "conclusion": "no incremental evidence",
        "reopen_conditions": ["qualified dated inputs"],
    }))
    contract = {"mission": "read existing evidence", "research_controls": {"budget": "unknown"}}
    (tmp_path / "contract.json").write_text(json.dumps(contract))
    result = build_context(tmp_path, studies=["study"], practice_only=True,
                           handoff_contract="contract.json")
    context = result["delegation_context"]
    assert context["practice_context"] == result["practice_context"]
    assert context["control"]["contract"] == contract
    assert context["execution_authorized"] is False
    assert "delegation_context" not in context["preparation"]
    assert "no incremental evidence" in json.dumps(context)


def test_handoff_only_does_not_invent_history_or_authorization(tmp_path):
    (tmp_path / "contract.json").write_text('{"mission":"inspect"}')
    result = build_context(tmp_path, practice_only=True, handoff_contract="contract.json")
    assert result["practice_context"]["history"]["status"] == "not_requested"
    assert result["delegation_context"]["control"]["research_controls"] == "unknown"
    assert result["execution_authorized"] is False


def test_missing_handoff_contract_is_visible(tmp_path):
    result = build_context(tmp_path, practice_only=True, handoff_contract="missing.json")
    assert result["delegation_context"]["status"] == "blocked"
