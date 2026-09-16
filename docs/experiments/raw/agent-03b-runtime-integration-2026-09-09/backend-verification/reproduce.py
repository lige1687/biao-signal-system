"""Controller 03B acceptance: isolated HTTP + real engine, no production writes/network.

Run from repo: PYTHONPATH=src python3.11 <this file>
Each check records expected acceptance behaviour and the observed counterexample.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
RAW = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="lei-03b-controller-")).resolve()
tempfile.tempdir = str(TMP)
SOURCES = [
    "src/lei_signal/copilot/backtest_requests.py", "src/lei_signal/copilot/resolve.py",
    "src/lei_signal/api/routes/agent.py", "src/lei_signal/api/routes/copilot.py",
    "src/lei_signal/plans/sessions.py", "src/lei_signal/backtest/service.py",
    "web/src/utils/resolveRoute.ts", "web/src/pages/AgentWorkspacePage.tsx",
    "web/src/components/AgentConsole.tsx", "tests/unit/test_discussion_backtest_03b.py",
    "configs/semantic_states.v1.json", "src/lei_signal/copilot/semantic_states.py",
]

def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}

BEFORE = hashes()
(RAW / "source-before.json").write_text(json.dumps(BEFORE, indent=2))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

def audit(event, args):
    if event == "socket.connect":
        raise RuntimeError("Controller test forbids network")
    if event == "sqlite3.connect":
        p = str(args[0])
        if p != ":memory:" and not Path(p).resolve().is_relative_to(TMP):
            raise RuntimeError(f"Controller forbids non-temp SQLite: {p}")
    if event == "open" and isinstance(args[0], (str, bytes)):
        flags = args[2] or 0
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            p = Path(os.fsdecode(args[0])).resolve()
            if str(p) != "/dev/null" and not any(p.is_relative_to(r) for r in (TMP, RAW)):
                raise RuntimeError(f"Controller forbids write: {p}")

sys.addaudithook(audit)
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lei_signal.api import config as api_config
from lei_signal.api.routes import agent, copilot
from lei_signal.backtest import service as bt
from lei_signal.backtest import runner as bt_runner
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.copilot import backtest_requests as br
from lei_signal.plans import llm, sessions
from lei_signal.storage.sqlite_store import connect

A, B = "000001.SS", "600000.SS"
idx = pd.bdate_range("2024-01-01", periods=330)
rng = np.random.default_rng(19)
close = 100 + np.cumsum(rng.normal(.1, 1, len(idx)))
frame = pd.DataFrame({"open": np.r_[close[0], close[:-1]], "high": close + 2,
                      "low": close - 2, "close": close, "volume": 1e6}, index=idx)
pool = TMP / ".lei_signal_lab/backtest_pool"
pool.mkdir(parents=True)
for sym in (A, B):
    frame.to_parquet(pool / f"{sym}.bars.parquet")
db = str(TMP / "lab.db")
results = {s: analyze_bars(s, frame.copy()) for s in (A, B)}
app = FastAPI()
app.state.plans_db_path = db
app.state.watchlist_db_path = db
app.state.analysis_service = SimpleNamespace(get=lambda s, *a, **k:
    SimpleNamespace(result=results.get(s), error="fixture absent"))
app.include_router(copilot.router)
app.include_router(agent.router)
observed = {}

def record(key, good, data):
    observed[key] = {"acceptance_pass": bool(good), "observed": data}
    print(key, "PASS" if good else "FAIL", flush=True)

def message(client, text, sid=None, symbol=A, cid="chat1"):
    return client.post("/api/agent/chat", json={"message": text,
        "context_kind": "symbol", "symbol": symbol, "session_id": sid,
        "client_request_id": cid})

def create(client, sid, qid, cid, **kw):
    body = dict(session_id=sid, question_id=qid, client_request_id=cid,
                symbol=A, module="A", exit_variant="a6_1_costbasis")
    body.update(kw)
    return client.post("/api/copilot/backtest-requests", json=body)

def run_sync(db_path, rid):
    br._ACTIVE.add(rid)
    br._worker(db_path, rid)
    return True

def read_request(rid):
    with connect(db) as conn:
        return br.get_request(conn, rid)

with ExitStack() as st:
    st.enter_context(patch.object(Path, "home", return_value=TMP))
    st.enter_context(patch.object(api_config, "sqlite_path", return_value=db))
    st.enter_context(patch.object(llm, "load_ark_config", return_value=None))
    st.enter_context(patch.object(bt, "BACKTEST_RUNS_DIR", TMP / "runs"))
    # Explicit fixture injection with the same feature computation as the loader;
    # no fake trusted-provider metadata is written for synthetic prices.
    st.enter_context(patch.object(bt, "load_pool_frames", side_effect=lambda:
        {s: bt_runner.classify_colors(bt_runner.compute_features(pd.read_parquet(pool / f"{s}.bars.parquet")))
         for s in (A, B)}))
    # 03B-R3 夹具调整（总控协议 sanctioned）：S1 修复后 worker 冻结不再信任
    # 无 meta 的池文件；合成行情改走**显式测试注入接口**（br._TEST_SOURCE_FRAMES，
    # 仅隔离验证设置，冻结记录标 test_injection）。断言语义不变。
    st.enter_context(patch.object(br, "_TEST_SOURCE_FRAMES", {A: frame, B: frame}))
    for name in ("_FRAME_CACHE", "_EVENT_CACHE", "_PIVOT_CACHE", "_GAP_CACHE", "_PROFILE_CACHE"):
        st.enter_context(patch.object(bt, name, None if name == "_FRAME_CACHE" else {}))
    client = st.enter_context(TestClient(app, raise_server_exceptions=False))

    if "--regression" in sys.argv:
        import pytest
        st.enter_context(patch.object(br, "start_request_worker", side_effect=run_sync))
        code = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp=" + str(TMP / "pytest"),
                            "tests/unit/test_discussion_backtest_03b.py"])
        (RAW / "regression-scope.json").write_text(json.dumps({
            "exit_code": code, "scheduler": "synchronous controlled worker, real engine",
            "source_unchanged": BEFORE == hashes(), "temporary_root": str(TMP)}, indent=2))
        sys.exit(code)

    resolved = client.post("/api/copilot/resolve", json={"message": f"{B} 最近如何",
        "selected_symbol": A, "client_request_id": "r1"}).json()
    reply = message(client, f"{B} 最近如何", cid="switch").json()
    record("d1_object", resolved["resolved_symbol"] == reply["resolved_symbol"] == B,
           {"resolve": resolved["resolved_symbol"], "chat": reply["resolved_symbol"]})

    intents = {}
    for t in ("先不要补测 模块A", "有没有已有回测结果 模块A", "我有一笔闲钱想定投"):
        intents[t] = client.post("/api/copilot/resolve", json={"message": t,
            "selected_symbol": A, "client_request_id": "intent"}).json()
    record("d2_intent", all(intents[t]["intent"] == "discussion" for t in list(intents)[:2])
           and intents[list(intents)[2]]["purpose"] == "spare_cash", intents)

    reply = message(client, "按模块B突破，用已有闲钱，预算10000元，先讨论依据", cid="snapshot").json()
    sid, qid = reply["session_id"], reply["question_id"]
    with connect(db) as conn:
        snap = json.loads(conn.execute("SELECT meta_json FROM agent_messages WHERE message_id=?",
            (qid,)).fetchone()[0])["discussion_v1"]
    record("d3_snapshot", snap["method"]["module"] == "B" and bool(snap["budget"])
           and bool(snap["data_refs"]) and bool(snap["rule_refs"]), snap)

    # Pause only the scheduler: prove HTTP accepts unbound objects/default methods.
    with patch.object(br, "start_request_worker", return_value=False):
        wrong = create(client, sid, qid, "wrong-symbol", symbol=B)
        body = dict(session_id=sid, question_id=qid, client_request_id="missing-method", symbol=A)
        missing = client.post("/api/copilot/backtest-requests", json=body)
        invalid = create(client, sid, qid, "invalid-method", module="X")
    record("d4_binding", wrong.status_code == 422 and missing.status_code == 422
           and invalid.status_code == 422,
           {"wrong_symbol": [wrong.status_code, wrong.json()],
            "missing_method": [missing.status_code, missing.json()],
            "invalid_method": [invalid.status_code, invalid.text]})

    # Real engine, cutoff before the final 150+ input rows.
    with connect(db) as conn:
        out = br.create_request(conn, session_id=sid, question_id=qid,
            client_request_id="cutoff", symbol=A, module="A",
            exit_variant="a6_1_costbasis", data_cutoff="2024-06-28")
        conn.commit()
    run_sync(db, out["request_id"])
    done = read_request(out["request_id"])
    if not done["result_ref"]:
        raise RuntimeError(json.dumps(done, ensure_ascii=False))
    engine_result = json.loads(Path(done["result_ref"]).read_text())
    record("d5_cutoff", engine_result["data_range"]["end"] <= "2024-06-28",
           {"saved_cutoff": done["data_cutoff"], "actual": engine_result["data_range"],
            "config_keys_missing_in_result": sorted(set(done["config"]) - set(engine_result["params"]))})

    # A queued request freezes a hash, then its file changes. Existing cache is
    # cleared here to ensure this counterexample is about changed source input.
    with connect(db) as conn:
        changed = br.create_request(conn, session_id=sid, question_id=qid,
            client_request_id="source-change", symbol=A, module="A", exit_variant="a6_1_costbasis")
        conn.commit()
    newer = frame.copy()
    newer.index = newer.index + pd.Timedelta(days=400)
    newer.to_parquet(pool / f"{A}.bars.parquet")
    newhash = hashlib.sha256((pool / f"{A}.bars.parquet").read_bytes()).hexdigest()
    bt._FRAME_CACHE = None
    bt._EVENT_CACHE.clear(); bt._PIVOT_CACHE.clear()
    run_sync(db, changed["request_id"])
    changed_done = read_request(changed["request_id"])
    changed_result = json.loads(Path(changed_done["result_ref"]).read_text()) if changed_done["result_ref"] else {}
    record("d6_input", changed_done["status"] != "completed" or
           changed_result.get("data_range", {}).get("end") == frame.index[-1].date().isoformat(),
           {"status": changed_done["status"], "saved_hash": changed_done["input_refs"][0].get("content_sha256"),
            "actual_file_hash": newhash, "actual_range": changed_result.get("data_range")})

    frame.to_parquet(pool / f"{A}.bars.parquet")
    bt._FRAME_CACHE = None
    bt._EVENT_CACHE.clear(); bt._PIVOT_CACHE.clear()
    with patch.object(br, "start_request_worker", side_effect=run_sync), \
         patch.object(bt, "execute_run", wraps=bt.execute_run) as execute:
        first = create(client, sid, qid, "retry")
        original_rid = first.json()["request_id"]
        again = create(client, sid, qid, "retry")
        count = execute.call_count
    record("d7_retry", count == 1,
           {"execute_count": count, "same_request": again.json()["request_id"] == original_rid})

    with connect(db) as conn:
        interrupted = br.create_request(conn, session_id=sid, question_id=qid,
            client_request_id="interrupted", symbol=A, module="A", exit_variant="a6_1_costbasis")
        conn.execute("UPDATE agent_backtest_requests SET status='running' WHERE request_id=?",
                     (interrupted["request_id"],))
        conn.commit()
    v1 = client.get("/api/copilot/backtest-requests/" + interrupted["request_id"]).json()
    v2 = client.get("/api/copilot/backtest-requests/" + interrupted["request_id"]).json()
    queued = client.get("/api/copilot/backtest-requests?session_id=" + sid).json()
    record("d8_restart", v1["status"] == "interrupted" and all(
        r["status"] != "queued" for r in queued["requests"]),
        {"first_get": v1["status"], "second_get": v2["status"],
         "orphan_queued": [r["request_id"] for r in queued["requests"] if r["status"] == "queued"]})

    payloads = []
    def capture(payload, *args):
        payloads.append(payload)
        return "固定解释"
    with patch.object(llm, "load_ark_config", return_value=SimpleNamespace()), \
         patch.object(llm, "chat_discussion", side_effect=capture):
        message(client, "定投状态和依据是什么", sid=sid, cid="dca")
    p = payloads[-1]
    record("d9_topic", any(k in p for k in ("dca", "dca_state", "dca_evidence")),
           {"payload_keys": list(p), "sentiment_signals": p.get("sentiment_signals"),
            "evidence_card": p.get("evidence_card")})
    record("d10_public_card", "evidence_card" in reply or "历史结果" in reply.get("reply", ""), reply)

    retry_chat1 = message(client, "同一问题重试", sid=sid, cid="same-chat").json()
    retry_chat2 = message(client, "同一问题重试", sid=sid, cid="same-chat").json()
    record("d11_chat_retry", retry_chat1["question_id"] == retry_chat2["question_id"],
           {"first_question": retry_chat1["question_id"], "retry_question": retry_chat2["question_id"]})

AFTER = hashes()
(RAW / "source-after.json").write_text(json.dumps(AFTER, indent=2))
output = {"isolation_root": str(TMP), "source_unchanged": BEFORE == AFTER,
          "checks": observed, "engine_result": engine_result}
(RAW / "results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str))
print("SOURCE_UNCHANGED", BEFORE == AFTER)
sys.exit(0 if all(r["acceptance_pass"] for r in observed.values()) else 1)
