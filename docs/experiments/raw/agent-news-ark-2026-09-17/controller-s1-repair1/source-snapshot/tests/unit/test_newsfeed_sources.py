"""newsfeed 快讯源与 RSS 源单元测试（fixture + monkeypatch，不打真实网络）。"""
from __future__ import annotations

import json

import pytest

from lei_signal.newsfeed.sources import NewsSourceError, rss, sina
from lei_signal.newsfeed.sources import eastmoney as em


class _FakeResp:
    def __init__(self, payload: dict | str, status: int = 200):
        self._payload = payload
        self.status_code = status
        self.text = payload if isinstance(payload, str) else json.dumps(payload)
        self.headers = {"content-type": "application/json"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict | str:
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


# ---------------- eastmoney ----------------

_EM_BODY = {
    "code": "1",
    "data": {
        "sortEnd": "1787829890030186",
        "fastNewsList": [
            {
                "summary": "【山西焦煤：西曲矿恢复生产】山西焦煤8月27日公告，恢复生产。",
                "code": "A",
                "realSort": "1787829926029",
            },
            {
                "summary": "旧条目应被水位过滤",
                "code": "B",
                "realSort": "1787800000000",
            },
            {"summary": "", "code": "C", "realSort": "1787829999999"},
        ],
    },
}


def test_eastmoney_parse_filter_and_watermark(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(em.requests, "get", lambda *a, **k: _FakeResp(_EM_BODY))
    items, wm = em.collect_eastmoney(since_ms=1787800000000)
    assert wm == "1787829999999"
    assert len(items) == 1
    assert items[0].title == "山西焦煤：西曲矿恢复生产"
    assert items[0].source == "eastmoney"
    assert items[0].published_at.startswith("20")


def test_eastmoney_real_sort_microseconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-08-27 实测：realSort 混用 16 位微秒与 13 位毫秒，需归一化。"""
    body = {
        "code": "1",
        "data": {
            "sortEnd": "1787833057036916",
            "fastNewsList": [
                {"summary": "【微秒游标】内容", "realSort": "1787833057036916"},
                {"summary": "【毫秒游标】旧内容", "realSort": "1787800000000"},
            ],
        },
    }
    monkeypatch.setattr(em.requests, "get", lambda *a, **k: _FakeResp(body))
    items, wm = em.collect_eastmoney(since_ms=1787800000000)
    assert wm == "1787833057036"
    assert len(items) == 1
    assert items[0].title == "微秒游标"


def test_eastmoney_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a, **k):
        raise em.requests.RequestException("timeout")

    monkeypatch.setattr(em.requests, "get", boom)
    with pytest.raises(NewsSourceError):
        em.collect_eastmoney(None)


# ---------------- sina ----------------

_SINA_BODY = {
    "result": {
        "status": {"code": 0},
        "data": {
            "feed": {
                "list": [
                    {
                        "id": 5062609,
                        "rich_text": "【永泰运：上半年净利润4807万元】同比下降11%。",
                        "create_time": "2026-08-27 19:28:32",
                    },
                    {
                        "id": 5062600,
                        "rich_text": "旧条目",
                        "create_time": "2026-08-27 18:00:00",
                    },
                ]
            }
        },
    }
}


def test_sina_parse_filter_and_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sina.requests, "get", lambda *a, **k: _FakeResp(_SINA_BODY))
    items, wm = sina.collect_sina(since_id=5062600)
    assert wm == "5062609"
    assert len(items) == 1
    assert items[0].title == "永泰运：上半年净利润4807万元"
    # create_time 北京时间 → 本地 ISO（带时区偏移）
    assert "T19:28:32" in items[0].published_at
    assert items[0].published_at.endswith(("+08:00", "+0800"))


# ---------------- rss ----------------

_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>t</title>
<item><title>Fed cuts rates by 25bp - Reuters</title>
<link>https://example.com/1</link>
<pubDate>Thu, 28 Aug 2026 01:00:00 GMT</pubDate></item>
<item><title>Old item</title><link>https://example.com/2</link>
<pubDate>Wed, 20 Aug 2026 01:00:00 GMT</pubDate></item>
<item><title>No date</title><link>https://example.com/3</link></item>
</channel></rss>"""

_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>t</title>
<entry><title>公众号文章标题</title>
<link href="https://mp.weixin.qq.com/s/abc"/>
<published>2026-08-27T10:00:00+08:00</published></entry>
</feed></rss>""".replace("</rss>", "")


def test_gnews_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict = {}

    def fake_get(url, headers=None, timeout=None):
        calls["url"] = url
        return _FakeResp(_RSS_XML)

    monkeypatch.setattr(rss.requests, "get", fake_get)
    items, wm = rss.collect_rss("NVDA earnings", is_gnews=True, since_iso="")
    assert "news.google.com/rss/search" in calls["url"]
    assert "NVDA+earnings" in calls["url"]
    # since_iso="" 非空 → 两条带日期的都算新（旧比较按字符串，空串最小）
    assert len(items) == 2
    first = items[0]
    assert first.title == "Fed cuts rates by 25bp"
    assert first.source_name == "Reuters"
    assert first.source == "gnews"
    assert wm is not None


def test_gnews_since_filters_old(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rss.requests, "get", lambda *a, **k: _FakeResp(_RSS_XML)
    )
    # since 取比两条都新的时间 → 空
    items, wm = rss.collect_rss("q", is_gnews=True,
                                since_iso="2026-12-31T00:00:00+08:00")
    assert items == [] and wm is None


def test_atom_feed_for_wechat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rss.requests, "get", lambda *a, **k: _FakeResp(_ATOM_XML)
    )
    items, _ = rss.collect_rss("http://localhost:4000/feeds/1.atom",
                               is_gnews=False, since_iso=None)
    assert len(items) == 1
    assert items[0].source == "rss"
    assert items[0].url == "https://mp.weixin.qq.com/s/abc"
    assert items[0].published_at.startswith("2026-08-27T10:00:00")


# ---------------- 美联储官方公告源（2026-09-17 S1） ----------------

from datetime import UTC, datetime  # noqa: E402
from pathlib import Path  # noqa: E402

from lei_signal.newsfeed.sources import fed  # noqa: E402

_FED_XML = (
    Path(__file__).resolve().parents[1]
    / "fixtures" / "newsfeed" / "agent-news" / "fed-press-monetary-sample.xml"
).read_text("utf-8")


def test_fed_parse_fixture_preserves_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fed.requests, "get",
        lambda *a, **k: _FakeBytesResp(_FED_XML.encode("utf-8")))
    items, wm = fed.collect_fed_press(since_iso=None)
    assert len(items) == 3
    stmt = items[0]
    assert stmt.source == "fed" and stmt.source_name == "美联储官网"
    assert stmt.category == "macro"  # 官方公告归宏观，不进 blogger
    assert stmt.title == "Federal Reserve issues FOMC statement"
    assert stmt.url.endswith("monetary20260916a.htm")
    # 原文摘要保留（含加息事实）
    assert "raise the target range" in (stmt.summary or "")
    # 已核事实：2026-09-16 14:00 EDT = 18:00 UTC = 北京时间 9-17 02:00
    assert datetime.fromisoformat(stmt.published_at) == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    assert wm is not None
    assert datetime.fromisoformat(wm) == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)


def test_fed_since_filters_and_no_date_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    xml = _FED_XML.replace(
        "<pubDate>Thu, 10 Sep 2026 13:30:00 EDT</pubDate>", "")
    monkeypatch.setattr(fed.requests, "get", lambda *a, **k: _FakeBytesResp(xml.encode("utf-8")))
    items, _ = fed.collect_fed_press(since_iso=None)
    assert [i.title for i in items] == [
        "Federal Reserve issues FOMC statement",
        "Federal Reserve issues implementation note",
    ]  # 无日期条目跳过：不能用抓取时间冒充发布时间
    # since 覆盖全部 → 空 + 水位 None
    items2, wm2 = fed.collect_fed_press(since_iso="2999-01-01T00:00:00+08:00")
    assert items2 == [] and wm2 is None


def test_fed_fetcher_injection_replay_idempotent() -> None:
    """重放同一材料：fetcher 注入已保存响应，两次解析结果一致（不打网络）。"""
    saved: dict = {"calls": 0}

    def fetcher(url: str, timeout: int) -> str:
        saved["calls"] += 1
        return _FED_XML

    items1, wm1 = fed.collect_fed_press(
        url="https://www.federalreserve.gov/feeds/press_monetary.xml",
        since_iso=None, fetcher=fetcher)
    items2, wm2 = fed.collect_fed_press(
        url="https://www.federalreserve.gov/feeds/press_monetary.xml",
        since_iso=None, fetcher=fetcher)
    assert [i.dedupe_key for i in items1] == [i.dedupe_key for i in items2]
    assert wm1 == wm2


def test_fed_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a, **k):
        raise fed.requests.RequestException("timeout")

    monkeypatch.setattr(fed.requests, "get", boom)
    with pytest.raises(NewsSourceError):
        fed.collect_fed_press(since_iso=None)


def test_fed_pubdate_named_zones_use_defined_offsets() -> None:
    """命名时区按其定义偏移（主控复核 R3），不做无来源"纠错"：

    - EST 恒为 -05:00、EDT 恒为 -04:00——即使日期落在另一个季节，也不
      擅自假定源站写错了去挪动一小时；
    - 已核事实保持：2026-09-16 14:00 EDT = 18:00 UTC（= 北京 9-17 02:00）；
    - 真实材料是 GMT（见 raw 保存响应），EST/EDT 路径为合成夹具覆盖。
    """
    winter = fed.parse_fed_pubdate("Sun, 11 Jan 2026 14:00:00 EST")
    summer = fed.parse_fed_pubdate("Sat, 11 Jul 2026 14:00:00 EDT")
    assert winter is not None and winter.utcoffset().total_seconds() == -5 * 3600
    assert summer is not None and summer.utcoffset().total_seconds() == -4 * 3600
    # 主控探针反例：9 月写 EST 也按其定义 -05:00（14:00 EST = 19:00 UTC），
    # 不得"纠错"成 18:00 UTC
    est_in_sept = fed.parse_fed_pubdate("Wed, 16 Sep 2026 14:00:00 EST")
    assert est_in_sept == datetime(2026, 9, 16, 19, 0, tzinfo=UTC)
    edt_in_sept = fed.parse_fed_pubdate("Wed, 16 Sep 2026 14:00:00 EDT")
    assert edt_in_sept == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    # GMT 与数字偏移
    assert fed.parse_fed_pubdate("Wed, 16 Sep 2026 18:00:00 GMT") == datetime(
        2026, 9, 16, 18, 0, tzinfo=UTC)
    numeric = fed.parse_fed_pubdate("Wed, 16 Sep 2026 14:00:00 -0400")
    assert numeric == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    # 无时区记号不猜
    assert fed.parse_fed_pubdate("Wed, 16 Sep 2026 14:00:00") is None
    assert fed.parse_fed_pubdate(None) is None
    assert fed.parse_fed_pubdate("garbage") is None


def test_fed_since_compares_real_instants() -> None:
    """书签比较统一真实时刻（主控复核 R3 探针反例）：

    feed 条目 18:00 GMT、书签 19:00 UTC → 不是新条目（旧代码转北京时间
    字符串后与 UTC 字符串比较，会误收为新条目）。
    """
    xml = (
        "<rss><channel><item>"
        "<title>Federal Reserve issues FOMC statement</title>"
        "<link>https://www.federalreserve.gov/x.htm</link>"
        "<pubDate>Wed, 16 Sep 2026 18:00:00 GMT</pubDate>"
        "</item></channel></rss>"
    )
    items, wm = fed.collect_fed_press(
        since_iso="2026-09-16T19:00:00+00:00", fetcher=lambda *a: xml)
    assert items == [] and wm is None
    # 书签 17:00 UTC → 同一条目是新条目（18:00 UTC > 17:00 UTC）
    items2, wm2 = fed.collect_fed_press(
        since_iso="2026-09-16T17:00:00+00:00", fetcher=lambda *a: xml)
    assert len(items2) == 1
    assert datetime.fromisoformat(wm2) == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    # 非法书签：报错而非静默忽略
    with pytest.raises(NewsSourceError):
        fed.collect_fed_press(since_iso="not-a-time", fetcher=lambda *a: xml)


def test_fed_future_and_undated_items_not_advancing_watermark() -> None:
    """未来日期/无时区条目不推进书签；全部不可解析 → 显式失败而非空采集。"""
    future_xml = (
        "<rss><channel>"
        "<item><title>Future stmt</title><link>https://www.federalreserve.gov/f.htm</link>"
        "<pubDate>Wed, 16 Sep 2099 14:00:00 GMT</pubDate></item>"
        "<item><title>Federal Reserve issues FOMC statement</title>"
        "<link>https://www.federalreserve.gov/x.htm</link>"
        "<pubDate>Wed, 16 Sep 2026 18:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )
    items, wm = fed.collect_fed_press(since_iso=None, fetcher=lambda *a: future_xml)
    assert [i.title for i in items] == ["Federal Reserve issues FOMC statement"]
    # 水位只到 2026 真实条目，不被 2099 的未来日期顶走
    assert datetime.fromisoformat(wm) == datetime(2026, 9, 16, 18, 0, tzinfo=UTC)

    all_invalid_xml = (
        "<rss><channel>"
        "<item><title>No date</title><link>https://www.federalreserve.gov/n.htm</link></item>"
        "<item><title>Bad date</title><link>https://www.federalreserve.gov/b.htm</link>"
        "<pubDate>not a date</pubDate></item>"
        "</channel></rss>"
    )
    with pytest.raises(NewsSourceError):
        fed.collect_fed_press(since_iso=None, fetcher=lambda *a: all_invalid_xml)


class _FakeBytesResp:
    """带原始字节的响应：_default_fetch 按 utf-8-sig 解码 content。"""

    def __init__(self, body: bytes, status: int = 200):
        self.content = body
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fed_parse_tolerates_utf8_bom(monkeypatch: pytest.MonkeyPatch) -> None:
    """官方 feed 实测带 UTF-8 BOM 且响应头无 charset（2026-09-17 受控采集）：
    按字节 utf-8-sig 解码，不能退化成 ISO-8859-1 乱码。"""
    body = b"\xef\xbb\xbf" + _FED_XML.encode("utf-8")
    monkeypatch.setattr(fed.requests, "get", lambda *a, **k: _FakeBytesResp(body))
    items, wm = fed.collect_fed_press(since_iso=None)
    assert len(items) == 3 and wm is not None


def test_fed_parse_tolerates_str_bom_on_replay() -> None:
    """重放路径传入含 U+FEFF 的文本也能解析（双保险）。"""
    items, wm = fed.collect_fed_press(
        since_iso=None, fetcher=lambda url, timeout: "﻿" + _FED_XML
    )
    assert len(items) == 3 and wm is not None
