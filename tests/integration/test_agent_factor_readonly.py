"""Factor queries never reach market analysis, LLMs, or the backtest worker."""
from __future__ import annotations

import json
import socket
from contextlib import closing
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import agent, copilot
from lei_signal.plans import llm
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from lei_signal.research import factor_runtime
    from lei_signal.research.factor_lab import adapters

    prohibited_calls = []
    def forbidden(*args, **kwargs):
        prohibited_calls.append("market/model/network")
        raise AssertionError("factor read-only query attempted market/model/network work")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(llm, "load_ark_config", forbidden)
    monkeypatch.setattr(llm, "chat_discussion", forbidden)
    monkeypatch.setattr(llm, "chat_discussion_stream", forbidden)
    monkeypatch.setattr(adapters, "calculate_batch", forbidden)
    monkeypatch.setattr(factor_runtime, "monthly_decisions", forbidden)
    app = FastAPI()
    app.include_router(agent.router)
    app.include_router(copilot.router)
    app.state.plans_db_path = str(tmp_path / "chat.db")
    app.state.watchlist_db_path = app.state.plans_db_path
    app.state.analysis_service = SimpleNamespace(get=forbidden)
    app.state.factor_service = SimpleNamespace(panel=lambda: {
        "generated_at": "2020-01-02 16:30:00", "data_as_of": "2026-09-22",
        "symbols": [{"code": "510300.SS", "as_of": "2020-01-02",
                     "mom_121": 0.25, "notes": []}], "factors": {},
    })
    yield TestClient(app)
    assert prohibited_calls == [], "A prohibited operation was attempted, even if caught"


def ask(client, message="510300这只ETF当前动量如何？", **extra):
    return client.post("/api/agent/chat", json={
        "message": message, "context_kind": "symbol", "symbol": "510300.SS", **extra,
    })


def events(response):
    return [(chunk.splitlines()[0][7:], json.loads(chunk.splitlines()[1][6:]))
            for chunk in response.text.strip().split("\n\n")]


@pytest.mark.parametrize("message", [
    "510300这只ETF当前动量如何？", "这个动量因子过去真的有用吗？",
    "比较一下高点位置与普通动量。", "按动量推荐ETF并回测模块A退出1",
    "mixed.momentum.raw 是什么", "trend.price.above_ma_200@latest",
])
def test_plain_is_read_only_and_persists_evidence(client, message):
    r = ask(client, message)
    assert r.status_code == 200
    body = r.json()
    assert body["answer_state"] == "answered"
    pack = body["evidence_card"]["factor_readonly"]
    assert pack["reply"] == body["reply"]
    assert "status" in pack and "metadata" in pack and "sources" in pack
    assert body["plan_artifact"] is None and body["next_steps"] == []
    msgs = client.get(f"/api/agent/sessions/{body['session_id']}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[-1]["evidence_card"] == body["evidence_card"]
    with closing(connect(client.app.state.plans_db_path)) as conn:
        meta = json.loads(conn.execute("SELECT meta_json FROM agent_messages WHERE message_id=?",
                                       (body["question_id"],)).fetchone()[0])
    snap = meta["discussion_v1"]
    assert snap["context_kind"] == "factor_readonly"
    assert snap["rule_refs"] == [] and snap["backtest_request_ids"] == []
    assert "analysis_service" not in json.dumps(snap)


def test_stale_individual_row_is_not_latest_market_date(client):
    body = ask(client).json()
    assert "2020-01-02" in body["reply"]
    assert "不能" in body["reply"]
    assert body["resolved_symbol"] == "510300.SS"


def test_stream_uses_same_pack_and_no_model_stage(client):
    r = client.post("/api/agent/chat/stream", json={
        "message": "510300当前动量如何", "symbol": "510300.SS",
        "client_request_id": "factor-stream-1",
    })
    assert r.status_code == 200
    ev = events(r)
    done = next(data for kind, data in ev if kind == "done")
    assert done["answer_state"] == "answered"
    assert done["next_steps"] == [] and done["plan_artifact"] is None
    assert not any(k == "stage" and d["key"] in {"fetch", "llm"} for k, d in ev)
    emitted = "".join(d["t"] for k, d in ev if k == "token")
    assert emitted == done["evidence_card"]["factor_readonly"]["reply"]


def test_same_request_replay_never_reloads_panel(client):
    first = ask(client, client_request_id="factor-retry-1").json()
    def forbidden():
        raise AssertionError("replay attempted a fresh read")
    client.app.state.factor_service.panel = forbidden
    second = ask(client, client_request_id="factor-retry-1").json()
    assert second["question_id"] == first["question_id"]
    assert second["evidence_card"] == first["evidence_card"]
    assert second["reply"] == first["reply"]


def test_save_failure_resume_uses_original_frozen_materials(client, monkeypatch):
    original = agent._append_answer
    def fail_save(*args, **kwargs):
        raise RuntimeError("injected save failure")
    monkeypatch.setattr(agent, "_append_answer", fail_save)
    with pytest.raises(RuntimeError, match="injected save failure"):
        ask(client, client_request_id="factor-resume-1")
    monkeypatch.setattr(agent, "_append_answer", original)
    def no_new_read():
        raise AssertionError("resume changed the question's frozen factor material")
    client.app.state.factor_service.panel = no_new_read
    r = ask(client, client_request_id="factor-resume-1")
    assert r.status_code == 200
    assert r.json()["answer_state"] == "answered"
    assert "2020-01-02" in r.json()["reply"]


@pytest.mark.parametrize("text", [
    "推荐动量因子", "回测动量因子模块A退出1", "比较高点位置和普通动量",
])
def test_resolve_and_dispatch_do_not_start_existing_pipelines(client, text):
    r = client.post("/api/copilot/resolve", json={"message": text, "selected_symbol": "510300.SS"})
    assert r.status_code == 200
    assert r.json()["intent"] == "discussion"
    assert r.json()["discussion_context"]["factor_readonly"] is True
    dispatch = client.post("/api/copilot/dispatch", json={"message": text}).json()
    assert dispatch["chat_fallback"] is True
    assert dispatch["card"] is None and dispatch["preview"] is None


def test_factor_question_cannot_be_backtest_task(client, monkeypatch):
    from lei_signal.copilot import backtest_requests
    def forbidden(*args, **kwargs):
        raise AssertionError("factor question created or started a backtest")
    monkeypatch.setattr(backtest_requests, "create_request", forbidden)
    monkeypatch.setattr(backtest_requests, "start_request_worker", forbidden)
    first = ask(client, "帮我回测动量因子模块A退出1").json()
    r = client.post("/api/copilot/backtest-requests", json={
        "session_id": first["session_id"], "question_id": first["question_id"],
        "client_request_id": "factor-bypass", "symbol": "510300.SS",
        "module": "A", "exit_variant": "a6_1_costbasis",
    })
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "FACTOR_RESEARCH_NOT_EXECUTABLE"


def test_multiple_symbols_are_not_silently_selected(client):
    body = ask(client, "比较510300和510500的动量").json()
    assert body["resolved_symbol"] is None
    assert "510300" in body["reply"] and "510500" in body["reply"]


@pytest.mark.parametrize("followup", ["那开始回测吧", "帮我回测一下", "回测看看"])
def test_followup_keeps_factor_scope_without_auto_execution(client, followup):
    first = ask(client).json()
    args = {"session_id": first["session_id"], "symbol": "510300.SS"}
    resolved = client.post("/api/copilot/resolve", json={
        "message": followup, "session_id": first["session_id"],
        "selected_symbol": "510300.SS",
    }).json()
    assert resolved["intent"] == "discussion"
    second = ask(client, followup, **args).json()
    assert second["evidence_card"]["factor_readonly"]
    assert second["next_steps"] == []


def test_multiple_local_names_are_not_silently_selected(client):
    body = ask(client, "比较通信ETF和红利低波ETF的动量").json()
    assert body["resolved_symbol"] is None
    assert body["evidence_card"]["factor_readonly"]["status"] == "needs_clarification"
    assert "515880" in body["reply"] and "512890" in body["reply"]


def test_etf_is_not_replaced_by_same_name_index(client):
    ambiguous = ask(client, "沪深300ETF当前动量如何", symbol="510500.SS").json()
    assert ambiguous["resolved_symbol"] is None
    explicit = ask(client, "沪深300ETF（510300）当前动量如何", symbol="510500.SS").json()
    assert explicit["resolved_symbol"] == "510300.SS"


def test_panel_failure_stays_inside_read_only_boundary(client):
    def broken():
        raise ValueError("fixture broken")
    client.app.state.factor_service.panel = broken
    r = ask(client)
    assert r.status_code == 200
    assert r.json()["evidence_card"]["factor_readonly"]
    assert r.json()["plan_artifact"] is None


def test_factor_reference_is_not_a_ticker(client):
    body = ask(client, "mixed.momentum.raw@1.0.0怎么定义？", symbol=None).json()
    assert body["resolved_symbol"] is None
    explicit = ask(client, "510300的mixed.momentum.raw@1.0.0当前读数", symbol="510500.SS").json()
    assert explicit["resolved_symbol"] == "510300.SS"
