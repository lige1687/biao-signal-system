"""Holding chat scope, evidence, and replay; no real model or portfolio writes."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api import portfolio_workspace
from lei_signal.api.routes import agent
from lei_signal.copilot.portfolio_context import scope_token
from lei_signal.plans import llm as plans_llm
from lei_signal.storage.sqlite_store import connect


def _workspace() -> dict:
    return {
        "generated_at": "2026-10-02T10:00:00+08:00",
        "review_date": "2026-10-02", "as_of": "2026-09-30",
        "coverage": {"total": 2, "with_plan": 1},
        "items": [
            {"holding_id": "A", "name": "甲基金", "code": "510300", "group_name": "宽基",
             "market_value": 1000, "weight_pct": 50, "return_pct": 2,
             "holding_as_of": "2026-09-30", "original_note": "长期看好宽基，仅为旧备注", "nav": {"value": 1.2, "date": "2026-09-29", "updated_at": "2026-10-02"},
             "symbol": "510300.SS", "status": "incomplete", "title_cn": "资料待补",
             "reason_cn": "没有已关联计划", "next_step_cn": "核实原计划", "gaps": ["尚未关联有效的持仓计划"],
             "technical": None, "plan": None, "plan_candidates": [{"plan_id": "candidate"}],
             "alerts": [{"code": "WATCH", "data_as_of": "2026-09-29",
                         "actionable_from": "2026-10-03", "next_step_cn": "待复核"}]},
            {"holding_id": "B", "name": "乙基金", "code": "159915", "group_name": "宽基",
             "market_value": 1000, "weight_pct": 50, "return_pct": -1,
             "holding_as_of": "2026-09-30", "nav": None,
             "symbol": None, "status": "incomplete", "title_cn": "资料待补",
             "reason_cn": "缺少行情", "next_step_cn": "核实同产品", "gaps": ["未能确认同一产品的技术行情"],
             "technical": None, "plan": None, "plan_candidates": []},
        ],
    }


@pytest.fixture()
def env(tmp_path, monkeypatch):
    db = str(tmp_path / "agent.db")
    connect(db).close()
    app = FastAPI()
    app.state.plans_db_path = db
    app.state.analysis_service = None
    app.include_router(agent.router)
    data = _workspace()
    monkeypatch.setattr(portfolio_workspace, "build_workspace", lambda request: data)
    monkeypatch.setattr(agent.plans_llm, "load_ark_config", lambda: None)
    monkeypatch.setattr(agent, "_symbol_candidates_from_message",
                        lambda _: pytest.fail("证券解析不应处理持仓问题"))
    with TestClient(app) as client:
        yield client, db, data


def _ask(client, holding_id, cid, *, session_id=None, message="原计划满足了吗？510300"):
    return client.post("/api/agent/chat", json={
        "context_kind": "portfolio", "portfolio_holding_id": holding_id,
        "symbol": None, "message": message, "session_id": session_id,
        "client_request_id": cid,
    })


def _events(response):
    result = []
    for frame in response.text.split("\n\n"):
        event = next((line[7:] for line in frame.splitlines() if line.startswith("event: ")), None)
        raw = next((line[6:] for line in frame.splitlines() if line.startswith("data: ")), None)
        if event and raw:
            result.append((event, json.loads(raw)))
    return result


def test_scope_identity_server_material_and_no_auto_plan(env):
    client, db, data = env
    a = _ask(client, "A", "cid-a")
    assert a.status_code == 200, a.text
    body = a.json()
    assert body["resolved_symbol"] is None
    assert body["plan_artifact"] is None
    assert "没有已关联计划" in body["reply"]
    material = body["evidence_card"]["portfolio"]
    assert material["portfolio_holding_id"] == "A"
    assert [item["holding_id"] for item in material["items"]] == ["A"]
    assert material["items"][0]["plan"] is None
    assert material["items"][0]["original_note"] == "长期看好宽基，仅为旧备注"
    assert material["items"][0]["alerts"][0]["data_as_of"] == "2026-09-29"
    assert material["items"][0]["alerts"][0]["actionable_from"] == "2026-10-03"
    assert material["items"][0]["nav"]["date"] == "2026-09-29"
    assert material["items"][0]["nav"]["updated_at"] == "2026-10-02"
    # The request scope is server-owned, including the session's persisted identity.
    with connect(db) as conn:
        row = conn.execute("SELECT symbol FROM agent_sessions WHERE session_id=?",
                           (body["session_id"],)).fetchone()
        assert row["symbol"] == scope_token("A")
        snap = json.loads(conn.execute("SELECT meta_json FROM agent_messages WHERE message_id=?",
                                       (body["question_id"],)).fetchone()[0])["discussion_v1"]
        assert snap["context_kind"] == "portfolio"
        assert snap["portfolio_holding_id"] == "A"
        assert snap["portfolio"]["items"][0]["name"] == "甲基金"

    # Identical cid is an exact replay even after live workspace changes.
    data["items"][0]["name"] = "改名之后"
    replay = _ask(client, "A", "cid-a")
    assert replay.status_code == 200
    assert replay.json()["reply"] == body["reply"]
    assert replay.json()["evidence_card"] == body["evidence_card"]


def test_user_send_reaches_existing_model_with_only_selected_server_material(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(agent.plans_llm, "load_ark_config",
                        lambda: plans_llm.ArkConfig(api_key="test-only"))
    seen = []

    def fake_chat(payload, history, message, config):
        seen.append((payload, history, message))
        return "甲基金资料待补，先核实原计划。"

    monkeypatch.setattr(agent.plans_llm, "chat_discussion", fake_chat)
    result = _ask(client, "A", "cid-model")
    assert result.status_code == 200
    assert result.json()["reply"] == "甲基金资料待补，先核实原计划。"
    assert result.json()["grounded"] is True
    assert len(seen) == 1
    assert seen[0][0]["context_kind"] == "portfolio"
    assert [item["holding_id"] for item in seen[0][0]["portfolio"]["items"]] == ["A"]
    assert seen[0][0]["portfolio"]["items"][0]["plan"] is None


def test_a_b_all_and_cross_scope_rejections(env):
    client, db, _ = env
    a = _ask(client, "A", "cid-a").json()
    b = _ask(client, "B", "cid-b").json()
    all_holdings = _ask(client, None, "cid-all").json()
    assert len(all_holdings["evidence_card"]["portfolio"]["items"]) == 2
    assert b["session_id"] != a["session_id"] != all_holdings["session_id"]
    assert _ask(client, "B", "cid-a").status_code == 409
    assert _ask(client, "B", "cid-next", session_id=a["session_id"]).status_code == 409
    assert _ask(client, None, "cid-next2", session_id=a["session_id"]).status_code == 409
    assert client.post("/api/agent/chat", json={"context_kind": "symbol", "symbol": "510300.SS",
      "message": "旧会话", "session_id": a["session_id"]}).status_code == 409
    assert client.get(f"/api/agent/sessions/{a['session_id']}/messages").status_code == 409
    assert client.get(f"/api/agent/sessions/{a['session_id']}/messages?context_kind=portfolio&portfolio_holding_id=B").status_code == 409
    assert client.get(f"/api/agent/sessions/{a['session_id']}/messages?context_kind=portfolio&portfolio_holding_id=A").status_code == 200
    assert _ask(client, "missing", "cid-missing").status_code == 404
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM agent_chat_requests WHERE client_request_id='cid-missing'").fetchone()[0] == 0


def test_stream_prepared_uses_server_scope_and_no_plan(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(agent.plans_llm, "load_ark_config", lambda: None)
    response = client.post("/api/agent/chat/stream", json={
        "context_kind": "portfolio", "portfolio_holding_id": "B", "symbol": None,
        "message": "乙基金有什么变化？159915", "client_request_id": "cid-stream",
    })
    events = _events(response)
    prepared = next(data for event, data in events if event == "prepared")
    done = next(data for event, data in events if event == "done")
    assert prepared["resolved_symbol"] is None
    assert [item["holding_id"] for item in prepared["evidence_card"]["portfolio"]["items"]] == ["B"]
    assert prepared["next_steps"] == []
    assert done["plan_artifact"] is None
    assert done["resolved_symbol"] is None


def test_incomplete_retry_uses_frozen_holding_material(env, monkeypatch):
    client, db, data = env
    monkeypatch.setattr(agent.plans_llm, "load_ark_config",
                        lambda: plans_llm.ArkConfig(api_key="test-only"))
    seen = []

    def fake_stream(payload, history, message, config):
        seen.append(payload["portfolio"]["items"][0]["name"])
        if len(seen) == 1:
            yield "部分回答"
            yield plans_llm.StreamInterrupt("connection_interrupted")
        else:
            yield "先核实原计划，不能凭候选计划说已经满足。"

    monkeypatch.setattr(agent.plans_llm, "chat_discussion_stream", fake_stream)
    request = {"context_kind": "portfolio", "portfolio_holding_id": "A",
               "symbol": None, "message": "原计划怎样？", "client_request_id": "cid-resume"}
    first = _events(client.post("/api/agent/chat/stream", json=request))
    done1 = next(payload for event, payload in first if event == "done")
    assert done1["answer_state"] == "incomplete"
    data["items"][0]["name"] = "更新后的名称"
    history = client.get(f"/api/agent/sessions/{done1['session_id']}/messages?context_kind=portfolio&portfolio_holding_id=A").json()
    incomplete = next(row for row in history if row["role"] == "assistant")
    assert incomplete["retry"]["client_request_id"] == "cid-resume"
    assert incomplete["retry"]["portfolio_holding_id"] == "A"
    assert incomplete["retry"]["symbol"] is None
    second = _events(client.post("/api/agent/chat/stream", json=request))
    done2 = next(payload for event, payload in second if event == "done")
    assert done2["question_id"] == done1["question_id"]
    assert done2["answer_state"] == "answered"
    assert seen == ["甲基金", "甲基金"]
    with connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0] == 1


def test_invalid_model_text_keeps_warning_and_system_fallback_after_reopen(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(agent.plans_llm, "load_ark_config",
                        lambda: plans_llm.ArkConfig(api_key="test-only"))
    calls = []

    def fake_stream(payload, history, message, config):
        calls.append(1)
        yield "甲基金会到 999999 元，原计划肯定安全。"

    monkeypatch.setattr(agent.plans_llm, "chat_discussion_stream", fake_stream)
    request = {"context_kind": "portfolio", "portfolio_holding_id": "A",
               "symbol": None, "message": "原计划怎样？", "client_request_id": "cid-unsafe"}
    first = _events(client.post("/api/agent/chat/stream", json=request))
    done = next(payload for event, payload in first if event == "done")
    assert done["grounded"] is False
    assert done["verify_note"]
    assert "今日持仓资料" in done["fallback"]
    history = client.get(f"/api/agent/sessions/{done['session_id']}/messages?context_kind=portfolio&portfolio_holding_id=A").json()
    assistant = next(row for row in history if row["role"] == "assistant")
    assert assistant["grounded"] is False
    assert assistant["verify_note"] == done["verify_note"]
    assert assistant["fallback"] == done["fallback"]
    assert assistant["evidence_card"]["portfolio"]["items"][0]["holding_id"] == "A"
    replay = _events(client.post("/api/agent/chat/stream", json=request))
    replay_done = next(payload for event, payload in replay if event == "done")
    assert replay_done["verify_note"] == done["verify_note"]
    assert replay_done["fallback"] == done["fallback"]
    assert calls == [1]
