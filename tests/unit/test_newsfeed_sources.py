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
