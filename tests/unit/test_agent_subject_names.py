"""对象不是替代品：真实路由 + 临时库 + 固定板块快照，无模型/行情请求。"""

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import agent, copilot
from lei_signal.copilot import subjects
from lei_signal.plans.sessions import create_session
from lei_signal.storage.sqlite_store import connect


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    (tmp_path / "sector_trend_snapshot.json").write_text(
        json.dumps(
            {
                "date": "2026-09-10",
                "generated_at": "2026-09-15",
                "boards": [
                    {
                        "code": "BK1215",
                        "name": "通信",
                        "level": 1,
                        "stage": "distribution",
                        "close": 123,
                        "b50": 62,
                        "next_watch": "观察均线方向",
                    },
                    {"code": "BK0448", "name": "通信设备", "level": 2},
                ],
            }
        )
    )
    db = str(tmp_path / "app.db")
    connect(db).close()
    a = FastAPI()
    a.state.plans_db_path = db
    a.state.watchlist_db_path = db

    # 用了ETF分析器就直接失败，防假通过。
    def forbidden(*a, **kw):
        raise AssertionError("板块问题不应调用个券分析或行情")

    a.state.analysis_service = SimpleNamespace(get=forbidden)
    a.include_router(agent.router)
    a.include_router(copilot.router)
    return a


@pytest.mark.parametrize(
    "text,want",
    [
        ("通信板块最近如何看", "BK1215.SECTOR"),
        ("通信版块最近如何看", "BK1215.SECTOR"),
        ("通信设备板块怎么看", "BK0448.SECTOR"),
        ("通信ETF怎么看", "515880.SS"),
        ("515880.SS最近如何", "515880.SS"),
        ("BK1215.SECTOR怎么看", "BK1215.SECTOR"),
    ],
)
def test_resolve_ignores_selected_etf(app, text, want):
    with TestClient(app) as c:
        r = c.post("/api/copilot/resolve", json={"message": text, "selected_symbol": "510300.SS"})
    assert r.status_code == 200
    assert r.json()["resolved_symbol"] == want
    assert r.json()["display_name"]


def test_name_placeholder_is_not_real_name(app):
    assert agent._static_symbol_name("515880.SS", "515880.SS") == "通信ETF"
    assert subjects.subject_label("515880.SS") == "通信ETF（515880.SS）"
    assert subjects.subject_label("999999.SS") == "名称待核实（999999.SS）"


def test_sector_preparation_uses_snapshot_not_trade_pipeline(app):
    with connect(app.state.plans_db_path) as conn:
        session = create_session(conn, "515880.SS", "测试")
    request = SimpleNamespace(app=app)
    body = agent.AgentChatRequest(
        message="通信版块最近如何看", context_kind="symbol", symbol="515880.SS"
    )
    result = agent._prepare_discussion(request, body, session_id=session.session_id)
    ctx = result[2]
    assert result[4] == "BK1215.SECTOR"
    assert ctx["display_name"] == "通信"
    assert ctx["as_of"] == "2026-09-10"
    assert ctx["sector"]["b50"] == 62
    assert "buy_point_candidate_n" not in ctx["evidence_card"]["facts"]
    assert all(s["kind"] == "expand_evidence" for s in agent._build_next_steps(ctx, result[4]))
    assert "ETF" in ctx["subject_note_cn"]


def test_missing_sector_never_substitutes_etf(app, monkeypatch, tmp_path):
    (tmp_path / "sector_trend_snapshot.json").unlink()
    assert subjects.named_subject("通信板块怎么看") == "BK1215.SECTOR"
    ctx = subjects.sector_context("BK1215.SECTOR")
    assert ctx["data_available"] is False and ctx["as_of"] is None
    with TestClient(app) as c:
        r = c.post(
            "/api/copilot/resolve",
            json={"message": "不存在的板块怎么看", "selected_symbol": "515880.SS"},
        )
    assert r.json()["resolved_symbol"] is None


def test_sector_stream_and_history_keep_named_subject(app, monkeypatch):
    monkeypatch.setattr(agent.plans_llm, "load_ark_config", lambda: None)
    with TestClient(app) as c:
        r = c.post(
            "/api/agent/chat/stream",
            json={
                "message": "通信版块最近如何看",
                "context_kind": "symbol",
                "symbol": "515880.SS",
                "client_request_id": "sector-case",
            },
        )
        assert r.status_code == 200
        frames = []
        for frame in r.text.split("\n\n"):
            lines = frame.splitlines()
            event = next((x[7:] for x in lines if x.startswith("event: ")), None)
            data = next((json.loads(x[6:]) for x in lines if x.startswith("data: ")), None)
            if event:
                frames.append((event, data))
        prepared = next(d for e, d in frames if e == "prepared")
        done = next(d for e, d in frames if e == "done")
        assert prepared["resolved_symbol"] == done["resolved_symbol"] == "BK1215.SECTOR"
        assert prepared["evidence_card"]["facts"]["display_name"] == "通信"
        history = c.get(f"/api/agent/sessions/{done['session_id']}/messages").json()
        answer = history[-1]
        assert answer["evidence_card"]["facts"]["display_name"] == "通信"
        assert answer["evidence_card"]["facts"]["as_of"] == "2026-09-10"
        assert "通信" in answer["content"]
    with connect(app.state.plans_db_path) as conn:
        assert conn.execute("select count(*) from trade_plans").fetchone()[0] == 0
