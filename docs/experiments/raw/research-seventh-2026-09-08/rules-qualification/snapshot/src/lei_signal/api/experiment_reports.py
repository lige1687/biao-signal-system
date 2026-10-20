"""实验报告库 · 扫描与抽取（纯函数，无框架依赖）。

数据来源两路合并，保证「既不漏文件、又不乱分类」：

1. **文件扫描**（保完整）：``docs/experiments/*.md`` 与 ``docs/`` 下指定的
   研究/规划文档全部入库——没被登记的文件也会显示，标为「待分类」，
   倒逼新实验按规约登记；
2. **登记簿**（保准确）：``docs/experiments/registry.json`` 给出每个文件的
   分类与结论状态，是分类的唯一权威来源（见 AGENTS.md 归档规约）。

每份报告要求正文含 ``## 一句话结论（大白话）`` 小节；抽取失败时 oneLiner
为空串，前端显示占位提示，同样起规约提醒作用。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: 实验结案报告目录（相对仓库根）。
EXPERIMENTS_DIR = Path("docs/experiments")
#: 登记簿路径（相对仓库根）。
REGISTRY_PATH = EXPERIMENTS_DIR / "registry.json"
#: docs/ 下除 experiments 外纳入报告库的研究/规划文档（相对仓库根）。
RESEARCH_GLOBS = [
    "docs/research-*.md",
    "docs/system-architecture-and-decisions-*.md",
    "docs/next-steps-master-plan-*.md",
]

#: 分类固定枚举——新分类须改这里 + registry.json 的 categories，防拼写漂移。
CATEGORIES = [
    "研究总纲",      # 跨轮次总纲/台账/规划（research-overview、round5-7、四轨架构等）
    "宽度择时",      # 市场宽度、出清信号、状态机
    "组合与仓位",    # 轮动、仓位阀门、二元/三档、执行方式
    "模块与信号",    # A/B/C/D 模块改进、信号质量、池边界
    "出场与止损",    # 出场矩阵、止损结构、时间止损
    "美股与跨市场",  # 美股、跨市场复制、美债/VIX 等海外变量
    "宏观与情绪",    # A股宏观、估值叠加、情绪触发
    "语义组合",      # 九语义探索（主从/多重确认/时间尺度分层等）
    "数据与质量",    # 数据质量审计、覆盖对账、池恢复
    "方法论与验证",  # 正交性、走查、鲁棒性、元扫描
    "任务书",        # prompt-* 系列任务派发文件
]

#: 结论状态：与 web 端 reportsIndex 既有口径一致。
VERDICTS = ["passed", "falsified", "mixed", "watch"]

#: 「待分类」占位（UI 高亮提醒登记）。
UNCATEGORIZED = "待分类"

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
#: 一句话结论小节标题（允许「（大白话）」等后缀）。
_ONELINER_RE = re.compile(
    r"^##\s*(?:[0-9]+[.、]\s*)?(?:一句话结论|大白话总结|大白话结论|一句话总纲|一句话大白话)[^\n]*$",
    re.MULTILINE,
)


def _repo_root(base: Path | None = None) -> Path:
    """仓库根：base 为 None 时取本文件向上第三级（src/lei_signal/api → 根）。"""
    if base is not None:
        return base
    return Path(__file__).resolve().parents[3]


def _clean_inline(text: str) -> str:
    """去掉行内 markdown 修饰（**加粗**、链接、反引号），保留纯文本。"""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    return text.strip()


def extract_meta(text: str, fallback_title: str) -> dict[str, Any]:
    """从 markdown 正文抽取 title / oneLiner。

    - title：首个 ``# `` 标题；
    - oneLiner：``## 一句话结论`` 小节到下一个 ``## `` 之间的文本，
      压平成单段并截断（完整结论以正文为准，卡片只做速览）。
    """
    m = _HEADING_RE.search(text)
    title = _clean_inline(m.group(1)) if m else fallback_title

    one_liner = ""
    m = _ONELINER_RE.search(text)
    if m:
        rest = text[m.end():]
        nxt = re.search(r"^##\s", rest, re.MULTILINE)
        seg = rest[: nxt.start()] if nxt else rest
        lines = [_clean_inline(x) for x in seg.splitlines()]
        one_liner = " ".join(x for x in lines if x)
    else:
        # 老文档兜底：头部条目里的「结论：/判定：/结果：」行（只扫前 80 行，
        # 避免命中正文深处无关句子）。找不到就留空，前端显示占位提示。
        head = "\n".join(text.splitlines()[:80])
        fm = re.search(r"^\s*(?:[-*>]+\s*)?(?:\*\*)?(?:结论|判定|结果)(?:\*\*)?[：:]\s*(.+)$", head, re.MULTILINE)
        if fm:
            one_liner = _clean_inline(fm.group(1))
    if len(one_liner) > 320:
        one_liner = one_liner[:320].rstrip() + "……"
    return {"title": title, "oneLiner": one_liner}


def _load_registry(root: Path) -> dict[str, dict[str, str]]:
    p = root / REGISTRY_PATH
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    entries = data.get("entries", {})
    return entries if isinstance(entries, dict) else {}


def _iter_doc_files(root: Path) -> list[tuple[str, Path]]:
    """收集纳入报告库的文件：experiments 全量 + docs 下研究/规划 glob。

    返回 (相对路径 posix, 绝对路径)；experiments 优先（同序稳定）。
    """
    out: list[tuple[str, Path]] = []
    exp_dir = root / EXPERIMENTS_DIR
    if exp_dir.is_dir():
        for p in sorted(exp_dir.glob("*.md")):
            out.append((p.relative_to(root).as_posix(), p))
    for pattern in RESEARCH_GLOBS:
        for p in sorted((root / "docs").glob(pattern.removeprefix("docs/"))):
            rel = p.relative_to(root).as_posix()
            if all(rel != r for r, _ in out):
                out.append((rel, p))
    return out


@dataclass
class ExperimentReport:
    """单份报告的展示元数据（正文另取，列表接口不带全文）。"""

    name: str          # 相对路径 posix，作为 API id
    title: str
    date: str          # YYYY-MM-DD（文件名优先，缺省用 mtime）
    category: str
    verdict: str       # passed/falsified/mixed/watch；未登记 → ""
    archived: bool     # 文件名含 ARCHIVE（任务已结案封存）
    isPrompt: bool     # prompt-* 任务书
    oneLiner: str
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["pending"] = self.category == UNCATEGORIZED
        return d


#: 列表扫描缓存：全量读 136+ 个文件约数秒，页面筛选全在前端做，
#: 60s TTL 足够新鲜（报告是归档产物，不会分钟级变动）。
_SCAN_CACHE: dict[str, Any] = {"key": None, "at": 0.0, "items": []}
_SCAN_TTL_SECONDS = 60.0


def scan_reports(base: Path | None = None) -> list[dict[str, Any]]:
    """扫描全部报告并合并登记簿，返回按日期倒序的元数据列表（60s 缓存）。"""
    import time

    root = _repo_root(base)
    cache_key = str(root)
    now = time.monotonic()
    if _SCAN_CACHE["key"] == cache_key and now - _SCAN_CACHE["at"] < _SCAN_TTL_SECONDS:
        return _SCAN_CACHE["items"]
    registry = _load_registry(root)
    items: list[ExperimentReport] = []
    for rel, path in _iter_doc_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        stem = path.stem
        meta = extract_meta(text, fallback_title=stem)
        reg = registry.get(rel, {})
        category = reg.get("category", "")
        if category not in CATEGORIES:
            category = UNCATEGORIZED
        verdict = reg.get("verdict", "")
        if verdict not in VERDICTS:
            verdict = ""
        dm = _DATE_RE.search(stem)
        date = dm.group(1) if dm else ""
        if not date:
            import datetime as _dt

            date = _dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        items.append(
            ExperimentReport(
                name=rel,
                title=meta["title"],
                date=date,
                category=category,
                verdict=verdict,
                archived="ARCHIVE" in stem.upper(),
                isPrompt=stem.startswith("prompt"),
                oneLiner=reg.get("oneLiner") or meta["oneLiner"],
                bytes=path.stat().st_size,
            )
        )
    items.sort(key=lambda x: (x.date, x.name), reverse=True)
    result = [x.to_dict() for x in items]
    _SCAN_CACHE.update(key=cache_key, at=now, items=result)
    return result


def read_report(name: str, base: Path | None = None) -> dict[str, Any] | None:
    """读取单份报告正文。name 必须命中扫描集合，天然挡路径穿越。"""
    root = _repo_root(base)
    valid = {rel: p for rel, p in _iter_doc_files(root)}
    path = valid.get(name)
    if path is None:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    reg = _load_registry(root).get(name, {})
    meta = extract_meta(text, fallback_title=path.stem)
    return {
        "name": name,
        "title": meta["title"],
        "oneLiner": reg.get("oneLiner") or meta["oneLiner"],
        "category": reg.get("category", UNCATEGORIZED),
        "verdict": reg.get("verdict", ""),
        "markdown": text,
    }
