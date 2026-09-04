"""实验报告库 · 路由。

前缀 ``/api/experiments``。只读：数据全部来自仓库内 markdown 文件与
``docs/experiments/registry.json`` 登记簿，本路由不产生、不修改任何结论。
分类与结论状态以登记簿为准（AGENTS.md 归档规约）。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from lei_signal.api import experiment_reports as er

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
def list_reports() -> dict:
    """报告元数据列表（日期倒序）+ 分类/状态统计（供前端筛选条）。"""
    items = er.scan_reports()
    stats = {
        "total": len(items),
        "pending": sum(1 for x in items if x["pending"]),
        "archived": sum(1 for x in items if x["archived"]),
        "byVerdict": {v: sum(1 for x in items if x["verdict"] == v) for v in er.VERDICTS},
        "byCategory": {c: sum(1 for x in items if x["category"] == c) for c in er.CATEGORIES + [er.UNCATEGORIZED]},
    }
    return {"items": items, "categories": er.CATEGORIES, "verdicts": er.VERDICTS, "stats": stats}


@router.get("/{name:path}")
def get_report(name: str) -> dict:
    """单份报告全文（markdown 原文，前端渲染）。未收录的路径 → 404。"""
    data = er.read_report(name)
    if data is None:
        raise HTTPException(status_code=404, detail="报告不存在或不在报告库收录范围")
    return data
