"""推荐讲解：GLM 接地通过 / 禁用词降级 / 编数值降级 / 无凭据模板直出。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.plans import llm as plans_llm


@pytest.fixture()
def app(tmp_path, monkeypatch):
    for name in ("GLM_API_KEY", "DEEPSEEK_API_KEY", "ARK_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    db = str(tmp_path / "t.db")
    conn = None
    from lei_signal.api.opportunity_scan import today_date
    from lei_signal.storage.sqlite_store import connect

    conn = connect(db)
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


def _with_llm(app, monkeypatch, reply_text):
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        copilot_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )
    monkeypatch.setattr(
        copilot_routes.plans_llm, "chat_copilot",
        lambda payload, message, config, *, system_prompt: reply_text,
    )
    return TestClient(app)


def test_no_credentials_template(app):
    r = TestClient(app).post("/api/copilot/recommend/explain", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is False
    assert "排序仅影响展示顺序" in body["reply"]


def test_grounded_llm_reply_passes(app, monkeypatch):
    client = _with_llm(
        app, monkeypatch,
        "今日自选里值得先看的是通信ETF，条件仍在等待成立；"
        "排序仅影响展示顺序，不构成新判定。",
    )
    body = client.post("/api/copilot/recommend/explain", json={}).json()
    assert body["grounded"] is True


def test_banned_word_degrades(app, monkeypatch):
    client = _with_llm(app, monkeypatch, "建议买入515880。")
    body = client.post("/api/copilot/recommend/explain", json={}).json()
    assert body["grounded"] is False
    assert "排序仅影响展示顺序" in body["reply"]


def test_fabricated_number_degrades(app, monkeypatch):
    client = _with_llm(
        app, monkeypatch, "515880 今天涨了 88.8%，排序仅影响展示顺序。"
    )
    body = client.post("/api/copilot/recommend/explain", json={}).json()
    assert body["grounded"] is False
