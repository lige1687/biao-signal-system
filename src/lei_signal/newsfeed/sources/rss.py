"""通用 RSS/Atom 源：Google News 定制查询（gnews 模式）与任意 RSS（P2 公众号 wewe-rss 复用）。

Google News RSS 必须带浏览器 UA（2026-08-27 实测裸 curl 返回空）。
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import compute_dedupe_key
from lei_signal.newsfeed.sources import NewsSourceError

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

_GNEWS_TMPL = (
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
)

# 标题形如 "Fed cuts rates - Reuters"：拆出媒体名。
_TITLE_SOURCE = re.compile(r"^(.*) - ([^-]{2,40})$")


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().isoformat(timespec="seconds")


def _parse_feed(xml_text: str) -> list[tuple[str, str, datetime | None, str | None]]:
    """返回 (title, link, published, source_hint) 列表。RSS2.0 与 Atom 通吃。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise NewsSourceError(f"RSS 解析失败: {exc}") from exc
    ns_atom = "{http://www.w3.org/2005/Atom}"
    ns_dc = "{http://purl.org/dc/elements/1.1/}"

    out: list[tuple[str, str, datetime | None, str | None]] = []
    # RSS 2.0: channel/item
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or item.findtext("guid") or "").strip()
        date: datetime | None = None
        pub = item.findtext("pubDate")
        if pub:
            try:
                date = parsedate_to_datetime(pub)
            except (TypeError, ValueError):
                date = None
        if date is None:
            dc = item.findtext(f"{ns_dc}date")
            if dc:
                try:
                    date = datetime.fromisoformat(dc.replace("Z", "+00:00"))
                except ValueError:
                    date = None
        out.append((title, link, date, None))
    if out:
        return out
    # Atom: feed/entry
    for entry in root.iter(f"{ns_atom}entry"):
        title = (entry.findtext(f"{ns_atom}title") or "").strip()
        link = ""
        link_el = entry.find(f"{ns_atom}link")
        if link_el is not None:
            link = (link_el.get("href") or "").strip()
        date = None
        for tag in ("published", "updated"):
            text = entry.findtext(f"{ns_atom}{tag}")
            if text:
                try:
                    date = datetime.fromisoformat(text.replace("Z", "+00:00"))
                except ValueError:
                    continue
        out.append((title, link, date, None))
    return out


def collect_rss(
    query_or_url: str,
    *,
    is_gnews: bool,
    since_iso: str | None,
    limit: int = 20,
) -> tuple[list[NewsItem], str | None]:
    """抓一个 RSS 源，过滤 published_at <= since_iso 的旧条目。

    新水位 = 本轮保留条目的最大 published_at（ISO）。无日期的条目跳过
    （无法做增量与排序，留着只会重复入库）。
    """
    url = _GNEWS_TMPL.format(query=quote_plus(query_or_url)) if is_gnews else query_or_url
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        entries = _parse_feed(resp.text)
    except (requests.RequestException, NewsSourceError) as exc:
        raise NewsSourceError(f"rss 抓取失败({query_or_url[:40]}): {exc}") from exc

    items: list[NewsItem] = []
    newest: str | None = None
    for title, link, date, _hint in entries[: max(limit * 2, 40)]:
        if not title or not link or date is None:
            continue
        published = _to_iso(date)
        if since_iso is not None and published <= since_iso:
            continue
        newest = published if newest is None else max(newest, published)
        source_name = None
        display_title = title
        m = _TITLE_SOURCE.match(title)
        if is_gnews and m:
            display_title, source_name = m.group(1).strip(), m.group(2).strip()
        items.append(
            NewsItem(
                source="gnews" if is_gnews else "rss",
                source_name=source_name or ("Google News" if is_gnews else None),
                title=display_title,
                summary=None,
                url=link,
                published_at=published,
                dedupe_key=compute_dedupe_key("gnews" if is_gnews else "rss", link, title),
            )
        )
        if len(items) >= limit:
            break
    return items, newest


__all__ = ["collect_rss"]
