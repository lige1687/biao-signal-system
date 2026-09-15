"""主控复核 2026-09-15 固定补修二：未完成回答的持久化与同身份重试。

固定矩阵：正文中断→当时提示→刷新/历史仍未完成→同 client_request_id 重试
确实再调用→成功后原问题不增加且可恢复最终结果；并发重复重试不重复生成；
正常完成重试继续只回放；资料卡（prepared）保留。全部走真实 FastAPI 路由
与临时 SQLite，合成模型流，不发任何真实模型请求。
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import agent as agent_routes
from lei_signal.copilot.chat_identity import enter_chat_request, chat_request_hash
from lei_signal.plans import llm as plans_llm
from lei_signal.storage.sqlite_store import connect

CID = "fix2-retry-1"


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
def env(tmp_path, monkeypatch):
    for name in ("GLM_API_KEY", "DEEPSEEK_API_KEY", "ARK_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        agent_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )
    db = str(tmp_path / "t.db")
    connect(db).close()
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = db
    a.state.watchlist_db_path = db
    a.include_router(agent_routes.router)
    calls = {"n": 0}
    state = {"mode": "interrupt"}

    def fake_stream(payload, history, message, config):
        calls["n"] += 1
        if state["mode"] == "interrupt":
            yield "按系统资料，先观察。"
            yield plans_llm.StreamInterrupt("connection_interrupted")
        else:
            yield "完整的回答正文，按系统资料先说结论。"

    monkeypatch.setattr(agent_routes.plans_llm, "chat_discussion_stream", fake_stream)
    with TestClient(a) as c:
        yield {"client": c, "db": db, "calls": calls, "state": state}


def _post_stream(client: TestClient):
    with client.stream(
        "POST", "/api/agent/chat/stream",
        json={"context_kind": "global", "message": "随便说说",
              "client_request_id": CID},
    ) as r:
        return _parse_sse("".join(chunk for chunk in r.iter_text()))


def _request_row(db: str) -> dict:
    import sqlite3
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = dict(conn.execute(
        "SELECT * FROM agent_chat_requests WHERE client_request_id=?", (CID,)).fetchone())
    conn.close()
    return row


def test_interrupt_then_retry_regenerates_same_question(env):
    client, db, calls = env["client"], env["db"], env["calls"]

    # —— 第一次：正文中断 ——
    events = _post_stream(client)
    kinds = [e for e, _ in events]
    assert "prepared" in kinds  # 资料卡先显保留
    done = next(d for e, d in events if e == "done")
    assert done["answer_state"] == "incomplete"
    assert "未完成" in done["verify_note"]
    tokens = [d["t"] for e, d in events if e == "token"]
    assert tokens == ["按系统资料，先观察。"]
    assert calls["n"] == 1

    # 当时落库：claim=incomplete，部分原文 meta 带未完成原因
    row = _request_row(db)
    assert row["answer_state"] == "incomplete"
    import sqlite3
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    answers = [dict(r) for r in conn.execute(
        "SELECT * FROM agent_messages WHERE role='assistant'")]
    questions = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    conn.close()
    assert len(answers) == 1 and questions == 1
    meta = json.loads(answers[0]["meta_json"])
    assert meta["answer_incomplete"]["reason"] == "connection_interrupted"

    # —— 刷新/历史路径：messages API 明确给出未完成标记 + 可核实重试身份 ——
    sid = done["session_id"]
    msgs = client.get(f"/api/agent/sessions/{sid}/messages").json()
    assistant = [m for m in msgs if m["role"] == "assistant"]
    assert assistant[0]["answer_incomplete"]["reason"] == "connection_interrupted"
    # 二轮复验遗漏二：历史投影可核实的原问题重试身份（cid+原始消息），不是猜的
    assert assistant[0]["retry"]["client_request_id"] == CID
    assert assistant[0]["retry"]["message"] == "随便说说"

    # —— 同 cid 重试：确实再调用模型，原问题不增加 ——
    env["state"]["mode"] = "ok"
    events2 = _post_stream(client)
    done2 = next(d for e, d in events2 if e == "done")
    assert done2["answer_state"] == "answered"
    assert "fallback" not in done2
    assert calls["n"] == 2  # 重试真的再生成
    assert done2["question_id"] == done["question_id"]  # 原问题
    conn = sqlite3.connect(db)
    q_after = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    answers_after = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='assistant'").fetchone()[0]
    final_meta = json.loads(conn.execute(
        "SELECT meta_json FROM agent_messages WHERE role='assistant' "
        "ORDER BY message_id DESC LIMIT 1").fetchone()[0])
    conn.close()
    assert q_after == 1  # 原问题不增加
    assert answers_after == 2  # 旧部分原文保留 + 新完整回答
    assert "answer_incomplete" not in final_meta  # 最终结果可区分
    assert _request_row(db)["answer_state"] == "answered"

    # —— 已完成问题保护：回答完成后，历史不再投影重试身份（含旧部分原文行） ——
    msgs2 = client.get(f"/api/agent/sessions/{sid}/messages").json()
    assert all(m.get("retry") is None for m in msgs2 if m["role"] == "assistant")

    # —— 正常完成后的重试：只回放，不再调用 ——
    events3 = _post_stream(client)
    kinds3 = [e for e, _ in events3]
    done3 = next(d for e, d in events3 if e == "done")
    assert done3.get("replayed") is True or calls["n"] == 2
    assert calls["n"] == 2
    assert "token" not in kinds3 or done3.get("replayed") is True


def test_legacy_incomplete_without_identity_not_retryable(env):
    """旧记录：meta 带未完成标记但无来源编号——只有标签，明确不可原问题重试。"""
    import sqlite3
    client, db = env["client"], env["db"]
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO agent_sessions (session_id, symbol, title_cn, created_at,"
        " last_active_at) VALUES ('sess_legacy', NULL, '旧', '2026-01-01', '2026-01-01')")
    conn.execute(
        "INSERT INTO agent_messages (session_id, role, content, grounded,"
        " meta_json, created_at, question_id, message_kind, source_request_id)"
        " VALUES ('sess_legacy','assistant','半句话',0,?, '2026-01-01',1,'','')",
        (json.dumps({"answer_incomplete": {"reason": "legacy"}}),))
    conn.commit()
    conn.close()
    msgs = client.get("/api/agent/sessions/sess_legacy/messages").json()
    assistant = [m for m in msgs if m["role"] == "assistant"]
    assert assistant[0]["answer_incomplete"] is not None
    assert assistant[0]["retry"] is None  # 不可考=不伪造重试身份


def test_concurrent_retry_claimed_once_at_identity_layer(tmp_path):
    """并发重复重试：incomplete→generating 的 CAS 只有一个胜出。"""
    db = str(tmp_path / "c.db")
    conn = connect(db)
    h = chat_request_hash(message="问", context_kind="global", symbol=None)
    outcome = enter_chat_request(
        conn, client_request_id="cc1", request_hash=h, session_id=None,
        new_session_symbol=None, new_session_title="t")
    assert outcome.kind == "proceed"
    from lei_signal.copilot.chat_identity import (
        attach_question_to_claim, mark_incomplete,
    )
    # 真实时序：问题落库后回填问题号，回答未完成收场后标记 incomplete
    attach_question_to_claim(conn, "cc1", question_id=5)
    mark_incomplete(conn, "cc1", message_id=1)
    # 两个并发重试：一个领到生成权，另一个得到未完成出口
    o1 = enter_chat_request(
        conn, client_request_id="cc1", request_hash=h, session_id=None,
        new_session_symbol=None, new_session_title="t")
    o2 = enter_chat_request(
        conn, client_request_id="cc1", request_hash=h, session_id=None,
        new_session_symbol=None, new_session_title="t")
    kinds = {o1.kind, o2.kind}
    assert "resume" in kinds and "incomplete" in kinds
    conn.close()
