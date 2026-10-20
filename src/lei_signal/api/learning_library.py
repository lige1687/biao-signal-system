"""文献学习库 · 只读内容装载（纯函数，无框架依赖）。

数据唯一来源是 ``docs/literature-learning/learning-seed.json``（内容维护
约定见该目录 README；页面开发要求见交接稿
``docs/experiments/literature-learning-library-handoff-2026-09-08.md``）。

本模块只做三件事：装载固定内容文件、核对引用完整性（条目→论文、路线→
条目、相关论文、本地研究链接是否真实存在）、按分类/优先级出统计。
不产生、不修改任何学习内容，不读取整个 Zotero 用户库，不调用模型。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 学习内容目录（相对仓库根）。
LEARNING_DIR = Path("docs/literature-learning")
#: 结构化内容文件：页面数据的唯一来源。
SEED_PATH = LEARNING_DIR / "learning-seed.json"


class LearningDataError(Exception):
    """内容文件缺失或格式非法——前端据此显示「学习资料暂不可用」。"""


def _repo_root(base: Path | None = None) -> Path:
    """仓库根：base 为 None 时取本文件向上第三级（src/lei_signal/api → 根）。"""
    if base is not None:
        return base
    return Path(__file__).resolve().parents[3]


def _load_seed(root: Path) -> dict[str, Any]:
    path = root / SEED_PATH
    if not path.is_file():
        raise LearningDataError(f"学习内容文件不存在：{SEED_PATH}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise LearningDataError(f"学习内容文件无法解析：{e}") from e
    for key in ("papers", "entries", "reading_paths", "categories"):
        if not isinstance(data.get(key), list):
            raise LearningDataError(f"学习内容缺少必要字段：{key}")
    return data


def load_library(base: Path | None = None) -> dict[str, Any]:
    """装载学习目录并核对引用完整性，返回可直接交给前端的整体结构。

    完整性核对不改写内容，只把问题如实上报（``stats.integrity``）：
    前端对缺失引用显示明确提示，而不是静默吞掉或回落到别的论文。
    """
    root = _repo_root(base)
    data = _load_seed(root)
    paper_ids = {p.get("id") for p in data["papers"] if isinstance(p, dict)}
    entry_ids = {e.get("id") for e in data["entries"] if isinstance(e, dict)}

    orphan_entry_ids: list[str] = []       # 条目指向的论文不存在
    missing_related_ids: list[str] = []    # 相关论文 ID 不在库内
    broken_path_ids: list[str] = []        # 学习路线引用的条目不存在
    for e in data["entries"]:
        if not isinstance(e, dict):
            continue
        if e.get("paper_id") not in paper_ids:
            orphan_entry_ids.append(e.get("id", "?"))
        for rid in e.get("related_paper_ids") or []:
            if rid not in paper_ids:
                missing_related_ids.append(f"{e.get('id', '?')}→{rid}")
    for pth in data["reading_paths"]:
        if not isinstance(pth, dict):
            continue
        for eid in pth.get("entry_ids") or []:
            if eid not in entry_ids:
                broken_path_ids.append(f"{pth.get('id', '?')}→{eid}")

    # 本地研究链接逐条核对真实存在：缺失时前端显示「链接的本地报告暂缺」，
    # 不渲染死链（这些是 docs/ 内报告，天然无路径穿越面——只做存在性判断）。
    entries: list[dict[str, Any]] = []
    for e in data["entries"]:
        item = dict(e)
        rel = item.get("local_research_path")
        item["local_research_available"] = bool(rel) and (root / rel).is_file()
        entries.append(item)

    categories = [c for c in data["categories"] if isinstance(c, str)]
    stats = {
        "papers": len(data["papers"]),
        "entries": len(entries),
        "paths": len(data["reading_paths"]),
        "byCategory": {c: sum(1 for e in entries if e.get("category") == c) for c in categories},
        "byPriority": {
            str(p): sum(1 for e in entries if str(e.get("priority")) == str(p))
            for p in (1, 2, 3)
        },
        "integrity": {
            "orphanEntryIds": orphan_entry_ids,
            "missingRelatedIds": missing_related_ids,
            "brokenPathIds": broken_path_ids,
        },
    }
    return {
        "schema_version": data.get("schema_version", ""),
        "purpose": data.get("purpose", ""),
        "updated_at": data.get("updated_at", ""),
        "categories": categories,
        "reading_paths": data["reading_paths"],
        "papers": data["papers"],
        "entries": entries,
        "stats": stats,
    }
