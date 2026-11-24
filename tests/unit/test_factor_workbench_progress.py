"""The progress endpoint must not promote stale or unlinked evidence."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lei_signal.factor_workbench import app as app_module
from lei_signal.factor_workbench.progress import STAGE_IDS, build_progress


def _write(path: Path, value: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    return hashlib.sha256(value.encode()).hexdigest()


def _case(cid: str, source_id: str) -> dict:
    stages = [{"id": sid, "title": sid, "status": "done", "summary": "保存的判断",
               "sourceIds": [source_id]} for sid in STAGE_IDS]
    return {
        "id": cid, "kind": "factor", "title": "同名因子", "researchVersion": "r1",
        "definitionRefs": [], "purpose": "排序", "universe": "固定样本", "period": "历史",
        "poolIds": [], "execution": {"state": "completed", "label": "已完成报价比较"},
        "conclusion": {"state": "unsupported", "text": "本用途未支持增加条件"},
        "bottleneck": {"scope": "扩大用途", "kind": "validation", "title": "新时期资料",
                       "detail": "未验证", "nextAction": "取得资料后验证", "dependency": "新资料",
                       "sourceIds": [source_id]},
        "currentStageId": "decision", "stages": stages,
        "timeline": [{"date": "2026-10-22", "label": "报告", "sourceIds": [source_id]}],
        "evidenceAsOf": "2025-12-31", "sourceIds": [source_id], "limitations": ["固定样本"],
    }


@pytest.fixture
def saved(tmp_path: Path) -> tuple[Path, Path, dict]:
    a = "docs/experiments/a.md"
    b = "docs/experiments/b.md"
    data = {
        "schemaVersion": 1, "reviewedAt": "2026-10-24T09:00:00+08:00",
        "projectionNote": "人工核对已有记录",
        "sources": [
            {"id": "a", "title": "A", "path": a, "sha256": _write(tmp_path / a, "A"),
             "sourceDate": "2026-10-22", "locator": "section A"},
            {"id": "b", "title": "B", "path": b, "sha256": _write(tmp_path / b, "B"),
             "sourceDate": "2026-10-22", "locator": "section B"},
        ],
        "cases": [_case("one", "a"), _case("two", "b")],
    }
    evidence = tmp_path / "docs/experiments/projection.json"
    evidence.write_text(json.dumps(data, ensure_ascii=False))
    return tmp_path, evidence, data


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False))


def test_verified_completed_and_unsupported_can_coexist(saved):
    root, path, _ = saved
    output = build_progress(root, path.relative_to(root))
    assert output["cases"][0]["execution"]["state"] == "completed"
    assert output["cases"][0]["conclusion"]["state"] == "unsupported"
    assert output["cases"][0]["integrity"] == "verified"
    assert output["sources"][0]["status"] == "verified"
    assert output["checkedAt"] != output["reviewedAt"]
    assert output["cases"][0]["evidenceAsOf"] == "2025-12-31"


def test_changed_source_only_downgrades_dependent_case(saved):
    root, path, _ = saved
    (root / "docs/experiments/a.md").write_text("changed")
    output = build_progress(root, path)
    first, second = output["cases"]
    assert first["integrity"] == "changed"
    assert first["execution"] == {"state": "unknown", "label": "待重新核对"}
    assert first["conclusion"]["state"] == "unknown"
    assert first["bottleneck"]["title"] == "证据需复核"
    assert all(x["status"] == "unknown" for x in first["stages"])
    assert second["integrity"] == "verified"
    assert second["conclusion"]["state"] == "unsupported"


def test_changed_source_only_downgrades_stages_that_cite_it(saved):
    root, path, data = saved
    data["cases"][0]["sourceIds"] = ["a", "b"]
    data["cases"][0]["stages"][1]["sourceIds"] = ["b"]
    _save(path, data)
    (root / "docs/experiments/a.md").write_text("changed")
    stages = build_progress(root, path)["cases"][0]["stages"]
    assert stages[0]["status"] == "unknown"
    assert stages[1]["status"] == "done"


def test_missing_source_does_not_break_other_case(saved):
    root, path, _ = saved
    (root / "docs/experiments/a.md").unlink()
    output = build_progress(root, path)
    assert output["sources"][0]["status"] == "missing"
    assert output["cases"][0]["integrity"] == "missing"
    assert output["cases"][1]["integrity"] == "verified"


@pytest.mark.parametrize("unsafe", ["/etc/passwd", "../outside", "docs/experiments/../../x", "data/a.md"])
def test_unsafe_source_path_rejected(saved, unsafe):
    root, path, data = saved
    data["sources"][0]["path"] = unsafe
    _save(path, data)
    with pytest.raises(ValueError, match="unsafe_source_path"):
        build_progress(root, path)


def test_symlink_escape_rejected(saved):
    root, path, data = saved
    outside = root.parent / "outside.md"
    outside.write_text("outside")
    link = root / "docs/experiments/link.md"
    link.symlink_to(outside)
    data["sources"][0]["path"] = "docs/experiments/link.md"
    _save(path, data)
    with pytest.raises(ValueError, match="unsafe_source_path"):
        build_progress(root, path)


def test_symlink_into_disallowed_repo_area_rejected(saved):
    root, path, data = saved
    secret = root / "private/local.md"
    _write(secret, "private")
    link = root / "docs/experiments/link.md"
    link.symlink_to(secret)
    data["sources"][0]["path"] = "docs/experiments/link.md"
    _save(path, data)
    with pytest.raises(ValueError, match="unsafe_source_path"):
        build_progress(root, path)


def test_same_title_different_ids_are_valid(saved):
    root, path, _ = saved
    output = build_progress(root, path)
    assert len({x["id"] for x in output["cases"]}) == 2
    assert len({x["title"] for x in output["cases"]}) == 1


def test_file_presence_never_upgrades_saved_unknown(saved):
    root, path, data = saved
    data["cases"][0]["execution"] = {"state": "unknown", "label": "未核对"}
    data["cases"][0]["conclusion"] = {"state": "not_evaluated", "text": "未评价"}
    _save(path, data)
    output = build_progress(root, path)
    assert output["cases"][0]["execution"]["state"] == "unknown"
    assert output["cases"][0]["conclusion"]["state"] == "not_evaluated"


def test_empty_evidence_done_and_invalid_reference_rejected(saved):
    root, path, data = saved
    data["cases"][0]["stages"][0]["sourceIds"] = []
    _save(path, data)
    with pytest.raises(ValueError, match="missing_stage_sourceIds_evidence"):
        build_progress(root, path)
    data["cases"][0]["stages"][0]["sourceIds"] = ["absent"]
    _save(path, data)
    with pytest.raises(ValueError, match="invalid_stage_sourceIds_reference"):
        build_progress(root, path)


def test_bad_schema_duplicate_id_and_bad_stage_order_rejected(saved):
    root, path, data = saved
    for change, error in [
        (lambda d: d.update(schemaVersion=2), "invalid_progress_schema"),
        (lambda d: d["cases"][1].update(id="one"), "duplicate_case_id"),
        (lambda d: d["cases"][0]["stages"].reverse(), "invalid_stage_order"),
    ]:
        draft = deepcopy(data)
        change(draft)
        _save(path, draft)
        with pytest.raises(ValueError, match=error):
            build_progress(root, path)


def test_catalog_selection_must_be_exact(saved):
    root, path, data = saved
    catalog = root / "web/public/research/factor-curve-library-20261022/catalog.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(json.dumps({"datasets": [{"id": "set", "factors": [{"id": "f"}],
                                                 "stockPools": [{"id": "all"}]}]}))
    case = data["cases"][0]
    case.update(datasetId="set", factorId="f", poolIds=["all"])
    _save(path, data)
    assert build_progress(root, path)["cases"][0]["integrity"] == "verified"
    case["poolIds"] = ["invented"]
    _save(path, data)
    with pytest.raises(ValueError, match="unknown_pool"):
        build_progress(root, path)


def test_get_progress_returns_checked_snapshot_without_model_call(saved, monkeypatch):
    root, path, _ = saved
    monkeypatch.setattr(app_module, "ROOT", root)
    monkeypatch.setattr(app_module, "build_progress", lambda project_root: build_progress(project_root, path))
    monkeypatch.setattr(app_module, "invoke_selection", lambda *args: pytest.fail("GET called model"))
    monkeypatch.setattr(app_module.llm, "load_ark_config", lambda: pytest.fail("GET loaded model"))
    app_module._requests = 0
    with TestClient(app_module.app) as client:
        before = client.get("/api/factor-workbench/health").json()["modelRequests"]
        response = client.get("/api/factor-workbench/progress")
        after = client.get("/api/factor-workbench/health").json()["modelRequests"]
    assert response.status_code == 200
    assert len(response.json()["cases"]) == 2
    assert all(x["integrity"] == "verified" for x in response.json()["cases"])
    assert before == after == 0


def test_get_progress_downgrades_changed_source(saved, monkeypatch):
    root, path, _ = saved
    monkeypatch.setattr(app_module, "ROOT", root)
    monkeypatch.setattr(app_module, "build_progress", lambda project_root: build_progress(project_root, path))
    (root / "docs/experiments/a.md").write_text("changed")
    with TestClient(app_module.app) as client:
        response = client.get("/api/factor-workbench/progress")
    assert response.status_code == 200
    first, second = response.json()["cases"]
    assert first["integrity"] == "changed"
    assert first["execution"]["state"] == "unknown"
    assert first["conclusion"]["state"] == "unknown"
    assert second["integrity"] == "verified"
    assert second["conclusion"]["state"] == "unsupported"


def test_get_progress_rejects_invalid_saved_projection(saved, monkeypatch):
    root, path, data = saved
    monkeypatch.setattr(app_module, "ROOT", root)
    monkeypatch.setattr(app_module, "build_progress", lambda project_root: build_progress(project_root, path))
    data["schemaVersion"] = 999
    _save(path, data)
    with TestClient(app_module.app) as client:
        response = client.get("/api/factor-workbench/progress")
    assert response.status_code == 422
