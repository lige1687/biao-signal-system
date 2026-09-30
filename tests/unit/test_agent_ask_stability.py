"""提问稳定性（2026-09-15 agent-ask-stability）：失败释放、等待反馈、分段计时。

固定矩阵（临时库 + 合成模型流，不发真实模型请求）：
- 提交即回执：第一个事件就是「已收到问题」；
- 持锁 ~7 秒：等待期间有「等待系统处理」心跳（不说成 AI 思考），
  释放后同一请求正常走通；
- 准备段失败（锁 30s 超时缩小为 0.5s）：done 是 answer_state=failed +
  retryable + 如实文案；claim 被释放回 pending——同 cid 立即重试成功，
  不再被「回答正在生成或重试中」挡 600 秒；
- 客户端断连：生成器 close 后 claim 释放回 pending，重试立即恢复生成；
- done 携带分段计时（received→…→answer_saved 的 marks）。
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api import ask_timing
from lei_signal.api.routes import agent as agent_routes
from lei_signal.plans import llm as plans_llm
from lei_signal.storage.sqlite_store import connect

CID = "stab-retry-1"


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
    return {"app": a, "db": db}


def _claim_state(db: str, cid: str = CID) -> str | None:
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT answer_state FROM agent_chat_requests WHERE client_request_id=?",
        (cid,)).fetchone()
    conn.close()
    return row[0] if row else None


def test_first_event_is_received_and_done_carries_timing(app):
    with TestClient(app["app"]) as c, c.stream(
        "POST", "/api/agent/chat/stream",
        json={"context_kind": "global", "message": "市场环境怎么样",
              "client_request_id": "stab-recv-1"},
    ) as r:
        text = "".join(chunk for chunk in r.iter_text())
    events = _parse_sse(text)
    assert events[0][0] == "stage"
    assert events[0][1]["key"] == "received"
    assert "已收到问题" in events[0][1]["text"]
    done = next(d for e, d in events if e == "done")
    timing = done["timing_ms"]
    marks = timing["marks_ms"]
    # 六段口径：收到→身份登记→准备→资料展示→（无模型无首字）→回答保存
    assert "received" in marks and "identity" in marks and "prepared" in marks
    assert "material_sent" in marks and "answer_saved" in marks
    assert marks["received"] <= marks["identity"] <= marks["answer_saved"]


def test_lock_hold_shows_waiting_then_succeeds_after_release(app, monkeypatch):
    """持锁 ~7 秒（小于 30s busy_timeout）：等待期间客户端收到真实阶段反馈，
    释放后同一请求正常完成——后台繁忙不再表现为「莫名失败或干等」。"""
    db = app["db"]
    holder = sqlite3.connect(db, timeout=5, check_same_thread=False)
    holder.execute("BEGIN IMMEDIATE")
    holder.execute(
        "INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES('hold-7s','v1','test')")

    def _release():
        time.sleep(7)
        holder.commit()
        holder.close()

    t = threading.Thread(target=_release)
    t.start()
    try:
        started = time.perf_counter()
        with TestClient(app["app"]) as c, c.stream(
            "POST", "/api/agent/chat/stream",
            json={"context_kind": "global", "message": "市场环境怎么样",
                  "client_request_id": "stab-lock-7s"},
        ) as r:
            text = "".join(chunk for chunk in r.iter_text())
        elapsed = time.perf_counter() - started
    finally:
        t.join()
    events = _parse_sse(text)
    kinds = [e for e, _ in events]
    assert kinds[0] == "stage" and events[0][1]["key"] == "received"
    waiting = [d for e, d in events if e == "stage" and d["key"] == "waiting"]
    assert waiting, "持锁等待期间必须有「等待系统处理」反馈"
    assert "等待系统处理" in waiting[0]["text"]
    assert "AI" not in waiting[0]["text"]  # 数据库等待不得描述成 AI 思考
    done = next(d for e, d in events if e == "done")
    assert done.get("answer_state") != "failed"  # 释放后正常走通
    assert done["session_id"]
    assert elapsed >= 6.5  # 确实等了锁
    assert _claim_state(db, "stab-lock-7s") == "answered"


def test_prepare_lock_timeout_fails_retryable_and_releases_claim(app, monkeypatch):
    """准备段等锁超时（busy_timeout 缩为 0.5s 模拟 30s 超时）：done 如实说明、
    retryable；claim 释放回 pending——同 cid 立即重试成功。"""
    from lei_signal.storage.write_tx import TrackedConnection

    def _connect_fast(path):
        c = sqlite3.connect(path, timeout=0.5, factory=TrackedConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        return c

    monkeypatch.setattr(agent_routes, "connect", _connect_fast)
    db = app["db"]
    holder = sqlite3.connect(db, timeout=5, check_same_thread=False)
    holder.execute("BEGIN IMMEDIATE")
    holder.execute(
        "INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES('hold-long','v1','test')")
    try:
        with TestClient(app["app"]) as c, c.stream(
            "POST", "/api/agent/chat/stream",
            json={"context_kind": "global", "message": "市场环境怎么样",
                  "client_request_id": CID},
        ) as r:
            text = "".join(chunk for chunk in r.iter_text())
    finally:
        holder.commit()
        holder.close()
    events = _parse_sse(text)
    done = next(d for e, d in events if e == "done")
    assert done["answer_state"] == "failed"
    assert done["retryable"] is True
    assert "database is locked" in done["verify_note"]
    assert "重试" in done["verify_note"]
    # 失败发生在登记前：无会话、无假问题落库
    assert _claim_state(db) is None

    # 锁已释放：同 cid 立即重试正常走通（不重复记录）
    with TestClient(app["app"]) as c, c.stream(
        "POST", "/api/agent/chat/stream",
        json={"context_kind": "global", "message": "市场环境怎么样",
              "client_request_id": CID},
    ) as r:
        text2 = "".join(chunk for chunk in r.iter_text())
    done2 = next(d for e, d in _parse_sse(text2) if e == "done")
    assert done2.get("answer_state") != "failed"
    conn = sqlite3.connect(db)
    q = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    conn.close()
    assert q == 1


def test_disconnect_releases_claim_and_retry_regenerates(app, monkeypatch):
    """客户端断连（生成器被 close）：claim 不卡在 generating，重试立即恢复。"""
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        agent_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )
    calls = {"n": 0}

    def fake_stream(payload, history, message, config):
        calls["n"] += 1
        yield "第一段。"
        for _ in range(50):  # 足够多片段，保证断连时流未结束
            yield "后续内容。"
            time.sleep(0.05)

    monkeypatch.setattr(
        agent_routes.plans_llm, "chat_discussion_stream", fake_stream)

    # 手动驱动生成器：读到第一个 token 后 close（等价于客户端断连）
    from starlette.requests import Request

    scope = {
        "type": "http", "method": "POST", "path": "/api/agent/chat/stream",
        "headers": [], "app": app["app"],
    }
    request = Request(scope)
    body = agent_routes.AgentChatRequest(
        context_kind="global", message="市场环境怎么样", client_request_id=CID)
    resp = agent_routes.agent_chat_stream(request, body)

    async def _drain_until_token_then_close():
        agen = resp.body_iterator.__aiter__()
        got_token = False
        while True:
            chunk = await agen.__anext__()
            if "event: token" in chunk:
                got_token = True
                break
        await agen.aclose()  # 断连：GeneratorExit 进入生成器
        return got_token

    import asyncio

    assert asyncio.run(_drain_until_token_then_close()) is True
    assert calls["n"] == 1
    # finally 释放：claim 回到 pending（不再「正在生成」挡 600 秒）
    assert _claim_state(db=app["db"]) == "pending"

    # 同 cid 重试：立即恢复生成（resume），不重复建问题
    with TestClient(app["app"]) as c, c.stream(
        "POST", "/api/agent/chat/stream",
        json={"context_kind": "global", "message": "市场环境怎么样",
              "client_request_id": CID},
    ) as r:
        text = "".join(chunk for chunk in r.iter_text())
    done = next(d for e, d in _parse_sse(text) if e == "done")
    assert done["answer_state"] == "answered"
    assert calls["n"] == 2
    conn = sqlite3.connect(app["db"])
    q = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    conn.close()
    assert q == 1


def test_ask_timing_marks_and_spans():
    tm = ask_timing.AskTiming()
    tm.mark("received")
    with tm.span("block"):
        time.sleep(0.01)
    with tm.span("block"):
        time.sleep(0.01)
    tm.mark("done")
    summary = tm.summary()
    assert summary["marks_ms"]["received"] <= summary["marks_ms"]["done"]
    assert summary["spans_ms"]["block"] >= 15  # 同名 span 累计
    assert summary["total_ms"] >= summary["marks_ms"]["done"]
    # 空实现同接口
    null = ask_timing.NULL_TIMING
    null.mark("x")
    with null.span("y"):
        pass
    assert null.summary() == {}


# ---- S1（主控复验 2026-09-15）：断开时生成权必须有人负责收尾 ----
#
# 共用约定：把 fastapi.responses.StreamingResponse 补丁为恒等函数，直接拿到
# 路由返回的同步生成器（与主控探针同一手法，隔离 HTTP 客户端缓冲），
# next() 取首条 received 后 close() 模拟消费者断开；真实 HTTP 断开由
# raw/acceptance_disconnect.py 在隔离 uvicorn 上验收（矩阵 5）。
from unittest.mock import patch  # noqa: E402

from starlette.requests import Request  # noqa: E402


def _raw_stream(app_dict, monkeypatch, cid: str, *, delay_enter=None,
                gate_prepare=None):
    """构造原始流生成器；返回 (generator, body, stop_fn)。

    补丁（enter/prepare 延迟）在 stop_fn 前保持有效——后台工作者线程
    在生成器创建后才真正调用它们。enter/prepare 包装均**一次性**
    （只延迟旧请求，不影响随后重试的新请求）。生成器不经补丁取得：
    StreamingResponse.body_iterator 即路由创建的同步生成器。"""
    scope = {
        "type": "http", "method": "POST", "path": "/api/agent/chat/stream",
        "headers": [], "app": app_dict["app"],
    }
    request = Request(scope)
    body = agent_routes.AgentChatRequest(
        context_kind="global", message="市场环境怎么样", client_request_id=cid)
    original_enter = agent_routes._enter_chat
    original_prepare = agent_routes._prepare_discussion
    used = {"enter": False, "prepare": False}
    # 旧请求的工作者已进入「等待放行」状态时置位——测试据此确保
    # 第一次调用确实属于旧请求（线程调度不定，不能靠 sleep 猜）。
    enter_waiting = threading.Event()

    def enter_wrapper(*a, **kw):
        if delay_enter is not None and not used["enter"]:
            used["enter"] = True
            enter_waiting.set()
            assert delay_enter.wait(10)
        return original_enter(*a, **kw)

    def prepare_wrapper(*a, **kw):
        if gate_prepare is not None and not used["prepare"]:
            used["prepare"] = True
            assert gate_prepare.wait(10)
        return original_prepare(*a, **kw)

    # StreamingResponse 恒等补丁只在路由调用的同步窗口内生效（与主控探针
    # 同手法），随后立即撤下——不能泄漏到随后 TestClient 重试的请求里。
    identity = patch("fastapi.responses.StreamingResponse",
                     lambda content, **kw: content)
    patches = []
    if delay_enter is not None:
        patches.append(patch.object(agent_routes, "_enter_chat", enter_wrapper))
    if gate_prepare is not None:
        patches.append(patch.object(
            agent_routes, "_prepare_discussion", prepare_wrapper))
    for p in patches:
        p.start()

    def _stop():
        for p in patches:
            p.stop()

    identity.start()
    try:
        gen = agent_routes.agent_chat_stream(request, body)
    finally:
        identity.stop()
    return gen, body, _stop, enter_waiting


def _wait_claim(db: str, cid: str, timeout: float = 10.0) -> str:
    """轮询 claim 直到出现并返回 answer_state。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT answer_state FROM agent_chat_requests"
            " WHERE client_request_id=?", (cid,)).fetchone()
        conn.close()
        if row:
            return row[0]
        time.sleep(0.05)
    raise AssertionError(f"claim {cid} 未出现")


def _wait_claim_state(db: str, cid: str, want: str,
                      timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = _claim_state(db, cid)
        if state == want:
            return
        time.sleep(0.05)
    raise AssertionError(f"claim {cid} 未到 {want}（当前 {_claim_state(db, cid)}）")


def test_s1_disconnect_before_identity_late_claim_released(app, monkeypatch):
    """矩阵 1：回执后、领号前断开；随后允许领号完成——工作者晚领号也收尾，
    原请求可立即重试（主控探针场景复测）。"""
    cid = "s1-early-close"
    gate = threading.Event()
    gen, body, stop, enter_waiting = _raw_stream(
        app, monkeypatch, cid, delay_enter=gate)
    try:
        first = next(gen)
        assert "已收到问题" in first
        assert enter_waiting.wait(10)  # 旧工作者已堵在登记（第一次调用归它）
        gen.close()          # 消费者在领号前断开
        gate.set()           # 现在允许后台真实登记完成
        _wait_claim_state(app["db"], cid, "pending")  # 晚领号被收尾，非 generating

        retry = agent_routes._enter_chat(_request_for(app), body)
        assert retry.kind == "proceed"  # 立即恢复，不再「正在生成」
    finally:
        stop()


def _request_for(app_dict):
    return Request({
        "type": "http", "method": "POST", "path": "/", "headers": [],
        "app": app_dict["app"],
    })


def test_s1_disconnect_with_entered_unread_released(app, monkeypatch):
    """矩阵 2：领号成功但消费者未读 entered 就断开——claim 同样收尾。"""
    cid = "s1-entered-unread"
    gate_prepare = threading.Event()
    gen, body, stop, _ew = _raw_stream(app, monkeypatch, cid,
                                       gate_prepare=gate_prepare)
    try:
        first = next(gen)
        assert "已收到问题" in first
        # 等领号完成（claim 已 generating），entered 事件在队列里消费者不读
        assert _wait_claim(app["db"], cid) == "generating"
        gen.close()           # 消费者断开：finally 按共享状态收尾
        _wait_claim_state(app["db"], cid, "pending")
        gate_prepare.set()    # 工作者完成准备；无消费者不启动生成
        retry = agent_routes._enter_chat(_request_for(app), body)
        assert retry.kind == "proceed"
    finally:
        stop()


def test_s1_disconnect_during_prepare_then_retry(app, monkeypatch):
    """矩阵 3a：准备资料期间断开——收尾后同 cid 重试正常完成，问题不重复。"""
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        agent_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )
    calls = {"n": 0}

    def fake_stream(payload, history, message, config):
        calls["n"] += 1
        yield "完整回答，按系统资料说。"

    monkeypatch.setattr(
        agent_routes.plans_llm, "chat_discussion_stream", fake_stream)
    cid = "s1-mid-prepare"
    gate_prepare = threading.Event()
    gen, _body, stop, _ew = _raw_stream(app, monkeypatch, cid,
                                        gate_prepare=gate_prepare)
    try:
        next(gen)
        assert _wait_claim(app["db"], cid) == "generating"
        gen.close()
        _wait_claim_state(app["db"], cid, "pending")
        gate_prepare.set()
    finally:
        stop()

    with TestClient(app["app"]) as c, c.stream(
        "POST", "/api/agent/chat/stream",
        json={"context_kind": "global", "message": "市场环境怎么样",
              "client_request_id": cid},
    ) as r:
        text = "".join(chunk for chunk in r.iter_text())
    done = next(d for e, d in _parse_sse(text) if e == "done")
    assert done["answer_state"] == "answered"
    assert calls["n"] == 1  # 断开的旧请求没有启动生成
    conn = sqlite3.connect(app["db"])
    q = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    conn.close()
    assert q == 1


def test_s1_late_worker_does_not_touch_retry_claim(app, monkeypatch):
    """矩阵 4：旧请求断开后其工作者仍堵在登记；重试已领号并完成——
    旧工作者迟到完成不得释放重试者的生成权、不得新增重复问题。"""
    monkeypatch.setenv("GLM_API_KEY", "k")
    monkeypatch.setattr(
        agent_routes.plans_llm, "load_ark_config",
        lambda: plans_llm.ArkConfig(api_key="k"),
    )
    calls = {"n": 0}

    def fake_stream(payload, history, message, config):
        calls["n"] += 1
        yield "重试后的完整回答。"

    monkeypatch.setattr(
        agent_routes.plans_llm, "chat_discussion_stream", fake_stream)
    cid = "s1-late-worker"
    gate = threading.Event()
    # 旧请求：received 后即断开，但其工作者仍堵在 _enter_chat
    gen, _body, stop, enter_waiting = _raw_stream(
        app, monkeypatch, cid, delay_enter=gate)
    next(gen)
    assert enter_waiting.wait(10)  # 旧工作者已堵在登记（第一次调用归它）
    gen.close()

    # 重试（同 cid）在旧工作者登记之前完成整轮
    with TestClient(app["app"]) as c, c.stream(
        "POST", "/api/agent/chat/stream",
        json={"context_kind": "global", "message": "市场环境怎么样",
              "client_request_id": cid},
    ) as r:
        text = "".join(chunk for chunk in r.iter_text())
    done = next(d for e, d in _parse_sse(text) if e == "done")
    assert done["answer_state"] == "answered"
    assert calls["n"] == 1

    gate.set()  # 旧工作者现在才完成登记：撞主键→replay/incomplete 出口
    stop()
    time.sleep(0.5)  # 给旧工作者收尾时间
    assert _claim_state(app["db"], cid) == "answered"  # 重试者终态未被触碰
    conn = sqlite3.connect(app["db"])
    q = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    a = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='assistant'").fetchone()[0]
    conn.close()
    assert q == 1 and a == 1  # 不重复问题、不重复回答
