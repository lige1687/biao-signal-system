"""机构化反例与边界知识库（knowledge_base）：任何新研究开题前强制查重与避坑。"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


DEFAULT_KB_RELATIVE = Path("docs/research/strategy-lab-knowledge.v1.json")


class KnowledgeBase:
    def __init__(self, repo_root: Path | None = None, path: Path | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
        self.path = Path(path) if path else (self.repo_root / DEFAULT_KB_RELATIVE)

    def load(self) -> dict:
        if not self.path.exists():
            return {"schema": "strategy-lab-knowledge/1.0", "anti_patterns": [], "verified_edges": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def query(self, terms: list[str] | str) -> dict[str, list[dict]]:
        """检索与当前假说相关的历史证伪雷区与已证实边界（大小写不敏感子串匹配）。"""
        if isinstance(terms, str):
            tokens = [t.strip().lower() for t in terms.replace("，", " ").replace(",", " ").split() if t.strip()]
        else:
            tokens = [str(t).strip().lower() for t in terms if str(t).strip()]
        data = self.load()
        if not tokens:
            return {
                "anti_patterns": list(data.get("anti_patterns", [])),
                "verified_edges": list(data.get("verified_edges", [])),
            }

        def _matches(entry: dict) -> bool:
            hay = " ".join([
                str(entry.get("title", "")),
                " ".join(str(k) for k in entry.get("keywords", [])),
                str(entry.get("economic_reason", "")),
                str(entry.get("evidence", "")),
                str(entry.get("boundary", "")),
            ]).lower()
            return any(tok in hay for tok in tokens)

        return {
            "anti_patterns": [e for e in data.get("anti_patterns", []) if _matches(e)],
            "verified_edges": [e for e in data.get("verified_edges", []) if _matches(e)],
        }

    def record_entry(self, bucket: str, entry: dict) -> dict:
        """向 anti_patterns 或 verified_edges 追加/更新结构化条目（禁止静默覆盖旧证据）。"""
        if bucket not in ("anti_patterns", "verified_edges"):
            raise ValueError("bucket 必须是 anti_patterns 或 verified_edges")
        if not entry.get("id") or not entry.get("title") or not entry.get("evidence"):
            raise ValueError("知识条目必须包含 id、title 与 evidence")
        data = self.load()
        items = list(data.get(bucket, []))
        existing_idx = next((i for i, x in enumerate(items) if x.get("id") == entry["id"]), None)
        if existing_idx is not None:
            items[existing_idx] = entry
        else:
            items.append(entry)
        data[bucket] = items
        self.save(data)
        return entry
