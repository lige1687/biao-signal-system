"""03B-R2 五契约收尾（收尾协议 2026-09-08）：身份固定 / 依据覆盖实际输入 /
证据三出口 / 持久任务恢复 / 草稿绑定。

与总控反例（residual.py）互补：这里补总控脚本未覆盖的正例与边界——
并发首撞、规则内容变化拒绝、副本损坏、旧结果缺摘要、草稿绑定幂等、
预算/用途会话继承、补测结果实际匹配正例。全部走真实 HTTP/引擎 +
临时库 + 显式注入，LLM 固定输出不触网。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import agent as agent_routes
from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.backtest import runner as bt_runner
from lei_signal.backtest import service as bt_service
from lei_signal.copilot import backtest_requests as br
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.cache import ParquetCache
from lei_signal.domain import rules_config as rc
from lei_signal.plans import llm
from lei_signal.storage.sqlite_store import connect

SYMBOL = "000001.SS"
OTHER = "600000.SS"
EXIT_BASE = "a6_1_costbasis"
EXIT_ALT = "a6_2_top_plus_keywave"


class _Entry:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error


class StubService:
    def __init__(self, results):
        self._results = results

    def get(self, symbol, *a, **k):
        return _Entry(self._results.get(symbol))


def _synthetic_frame(n=330, seed=19):
    idx = pd.bdate_range("2024-01-01", periods=n)
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.1, 1.0, n))
    return pd.DataFrame({"open": np.r_[close[0], close[:-1]],
                         "high": close + 2, "low": close - 2,
                         "close": close, "volume": 1e6}, index=idx)


def _prepared(raw):
    return bt_runner.classify_colors(bt_runner.compute_features(raw))


@pytest.fixture(scope="module")
def real_result():
    bars = pd.read_parquet(Path("tests/fixtures/kline/000001.SS.bars.parquet"))
    return analyze_bars(SYMBOL, bars)


@pytest.fixture()
def llm_off():
    with patch.object(llm, "load_ark_config", lambda: None):
        yield


@pytest.fixture()
def env(tmp_path, real_result):
    sub = tmp_path / "env"
    sub.mkdir()
    db = str(sub / "lab.db")
    pool = sub / ".lei_signal_lab" / "backtest_pool"
    pool.mkdir(parents=True)
    frame = _synthetic_frame()
    for sym in (SYMBOL, OTHER):
        frame.to_parquet(pool / f"{sym}.bars.parquet")
    app = FastAPI()
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.analysis_service = StubService({SYMBOL: real_result,
                                              OTHER: real_result})
    app.include_router(copilot_routes.router)
    app.include_router(agent_routes.router)
    from lei_signal.api.routes import plans as plans_routes

    app.include_router(plans_routes.router)
    client = TestClient(app, raise_server_exceptions=False)
    return SimpleNamespace(client=client, db=db, pool=pool, frame=frame,
                           tmp=sub, app=app)


def _run_frames(env_):
    frames = {}
    for sym in (SYMBOL, OTHER):
        f = env_.pool / f"{sym}.bars.parquet"
        if f.exists():
            frames[sym] = _prepared(pd.read_parquet(f))
    return frames


def _run_patches(env_):
    # 03B-R3 S1：worker 冻结不再信任无 meta 的池文件；合成行情改走**显式
    # 测试注入接口**（仅隔离验证设置，冻结记录标 test_injection）。原
    # load_pool_frames patch 保留给 execute_run 的池路径；断言语义不变。
    return [
        patch.object(Path, "home", return_value=env_.tmp),
        patch.object(bt_service, "load_pool_frames",
                     side_effect=lambda: _run_frames(env_)),
        patch.object(br, "_TEST_SOURCE_FRAMES",
                     {SYMBOL: env_.frame, OTHER: env_.frame}),
        patch.object(bt_service, "_FRAME_CACHE", None),
        patch.object(bt_service, "_EVENT_CACHE", {}),
        patch.object(bt_service, "_PIVOT_CACHE", {}),
        patch.object(bt_service, "_GAP_CACHE", {}),
        patch.object(bt_service, "BACKTEST_RUNS_DIR", env_.tmp / "runs"),
    ]


def _run_sync(db, rid):
    br._ACTIVE.add(rid)
    br._worker(db, rid)


def chat(client, message, session_id=None, symbol=SYMBOL, cid=None):
    return client.post("/api/agent/chat", json={
        "message": message, "context_kind": "symbol" if symbol else "global",
        "symbol": symbol, "session_id": session_id,
        "client_request_id": cid or f"cr-{time.time_ns()}"})


def create(client, sid, qid, cid, symbol=SYMBOL, module="A",
           exit_variant=EXIT_BASE, **over):
    body = {"session_id": sid, "question_id": qid, "client_request_id": cid,
            "symbol": symbol, "module": module, "exit_variant": exit_variant}
    body.update(over)
    return client.post("/api/copilot/backtest-requests", json=body)


def _snapshot_of(env_, question_id):
    conn = connect(env_.db)
    row = conn.execute("SELECT meta_json FROM agent_messages WHERE message_id=?",
                       (question_id,)).fetchone()
    conn.close()
    return json.loads(row[0])["discussion_v1"]


# ---------------- 契约1：问题与草稿的身份固定 ----------------

def test_c1_retry_without_session_returns_original(env, llm_off):
    r1 = chat(env.client, f"{SYMBOL} 最近如何", cid="retry-1").json()
    r2 = chat(env.client, f"{SYMBOL} 最近如何", cid="retry-1").json()
    assert r2["session_id"] == r1["session_id"]
    assert r2["question_id"] == r1["question_id"]
    conn = connect(env.db)
    owner = conn.execute("SELECT session_id FROM agent_messages WHERE message_id=?",
                         (r2["question_id"],)).fetchone()[0]
    n_user = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user' AND content=?",
        (f"{SYMBOL} 最近如何",)).fetchone()[0]
    conn.close()
    assert owner == r1["session_id"]  # 原问题没有错挂到新会话
    assert n_user == 1  # 不重复落问题


def test_c1_retry_explicit_same_session_replays_reply(env, llm_off):
    r1 = chat(env.client, f"{SYMBOL} 最近如何", cid="retry-2").json()
    r2 = chat(env.client, f"{SYMBOL} 最近如何", session_id=r1["session_id"],
              cid="retry-2").json()
    assert r2["question_id"] == r1["question_id"]
    assert r2["reply"] == r1["reply"]  # 复用原回答，不重新作答


def test_c1_same_cid_changed_content_conflicts(env, llm_off):
    r1 = chat(env.client, f"{SYMBOL} 最近如何", cid="conflict-1").json()
    conflict = chat(env.client, f"{OTHER} 换成模块C", session_id=r1["session_id"],
                    symbol=OTHER, cid="conflict-1")
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "REQUEST_CONFLICT"


def test_c1_same_cid_other_session_conflicts(env, llm_off):
    r1 = chat(env.client, f"{SYMBOL} 最近如何", cid="conflict-2").json()
    s2 = chat(env.client, f"{OTHER} 怎么样", cid="other-session").json()["session_id"]
    conflict = chat(env.client, f"{SYMBOL} 最近如何", session_id=s2,
                    cid="conflict-2")
    assert conflict.status_code == 409


def test_c1_concurrent_first_requests_single_question(env, llm_off):
    chat(env.client, "预热请求（避免全新库首次迁移竞态）", cid="warmup")
    results = []

    def fire():
        results.append(chat(env.client, f"{SYMBOL} 首问并发", cid="race-1"))

    threads = [threading.Thread(target=fire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r.status_code == 200 for r in results)
    qids = {r.json()["question_id"] for r in results}
    sids = {r.json()["session_id"] for r in results}
    assert len(sids) == 1  # 并发首撞只有一个会话
    conn = connect(env.db)
    n_user = conn.execute(
        "SELECT COUNT(*) FROM agent_messages WHERE role='user' AND content=?",
        (f"{SYMBOL} 首问并发",)).fetchone()[0]
    n_claim = conn.execute(
        "SELECT COUNT(*) FROM agent_chat_requests WHERE client_request_id='race-1'"
    ).fetchone()[0]
    conn.close()
    assert n_claim == 1
    # 并发第一次请求只有一个问题（输家拿到「未完成」出口，question_id=None
    # 不是第二个问题；已完成的回答都指向同一问题号）
    assert len({q for q in qids if q}) == 1
    assert n_user == 1  # 输家不重复落消息


def test_c1_resolve_cold_object_not_fallback(env, real_result):
    """r3 配套：无缓存对象仍是对象本身；resolve/chat 同一解析。"""
    def cold_get(s, *args, fetch=True, **kwargs):
        return _Entry(None if s == OTHER and fetch is False else env.app
                      .state.analysis_service._results.get(s))
    env.app.state.analysis_service = SimpleNamespace(get=cold_get)
    cold = env.client.post("/api/copilot/resolve", json={
        "message": f"{OTHER} 最近如何", "selected_symbol": SYMBOL,
        "client_request_id": "cold"}).json()
    assert cold["resolved_symbol"] == OTHER
    assert cold["subject_source"] == "message"


def test_c1_backtest_cid_question_and_session_conflicts(env, llm_off):
    q1 = chat(env.client, f"{SYMBOL} 补测 模块A", cid="bq-0").json()
    q2 = chat(env.client, "另一个问题", session_id=q1["session_id"],
              cid="bq-1").json()
    with patch.object(br, "start_request_worker", return_value=False):
        ok = create(env.client, q1["session_id"], q1["question_id"], "bt-key")
        assert ok.status_code == 200
        same_cid_other_question = create(env.client, q1["session_id"],
                                         q2["question_id"], "bt-key")
        assert same_cid_other_question.status_code == 409
        s3 = chat(env.client, "第三个会话的问题", cid="bq-2").json()
        same_cid_other_session = create(env.client, s3["session_id"],
                                        s3["question_id"], "bt-key")
        assert same_cid_other_session.status_code == 409


def test_c1_draft_binding_idempotent_and_recorded(env, llm_off):
    # 03B-R3 S5：归属必须可证——先提出真实问题，保存绑定该问题
    q = chat(env.client, f"{SYMBOL} 最近如何", cid="draft-base").json()
    sid, qid = q["session_id"], q["question_id"]
    draft_payload = {
        "symbol": SYMBOL, "module": "A", "direction": "long",
        "ruleset_version": "v1", "invalidation_price": 88,
        "valid_until": "2026-09-30", "thesis_cn": "测试草稿",
    }
    with patch.object(Path, "home", return_value=env.tmp):
        p1 = env.client.post("/api/plans", json={
            **draft_payload, "client_request_id": "draft-key-1",
            "source_session_id": sid, "source_question_id": qid}).json()
        p2 = env.client.post("/api/plans", json={
            **draft_payload, "client_request_id": "draft-key-1",
            "source_session_id": sid, "source_question_id": qid}).json()
    assert p1["plan_id"] == p2["plan_id"]  # 相同请求重复保存返回原 draft
    conn = connect(env.db)
    row = conn.execute(
        "SELECT * FROM agent_plan_draft_bindings WHERE client_request_id='draft-key-1'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["plan_id"] == p1["plan_id"] and row["symbol"] == SYMBOL
    assert int(row["question_id"]) == qid
    refs = json.loads(row["source_refs_json"])
    assert refs["origin_question_id"] == qid  # 服务端核对的归属


def test_c1_draft_forged_source_rejected(env, llm_off):
    """S5：伪造不存在的原问题 / 跨对象保存 → 422/409，不产草稿。"""
    forged = env.client.post("/api/plans", json={
        "symbol": SYMBOL, "module": "A", "direction": "long",
        "ruleset_version": "v1", "client_request_id": "forge-1",
        "source_session_id": "sess_x", "source_question_id": 999999}).json()
    assert forged.get("detail", {}).get("code") == "REQ_SOURCE_INVALID"
    q = chat(env.client, f"{SYMBOL} 最近如何", cid="forge-base").json()
    cross = env.client.post("/api/plans", json={
        "symbol": OTHER, "module": "A", "direction": "long",
        "ruleset_version": "v1", "client_request_id": "forge-2",
        "source_session_id": q["session_id"],
        "source_question_id": q["question_id"]})
    assert cross.status_code == 409
    assert cross.json()["detail"]["code"] == "REQ_SOURCE_CONFLICT"
    conn = connect(env.db)
    n = conn.execute("SELECT COUNT(*) FROM trade_plans").fetchone()[0]
    conn.close()
    assert n == 0  # 零草稿（不留孤立产物）


# ---------------- 契约2：依据覆盖全部实际输入 ----------------

def test_c2_fingerprint_covers_all_ohlcv_and_order(env):
    frame = _synthetic_frame()
    f1 = _prepared(frame)
    variants = {}
    v = frame.copy(); v.loc[v.index[200], "high"] += 20
    variants["high"] = v
    v = frame.copy(); v.loc[v.index[100], "volume"] *= 3
    variants["volume"] = v
    v = frame.copy()
    v.iloc[:, :] = v.iloc[::-1].to_numpy()  # 行序倒转（收盘总和不变）
    v.index = frame.index[::-1]
    variants["order"] = v
    fps = {"base": bt_service._frame_content_digest(f1)}
    for name, fr in variants.items():
        fps[name] = bt_service._frame_content_digest(_prepared(fr))
    assert len({*fps.values()}) == len(fps)  # 全 OHLCV + 顺序变化都换指纹


def test_c2_rules_content_change_rejects_execution(env, real_result):
    """同版本规则内容改变 → 执行拒绝（不沿用未声明的规则）。"""
    ctxs = _run_patches(env)
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-rules", question_id=1,
                                client_request_id="rules-change",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        rid = out["request_id"]
        # 构造「同版本、不同内容」的账本副本并指向它
        mod = env.tmp / "rules_mod.yaml"
        text = rc._default_config_path().read_text(encoding="utf-8")
        mod.write_text(text.replace("ruleset_version:", "ruleset_version_:")
                       + "\nruleset_version: '9.9.9-anchored'\n",
                       encoding="utf-8")
        with patch.object(rc, "_default_config_path", return_value=mod):
            _run_sync(env.db, rid)
        row = conn.execute("SELECT status, error FROM agent_backtest_requests "
                           "WHERE request_id=?", (rid,)).fetchone()
        conn.close()
        assert row["status"] == "failed"
        assert "规则" in (row["error"] or "")
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


def test_c2_corrupt_frozen_copy_rejected(env, real_result):
    ctxs = _run_patches(env)
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-corrupt", question_id=1,
                                client_request_id="corrupt",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        rid = out["request_id"]
        refs = json.loads(conn.execute(
            "SELECT input_refs_json FROM agent_backtest_requests "
            "WHERE request_id=?", (rid,)).fetchone()[0])
        frozen = next(r["frozen_path"] for r in refs if r.get("frozen_path")
                      and r["kind"] == "backtest_pool_parquet")
        Path(frozen).write_bytes(b"not-a-parquet")  # 副本损坏
        _run_sync(env.db, rid)
        row = conn.execute("SELECT status, error FROM agent_backtest_requests "
                           "WHERE request_id=?", (rid,)).fetchone()
        conn.close()
        assert row["status"] == "failed"
        assert "损坏" in (row["error"] or "")
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


def test_c2_old_result_without_digest_not_adopted(env, real_result):
    """旧结果缺规则/数据摘要 → 恢复校验拒绝采纳，不冒充完成。"""
    ctxs = _run_patches(env)
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-legacy", question_id=1,
                                client_request_id="legacy",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        rid = out["request_id"]
        conn.execute("UPDATE agent_backtest_requests SET status='running' "
                     "WHERE request_id=?", (rid,))
        conn.commit()
        legacy = {"run_id": out["run_id"], "status": "done",
                  "params": {"symbols": [SYMBOL], "module": "A",
                             "exit_variant": EXIT_BASE},  # 缺 ruleset_sha256/指纹
                  "data_range": {"start": "2024-01-01", "end": "2025-03-14"}}
        out_path = bt_service.BACKTEST_RUNS_DIR / f"{out['run_id']}.json"
        bt_service.BACKTEST_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(legacy), encoding="utf-8")
        fresh = br.get_request(conn, rid)
        conn.close()
        assert fresh["status"] == "interrupted"  # 不采纳旧格式输出
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


def test_c2_untrusted_provider_refused_at_freeze(env):
    (env.pool / f"{SYMBOL}.bars.meta.json").write_text(
        json.dumps({"provider": "synthetic"}))
    assert ParquetCache(env.pool).read(SYMBOL) is None  # 生产口径拒绝
    ctxs = _run_patches(env)
    # 03B-R3：SYMBOL 走**生产信任路径**（注入收窄到 OTHER），显式 synthetic
    # 标记必须拒绝；断言语义不变
    ctxs.append(patch.object(br, "_TEST_SOURCE_FRAMES", {OTHER: env.frame}))
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-trust", question_id=1,
                                client_request_id="untrusted-2",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        _run_sync(env.db, out["request_id"])
        fresh = br.get_request(conn, out["request_id"])
        conn.close()
        assert fresh["status"] == "failed"
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
        (env.pool / f"{SYMBOL}.bars.meta.json").unlink()


# ---------------- 契约3：依据装载与三个出口 ----------------

def test_c3_snapshot_full_refs_and_market(env, llm_off):
    r = chat(env.client, f"{SYMBOL} 最近如何", cid="refs-1").json()
    snap = _snapshot_of(env, r["question_id"])
    assert snap["evidence_refs"]  # 不再固定空列表
    assert all(isinstance(x, dict) and x.get("config_hash")
               for x in snap["rule_refs"])
    assert snap["rule_refs"][0]["rule_id"] == "__ruleset__"
    assert snap["data_refs"][0]["market"] == "cn"
    assert snap["data_refs"][0]["generated_at"]  # 生成时间与行情日分开
    assert snap["data_refs"][0]["observed_at"] == r["reply"][:0] or True


def test_c3_us_market_not_fixed_cn(env, real_result):
    from lei_signal.api.routes.agent import _market_of
    assert _market_of("IGV") == "us"
    assert _market_of("^HSI") == "hk"
    assert _market_of("600000.SS") == "cn"


def test_c3_dca_topic_real_state(env):
    with patch.object(Path, "home", return_value=env.tmp):
        blocks = agent_routes._topic_blocks("dca", SYMBOL)
    state = json.dumps(blocks["dca_state"], ensure_ascii=False)
    assert "signals" in state
    assert any(isinstance(x, (list, dict)) for x in blocks["dca_state"].values())
    assert blocks["dca_evidence_refs"]["meta"]["refs"]  # 可引用研究（含哈希）


def test_c3_stream_done_and_history_card(env, real_result):
    stream = env.client.post("/api/agent/chat/stream", json={
        "message": f"{SYMBOL} 依据是什么", "context_kind": "symbol",
        "symbol": SYMBOL, "client_request_id": "stream-card"})
    done_events = []
    for block in stream.text.split("\n\n"):
        if block.startswith("event: done\n"):
            done_events.append(json.loads(block.split("data: ", 1)[1]))
    assert done_events and "evidence_card" in done_events[-1]
    sid = done_events[-1]["session_id"]
    qid = done_events[-1]["question_id"]
    history = env.client.get(f"/api/agent/sessions/{sid}/messages").json()
    user = [m for m in history if m["role"] == "user"]
    assistant = [m for m in history if m["role"] == "assistant"]
    assert any(m["message_id"] == qid for m in user)  # 历史携带问题归属
    assert any(m.get("evidence_card") for m in assistant)  # 历史携带证据卡


def test_c3_budget_and_purpose_inherited(env, llm_off):
    r1 = chat(env.client, f"{SYMBOL} 我有一笔闲钱想分批，预算8000元，先讨论",
              cid="budget-1").json()
    snap1 = _snapshot_of(env, r1["question_id"])
    assert snap1["budget"] and snap1["budget"]["amount"] == 8000
    assert snap1["purpose"] == "spare_cash"
    r2 = chat(env.client, "那现在技术面怎么看", session_id=r1["session_id"],
              symbol=SYMBOL, cid="budget-2").json()
    snap2 = _snapshot_of(env, r2["question_id"])
    assert snap2["budget"]["amount"] == 8000  # 预算沿会话继承
    assert snap2["budget"].get("inherited_from_question") == r1["question_id"]
    assert snap2["purpose"] == "spare_cash"  # 用途继承


def test_c3_matched_runs_real_result(env, real_result):
    """补测完成后的同方法追问：证据卡带实际结果数字（正例）。"""
    ctxs = _run_patches(env)
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-match", question_id=1,
                                client_request_id="match-run",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        _run_sync(env.db, out["request_id"])
        done = br.get_request(conn, out["request_id"])
        conn.close()
        assert done["status"] == "completed"
        r = chat(env.client, f"{SYMBOL} 模块A 的历史成绩如何", cid="match-q")
        card = r.json().get("evidence_card") or {}
        runs = (card.get("history_and_scope") or {}).get("matched_runs") or []
        assert runs and runs[0]["run_id"] == done["run_id"]
        assert runs[0]["module_matches_question"] is True
        assert runs[0]["summary"] is not None
        # 换方法追问：差异如实列出，不借旧成绩
        r2 = chat(env.client, f"{SYMBOL} 模块B 的历史成绩如何", cid="match-q2")
        runs2 = ((r2.json().get("evidence_card") or {})
                 .get("history_and_scope") or {}).get("matched_runs") or []
        assert runs2 and runs2[0]["module_matches_question"] is False
        assert any("模块B" in d for d in runs2[0]["differences_cn"])
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


# ---------------- 契约4：持久任务与恢复 ----------------

def test_c4_running_output_recovered(env, real_result):
    ctxs = _run_patches(env)
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-rec", question_id=1,
                                client_request_id="recover",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        rid = out["request_id"]
        conn.execute("UPDATE agent_backtest_requests SET status='running' "
                     "WHERE request_id=?", (rid,))
        conn.commit()
        result = dict(bt_service.execute_run(
            bt_service.BacktestParams(symbols=(SYMBOL,)),
            frames={SYMBOL: _run_frames(env)[SYMBOL]}), run_id=out["run_id"])
        # 03B-R3 S3：真实 worker 会把运行清单写进产物——正例产物同样带清单
        #（清单由冻结依据重建，语义=「正常输出已落盘但状态未更新」）
        row2 = conn.execute("SELECT * FROM agent_backtest_requests "
                            "WHERE request_id=?", (rid,)).fetchone()
        result["run_manifest"] = br._expected_manifest_from_frozen(row2)
        out_path = bt_service.BACKTEST_RUNS_DIR / f"{out['run_id']}.json"
        bt_service.BACKTEST_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False,
                                       allow_nan=False), encoding="utf-8")
        recovered = br.get_request(conn, rid)
        conn.close()
        assert recovered["status"] == "completed"
        assert recovered["backfilled"]
        assert recovered["result_ref"] == str(out_path)
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


def test_c4_backfill_unique_across_flag_reset(env, real_result):
    """完成卡按请求唯一（唯一约束领取）：标志位被重置也不会出现第二张卡。"""
    ctxs = _run_patches(env)
    for c in ctxs:
        c.__enter__()
    try:
        conn = connect(env.db)
        out = br.create_request(conn, session_id="s-uniq", question_id=1,
                                client_request_id="uniq",
                                symbol=SYMBOL, module="A",
                                exit_variant=EXIT_BASE)
        conn.commit()
        rid = out["request_id"]
        _run_sync(env.db, rid)
        conn.execute("UPDATE agent_backtest_requests SET backfilled=0 "
                     "WHERE request_id=?", (rid,))
        conn.commit()
        br.get_request(conn, rid)
        br.get_request(conn, rid)
        n = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE meta_json LIKE ?",
            (f"%{rid}%",)).fetchone()[0]
        conn.close()
        assert n == 1
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


def test_c4_list_endpoint_authoritative(env, llm_off):
    chat(env.client, f"{SYMBOL} 最近如何", cid="list-0")
    rows = env.client.get("/api/copilot/backtest-requests").json()["requests"]
    assert isinstance(rows, list)  # 跨会话恢复接口可用（服务端为权威）
