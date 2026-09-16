"""文献学习库单元测试：内容装载、引用完整性核对、路由（只读、503/404语义）。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from lei_signal.api import learning_library as ll
from lei_signal.api.app import create_app


def _make_repo(root: Path, seed: dict) -> Path:
    """最小假仓库：只含 learning-seed.json 与一篇被链接的本地报告。"""
    docs = root / "docs/literature-learning"
    docs.mkdir(parents=True)
    (docs / "learning-seed.json").write_text(
        json.dumps(seed, ensure_ascii=False), encoding="utf-8"
    )
    exp = root / "docs/experiments"
    exp.mkdir(parents=True, exist_ok=True)
    (exp / "some-review-2026-09-08.md").write_text("# 报告\n", encoding="utf-8")
    return root


_SEED_OK = {
    "schema_version": "learning-library-draft/1",
    "purpose": "测试",
    "updated_at": "2026-09-08",
    "categories": ["实验方法", "投资启示"],
    "papers": [
        {
            "id": "p1", "title": "Paper One", "authors": ["A"], "year": 2000,
            "publication_kind": "journalArticle", "venue": "J", "doi": None,
            "source_url": "https://example.org/1", "zotero_item_key": "KEY1",
            "zotero_uri": "zotero://select/library/items/KEY1",
            "selection_label": "测试", "reading_level": "摘要已核验",
            "read_version": "2000", "source_locator": "测试",
            "checked_at": "2026-09-08", "replication_status": "未复现",
        },
        {"id": "p2", "title": "Paper Two", "authors": ["B"], "year": 2020,
         "publication_kind": "report"},
    ],
    "entries": [
        {
            "id": "p1-lesson-1", "paper_id": "p1", "title": "条目一",
            "category": "实验方法", "priority": 1,
            "related_paper_ids": ["p2"],
            "local_research_path": "docs/experiments/some-review-2026-09-08.md",
        },
        {
            "id": "p2-lesson-1", "paper_id": "缺Paper", "title": "孤儿条目",
            "category": "投资启示", "priority": 2,
            "related_paper_ids": ["不在库"], "local_research_path": None,
        },
    ],
    "reading_paths": [
        {"id": "start", "title": "路线", "entry_ids": ["p1-lesson-1", "缺Entry"]},
    ],
}


def test_load_library_integrity(tmp_path: Path) -> None:
    lib = ll.load_library(_make_repo(tmp_path, _SEED_OK))
    stats = lib["stats"]
    assert (stats["papers"], stats["entries"], stats["paths"]) == (2, 2, 1)
    # 条目→论文缺失、相关论文缺失、路线→条目缺失，三类问题都如实上报
    assert stats["integrity"]["orphanEntryIds"] == ["p2-lesson-1"]
    assert stats["integrity"]["missingRelatedIds"] == ["p2-lesson-1→不在库"]
    assert stats["integrity"]["brokenPathIds"] == ["start→缺Entry"]
    # 本地报告存在性核对：存在 → True
    assert lib["entries"][0]["local_research_available"] is True
    assert lib["entries"][1]["local_research_available"] is False
    by_cat = stats["byCategory"]
    assert by_cat == {"实验方法": 1, "投资启示": 1}


def test_load_library_missing_file(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ll.LearningDataError):
        ll.load_library(tmp_path)


def test_load_library_bad_json(tmp_path: Path) -> None:
    docs = tmp_path / "docs/literature-learning"
    docs.mkdir(parents=True)
    (docs / "learning-seed.json").write_text("{不是JSON", encoding="utf-8")
    import pytest

    with pytest.raises(ll.LearningDataError):
        ll.load_library(tmp_path)


def test_route_read_only(tmp_path: Path) -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/learning")
    # 测试仓库根不是本仓库 → 假仓库未挂进应用，真实文件仍可读；
    # 这里只验证接口语义：200 且结构完整（或 503 内容缺失），不允许 5xx 崩溃。
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        body = resp.json()
        for key in ("papers", "entries", "reading_paths", "categories", "stats"):
            assert key in body
