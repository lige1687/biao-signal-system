"""统一 chat 端点：会话持久化、多轮历史进 payload、数值接地降级、trace 角标数据。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import lei_signal.plans.llm as llm
from lei_signal.api.app import create_app
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.llm import ArkConfig

SYMBOL = "000300.SS"


def _fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    """fixture 分析：tests/000300.SS.bars.parquet（1500 根，真实指标链）。"""
    bars = pd.read_parquet(Path("tests/000300.SS.bars.parquet"))
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    price_data = PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info,
    )
    return analyze_bars(symbol, frame, price_data=price_data)


def _config() -> ArkConfig:
    return ArkConfig(api_key="test-only", base_url="https://example.test", model="test")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """带 fixture 分析服务的 app（同 tests/unit/test_agent_chat.py 的构造模式）。

    LLM mock 只给配置（load_ark_config -> 测试配置）；网络层由各测试按需
    monkeypatch ``llm._llm_call``（plans.llm 的统一 monkeypatch 点）。
    """
    db_path = str(tmp_path / "agent-chat.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    monkeypatch.setattr(llm, "load_ark_config", lambda: _config())
    return TestClient(app)


def test_chat_creates_session_and_persists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "结构确认，关键位 4029.86")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "这个买点为什么是买点",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    sid = body["session_id"]
    msgs = client.get(f"/api/agent/sessions/{sid}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_second_turn_carries_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict = {}

    def fake(cfg, msgs):  # noqa: ANN001, ANN002
        seen["history"] = [m for m in msgs if m["role"] != "system"]
        return "好的"

    monkeypatch.setattr(llm, "_llm_call", fake)
    first = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "第一问",
    }).json()
    client.post("/api/agent/chat", json={
        "session_id": first["session_id"], "context_kind": "symbol",
        "symbol": "000300.SS", "message": "第二问",
    })
    contents = [m["content"] for m in seen["history"]]
    assert any("第一问" in c for c in contents)      # 历史进 payload
    assert any("技术材料" in c for c in contents)     # 技术全貌也在


def test_invented_number_degrades(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "关键位 99999.99")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "说说",
    }).json()
    assert r["grounded"] is False  # 编数字 → 降级模板
    assert "rule_id:" not in r["reply"] or r["trace"]  # trace 走结构化字段


def test_llm_unavailable_still_replies(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "load_ark_config", lambda: None)
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "说说",
    })
    assert r.status_code == 200 and r.json()["grounded"] is False


def test_sessions_list(client: TestClient) -> None:
    r = client.post("/api/agent/sessions", json={
        "symbol": "000300.SS", "title_cn": "讨论",
    })
    assert r.status_code == 200
    lst = client.get("/api/agent/sessions?symbol=000300.SS").json()
    assert any(s["title_cn"] == "讨论" for s in lst)
