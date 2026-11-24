"""Opportunity public context uses exact identity and bounded persistent lookup."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from lei_signal.api import opportunity_context as context
from lei_signal.api import opportunity_evidence as evidence


def _request(tmp_path):
    state = SimpleNamespace(plans_db_path=str(tmp_path / "plans.db"))
    return SimpleNamespace(app=SimpleNamespace(state=state))


def _snapshot():
    subject = {"key": "symbol:512890.SS", "id": "512890.SS", "name": "红利低波ETF"}
    return {
        "items": [{"subject": subject, "intent": "buy"}, {"subject": subject, "intent": "sell"}]
    }


def test_missing_holding_public_code_never_searches_private_id(tmp_path, monkeypatch):
    request = _request(tmp_path)
    private_id = "private-holding-5045587e5cff"
    holding = {
        "kind": "holding",
        "key": f"holding:{private_id}",
        "id": private_id,
        "name": "红利低波ETF",
        "code": None,
    }
    calls = []
    monkeypatch.setattr(context, "_fetch_headlines", lambda query: calls.append(query) or [])
    only_holding = {"items": [{"subject": holding}]}
    assert context._subjects(only_holding) == []
    assert not context.needs_context(request, only_holding)
    context.prepare_context(request, only_holding)
    assert calls == []

    symbol = {
        "kind": "symbol",
        "key": "symbol:512890.SS",
        "id": "512890.SS",
        "code": private_id,
        "name": "红利低波ETF",
    }
    snapshot = {"items": [{"subject": holding}, {"subject": symbol}]}
    context.prepare_context(request, snapshot)
    assert len(calls) == 2
    assert all(private_id not in query and '"512890"' in query for query in calls)
    assert context._subjects({"items": [{"subject": {**holding, "code": "001513"}}]}) == [
        ("001513", "红利低波ETF")
    ]


def test_curated_source_requires_exact_identity_and_dates(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    path = tmp_path / "sources.json"
    good = {
        "symbol": "512890.SS",
        "name": "红利低波ETF",
        "summary": "公开资料",
        "source_name": "基金公司",
        "source_url": "https://example.test/fund",
        "published_at": today.isoformat(),
        "report_date": today.isoformat(),
    }
    future = (today + timedelta(days=1)).isoformat()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "checked_at": today.isoformat(),
                "products": [
                    good,
                    {**good, "name": "另一只基金"},
                    {**good, "source_url": "http://example.test/fund"},
                    {**good, "report_date": future},
                    {**good, "published_at": future},
                    {**good, "checked_at": future},
                ],
            }
        )
    )
    rows = context.public_sources("512890.SS", "红利低波ETF", today=today, path=path)
    assert len(rows) == 1
    assert rows[0]["report_date"] == today.isoformat()
    assert context.public_sources("512890.SS", "错误名称", today=today, path=path) == []


def test_real_communication_alias_binds_one_canonical_product() -> None:
    today = date(2026, 10, 15)
    rows = context.public_sources("515880.SS", "通信ETF国泰", today=today)
    assert len(rows) == 4
    assert any("2026年中期报告" in row["source"] for row in rows)
    assert any("新易盛2026年半年度报告" in row["source"] for row in rows)
    assert not any("电信业务收入" in row["text"] for row in rows)
    assert next(row for row in rows if "十五五" in row["source"])["relevance"] == "indirect"
    assert context.public_sources("515880.SS", "通信ETF", today=today) == rows
    assert context.public_sources("512890.SS", "通信ETF国泰", today=today) == []
    assert context.public_sources("515880.SS", "通信", today=today) == []
    assert context.public_sources("515880.SS", "错误名称", today=today) == []


def test_conflicting_alias_for_same_symbol_is_rejected(tmp_path) -> None:
    today = date(2026, 10, 15)
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "checked_at": today.isoformat(),
        "products": [
            {"symbol": "515880.SS", "name": "产品甲", "aliases": ["共同别名"],
             "summary": "甲", "source_name": "甲来源", "source_url": "https://example.test/a",
             "published_at": today.isoformat()},
            {"symbol": "515880.SS", "name": "产品乙", "aliases": ["共同别名"],
             "summary": "乙", "source_name": "乙来源", "source_url": "https://example.test/b",
             "published_at": today.isoformat()},
        ],
    }))
    assert context.public_sources("515880.SS", "共同别名", today=today, path=path) == []
    assert context.public_sources("515880.SS", "产品甲", today=today, path=path)[0]["text"] == "甲"


def test_report_date_without_publication_and_static_profile_preserve_unknowns(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    base = {
        "symbol": "512890.SS",
        "name": "红利低波ETF",
        "source_name": "基金公司",
        "source_url": "https://example.test/profile",
    }
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "checked_at": today.isoformat(),
                "products": [
                    {**base, "summary": "季度报告数据", "report_date": today.isoformat()},
                    {**base, "summary": "静态投资范围", "provenance": "product_profile"},
                ],
            }
        )
    )
    rows = context.public_sources("512890.SS", "红利低波ETF", today=today, path=path)
    assert len(rows) == 2
    report, profile = rows
    assert report["date"] == today.isoformat() and report["published_at"] is None
    assert report["provenance"] == "reporting_date_only"
    assert any("发布日期未知" in text for text in report["limitations"])
    assert profile["date"] is None and profile["published_at"] is None
    assert profile["category"] == "industry" and profile["provenance"] == "product_profile"
    assert any("最新成分" in text for text in profile["limitations"])


def test_prepare_context_queries_once_for_both_directions_and_survives_restart(
    tmp_path, monkeypatch
):
    request = _request(tmp_path)
    snapshot = _snapshot()
    calls = []

    def fake_fetch(query):
        calls.append(query)
        today = datetime.now(ZoneInfo("Asia/Shanghai"))
        return [("红利低波ETF 公告", "https://example.test/news", today, "交易所")]

    monkeypatch.setattr(context, "_fetch_headlines", fake_fetch)
    assert context.needs_context(request, snapshot)
    assert context.cached_news(request, "512890.SS", "红利低波ETF")["status"] == "unavailable"
    context.prepare_context(request, snapshot)
    assert len(calls) == 2
    assert all('"512890"' in query and '"512890.SS"' not in query for query in calls)
    assert all("when:7d" in query for query in calls)
    assert sum("风险 OR" in query for query in calls) == 1
    restarted = _request(tmp_path)
    assert not context.needs_context(restarted, snapshot)
    news = context.cached_news(restarted, "512890.SS", "红利低波ETF")
    assert news["status"] == "checked" and len(news["leads"]) == 1
    risk = context.cached_risk_news(restarted, "512890.SS", "红利低波ETF")
    assert risk["status"] == "checked" and risk["count"] == 1
    assert risk["checked_at"] and risk["query"] in calls and risk["error"] == ""
    context.prepare_context(restarted, snapshot)
    assert len(calls) == 2


def test_prepared_context_reuses_reads_while_another_writer_holds_database(tmp_path, monkeypatch):
    request = _request(tmp_path)
    calls = []
    monkeypatch.setattr(context, "_fetch_headlines", lambda query: calls.append(query) or [])
    context.prepare_context(request, _snapshot())
    assert len(calls) == 2
    with sqlite3.connect(request.app.state.plans_db_path) as writer:
        writer.execute("BEGIN IMMEDIATE")
        context.prepare_context(request, _snapshot())
        assert len(calls) == 2
        writer.rollback()


def test_repeated_context_reads_close_database_handles(tmp_path, monkeypatch):
    request = _request(tmp_path)
    opened = []
    original_connect = sqlite3.connect

    class Connection(sqlite3.Connection):
        closed = False

        def close(self):
            self.closed = True
            super().close()

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs, factory=Connection)
        opened.append(connection)
        return connection

    monkeypatch.setattr(context.sqlite3, "connect", connect)
    monkeypatch.setattr(context, "_fetch_headlines", lambda query: [])
    context.prepare_context(request, _snapshot())
    for _ in range(20):
        context.cached_news(request, "512890.SS", "红利低波ETF")
        context.cached_risk_news(request, "512890.SS", "红利低波ETF")
    assert opened and all(connection.closed for connection in opened)


def test_busy_cache_write_waits_then_commits_without_repeating_lookup(tmp_path, monkeypatch):
    request = _request(tmp_path)
    db_path = request.app.state.plans_db_path
    monkeypatch.setattr(context, "_SQLITE_WRITE_TIMEOUT", 0.02)
    calls = []
    original_write = context._write_cache
    locked = threading.Event()
    holders = []

    def hold_lock():
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            locked.set()
            time.sleep(0.07)

    def write_with_one_lock(path, write):
        if write.__name__ == "save_result" and not holders:
            holder = threading.Thread(target=hold_lock)
            holders.append(holder)
            holder.start()
            assert locked.wait(1)
        return original_write(path, write)

    monkeypatch.setattr(context, "_write_cache", write_with_one_lock)
    published = datetime.now(ZoneInfo("Asia/Shanghai"))

    def fetch(query):
        calls.append(query)
        return [("红利低波ETF 公告", "https://example.test/news", published, "交易所")]

    monkeypatch.setattr(context, "_fetch_headlines", fetch)
    try:
        context.prepare_context(request, _snapshot())
    finally:
        for holder in holders:
            holder.join(timeout=1)
    assert len(calls) == 2
    assert not context.needs_context(request, _snapshot())
    saved = context.cached_news(request, "512890.SS", "红利低波ETF")
    assert saved["status"] == "checked"
    assert saved["leads"][0]["published_at"] == published.isoformat()


def test_persistent_busy_cache_write_keeps_original_error(tmp_path, monkeypatch):
    path = str(tmp_path / "locked.sqlite")
    monkeypatch.setattr(context, "_SQLITE_WRITE_TIMEOUT", 0.01)
    with sqlite3.connect(path) as writer:
        writer.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError) as error:
            context._write_cache(path, lambda conn: conn.execute("CREATE TABLE blocked(value)"))
        assert error.value.sqlite_errorcode & 0xFF == sqlite3.SQLITE_BUSY
        writer.rollback()
    with sqlite3.connect(path) as conn:
        assert (
            conn.execute("SELECT name FROM sqlite_master WHERE name='blocked'").fetchone()
            is None
        )


def test_non_busy_cache_error_is_not_retried(tmp_path, monkeypatch):
    path = str(tmp_path / "broken.sqlite")
    calls = []
    monkeypatch.setattr(context, "_SQLITE_WRITE_TIMEOUT", 0.01)

    def invalid(conn):
        calls.append(1)
        conn.execute("INSERT INTO absent VALUES (1)")

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        context._write_cache(path, invalid)
    assert calls == [1]


def test_failed_lookup_is_recorded_once_for_day(tmp_path, monkeypatch):
    request = _request(tmp_path)
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("network")

    monkeypatch.setattr(context, "_fetch_headlines", fail)
    context.prepare_context(request, _snapshot())
    assert context.cached_news(request, "512890.SS", "红利低波ETF")["status"] == "unavailable"
    context.prepare_context(_request(tmp_path), _snapshot())
    assert len(calls) == 2


def test_old_general_cache_still_requires_recorded_risk_lookup(tmp_path, monkeypatch):
    request = _request(tmp_path)
    subject = ("512890.SS", "红利低波ETF")
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    with sqlite3.connect(request.app.state.plans_db_path) as conn:
        context._ensure_table(conn)
        conn.execute(
            "INSERT INTO opportunity_context_sources "
            "(symbol,product_name,checked_on,status,leads_json,error) "
            "VALUES (?,?,?,'checked','[]','')",
            (*subject, today),
        )
    before = context.cached_risk_news(request, *subject)
    assert before["status"] == "unavailable" and before["checked_at"] is None
    assert context.needs_context(request, _snapshot())
    calls = []
    monkeypatch.setattr(context, "_fetch_headlines", lambda query: calls.append(query) or [])
    context.prepare_context(request, _snapshot())
    assert len(calls) == 1 and "风险 OR" in calls[0]
    after = context.cached_risk_news(request, *subject)
    assert after["status"] == "checked" and after["count"] == 0
    assert "不代表没有风险" in after["detail"]
    assert not context.needs_context(request, _snapshot())


def test_risk_lookup_failure_retry_does_not_repeat_general_news(tmp_path, monkeypatch):
    request = _request(tmp_path)
    calls = []
    risk_fail = {"value": True}

    def fetch(query):
        calls.append(query)
        if "风险 OR" in query and risk_fail["value"]:
            raise TimeoutError("network")
        return []

    monkeypatch.setattr(context, "_fetch_headlines", fetch)
    context.prepare_context(request, _snapshot())
    receipt = context.cached_risk_news(request, "512890.SS", "红利低波ETF")
    assert receipt["status"] == "unavailable" and receipt["error"] == "TimeoutError"
    assert receipt["checked_at"] and receipt["count"] == 0
    assert not context.needs_context(request, _snapshot())
    risk_fail["value"] = False
    context.prepare_context(request, _snapshot(), retry_failed=True)
    assert len(calls) == 3 and sum("风险 OR" in query for query in calls) == 2
    assert context.cached_risk_news(request, "512890.SS", "红利低波ETF")["status"] == "checked"


def test_explicit_retry_rechecks_failed_news_but_reuses_successful_empty_result(
    tmp_path, monkeypatch
):
    request = _request(tmp_path)
    calls = []

    def fetch(query):
        calls.append(query)
        if "风险 OR" not in query and sum("风险 OR" not in item for item in calls) == 1:
            raise TimeoutError("network")
        return []

    monkeypatch.setattr(context, "_fetch_headlines", fetch)
    context.prepare_context(request, _snapshot())
    assert not context.needs_context(request, _snapshot())
    assert context.needs_context(request, _snapshot(), retry_failed=True)
    context.prepare_context(request, _snapshot(), retry_failed=True)
    assert len(calls) == 3
    assert sum("风险 OR" in query for query in calls) == 1
    assert context.cached_news(request, "512890.SS", "红利低波ETF")["status"] == "checked"
    assert not context.needs_context(request, _snapshot(), retry_failed=True)
    context.prepare_context(request, _snapshot(), retry_failed=True)
    assert len(calls) == 3


def test_only_recent_nonfuture_headlines_are_kept(tmp_path, monkeypatch):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    monkeypatch.setattr(
        context,
        "_fetch_headlines",
        lambda _query: [
            ("红利低波ETF 旧文", "https://example.test/old", now - timedelta(days=8), "来源"),
            ("红利低波ETF 未来", "https://example.test/future", now + timedelta(days=1), "来源"),
            (
                "红利低波ETF 今日",
                "https://example.test/current",
                now - timedelta(minutes=1),
                "来源",
            ),
        ],
    )
    _, result = context._query(("512890.SS", "红利低波ETF"), now.date())
    assert [lead["title"] for lead in result["leads"]] == ["红利低波ETF 今日"]


def test_risk_direction_query_keeps_only_exact_product_headline(monkeypatch):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    seen = []

    def fetch(query):
        seen.append(query)
        return [
            ("另一只基金 风险", "https://example.test/other", now, "来源"),
            ("红利低波ETF 风险", "https://example.test/exact", now, "来源"),
        ]

    monkeypatch.setattr(context, "_fetch_headlines", fetch)
    _, result = context._query(("512890.SS", "红利低波ETF"), now.date(), risk=True)
    assert len(seen) == 1 and "风险 OR 亏损 OR 下调 OR 调查 OR risk OR downgrade" in seen[0]
    assert '"512890"' in seen[0] and '"512890.SS"' not in seen[0]
    assert result["count"] == 1
    assert [lead["source_url"] for lead in result["leads"]] == ["https://example.test/exact"]


def test_interrupted_running_row_can_be_reclaimed_without_retrying_success(tmp_path, monkeypatch):
    request = _request(tmp_path)
    subject = ("512890.SS", "红利低波ETF")
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    old = (datetime.now(ZoneInfo("UTC")) - timedelta(minutes=2)).isoformat()
    with sqlite3.connect(request.app.state.plans_db_path) as conn:
        context._ensure_table(conn)
        conn.execute(
            "INSERT INTO opportunity_context_sources "
            "(symbol,product_name,checked_on,status,leads_json,error,started_at) "
            "VALUES (?,?,?,'running','[]','',?)",
            (*subject, today, old),
        )
    assert context.needs_context(request, _snapshot())
    assert "中断" in context.cached_news(request, *subject)["detail"]
    calls = []

    def fetched(_query):
        calls.append(1)
        return []

    monkeypatch.setattr(context, "_fetch_headlines", fetched)
    context.prepare_context(request, _snapshot())
    assert len(calls) == 2 and not context.needs_context(request, _snapshot())
    assert "近七日" in context.cached_news(request, *subject)["detail"]
    context.prepare_context(request, _snapshot())
    assert len(calls) == 2


def test_title_matches_exact_name_curated_alias_or_bare_code_only(tmp_path, monkeypatch):
    source = tmp_path / "sources.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "products": [
                    {
                        "symbol": "512890.SS",
                        "name": "红利低波ETF",
                        "aliases": ["红利低波", "信息产业"],
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(context, "SOURCES_PATH", source)
    aliases = context._aliases("512890.SS", "红利低波ETF")
    assert aliases == ["红利低波"]
    assert context._title_matches("红利低波公告", "512890.SS", "红利低波ETF", aliases)
    assert context._title_matches("基金512890公告", "512890.SS", "红利低波ETF", aliases)
    assert not context._title_matches("信息产业变化", "512890.SS", "红利低波ETF", aliases)
    assert not context._title_matches("15128901公告", "512890.SS", "红利低波ETF", aliases)


def test_title_rejects_tokenized_etf_conversion_namesake_only():
    code, name, aliases = "SOXX", "iShares Semiconductor ETF", ["SOXX"]
    assert not context._title_matches(
        "Robinhood Tokenized SOXX ETF Convert to crypto assets", code, name, aliases
    )
    assert not context._title_matches(
        "Convert 1 SOXX (iShares Semiconductor ETF • Robinhood Token) "
        "to TRY (Turkish Lira) - Bybit",
        code,
        name,
        aliases,
    )
    assert not context._title_matches("SOXX代币兑换加密资产", code, name, aliases)
    assert context._title_matches("SOXX ETF holdings report released", code, name, aliases)
    assert context._title_matches(
        "Tokenized products grow as SOXX ETF tracks semiconductors", code, name, aliases
    )


def test_cached_token_namesake_is_removed_from_card_without_requery(tmp_path, monkeypatch):
    request = _request(tmp_path)
    subject = ("SOXX", "iShares Semiconductor ETF")
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    title = (
        "Convert 1 SOXX (iShares Semiconductor ETF • Robinhood Token) "
        "to TRY (Turkish Lira) - Bybit"
    )
    token = {
        "title": title,
        "published_at": now.isoformat(),
        "source_name": "Google News",
        "source_url": "https://example.test/token-conversion",
    }
    original = {
        **token,
        "title": "SOXX ETF publishes holdings update",
        "source_url": "https://example.test/etf-update",
    }
    with sqlite3.connect(request.app.state.plans_db_path) as conn:
        context._ensure_table(conn)
        conn.execute(
            "INSERT INTO opportunity_context_sources "
            "(symbol,product_name,checked_on,status,leads_json,error) "
            "VALUES (?,?,?,'checked',?,'')",
            (*subject, now.date().isoformat(), json.dumps([token, original])),
        )
        conn.execute(
            "INSERT INTO opportunity_context_risk_sources "
            "(symbol,product_name,checked_on,status,leads_json,error,query,"
            "checked_at,matched_count) "
            "VALUES (?,?,?,'checked',?,'',?,?,1)",
            (
                *subject,
                now.date().isoformat(),
                json.dumps([token]),
                "recorded risk query",
                now.isoformat(),
            ),
        )
    monkeypatch.setattr(context, "public_sources", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        context,
        "_fetch_headlines",
        lambda _query: (_ for _ in ()).throw(AssertionError("cache read must not requery")),
    )
    ordinary = context.cached_news(request, *subject)
    risk = context.cached_risk_news(request, *subject)
    assert [item["title"] for item in ordinary["leads"]] == [original["title"]]
    assert risk["leads"] == []
    assert risk["count"] == 1 and risk["query"] == "recorded risk query"
    assert "排除" in ordinary["detail"] and "排除" in risk["detail"]
    card = {"evidence": [], "searches": [], "limitations": []}
    evidence._public_context(request, card, *subject, now)
    assert all(title not in item["text"] for item in card["evidence"])
    assert any(original["title"] in item["text"] for item in card["evidence"])
    receipt = next(item for item in card["searches"] if item["name"] == "同产品风险方向标题检索")
    assert receipt["count"] == 1 and receipt["query"] == "recorded risk query"


def test_unstarted_subject_is_not_marked_checked_at_batch_deadline(tmp_path, monkeypatch):
    subjects = [
        {"key": f"symbol:{code}.SS", "id": f"{code}.SS", "name": f"基金{code}"}
        for code in ("512890", "510300", "515880")
    ]
    snapshot = {"items": [{"subject": item} for item in subjects]}
    monkeypatch.setattr(context, "_BATCH_DEADLINE", 0.01)

    def slow_fetch(_query):
        time.sleep(0.04)
        return []

    monkeypatch.setattr(context, "_fetch_headlines", slow_fetch)
    request = _request(tmp_path)
    context.prepare_context(request, snapshot)
    missing = [
        s
        for s in subjects
        if context._read_saved(
            request,
            (s["id"], s["name"]),
            datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
        )
        is None
    ]
    assert len(missing) >= 1
    assert len(missing) + sum(
        context._read_risk_saved(
            request,
            (s["id"], s["name"]),
            datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
        ) is None
        for s in subjects
    ) >= 4
    assert context.needs_context(request, snapshot)


def test_focus_routes_exact_sector_and_broad_identity_without_name_guessing():
    assert context.narrative_focus("515880.SS", "通信ETF国泰")["kind"] == "sector"
    assert context.narrative_focus("515880.SS", "通信ETF国泰")["topics"] == [
        "光模块", "数据中心互联", "通信设备"]
    assert context.narrative_focus("000300.SS", "沪深300") == {
        "kind": "broad", "label": "市场宏观", "market": "cn", "topics": []}
    assert context.narrative_focus("^GSPC", "标普500")["market"] == "us"
    assert context.narrative_focus("515880.SS", "通信")["kind"] == "unknown"
    assert context.narrative_focus("unknown", "沪深300")["kind"] == "unknown"
    assert context.macro_markets({"items": [
        {"narrative_focus": {"market": "cn"}}, {"narrative_focus": {"market": "cn"}},
        {"narrative_focus": {"market": "us"}},
        {"narrative_focus": {"market": "hk"}}, {}]}) == ["cn", "us"]
