"""dispatch：意图分发正确、卡片带 card_type、未识别回落 chat。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def app(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    # 预置当日扫描行：dispatch 推荐分支读表即可，不需要 analysis_service
    from lei_signal.api.opportunity_scan import today_date

    conn.execute(
        "INSERT OR REPLACE INTO daily_opportunity_scan "
        "(scan_date, symbol, display_name, verdict, verdict_cn, best_scenario_cn, "
        " best_state, reward_risk_ratio, reward_risk_computable, blocking_reasons, "
        " missing_summary_cn, has_active_plan, generated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (today_date(), "515880", "通信ETF", "waiting", "等待条件成立",
         "A·回调", "watch", 2.5, 1, "[]", "站上EMA20", 0, "x"),
    )
    conn.commit()
    conn.close()
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = db
    a.state.watchlist_db_path = db
    a.include_router(copilot_routes.router)
    return a


def test_dispatch_recommend_returns_card(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "今天看什么"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "recommend"
    assert body["chat_fallback"] is False
    assert body["card"]["card_type"] == "recommend"
    assert "items" in body["card"]["data"]


def test_dispatch_trade_report_returns_preview(app):
    r = TestClient(app).post(
        "/api/copilot/dispatch", json={"message": "我昨天买了1万515880"}
    )
    body = r.json()
    assert body["intent"] == "trade_report"
    assert body["preview"]["fund_code"] == "515880"
    assert body["preview"]["amount"] == 10000.0
    assert body["chat_fallback"] is False


def test_dispatch_holdings_card(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "持仓速览"})
    body = r.json()
    assert body["intent"] == "holdings"
    assert body["card"]["card_type"] == "holdings"


def test_dispatch_unknown_falls_back_to_chat(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "市场环境怎么样"})
    body = r.json()
    assert body["intent"] == "chat" and body["chat_fallback"] is True
    assert body["card"] is None
