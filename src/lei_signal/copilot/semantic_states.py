"""语义状态目录加载/校验（03B，总控协议 §4，2026-09-08）。

`configs/semantic_states.v1.json` 只存解释与来源目录（A3 静态字段 + 增量
layer/source_adapter/allowed_claims/forbidden_claims），**不存第二份阈值或
计算式**；数值/日期由既有 Python 判定层输出填充。目录中找不到真实规则身份
就 null + 限制，不编 rule_id。

纯只读：加载 + 结构校验 + 查询；本模块不产出任何动态 active 判断。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_PATHS = [
    Path(__file__).resolve().parents[3] / "configs" / "semantic_states.v1.json",
    Path(__file__).resolve().parents[2] / "configs" / "semantic_states.v1.json",
]
_lock = threading.Lock()
_cache: dict[str, Any] | None = None
_mtime: float | None = None

#: A3 静态字段 + 增量字段（缺一即校验失败；不新增同义字段）
REQUIRED_FIELDS = (
    "id", "label_cn", "definition_ref", "evidence_refs", "valid_boundaries",
    "state_end_ref", "position_exit_ref", "agent_behavior", "research_status",
    "strategy_scope", "rule_refs", "missing_behavior", "allowed_actions",
    "layer", "source_adapter", "allowed_claims", "forbidden_claims",
)


def _load() -> dict[str, Any]:
    global _cache, _mtime
    path = next((p for p in _PATHS if p.exists()), None)
    if path is None:
        return {"version": "missing", "states": [],
                "note_cn": "语义状态目录文件未找到"}
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = None
    with _lock:
        if _cache is not None and mtime is not None and _mtime == mtime:
            return _cache
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {"version": "invalid", "states": [],
                    "note_cn": "语义状态目录解析失败"}
        _cache, _mtime = data, mtime
        return data


def state_catalog() -> dict[str, Any]:
    """目录全文（校验后）。字段缺失的条目保留但标 `_invalid`，不静默丢弃。"""
    data = _load()
    for st in data.get("states", []):
        missing = [f for f in REQUIRED_FIELDS if f not in st]
        if missing:
            st["_invalid"] = {"missing_fields": missing}
    return data


def get_state(state_id: str) -> dict[str, Any] | None:
    """按 id 查条目；找不到返回 None（调用方如实说无，不编造）。"""
    for st in _load().get("states", []):
        if st.get("id") == state_id:
            return st
    return None


def states_for_topic(topic: str) -> list[dict[str, Any]]:
    """按讨论主题返回相关状态条目（供讨论材料引用来源与边界）。"""
    topic_layers = {
        "overview": ["technical", "market", "sentiment"],
        "evidence": ["technical"],
        "plan": ["technical"],
        "dca": ["dca"],
        "sentiment": ["sentiment", "market"],
        "mindset": ["mindset"],
        "money": ["dca", "technical"],
    }
    layers = topic_layers.get(topic, [])
    return [st for st in _load().get("states", [])
            if st.get("layer") in layers and not st.get("_invalid")]


__all__ = ["state_catalog", "get_state", "states_for_topic", "REQUIRED_FIELDS"]
