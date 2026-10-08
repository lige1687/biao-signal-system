"""Boundaries for the local, read-only GPT context transport."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from lei_signal.integrations.gpt_context import _MAX_HTTP_BYTES, SystemContext


def _packet(root: Path, *, slot: str = "1135", stamp: str = "2026-10-08T11:39:00+08:00") -> None:
    folder = root / "data/cache/portfolio-chat-briefing"
    folder.mkdir(parents=True, exist_ok=True)
    value = {
        "slot": slot,
        "generated_at": stamp,
        "holding_record_as_of": "2026-09-04",
        "coverage": {"total": 1, "with_plan": 0, "with_technical": 0},
        "holdings": [{"code": "013403", "holding_id": "one"}],
        "trade_ledger": {"records": [], "changes": [], "reconciliation_note": "旧快照未对账"},
        "news": [
            {"title": "代码未绑定的标题", "symbols": None},
            {
                "title": "明确绑定",
                "symbols": ["013403"],
                "published_at": "2026-10-08T10:00:00+08:00",
            },
            {"title": "其他基金", "symbols": ["012345"]},
        ],
        "blogger_yesterday": [{"title": "作者记录", "symbols": None}],
        "news_coverage": {
            "returned": 4,
            "total": 4,
            "last_run": {
                "finished_at": "2026-10-08T00:40:00+08:00",
                "status": "partial",
                "errors": [{"source": "blogger"}],
            },
        },
        "configured_authors": [{"name": "作者"}],
        "unqualified_news": [{"reason": "发布时间缺失"}],
        "user_stated_context": [
            {"fund_code": "013403", "text": "当初看好恒科"},
            {"fund_code": "012345", "text": "另一只基金"},
        ],
        "user_context_note": "原话不是已确认计划",
        "source_status": {"workspace": {"ok": True}, "user_context": {"ok": True}},
    }
    (folder / f"packet-20261008T113900000000-{slot}-fixed.json").write_text(
        json.dumps(value, ensure_ascii=False), encoding="utf-8"
    )


def _fake(path: str):
    data = {
        "/api/portfolio/workspace": {
            "generated_at": "2026-10-08T11:40:00+08:00",
            "as_of": "2026-09-04",
            "coverage": {"total": 1, "with_plan": 0, "with_technical": 0},
            "items": [
                {
                    "code": "013403",
                    "holding_id": "one",
                    "plan": None,
                    "technical": {"meta": {"is_intraday_forming": True}},
                    "status": "incomplete",
                    "gaps": ["未能确认同一产品的技术行情"],
                }
            ],
        },
        "/api/portfolio": {
            "as_of": "2026-09-04",
            "groups": [
                {"name": "港股", "holdings": [{"code": "013403", "report_quarter": "2026Q2"}]}
            ],
        },
        "/api/plans": [{"plan_id": "other", "symbol": "SZ000001", "state": "entered"}],
        "/api/plans/summary": {
            "open_actions": 0,
            "active_plans": 1,
            "today_opportunities": 0,
            "today_signal_total": 0,
        },
        "/api/fundamentals/observations?market=cn": {"generated_at": "2026-10-08", "items": []},
        "/api/fundamentals/observations?market=us": {"generated_at": "2026-10-08", "items": []},
        "/api/factors/panel": {"generated_at": "2026-10-07", "data_as_of": "2026-10-06"},
        "/api/experiments": {"items": []},
        "/api/upgrades": {"generated_at": "2026-10-08T11:30:00+08:00", "items": []},
    }
    return data[path]


def test_named_saved_candidates_and_fixed_product_analysis(tmp_path):
    root = Path(__file__).resolve().parents[2]

    def fetch(path):
        if path == "/api/watchlist":
            return []
        if path == "/api/opportunities/today":
            return {
                "scan_date": "2026-10-08",
                "waiting": [
                    {"symbol": "515880.SS", "display_name": "515880.SS"},
                    {"symbol": "IGV", "display_name": None},
                ],
                "actionable": [],
                "blocked": [],
            }
        if path == "/api/symbols/515880.SS/detail":
            return {"symbol": "515880.SS", "meta": {"last_bar_date": "2026-09-30"}}
        raise AssertionError(path)

    context = SystemContext(root, fetch=fetch)
    data = context.opportunities()["data"]
    assert data["waiting"][0]["display_name"] == "国泰中证全指通信设备ETF"
    assert data["waiting"][1]["display_name"] == "iShares软件行业ETF"
    assert data["requires_detail_review"] is True
    assert context.analysis("515880.SS")["data"]["meta"]["last_bar_date"] == "2026-09-30"
    assert context.analysis("../secret")["available"] is False


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://example.com:8000",
        "http://user:pass@127.0.0.1:8000",
        "http://127.0.0.1:8000/api",
        "http://127.0.0.1:8000?refresh=true",
        "http://127.0.0.1:8000#frag",
    ],
)
def test_rejects_nonlocal_or_decorated_base(url: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SystemContext(tmp_path, url, fetch=_fake)


def test_allowlist_rejects_arbitrary_get_and_refresh(tmp_path: Path) -> None:
    context = SystemContext(tmp_path, fetch=_fake)
    for path in (
        "/api/symbols/QQQ/detail?refresh=true",
        "/api/factors/panel?refresh=true",
        "/api/experiments/../../secret",
        "http://example.com/",
    ):
        with pytest.raises(ValueError):
            context._get(path)


def test_missing_plan_and_intraday_remain_gaps(tmp_path: Path) -> None:
    context = SystemContext(tmp_path, fetch=_fake)
    portfolio = context.portfolio("013403")
    assert portfolio["data"]["items"][0]["status"] == "incomplete"
    assert portfolio["data"]["items"][0]["technical"]["meta"]["is_intraday_forming"]
    assert context.plans("013403")["data"]["plans"] == []
    assert context.portfolio("../bad")["available"] is False


def test_packet_views_preserve_cache_date_and_only_explicit_news_binding(tmp_path: Path) -> None:
    _packet(tmp_path)
    context = SystemContext(tmp_path, fetch=_fake)
    news = context.news("013403")
    assert [x["title"] for x in news["data"]["items"]] == ["明确绑定"]
    assert news["data"]["news_coverage"]["last_run"]["errors"]
    assert datetime.fromisoformat(news["generated_at"]).tzinfo is not None
    assert news["data"]["packet_generated_at"] == "2026-10-08T11:39:00+08:00"
    assert news["sources"]["briefing_packet"]["source_generated_at"] == "2026-10-08T11:39:00+08:00"
    assert news["errors"]["news_receipt"]
    assert context.news("999999")["data"]["items"] == []
    assert context.trades()["data"]["trade_ledger"]["reconciliation_note"] == "旧快照未对账"
    brief = context.latest_brief("1135")
    assert brief["data"]["holding_record_as_of"] == "2026-09-04"
    assert context.latest_brief("1440")["available"] is False


def test_blogger_records_are_separate_from_general_news_limit(tmp_path: Path) -> None:
    _packet(tmp_path)
    path = next((tmp_path / "data/cache/portfolio-chat-briefing").glob("packet-*.json"))
    packet = json.loads(path.read_text())
    packet["news"] = [{"title": f"general {n}", "symbols": None} for n in range(25)]
    packet["blogger_yesterday"] = [
        {"title": "author one", "symbols": ["013403"]},
        {"title": "author two", "symbols": None},
    ]
    path.write_text(json.dumps(packet))
    context = SystemContext(tmp_path, fetch=_fake)
    all_news = context.news(limit=20)
    assert len(all_news["data"]["items"]) == 20
    assert [x["title"] for x in all_news["data"]["blogger_yesterday"]] == [
        "author one",
        "author two",
    ]
    assert [x["title"] for x in context.news("013403")["data"]["blogger_yesterday"]] == [
        "author one"
    ]
    assert "不能当作某只基金" in " ".join(all_news["limitations"])


def test_user_stated_reason_is_filtered_and_not_promoted_to_plan(tmp_path: Path) -> None:
    _packet(tmp_path)
    context = SystemContext(tmp_path, fetch=_fake)
    portfolio = context.portfolio("013403")
    assert portfolio["data"]["user_stated_context"] == [
        {"fund_code": "013403", "text": "当初看好恒科"}
    ]
    assert portfolio["data"]["items"][0]["plan"] is None
    assert portfolio["data"]["user_context_packet_generated_at"] == "2026-10-08T11:39:00+08:00"
    assert portfolio["sources"]["briefing_packet"]["path"]
    assert context.latest_brief()["data"]["user_context_note"] == "原话不是已确认计划"
    assert len(context.latest_brief()["data"]["user_stated_context"]) == 2


def test_source_failure_is_visible_without_suppressing_other_sources(tmp_path: Path) -> None:
    def fetch(path: str):
        if path == "/api/factors/panel":
            raise ValueError("offline")
        return _fake(path)

    result = SystemContext(tmp_path, fetch=fetch).overview()
    assert result["available"]
    assert result["errors"]["factors"] == "offline"
    assert result["data"]["workspace"]["coverage"]["total"] == 1
    assert result["data"]["chatgpt_direct_local_connection_verified"] is False
    assert result["sources"]["factors"]["available"] is False
    assert result["sources"]["workspace"]["path"] == "/api/portfolio/workspace"
    assert result["sources"]["workspace"]["retrieved_at"]


def test_overview_bounds_upgrade_progress_and_keeps_ledger_date(tmp_path: Path) -> None:
    goals = [
        {
            "id": f"okr-{n}",
            "title": f"target {n}",
            "kind": "concrete",
            "status": "in_progress",
            "owner": "owner",
            "progress": {"done": 1, "total": 2},
            "evidence": "receipt" * 120 if n == 0 else "receipt",
            "links": [{"url": f"local-{i}"} for i in range(7)] if n == 0 else [],
            "next_action": "verify" * 80 if n == 0 else "verify",
            "updated_at": "2026-10-08T09:00:00+08:00",
            "authorization": {
                "granted": True,
                "at": "2026-10-08T09:00:00+08:00",
                "scope": "specific work only",
            },
            "history": ["private history"],
        }
        for n in range(105)
    ]

    def fetch(path: str):
        if path == "/api/upgrades":
            return {"generated_at": "2026-10-08T11:30:00+08:00", "items": goals}
        return _fake(path)

    result = SystemContext(tmp_path, fetch=fetch).overview()
    upgrades = result["data"]["system_upgrades"]
    assert upgrades["generated_at"] == "2026-10-08T11:30:00+08:00"
    assert (upgrades["total"], upgrades["matched_total"], upgrades["returned"]) == (105, 105, 10)
    assert (upgrades["truncated"], len(upgrades["items"])) == (True, 10)
    assert upgrades["status_counts"] == {"in_progress": 105}
    assert upgrades["items"][0]["progress"] == {"done": 1, "total": 2}
    assert "history" not in upgrades["items"][0]
    assert len(upgrades["items"][0]["evidence"]) == 500
    assert len(upgrades["items"][0]["next_action"]) == 300
    assert len(upgrades["items"][0]["links"]) == 5
    assert upgrades["items"][0]["fields_truncated"] == {"evidence": True, "next_action": True}
    assert upgrades["items"][0]["links_truncated"] is True
    assert upgrades["items"][0]["authorization_scope_omitted"] is True
    assert "scope" not in upgrades["items"][0]["authorization"]
    assert upgrades["items"][1]["fields_truncated"] == {"evidence": False, "next_action": False}
    assert result["sources"]["upgrades"]["source_generated_at"] == upgrades["generated_at"]
    assert "跨 AI" in " ".join(result["limitations"])
    assert "granted=true" in " ".join(result["limitations"])
    filtered = SystemContext(tmp_path, fetch=fetch).overview(query="okr-104", limit=2)
    filtered_upgrades = filtered["data"]["system_upgrades"]
    assert (
        filtered_upgrades["total"],
        filtered_upgrades["matched_total"],
        filtered_upgrades["returned"],
        filtered_upgrades["truncated"],
    ) == (105, 1, 1, False)
    assert filtered_upgrades["items"][0]["id"] == "okr-104"
    empty = SystemContext(tmp_path, fetch=fetch).overview(query="not present")
    assert empty["data"]["system_upgrades"]["matched_total"] == 0
    assert empty["sources"]["upgrades"]["available"] is True


def test_overview_rejects_bad_query_and_limit_without_fetch(tmp_path: Path) -> None:
    def no_fetch(_path: str):
        raise AssertionError("invalid input must not call API")

    context = SystemContext(tmp_path, fetch=no_fetch)
    for query in ("x" * 161, "bad\x00query"):
        assert context.overview(query=query)["available"] is False
    for limit in (0, 21, True, "10"):
        assert context.overview(limit=limit)["available"] is False


def test_overview_keeps_upgrade_source_failure_separate(tmp_path: Path) -> None:
    def fetch(path: str):
        if path == "/api/upgrades":
            raise ValueError("goal database offline")
        return _fake(path)

    result = SystemContext(tmp_path, fetch=fetch).overview()
    assert result["available"]
    assert result["errors"]["upgrades"] == "goal database offline"
    assert result["sources"]["upgrades"]["available"] is False
    assert result["data"]["workspace"]["coverage"]["total"] == 1
    assert result["data"]["system_upgrades"]["total"] is None
    assert result["data"]["system_upgrades"]["matched_total"] is None


def test_only_us_macro_uses_longer_timeout(tmp_path: Path) -> None:
    class Response:
        status = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return b"{}"

    class Opener:
        def __init__(self):
            self.calls = []

        def open(self, request, timeout):
            self.calls.append((request.full_url, timeout))
            return Response()

    context = SystemContext(tmp_path)
    opener = Opener()
    context._opener = opener
    assert context.fundamentals(section="us-macro")["available"]
    assert context.fundamentals(section="rates")["available"]
    assert opener.calls[0][1] == 30
    assert opener.calls[1][1] == 8


def test_fixed_fundamental_sections_preserve_scope_and_payload(tmp_path: Path) -> None:
    expected = {
        "observations": ("/api/fundamentals/observations?market=us", "us", True),
        "overview": ("/api/fundamentals/overview", "mixed", False),
        "rates": ("/api/fundamentals/rates", "mixed", False),
        "us-macro": ("/api/fundamentals/us-macro", "us", False),
        "rates-history": (
            "/api/fundamentals/rates-history?lookback_days=1095",
            "mixed",
            False,
        ),
        "macro-history": ("/api/fundamentals/macro-history?page_size=60", "cn", False),
    }
    calls = []

    def fetch(path: str):
        calls.append(path)
        return {
            "generated_at": "2026-10-08T11:00:00+08:00",
            "errors": ["old source gap"],
            "provenance": {"source": "system"},
            "date": "2026-09-29",
        }

    context = SystemContext(tmp_path, fetch=fetch)
    for section, (path, scope, applied) in expected.items():
        result = context.fundamentals(market="us", section=section)
        assert result["available"]
        assert result["sources"][section]["path"] == path
        assert result["selection"]["effective_market_scope"] == scope
        assert result["selection"]["market_parameter_applied"] is applied
        assert result["data"]["errors"] == ["old source gap"]
        assert result["data"]["date"] == "2026-09-29"
    assert calls == [value[0] for value in expected.values()]
    assert context.fundamentals(section="overview?refresh=true")["available"] is False
    assert context.fundamentals(market="hk")["available"] is False
    with pytest.raises(ValueError):
        context._get("/api/fundamentals/rates?refresh=true")


def test_wrong_json_schema_is_a_per_source_failure(tmp_path: Path) -> None:
    def fetch(path: str):
        if path == "/api/plans":
            return {"plans": []}
        if path == "/api/factors/panel":
            return []
        return _fake(path)

    context = SystemContext(tmp_path, fetch=fetch)
    assert "expected list" in context.plans()["errors"]["plans"]
    overview = context.overview()
    assert "expected object" in overview["errors"]["factors"]
    assert overview["data"]["workspace"]["coverage"]["total"] == 1


def test_packet_fallback_is_visible_and_future_packet_rejected(tmp_path: Path) -> None:
    _packet(tmp_path)
    folder = tmp_path / "data/cache/portfolio-chat-briefing"
    (folder / "packet-99999999-bad.json").write_text("broken", encoding="utf-8")
    result = SystemContext(tmp_path, fetch=_fake).latest_brief()
    assert result["available"]
    assert result["sources"]["briefing_packet"]["fallback"] is True
    assert result["errors"]["briefing_packet_fallback"]
    future = (datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1)).isoformat()
    (folder / "packet-99999998-future.json").write_text(
        json.dumps({"slot": "1135", "generated_at": future})
    )
    (folder / "packet-99999997-oversize.json").write_bytes(b" " * (8 * 1024 * 1024 + 1))
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"slot": "1135", "generated_at": future}))
    (folder / "packet-99999996-escape.json").symlink_to(outside)
    result = SystemContext(tmp_path, fetch=_fake).latest_brief()
    reasons = str(result["errors"]["briefing_packet_fallback"])
    assert "future" in reasons and "too large" in reasons and "escapes cache" in reasons


def test_unavailable_packet_source_retains_old_data_with_error(tmp_path: Path) -> None:
    _packet(tmp_path)
    path = next((tmp_path / "data/cache/portfolio-chat-briefing").glob("packet-*.json"))
    packet = json.loads(path.read_text())
    packet["trade_ledger"]["available"] = False
    packet["source_status"]["trades"] = {"ok": False, "error": "database offline"}
    packet["source_status"]["news"] = {"ok": False, "error": "collector offline"}
    packet["source_status"]["user_context"] = {"ok": False, "error": "context file offline"}
    path.write_text(json.dumps(packet))
    context = SystemContext(tmp_path, fetch=_fake)
    trades = context.trades()
    assert trades["available"] is False
    assert trades["data"]["packet_generated_at"] == "2026-10-08T11:39:00+08:00"
    assert trades["errors"]["trades"] == "database offline"
    assert context.news()["available"] is False
    assert context.latest_brief()["available"] is False
    portfolio = context.portfolio("013403")
    assert portfolio["data"]["user_stated_context"]
    assert portfolio["errors"]["user_context"] == "context file offline"


def _report_fixture(
    root: Path, *, content: str = "# 已登记报告\n\n## 一句话结论（大白话）\n无交易依据。"
):
    path = root / "docs/experiments/registered-2026-10-08.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    name = path.relative_to(root).as_posix()
    registry = {
        "entries": {
            name: {
                "category": "方法论与验证",
                "verdict": "mixed",
                "report_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        }
    }
    (root / "docs/experiments/registry.json").write_text(json.dumps(registry), encoding="utf-8")
    return name, path


def test_report_requires_index_registry_and_raw_byte_hash(tmp_path: Path) -> None:
    name, path = _report_fixture(tmp_path)

    def fetch(route: str):
        assert route == "/api/experiments"
        return {
            "items": [
                {
                    "name": name,
                    "title": "已登记报告",
                    "date": "2026-10-08",
                    "pending": False,
                    "verdict": "passed",
                    "category": "数据与质量",
                    "oneLiner": "无交易依据",
                },
                {"name": "docs/experiments/pending.md", "pending": True},
            ]
        }

    context = SystemContext(tmp_path, fetch=fetch)
    good = context.research_report(name, max_chars=9)
    assert good["data"]["registry_sha256_verified"] is True
    assert good["data"]["truncated"] is True
    assert good["data"]["verdict"] == "mixed"
    assert good["data"]["category"] == "方法论与验证"
    assert "differs from registry" in str(good["limitations"])
    assert context.research_report("docs/experiments/pending.md")["available"] is False
    assert context.research_report("../../secret")["available"] is False
    path.write_text("tampered", encoding="utf-8")
    assert "SHA-256" in context.research_report(name)["errors"]["report"]
    assert context.research_search("x" * 201)["available"] is False


def test_report_rejects_symlink_escape(tmp_path: Path) -> None:
    name, _ = _report_fixture(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "docs/experiments/escape-2026-10-08.md"
    link.symlink_to(outside)
    registry_path = tmp_path / "docs/experiments/registry.json"
    registry = json.loads(registry_path.read_text())
    registry["entries"]["docs/experiments/escape-2026-10-08.md"] = {
        "report_sha256": hashlib.sha256(outside.read_bytes()).hexdigest()
    }
    registry_path.write_text(json.dumps(registry))
    context = SystemContext(
        tmp_path,
        fetch=lambda _: {
            "items": [
                {"name": name, "pending": False},
                {"name": "docs/experiments/escape-2026-10-08.md", "pending": False},
            ]
        },
    )
    assert context.research_report("docs/experiments/escape-2026-10-08.md")["available"] is False


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/factors/panel":
            self.send_response(302)
            self.send_header("Location", "http://example.com/private")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b" " * (_MAX_HTTP_BYTES + 1))

    def log_message(self, *args) -> None:  # noqa: ANN002
        pass


def test_redirect_and_oversize_are_rejected(tmp_path: Path) -> None:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        context = SystemContext(tmp_path, f"http://127.0.0.1:{server.server_port}")
        with pytest.raises(ValueError):
            context._get("/api/factors/panel")
        with pytest.raises(ValueError, match="too large"):
            context._get("/api/plans")
    finally:
        server.shutdown()
        worker.join(timeout=2)


def test_blogger_window_new_packet_and_legacy_are_not_confused(tmp_path: Path) -> None:
    _packet(tmp_path)
    path = next((tmp_path / "data/cache/portfolio-chat-briefing").glob("packet-*.json"))
    context = SystemContext(tmp_path, fetch=_fake)
    assert context.news()["data"]["blogger_window"]["status"] == "legacy_packet"
    assert context.news()["data"]["blogger_previous_trading_day"] == []
    packet = json.loads(path.read_text())
    packet["blogger_previous_trading_day"] = [{"title": "previous session", "symbols": ["013403"]}]
    packet["blogger_window"] = {"status": "verified", "date": "2026-09-30"}
    path.write_text(json.dumps(packet))
    result = context.news("013403")["data"]
    assert result["blogger_previous_trading_day"][0]["title"] == "previous session"
    assert result["blogger_window"]["date"] == "2026-09-30"
    assert context.latest_brief("1135")["data"]["blogger_previous_trading_day_count"] == 1
