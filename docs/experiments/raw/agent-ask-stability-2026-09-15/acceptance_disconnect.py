"""S1 矩阵 5（主控复验固定要求）：隔离 HTTP 服务上的**真实客户端断开**与重试。

真实 uvicorn + httpx：模型桩慢速逐段输出；客户端读到首段正文后**断开
HTTP 连接**（r.close()）——这不是手动 close Python 生成器，而是真实 TCP
断开经 ASGI 传播。随后同 client_request_id 重试：精确核对
问题数（user 消息=1）、生成调用数（=2）与最终状态（claim=answered）。

输出：acceptance-disconnect.json。零付费模型。
运行：PYTHONPATH=<repo>/src python3 acceptance_disconnect.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
import time

os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("ARK_API_KEY", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
os.environ["GLM_API_KEY"] = "stub-key"

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from lei_signal.api.routes import agent as agent_routes  # noqa: E402
from lei_signal.plans import llm as plans_llm  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "acceptance-disconnect.json")
PORT = 8933
CID = "acc-disconnect-1"

calls = {"n": 0}


def fake_config():
    return plans_llm.ArkConfig(api_key="stub-key")


def fake_stream(payload, history, message, config):
    calls["n"] += 1
    yield "第一段正文。"
    for _ in range(200):  # 足够慢，保证断开时流远未结束
        yield "后续。"
        time.sleep(0.05)


agent_routes.plans_llm.load_ark_config = fake_config
agent_routes.plans_llm.chat_discussion_stream = fake_stream


def claim_state(db: str):
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT answer_state FROM agent_chat_requests WHERE client_request_id=?",
        (CID,)).fetchone()
    conn.close()
    return row[0] if row else None


def counts(db: str):
    conn = sqlite3.connect(db)
    q = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
    conn.close()
    return q


def main() -> None:
    db = tempfile.mktemp(suffix=".db")
    connect(db).close()
    app = FastAPI()
    app.state.analysis_service = None
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.include_router(agent_routes.router)

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="error")
    server = uvicorn.Server(config)
    srv = threading.Thread(target=server.run, daemon=True)
    srv.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)

    result: dict = {"checks": {}, "failures": 0}

    def check(name: str, ok: bool, detail: object = "") -> None:
        result["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            result["failures"] += 1

    try:
        # —— 第一次：读到首段正文后真实断开 ——
        got_token_at = None
        t0 = time.perf_counter()
        with httpx.stream(
            "POST", f"http://127.0.0.1:{PORT}/api/agent/chat/stream",
            json={"context_kind": "global", "message": "市场环境怎么样",
                  "client_request_id": CID},
            timeout=60,
        ) as r:
            buf = ""
            for chunk in r.iter_text():
                buf += chunk
                if "event: token" in buf:
                    got_token_at = round(time.perf_counter() - t0, 2)
                    break
            r.close()  # 真实 HTTP 断开
        result["first"] = {"got_token_at_s": got_token_at,
                           "model_calls_after_first": calls["n"]}
        check("got_first_token", got_token_at is not None, got_token_at)
        check("first_generation_started", calls["n"] == 1, calls["n"])

        # 断开后 claim 必须被收尾为 pending（不再卡 generating 600 秒）
        deadline = time.time() + 15
        state = None
        while time.time() < deadline:
            state = claim_state(db)
            if state == "pending":
                break
            time.sleep(0.2)
        result["state_after_disconnect"] = state
        check("claim_released_after_real_disconnect", state == "pending", state)

        # —— 同 cid 重试：立即恢复生成 ——
        t0 = time.perf_counter()
        with httpx.stream(
            "POST", f"http://127.0.0.1:{PORT}/api/agent/chat/stream",
            json={"context_kind": "global", "message": "市场环境怎么样",
                  "client_request_id": CID},
            timeout=120,
        ) as r:
            text = ""
            for chunk in r.iter_text():
                text += chunk
                if "event: done" in text:
                    break
        done = None
        for frame in text.split("\n\n"):
            if frame.startswith("event: done"):
                done = json.loads(frame.split("data: ", 1)[1])
        result["retry"] = {
            "seconds": round(time.perf_counter() - t0, 2),
            "answer_state": (done or {}).get("answer_state"),
            "model_calls": calls["n"],
            "user_messages": counts(db),
            "claim": claim_state(db),
        }
        check("retry_answered", (done or {}).get("answer_state") == "answered",
              (done or {}).get("answer_state"))
        check("model_called_twice", calls["n"] == 2, calls["n"])
        check("no_duplicate_question", counts(db) == 1, counts(db))
        check("claim_answered", claim_state(db) == "answered", claim_state(db))
    finally:
        server.should_exit = True
        srv.join(timeout=5)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({"failures": result["failures"],
                      "checks": {k: v["ok"] for k, v in result["checks"].items()}},
                     ensure_ascii=False, indent=1))
    os.unlink(db)
    sys.exit(1 if result["failures"] else 0)


if __name__ == "__main__":
    main()
