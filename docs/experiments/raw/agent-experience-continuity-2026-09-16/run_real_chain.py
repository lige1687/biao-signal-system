"""真实模型连续追问链（2026-09-16，执行书 §6 授权范围内：最多 6 次新增请求）。

逐次计数：流式路径每题恰好 1 次模型请求（无重试分支），results 里
model_request_no 逐题登记。问题集：案例 1/3/4/6/7（表达关键链；2/8 已改
确定性作答不走模型，5 是工程链路）。
"""
from __future__ import annotations

import json
import time
import uuid

import requests

BASE = "http://127.0.0.1:8022"
QUESTIONS = [
    ("case1", "通信板块最近怎么看？"),
    ("case3", "就看515880，现在怎么看？"),
    ("case4", "先别买，什么情况值得再看？"),
    ("case6", "我已经持有了。"),
    ("case7", "我有一万元，能不能买一点？"),
]

results = []
sid = None
symbol = None
req_no = 0
for case_id, message in QUESTIONS:
    req_no += 1  # 流式路径每题一次模型请求
    t0 = time.monotonic()
    marks: dict[str, float] = {}
    text = ""
    done = None
    with requests.post(f"{BASE}/api/agent/chat/stream", json={
        "session_id": sid, "context_kind": "symbol" if symbol else "global",
        "symbol": symbol, "message": message, "client_request_id": str(uuid.uuid4()),
    }, stream=True, timeout=(15, 600)) as r:
        et = None
        for line in r.iter_lines(decode_unicode=True):
            if line.startswith("event:"):
                et = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            d = json.loads(line[5:])
            now = time.monotonic() - t0
            if "received" not in marks:
                marks["received"] = now
            if et == "prepared" and "prepared" not in marks:
                marks["prepared"] = now
            if et == "token":
                if "first_token" not in marks:
                    marks["first_token"] = now
                text += str(d.get("t") or "")
            if et == "done":
                marks["done"] = now
                done = d
    d = done or {}
    sid = d.get("session_id") or sid
    symbol = d.get("resolved_symbol") or symbol
    results.append({
        "case": case_id, "message": message, "model_request_no": req_no,
        "marks_ms": {k: round(v * 1000, 1) for k, v in marks.items()},
        "resolved_symbol": d.get("resolved_symbol"),
        "grounded": d.get("grounded"), "answer_state": d.get("answer_state"),
        "verify_note": d.get("verify_note"), "fallback": d.get("fallback"),
        "answer_text": text, "answer_chars": len(text),
        "next_steps": [s.get("kind") for s in (d.get("next_steps") or [])],
    })
    print(f"[{req_no}/6] {case_id} done in {marks.get('done', 0):.1f}s "
          f"chars={len(text)} grounded={d.get('grounded')}", flush=True)

with open("real-chain-2026-09-16.json", "w", encoding="utf-8") as f:
    json.dump({"synthetic": False, "model": "ark-code-latest (runtime .env)",
               "model_requests_used": req_no, "budget": 6,
               "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "results": results}, f, ensure_ascii=False, indent=1)
print(f"WROTE real-chain-2026-09-16.json requests={req_no}")
