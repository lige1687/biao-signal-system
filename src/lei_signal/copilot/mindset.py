"""认知/心态种子库加载器（叙事/教育层，research_proxy 禁网红线内）。

定位：**只叙事**——种子是给讨论与展示用的认知/心态内容（文本+引用出处），
永不参与技术判定、评分、过滤、推荐排序（AGENTS.md 基本面/消息面只做叙事
标注层的同一原则；docs/trading-spec-v1.md 体系内不存在「心态」判定输入）。

数据源：configs/mindset_seed.json（来自 lei-signal-sync 同名文件，
sha256=4bff4b76c120b2ac429e479752606390402b578d1bb248a533def927151b03e4，
26 条，内容不改）。字段：category/text/source 必有，quote 可选（实测 26 条
中仅 3 条带 quote）；无显式 seed_key——
去重键自拟为 sha256(category + "\\x00" + text) 前十六位（文档化于本 docstring
与实验报告 agent-mindset-seed-2026-09-19）。

加载策略：按需加载（每次调用读盘），不引入「首启自动导入」机制——运行主线
没有首启钩子，按需加载行为等价且零新依赖；取舍见实验报告。

降级路径：文件缺失/损坏/无有效条目时返回 available=False，由调用方
（intent.py 的 fallback 标注、copilot dispatch 的回落分支）保持既有回落
行为，与接入前一致。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

#: 仓库根下 configs/mindset_seed.json（copilot → lei_signal → src → 仓库根）。
_DEFAULT_PATH = Path(__file__).resolve().parents[2].parent / "configs/mindset_seed.json"

_REQUIRED_FIELDS = ("category", "text", "source")


def _seed_key(item: dict) -> str:
    """自拟去重键：类别+正文联合哈希（种子文件无显式 seed_key）。"""
    raw = f"{item.get('category', '')}\x00{item.get('text', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_mindset_seeds(path: str | Path | None = None) -> dict:
    """读种子文件→校验必需字段→按自拟键去重。

    返回 {"available", "items", "count", "dropped", "duplicates", "sha256"}；
    任何一步失败返回 available=False + reason（调用方据此回落，不冒充可用）。
    """
    p = Path(path) if path else _DEFAULT_PATH
    try:
        raw = p.read_bytes()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "reason": f"seed_file_missing_or_corrupt:{type(exc).__name__}",
            "items": [],
            "count": 0,
        }
    entries = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return {
            "available": False,
            "reason": "seed_file_bad_structure",
            "items": [],
            "count": 0,
        }
    items: list[dict] = []
    dropped = 0
    seen: set[str] = set()
    duplicates = 0
    for entry in entries:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(f), str) or not entry.get(f, "").strip()
            for f in _REQUIRED_FIELDS
        ):
            dropped += 1
            continue
        key = _seed_key(entry)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        quote = entry.get("quote")
        items.append(
            {
                "category": entry["category"].strip(),
                "text": entry["text"].strip(),
                "quote": quote.strip() if isinstance(quote, str) else "",
                "source": entry["source"].strip(),
                "seed_key": key,
            }
        )
    if not items:
        return {
            "available": False,
            "reason": "seed_file_no_valid_items",
            "items": [],
            "count": 0,
        }
    return {
        "available": True,
        "items": items,
        "count": len(items),
        "dropped": dropped,
        "duplicates": duplicates,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def seeds_available(path: str | Path | None = None) -> bool:
    """种子库是否可用（intent.py 回落标注用；缺位时回落行为与接入前一致）。"""
    return load_mindset_seeds(path)["available"]
