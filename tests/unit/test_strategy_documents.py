from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lei_signal.api import strategy_documents as sd
from lei_signal.api.app import create_app


def _write_fixture(root: Path, home: Path, body: str = "# 总纲\n\n## 道路\n\n## 道路\n") -> str:
    source = home / "Desktop/lei signal doc"
    source.mkdir(parents=True)
    path = source / "LEI 技术交易体系.md"
    path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    config = root / "configs"
    config.mkdir(parents=True)
    (config / "strategy-documents.v1.json").write_text(json.dumps({
        "schema_version": "strategy-documents/1",
        "canonical_directory": "~/Desktop/lei signal doc",
        "documents": [{
            "id": "technical-system", "title": "LEI 技术交易体系",
            "file_name": "LEI 技术交易体系.md", "role": "最高来源",
            "approved_sha256": digest, "confirmed_at": "2026-09-29", "order": 1,
        }],
    }, ensure_ascii=False), encoding="utf-8")
    return digest


def test_read_confirmed_document_and_headings(tmp_path: Path) -> None:
    home = tmp_path / "home"
    digest = _write_fixture(tmp_path, home)
    doc = sd.read_document("technical-system", tmp_path, home)
    assert doc is not None
    assert doc["approvalStatus"] == "confirmed"
    assert doc["currentSha256"] == digest
    assert [h["id"] for h in doc["headings"]] == ["总纲", "道路", "道路-2"]


def test_changed_and_missing_are_reported(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    source = home / "Desktop/lei signal doc/LEI 技术交易体系.md"
    source.write_text("# 已改变\n", encoding="utf-8")
    assert sd.read_document("technical-system", tmp_path, home)["approvalStatus"] == "changed"
    source.unlink()
    summary = sd.list_documents(tmp_path, home)["documents"][0]
    assert summary["approvalStatus"] == "missing"
    with pytest.raises(sd.StrategyDocumentError, match="源文件不存在"):
        sd.read_document("technical-system", tmp_path, home)


def test_unknown_id_and_path_escape(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    assert sd.read_document("unknown", tmp_path, home) is None
    index = tmp_path / "configs/strategy-documents.v1.json"
    data = json.loads(index.read_text(encoding="utf-8"))
    data["documents"][0]["file_name"] = "../secret.md"
    index.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(sd.StrategyDocumentError, match="权威目录之外"):
        sd.list_documents(tmp_path, home)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    source = home / "Desktop/lei signal doc/LEI 技术交易体系.md"
    source.unlink()
    source.symlink_to(tmp_path / "secret.md")
    with pytest.raises(sd.StrategyDocumentError, match="权威目录之外"):
        sd.read_document("technical-system", tmp_path, home)


def test_encoding_and_unreadable_errors(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    source = home / "Desktop/lei signal doc/LEI 技术交易体系.md"
    source.write_bytes(b"\xff")
    with pytest.raises(sd.StrategyDocumentError, match="有效 UTF-8"):
        sd.read_document("technical-system", tmp_path, home)
    original_open = Path.open

    def denied(path, *args, **kwargs):
        if path == source.resolve():
            raise PermissionError("denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(sd.StrategyDocumentError, match="无法读取"):
        sd.list_documents(tmp_path, home)


def test_headings_ignore_code_and_have_unique_ids() -> None:
    headings = sd._headings("# 道路\n```md\n## 假标题\n```\n## 道路-2\n## 道路\n")
    assert [h["id"] for h in headings] == ["道路", "道路-2", "道路-3"]


def test_strategy_document_routes(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    _write_fixture(tmp_path, home)
    monkeypatch.setattr(sd, "_repo_root", lambda base=None: tmp_path)
    monkeypatch.setattr(sd.Path, "home", lambda: home)
    client = TestClient(create_app())
    listed = client.get("/api/strategy-documents")
    assert listed.status_code == 200
    assert listed.json()["documents"][0]["id"] == "technical-system"
    detail = client.get("/api/strategy-documents/technical-system")
    assert detail.status_code == 200
    assert detail.json()["headings"][1]["text"] == "道路"
    assert client.get("/api/strategy-documents/unknown").status_code == 404
    assert client.get("/api/strategy-documents/../AGENTS.md").status_code in (404, 422)
    assert client.get("/api/strategy-documents/%2E%2E%2FAGENTS.md").status_code == 404
    changed = home / "Desktop/lei signal doc/LEI 技术交易体系.md"
    changed.write_text("# 已变化", encoding="utf-8")
    assert client.get("/api/strategy-documents/technical-system").json()[
        "approvalStatus"
    ] == "changed"
    changed.write_bytes(b"\xff")
    encoding_error = client.get("/api/strategy-documents/technical-system")
    assert encoding_error.status_code == 503
    assert "UTF-8" in encoding_error.json()["detail"]
    changed.unlink()
    assert client.get("/api/strategy-documents").json()["documents"][0][
        "approvalStatus"
    ] == "missing"
    missing = client.get("/api/strategy-documents/technical-system")
    assert missing.status_code == 503
    assert "源文件不存在" in missing.json()["detail"]


def test_route_reports_index_error(monkeypatch) -> None:
    def broken():
        raise sd.StrategyDocumentError("策略文档索引不可用")

    monkeypatch.setattr(sd, "list_documents", broken)
    response = TestClient(create_app()).get("/api/strategy-documents")
    assert response.status_code == 503
    assert response.json()["detail"] == "策略文档索引不可用"
