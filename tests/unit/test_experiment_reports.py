"""实验报告库单元测试：抽取、登记簿合并、路由（含路径穿越防护）。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from lei_signal.api import experiment_reports as er
from lei_signal.api.app import create_app


def _make_repo(root: Path) -> None:
    (root / "docs/experiments").mkdir(parents=True)
    (root / "docs/experiments" / "alpha-2026-09-04.md").write_text(
        "# 阿尔法实验\n\n背景略。\n\n"
        "## 一句话结论（大白话）\n\n**判定：通过**——该方向有效，\n可以进入下一阶段。\n\n"
        "## 1. 明细\n\n表格略。\n",
        encoding="utf-8",
    )
    (root / "docs/experiments" / "beta-ARCHIVE-2026-09-01.md").write_text(
        "# 贝塔实验\n\n- 结论：证伪，无信息量。\n", encoding="utf-8"
    )
    (root / "docs/experiments" / "gamma-2026-09-02.md").write_text(
        "# 伽马实验\n\n没有任何标准小节。\n", encoding="utf-8"
    )
    (root / "docs/experiments" / "registry.json").write_text(
        json.dumps(
            {
                "version": 1,
                "entries": {
                    "docs/experiments/alpha-2026-09-04.md": {
                        "category": "宽度择时", "verdict": "passed"
                    },
                    "docs/experiments/beta-ARCHIVE-2026-09-01.md": {
                        "category": "美股与跨市场", "verdict": "falsified"
                    },
                    # 伽马故意不登记 → 待分类
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_extract_meta_variants(tmp_path: Path) -> None:
    (f := tmp_path / "a.md").write_text(
        "# T\n\n## 0. 一句话结论\n\n编号前缀也算。\n", encoding="utf-8"
    )
    assert er.extract_meta(f.read_text(encoding="utf-8"), "a")["oneLiner"] == "编号前缀也算。"
    (f2 := tmp_path / "b.md").write_text(
        "# T\n\n## 大白话总结\n\n变体标题也算。\n", encoding="utf-8"
    )
    assert er.extract_meta(f2.read_text(encoding="utf-8"), "b")["oneLiner"] == "变体标题也算。"


def test_scan_merges_registry(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    items = {i["name"]: i for i in er.scan_reports(tmp_path)}
    assert len(items) == 3

    a = items["docs/experiments/alpha-2026-09-04.md"]
    assert a["category"] == "宽度择时" and a["verdict"] == "passed"
    assert a["date"] == "2026-09-04" and not a["pending"]
    assert "判定：通过" in a["oneLiner"] and "下一阶段" in a["oneLiner"]

    b = items["docs/experiments/beta-ARCHIVE-2026-09-01.md"]
    assert b["archived"] and b["category"] == "美股与跨市场"
    assert b["oneLiner"].startswith("证伪")  # 老文档「结论：」行兜底

    g = items["docs/experiments/gamma-2026-09-02.md"]
    assert g["pending"] and g["oneLiner"] == ""  # 未登记 + 无结论 → 双重提醒

    # 日期倒序
    names = [i["name"] for i in er.scan_reports(tmp_path)]
    assert names[0].endswith("alpha-2026-09-04.md")


def test_read_report_and_traversal_guard(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    data = er.read_report("docs/experiments/alpha-2026-09-04.md", tmp_path)
    assert data is not None and "阿尔法实验" in data["markdown"]
    # 白名单外路径（含穿越）一律 404 语义
    assert er.read_report("../AGENTS.md", tmp_path) is None
    assert er.read_report("docs/trading-spec-v1.md", tmp_path) is None


def test_api_routes(monkeypatch, tmp_path: Path) -> None:
    _make_repo(tmp_path)
    monkeypatch.setattr(er, "_repo_root", lambda base=None: tmp_path)
    app = create_app()
    client = TestClient(app)

    r = client.get("/api/experiments")
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["total"] == 3 and body["stats"]["pending"] == 1
    assert body["stats"]["byVerdict"]["passed"] == 1
    assert body["stats"]["byCategory"]["宽度择时"] == 1

    r = client.get("/api/experiments/docs/experiments/alpha-2026-09-04.md")
    assert r.status_code == 200 and "阿尔法实验" in r.json()["markdown"]

    # %2e 编码绕开 httpx 客户端路径归一化，直击路由的 {name:path} 分支
    assert client.get("/api/experiments/%2e%2e/AGENTS.md").status_code == 404
