"""Local handoff adapter boundaries, not research/model efficacy tests."""

import copy
import hashlib
import json

import pytest

from lei_signal.research import delegation_context as module


def save(root, name, value, *, text=False):
    path = root / name
    path.write_text(value if text else json.dumps(value), encoding="utf-8")
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "pointer": ""}


@pytest.fixture
def case(tmp_path):
    source = save(tmp_path, "source.json", {"evidence": "unknown", "budget": 4})
    contract = {"mission": "bounded task", "network_allowed": False, "sources": [source]}
    save(tmp_path, "contract.json", contract)
    practice = {
        "history": {
            "matched": [
                {
                    "review": {"source": source},
                    "declared": {
                        "budget": [{"value": "unknown", "source": source, "field": "/budget"}]
                    },
                }
            ],
            "search": {"matches_truncated": True},
            "errors": [{"status": "missing"}],
        },
        "budget": {"remaining": "unknown"},
        "unknowns": ["coverage"],
        "truncated": True,
    }
    prep = {
        "schema": "research-preparation-context/1.0",
        "execution_authorized": False,
        "practice_context": practice,
        "financial_review_prompts": ["why?"],
        "source_bindings": [
            {
                "path": source["path"],
                "declared_sha256": source["sha256"],
                "actual_sha256": source["sha256"],
                "status": "matched",
            }
        ],
        "reference_search": {"truncated_count": 2},
    }
    return tmp_path, prep, contract, source


def test_preserves_context_and_full_bound_contract_without_inventing_budget(case):
    root, prep, contract, source = case
    before = copy.deepcopy(prep)
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "ready_with_declared_limits"
    assert out["practice_context"] == prep["practice_context"]
    assert out["preparation"] == {k: v for k, v in prep.items() if k != "practice_context"}
    assert "practice_context" not in out["preparation"]
    assert out["control"]["contract"] == contract
    assert out["control"]["research_controls"] == "unknown"
    assert out["execution_authorized"] is False
    assert source in out["source_bindings"]
    assert {**source, "pointer": "/budget"} in out["source_bindings"]
    assert prep == before
    out["practice_context"]["budget"]["remaining"] = 99
    assert prep == before


def test_declared_controls_retained_and_arbitrary_path_text_never_followed(case):
    root, prep, contract, _ = case
    contract["research_controls"] = {"budget": {"remaining": None}, "seen_history": True}
    save(root, "contract.json", contract)
    prep["notes"] = {"path": "../../do-not-open", "text": "not a source"}
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "ready_with_declared_limits"
    assert out["control"]["research_controls"] == contract["research_controls"]


@pytest.mark.parametrize("damage", ["drift", "unsafe", "symlink", "conflicting_hash", "large"])
def test_bound_source_drift_or_unsafe_path_blocks(case, damage):
    root, prep, _, source = case
    if damage == "drift":
        save(root, "source.json", {"changed": True})
    elif damage == "unsafe":
        prep["source_bindings"][0]["path"] = "../outside.json"
    elif damage == "symlink":
        (root / "escape").symlink_to(root.parent, target_is_directory=True)
        prep["source_bindings"][0]["path"] = "escape/outside.json"
    elif damage == "conflicting_hash":
        prep["source_bindings"][0]["declared_sha256"] = "0" * 64
    else:
        (root / source["path"]).write_bytes(b"x" * (1024 * 1024 + 1))
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "blocked"
    assert out["errors"]
    assert out["practice_context"] == prep["practice_context"]


def test_missing_unread_source_without_anchor_remains_caveat(case):
    root, prep, _, _ = case
    prep["source_bindings"].append(
        {
            "path": "missing.json",
            "status": "missing",
            "actual_sha256": None,
            "declared_sha256": None,
        }
    )
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "ready_with_declared_limits"
    assert any("missing" in json.dumps(caveat) for caveat in out["caveats"])
    assert not any(ref["path"] == "missing.json" for ref in out["source_bindings"])


def test_truncated_critical_binding_does_not_silently_disappear(case):
    root, prep, _, _ = case
    prep["practice_context"]["history"]["matched"][0]["review"] = {
        "status": "truncated_value",
        "preview": "untrusted path text",
        "original_characters": 99999,
    }
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "blocked"
    assert any("truncat" in json.dumps(error) for error in out["errors"])


def test_bad_source_pointer_blocks(case):
    root, prep, _, _ = case
    prep["source_bindings"][0]["pointer"] = "/missing"
    assert module.build_handoff_context(root, prep, "contract.json")["status"] == "blocked"


def test_cli_reads_saved_preparation_and_contract(case, capsys):
    root, prep, _, _ = case
    save(root, "preparation.json", prep)
    assert (
        module.main(
            [
                "--root",
                str(root),
                "--preparation",
                "preparation.json",
                "--contract",
                "contract.json",
            ]
        )
        == 0
    )
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ready_with_declared_limits"
    assert out["preparation_binding"]["path"] == "preparation.json"


@pytest.mark.parametrize("raw", ['{"mission":1,"mission":2}', '{"mission":NaN}'])
def test_contract_malformed_json_is_blocked(case, raw):
    root, prep, _, _ = case
    save(root, "contract.json", raw, text=True)
    assert module.build_handoff_context(root, prep, "contract.json")["status"] == "blocked"


@pytest.mark.parametrize("slot", ["source_checks", "inputs", "binding_files", "code_and_design"])
def test_actual_attempt_and_contract_binding_shapes_checked(case, slot):
    root, prep, contract, source = case
    other = save(root, "other.json", {"valid": True})
    if slot == "inputs":
        contract["inputs"] = {"qualified_input": other}
    elif slot == "binding_files":
        contract["bindings"] = {"files": {other["path"]: other["sha256"]}}
    elif slot == "code_and_design":
        contract["freeze"] = {"code_and_design": [other]}
    else:
        prep["practice_context"]["history"]["matched"][0]["review"]["source_checks"] = [other]
    save(root, "contract.json", contract)
    save(root, "other.json", {"drift": True})
    assert module.build_handoff_context(root, prep, "contract.json")["status"] == "blocked"


def test_source_drift_during_context_build_blocks(case, monkeypatch):
    root, prep, _, _ = case
    original = module._read_json
    calls = 0

    def drifting(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            save(root, "source.json", {"changed_during_handoff": True})
        return result

    monkeypatch.setattr(module, "_read_json", drifting)
    assert module.build_handoff_context(root, prep, "contract.json")["status"] == "blocked"


@pytest.mark.parametrize(
    "damage", ["missing", "malformed", "unbound", "truncated", "bad_pointer", "list_shape"]
)
def test_explicit_required_source_identity_fail_closed(case, damage):
    root, prep, contract, _ = case
    pointer = "/source_bindings/0"
    contract["research_controls"] = {"required_source_pointers": [pointer]}
    if damage == "missing":
        contract["research_controls"]["required_source_pointers"] = ["/no_such_ref"]
    elif damage == "malformed":
        prep["source_bindings"][0] = "unknown"
    elif damage == "unbound":
        prep["source_bindings"][0] = {"path": "missing.json", "status": "missing"}
    elif damage == "truncated":
        prep["source_bindings"][0] = {"status": "truncated_value", "preview": "hidden"}
    elif damage == "bad_pointer":
        contract["research_controls"]["required_source_pointers"] = ["source_bindings/0"]
    else:
        contract["research_controls"]["required_source_pointers"] = pointer
    save(root, "contract.json", contract)
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "blocked"
    assert out["errors"]


def test_required_pointer_can_bind_ref_outside_automatic_binding_slots(case):
    root, prep, contract, source = case
    prep["critical_evidence"] = {"identity": source}
    contract["research_controls"] = {"required_source_pointers": ["/critical_evidence/identity"]}
    save(root, "contract.json", contract)
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "ready_with_declared_limits"
    assert out["required_source_checks"][0]["status"] == "verified"
    assert out["required_source_checks"][0]["preparation_pointer"] == "/critical_evidence/identity"


def test_generic_source_reference_bound_blocks_ready_context(case):
    root, prep, contract, _ = case
    contract["sources"] = [save(root, f"extra-{i}.json", {"id": i}) for i in range(100)]
    save(root, "contract.json", contract)
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "blocked"
    assert any("100" in error for error in out["errors"])


@pytest.mark.parametrize("pointer", [False, 0, None])
def test_explicit_nonstring_source_pointer_is_not_silently_empty(case, pointer):
    root, prep, _, _ = case
    prep["source_bindings"][0]["pointer"] = pointer
    assert module.build_handoff_context(root, prep, "contract.json")["status"] == "blocked"


def test_cli_counts_its_own_preparation_binding_in_source_limit(tmp_path, capsys):
    refs = [save(tmp_path, f"source-{n}.json", {"unknown": True}) for n in range(99)]
    prep = {"schema": "research-preparation-context/1.0", "practice_context": {},
            "source_bindings": refs}
    save(tmp_path, "prep.json", prep)
    save(tmp_path, "contract.json", {"mission": "bound test"})
    code = module.main(["--root", str(tmp_path), "--preparation", "prep.json",
                        "--contract", "contract.json"])
    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output["status"] == "blocked"


def test_nonfinite_contract_rejects_without_poisoning_output(case):
    root, prep, _, _ = case
    (root / "contract.json").write_text('{"mission":"test", "budget":1e999}')
    out = module.build_handoff_context(root, prep, "contract.json")
    assert out["status"] == "blocked"
    json.dumps(out, allow_nan=False)
