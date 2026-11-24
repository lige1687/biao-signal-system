import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lei_signal.research.preparation import build_context


ROOT = Path(__file__).resolve().parents[2]
CASES = "docs/research/methods/research-method-cases/cases"


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _case(root, case_id, *, title="宽度风险", status="rejected", references=()):
    value = {
        "id": case_id, "title": title, "problem": "宽度资料资格不明", "scope": "两只ETF",
        "status": status, "before_after": {"old_result": "失败", "new_result": "未采纳"},
        "references": list(references), "object_states": ["mixed.asset.total_return@1.0.0: exists"],
    }
    _write(root / CASES / f"{case_id}.json", json.dumps(value, ensure_ascii=False))
    return value


def _fixture(tmp_path):
    standards = json.loads((ROOT / "docs/research/current-standards.json").read_text())
    _write(tmp_path / "docs/research/current-standards.json", json.dumps(standards))
    registry = ROOT / standards["definition_registry"]
    _write(tmp_path / standards["definition_registry"], registry.read_text())
    return tmp_path


def test_exact_definition_expands_profile_and_dependencies(tmp_path):
    root = _fixture(tmp_path)
    result = build_context(root, definition_refs=["mixed.asset.total_return@1.0.0"])
    cards = result["definitions"]
    assert [card["ref"] for card in cards] == ["mixed.asset.total_return@1.0.0", "mixed.price.economic@1.0.0"]
    assert cards[0]["card"]["input"]["currency"]
    assert cards[0]["card"]["dependencies"] == ["mixed.price.economic@1.0.0"]
    assert result["execution_authorized"] is False


def test_unknown_version_and_latest_are_rejected(tmp_path):
    root = _fixture(tmp_path)
    for ref in ("mixed.asset.total_return@9.9.9", "mixed.asset.total_return@latest"):
        with pytest.raises(ValueError, match="unknown exact definition version"):
            build_context(root, definition_refs=[ref])


def test_idea_without_definition_and_no_match_are_explicit(tmp_path):
    root = _fixture(tmp_path)
    (root / CASES).mkdir(parents=True)
    result = build_context(root, terms=["完全无关的想法"])
    assert result["definition_status"] == "idea_definition_only"
    assert result["case_search"]["matched_count"] == 0
    assert "不等于" in result["case_search"]["no_match_note"]
    assert len(result["financial_review_prompts"]) == 6


def test_empty_query_is_rejected(tmp_path):
    root = _fixture(tmp_path)
    for terms in ((), ("  ",)):
        with pytest.raises(ValueError, match="at least one"):
            build_context(root, terms=terms)


def test_term_match_truncation_and_rejected_case_retained(tmp_path):
    root = _fixture(tmp_path)
    _case(root, "rmc-b", title="宽度样本B")
    _case(root, "rmc-a", title="宽度样本A")
    result = build_context(root, terms=["宽度"], limit=1)
    search = result["case_search"]
    assert (search["scanned_count"], search["matched_count"], search["truncated_count"]) == (2, 2, 1)
    assert search["undisplayed_ids"] == ["rmc-b"]
    case = result["cases"][0]
    assert case["status"] == "rejected" and case["before_after"]["old_result"] == "失败"
    assert case["match_reasons"] and case["scope"] == "两只ETF"


def test_explicit_case_takes_priority_over_limit(tmp_path):
    root = _fixture(tmp_path)
    _case(root, "rmc-a", title="宽度样本A")
    _case(root, "rmc-b", title="宽度样本B")
    result = build_context(root, terms=["宽度"], case_ids=["rmc-b"], limit=1)
    assert [case["id"] for case in result["cases"]] == ["rmc-b"]


def test_explicit_case_and_reference_issues_do_not_write_inputs(tmp_path):
    root = _fixture(tmp_path)
    good = _write(root / "docs/experiments/source.md", "原报告")
    _case(root, "rmc-specific", references=["docs/experiments/source.md", "docs/experiments/missing.md", "../outside.md"])
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    result = build_context(root, case_ids=["rmc-specific"])
    bindings = result["cases"][0]["source_bindings"]
    assert bindings[0]["actual_sha256"] == hashlib.sha256(good.read_bytes()).hexdigest()
    assert [b["status"] for b in bindings] == ["present", "missing", "outside_root"]
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    assert after == before


def test_selected_definition_source_drift_is_reported(tmp_path):
    root = _fixture(tmp_path)
    registry = json.loads((root / "docs/research/definitions.v1.json").read_text())
    source_path = registry["sources"]["mixed_code"]["path"]
    _write(root / source_path, "changed source bytes")
    result = build_context(root, definition_refs=["mixed.asset.total_return@1.0.0"])
    bindings = [b for card in result["definitions"] for b in card["source_bindings"]]
    assert any(b["status"] == "drift" and b["path"] == source_path for b in bindings)


def test_case_symlink_outside_root_is_not_read(tmp_path):
    root = _fixture(tmp_path / "root")
    outside = _write(tmp_path / "outside.json", json.dumps({"id": "rmc-leak", "title": "secret"}))
    link = root / CASES / "rmc-leak.json"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    result = build_context(root, terms=["secret"])
    assert result["case_search"]["matched_count"] == 0
    assert any(issue["status"] == "outside_root" for issue in result["issues"])


@pytest.mark.parametrize("kind", ["missing", "file", "outside_symlink"])
def test_unavailable_case_library_is_not_zero_match(tmp_path, kind):
    root = _fixture(tmp_path / "root")
    library = root / CASES
    if kind == "file":
        _write(library, "not a directory")
    elif kind == "outside_symlink":
        outside = tmp_path / "outside-cases"
        outside.mkdir()
        _write(outside / "rmc-secret.json", json.dumps({"id": "rmc-secret", "title": "secret"}))
        library.parent.mkdir(parents=True, exist_ok=True)
        library.symlink_to(outside, target_is_directory=True)
    result = build_context(root, terms=["secret"])
    assert result["case_search"]["search_available"] is False
    assert result["case_search"]["no_match_note"] != "无命中不等于没有风险；可用准确案例ID补查。"
    assert any(issue["status"] == "case_library_unavailable" for issue in result["issues"])
    assert result["execution_authorized"] is False


def test_valid_empty_case_library_is_a_real_zero_match(tmp_path):
    root = _fixture(tmp_path)
    (root / CASES).mkdir(parents=True)
    result = build_context(root, terms=["宽度"])
    assert result["case_search"]["search_available"] is True
    assert result["case_search"]["scanned_count"] == 0
    assert result["case_search"]["matched_count"] == 0


def test_cli_stdout_json_and_no_workflow_import(tmp_path):
    root = _fixture(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    code = "import sys; from lei_signal.research.preparation import main; main(['--root', sys.argv[1], '--term', '宽度']); assert 'lei_signal.research.workflow' not in sys.modules"
    run = subprocess.run([sys.executable, "-c", code, str(root)], env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["execution_authorized"] is False
