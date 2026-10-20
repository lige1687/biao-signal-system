"""美联储官方货币政策公告源（2026-09-17 S1）。

为什么单列：通用 RSS 层（sources/rss.py）不保留 description 摘要、且把来源
统一标为 ``rss``（管线里再被归进 blogger）。官方公告需要无损保留原文摘要、
带时区发布时间与独立 source=fed 身份，且**不得分进博主**，故独立适配。

来源：`https://www.federalreserve.gov/feeds/press_monetary.xml`（RSS 2.0）。
pubDate 实测为命名美东时区（EST/EDT）写法；夏令/冬令切换用 zoneinfo
按日期解析，不用固定美国时差；数字偏移与 GMT 写法也兼容。
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import requests

from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import compute_dedupe_key
from lei_signal.newsfeed.sources import NewsSourceError

#: 官方货币政策公告 feed（唯一接入的官方来源，2026-09-17 计划冻结）。
FED_PRESS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

#: 命名美东时区 → IANA 区（zoneinfo 按日期处理夏令/冬令，不用固定时差）。
_NAMED_US_ZONES = {
    "EST": "America/New_York", "EDT": "America/New_York",
    "CST": "America/Chicago", "CDT": "America/Chicago",
    "MST": "America/Denver", "MDT": "America/Denver",
    "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
}
_UTC_NAMES = {"GMT", "UT", "UTC", "Z"}

#: RFC 822 日期尾部时区记号（命名或 ±HHMM）。
_TZ_TAIL = re.compile(r"\s+([A-Za-z]{1,5}|[+-]\d{4})\s*$")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def parse_fed_pubdate(raw: str | None) -> datetime | None:
    """解析官方 feed 的 pubDate 为带时区 datetime；无法确定时区返回 None。

    命名美东时区（EST/EDT 等）按 zoneinfo 对应 IANA 区的当天规则换算
    （冬令/夏令由日期决定，容忍源站把 EDT 误写成 EST）；数字偏移与
    GMT/UT 直接采用；完全无时区记号不猜，返回 None。
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    m = _TZ_TAIL.search(text)
    if m is None:
        return None
    token = m.group(1).upper()
    body = text[: m.start()].strip()
    try:
        naive = datetime.strptime(body, "%a, %d %b %Y %H:%M:%S")
    except ValueError:
        # 兜底：带数字偏移的标准 RFC 2822（email 解析器可处理）。
        try:
            dt = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        return dt if dt.tzinfo is not None else None
    if token in _UTC_NAMES:
        return naive.replace(tzinfo=UTC)
    if token in _NAMED_US_ZONES:
        return naive.replace(tzinfo=ZoneInfo(_NAMED_US_ZONES[token]))
    if re.fullmatch(r"[+-]\d{4}", token):
        try:
            return parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
    return None


def _clean_html(text: str | None) -> str | None:
    """官方 description 为纯文本，防御性去标签并压缩空白（保留原文事实）。"""
    if not text:
        return None
    cleaned = _WS.sub(" ", _TAG.sub(" ", text)).strip()
    return cleaned or None


def _default_fetch(url: str, timeout: int) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    # 官方 feed 响应头未声明 charset，requests 按 ISO-8859-1 解码会把
    # UTF-8 BOM 变成乱码字符（2026-09-17 S1 受控采集实测）：直接按
    # utf-8-sig 解码字节（自带 BOM 剥离）。
    return resp.content.decode("utf-8-sig", errors="replace")


def collect_fed_press(
    *,
    url: str = FED_PRESS_URL,
    since_iso: str | None,
    limit: int = 20,
    timeout: int = 20,
    fetcher: Callable[[str, int], str] | None = None,
) -> tuple[list[NewsItem], str | None]:
    """抓官方货币政策公告 feed，过滤 ``published_at <= since_iso`` 的旧条目。

    返回 ``(items, new_watermark)``；无新内容水位为 None。失败抛
    :class:`NewsSourceError` 由管线降级记录（网络失败单列，不换成无来源
    模型回答）。``fetcher`` 可注入，测试/重放用已保存响应，不打网络。
    """
    fetch = fetcher or _default_fetch
    try:
        xml_text = fetch(url, timeout)
        # 官方 feed 实测带 UTF-8 BOM（2026-09-17 S1 受控采集）：先剥再解析。
        root = ET.fromstring(xml_text.lstrip("﻿"))
    except NewsSourceError:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一封装为源错误
        raise NewsSourceError(f"fed 官方公告抓取失败: {exc}") from exc

    items: list[NewsItem] = []
    newest: str | None = None
    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or node.findtext("guid") or "").strip()
        if not title or not link:
            continue
        dt = parse_fed_pubdate(node.findtext("pubDate"))
        if dt is None:
            # 无日期/时区不可确定的条目跳过：不能用抓取时间冒充发布时间。
            continue
        published = dt.astimezone().isoformat(timespec="seconds")
        if since_iso is not None and published <= since_iso:
            continue
        newest = published if newest is None else max(newest, published)
        items.append(
            NewsItem(
                source="fed",
                source_name="美联储官网",
                title=title,
                summary=_clean_html(node.findtext("description")),
                url=link,
                published_at=published,
                category="macro",  # 官方货币政策公告：宏观类，绝不进 blogger
                dedupe_key=compute_dedupe_key("fed", link, title),
            )
        )
        if len(items) >= limit:
            break
    return items, newest


__all__ = ["FED_PRESS_URL", "collect_fed_press", "parse_fed_pubdate"]
