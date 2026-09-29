"""固定权威来源的只读装载器；不复制正文，不写入源文件或确认值。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

_INDEX = Path("configs/strategy-documents.v1.json")
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


def _load_index(repo_root: Path) -> dict:
    path = repo_root / _INDEX
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != "strategy-documents/1":
            raise StrategyDocumentError("策略文档索引版本不受支持")
        if not isinstance(data["documents"], list):
            raise ValueError("documents")
        ids = set()
        for entry in data["documents"]:
            for field in ("id", "title", "file_name", "role", "approved_sha256",
                          "confirmed_at", "order"):
                if field not in entry:
                    raise ValueError(field)
            if entry["id"] in ids:
                raise ValueError("重复文档 ID")
            ids.add(entry["id"])
        return data
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise StrategyDocumentError(f"策略文档索引不可用：{path}") from exc


def _resolve_sources(repo_root: Path, home: Path) -> list[tuple[dict, Path]]:
    index = _load_index(repo_root)
    try:
        raw_dir = index["canonical_directory"]
        canonical = ((home / raw_dir[2:]) if raw_dir.startswith("~/")
                     else Path(raw_dir)).resolve()
        rows = []
        for entry in sorted(index["documents"], key=lambda item: item["order"]):
            source = (canonical / entry["file_name"]).resolve()
            if source.parent != canonical:
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
    return {**entry, "path": str(source), "available": True,
            "currentSha256": current,
            "approvalStatus": "confirmed" if current == entry["approved_sha256"] else "changed",
            "modifiedAt": modified}


def list_documents(repo_root: Path | None = None, home: Path | None = None) -> dict:
    rows = []
    for entry, source in _resolve_sources(_repo_root(repo_root), home or Path.home()):
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
                  home: Path | None = None) -> dict | None:
    for entry, source in _resolve_sources(_repo_root(repo_root), home or Path.home()):
        if entry["id"] != document_id:
            continue
        payload, modified = _read_source(source)
        try:
            markdown = payload.decode("utf-8")
        except UnicodeError as exc:
            raise StrategyDocumentError(f"策略源文件不是有效 UTF-8：{source}") from exc
        return {**_summary(entry, source, payload, modified),
                "markdown": markdown, "headings": _headings(markdown)}
    return None
