"""固定权威来源的只读装载器；不复制正文，不写入源文件或确认值。"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import yaml

_INDEX = Path("configs/strategy-documents.v1.json")
_GUIDE_INDEX = Path("configs/factor-guide-documents.v1.json")
_HEADING = re.compile(r"^ {0,3}(#{1,3})\s+(.+?)\s*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


class StrategyDocumentError(RuntimeError):
    """可直接展示给用户的来源错误。"""


def _repo_root(base: Path | None = None) -> Path:
    return base or Path(__file__).resolve().parents[3]


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    normalized = re.sub(r"[`*_~]", "", normalized)
    return re.sub(r"[^\w\u4e00-\u9fff-]+", "-", normalized).strip("-") or "section"


def _headings(markdown: str) -> list[dict]:
    used: set[str] = set()
    result = []
    fence = ""
    for line in markdown.splitlines():
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)
            if not fence:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = ""
            continue
        if fence:
            continue
        match = _HEADING.match(line)
        if not match:
            continue
        text = re.sub(r"\s+#+\s*$", "", match.group(2)).strip()
        base = _slug(text)
        anchor, suffix = base, 1
        while anchor in used:
            suffix += 1
            anchor = f"{base}-{suffix}"
        used.add(anchor)
        result.append({"id": anchor, "text": text, "level": len(match.group(1))})
    return result


def _load_index(repo_root: Path, guide: bool = False) -> dict:
    path = repo_root / (_GUIDE_INDEX if guide else _INDEX)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        schema = "factor-guide-documents/1" if guide else "strategy-documents/1"
        if data.get("schema_version") != schema:
            raise StrategyDocumentError("策略文档索引版本不受支持")
        if not isinstance(data["documents"], list):
            raise ValueError("documents")
        ids = set()
        for entry in data["documents"]:
            fingerprint = "baseline_sha256" if guide else "approved_sha256"
            date = "recorded_at" if guide else "confirmed_at"
            for field in ("id", "title", "file_name", "role", fingerprint, date, "order"):
                if field not in entry:
                    raise ValueError(field)
            if entry["id"] in ids:
                raise ValueError("重复文档 ID")
            ids.add(entry["id"])
        return data
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise StrategyDocumentError(f"策略文档索引不可用：{path}") from exc


def _resolve_sources(repo_root: Path, home: Path, guide: bool = False) -> list[tuple[dict, Path]]:
    index = _load_index(repo_root, guide)
    try:
        raw_dir = index["canonical_directory"]
        canonical = ((home / raw_dir[2:]) if raw_dir.startswith("~/")
                     else Path(raw_dir)).resolve()
        rows = []
        for entry in sorted(index["documents"], key=lambda item: item["order"]):
            source = (canonical / entry["file_name"]).resolve()
            inside = source.is_relative_to(canonical) if guide else source.parent == canonical
            if not inside or source == canonical:
                raise StrategyDocumentError("策略文档路径落在权威目录之外")
            rows.append((entry, source))
        return rows
    except StrategyDocumentError:
        raise
    except (OSError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        raise StrategyDocumentError("策略文档权威路径无法解析") from exc


def _read_source(source: Path) -> tuple[bytes, str]:
    try:
        with source.open("rb") as stream:
            payload = stream.read()
            # 同一次读取的内容用于正文与指纹，避免文件变化时二者不一致。
            modified = datetime.fromtimestamp(os.fstat(stream.fileno()).st_mtime)
        return payload, modified.astimezone().isoformat()
    except FileNotFoundError as exc:
        raise StrategyDocumentError(f"策略源文件不存在：{source}") from exc
    except OSError as exc:
        raise StrategyDocumentError(f"策略源文件无法读取：{source}") from exc


def _summary(entry: dict, source: Path, payload: bytes, modified: str) -> dict:
    current = hashlib.sha256(payload).hexdigest()
    baseline = entry.get("baseline_sha256", entry.get("approved_sha256"))
    unchanged = "unchanged" if "baseline_sha256" in entry else "confirmed"
    return {**entry, "path": str(source), "available": True,
            "currentSha256": current,
            "approvalStatus": unchanged if current == baseline else "changed",
            "modifiedAt": modified}


def list_documents(repo_root: Path | None = None, home: Path | None = None,
                   *, guide: bool = False) -> dict:
    rows = []
    for entry, source in _resolve_sources(_repo_root(repo_root), home or Path.home(), guide):
        try:
            payload, modified = _read_source(source)
        except StrategyDocumentError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                rows.append({**entry, "path": str(source), "available": False,
                             "currentSha256": None, "approvalStatus": "missing",
                             "modifiedAt": None})
                continue
            raise
        rows.append(_summary(entry, source, payload, modified))
    return {"documents": rows}


def read_document(document_id: str, repo_root: Path | None = None,
                  home: Path | None = None, *, guide: bool = False) -> dict | None:
    for entry, source in _resolve_sources(_repo_root(repo_root), home or Path.home(), guide):
        if entry["id"] != document_id:
            continue
        payload, modified = _read_source(source)
        try:
            markdown = payload.decode("utf-8")
        except UnicodeError as exc:
            raise StrategyDocumentError(f"策略源文件不是有效 UTF-8：{source}") from exc
        if guide and source.suffix != ".md":
            markdown = _guide_markdown(entry, source, markdown)
        return {**_summary(entry, source, payload, modified),
                "markdown": markdown, "headings": _headings(markdown)}
    return None


def _guide_markdown(entry: dict, source: Path, text: str) -> str:
    """结构化文件只作阅读呈现；指纹始终计算自原始字节。"""
    fence = "`" * max(3, max((len(s) for s in re.findall(r"`+", text)), default=0) + 1)
    language = source.suffix.removeprefix(".")
    raw = f"{fence}{language}\n{text}\n{fence}\n"
    if entry["id"] != "candidate-registry":
        return f"# {entry['title']}\n\n{raw}"
    try:
        registry = yaml.safe_load(text)
        candidates = registry["candidates"]
        if not isinstance(candidates, list) or not all(isinstance(c, dict) for c in candidates):
            raise ValueError("candidates")
    except (yaml.YAMLError, KeyError, TypeError, ValueError) as exc:
        raise StrategyDocumentError(f"候选注册表格式无法读取：{source}") from exc
    labels = {
        "family_id": "所属类别", "priority_proposal": "建议研究顺序",
        "quantification_direction": "如何转成可计算指标",
        "research_question_and_baseline": "研究问题与比较对象",
        "source_sections": "来源章节", "provenance_note": "来源说明",
        "extension_note": "扩展说明", "required_data": "所需数据",
        "status": "原文件研究状态", "definition_status": "原文件定义状态", "result": "结果",
    }

    def safe(value: object) -> str:
        if value is None:
            return "未填写（null）"
        if isinstance(value, list):
            return "；".join(safe(item) for item in value)
        # 不把登记值解释为 HTML、Markdown 标题或指令。
        return html.escape(str(value)).replace("`", "&#96;").replace("\n", " ")

    sections = [f"# 候选因子注册表\n\n共 {len(candidates)} 项候选。"
                "状态按原文件展示；NOT_RUN 表示尚未运行，DRAFT 表示定义草稿。"
                "登记不代表有效或获准交易。\n"]
    for candidate in candidates:
        sections.append(f"## {safe(candidate.get('id', '未命名'))}\n")
        for key, value in candidate.items():
            if key != "id":
                sections.append(f"- **{labels.get(key, safe(key))}**：{safe(value)}\n")
        sections.append("\n")
    return "\n".join(sections) + "\n## YAML 原文\n\n" + raw
