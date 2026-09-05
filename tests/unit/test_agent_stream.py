"""流式讨论端点：SSE 事件协议（stage/token/done）与降级路径。"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import agent as agent_routes
from lei_signal.plans import llm as plans_llm
from lei_signal.storage.sqlite_store import connect


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for frame in text.split("\n\n"):
        frame = frame.strip()
        if not frame:
            continue
        event, data = None, None
        for line in frame.splitlines():
            if line.startswith("event: "):
                event = line[7:].strip()
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if event and data is not None:
            events.append((event, data))
    return events


@pytest.fixture()
def app(tmp_path, monkeypatch):
    for name in ("GLM_API_KEY", "DEEPSEEK_API_KEY", "ARK_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    db = str(tmp_path / "t.db")
    connect(db).close()
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = db
    a.state.watchlist_db_path = db
    a.include_router(agent_routes.router)
    return a


def test_stream_no_llm_gives_fallback_only(app):
    with TestClient(app) as c:
        with c.stream(
            "POST", "/api/agent/chat/stream",
            json={"context_kind": "global", "message": "市场环境怎么样"},
        ) as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/event-stream")
            text = "".join(chunk for chunk in r.iter_text())
    events = _parse_sse(text)
    kinds = [e for e, _ in events]
    assert "stage" in kinds and "done" in kinds
    done = next(d for e, d in events if e == "done")
    assert done["grounded"] is False
    assert done["fallback"]  # 模板直出兜底


def test_stream_tokens_and_grounded_done(app, monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        agent_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )

    def fake_stream(payload, history, message, config):
        yield "均线多头排列"
        yield "，强度增强。"

    monkeypatch.setattr(
        agent_routes.plans_llm, "chat_discussion_stream", fake_stream
    )
    with TestClient(app) as c:
        with c.stream(
            "POST", "/api/agent/chat/stream",
            json={"context_kind": "global", "message": "随便说说"},
        ) as r:
            text = "".join(chunk for chunk in r.iter_text())
    events = _parse_sse(text)
    tokens = [d["t"] for e, d in events if e == "token"]
    assert tokens == ["均线多头排列", "，强度增强。"]
    done = next(d for e, d in events if e == "done")
    assert done["grounded"] is True
    assert "fallback" not in done


def test_stream_verify_fail_appends_fallback(app, monkeypatch):
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        agent_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )

    def fake_stream(payload, history, message, config):
        yield "建议买入 515880。"  # 禁用词，必不过校验

    monkeypatch.setattr(
        agent_routes.plans_llm, "chat_discussion_stream", fake_stream
    )
    with TestClient(app) as c:
        with c.stream(
            "POST", "/api/agent/chat/stream",
            json={"context_kind": "global", "message": "随便说说"},
        ) as r:
            text = "".join(chunk for chunk in r.iter_text())
    events = _parse_sse(text)
    done = next(d for e, d in events if e == "done")
    assert done["grounded"] is False
    assert done["verify_note"]
    assert done["fallback"]
