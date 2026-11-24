"""Official-article gating and offline cache behavior."""

import json
import sqlite3
from datetime import date

from lei_signal.api import opportunity_news as news

DAY = date(2026, 10, 19)
SOURCE = {
    "id": "official-test",
    "name": "测试官方来源",
    "kind": "industry",
    "market": "us",
    "feed_type": "rss",
    "feed_url": "https://example.gov/feed.xml",
    "official_domains": ["example.gov"],
    "topics": ["半导体"],
    "keywords": ["chip"],
    "importance": 2,
    "event_type": "industry_update",
}
PROFILES = [{"symbol": "SOXX", "name": "半导体 SOXX", "market": "us", "topics": ["半导体"]}]
FEED = """<rss><channel><item><title>Chip manufacturing update</title>
<link>https://example.gov/releases/1</link></item></channel></rss>"""
BODY = "Chip manufacturers described fabrication capacity and equipment supply. " * 4


def article(day: str = "2026-10-18", body: str = BODY) -> str:
    return (
        "<html><head><meta property='article:published_time' content='"
        + day
        + "'></head><body><h1>Chip manufacturing update</h1><article><p>"
        + body
        + "</p></article></body></html>"
    )


def setup(monkeypatch, page: str, feed: str = FEED):
    monkeypatch.setattr(news, "_sources", lambda: [SOURCE])
    calls = []

    def fake_get(url, domains):
        calls.append(url)
        return (feed if url.endswith("feed.xml") else page), url

    monkeypatch.setattr(news, "_get", fake_get)
    return calls


def test_verified_event_cached_deduped_and_get_offline(tmp_path, monkeypatch):
    calls = setup(monkeypatch, article())
    db = tmp_path / "main.sqlite3"
    assert news.news_due(db, DAY, PROFILES)
    first = news.refresh_news(db, DAY, PROFILES)
    assert first["refresh"]["verified_new"] == 1
    assert first["events"][0]["products"] == [
        {"symbol": "SOXX", "name": "半导体 SOXX", "relation": "industry_reference"}
    ]
    assert first["events"][0]["impact"] == "unknown"
    assert len(first["events"][0]["source_document_hash"]) == 64
    assert first["events"][0]["published_at"] == "2026-10-18"
    assert first["coverage"]["expected_sources"] == 1
    assert first["coverage"]["checked_sources"] == 1
    assert len(calls) == 2
    assert not news.news_due(db, DAY, PROFILES)
    assert news.refresh_news(db, DAY, PROFILES)["refresh"]["status"] == "cached"
    assert len(calls) == 2
    assert news.read_news(db, DAY, PROFILES)["events"] == first["events"]
    assert len(calls) == 2
    forced = news.refresh_news(db, DAY, PROFILES, force=True)
    assert forced["refresh"]["verified_new"] == 0
    assert len(calls) == 4


def test_only_title_missing_date_and_short_body_are_not_verified(tmp_path, monkeypatch):
    db = tmp_path / "main.sqlite3"
    setup(monkeypatch, "<html><title>Chip manufacturing update</title></html>")
    missing = news.refresh_news(db, DAY, PROFILES)
    assert missing["events"] == []
    assert missing["coverage"]["missing_date"] == 1
    assert missing["refresh"]["status"] == "partial"
    setup(monkeypatch, article(body="Chip update."))
    short = news.refresh_news(db, DAY, PROFILES, force=True)
    assert short["events"] == []
    assert short["coverage"]["missing_original"] == 1


def test_old_and_future_article_excluded(tmp_path, monkeypatch):
    db = tmp_path / "main.sqlite3"
    setup(monkeypatch, article("2026-10-14"))
    old = news.refresh_news(db, DAY, PROFILES)
    assert old["events"] == []
    assert old["coverage"]["expired"] == 1
    setup(monkeypatch, article("2026-10-20"))
    future = news.refresh_news(db, DAY, PROFILES, force=True)
    assert future["events"] == []
    assert future["coverage"]["missing_date"] == 1
    assert news._published(["2026-10-20", "2026-10-18"], DAY) is None


def test_source_or_business_mismatch_and_failure_cooldown(tmp_path, monkeypatch):
    calls = setup(monkeypatch, article())
    db = tmp_path / "main.sqlite3"
    unmatched = [{"symbol": "XLK", "name": "科技 XLK", "market": "us", "topics": ["软件"]}]
    assert news.refresh_news(db, DAY, unmatched)["events"] == []
    assert calls == []

    def fail(url, domains):
        raise ValueError("source unavailable")

    monkeypatch.setattr(news, "_get", fail)
    result = news.refresh_news(db, DAY, PROFILES)
    assert result["refresh"]["status"] == "partial"
    assert result["coverage"]["failures"][0]["reason_code"] == "feed_ValueError"
    assert result["coverage"]["failures"][0]["source_name"] == "测试官方来源"
    assert result["coverage"]["failed_sources"] == 1
    assert not news.news_due(db, DAY, PROFILES)
    assert news.refresh_news(db, DAY, PROFILES)["refresh"]["status"] == "cooldown"


def test_read_news_does_not_create_cache(tmp_path, monkeypatch):
    setup(monkeypatch, article())
    db = tmp_path / "main.sqlite3"
    assert news.read_news(db, DAY, PROFILES)["events"] == []
    assert not news._cache_path(db).exists()


def test_real_config_schema_and_fake_http_response(tmp_path, monkeypatch):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"schema_version": 1, "sources": [SOURCE]}), encoding="utf-8")
    assert news._sources(path) == [SOURCE]

    class Response:
        url = "https://example.gov/releases/1"
        encoding = "utf-8"

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield article().encode()

        def close(self):
            return None

    calls = []

    def fake_request(url, **kwargs):
        calls.append((url, kwargs["timeout"], kwargs["stream"]))
        return Response()

    monkeypatch.setattr(news.requests, "get", fake_request)
    content, final = news._get("https://example.gov/releases/1", ["example.gov"])
    assert "Chip manufacturing update" in content
    assert final == "https://example.gov/releases/1"
    assert calls == [("https://example.gov/releases/1", 12, True)]


def test_append_only_versions_attempts_and_config_change(tmp_path, monkeypatch):
    source = dict(SOURCE)
    monkeypatch.setattr(news, "_sources", lambda: [source])
    current = {"page": article()}
    calls = []

    def fake_get(url, domains):
        calls.append(url)
        return (FEED if url.endswith("feed.xml") else current["page"]), url

    monkeypatch.setattr(news, "_get", fake_get)
    db = tmp_path / "main.sqlite3"
    first = news.refresh_news(db, DAY, PROFILES)
    first_hash = first["events"][0]["source_document_hash"]
    source["keywords"] = ["manufacturing"]
    assert news.news_due(db, DAY, PROFILES)
    current["page"] = article(body=BODY + "Chip manufacturing line expanded.")
    second = news.refresh_news(db, DAY, PROFILES)
    assert second["refresh"]["verified_new"] == 0
    assert second["events"][0]["source_document_hash"] != first_hash
    assert len(calls) == 4
    with sqlite3.connect(news._cache_path(db)) as conn:
        assert conn.execute("SELECT count(*) FROM opportunity_news_events").fetchone()[0] == 1
        assert (
            conn.execute("SELECT count(*) FROM opportunity_news_event_versions").fetchone()[0] == 2
        )
        assert (
            conn.execute("SELECT count(*) FROM opportunity_news_attempt_history").fetchone()[0] == 2
        )


def test_cross_market_reference_and_empty_index_not_success(tmp_path, monkeypatch):
    source = {**SOURCE, "related_markets": ["us", "cn"]}
    cn_profile = [{"symbol": "515880.SS", "name": "通信ETF", "market": "cn", "topics": ["半导体"]}]
    assert news._matched_products(source, cn_profile) == [
        {
            "symbol": "515880.SS",
            "name": "通信ETF",
            "relation": "cross_market_industry_reference",
        }
    ]
    source["feed_type"] = "html_index"
    monkeypatch.setattr(news, "_sources", lambda: [source])
    monkeypatch.setattr(news, "_get", lambda url, domains: ("<html>No links</html>", url))
    result = news.refresh_news(tmp_path / "main.sqlite3", DAY, cn_profile)
    assert result["events"] == []
    assert result["coverage"]["failures"][0]["reason_code"] == "no_article_links"


def test_html_index_with_only_old_articles_is_partial(tmp_path, monkeypatch):
    source = {**SOURCE, "feed_type": "html_index"}
    monkeypatch.setattr(news, "_sources", lambda: [source])
    index = "<a href='https://example.gov/releases/1'>Chip manufacturing update</a>"
    monkeypatch.setattr(
        news,
        "_get",
        lambda url, domains: (index if url.endswith("feed.xml") else article("2026-10-14"), url),
    )
    result = news.refresh_news(tmp_path / "main.sqlite3", DAY, PROFILES)
    assert result["events"] == []
    assert result["coverage"]["expired"] == 1
    assert result["coverage"]["failures"][0]["reason_code"] == "index_only_expired"


def test_default_and_index_documents_share_directory_identity():
    directory = "https://www.federalreserve.gov/releases/g17/20261016"
    for suffix in ("/", "/default.htm", "/default.html", "/index.htm", "/index.html"):
        assert news._canonical(directory + suffix) == directory
    assert news._canonical(directory + "/default.htm?x=1#section") == directory
