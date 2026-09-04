"""台账路由：预览→确认→列表链路 + 校验拒绝（fetch_nav 注入，不打网络）。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.copilot import trades as trades_mod
from lei_signal.portfolio.funddata import NavPoint


@pytest.fixture()
def app(tmp_path, monkeypatch):
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = str(tmp_path / "t.db")
    a.state.watchlist_db_path = a.state.plans_db_path
    a.include_router(copilot_routes.router)

    def fake_fetch(code, page_size=40):
        return [NavPoint(date="2026-09-05", unit_nav=1.10),
                NavPoint(date="2026-09-04", unit_nav=1.00)]

    monkeypatch.setattr(trades_mod, "fetch_nav_history", fake_fetch)
    return a


def test_preview_then_create_then_list(app):
    client = TestClient(app)
    pv = client.post(
        "/api/copilot/trades/preview", json={"message": "我昨天买了1万012414"}
    ).json()
    assert pv["fund_code"] == "012414" and pv["amount"] == 10000.0
    created = client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "测试基金", "side": "buy",
        "amount": 10000.0, "trade_date": "2026-09-04",
    })
    assert created.status_code == 200
    body = created.json()
    assert body["price_status"] == "priced"      # 创建即尝试定价
    assert body["priced_nav"] == pytest.approx(1.00)
    listed = client.get("/api/copilot/trades").json()
    assert len(listed["trades"]) == 1
    assert listed["positions"][0]["shares"] == pytest.approx(10000.0)


def test_create_rejects_bad_payload(app):
    client = TestClient(app)
    r = client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "x", "side": "hold",
        "amount": 1.0, "trade_date": "2026-09-04",
    })
    assert r.status_code in (400, 422)
    r2 = client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "x", "side": "buy",
        "amount": -5, "trade_date": "2026-09-04",
    })
    assert r2.status_code in (400, 422)


def test_dispatch_holdings_includes_fund_positions(app):
    client = TestClient(app)
    client.post("/api/copilot/trades", json={
        "fund_code": "012414", "fund_name": "测试基金", "side": "buy",
        "amount": 10000.0, "trade_date": "2026-09-04",
    })
    body = client.post(
        "/api/copilot/dispatch", json={"message": "持仓速览"}
    ).json()
    data = body["card"]["data"]
    assert len(data["fund_positions"]) == 1
