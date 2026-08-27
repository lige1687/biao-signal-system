"""东方财富 7x24 快讯源（2026-08-27 实测可达，免登录）。"""
from __future__ import annotations

import re
from datetime import UTC, datetime

import requests

from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import compute_dedupe_key
from lei_signal.newsfeed.sources import NewsSourceError

_URL = "https://np-listapi.eastmoney.com/comm/web/getFastNewsList"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://kuaixun.eastmoney.com/",
}

_TITLE_BRACKET = re.compile(r"^【(.+?)】")


def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).astimezone().isoformat(
        timespec="seconds"
    )


def _norm_real_sort(raw: int) -> int:
    """东财游标混用微秒(16位)/毫秒(13位)，统一到毫秒（水位与时间解析共用）。"""
    return raw // 1000 if raw > 10**14 else raw


def collect_eastmoney(since_ms: int | None, limit: int = 50) -> tuple[list[NewsItem], str | None]:
    """拉最新一页快讯，过滤 realSort <= since_ms 的旧条目。

    新水位 = 本轮见到的最大 realSort（毫秒时间戳，转 str 存储）。
    """
    params = {
        "client": "web",
        "biz": "web_724",
        "fastColumn": "102",
        "sortEnd": "",
        "pageSize": str(max(1, min(limit, 50))),
        "req_trace": "1",
    }
    try:
        resp = requests.get(_URL, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise NewsSourceError(f"eastmoney 抓取失败: {exc}") from exc
    data = payload.get("data") or {}
    items: list[NewsItem] = []
    newest: int | None = None
    for row in data.get("fastNewsList") or []:
        try:
            ms = _norm_real_sort(int(row["realSort"]))
        except (KeyError, TypeError, ValueError):
            continue
        if since_ms is not None and ms <= since_ms:
            continue
        newest = ms if newest is None else max(newest, ms)
        summary = (row.get("summary") or "").strip()
        if not summary:
            continue
        m = _TITLE_BRACKET.match(summary)
        title = m.group(1) if m else summary[:30]
        items.append(
            NewsItem(
                source="eastmoney",
                source_name="东财快讯",
                title=title,
                summary=summary[:500],
                url=None,
                published_at=_ms_to_iso(ms),
                dedupe_key=compute_dedupe_key("eastmoney", None, summary[:80]),
            )
        )
    return items, (str(newest) if newest is not None else None)


__all__ = ["collect_eastmoney"]
