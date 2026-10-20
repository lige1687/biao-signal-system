"""重大事件来源与阶段归一化（纯函数，2026-09-17 S1）。

回答买前一个问题：这条消息是「预期 / 正式结果 / 评论 / 未知」，出处和
时间能不能核对。

口径（计划 §4 Task 3 冻结）：
- 正式结果（official_result）必须由可信官方来源且内容确实为决议支持；
  官方域名的讲话、日历、会议纪要不自动算新的利率决议；
- 旧概率报道保持 expectation，不因后来正式落地回写成已确认事实；
- 文章时间与事件时间分开；无法确认事件时间就 null，不用抓取时间冒充；
- 同一官方公告 URL / 确定事件身份才去重；不跨会议合并、不凭日期相近
  伪造关联；首批宁可关联未知（related_to 保持 null）；
- direction / importance 是模型解释，放入 model_annotation，未知时不填，
  不冒充「中性事实」。
"""
from __future__ import annotations

from urllib.parse import urlparse

from lei_signal.newsfeed.timeparse import parse_iso_ts

#: 官方可信来源（首批仅美联储货币政策公告；source=fed 或官方域名）。
_OFFICIAL_SOURCES = frozenset({"fed"})
_OFFICIAL_DOMAINS = ("federalreserve.gov",)

#: 官方内容中「确实是决议」的标题模式（讲话/纪要/日历不在此列）。
_OFFICIAL_RESULT_TITLE_PATTERNS = (
    "issues fomc statement",
    "fomc statement",
    "implementation note",
    "federal open market committee announces",
)

#: 官方来源中明确属于评论/记录类（非新决议）的标题模式。
_OFFICIAL_COMMENTARY_TITLE_PATTERNS = (
    "speech by",
    "testimony by",
    "minutes of",
    "calendar",
    "semiannual monetary policy report",
)

#: 预期/概率语言（中英）。
_EXPECTATION_PATTERNS = (
    "概率", "预期", "预计", "有望", "或将", "前瞻", "押注", "猜测",
    "probability", "odds", "likely to", "expected to", "forecast",
    "bets on", "fedwatch", "priced in",
)

#: 评论/解读语言（中英）。
_COMMENTARY_PATTERNS = (
    "评论", "解读", "分析", "观点", "复盘", "综述", "怎么看", "点评",
    "opinion", "analysis", "commentary", "what it means", "takeaways",
)


def _is_official(source: str | None, url: str | None) -> bool:
    if (source or "") in _OFFICIAL_SOURCES:
        return True
    if not url:
        return False
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in _OFFICIAL_DOMAINS)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(p in low for p in patterns)


def _event_key_from_url(url: str | None) -> str | None:
    """官方公告 URL → 确定事件身份（路径末段去扩展名）。无法确定返回 None。"""
    if not url:
        return None
    try:
        path = urlparse(url).path
    except ValueError:
        return None
    seg = path.rstrip("/").rsplit("/", 1)[-1]
    if not seg:
        return None
    stem = seg.rsplit(".", 1)[0] if "." in seg else seg
    return f"official:{stem}" if stem else None


def build_event_reference(item: dict) -> dict:
    """从一条消息行归一化事件参考。无确定依据的字段保持 None。"""
    source = item.get("source")
    source_name = item.get("source_name")
    url = item.get("url")
    title = str(item.get("title") or "")
    summary = str(item.get("summary") or "")
    published_raw = item.get("published_at")
    ingested_raw = item.get("ingested_at")
    # 时间合法性：无时区/坏串视为缺失（未知），不用抓取时间冒充发布时间。
    published_at = published_raw if parse_iso_ts(published_raw) is not None else None
    ingested_at = ingested_raw if parse_iso_ts(ingested_raw) is not None else None

    text = f"{title}\n{summary}"
    title_low = title.lower()
    official = _is_official(source, url)

    stage = "unknown"
    event_at: str | None = None
    if official and _contains_any(title_low, _OFFICIAL_RESULT_TITLE_PATTERNS):
        stage = "official_result"
        # 官方决议声明的发布时点即事件时点。
        event_at = published_at
    elif official and _contains_any(title_low, _OFFICIAL_COMMENTARY_TITLE_PATTERNS):
        stage = "commentary"
    elif _contains_any(text, _EXPECTATION_PATTERNS):
        stage = "expectation"
    elif (item.get("category") == "blogger") or _contains_any(text, _COMMENTARY_PATTERNS):
        stage = "commentary"

    importance = item.get("importance")
    direction = item.get("direction")
    scored = importance is not None
    return {
        "event_stage": stage,
        "source": source,
        "source_name": source_name,
        "source_url": url,
        "published_at": published_at,
        "event_at": event_at,
        "ingested_at": ingested_at,
        "event_key": (
            _event_key_from_url(url)
            if (official and stage == "official_result") else None
        ),
        "related_to": None,
        "relevance_cn": None,
        "model_annotation": {
            "scored": scored,
            "direction": direction if scored else None,
            "importance": importance if scored else None,
        },
    }


def _dedupe_rank(ref: dict) -> tuple[int, int]:
    """同一事件身份内的保留优先级：正式结果优先，其次已评分。"""
    return (
        1 if ref.get("event_stage") == "official_result" else 0,
        1 if (ref.get("model_annotation") or {}).get("scored") else 0,
    )


def dedupe_events(refs: list[dict]) -> list[dict]:
    """按确定事件身份去重：同一 event_key 只保留最高优先级一条。

    event_key 为 None 的条目永不合并（无确定身份不伪造关联）；不同
    event_key 的条目全部保留（不跨会议合并）。输出顺序保持输入顺序。
    """
    best_by_key: dict[str, dict] = {}
    result: list[dict] = []
    for ref in refs:
        key = ref.get("event_key")
        if not key:
            result.append(ref)
            continue
        prev = best_by_key.get(key)
        if prev is None:
            best_by_key[key] = ref
            result.append(ref)
        elif _dedupe_rank(ref) > _dedupe_rank(prev):
            result[result.index(prev)] = ref
            best_by_key[key] = ref
    return result


__all__ = ["build_event_reference", "dedupe_events"]
