"""/api/signals/day/{date} 路由门禁：快照优先、回放补算、日期校验。"""
from __future__ import annotations

from contextlib import closing
from datetime import date, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import today_date
from lei_signal.api.signal_alerts_store import upsert_signal_alerts
from lei_signal.storage.sqlite_store import connect

PAST = "2026-08-21"  # 周五


def _app(tmp_path):
    app = create_app(analysis_service=SimpleNamespace())
    db = str(tmp_path / "lab.db")
    app.state.plans_db_path = db
    return app, db


def _seed_snapshot(db: str, day: str) -> None:
    with closing(connect(db)) as conn:
        upsert_signal_alerts(conn, day, "close", [])


def test_day_with_snapshot_returns_full(tmp_path) -> None:
    app, db = _app(tmp_path)
    _seed_snapshot(db, PAST)
    with TestClient(app) as client:
        resp = client.get(f"/api/signals/day/{PAST}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["scan_date"] == PAST and body["as_of"] == "close"


def test_day_without_snapshot_returns_available_false(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get(f"/api/signals/day/{PAST}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["as_of"] is None and body["sell_hard"] == []


def test_today_and_future_rejected(tmp_path) -> None:
    app, _db = _app(tmp_path)
    today = today_date()
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    with TestClient(app) as client:
        assert client.get(f"/api/signals/day/{today}").status_code == 422
        assert client.get(f"/api/signals/day/{tomorrow}").status_code == 422


def test_non_trading_day_rejects_with_suggestion(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get("/api/signals/day/2026-08-23")  # 周日
    assert resp.status_code == 422
    assert "2026-08-21" in resp.json()["detail"]


def test_bad_format_rejected(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/signals/day/20260821").status_code == 422


def test_replay_runs_and_persists(tmp_path, monkeypatch) -> None:
    app, db = _app(tmp_path)
    from lei_signal.api import signal_replay
    monkeypatch.setattr(
        signal_replay, "run_signal_replay",
        lambda db_path, day, **kw: {"scan_date": day.isoformat(), "as_of": "close",
                                    "scanned": 0, "buy_rows": 0, "sell_rows": 0,
                                    "unavailable": 0, "generated_at": "x"},
    )
    with TestClient(app) as client:
        resp = client.post(f"/api/signals/day/{PAST}/replay")
    assert resp.status_code == 200
    assert resp.json()["available"] is True
    with closing(connect(db)) as conn:
        assert conn.execute(
            "SELECT title FROM signal_alerts WHERE scan_date=? AND side='meta'", (PAST,),
        ).fetchone() is not None  # 回放落了 meta 行
