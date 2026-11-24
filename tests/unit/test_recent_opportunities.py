"""The home list must never promote old, provisional, or proxy events."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from lei_signal.api import recent_opportunities as recent
from lei_signal.api.routes import opportunity_reviews as route
from lei_signal.copilot import opportunity_review


def subject(key: str, symbol: str, *, kind: str = "symbol") -> dict:
    return {
        "card": {
            "subject": {
                "key": key,
                "kind": kind,
                "id": symbol if kind == "symbol" else "holding-id",
                "symbol": symbol,
                "name": "中文产品名",
            }
        }
    }


def signal(
    identity: str,
    *,
    side: str = "buy",
    status: str = "new",
    event: str | None = "2026-10-16",
    age: int | None = 0,
    recent_flag: bool = True,
    provenance: str = "lei_explicit",
) -> dict:
    return {
        "id": identity,
        "side": side,
        "title": "阶段与路牌",
        "summary": "收盘出现结构变化",
        "status": status,
        "event_date": event,
        "age_bars": age,
        "is_recent": recent_flag,
        "provenance": provenance,
    }


def snapshot(
    *signals: dict, bar: str = "2026-10-16", freshness: str = "current", bar_status: str = "closed"
) -> dict:
    return {
        "display_name": "中文产品名",
        "meta": {
            "last_bar_date": bar,
            "freshness": freshness,
            "bar_status": bar_status,
            "is_intraday_forming": bar_status == "intraday",
        },
        "signals": list(signals),
    }


def test_buy_sell_and_waiting_are_separate_and_same_product_is_read_once():
    board = {
        "run_id": "orb_saved",
        "checked_at": "2026-10-16T16:00:00+08:00",
        "status": "partial",
        "items": [
            subject("symbol:510300.SS", "510300.SS"),
            subject("holding:owned", "510300.SS", kind="holding"),
        ],
    }
    calls = []

    def cached(symbol):
        calls.append(symbol)
        return snapshot(
            signal("buy-1"),
            signal("sell-1", side="sell", age=1),
            signal("waiting-1", status="waiting"),
        )

    result = recent.build_recent_opportunities(board, cached)
    assert calls == ["510300.SS"]
    assert [(row["side"], row["subject_key"]) for row in result["items"]] == [
        ("buy", "holding:owned"),
        ("sell", "holding:owned"),
    ]
    assert [row["id"] for row in result["waiting"]] == ["waiting-1"]
    assert result["review_incomplete"] is True


def test_cleared_old_future_unknown_and_proxy_never_become_current():
    board = {"status": "complete", "items": [subject("symbol:510300.SS", "510300.SS")]}
    rows = [
        signal("cleared", status="cleared"),
        signal("old", age=3, recent_flag=False),
        signal("future", event="2026-10-19"),
        signal("unknown", event=None),
        signal("proxy", provenance="research_proxy"),
        signal("unknown-source", provenance="system"),
        signal("valid", side="sell"),
    ]
    result = recent.build_recent_opportunities(board, lambda _: snapshot(*rows))
    assert [row["id"] for row in result["items"]] == ["valid"]
    assert result["waiting"] == []
    assert result["cleared"] == []


def test_recent_clearance_uses_changed_date_and_keeps_close_boundary():
    board = {"status": "complete", "items": [subject("symbol:510300.SS", "510300.SS")]}
    cleared = signal("old-event", status="cleared", event="2026-10-01", age=10,
                     recent_flag=False)
    cleared.update(state_changed_date="2026-10-16", state_age_bars=0,
                   next_step_cn="留作历史", invalidation_cn="新高解除")
    closed = recent.build_recent_opportunities(board, lambda _: snapshot(cleared))
    assert closed["items"] == closed["waiting"] == []
    assert [(row["id"], row["status"], row["state_changed_date"], row["invalidation_cn"])
            for row in closed["cleared"]] == [("old-event", "cleared", "2026-10-16", "新高解除")]
    forming = recent.build_recent_opportunities(
        board, lambda _: snapshot(cleared, bar_status="intraday")
    )
    assert forming["cleared"][0]["status"] == "waiting_close"


def test_clearance_rejects_old_future_proxy_or_missing_changed_state():
    board = {"status": "complete", "items": [subject("symbol:510300.SS", "510300.SS")]}
    rows = []
    for identity, changed, state_age, provenance in [
        ("old", "2026-10-13", 3, "lei_explicit"),
        ("future", "2026-10-19", 0, "lei_explicit"),
        ("missing", None, 0, "lei_explicit"),
        ("proxy", "2026-10-16", 0, "research_proxy"),
    ]:
        item = signal(identity, status="cleared", event="2026-10-01", recent_flag=False)
        item.update(state_changed_date=changed, state_age_bars=state_age,
                    provenance=provenance)
        rows.append(item)
    result = recent.build_recent_opportunities(board, lambda _: snapshot(*rows))
    assert result["cleared"] == []


@pytest.mark.parametrize("provenance", ["lei_explicit", "lei_inferred", "existing_backtest"])
def test_existing_lei_sources_keep_their_original_provenance(provenance):
    board = {"status": "complete", "items": [subject("symbol:510300.SS", "510300.SS")]}
    result = recent.build_recent_opportunities(
        board, lambda _: snapshot(signal("known", provenance=provenance))
    )
    assert [(row["id"], row["provenance"]) for row in result["items"]] == [("known", provenance)]


def test_saved_communication_top_warning_is_recent_risk_not_a_sell_instruction():
    # Small exact-field regression from .codex/decision-chain-20261018/communication-technical.json.
    technical = {
        "symbol": "515880.SS",
        "display_name": "通信ETF",
        "meta": {
            "last_bar_date": "2026-10-16",
            "bar_status": "closed",
            "is_intraday_forming": False,
            "freshness": "current",
        },
        "signals": [
            {
                "id": "sell:top:structure_top_structure:9b36df8398908f9fefaf1cc2",
                "side": "sell",
                "title": "顶部构造预警",
                "summary": (
                    "顶部警报确认：第二高点低于第一高点(0.8280)，收盘跌破颈线0.5420。"
                    "仅为风险提示，不构成卖出指令。"
                ),
                "status": "active",
                "event_date": "2026-10-15",
                "age_bars": 1,
                "is_recent": True,
                "provenance": "existing_backtest",
            }
        ],
    }
    board = {"status": "partial", "items": [subject("symbol:515880.SS", "515880.SS")]}
    result = recent.build_recent_opportunities(
        board, lambda symbol: technical if symbol == "515880.SS" else None
    )
    assert len(result["items"]) == 1
    row = result["items"][0]
    assert (row["symbol"], row["side"], row["event_date"], row["bar_date"]) == (
        "515880.SS",
        "sell",
        "2026-10-15",
        "2026-10-16",
    )
    assert row["provenance"] == "existing_backtest"
    assert "风险提示，不构成卖出指令" in row["summary"]


def test_stale_unknown_and_missing_cache_are_not_latest_confirmations():
    board = {
        "status": "complete",
        "items": [
            subject("symbol:510300.SS", "510300.SS"),
            subject("symbol:159915.SZ", "159915.SZ"),
        ],
    }
    result = recent.build_recent_opportunities(
        board,
        lambda symbol: (
            snapshot(signal("old-bar"), freshness="stale") if symbol == "510300.SS" else None
        ),
    )
    assert result["items"] == result["waiting"] == []
    assert result["cached_subjects"] == result["missing_cached_subjects"] == 1
    assert result["unverified_cached_subjects"] == 1


def test_intraday_signal_is_waiting_for_close():
    board = {"status": "complete", "items": [subject("symbol:510300.SS", "510300.SS")]}
    result = recent.build_recent_opportunities(
        board, lambda _: snapshot(signal("forming"), bar_status="intraday")
    )
    assert result["items"] == []
    assert result["waiting"][0]["status"] == "waiting_close"


def test_no_saved_run_is_honest_empty_state_and_no_cache_read():
    result = recent.build_recent_opportunities(None, lambda _: 1 / 0)
    assert result["review_status"] == "missing"
    assert result["items"] == result["waiting"] == []


def test_latest_run_reader_does_not_create_missing_database_or_modify_existing(tmp_path):
    path = tmp_path / "saved.sqlite"
    assert recent.latest_saved_run(str(path)) is None
    assert not path.exists()
    with sqlite3.connect(path) as conn:
        opportunity_review.ensure_schema(conn)
        conn.execute(
            "INSERT INTO opportunity_review_runs VALUES (?,?,?,?,?,?,?)",
            (
                "orb_saved",
                "key",
                "2026-10-16",
                "2026-10-16T16:00:00+08:00",
                "{}",
                "[]",
                json.dumps([]),
            ),
        )
    before = path.read_bytes()
    assert recent.latest_saved_run(str(path))["run_id"] == "orb_saved"
    assert path.read_bytes() == before


def test_current_run_pointer_survives_reopen_without_rewriting_run_dates(tmp_path):
    path = tmp_path / "saved.sqlite"
    older, newer = "orb_" + "a" * 64, "orb_" + "b" * 64
    with sqlite3.connect(path) as conn:
        opportunity_review.ensure_schema(conn)
        for run_id, checked_at in [
            (older, "2026-10-19T00:19:00+08:00"),
            (newer, "2026-10-19T00:25:00+08:00"),
        ]:
            conn.execute(
                "INSERT INTO opportunity_review_runs VALUES (?,?,?,?,?,?,?)",
                (run_id, run_id, "2026-10-19", checked_at, "{}", "[]", "[]"),
            )
    assert recent.latest_saved_run(str(path))["run_id"] == newer
    with sqlite3.connect(path) as conn:
        opportunity_review.select_current_run(conn, older)
        dates = conn.execute(
            "SELECT checked_at FROM opportunity_review_runs ORDER BY checked_at"
        ).fetchall()
    before_read = path.read_bytes()
    assert recent.latest_saved_run(str(path))["run_id"] == older
    assert path.read_bytes() == before_read
    assert [row[0] for row in dates] == [
        "2026-10-19T00:19:00+08:00", "2026-10-19T00:25:00+08:00"
    ]


def test_legacy_run_reader_and_unknown_pointer_fall_back_to_latest(tmp_path):
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE opportunity_review_runs (run_id TEXT PRIMARY KEY, board_key TEXT, "
            "as_of TEXT, checked_at TEXT, coverage_json TEXT, limitations_json TEXT, "
            "review_ids_json TEXT)"
        )
        conn.execute(
            "INSERT INTO opportunity_review_runs VALUES (?,?,?,?,?,?,?)",
            ("orb_legacy", "legacy", "2026-10-19", "2026-10-19T00:25:00+08:00", "{}", "[]", "[]"),
        )
    before = path.read_bytes()
    assert recent.latest_saved_run(str(path))["run_id"] == "orb_legacy"
    assert path.read_bytes() == before
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE opportunity_review_current(slot TEXT PRIMARY KEY, run_id TEXT)")
        conn.execute("INSERT INTO opportunity_review_current VALUES ('current','orb_missing')")
    assert recent.latest_saved_run(str(path))["run_id"] == "orb_legacy"


def test_recent_route_only_uses_cached_snapshot(monkeypatch):
    app = FastAPI()
    app.include_router(route.router)
    monkeypatch.setattr(
        recent,
        "latest_saved_run",
        lambda _: {
            "run_id": "orb_saved",
            "status": "partial",
            "items": [subject("symbol:510300.SS", "510300.SS")],
        },
    )

    def cached(req, symbol, *, cached_only, include_chart):
        assert symbol == "510300.SS" and cached_only is True and include_chart is False
        return snapshot(signal("confirmed"))

    monkeypatch.setattr(route, "_technical_snapshot", cached)
    value = TestClient(app).get("/api/opportunity-reviews/recent")
    assert value.status_code == 200
    assert value.json()["items"][0]["id"] == "confirmed"


def test_recent_route_binds_selected_run_and_never_falls_back(monkeypatch, tmp_path):
    app = FastAPI()
    app.include_router(route.router)
    path = tmp_path / "saved.sqlite"
    app.state.plans_db_path = str(path)
    selected = "orb_" + "a" * 64
    newer = "orb_" + "b" * 64
    with sqlite3.connect(path) as conn:
        opportunity_review.ensure_schema(conn)
        for run_id, checked_at in [(selected, "2026-10-19T00:19:00+08:00"),
                                   (newer, "2026-10-19T00:20:00+08:00")]:
            conn.execute("INSERT INTO opportunity_review_runs VALUES (?,?,?,?,?,?,?)",
                         (run_id, run_id, "2026-10-19", checked_at, "{}", "[]", "[]"))
    monkeypatch.setattr(route, "_technical_snapshot", lambda *args, **kwargs: 1 / 0)
    before = path.read_bytes()
    client = TestClient(app)
    assert client.get("/api/opportunity-reviews/recent").json()["run_id"] == newer
    result = client.get("/api/opportunity-reviews/recent", params={"run_id": selected})
    assert result.status_code == 200 and result.json()["run_id"] == selected
    assert client.get(
        "/api/opportunity-reviews/recent", params={"run_id": "orb_bad"}
    ).status_code == 422
    assert client.get(
        "/api/opportunity-reviews/recent", params={"run_id": "orb_" + "c" * 64}
    ).status_code == 404
    assert path.read_bytes() == before
    app.state.plans_db_path = str(tmp_path / "absent.sqlite")
    assert client.get(
        "/api/opportunity-reviews/recent", params={"run_id": selected}
    ).status_code == 404
    assert not (tmp_path / "absent.sqlite").exists()


def test_compact_snapshot_skips_full_chart_serialization(monkeypatch):
    from lei_signal.api import opportunity_signals
    from lei_signal.api.routes import opportunities, symbols
    from lei_signal.ui import echarts_kline

    day = pd.Timestamp("2026-10-16")
    result = SimpleNamespace(
        symbol="510300.SS",
        display_name="沪深300ETF",
        frame=pd.DataFrame({"close": [1.0]}, index=pd.DatetimeIndex([day])),
        price_data=SimpleNamespace(
            report=SimpleNamespace(last_date=day, provider="test", adjusted=True),
            info=SimpleNamespace(timezone="Asia/Shanghai"),
        ),
        cache_fallback_used=False,
        weekly_trend=pd.DataFrame(),
    )
    fetched = datetime(2026, 10, 16, 8, 0, tzinfo=UTC)
    app = FastAPI()
    app.state.analysis_service = SimpleNamespace(
        _entries={"510300.SS": SimpleNamespace(result=result, error=None, fetched_at=fetched)}
    )
    request = Request({"type": "http", "app": app})
    monkeypatch.setattr(
        symbols,
        "_assessment_dto",
        lambda _: SimpleNamespace(
            as_of="2026-10-16", color="green", color_cn="绿色", stage_cn="上涨"
        ),
    )
    monkeypatch.setattr(
        opportunities, "build_review", lambda *args, **kwargs: SimpleNamespace(degraded_cn=None)
    )
    monkeypatch.setattr(opportunity_signals, "build_signal_rows", lambda *args: [signal("saved")])
    monkeypatch.setattr(route, "_technical_freshness", lambda **kwargs: ("current", "已核对"))
    monkeypatch.setattr(echarts_kline, "serialize_result", lambda *args, **kwargs: 1 / 0)
    compact = route._technical_snapshot(request, "510300.SS", cached_only=True, include_chart=False)
    assert compact["signals"][0]["id"] == "saved"
    assert compact["chart"] is None
