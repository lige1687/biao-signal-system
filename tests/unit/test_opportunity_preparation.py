"""Bounded preparation of exact opportunity symbols; no real feeds or model."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from threading import Event, Thread
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import opportunity_reviews as route


@pytest.fixture(autouse=True)
def isolated_news(monkeypatch):
    from lei_signal.api import opportunity_context

    monkeypatch.setattr(
        opportunity_context,
        "_query",
        lambda subject, today, *, risk=False: (
            subject,
            {
                "checked_on": today.isoformat(),
                "checked_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                "status": "checked",
                "query": "risk-fixture" if risk else "general-fixture",
                "count": 0,
                "leads": [],
            },
        ),
    )


def _snapshot(*, ready=False):
    return {
        "as_of": "2026-10-15",
        "checked_at": "2026-10-15T14:30:00+08:00",
        "coverage": {"watchlist": 1, "holdings": 1, "review_candidates": int(ready)},
        "limitations": [],
        "items": [
            {
                "candidate_key": "symbol:512890.SS:buy",
                "subject": {
                    "key": "symbol:512890.SS",
                    "kind": "symbol",
                    "id": "512890.SS",
                    "name": "红利低波ETF",
                },
                "intent": "buy",
                "status": "candidate" if ready else "unknown",
                "headline": "待核",
                "agent_eligible": ready,
                "data_as_of": "2026-10-15" if ready else None,
                "evidence": [{"id": "ev1", "role": "unknown", "text": "待核", "source": "系统"}],
                "searches": [],
                "limitations": [],
            }
        ],
    }


class Service:
    def __init__(self, fail=False):
        self._entries = {}
        self.calls = []
        self.fail = fail

    def get_many(self, symbols, *, refresh=False, background=False):
        self.calls.append((symbols, refresh, background))
        if self.fail:
            raise RuntimeError("synthetic failure")
        self._entries.update({symbol: SimpleNamespace(result=object()) for symbol in symbols})
        return {}


def _app(tmp_path, service=None):
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "reviews.sqlite")
    if service is not None:
        app.state.analysis_service = service
    app.include_router(route.router)
    return app


def test_exact_target_set_uses_only_board_and_existing_holding_bindings(monkeypatch):
    from lei_signal.api import portfolio_workspace

    monkeypatch.setattr(
        portfolio_workspace,
        "build_workspace",
        lambda _: {
            "items": [
                {
                    "symbol": "512890.SS",
                    "industry_reference": {
                        "references": [
                            {"symbol": "515880.SS"},
                            {"symbol": "515880.SS"},
                        ]
                    },
                },
                {"symbol": None, "code": "001513", "industry_reference": {"references": []}},
            ]
        },
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    assert route._targets(request, _snapshot()) == ["512890.SS", "515880.SS"]


def test_cold_cache_prepares_new_run_and_reuses_single_flight(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_evidence

    service = Service()
    app = _app(tmp_path, service)
    monkeypatch.setattr(
        opportunity_evidence, "build_snapshot", lambda _: _snapshot(ready=bool(service._entries))
    )
    monkeypatch.setattr(route, "_targets", lambda *_: ["512890.SS"])
    monkeypatch.setattr(
        route, "_needs_fetch", lambda request, symbol, now: (symbol not in service._entries, False)
    )
    processed = []
    original_process = route.review.process_run

    def process(db, rid):
        processed.append(rid)
        original_process(
            db,
            rid,
            model=lambda ids, _: json.dumps(
                {
                    "reviews": [
                        {
                            "review_id": item,
                            "support_ids": [],
                            "opposition_ids": [],
                            "unknown_ids": ["ev1"],
                            "condition_ids": [],
                            "lead_ids": [],
                        }
                        for item in ids
                    ]
                }
            ),
        )

    monkeypatch.setattr(route.review, "process_run", process)
    with TestClient(app) as client:
        first = client.post("/api/opportunity-reviews/ensure").json()
        assert first["preparation_id"].startswith("opr_")
        prepared = client.get(
            "/api/opportunity-reviews/preparations/" + first["preparation_id"]
        ).json()
        assert prepared == {
            "id": first["preparation_id"],
            "status": "complete",
            "run_id": prepared["run_id"],
            "error": None,
        }
        assert prepared["run_id"] != first["run_id"]
        assert client.get("/api/opportunity-reviews/runs/" + prepared["run_id"]).status_code == 200
        second = client.post("/api/opportunity-reviews/ensure").json()
        assert second["run_id"] == prepared["run_id"]
        assert "preparation_id" not in second
    assert service.calls == [(["512890.SS"], False, False)]
    assert processed == [prepared["run_id"]]


def test_running_preparation_reused_and_timeout_fails(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_evidence

    app = _app(tmp_path, Service())
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: _snapshot())
    monkeypatch.setattr(route, "_targets", lambda *_: ["512890.SS"])
    monkeypatch.setattr(route, "_needs_fetch", lambda *_: (True, False))
    monkeypatch.setattr(route, "_prepare", lambda *_: None)
    with TestClient(app) as client:
        first = client.post("/api/opportunity-reviews/ensure").json()
        second = client.post("/api/opportunity-reviews/ensure").json()
        assert first["preparation_id"] == second["preparation_id"]
        explicit = client.post(
            "/api/opportunity-reviews/ensure", json={"retry_failed": True}
        ).json()
        assert explicit["preparation_id"] == first["preparation_id"]
        lock, registry = app.state.opportunity_preparations
        with lock:
            assert registry[first["preparation_id"]]["retry_requested"] is True
            registry[first["preparation_id"]]["started"] -= route._PREPARATION_TIMEOUT + 1
        timed = client.get(
            "/api/opportunity-reviews/preparations/" + first["preparation_id"]
        ).json()
        assert timed["status"] == "failed" and "超时" in timed["error"]
        with lock:
            registry[first["preparation_id"]]["finished"] -= 61
        still_active = client.post("/api/opportunity-reviews/ensure").json()
        assert still_active["preparation_id"] == first["preparation_id"]


def test_only_forming_or_fallback_does_not_trigger_intraday_refresh(monkeypatch):
    from lei_signal.api import opportunity_evidence

    entry = SimpleNamespace(result=object(), error=None)
    service = SimpleNamespace(_entries={"512890.SS": entry}, _is_fresh=lambda *_: True)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(analysis_service=service)))
    now = datetime(2026, 10, 15, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    monkeypatch.setattr(
        opportunity_evidence,
        "_technical",
        lambda *_: (
            entry.result,
            object(),
            [
                opportunity_evidence._INTRADAY_GAP,
                "技术资料使用旧缓存",
            ],
        ),
    )
    assert route._needs_fetch(request, "512890.SS", now) == (False, False)
    monkeypatch.setattr(
        opportunity_evidence,
        "_technical",
        lambda *_: (
            entry.result,
            object(),
            [
                "技术行情日期过旧、未来或无法核实",
            ],
        ),
    )
    assert route._needs_fetch(request, "512890.SS", now) == (True, True)
    monkeypatch.setattr(
        opportunity_evidence,
        "_technical",
        lambda *_: (
            entry.result,
            object(),
            [
                opportunity_evidence._INTRADAY_GAP,
            ],
        ),
    )
    service._is_fresh = lambda *_: False
    assert route._needs_fetch(request, "512890.SS", now) == (True, False)


def test_completed_preparation_cooldown_keeps_new_board(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_evidence

    service = Service()
    app = _app(tmp_path, service)
    current = {"text": "旧材料"}

    def snapshot(_):
        board = _snapshot()
        board["items"][0]["evidence"][0]["text"] = current["text"]
        return board

    monkeypatch.setattr(opportunity_evidence, "build_snapshot", snapshot)
    monkeypatch.setattr(route, "_targets", lambda *_: ["512890.SS"])
    monkeypatch.setattr(route, "_needs_fetch", lambda *_: (True, False))
    monkeypatch.setattr(route.review, "process_run", lambda *_: None)
    with TestClient(app) as client:
        first = client.post("/api/opportunity-reviews/ensure").json()
        prepared = client.get(
            "/api/opportunity-reviews/preparations/" + first["preparation_id"]
        ).json()
        assert prepared["status"] == "complete"
        current["text"] = "新材料"
        second = client.post("/api/opportunity-reviews/ensure").json()
        assert second["run_id"] != first["run_id"]
        assert "preparation_id" not in second
        assert len(service.calls) == 1


def test_failure_cools_down_and_no_service_preserves_old_ensure(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_evidence

    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: _snapshot())
    monkeypatch.setattr(route, "_targets", lambda *_: ["512890.SS"])
    monkeypatch.setattr(route, "_needs_fetch", lambda *_: (True, False))
    service = Service(fail=True)
    with TestClient(_app(tmp_path, service)) as client:
        first = client.post("/api/opportunity-reviews/ensure").json()
        failed = client.get(
            "/api/opportunity-reviews/preparations/" + first["preparation_id"]
        ).json()
        assert failed["status"] == "failed" and failed["run_id"] is None
        again = client.post("/api/opportunity-reviews/ensure").json()
        assert again["preparation_id"] == first["preparation_id"]
        assert len(service.calls) == 1
        service.fail = False
        retried = client.post("/api/opportunity-reviews/ensure", json={"retry_failed": True}).json()
        assert retried["preparation_id"] != first["preparation_id"]
        recovered = client.get(
            "/api/opportunity-reviews/preparations/" + retried["preparation_id"]
        ).json()
        assert recovered["status"] == "complete"
        assert len(service.calls) == 2
    (tmp_path / "plain").mkdir()
    with TestClient(_app(tmp_path / "plain")) as client:
        board = client.post("/api/opportunity-reviews/ensure").json()
        assert "preparation_id" not in board


def test_retry_arriving_during_board_save_is_not_lost(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_context, opportunity_evidence

    app = _app(tmp_path, Service())
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: _snapshot())
    monkeypatch.setattr(route, "_targets", lambda *_: ["512890.SS"])
    monkeypatch.setattr(route, "_needs_fetch", lambda *_: (True, False))
    prepared_flags = []
    monkeypatch.setattr(
        opportunity_context,
        "prepare_context",
        lambda request, snapshot, *, retry_failed=False: prepared_flags.append(retry_failed),
    )
    original = route.review.ensure_board
    calls = 0

    def save_board(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            lock, registry = app.state.opportunity_preparations
            with lock:
                next(iter(registry.values()))["retry_requested"] = True
        return original(*args, **kwargs)

    monkeypatch.setattr(route.review, "ensure_board", save_board)
    with TestClient(app) as client:
        board = client.post("/api/opportunity-reviews/ensure").json()
        prepared = client.get(
            "/api/opportunity-reviews/preparations/" + board["preparation_id"]
        ).json()
        assert prepared["status"] == "complete"
    assert prepared_flags == [False, True]


@pytest.mark.parametrize("fetch_before_retry", [True, False])
def test_normal_ensure_cannot_claim_retry_preparation_run(
    tmp_path, monkeypatch, fetch_before_retry
):
    from lei_signal.api import opportunity_context, opportunity_evidence, opportunity_macro

    app = _app(tmp_path, Service())
    monkeypatch.setattr(route, "connect", sqlite3.connect)
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda _: _snapshot(ready=True))
    monkeypatch.setattr(route, "_targets", lambda *_: ["512890.SS"])
    fetch_needed = {"value": fetch_before_retry}
    monkeypatch.setattr(route, "_needs_fetch", lambda *_: (fetch_needed["value"], False))
    monkeypatch.setattr(opportunity_context, "prepare_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(opportunity_context, "needs_context", lambda *args, **kwargs: False)
    monkeypatch.setattr(opportunity_macro, "prepare_macro", lambda *args, **kwargs: None)

    db_path = app.state.plans_db_path
    with sqlite3.connect(db_path) as conn:
        initial, _ = route.review.ensure_board(conn, _snapshot(ready=True))
        conn.execute(
            "UPDATE opportunity_review_cards SET status='failed',failure_code='old_failure'"
        )
        conn.commit()

    board_saved = Event()
    allow_review = Event()
    original_ensure = route.review.ensure_board

    def pause_after_retry_save(conn, snapshot, *, retry_failed=False):
        board, work = original_ensure(conn, snapshot, retry_failed=retry_failed)
        if retry_failed:
            board_saved.set()
            assert allow_review.wait(5)
        return board, work

    monkeypatch.setattr(route.review, "ensure_board", pause_after_retry_save)
    calls = []
    original_process = route.review.process_run
    review_started = Event()
    allow_finish = Event()

    def process(db, run_id, *, retry_failed=False):
        calls.append((run_id, retry_failed))
        review_started.set()
        assert allow_finish.wait(5)
        original_process(
            db, run_id, retry_failed=retry_failed,
            model=lambda ids, _: json.dumps({"reviews": [{
                "review_id": rid,
                "support_ids": [], "opposition_ids": [], "unknown_ids": ["ev1"],
                "condition_ids": [], "lead_ids": [],
            } for rid in ids]}),
        )

    monkeypatch.setattr(route.review, "process_run", process)
    replies = []
    with TestClient(app) as client:
        worker = Thread(target=lambda: replies.append(client.post(
            "/api/opportunity-reviews/ensure", json={"retry_failed": True}
        )))
        worker.start()
        try:
            assert board_saved.wait(5)
            # The source is now ready: the ordinary request would bypass preparation.
            fetch_needed["value"] = False
            normal = client.post("/api/opportunity-reviews/ensure").json()
            assert normal["run_id"] == initial["run_id"]
            assert normal["preparation_id"].startswith("opr_")
            assert calls == []
        finally:
            allow_review.set()
            if review_started.wait(5):
                normal_during_review = client.post("/api/opportunity-reviews/ensure").json()
                assert normal_during_review["preparation_id"] == normal["preparation_id"]
                lock, registry = app.state.opportunity_preparations
                with lock:
                    assert registry[normal["preparation_id"]]["active_worker"] is True
                    assert registry[normal["preparation_id"]]["status"] == "running"
                assert calls == [(initial["run_id"], True)]
            allow_finish.set()
            worker.join(5)
        assert not worker.is_alive()
        assert len(replies) == 1 and replies[0].status_code == 200
        prepared = client.get(
            "/api/opportunity-reviews/preparations/" + normal["preparation_id"]
        ).json()
        assert prepared["status"] == "complete"
    assert calls == [(initial["run_id"], True)]
    with sqlite3.connect(db_path) as conn:
        assert route.review.get_run(conn, initial["run_id"])["status"] == "complete"
        assert conn.execute("SELECT count(*) FROM opportunity_review_workers").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM opportunity_review_attempts").fetchone()[0] == 1
