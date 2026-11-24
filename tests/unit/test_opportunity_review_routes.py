"""Shared brief reads a selected saved review without starting new model work."""

import sqlite3
from copy import deepcopy

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from lei_signal.api.routes import opportunity_reviews as route

RUN = "orb_" + "a" * 64


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(route.router)
    board = {
        "run_id": RUN,
        "status": "partial",
        "items": [
            {
                "card": {
                    "subject": {
                        "key": "symbol:515880.SS",
                        "kind": "symbol",
                        "id": "515880.SS",
                        "name": "通信ETF",
                    }
                }
            },
            {
                "card": {
                    "subject": {
                        "key": "holding:5045587e5cff",
                        "kind": "holding",
                        "id": "5045587e5cff",
                        "name": "易方达信息产业混合A",
                    }
                }
            },
        ],
    }
    monkeypatch.setattr(route, "run", lambda *a: deepcopy(board))
    from lei_signal.api import opportunity_brief

    monkeypatch.setattr(
        opportunity_brief,
        "build_product_brief",
        lambda board, key, **data: {"run_id": board["run_id"], "key": key, **data},
    )
    return TestClient(app)


def test_symbol_brief_reads_one_exact_snapshot_and_no_fund_market(client, monkeypatch):
    calls = []
    def cached_snapshot(req, symbol, *, cached_only):
        assert cached_only is True
        calls.append(symbol)
        return {"snapshot_id": "same"}

    monkeypatch.setattr(route, "_technical_snapshot", cached_snapshot)
    monkeypatch.setattr(route, "holding_market", lambda *a: pytest.fail("foreign fund lookup"))
    value = client.get(
        f"/api/opportunity-reviews/runs/{RUN}/brief", params={"subject_key": "symbol:515880.SS"}
    )
    assert value.status_code == 200
    assert value.json()["technical"]["snapshot_id"] == "same"
    assert calls == ["515880.SS"]


def test_fund_brief_never_substitutes_industry_etf_for_own_signals(client, monkeypatch):
    monkeypatch.setattr(route, "technical_signals", lambda *a: pytest.fail("industry substitution"))
    monkeypatch.setattr(
        route, "holding_market", lambda req, identity: {"subject_key": "holding:" + identity}
    )
    value = client.get(
        f"/api/opportunity-reviews/runs/{RUN}/brief", params={"subject_key": "holding:5045587e5cff"}
    ).json()
    assert value["technical"] is None
    assert value["market"]["subject_key"] == "holding:5045587e5cff"


def test_technical_failure_keeps_selected_review_and_error(client, monkeypatch):
    def fail(*args, cached_only):
        assert cached_only is True
        raise HTTPException(503, "技术资料未取得")

    monkeypatch.setattr(route, "_technical_snapshot", fail)
    value = client.get(
        f"/api/opportunity-reviews/runs/{RUN}/brief", params={"subject_key": "symbol:515880.SS"}
    )
    assert value.status_code == 200
    assert value.json()["errors"] == {"technical": "技术资料未取得"}


@pytest.mark.parametrize("key,status", [("symbol:UNKNOWN", 404), ("holding:../x", 422)])
def test_unknown_or_invalid_selection_does_not_query_prices(client, monkeypatch, key, status):
    monkeypatch.setattr(route, "technical_signals", lambda *a: pytest.fail("unexpected lookup"))
    value = client.get(f"/api/opportunity-reviews/runs/{RUN}/brief", params={"subject_key": key})
    assert value.status_code == status


def test_model_start_failure_is_visible_in_preparation_and_run(tmp_path, monkeypatch):
    """A completed preparation cannot hide a later exception starting its review."""
    from types import SimpleNamespace

    from lei_signal.api import opportunity_context, opportunity_evidence, opportunity_macro

    app = FastAPI()
    app.state.analysis_service = SimpleNamespace()
    app.state.plans_db_path = str(tmp_path / "review.sqlite")
    request = SimpleNamespace(app=app)
    lock, registry = route._registry(request)
    registry["prep"] = {
        "id": "prep",
        "status": "running",
        "run_id": None,
        "error": None,
        "started": route.time.monotonic(),
        "active_worker": True,
    }
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: {"items": []})
    monkeypatch.setattr(opportunity_context, "macro_markets", lambda _: [])
    monkeypatch.setattr(opportunity_context, "prepare_context", lambda *a, **kw: None)
    monkeypatch.setattr(opportunity_macro, "prepare_macro", lambda *a: None)
    monkeypatch.setattr(route.review, "ensure_board", lambda *a, **kw: ({"run_id": RUN}, True))
    monkeypatch.setattr(route, "connect", sqlite3.connect)
    monkeypatch.setattr(route.review, "get_run", lambda *a: {"run_id": RUN, "status": "pending"})
    selected = []
    monkeypatch.setattr(route, "_select_current", lambda db, run_id: selected.append(run_id))

    def fail(*a):
        raise RuntimeError("fixture model start failure")

    monkeypatch.setattr(route.review, "process_run", fail)
    route._prepare(request, "prep", [], app.state.plans_db_path)
    prep = route._preparation(request, "prep")
    assert prep["status"] == "complete"
    assert prep["error_phase"] == "review"
    assert prep["error_code"] == "RuntimeError"
    assert prep["review_error"] == route.run(request, RUN)["review_error"]
    assert registry["prep"]["active_worker"] is False
    assert selected == [RUN]


def test_successful_preparation_selects_returned_run_after_review(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from lei_signal.api import opportunity_context, opportunity_evidence, opportunity_macro

    app = FastAPI()
    app.state.analysis_service = SimpleNamespace()
    app.state.plans_db_path = str(tmp_path / "review.sqlite")
    request = SimpleNamespace(app=app)
    lock, registry = route._registry(request)
    registry["prep"] = {
        "id": "prep", "status": "running", "run_id": None, "error": None,
        "started": route.time.monotonic(), "active_worker": True,
    }
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: {"items": []})
    monkeypatch.setattr(opportunity_context, "macro_markets", lambda _: [])
    monkeypatch.setattr(opportunity_context, "prepare_context", lambda *a, **kw: None)
    monkeypatch.setattr(opportunity_macro, "prepare_macro", lambda *a: None)
    monkeypatch.setattr(route.review, "ensure_board", lambda *a, **kw: ({"run_id": RUN}, True))
    monkeypatch.setattr(route, "connect", sqlite3.connect)
    calls = []
    monkeypatch.setattr(route.review, "process_run", lambda *a: calls.append("review"))
    monkeypatch.setattr(
        route, "_select_current", lambda db, run_id: calls.append(("select", run_id))
    )

    route._prepare(request, "prep", [], app.state.plans_db_path)
    assert route._preparation(request, "prep")["status"] == "complete"
    assert calls == ["review", ("select", RUN)]
    assert registry["prep"]["active_worker"] is False


def test_interrupted_preparation_does_not_change_current_run(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from lei_signal.api import opportunity_context, opportunity_evidence, opportunity_macro

    app = FastAPI()
    app.state.analysis_service = SimpleNamespace()
    app.state.plans_db_path = str(tmp_path / "review.sqlite")
    request = SimpleNamespace(app=app)
    _, registry = route._registry(request)
    registry["prep"] = {
        "id": "prep", "status": "running", "run_id": None, "error": None,
        "started": route.time.monotonic(), "active_worker": True,
    }
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: {"items": []})
    monkeypatch.setattr(opportunity_context, "macro_markets", lambda _: [])
    monkeypatch.setattr(opportunity_macro, "prepare_macro", lambda *a: None)
    monkeypatch.setattr(
        opportunity_context, "prepare_context",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("fixture interrupted")),
    )
    monkeypatch.setattr(route, "_select_current", lambda *a: pytest.fail("must not select"))

    route._prepare(request, "prep", [], app.state.plans_db_path)
    assert route._preparation(request, "prep")["status"] == "failed"


def test_market_watch_read_is_offline_and_explicit_refresh_only_updates_news(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from lei_signal.api import (
        opportunity_market_watch,
        opportunity_news,
        opportunity_summary_context,
    )

    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "lab.db")
    request = SimpleNamespace(app=app)
    board = {"run_id": RUN, "items": []}
    monkeypatch.setattr(route, "_saved_summary_board", lambda *a: board)
    monkeypatch.setattr(
        opportunity_market_watch, "build_market_watch", lambda **kw: {"limitations": []}
    )
    monkeypatch.setattr(
        opportunity_news, "read_news", lambda *a: {"events": [], "coverage": {"status": "partial"}}
    )
    monkeypatch.setattr(
        opportunity_summary_context,
        "recent_news_watch",
        lambda *a, **kw: {"news_update": kw["automated"]["coverage"], "news_limitations": []},
    )
    calls = []
    monkeypatch.setattr(
        opportunity_news,
        "refresh_news",
        lambda *a, **kw: calls.append(kw) or {"refresh": {"status": "fresh"}},
    )
    monkeypatch.setattr(
        route.review, "process_run", lambda *a, **kw: pytest.fail("must not rerun agents")
    )
    assert route.market_watch(request, RUN)["news_update"]["status"] == "partial"
    assert calls == []
    assert route.refresh_market_news(request, RUN)["news_update"]["refresh"]["status"] == "fresh"
    assert calls == [{"force": True}]


def test_recent_links_are_local_read_only_and_fail_without_losing_events(monkeypatch):
    from types import SimpleNamespace

    from lei_signal.api import opportunity_connections, portfolio_workspace

    request = SimpleNamespace(app=FastAPI())
    board = {"run_id": RUN, "status": "complete", "items": []}
    monkeypatch.setattr(route, "_saved_summary_board", lambda *a: board)
    monkeypatch.setattr(
        portfolio_workspace, "build_workspace", lambda _: {"items": [{"name": "local-only"}]}
    )
    seen = []
    def connections(recent, items, *, as_of):
        seen.extend(items)
        return {"symbol": [{"fund_name": "local-only"}]}
    monkeypatch.setattr(opportunity_connections, "build_opportunity_connections", connections)
    value = route.recent(request, RUN)
    assert value["connections_status"] == "available"
    assert seen == [{"name": "local-only"}]
    assert value["related_holdings"]["symbol"][0]["fund_name"] == "local-only"
    def unavailable(_):
        raise HTTPException(503, "fixture unavailable")
    monkeypatch.setattr(portfolio_workspace, "build_workspace", unavailable)
    failed = route.recent(request, RUN)
    assert failed["run_id"] == RUN
    assert failed["items"] == value["items"]
    assert failed["connections_status"] == "unavailable"
    assert failed["related_holdings"] == {}
