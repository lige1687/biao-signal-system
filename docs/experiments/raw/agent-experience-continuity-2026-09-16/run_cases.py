"""固定案例执行器（agent-experience-continuity-2026-09-16）。

按 inputs-and-acceptance.md 冻结的案例链，镜像前端真实流程打隔离服务：
每条消息先 /api/copilot/resolve（记录意图路由），再按动作走
stream 讨论 / 非流式补测建档 / dispatch。逐事件记录到达时刻：
提交回执(首事件) / 资料出现(prepared) / 正文首字(首 token) / 完整回答(done)。

合成标记：本脚本产出一律带 synthetic=True——只证明工程行为（路由、对象、
日期字段、状态机、计时链路），不证明真实模型表达质量。

用法：python3 run_cases.py --base http://127.0.0.1:8022 --out baseline-degraded.json
"""
from __future__ import annotations

import argparse
import json
import time
import uuid

import requests

CHAIN_A = [
    ("case1", "通信板块最近怎么看？"),
    ("case2", "有哪些对应的ETF？"),
    ("case3", "就看515880，现在怎么看？"),
    ("case4", "先别买，什么情况值得再看？"),
    ("case5", "刚才那个依据够吗，不够补测。"),
    ("case6", "我已经持有了。"),
    ("case7", "我有一万元，能不能买一点？"),
    ("case8", "和刚才相比有什么变化？"),
]
CASE_B = [
    ("case10a", "科创板整体怎么看？"),
    ("case10b", "科创50板块怎么看？"),
]


def _cid() -> str:
    return str(uuid.uuid4())


def resolve(base: str, message: str, session_id: str | None, symbol: str | None) -> dict:
    r = requests.post(f"{base}/api/copilot/resolve", json={
        "message": message, "client_request_id": _cid(),
        "session_id": session_id, "selected_symbol": symbol,
    }, timeout=60)
    return {"status": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:500]}


def stream_chat(base: str, message: str, session_id: str | None, symbol: str | None,
                context_kind: str, abort_after_first: bool = False,
                fixed_cid: str | None = None) -> dict:
    """走 /agent/chat/stream，逐事件计时。abort_after_first=True 模拟
    回执后客户端立刻断开（生成中断重试场景 9c 的前半）。"""
    cid = fixed_cid or _cid()
    t0 = time.monotonic()
    marks: dict[str, float] = {}
    events: list[dict] = []
    done: dict | None = None
    received_text = ""
    aborted = False
    with requests.post(f"{base}/api/agent/chat/stream", json={
        "session_id": session_id, "context_kind": context_kind,
        "symbol": symbol, "message": message, "client_request_id": cid,
    }, stream=True, timeout=(10, 300)) as resp:
        resp.encoding = "utf-8"
        etype = None
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                etype = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            try:
                data = json.loads(line[5:])
            except ValueError:
                continue
            now = time.monotonic() - t0
            if "received" not in marks:
                marks["received"] = now
            if etype == "prepared" and "prepared" not in marks:
                marks["prepared"] = now
            if etype == "token":
                if "first_token" not in marks:
                    marks["first_token"] = now
                received_text += str(data.get("t") or "")
            if etype == "done":
                marks["done"] = now
                done = data
            events.append({"event": etype, "t": round(now, 3),
                           "data": data if etype in ("prepared", "done", "error") else
                           ({"key": data.get("key"), "text": data.get("text")} if etype == "stage" else {})})
            if abort_after_first:
                aborted = True
                break  # 关流=客户端断开
    return {"client_request_id": cid, "marks_ms": {k: round(v * 1000, 1) for k, v in marks.items()},
            "received_text": received_text, "done": done, "events": events, "aborted": aborted}


def plain_chat(base: str, message: str, session_id: str | None, symbol: str | None,
               context_kind: str) -> dict:
    """补测建档路径（handleBacktest 同款非流式 /agent/chat）。"""
    t0 = time.monotonic()
    r = requests.post(f"{base}/api/agent/chat", json={
        "session_id": session_id, "context_kind": context_kind,
        "symbol": symbol, "message": message, "client_request_id": _cid(),
    }, timeout=300)
    return {"status": r.status_code, "elapsed_ms": round((time.monotonic() - t0) * 1000, 1),
            "body": r.json()}


def session_messages(base: str, session_id: str) -> dict:
    r = requests.get(f"{base}/api/agent/sessions/{session_id}/messages", timeout=60)
    return {"status": r.status_code, "body": r.json()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8022")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result: dict = {"synthetic": True, "base": args.base, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "chain_A": [], "case9": {}, "case_B": []}

    # ---- 案例链 A：同一会话顺序提问（全局入口，context_kind=global 起步）----
    sid: str | None = None
    symbol: str | None = None
    for case_id, message in CHAIN_A:
        rz = resolve(args.base, message, sid, symbol)
        rbody = rz["body"] if isinstance(rz["body"], dict) else {}
        intent = rbody.get("intent")
        resolved_symbol = rbody.get("resolved_symbol")
        eff_symbol = resolved_symbol or symbol
        rec: dict = {"case": case_id, "message": message,
                     "resolve": {"intent": intent, "topic": rbody.get("topic"),
                                 "resolved_symbol": resolved_symbol,
                                 "clarification": rbody.get("clarification"),
                                 "need_clarification": rbody.get("need_clarification")}}
        if intent == "backtest_request":
            rec["chat"] = plain_chat(args.base, message, sid, eff_symbol,
                                     "symbol" if eff_symbol else "global")
            body = rec["chat"]["body"]
            sid = body.get("session_id") or sid
            symbol = body.get("resolved_symbol") or symbol
            rec["setup_panel_would_open"] = bool(body.get("question_id") and body.get("resolved_symbol"))
        else:
            st = stream_chat(args.base, message, sid, eff_symbol,
                             "symbol" if eff_symbol else "global")
            rec["stream"] = st
            d = st.get("done") or {}
            sid = d.get("session_id") or sid
            symbol = d.get("resolved_symbol") or symbol
        rec["session_id"] = sid
        rec["current_symbol"] = symbol
        result["chain_A"].append(rec)

    # ---- 案例 9a：切标的（515880 → 通信板块）再切回，检查不串对象 ----
    st = stream_chat(args.base, "通信板块最近怎么看？", None, None, "global")
    result["case9"]["switch_sector"] = st
    # ---- 案例 9b：刷新恢复——拉案例链 A 的会话历史 ----
    if sid:
        result["case9"]["reload_session_A"] = session_messages(args.base, sid)
    # ---- 案例 9c：回执后立刻断开，再同 cid 重试 ----
    first = stream_chat(args.base, "515880 的筹码分布现在什么情况？", sid, "515880.SS",
                        "symbol", abort_after_first=True)
    retry = stream_chat(args.base, "515880 的筹码分布现在什么情况？", sid, "515880.SS",
                        "symbol", fixed_cid=first["client_request_id"])
    result["case9"]["abort_first"] = first
    result["case9"]["retry_same_cid"] = retry

    # ---- 案例 B：名称身份（独立会话）----
    for case_id, message in CASE_B:
        rz = resolve(args.base, message, None, None)
        rbody = rz["body"] if isinstance(rz["body"], dict) else {}
        eff = rbody.get("resolved_symbol")
        st = stream_chat(args.base, message, None, eff, "symbol" if eff else "global")
        result["case_B"].append({"case": case_id, "message": message,
                                 "resolve": {"intent": rbody.get("intent"),
                                             "resolved_symbol": rbody.get("resolved_symbol"),
                                             "clarification": rbody.get("clarification")},
                                 "stream": st})

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"WROTE {args.out}")


if __name__ == "__main__":
    main()
