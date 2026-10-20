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

ROOT = Path('/Users/yongbiaoli/lei-signal-integration-20260909')
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
    "src/lei_signal/copilot/chat_identity.py", "web/src/components/PlanDraftCard.tsx",
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
from lei_signal.api.routes import plans
app.include_router(plans.router)
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

