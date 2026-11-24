import hashlib

import pytest


def reader():
    from lei_signal.research.llm_output_review import read_evidence
    return read_evidence


def test_exact_source_pointer_and_hash(tmp_path):
    raw = b'{"a/b": {"~key": [0, false, 2.5]}}'
    (tmp_path / "saved.json").write_bytes(raw)
    value, binding = reader()(tmp_path, {
        "path": "saved.json", "sha256": hashlib.sha256(raw).hexdigest(),
        "pointer": "/a~1b/~0key/2",
    })
    assert value == 2.5
    assert binding["status"] == "matched"
    assert binding["pointer"] == "/a~1b/~0key/2"


@pytest.mark.parametrize("damage", [
    "hash", "traversal", "absolute", "pointer", "nonfinite", "duplicate", "oversize",
])
def test_invalid_evidence_cannot_be_reviewed(tmp_path, damage):
    raw = b'{"x": [1]}'
    if damage == "duplicate":
        raw = b'{"x": 1, "x": 2}'
    if damage == "nonfinite":
        raw = b'{"x": NaN}'
    if damage == "oversize":
        raw = b' ' * (1048576 + 1)
    path = tmp_path / "saved.json"
    path.write_bytes(raw)
    ref = {"path": "saved.json", "sha256": hashlib.sha256(raw).hexdigest(), "pointer": "/x"}
    if damage == "hash":
        ref["sha256"] = "0" * 64
    if damage == "traversal":
        ref["path"] = "../saved.json"
    if damage == "absolute":
        ref["path"] = str(path)
    if damage == "pointer":
        ref["pointer"] = "/x/01"
    with pytest.raises(ValueError):
        reader()(tmp_path, ref)


def test_symbolic_escape_is_rejected(tmp_path):
    inner = tmp_path / "repo"
    inner.mkdir()
    (tmp_path / "other.json").write_text("{}")
    (inner / "link.json").symlink_to(tmp_path / "other.json")
    with pytest.raises(ValueError, match="inside"):
        reader()(inner, {"path": "link.json", "sha256": "0" * 64, "pointer": ""})


def test_missing_request_is_blocked_without_authority(tmp_path):
    from lei_signal.research.llm_output_review import review_file
    result = review_file(tmp_path, "missing.json")
    assert result["status"] == "blocked"
    assert result["execution_authorized"] is False


def test_dispatches_requested_review_and_marks_other_not_requested(tmp_path, monkeypatch):
    from lei_signal.research.llm_output_review import review_outputs
    monkeypatch.setattr("lei_signal.research.llm_perturbation_review.review_perturbations",
                        lambda root, request: {"status": "complete_for_manual_review"})
    result = review_outputs(tmp_path, {"schema": "llm-output-review/1", "perturbation": {}})
    assert result["perturbation"]["status"] == "complete_for_manual_review"
    assert result["timing"]["status"] == "not_requested"
    assert result["execution_authorized"] is False


def test_empty_request_does_not_claim_completion(tmp_path):
    from lei_signal.research.llm_output_review import review_outputs
    assert review_outputs(tmp_path, {"schema": "llm-output-review/1"})["status"] == "blocked"
