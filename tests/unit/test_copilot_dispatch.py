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
    assert body["fallback_reason"] is None  # 真未命中：回落不带原因


# ---- 意图路由扩展（2026-09-19）入口级轨迹断言 ----
# 断言回包结构（intent/chat_fallback/card.card_type/fallback_reason），不凭回答正文判定。


def test_dispatch_dca_returns_state_card(app):
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "现在能定投吗"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "dca"
    assert body["chat_fallback"] is False
    assert body["card"]["card_type"] == "dca"
    data = body["card"]["data"]
    assert "evidence_available" in data
    assert "states" in data and isinstance(data["states"], list)
    assert set(data["breadth"]) == {"cn", "us"}
    assert "只提示不判定" in data["hint_cn"]


def test_dispatch_dca_with_symbol(app):
    r = TestClient(app).post(
        "/api/copilot/dispatch",
        json={"message": "这个ETF适合定投吗", "symbol": "515880.SS"},
    )
    body = r.json()
    assert body["intent"] == "dca" and body["symbol"] == "515880.SS"
    assert body["card"]["card_type"] == "dca"


def test_dispatch_sentiment_narrative_card(app, monkeypatch):
    # 禁网红线：两融行情为外呼来源，测试注入 None（生产路径不变，缺席如实）
    monkeypatch.setattr("lei_signal.copilot.sentiment.margin_regime_cn", lambda: None)
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "市场情绪怎么样"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "sentiment"
    assert body["chat_fallback"] is False
    assert body["card"]["card_type"] == "sentiment"
    data = body["card"]["data"]
    assert "available" in data and "hot_boards" in data and "cold_boards" in data
    assert data["margin"] is None
    assert "不参与技术判定" in body["note_cn"]  # 只叙事红线随卡下带


def test_dispatch_mindset_returns_narrative_card(app):
    # 种子库在场（已入仓）：出 card_type=mindset 叙事卡，带出处与只叙事红线
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "心态崩了"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "mindset"
    assert body["chat_fallback"] is False
    assert body["fallback_reason"] is None
    assert body["card"]["card_type"] == "mindset"
    data = body["card"]["data"]
    assert data["available"] is True and data["count"] > 0
    for item in data["items"][:3]:
        assert set(item) >= {"category", "text", "quote", "source", "seed_key"}
    assert "不参与" in body["note_cn"]  # 只叙事红线随卡下带


def test_dispatch_mindset_falls_back_with_reason(app, monkeypatch):
    # 种子库缺位（模拟文件缺失）：回落行为与接入前一致，原因可观察
    from lei_signal.copilot import intent as intent_mod
    from lei_signal.copilot import mindset as mindset_mod

    monkeypatch.setattr(intent_mod, "_mindset_seeds_ok", lambda: False)
    monkeypatch.setattr(
        mindset_mod, "load_mindset_seeds",
        lambda path=None: {"available": False, "items": [], "count": 0},
    )
    r = TestClient(app).post("/api/copilot/dispatch", json={"message": "心态崩了"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "chat"
    assert body["chat_fallback"] is True
    assert body["fallback_reason"] == "mindset_seed_missing"  # 回落原因可观察
    assert "心态" in body["note_cn"]


def test_dispatch_sequence_no_hidden_state(app):
    # 连续讨论：dispatch 逐条独立判定，无跨消息会话态
    client = TestClient(app)
    for msg, kind in (
        ("现在能定投吗", "dca"),
        ("515880 呢", "chat"),
        ("我昨天买了1万515880", "trade_report"),
    ):
        body = client.post("/api/copilot/dispatch", json={"message": msg}).json()
        assert body["intent"] == kind, msg
