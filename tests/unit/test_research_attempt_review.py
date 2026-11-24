import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.research import attempt_review


def _put(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_workflow_journal_preserves_retries_failures_and_corruption(tmp_path):
    family = "known-family"
    path = attempt_review._family_path(family)
    original = (
        "\n".join(
            [
                json.dumps(
                    {"event": "family", "family": family, "budget": {"scientific_variants": 1}}
                ),
                json.dumps(
                    {
                        "event": "gate_attempt",
                        "classification": "mechanical_rejection",
                        "seconds": 0.1,
                    }
                ),
                json.dumps(
                    {"event": "start", "run_id": "r1", "classification": "scientific_variant"}
                ),
                json.dumps(
                    {
                        "event": "finish",
                        "run_id": "r1",
                        "status": "failed_after_callback",
                        "results_seen": True,
                    }
                ),
                json.dumps(
                    {"event": "start", "run_id": "r2", "classification": "mechanical_retry"}
                ),
                "{broken",  # A damaged line cannot become zero failures or a complete index.
                json.dumps(
                    {
                        "event": "gate_attempt",
                        "classification": "mechanical_rejection",
                        "seconds": 0.2,
                    }
                ),
            ]
        )
        + "\n"
    )
    _put(tmp_path, path, original)
    result = attempt_review.review(tmp_path, family=family)
    journal = result["ledgers"][0]
    assert journal["source"]["sha256"] == hashlib.sha256(original.encode()).hexdigest()
    assert journal["budget"] == {"scientific_variants": 1}
    assert journal["event_count"] == 6
    assert journal["seen_history"] == "yes"
    assert journal["runs"] == [
        {
            "run_id": "r1",
            "start_count": 1,
            "finish_count": 1,
            "status": "failed_after_callback",
            "classification": "scientific_variant",
        },
        {
            "run_id": "r2",
            "start_count": 1,
            "finish_count": 0,
            "status": "unsettled",
            "classification": "mechanical_retry",
        },
    ]
    assert journal["errors"][0]["line"] == 6
    assert result["complete"] is False
    assert result["methods"]["all_attempts"]["status"] == "incomplete_source"
    assert (tmp_path / path).read_text(encoding="utf-8") == original


def test_study_sources_and_unknowns_are_descriptive(tmp_path):
    _put(tmp_path, "inputs/source.csv", "x\n1\n")
    source_sha = hashlib.sha256(b"x\n1\n").hexdigest()
    contract = {
        "task_id": "old-study",
        "history": {"family": "old-family"},
        "question": {"validation": {"stage": "exploration"}},
        "baseline": "equal-weight",
        "scope": {"market": "CN"},
        "stop": "No incremental help after costs",
        "sources": [{"path": "inputs/source.csv", "sha256": source_sha}],
    }
    _put(tmp_path, "docs/experiments/raw/old-study/contract.json", json.dumps(contract))
    _put(
        tmp_path,
        "docs/experiments/raw/old-study/manifest.json",
        json.dumps({"run_id": "old-run", "report": "docs/experiments/old-study.md"}),
    )
    result = attempt_review.review(tmp_path, studies=["docs/experiments/raw/old-study"])
    study = result["studies"][0]
    assert study["family"] == "old-family"
    assert study["run_id"] == "old-run"
    assert study["declared_validation_stage"] == "exploration"
    assert study["forward_reference"] == "unknown"
    assert study["results_seen"] == "unknown"
    assert study["binding_status"] == "matched"
    assert study["source_checks"][0]["sha256"] == source_sha
    assert study["read_complete"] is True
    assert study["evidence_identity_complete"] is True
    assert result["methods"]["strong_baseline"]["status"] == "declared_reference"
    assert result["methods"]["predeclared_failure"]["status"] == "declared_reference"
    assert result["methods"]["execution_perturbation"]["status"] == "missing_or_unknown"
    assert result["methods"]["all_attempts"]["status"] == "missing_or_unknown"


def test_drift_and_path_escape_never_upgrade_evidence(tmp_path):
    _put(tmp_path, "input.txt", "changed")
    _put(
        tmp_path,
        "study/contract.json",
        json.dumps(
            {
                "sources": [
                    {"path": "input.txt", "sha256": "0" * 64},
                    {"path": "../outside", "sha256": "0" * 64},
                ]
            }
        ),
    )
    result = attempt_review.review(tmp_path, studies=["study"])
    study = result["studies"][0]
    assert study["binding_status"] == "drift"
    assert [x["status"] for x in study["source_checks"]] == ["drift", "outside_root"]
    with pytest.raises(ValueError, match="repository-relative"):
        attempt_review.review(tmp_path, studies=["../outside"])
    (tmp_path / "link").symlink_to(Path(tmp_path).parent, target_is_directory=True)
    with pytest.raises(ValueError, match="outside repository"):
        attempt_review.review(tmp_path, studies=["link/elsewhere"])


def test_missing_and_invalid_files_do_not_mean_zero_attempts(tmp_path):
    family = "absent"
    missing = attempt_review.review(tmp_path, family=family)
    assert missing["complete"] is False
    assert missing["ledgers"][0]["source"]["status"] == "missing"
    _put(tmp_path, "study/contract.json", "{invalid")
    broken = attempt_review.review(tmp_path, studies=["study"])
    assert broken["complete"] is False
    assert broken["studies"][0]["errors"][0]["status"] == "invalid_json"
    empty = attempt_review.review(tmp_path, studies=["empty"])
    assert empty["complete"] is False
    assert all(x["status"] == "missing" for x in empty["studies"][0]["files"])


def test_term_filters_only_family_headers(tmp_path):
    for family in ("risk-tail", "price-trend"):
        _put(
            tmp_path,
            attempt_review._family_path(family),
            json.dumps({"event": "family", "family": family, "budget": {"real_runs": 1}}) + "\n",
        )
    result = attempt_review.review(tmp_path, term="risk")
    assert [x["family"] for x in result["ledgers"]] == ["risk-tail"]
    assert result["ledgers"][0]["budget"] == {"real_runs": 1}


def test_explicit_not_applicable_and_study_file_allowlist(tmp_path):
    _put(
        tmp_path,
        "study/contract.json",
        json.dumps(
            {
                "not_applicable_methods": ["risk_source_separation"],
                "question": "input qualification",
            }
        ),
    )
    result = attempt_review.review(tmp_path, studies=["study"])
    assert result["studies"][0]["question"] == "input qualification"
    assert result["methods"]["risk_source_separation"]["status"] == "declared_not_applicable"
    _put(tmp_path, "study/outcome.json", "{}")
    with pytest.raises(ValueError, match="accepts only"):
        attempt_review.review(tmp_path, studies=["study/outcome.json"])


def test_readable_unsettled_journal_without_header_is_not_complete(tmp_path):
    family = "one-start"
    _put(
        tmp_path,
        attempt_review._family_path(family),
        json.dumps({"event": "start", "run_id": "r1"}) + "\n",
    )
    result = attempt_review.review(tmp_path, family=family)
    ledger = result["ledgers"][0]
    assert ledger["read_complete"] is True
    assert ledger["complete"] is False
    assert ledger["evidence_identity_complete"] is False
    assert ledger["seen_history"] == "unknown"
    assert {e["error"] for e in ledger["errors"]} == {
        "missing_family_header",
        "unsettled_or_duplicate_run:r1",
    }
    assert result["methods"]["all_attempts"]["status"] == "incomplete_source"


def test_conflicting_family_header_is_not_complete(tmp_path):
    family = "one-family"
    _put(
        tmp_path,
        attempt_review._family_path(family),
        "\n".join(
            json.dumps(x)
            for x in (
                {"event": "family", "family": family, "budget": {}},
                {"event": "family", "family": "other", "budget": {}},
            )
        )
        + "\n",
    )
    ledger = attempt_review.review(tmp_path, family=family)["ledgers"][0]
    assert ledger["complete"] is False
    assert any(e["error"] == "conflicting family header" for e in ledger["errors"])


def test_manifest_only_and_forward_string_remain_unverified(tmp_path):
    _put(tmp_path, "study/manifest.json", json.dumps({"forward": "future-log.json"}))
    result = attempt_review.review(tmp_path, studies=["study"])
    study = result["studies"][0]
    assert study["read_complete"] is True
    assert study["evidence_identity_complete"] is False
    assert study["complete"] is False
    assert result["methods"]["historical_forward_separation"]["status"] == "declared_reference"


def test_binding_files_drift_missing_and_size_limit_block_identity(tmp_path, monkeypatch):
    _put(tmp_path, "data/current.txt", "changed")
    _put(tmp_path, "data/big.txt", "x" * 513)
    contract = {
        "bindings": {
            "files": {
                "data/current.txt": "0" * 64,
                "data/missing.txt": "1" * 64,
                "data/big.txt": "2" * 64,
            }
        },
    }
    _put(tmp_path, "study/contract.json", json.dumps(contract))
    monkeypatch.setattr(attempt_review, "MAX_BYTES", 4096)
    study = attempt_review.review(tmp_path, studies=["study"])["studies"][0]
    assert study["binding_status"] == "drift"
    assert study["complete"] is False
    assert [s["status"] for s in study["source_checks"]] == ["drift", "missing", "drift"]
    monkeypatch.setattr(attempt_review, "MAX_BYTES", 512)
    study = attempt_review.review(tmp_path, studies=["study"])["studies"][0]
    assert study["source_checks"][2]["status"] == "truncated_size_limit"
    assert study["evidence_identity_complete"] is False


def test_independent_study_1024_format_keeps_attempts_and_declarations(tmp_path):
    directory = "docs/experiments/raw/existing-factor-strategy-expansion-2026-10-24"
    _put(tmp_path, "inputs/panel.csv", "qualified\n")
    source_sha = hashlib.sha256(b"qualified\n").hexdigest()
    contract = {
        "question": "Do fixed combinations beat strong components?",
        "scope": ["CN common pool", "US public groups"],
        "definition_refs": ["reference.french.joint.op_inv@1.0.0"],
        "frozen_at": "2026-10-24T13:46:30+08:00",
        "case_selection": "fixed before new outcomes; all history previously seen",
        "status": "frozen_before_effects",
    }
    design = {
        "all_history_previously_seen": True,
        "cn": {"comparators": ["P", "M", "mix"], "primary_months": "full union"},
        "us": {
            "comparators": ["joint alone", "momentum alone"],
            "periods": {"primary": ["201501", "202412"]},
        },
        "acceptance": "narrow clue only against strong alternatives",
    }
    contract_path = _put(tmp_path, f"{directory}/contract.json", json.dumps(contract))
    design_path = _put(tmp_path, f"{directory}/design.json", json.dumps(design))
    _put(
        tmp_path,
        f"{directory}/inputs.json",
        json.dumps({"cn_price_panel": {"path": "inputs/panel.csv", "sha256": source_sha}}),
    )
    _put(
        tmp_path,
        f"{directory}/attempts.json",
        json.dumps(
            [
                {
                    "stage": "input_binding",
                    "status": "corrected_before_effect",
                    "reason": "old receipt mismatch",
                },
                {
                    "stage": "chart_render",
                    "status": "corrected_display_only",
                    "failure": "glyph warning",
                    "fix": "font changed",
                },
            ]
        ),
    )
    _put(
        tmp_path,
        f"{directory}/freeze.json",
        json.dumps(
            {
                "frozen_at": "2026-10-24T13:46:31+08:00",
                "code_and_design": [
                    {
                        "path": f"{directory}/contract.json",
                        "sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
                    },
                    {
                        "path": f"{directory}/design.json",
                        "sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
                    },
                ],
            }
        ),
    )
    _put(
        tmp_path,
        f"{directory}/completion.json",
        json.dumps({"status": "completed_bounded_questions", "core_batches_used": 1}),
    )
    _put(
        tmp_path,
        f"{directory}/result-locator.json",
        json.dumps(
            {
                "status": "completed",
                "commands": [{"argv": ["python", "cn.py"], "exit_code": 0}],
                "output": "/Volumes/external/result",
                "files": [{"path": "private.csv"}],
            }
        ),
    )
    result = attempt_review.review(tmp_path, studies=[directory])
    study = result["studies"][0]
    assert study["read_complete"] is True
    assert study["evidence_identity_complete"] is True
    assert study["scientific_effect_status"] == "not_evaluated_by_index"
    assert study["scope"] == contract["scope"]
    assert study["objects"] == contract["definition_refs"]
    assert study["freeze"] == contract["frozen_at"]
    assert study["seen_history_declaration"] == contract["case_selection"]
    assert study["results_seen"] == "unknown"
    assert study["attempt_count"] == 2
    assert study["attempts"][1]["failure"] == "glyph warning"
    assert study["attempt_scope"] == "declared_study_attempts_only"
    assert study["core_batches_used_declaration"] == 1
    assert study["design"]["comparators"]["cn"] == ["P", "M", "mix"]
    assert study["design"]["periods"]["us"]["primary"] == ["201501", "202412"]
    assert study["result_locator"]["commands"][0]["exit_code"] == 0
    assert study["result_locator"]["output_followed"] is False
    assert study["result_locator"]["files_declared_count"] == 1
    assert result["methods"]["all_attempts"]["status"] == "declared_reference"
    assert result["methods"]["strong_baseline"]["status"] == "declared_reference"


def test_independent_study_incomplete_freeze_cannot_promote(tmp_path):
    directory = "study"
    _put(tmp_path, f"{directory}/contract.json", json.dumps({"scope": ["CN"]}))
    for name, value in {
        "inputs.json": {},
        "attempts.json": [],
        "freeze.json": {"code_and_design": []},
        "completion.json": {},
        "design.json": {},
        "result-locator.json": {},
    }.items():
        _put(tmp_path, f"{directory}/{name}", json.dumps(value))
    study = attempt_review.review(tmp_path, studies=[directory])["studies"][0]
    assert study["read_complete"] is True
    assert study["binding_status"] == "unknown"
    assert study["evidence_identity_complete"] is False
    assert study["source_checks"][0]["status"] == "unrecognized_source_entry"
