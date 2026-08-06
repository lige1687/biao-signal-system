"""买点分析问答门禁：接地校验与降级（红线：LLM 不自行判断买点，不推算价位）。"""
from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.routes import agent
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.llm import ArkConfig

SYMBOL = "000001.SS"


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
                     "close": close, "volume": 1_000_000})
    df = pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=n))
    return df[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info))


def _client(tmp_path, monkeypatch) -> TestClient:
    db = str(tmp_path / "bpc.db")
    svc = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=svc)
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    return TestClient(app)


def _config() -> ArkConfig:
    return ArkConfig(api_key="test-only", base_url="https://example.test", model="test")


def test_buy_point_chat_grounded_when_llm_clean(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: _config())
    monkeypatch.setattr(
        agent, "chat_buy_point",
        lambda payload, message, config: (
            "当前无系统定义的买点，可交易性未阻断。判定方式为研究代理。"
        ),
    )
    resp = client.post(f"/api/symbols/{SYMBOL}/buy-point-chat", json={"message": "能买吗"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is True
    assert "研究代理" in body["reply"]
    assert body["symbol"] == SYMBOL
    assert body["review"] is not None


def test_buy_point_chat_falls_back_when_llm_uses_forbidden_word(tmp_path, monkeypatch):  # noqa: ANN001
    """LLM 输出含禁用词 -> 降级模板（grounded=False），不把禁用词带给用户。"""
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: _config())
    monkeypatch.setattr(agent, "chat_buy_point", lambda payload, message, config: "建议买入该标的")
    resp = client.post(f"/api/symbols/{SYMBOL}/buy-point-chat", json={"message": ""})
    body = resp.json()
    assert body["grounded"] is False
    assert "建议买" not in body["reply"]
    # 降级模板仍带结构化审阅
    assert "买点审阅" in body["reply"]


def test_buy_point_chat_falls_back_when_no_config(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """无 ark 凭据 -> 直接模板直出（grounded=False）。"""
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: None)
    resp = client.post(f"/api/symbols/{SYMBOL}/buy-point-chat", json={"message": "怎么看"})
    body = resp.json()
    assert body["grounded"] is False
    assert "买点审阅" in body["reply"]
    assert SYMBOL in body["reply"] or "000001" in body["reply"]


def test_buy_point_chat_falls_back_when_llm_cites_fake_rule_id(tmp_path, monkeypatch):  # noqa: ANN001
    """LLM 编造 review 未给出的 rule_id -> 降级。"""
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: _config())
    monkeypatch.setattr(
        agent, "chat_buy_point",
        lambda payload, message, config: "rule_id:totally_fake_rule 触发买点",
    )
    resp = client.post(f"/api/symbols/{SYMBOL}/buy-point-chat", json={"message": "?"})
    body = resp.json()
    assert body["grounded"] is False
    assert "totally_fake_rule" not in body["reply"]


def test_buy_point_chat_returns_review_object(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """回复里带完整 review 对象，前端可同时展示结构化数据与讲解。"""
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(agent, "load_ark_config", lambda: None)
    resp = client.post(f"/api/symbols/{SYMBOL}/buy-point-chat", json={"message": ""})
    body = resp.json()
    assert body["review"]["symbol"] == SYMBOL
    assert body["review"]["verdict"] in ("actionable", "blocked", "waiting", "none")
