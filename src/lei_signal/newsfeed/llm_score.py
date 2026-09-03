"""LLM 批量打分与今日简报生成（参考层，复用 plans.llm 投递骨架）。

铁律对齐仓库哲学：LLM 只做"打分/归类/摘要/整合"这类结构化工序，
不给操作建议；任何失败返回 None / 空列表，调用方降级保持未评分态。
"""
from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Any

from lei_signal.plans.llm import ArkConfig, load_ark_config, post_user_content

logger = logging.getLogger(__name__)

#: 打分输入截断（字）。字幕全文入库保留 20000，但打分只需要开头足够判断；
#: 长字幕批量进 prompt 会撑爆模型上下文（实测一批直播回放字幕 ≈ 10 万 token）。
_SUMMARY_MAX = 500
_CONTENT_MAX = 6000
_BATCH_SIZE = 20

_VALID_CATEGORIES = ("macro", "risk", "policy", "industry", "blogger")
_VALID_DIRECTIONS = ("bullish", "bearish", "neutral")

SCORE_SYSTEM_PROMPT = """你是财经资讯编辑助手。对给定资讯逐条输出结构化评分 JSON 数组。
铁律：
1. 只依据给定文本判断，不引入外部信息。
2. importance 0-10：对 A股/港股/美股投资者的决策影响
   （系统性事件 8-10，行业重大 6-8，常规数据 3-5，噪音 0-2）。
3. category 从 macro/risk/policy/industry/blogger 选最贴切的一个。
4. direction：bullish/bearish/neutral，拿不准用 neutral。
5. symbols：涉及股票代码或简称，最多 3 个（如 ["NVDA","中际旭创"]），无则 []。
6. note：一句话中文点评（≤60 字），只概括事实与含义，不给操作建议。
   若该条带长文本（视频字幕/文章正文），note 改写为 ≤120 字的核心内容
   摘要：博主/作者到底说了什么、多空倾向、提到的关键点位或标的——
   读者只看 note 就能知道内容，不必点开原文。
输出：严格 JSON 数组，每项
{"id":<原样返回>,"category":"..","importance":<int>,"direction":"..","symbols":[..],"note":".."}。
除 JSON 外不输出任何文字。"""

DIGEST_SYSTEM_PROMPT = """你是财经资讯编辑。把当日已评分资讯整合成简报 JSON。
铁律：只归纳合并给定条目，不添加外部信息；同一事件多源合并为一条；不给操作建议。
输出：{"sections":[{"category":"macro|risk|policy|industry|blogger",
"headline":"≤12字","bullets":["每条≤40字"]}],
"top_events":[{"title":"..","importance":<int>,"why":"≤30字",
"symbols":["涉及股票代码或简称，最多3个，无则[]"],
"direction":"bullish|bearish|neutral，事件整体方向，拿不准 neutral"}]}
sections 只含有内容的类别，按 macro,risk,policy,industry,blogger 排序；
top_events 取 importance 最高的至多 5 条，symbols/direction 从合并条目中
归纳（条目已有的标的优先保留）。
除 JSON 外不输出任何文字。"""


def _extract_json_span(text: str, *, array: bool) -> str:
    """剥 ```json 围栏与前后杂字：取首个 [ 到末个 ]（或 { 到 }）。"""
    open_ch, close_ch = ("[", "]") if array else ("{", "}")
    start = text.find(open_ch)
    end = text.rfind(close_ch)
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no json span")
    return text[start : end + 1]


def _clamp_importance(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, n))


def parse_scores(text: str) -> list[dict]:
    """容错解析打分输出；字段非法的条目丢弃，id 必须是 int。"""
    try:
        raw = json.loads(_extract_json_span(text, array=True))
    except (ValueError, json.JSONDecodeError):
        return []
    out: list[dict] = []
    if not isinstance(raw, list):
        return []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            item_id = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue
        category = str(item.get("category", "")).strip()
        direction = str(item.get("direction", "")).strip()
        symbols = item.get("symbols")
        out.append(
            {
                "id": item_id,
                "category": category if category in _VALID_CATEGORIES else "macro",
                "importance": _clamp_importance(item.get("importance")),
                "direction": direction if direction in _VALID_DIRECTIONS else "neutral",
                "symbols": [
                    str(s)[:16]
                    for s in (symbols if isinstance(symbols, list) else [])[:3]
                ],
                "note": str(item.get("note", ""))[:200],
            }
        )
    return out


def parse_digest(text: str) -> dict:
    """容错解析简报输出；结构不合给出空骨架。"""
    try:
        raw = json.loads(_extract_json_span(text, array=False))
    except (ValueError, json.JSONDecodeError):
        return {"sections": [], "top_events": []}
    if not isinstance(raw, dict):
        return {"sections": [], "top_events": []}
    sections = []
    for s in raw.get("sections") or []:
        if not isinstance(s, dict):
            continue
        category = str(s.get("category", "")).strip()
        if category not in _VALID_CATEGORIES:
            continue
        bullets = [str(b)[:60] for b in (s.get("bullets") or []) if b][:8]
        if not bullets:
            continue
        sections.append(
            {"category": category, "headline": str(s.get("headline", ""))[:16], "bullets": bullets}
        )
    top_events = []
    for e in raw.get("top_events") or []:
        if not isinstance(e, dict) or not e.get("title"):
            continue
        direction = str(e.get("direction", "")).strip()
        symbols = e.get("symbols")
        top_events.append(
            {
                "title": str(e["title"])[:60],
                "importance": _clamp_importance(e.get("importance")),
                "why": str(e.get("why", ""))[:40],
                "symbols": [
                    str(s)[:16]
                    for s in (symbols if isinstance(symbols, list) else [])[:3]
                ],
                "direction": direction if direction in _VALID_DIRECTIONS else "neutral",
            }
        )
    return {"sections": sections[:5], "top_events": top_events[:5]}


def _safe_json_list(raw: Any) -> list:
    """symbols 列在 SQLite 是 JSON 文本，解码失败按空处理。"""
    if isinstance(raw, list):
        return raw
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _rows_to_prompt_payload(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                "id": r.get("id"),
                "title": (r.get("title") or "")[:120],
                "text": ((r.get("summary") or "")[:_SUMMARY_MAX]
                         + "\n" + (r.get("content") or "")[:_CONTENT_MAX]).strip(),
                "source": r.get("source"),
                "source_name": r.get("source_name"),
            }
        )
    return out


def score_items(rows: list[dict], config: ArkConfig | None = None) -> list[dict] | None:
    """一批（≤20 条）打分。返回 parse 后的列表；任何失败返回 None（调用方重试/降级）。"""
    if not rows:
        return []
    resolved = config or load_ark_config()
    if resolved is None:
        return None
    content = (
        "对下面每条资讯输出评分 JSON 数组（严格按系统提示格式）：\n"
        + json.dumps(_rows_to_prompt_payload(rows), ensure_ascii=False, indent=1)
    )
    text = post_user_content(content, resolved, system_prompt=SCORE_SYSTEM_PROMPT)
    if text is None:
        return None
    scores = parse_scores(text)
    if not scores:
        logger.warning("newsfeed 打分解析为空，批大小=%d", len(rows))
        return None
    valid_ids = {r.get("id") for r in rows}
    return [s for s in scores if s["id"] in valid_ids]


def generate_digest(rows: list[dict], config: ArkConfig | None = None) -> dict | None:
    """当日已评分条目 → 结构化简报。失败返回 None（调用方跳过，不阻断）。

    推理模型 thinking 可能吃满默认 max_tokens 导致 200 无 text：这里把
    max_tokens 提到 ≥12000 给思考留余量（简报正文本身很小）。
    """
    if not rows:
        return None
    resolved = config or load_ark_config()
    if resolved is None:
        return None
    if resolved.max_tokens < 12000 or resolved.timeout < 180.0:
        # 推理模型 thinking 长：百行级输入 + 长思考会撞 90s 默认超时。
        resolved = replace(
            resolved,
            max_tokens=max(resolved.max_tokens, 12000),
            timeout=max(resolved.timeout, 180.0),
        )
    # 输入按重要性截 Top 60（调用方已按 importance DESC 排序）。
    rows = rows[:60]
    payload = [
        {
            "title": (r.get("title") or "")[:120],
            "note": (r.get("llm_note") or "")[:80],
            "category": r.get("category"),
            "importance": r.get("importance"),
            "direction": r.get("direction"),
            # symbols 是 JSON 文本（scored_rows_for_digest 已 SELECT），解码后透传给简报归纳
            "symbols": _safe_json_list(r.get("symbols")),
            "source": r.get("source"),
        }
        for r in rows
    ]
    content = (
        "把下面当日已评分资讯整合成简报 JSON（严格按系统提示格式）：\n"
        + json.dumps(payload, ensure_ascii=False, indent=1)
    )
    text = post_user_content(content, resolved, system_prompt=DIGEST_SYSTEM_PROMPT)
    if text is None:
        return None
    digest = parse_digest(text)
    return digest if (digest["sections"] or digest["top_events"]) else None


__all__ = [
    "DIGEST_SYSTEM_PROMPT",
    "SCORE_SYSTEM_PROMPT",
    "generate_digest",
    "parse_digest",
    "parse_scores",
    "score_items",
]
