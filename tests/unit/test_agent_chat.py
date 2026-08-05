"""监督员 agent chat 端点：接地校验与降级（红线：判定权在 Python，LLM 只表达）。"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.routes import agent
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.llm import ArkConfig
from lei_signal.plans.store import confirm_plan, create_plan
from lei_signal.storage.sqlite_store import connect

SYMBOL = "000001.SS"
RULESET = "1.3.0"


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    index = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    price_data = PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info,
    )
    return analyze_bars(symbol, frame, price_data=price_data)


def _client(tmp_path, monkeypatch) -> TestClient:
    db_path = str(tmp_path / "agent.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    # 建一个已确认的计划供 chat 端点监督。
    conn = connect(db_path)
    try:
        plan = create_plan(
            conn, symbol=SYMBOL, module="A", direction="long", ruleset_version=RULESET,
            reason="测试", valid_until="2026-12-31", entry_rule_id="first_ma_pullback",
            entry_lifecycle_id="lc1", entry_trigger_cn="首次回撤确认",
            entry_price_ref=100.0, invalidation_price=95.0, target_b_price=115.0,
            target_b_source="swing_high", reward_risk_at_plan=3.0, thesis_cn="测试假设",
            invalidation_criteria_cn="跌破 95", drawdown_playbook_cn="回踩 SMA60",
            take_profit_plan_cn="分批止盈", stop_plan_cn="结构止损",
        )
        confirm_plan(conn, plan.plan_id)
        plan_id = plan.plan_id
    finally:
        conn.close()
    client = TestClient(app)
    client.plan_id = plan_id  # type: ignore[attr-defined]
    return client


def _config() -> ArkConfig:
    return ArkConfig(api_key="test-only", base_url="https://example.test", model="test")


def test_chat_grounded_when_llm_output_clean(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: _config())
    monkeypatch.setattr(
        agent, "chat_ark", lambda payload, message, config: "当前监督提醒：均线回撤，可执行日见待办。"
    )
    resp = client.post(f"/api/plans/{client.plan_id}/chat", json={"message": "怎么看"})  # type: ignore[attr-defined]
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is True
    assert "均线回撤" in body["reply"]
    assert body["plan_id"] == client.plan_id  # type: ignore[attr-defined]


def test_chat_falls_back_when_llm_uses_forbidden_word(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: _config())
    monkeypatch.setattr(agent, "chat_ark", lambda payload, message, config: "建议买入该标的")
    resp = client.post(f"/api/plans/{client.plan_id}/chat", json={"message": ""})  # type: ignore[attr-defined]
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is False
    # 降级模板直出，含计划头（不混入禁用词）。
    assert "建议买" not in body["reply"]


def test_chat_falls_back_when_llm_cites_unknown_rule_id(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: _config())
    monkeypatch.setattr(
        agent, "chat_ark", lambda payload, message, config: "rule_id:totally_fake_rule 触发"
    )
    resp = client.post(f"/api/plans/{client.plan_id}/chat", json={"message": "?"})  # type: ignore[attr-defined]
    body = resp.json()
    assert body["grounded"] is False
    assert "totally_fake_rule" not in body["reply"]


def test_chat_falls_back_when_no_ark_config(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: None)
    resp = client.post(f"/api/plans/{client.plan_id}/chat", json={"message": "怎么看"})  # type: ignore[attr-defined]
    body = resp.json()
    assert body["grounded"] is False
    # 模板仍带计划信息。
    assert SYMBOL in body["reply"]


def test_chat_404_for_unknown_plan(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/plans/no-such-plan/chat", json={"message": ""})
    assert resp.status_code == 404
