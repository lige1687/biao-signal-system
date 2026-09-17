"""美联储官方货币政策公告源（2026-09-17 S1；repair-1 按主控复核 R3 返修）。

为什么单列：通用 RSS 层（sources/rss.py）不保留 description 摘要、且把来源
统一标为 ``rss``（管线里再被归进 blogger）。官方公告需要无损保留原文摘要、
带时区发布时间与独立 source=fed 身份，且**不得分进博主**，故独立适配。

来源：`https://www.federalreserve.gov/feeds/press_monetary.xml`（RSS 2.0）。
真实材料实测（2026-09-17 受控采集，证据
``docs/experiments/raw/agent-news-ark-2026-09-17/fed-press-monetary-live-2026-09-17.xml``）：
- pubDate 用 **GMT** 命名时区、CDATA 包裹（如 ``Wed, 16 Sep 2026 18:00:00 GMT``）；
- 响应 UTF-8 带 BOM 且响应头未声明 charset。

时区口径（主控复核 R3）：
- 命名时区**按其明确偏移**处理（EST=-5、EDT=-4 等），不做无来源证据的
  "纠错"（曾把 9 月 16 日 14:00 EST 擅自按夏令时挪一小时，已禁止）；
- 只有来源提供「美东当地时间」语义（本 feed 并未出现）才按日期套用季节
  规则；来源矛盾不可确认时标未知，不静默移动时间；
- EST/EDT 写法仅见于合成夹具（tests/fixtures），真实材料是 GMT，两者在
  注释与测试中分开表述。

比较口径（主控复核 R3）：书签（since）、新旧判断统一按**真实时刻**
（带时区 datetime）比较，不同时区表示的同一时刻不错判；未来日期与
无时区条目不推进书签；整份 feed 时间全部不可解析时抛 NewsSourceError，
不装成一次成功的空采集。
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import compute_dedupe_key
from lei_signal.newsfeed.sources import NewsSourceError
from lei_signal.newsfeed.timeparse import parse_iso_ts

logger = logging.getLogger(__name__)

#: 官方货币政策公告 feed（唯一接入的官方来源，2026-09-17 计划冻结）。
FED_PRESS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
}

#: 命名美国时区 → 其定义的固定偏移（主控复核 R3：按明确偏移，不做无来源
#: "纠错"；仅当来源提供美东当地时间语义时才按日期套季节规则，本 feed 未出现）。
_NAMED_US_ZONE_OFFSETS = {
    "EST": -5, "EDT": -4,
    "CST": -6, "CDT": -5,
    "MST": -7, "MDT": -6,
    "PST": -8, "PDT": -7,
}
_UTC_NAMES = {"GMT", "UT", "UTC", "Z"}

#: RFC 822 日期尾部时区记号（命名或 ±HHMM）。
_TZ_TAIL = re.compile(r"\s+([A-Za-z]{1,5}|[+-]\d{4})\s*$")
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def parse_fed_pubdate(raw: str | None) -> datetime | None:
    """解析官方 feed 的 pubDate 为带时区 datetime；无法确定时区返回 None。

    命名美国时区按其定义偏移（EST=-5、EDT=-4……），数字偏移与 GMT/UT 直接
    采用；完全无时区记号不猜，返回 None。
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
    if token in _NAMED_US_ZONE_OFFSETS:
        return naive.replace(
            tzinfo=timezone(timedelta(hours=_NAMED_US_ZONE_OFFSETS[token]))
        )
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
    """抓官方货币政策公告 feed，过滤发布时间早于等于书签的旧条目。

    返回 ``(items, new_watermark)``；无新内容水位为 None。失败抛
    :class:`NewsSourceError` 由管线降级记录（网络失败单列，不换成无来源
    模型回答）。``fetcher`` 可注入，测试/重放用已保存响应，不打网络。

    主控复核 R3：
    - 书签比较按真实时刻（带时区 datetime），``since_iso`` 非法时报错而非
      静默忽略；
    - 未来日期/无时区条目跳过且不推进书签，记 warning 留痕；整份 feed
      条目时间全部不可解析时抛 NewsSourceError，不装成成功的空采集。
    """
    since_dt: datetime | None = None
    if since_iso is not None:
        since_dt = parse_iso_ts(since_iso)
        if since_dt is None:
            raise NewsSourceError(f"fed 书签时间非法（无时区/坏串）: {since_iso!r}")

    fetch = fetcher or _default_fetch
    try:
        xml_text = fetch(url, timeout)
        # 官方 feed 实测带 UTF-8 BOM（2026-09-17 S1 受控采集）：先剥再解析。
        root = ET.fromstring(xml_text.lstrip("﻿"))
    except NewsSourceError:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一封装为源错误
        raise NewsSourceError(f"fed 官方公告抓取失败: {exc}") from exc

    now_utc = datetime.now(UTC)
    items: list[NewsItem] = []
    newest_dt: datetime | None = None
    seen = 0
    skipped_invalid = 0
    for node in root.iter("item"):
        seen += 1
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or node.findtext("guid") or "").strip()
        if not title or not link:
            continue
        dt = parse_fed_pubdate(node.findtext("pubDate"))
        if dt is None:
            # 无日期/时区不可确定的条目跳过：不能用抓取时间冒充发布时间。
            skipped_invalid += 1
            continue
        if dt > now_utc:
            # 未来日期不推进书签（R3），留痕见下。
            skipped_invalid += 1
            continue
        if since_dt is not None and dt <= since_dt:
            # 真实时刻比较：不同时区表示的同一时刻不误收为新条目。
            continue
        newest_dt = dt if newest_dt is None else max(newest_dt, dt)
        items.append(
            NewsItem(
                source="fed",
                source_name="美联储官网",
                title=title,
                summary=_clean_html(node.findtext("description")),
                url=link,
                published_at=dt.astimezone().isoformat(timespec="seconds"),
                category="macro",  # 官方货币政策公告：宏观类，绝不进 blogger
                dedupe_key=compute_dedupe_key("fed", link, title),
            )
        )
        if len(items) >= limit:
            break
    if seen > 0 and skipped_invalid == seen:
        raise NewsSourceError(
            f"fed 官方公告 {seen} 条目的发布时间均不可解析或为未来时间，"
            "不作为成功的空采集"
        )
    if skipped_invalid:
        logger.warning(
            "fed 官方公告 %d/%d 条因时间不可解析或为未来时间被跳过（不推进书签）",
            skipped_invalid, seen,
        )
    newest = (
        newest_dt.astimezone().isoformat(timespec="seconds")
        if newest_dt is not None else None
    )
    return items, newest


__all__ = ["FED_PRESS_URL", "collect_fed_press", "parse_fed_pubdate"]
