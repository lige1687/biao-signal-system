"""新浪财经 7x24 快讯源（2026-08-27 实测可达，免登录）。"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import requests

from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import compute_dedupe_key
from lei_signal.newsfeed.sources import NewsSourceError

_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.sina.com.cn/7x24/",
}

_TITLE_BRACKET = re.compile(r"^【(.+?)】")

# 新浪接口的 create_time 是北京时间字符串，接口本身无时区信息。
_CN_TZ = timezone(timedelta(hours=8))


def _create_time_to_iso(raw: str) -> str:
    naive = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    return naive.replace(tzinfo=_CN_TZ).astimezone().isoformat(timespec="seconds")


def collect_sina(since_id: int | None, limit: int = 50) -> tuple[list[NewsItem], str | None]:
    """拉最新一页直播快讯，过滤 id <= since_id 的旧条目。新水位 = 最大 id。"""
    params = {
        "page": "1",
        "page_size": str(max(1, min(limit, 50))),
        "zhibo_id": "152",
        "tag_id": "0",
        "dire": "f",
        "dpc": "1",
    }
    try:
        resp = requests.get(_URL, params=params, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise NewsSourceError(f"sina 抓取失败: {exc}") from exc
    feed = ((payload.get("result") or {}).get("data") or {}).get("feed") or {}
    items: list[NewsItem] = []
    newest: int | None = None
    for row in feed.get("list") or []:
        try:
            item_id = int(row["id"])
            rich = (row.get("rich_text") or "").strip()
        except (KeyError, TypeError, ValueError):
            continue
        if not rich:
            continue
        if since_id is not None and item_id <= since_id:
            continue
        newest = item_id if newest is None else max(newest, item_id)
        try:
            published_at = _create_time_to_iso(row["create_time"])
        except (KeyError, TypeError, ValueError):
            continue
        m = _TITLE_BRACKET.match(rich)
        title = m.group(1) if m else rich[:30]
        items.append(
            NewsItem(
                source="sina",
                source_name="新浪7x24",
                title=title,
                summary=rich[:500],
                url=None,
                published_at=published_at,
                dedupe_key=compute_dedupe_key("sina", None, rich[:80]),
            )
        )
    return items, (str(newest) if newest is not None else None)


__all__ = ["collect_sina"]
