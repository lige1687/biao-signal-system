"""固定验收 A（任务书§四）：模拟持锁 35 秒（真实 uvicorn 服务 + httpx 流）。

注意：starlette TestClient 会缓冲 SSE（事件全部在结束时才到达），不能用来
验证「及时反馈」——本验收因此用真实 uvicorn + httpx.stream（生产同一
ASGI 服务器）。临时库、无模型（fallback 模板路径）、不发任何模型请求。

场景：
1. 另一连接 BEGIN IMMEDIATE 持写锁 35 秒（超过 busy_timeout 30 秒）；
2. 锁已持 1 秒后发出提问：断言「已收到问题」秒到、等待期间有
   「等待系统处理」心跳（不说成 AI 思考）；
3. ~30 秒请求超时失败：done 如实（database is locked + 重试入口）、
   answer_state=failed、retryable=true、问题不落假记录；
4. 释放锁后同 client_request_id 重试：成功、user 消息恰好 1 条、
   claim 终态 answered；
5. 冷启动与同编号重放耗时分别记录。

输出：acceptance-lock35.json。运行：PYTHONPATH=<repo>/src python3 acceptance_lock35.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
import time

os.environ.pop("GLM_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("ARK_API_KEY", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402

from lei_signal.api.routes import agent as agent_routes  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "acceptance-lock35.json")
PORT = 8931
HOLD_SECONDS = 35
CID_LOCK = "acc-lock35-1"
CID_COLD = "acc-cold-1"


def parse_sse_frames(buffer: str) -> tuple[list[tuple[str, dict]], str]:
    """解析累积缓冲里**完整**的 SSE 帧；返回 (帧列表, 未消费残余)。"""
    events: list[tuple[str, dict]] = []
    rest = buffer
    while "\n\n" in rest:
        frame, rest = rest.split("\n\n", 1)
        ev, data = None, None
        for line in frame.splitlines():
            if line.startswith("event: "):
                ev = line[7:].strip()
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    data = None
        if ev:
            events.append((ev, data or {}))
    return events, rest


def stream_events(message: str, cid: str) -> tuple[list[tuple[str, dict, float]], float]:
    """真实流式读取：返回 ((event, data, 到达时刻秒), 总耗时)。"""
    got: list[tuple[str, dict, float]] = []
    t0 = time.perf_counter()
    with httpx.stream(
        "POST", f"http://127.0.0.1:{PORT}/api/agent/chat/stream",
        json={"context_kind": "global", "message": message,
              "client_request_id": cid},
        timeout=120,
    ) as r:
        buf = ""
        for chunk in r.iter_text():
            buf += chunk
            frames, buf = parse_sse_frames(buf)
            for ev, data in frames:
                got.append((ev, data, time.perf_counter() - t0))
    return got, time.perf_counter() - t0


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

    result: dict = {"hold_seconds": HOLD_SECONDS, "checks": {}, "failures": 0}

    def check(name: str, ok: bool, detail: object = "") -> None:
        result["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            result["failures"] += 1

    try:
        # ---- 场景一：持锁 35 秒 ----
        holder = sqlite3.connect(db, timeout=5, check_same_thread=False)
        holder.execute("BEGIN IMMEDIATE")
        holder.execute(
            "INSERT INTO rule_registry(rule_id, rule_version, provenance)"
            " VALUES('acc-lock35','v1','acceptance')")

        def _release():
            time.sleep(HOLD_SECONDS)
            holder.commit()
            holder.close()

        t = threading.Thread(target=_release)
        t.start()
        time.sleep(1.0)  # 锁已持 1 秒后才发提问（模拟「后台繁忙时提问」）
        try:
            got, waited = stream_events("市场环境怎么样", CID_LOCK)
        finally:
            t.join()
        timeline = [{"t": round(ts, 2), "event": ev,
                     "key": d.get("key"),
                     "text": (d.get("text") or d.get("verify_note") or "")[:90],
                     "answer_state": d.get("answer_state"),
                     "retryable": d.get("retryable")}
                    for ev, d, ts in got]
        result["lock35"] = {"waited_total_s": round(waited, 2),
                            "timeline": timeline}

        check("first_event_received_fast",
              bool(got) and got[0][0] == "stage"
              and got[0][1].get("key") == "received" and got[0][2] < 5,
              timeline[0] if timeline else "no events")
        waiting = [(ev, d, ts) for ev, d, ts in got
                   if ev == "stage" and d.get("key") == "waiting"]
        check("waiting_heartbeats_during_hold",
              len(waiting) >= 3
              and all("等待系统处理" in d.get("text", "") for _, d, _ in waiting)
              and waiting[0][2] < 10,
              f"{len(waiting)} heartbeats, first at "
              f"{waiting[0][2] if waiting else None}s")
        check("waiting_not_described_as_ai",
              all("AI" not in d.get("text", "") for _, d, _ in waiting),
              "no AI wording in waiting heartbeats")
        dones = [(d, ts) for ev, d, ts in got if ev == "done"]
        check("fails_after_busy_timeout_before_release",
              dones and 25 < dones[-1][1] < HOLD_SECONDS,
              dones[-1][1] if dones else "no done")
        done1 = dones[-1][0] if dones else {}
        check("failed_done_truthful_and_retryable",
              done1.get("answer_state") == "failed"
              and done1.get("retryable") is True
              and "database is locked" in (done1.get("verify_note") or "")
              and "重试" in (done1.get("verify_note") or ""),
              {"answer_state": done1.get("answer_state"),
               "retryable": done1.get("retryable"),
               "note": (done1.get("verify_note") or "")[:60]})
        result["lock35"]["done_payload"] = {
            "answer_state": done1.get("answer_state"),
            "retryable": done1.get("retryable"),
            "verify_note": done1.get("verify_note"),
            "timing_ms": done1.get("timing_ms"),
        }

        # ---- 场景二：释放后同 cid 重试 ----
        got2, retry_s = stream_events("市场环境怎么样", CID_LOCK)
        done2 = next((d for ev, d, _ in got2 if ev == "done"), {})
        result["retry_after_release"] = {
            "seconds": round(retry_s, 2),
            "answer_state": done2.get("answer_state"),
            "timing_ms": done2.get("timing_ms"),
        }
        check("retry_succeeds_after_release",
              done2.get("answer_state") not in ("failed", None)
              and bool(done2.get("session_id")),
              done2.get("answer_state"))
        conn = sqlite3.connect(db)
        q = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0]
        claim = conn.execute(
            "SELECT answer_state FROM agent_chat_requests WHERE client_request_id=?",
            (CID_LOCK,)).fetchone()
        conn.close()
        check("no_duplicate_question", q == 1, f"user messages={q}")
        check("claim_answered", claim and claim[0] == "answered",
              claim[0] if claim else None)

        # ---- 场景三：冷启动 vs 同编号重放 ----
        got3, cold_s = stream_events("市场环境怎么样", CID_COLD)
        done3 = next((d for ev, d, _ in got3 if ev == "done"), {})
        got4, replay_s = stream_events("市场环境怎么样", CID_COLD)
        done4 = next((d for ev, d, _ in got4 if ev == "done"), {})
        result["cold_vs_replay"] = {
            "cold_seconds": round(cold_s, 2),
            "cold_timing_ms": done3.get("timing_ms"),
            "replay_seconds": round(replay_s, 2),
            "replayed": done4.get("replayed"),
            "replay_timing_ms": done4.get("timing_ms"),
        }
        check("cold_completed", done3.get("answer_state") == "answered",
              done3.get("answer_state"))
        check("replay_is_replay", done4.get("replayed") is True,
              done4.get("replayed"))
        check("replay_much_faster", replay_s < cold_s,
              f"cold={cold_s:.2f}s replay={replay_s:.2f}s")
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
