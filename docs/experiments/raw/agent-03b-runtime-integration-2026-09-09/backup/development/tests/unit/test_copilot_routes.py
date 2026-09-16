"""copilot 路由：推荐端点用假 service + 预置扫描表，验证读表/存证/降级。"""
from __future__ import annotations

from contextlib import closing

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.opportunity_scan import today_date
from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


class _FakeEntry:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error


class _FakeService:
    def __init__(self, results):
        self._results = results

    def get(self, symbol, refresh=False):
        return self._results.get(symbol, _FakeEntry(error="no data"))

    def get_many(self, symbols, refresh=False):
        return {s: self.get(s) for s in symbols}


@pytest.fixture()
def app(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO daily_opportunity_scan "
        "(scan_date, symbol, display_name, verdict, verdict_cn, best_scenario_cn, "
        " best_state, reward_risk_ratio, reward_risk_computable, blocking_reasons, "
        " missing_summary_cn, has_active_plan, generated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (today_date(), "515880", "通信ETF", "waiting", "等待条件成立",
         "A·回调", "watch", 2.5, 1, "[]", "站上EMA20", 0, "2026-09-05T15:00:00"),
    )
    conn.commit()
    conn.close()

    a = FastAPI()
    a.state.analysis_service = _FakeService({})
    a.state.plans_db_path = db
    a.state.watchlist_db_path = db
    a.include_router(copilot_routes.router)
    return a


def test_recommend_reads_today_table_and_saves_journal(app):
    client = TestClient(app)
    resp = client.get("/api/copilot/recommend")
    assert resp.status_code == 200
    card = resp.json()
    assert card["run_date"] == today_date()
    assert [i["symbol"] for i in card["items"]] == ["515880"]
    with closing(connect(app.state.plans_db_path)) as conn:
        assert journal.load_recommendation(conn, today_date()) is not None


def test_recommend_save_false_skips_journal(app):
    client = TestClient(app)
    resp = client.get("/api/copilot/recommend?save=false")
    assert resp.status_code == 200
    with closing(connect(app.state.plans_db_path)) as conn:
        assert journal.load_recommendation(conn, today_date()) is None


def test_recommend_empty_table_returns_empty_card(app):
    with closing(connect(app.state.plans_db_path)) as conn:
        conn.execute("DELETE FROM daily_opportunity_scan")
        conn.commit()
    client = TestClient(app)
    resp = client.get("/api/copilot/recommend")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
