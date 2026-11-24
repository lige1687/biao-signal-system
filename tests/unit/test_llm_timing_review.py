"""Synthetic saved-answer boundaries; no model calls or market efficacy claims."""

import copy
import hashlib
import json

import pytest

from lei_signal.research import llm_timing_review as module


def save(root, name, value):
    path = root / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "pointer": ""}


@pytest.fixture
def case(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("synthetic publication fixture")
    common = {
        "code": "TEST",
        "metric": "sales",
        "period_end": "2023-12-31",
        "unit": "CNY",
        "retrieved_at": "2026-11-01T10:00:00+08:00",
        "source": {
            "path": "source.txt",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "locator": "synthetic fixture",
        },
    }
    bundle = {
        "schema": "financial-source-versions/1",
        "publication_timezone": "Asia/Shanghai",
        "records": [
            {
                **common,
                "version": "v1",
                "value": "100",
                "published_at": "2024-03-27T09:00:00+08:00",
                "vendor_available_at": "2024-03-28T09:00:00+08:00",
            },
            {
                **common,
                "version": "v2",
                "value": "110",
                "published_at": "2025-03-27T09:00:00+08:00",
                "vendor_available_at": "2025-03-28T09:00:00+08:00",
            },
        ],
        "coverage": [
            {
                "code": "TEST",
                "metric": "sales",
                "period_ends": ["2023-12-31"],
                "complete_versions": True,
                "complete_periods": True,
                "as_of": "2026-11-01T10:00:00+08:00",
            }
        ],
    }
    claim = {
        "data_mode": "synthetic",
        "question_mode": "exact",
        "decision_at": "2024-06-01T09:30:00+08:00",
        "availability_basis": "public",
        "code": "TEST",
        "metric": "sales",
        "period_end": "2023-12-31",
        "requested_period_end": "2023-12-31",
        "version": "v1",
        "value": "100",
        "unit": "CNY",
        "answer_identity": {"model": "fixture", "model_version": "v0", "response_id": "one"},
        "answer_origin": "model",
        "raw_answer": "Synthetic saved answer: sales 100 CNY in 2023.",
        "answer_locator": {"pointer": ""},
    }

    def run(claims=None):
        catalog = save(tmp_path, "catalog.json", bundle)
        refs = [save(tmp_path, f"claim-{i}.json", row) for i, row in enumerate(claims or [claim])]
        return module.review_timing(
            tmp_path, {"schema": "llm-timing-review/1", "catalog": catalog, "claims": refs}
        )

    return tmp_path, bundle, claim, run


def test_future_and_stale_are_separate_and_repeated_answers_not_independent(case):
    _, _, claim, run = case
    future = {**claim, "version": "v2", "value": "110"}
    stale = {**claim, "decision_at": "2025-06-01T09:30:00+08:00"}
    another = copy.deepcopy(stale)
    another["answer_identity"]["response_id"] = "two"
    out = run([future, stale, another])
    assert [row["timing_status"] for row in out["claims"]] == [
        "future_reference",
        "stale_version",
        "stale_version",
    ]
    counts = out["summary"]["synthetic"]
    assert counts["future_reference"] == 1
    assert counts["stale_version"] == 2
    assert counts["eligible_claim_count"] == 3
    assert counts["decision_group_count"] == 2
    assert out["real_error_rate"] == "not_evaluated"
    assert out["run_authorized"] is False


@pytest.mark.parametrize(
    "cutoff,status",
    [("2024-03-27T01:00:00+00:00", "future_reference"), ("2024-03-27T09:00:01+08:00", "matched")],
)
def test_timezone_and_strict_equal_boundary(case, cutoff, status):
    _, _, claim, run = case
    claim["decision_at"] = cutoff
    assert run()["claims"][0]["timing_status"] == status


def test_date_only_same_day_and_vendor_delay_remain_unavailable(case):
    _, bundle, claim, run = case
    bundle["records"][0]["published_at"] = "2024-03-27"
    claim["decision_at"] = "2024-03-27T12:00:00+08:00"
    assert run()["claims"][0]["timing_status"] == "unresolved"
    bundle["records"][0]["published_at"] = "2024-03-27T09:00:00+08:00"
    assert run()["claims"][0]["timing_status"] == "matched"
    claim["availability_basis"] = "vendor"
    assert run()["claims"][0]["timing_status"] == "future_reference"
    bundle["records"][0]["vendor_available_at"] = None
    assert run()["claims"][0]["timing_status"] == "unresolved"


def test_latest_period_precedes_old_period_later_revision(case):
    _, bundle, claim, run = case
    newer = {
        **bundle["records"][0],
        "period_end": "2024-12-31",
        "version": "v1",
        "value": "200",
        "published_at": "2025-03-01T09:00:00+08:00",
        "vendor_available_at": "2025-03-02T09:00:00+08:00",
    }
    bundle["records"].append(newer)
    bundle["coverage"][0]["period_ends"].append("2024-12-31")
    claim.update(
        question_mode="latest", decision_at="2025-06-01T09:30:00+08:00", version="v2", value="110"
    )
    assert run()["claims"][0]["timing_status"] == "stale_period"
    claim.update(period_end="2024-12-31", version="v1", value="200")
    assert run()["claims"][0]["timing_status"] == "matched"
    claim.update(question_mode="exact", requested_period_end="2023-12-31")
    assert run()["claims"][0]["fact_mismatch"] is True


@pytest.mark.parametrize("damage", ["absent", "versions", "periods", "as_of", "period_list"])
def test_missing_coverage_never_counts_fresh_or_stale(case, damage):
    _, bundle, claim, run = case
    claim.update(question_mode="latest", decision_at="2025-06-01T09:30:00+08:00")
    if damage == "absent":
        del bundle["coverage"]
    elif damage == "as_of":
        bundle["coverage"][0]["as_of"] = "2024-06-01T09:30:00+08:00"
    elif damage == "period_list":
        bundle["coverage"][0]["period_ends"] = []
    else:
        bundle["coverage"][0]["complete_" + damage] = False
    out = run()
    assert out["claims"][0]["timing_status"] == "unresolved"
    assert out["summary"]["synthetic"]["eligible_claim_count"] == 0
    assert out["status"] == "reviewed"
    assert out["assessment_complete"] is False


def test_fact_mismatch_is_separate_from_timing_and_modes_separate(case):
    _, _, claim, run = case
    real = {
        **claim,
        "data_mode": "real",
        "value": "999",
        "unit": "USD",
        "answer_identity": {**claim["answer_identity"], "response_id": "real-response"},
    }
    out = run([claim, real])
    assert out["claims"][1]["timing_status"] == "matched"
    assert out["claims"][1]["fact_mismatch"] is True
    assert out["summary"]["real"]["saved_answer_fragment_count"] == 1
    assert out["summary"]["synthetic"]["saved_answer_fragment_count"] == 1


@pytest.mark.parametrize("damage", ["external", "hash", "large"])
def test_source_is_validated_before_legacy_reader(case, monkeypatch, damage):
    root, bundle, _, run = case
    if damage == "external":
        bundle["records"][0]["source"]["path"] = "../outside.txt"
    elif damage == "hash":
        bundle["records"][0]["source"]["sha256"] = "0" * 64
    else:
        (root / "source.txt").write_bytes(b"x" * (1024 * 1024 + 1))

    def unsafe_read(*args, **kwargs):
        pytest.fail("unsafe source reached legacy loader")

    monkeypatch.setattr(module, "load_bundle", unsafe_read)
    with pytest.raises(ValueError):
        run()


def test_source_drift_during_legacy_load_is_rejected(case, monkeypatch):
    root, _, _, run = case
    original = module.load_bundle

    def drifting(path):
        result = original(path)
        (root / "source.txt").write_text("changed")
        return result

    monkeypatch.setattr(module, "load_bundle", drifting)
    with pytest.raises(ValueError, match="source"):
        run()


@pytest.mark.parametrize("damage", ["fallback", "raw", "identity", "locator", "timezone"])
def test_original_answer_binding_required(case, damage):
    _, _, claim, run = case
    if damage == "fallback":
        claim["answer_origin"] = "fallback_template"
    elif damage == "raw":
        claim["raw_answer"] = ""
    elif damage == "identity":
        del claim["answer_identity"]["model_version"]
    elif damage == "locator":
        claim["answer_locator"]["pointer"] = "/other"
    else:
        claim["decision_at"] = "2024-06-01T09:30:00"
    with pytest.raises(ValueError):
        run()


def test_claim_limit_and_no_empty_denominator(case):
    root, bundle, claim, _ = case
    request = {
        "schema": "llm-timing-review/1",
        "catalog": save(root, "catalog.json", bundle),
        "claims": [],
    }
    with pytest.raises(ValueError):
        module.review_timing(root, request)
    request["claims"] = [save(root, "claim.json", claim)] * 101
    with pytest.raises(ValueError):
        module.review_timing(root, request)


@pytest.mark.parametrize("copied_wrapper", [False, True])
def test_duplicate_fragments_are_retained_but_excluded_from_all_denominators(case, copied_wrapper):
    root, bundle, claim, _ = case
    first = save(root, "first.json", claim)
    if copied_wrapper:
        copied = copy.deepcopy(claim)
        copied["wrapper_note"] = "copied packaging, same model response and fact"
        second = save(root, "copy.json", copied)
    else:
        second = first
    out = module.review_timing(
        root,
        {
            "schema": "llm-timing-review/1",
            "catalog": save(root, "catalog.json", bundle),
            "claims": [first, second],
        },
    )
    assert len(out["claims"]) == 2
    assert out["claims"][1]["duplicate"] is True
    assert out["claims"][1]["duplicate_of"] == 0
    counts = out["summary"]["synthetic"]
    assert counts["input_reference_count"] == 2
    assert counts["duplicate_count"] == 1
    assert counts["saved_answer_fragment_count"] == 1
    assert counts["eligible_claim_count"] == 1
    assert counts["matched"] == 1
    assert counts["decision_group_count"] == 1
    assert out["structured_claim_extraction_verified"] is False


@pytest.mark.parametrize("field,value", [("value", "999"), ("version", "v2"), ("unit", "USD")])
def test_conflicting_response_fact_invalidates_whole_group(case, field, value):
    _, _, claim, run = case
    conflict = {**claim, field: value}
    out = run([claim, conflict, copy.deepcopy(claim)])
    assert out["assessment_complete"] is False
    assert all(row["conflicting_duplicate"] for row in out["claims"])
    assert all(row["timing_status"] == "unresolved" for row in out["claims"])
    assert all(row["reason"] == "conflicting_duplicate" for row in out["claims"])
    assert not any(row["included_in_denominators"] for row in out["claims"])
    counts = out["summary"]["synthetic"]
    assert counts["conflicting_duplicate_count"] == 3
    assert counts["eligible_claim_count"] == 0
    assert counts["saved_answer_fragment_count"] == 0
    assert counts["matched"] == 0
    assert counts["decision_group_count"] == 0
    if field != "version":
        assert out["claims"][1]["fact_mismatch"] is True


@pytest.mark.parametrize("field", ["model", "model_version", "response_id"])
@pytest.mark.parametrize("unknown", ["unknown", "null", "none", "n/a", " UNKNOWN "])
def test_unknown_model_identity_is_not_saved_model_evidence(case, field, unknown):
    _, _, claim, run = case
    claim["answer_identity"][field] = unknown
    with pytest.raises(ValueError, match="unknown"):
        run()
