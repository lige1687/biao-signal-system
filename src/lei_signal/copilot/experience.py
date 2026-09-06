"""回测经验索引检索（纯读，零 LLM）：experience.json 的条件→历史结果匹配。

设计（docs/experiments/EXPERIENCE-INDEX.md，2026-09-05）：
- 查询做 match 键值**子集匹配**：finding 的 match 全部键值与查询一致才命中；
- 命中返回大白话结论（conclusion_cn/metrics_cn/direction）+ 源报告可溯源；
- 红线：经验只做「叙事标注/置信度参考」，不参与技术判定、不硬过滤——
  与情绪面/消息面同一纪律（当前口径，升级为规则需用户拍板改规则账本）。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_DEFAULT_PATHS = [
    # 仓内源文件（开发/测试）；lab 部署同结构
    Path(__file__).resolve().parents[3] / "docs" / "experiments" / "experience.json",
    # 打包/其它布局兜底：模块同级向上两级 docs
    Path(__file__).resolve().parents[2] / "docs" / "experiments" / "experience.json",
]

_lock = threading.Lock()
_cache: dict[str, Any] | None = None
_cache_mtime: float | None = None
_cache_path: Path | None = None


def _locate() -> Path | None:
    for p in _DEFAULT_PATHS:
        if p.exists():
            return p
    return None


def _load() -> dict[str, Any]:
    """带 mtime 缓存的加载（热更新：索引文件改了立即生效，无需重启）。"""
    global _cache, _cache_mtime, _cache_path
    path = _locate()
    if path is None:
        return {"version": 0, "entries": [], "note_cn": "经验索引文件未找到"}
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = None
    with _lock:
        if (
            _cache is not None
            and _cache_path == path
            and mtime is not None
            and _cache_mtime == mtime
        ):
            return _cache
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = _cache or {"version": 0, "entries": [], "note_cn": "索引解析失败"}
        _cache, _cache_mtime, _cache_path = data, mtime, path
        return data


def _hit(finding_match: dict, query: dict[str, str]) -> bool:
    """情境匹配：查询给出的每个键，经验的 match 必须相等或缺失（缺失=通配）。

    语义：查询描述「当前情境」（如 pool=行业ETF），经验 match 是它的适用
    条件。查询与经验**共有的键**取值必须一致；match 缺的键表示该经验与
    此键无关（通配，仍适用）。反之经验限定而查询未给的键（如经验要求
    signal=A、查询只给了 pool）不构成冲突——命中后由引用方看 match 自行
    判断细化条件。
    """
    for k, v in query.items():
        m = finding_match.get(k)
        if m is not None and m != v:
            return False
    return True


_DIR_CN = {"positive": "历史支持", "negative": "历史反对", "neutral": "无差异"}


def query_experience(
    conditions: dict[str, str] | None = None,
    *,
    limit: int = 8,
) -> dict[str, Any]:
    """按条件查经验。返回 {available, items: [{...finding, entry...}], note_cn}。

    conditions 为空/无命中时 available=False（调用方如实说无，不硬凑）。
    """
    data = _load()
    entries = [e for e in data.get("entries") or [] if isinstance(e, dict)]
    q = {k: v for k, v in (conditions or {}).items() if v}
    if not q:
        # 空情境不兜底全量（避免把无关经验灌进材料）
        return {
            "available": False,
            "items": [],
            "note_cn": "历史经验叙事层（来自回测定案报告），不参与技术判定",
        }
    hits: list[dict[str, Any]] = []
    for e in entries:
        for f in e.get("findings") or []:
            if not isinstance(f, dict) or not _hit(f.get("match") or {}, q):
                continue
            direction = f.get("direction") or "neutral"
            hits.append(
                {
                    "entry_id": e.get("id"),
                    "report": e.get("report"),
                    "date": e.get("date"),
                    "verdict": e.get("verdict"),
                    "direction": direction,
                    "direction_cn": _DIR_CN.get(direction, direction),
                    "confidence": f.get("confidence") or "observed",
                    "match": f.get("match") or {},
                    "metrics_cn": f.get("metrics_cn") or "",
                    "conclusion_cn": f.get("conclusion_cn") or "",
                }
            )
    # 定义级经验优先、日期新者优先
    hits.sort(key=lambda h: (h["confidence"] != "defined", h.get("date") or ""), )
    return {
        "available": bool(hits),
        "items": hits[: max(1, int(limit))],
        "note_cn": "历史经验叙事层（来自回测定案报告），不参与技术判定",
    }


def experience_for_symbol(
    symbol: str,
    *,
    signal: str | None = None,
) -> list[dict[str, Any]]:
    """按标的池类型推断查询（推荐/讨论侧便捷入口）。

    池推断是保守的展示层映射：指数本体/宽基 ETF → broad_base_etf|index；
    行业 ETF（.SECTOR 除外）→ industry_etf；推断不出就不查（宁缺毋滥）。
    """
    pool = infer_pool(symbol)
    if pool is None:
        return []
    out = query_experience({"pool": pool, **({"signal": signal} if signal else {})})
    return out["items"]


def infer_pool(symbol: str) -> str | None:
    """标的代码 → 经验词表的池类型（保守推断，推断不出返回 None）。"""
    if not symbol:
        return None
    if ".SECTOR" in symbol:
        return "index"  # 板块指数本体按指数口径处理（展示层近似）
    sym = symbol.upper()
    broad = {
        "510300.SS", "510500.SS", "510050.SS", "159915.SZ",
        "588000.SS", "512100.SS", "159949.SZ",
    }
    if sym in broad:
        return "broad_base_etf"
    if sym.startswith(("51", "15", "56", "58")) and (
        sym.endswith(".SS") or sym.endswith(".SZ")
    ):
        return "industry_etf"
    if sym.startswith("^") or sym[:1].isdigit() and sym.endswith((".SS", ".SZ")) and len(sym.split(".")[0]) <= 6:
        # 指数代码（000300.SS 等 6 位数字）视作指数本体；个股 6 位同样长度，
        # 展示层无法可靠区分时返回 None（宁缺毋滥，不做错配经验）
        return "index" if sym.startswith(("000", "399", "931")) else None
    return None


__all__ = ["query_experience", "experience_for_symbol", "infer_pool"]
