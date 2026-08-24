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
    assert "rule_id:" not in r["reply"]  # FR-2 收紧：降级模板正文无工程标注


def test_rule_id_echo_degrades(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-2: LLM 回显「rule_id:」即使过白名单校验也降级——工程标注只走 trace 角标。

    「rule_id: 见溯源角标」中 rule_id 后无 ASCII 标识符，``verify_grounding``
    抽不到 rule_id（白名单不拒），数值校验也无数字可拒——只有 FR-2 新增的
    ``"rule_id:" not in raw`` 能确定性拦下，防合法 rule_id 回显漏进默认 DOM。
    """
    monkeypatch.setattr(
        llm, "_llm_call", lambda cfg, msgs: "结构确认成立（rule_id: 见溯源角标）"
    )
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "这个买点为什么是买点",
    }).json()
    assert r["grounded"] is False
    assert "rule_id:" not in r["reply"]


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


# ---- Fix round 1：审查 Important-1 / M-1 / M-2 / M-4 回归测试 ----


def _boom_discussion(payload, history, message, config):  # noqa: ANN001
    """模拟 chat_discussion 段真 bug（网络层已被 llm.py 捕获返 None，兜不住的路径）。"""
    raise RuntimeError("unexpected bug in discussion pipeline")


def test_llm_unexpected_exception_degrades(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Important-1：LLM 段意外异常不 500 裸奔，走降级模板（grounded=False）。"""
    monkeypatch.setattr(llm, "chat_discussion", _boom_discussion)
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "说说",
    })
    assert r.status_code == 200  # 不再 500
    body = r.json()
    assert body["grounded"] is False
    assert "数据日" in body["reply"]  # symbol 上下文的降级模板


def test_llm_exception_still_persists_turn(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Important-1：异常兜底后本轮消息仍成对落库，不丢会话、不留空会话。"""
    monkeypatch.setattr(llm, "chat_discussion", _boom_discussion)
    body = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "说说",
    }).json()
    msgs = client.get(f"/api/agent/sessions/{body['session_id']}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["grounded"] is False


def test_user_number_echo_stays_grounded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M-1：用户消息中的数字并入白名单，LLM 回显「你说的 8700」不再降级。"""
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "你说的 8700 与当前结构不重叠")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "8700 是不是更好的位置",
    })
    assert r.status_code == 200
    assert r.json()["grounded"] is True


def test_global_context_degraded_copy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M-4：global 上下文降级不输出「【】数据日 -」空段，给全局会话专属文案。"""
    monkeypatch.setattr(llm, "load_ark_config", lambda: None)
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "global",
        "symbol": None, "message": "现在整体环境怎么看",
    })
    assert r.status_code == 200
    reply = r.json()["reply"]
    assert "数据日 -" not in reply
    assert "全局会话" in reply


def test_plans_filtered_to_armed_entered(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M-2：喂给 build_discussion_context 的 plans 只剩 armed/entered（保序过滤）。"""
    from lei_signal.api.routes import agent as agent_routes
    from lei_signal.plans.models import TradePlan

    def plan(pid: str, state: str) -> TradePlan:
        return TradePlan(
            plan_id=pid, symbol=SYMBOL, module="A", direction="long",
            entry_rule_id=None, entry_lifecycle_id=None, entry_trigger_cn=None,
            entry_price_ref=None, invalidation_price=None, target_b_price=None,
            target_b_source=None, reward_risk_at_plan=None,
            valid_until="2099-01-01", state=state, ruleset_version="test",
            reason="test",
        )

    mixed = [
        plan("p-entered", "entered"), plan("p-draft", "draft"),
        plan("p-closed", "closed"), plan("p-armed", "armed"),
        plan("p-exited", "exited"),
    ]
    captured: dict = {}

    def fake_build_ctx(result, review, plans, open_items):  # noqa: ANN001
        captured["states"] = [p.state for p in plans]
        return {"context_kind": "symbol"}

    monkeypatch.setattr(
        agent_routes, "list_plans",
        lambda conn, *, symbol=None, state=None: mixed,
    )
    monkeypatch.setattr(agent_routes, "build_discussion_context", fake_build_ctx)
    monkeypatch.setattr(llm, "_llm_call", lambda cfg, msgs: "好的")
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "symbol",
        "symbol": "000300.SS", "message": "当前在盯什么计划",
    })
    assert r.status_code == 200
    assert captured["states"] == ["entered", "armed"]


def test_global_message_with_code_resolves_symbol(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """全局会话里用户报代码（「000300 怎么看」）→ 自动带出技术材料，不再反问。"""
    captured = {}

    def fake_call(cfg, messages):  # noqa: ANN001, ANN202
        captured["material"] = next(
            (m["content"] for m in messages if "技术材料" in str(m.get("content", ""))), ""
        )
        return "好的，已看到材料。"

    monkeypatch.setattr(llm, "_llm_call", fake_call)
    r = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "global",
        "symbol": None, "message": "515880 怎么看",
    })
    assert r.status_code == 200
    assert "515880.SS" in captured["material"]


def test_symbol_inherited_across_turns(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    """第一轮报代码，第二轮无代码追问 → 材料（resolved_symbol meta）继承。"""
    captured = {}

    def fake_call(cfg, messages):  # noqa: ANN001, ANN202
        captured["material"] = str(messages)
        return "收到。"

    monkeypatch.setattr(llm, "_llm_call", fake_call)
    first = client.post("/api/agent/chat", json={
        "session_id": None, "context_kind": "global",
        "symbol": None, "message": "515880 怎么看",
    }).json()
    second = client.post("/api/agent/chat", json={
        "session_id": first["session_id"], "context_kind": "global",
        "symbol": None, "message": "筹码呢",
    })
    assert second.status_code == 200
    assert "515880.SS" in captured["material"]  # 第二轮仍有该标的材料
