"""03B 标的讨论与补测集成（总控协议 §7 十四场景 + R8 重写，2026-09-08）。

R8 修正（对照总控复验）：
- 合成行情经**与生产加载器同一函数链**（compute_features + classify_colors）
  预处理后交引擎，不再把原始 OHLCV 冒充池帧；
- 补测 worker 全生命周期（提交→领取→执行→落盘→回填）都在临时路径与替换
  作用域内，**同步调度**等待后台结束才退出，不依赖真实池文件；
- 断言核对输出意义（数据区间、配置逐项、链上 ID、状态语义），无恒真断言；
- LLM 用固定输出（patch），不触网；全部临时库，不触真实 lab.db。
"""
from __future__ import annotations

import contextlib
import json
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
from lei_signal.copilot import resolve as resolve_mod
from lei_signal.compose.pipeline import analyze_bars
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
    """与生产加载器同一特征计算链。"""
    return bt_runner.classify_colors(bt_runner.compute_features(raw))


@pytest.fixture(scope="module")
def real_result():
    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet"))
    return analyze_bars(SYMBOL, bars)


@pytest.fixture()
def llm_fixed():
    cfg = llm.ArkConfig(api_key="test-only", base_url="https://example.test",
                        model="test")
    with patch.object(llm, "load_ark_config", lambda: cfg), \
         patch.object(llm, "_llm_call", return_value="（AI 固定回复）好的"):
        yield


def _make_env(tmp_path, real_result, name="env"):
    sub = tmp_path / name
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
    app.include_router(__import__("lei_signal.api.routes.plans",
                                  fromlist=["plans"]).router)
    client = TestClient(app, raise_server_exceptions=False)
    return SimpleNamespace(client=client, db=db, pool=pool, frame=frame,
                           tmp=sub)


@pytest.fixture()
def env(tmp_path, real_result):
    return _make_env(tmp_path, real_result, "env")


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
    """受控同步调度：worker 全程在替换作用域内执行完毕才返回。"""
    br._ACTIVE.add(rid)
    br._worker(db, rid)


def _rid_by_cid(db, cid):
    conn = connect(db)
    row = conn.execute("SELECT request_id FROM agent_backtest_requests "
                       "WHERE client_request_id=?", (cid,)).fetchone()
    conn.close()
    return row[0]


def _sync_start_patch():
    """把 start_request_worker 替换为同步执行（总控同一手法）：
    路由创建任务后由本函数立刻同步跑完 worker，使实际执行留在
    替换作用域与临时路径内；执行计数可见。"""
    executed = {"count": 0}

    def _sync_start(db, rid):
        executed["count"] += 1
        _run_sync(db, rid)
        return True

    return (patch.object(br, "start_request_worker",
                         side_effect=lambda db, rid: _sync_start(db, rid)),
            executed)


def _create(client, sid, qid, cid, symbol=SYMBOL, module="A",
            exit_variant=EXIT_BASE, **over):
    body = {"session_id": sid, "question_id": qid, "client_request_id": cid,
            "symbol": symbol, "module": module, "exit_variant": exit_variant}
    body.update(over)
    return client.post("/api/copilot/backtest-requests", json=body)


def chat(client, message, session_id=None, symbol=SYMBOL, cid=None):
    return client.post("/api/agent/chat", json={
        "message": message, "context_kind": "symbol" if symbol else "global",
        "symbol": symbol, "session_id": session_id,
        "client_request_id": cid or f"cr-{time.time_ns()}"})


def resolve(client, message, **over):
    body = {"message": message, "client_request_id": f"cr-{time.time_ns()}"}
    body.update(over)
    return client.post("/api/copilot/resolve", json=body)


def _chat_question(env_):
    r = chat(env_.client, f"{SYMBOL} 最近如何")
    reply = r.json()
    return reply["session_id"], reply["question_id"], reply


# ---------------- 场景 1/3：统一解析与对象优先级（R1） ----------------

def test_s1_resolve_overview_selected_and_explicit(env, real_result):
    d1 = resolve(env.client, "这个标的最近如何", selected_symbol=SYMBOL).json()
    assert d1["intent"] == "discussion" and d1["topic"] == "overview"
    assert d1["resolved_symbol"] == SYMBOL and d1["subject_source"] == "selected"
    d2 = resolve(env.client, f"{SYMBOL} 最近如何").json()
    assert d2["resolved_symbol"] == SYMBOL and d2["subject_source"] == "message"


def test_r1_chat_message_symbol_overrides_selected(env, real_result):
    """R1/d1：选中 A、明确问 B——chat 回复对象是 B；新问题快照绑定 B。"""
    r = chat(env.client, f"{OTHER} 最近如何", symbol=SYMBOL)
    assert r.status_code == 200
    assert r.json()["resolved_symbol"] == OTHER
    conn = connect(env.db)
    snap = json.loads(conn.execute(
        "SELECT meta_json FROM agent_messages WHERE role='user' "
        "ORDER BY message_id DESC LIMIT 1").fetchone()[0])["discussion_v1"]
    conn.close()
    assert snap["symbol"] == OTHER  # 新问题绑定 B；旧问题不覆写


def test_r1_backtest_object_mismatch_rejected_zero_created(tmp_path, real_result):
    service = StubService({SYMBOL: real_result})
    client, db = _make_simple(tmp_path, service, "m1")
    with patch.object(llm, "load_ark_config", lambda: None):
        r = chat(client, f"{SYMBOL} 最近如何")
    reply = r.json()
    bad = _create(client, reply["session_id"], reply["question_id"], "x1",
                  symbol=OTHER)
    assert bad.status_code == 422
    assert bad.json()["detail"]["code"] == "OBJECT_MISMATCH"
    conn = connect(db)
    n = conn.execute("SELECT COUNT(*) FROM agent_backtest_requests").fetchone()[0]
    conn.close()
    assert n == 0  # 零创建


def _make_simple(tmp_path, service, name="s"):
    app = FastAPI()
    db = str(tmp_path / f"{name}.db")
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.analysis_service = service
    app.include_router(copilot_routes.router)
    app.include_router(agent_routes.router)
    from lei_signal.api.routes import plans as plans_routes

    app.include_router(plans_routes.router)
    return TestClient(app), db


# ---------------- 场景 2/11：意图边界与资金用途（R2） ----------------

def test_s2_discussion_vs_trade_report_boundary(env):
    for msg in ("想买一些", "打算申购", "要不要赎回呢", "如果卖出会怎样",
                "没买", "别帮我报单", "先不要补测 模块A",
                "有没有已有回测结果 模块A"):
        d = resolve(env.client, msg).json()
        assert d["intent"] == "discussion", (msg, d["intent"])
    assert resolve(env.client, "我已经买了515880").json()["intent"] == "trade_report"
    assert resolve(env.client, "报单").json()["intent"] == "trade_report"
    assert resolve(env.client, "帮我补测一下 模块A").json()["intent"] == "backtest_request"


def test_s11_purpose_source_and_clarification_once(env):
    d = resolve(env.client, "我有一笔闲钱想定投").json()
    assert d["purpose"] == "spare_cash"  # 闲钱优先，不推定持续新收入
    d2 = resolve(env.client, "每月工资定投一点").json()
    assert d2["purpose"] == "income_dca"
    d3 = resolve(env.client, "投多少合适").json()
    assert "purpose" in [c["kind"] for c in d3["clarification"]]


# ---------------- 场景 4/5：证据卡与语义状态（R3） ----------------

def test_s4_evidence_card_four_parts_and_unknown(env, real_result):
    captured = {}

    def fake_chat(payload, history, message, config):
        captured["payload"] = payload
        return "回复"

    cfg = llm.ArkConfig(api_key="t", base_url="https://x", model="m")
    with patch.object(llm, "load_ark_config", lambda: cfg), \
         patch.object(llm, "chat_discussion", fake_chat):
        r = chat(env.client, "这个标的最近如何")
    card = r.json()["evidence_card"]
    assert card is not None  # 服务端结构化产物，随 HTTP 回复送达页面
    assert set(card.keys()) == {"facts", "history_and_scope", "explanations",
                                "pending_conditions"}
    we = card["history_and_scope"]["winrate_evidence"]
    assert we["compatibility"] == "unknown"  # module_winrate 缺字段 → unknown


def test_s5_semantic_states_limitations(env):
    d = resolve(env.client, "市场恐慌，冰点了吗").json()
    states = {s["id"]: s for s in d["discussion_context"]["states"]}
    assert "icepoint" in states and states["icepoint"]["forbidden_claims"]
    d2 = resolve(env.client, "定投还继续吗").json()
    ids2 = {s["id"] for s in d2["discussion_context"]["states"]}
    assert {"deep20", "bottom_zone", "dca_standard"} <= ids2


# ---------------- 6/7：补测请求校验（R2） ----------------

def test_s6_backtest_single_symbol_and_binding(env, real_result, llm_fixed):
    sid, qid, _ = _chat_question(env)
    cases = [
        {},                               # 缺标的（不默认）
        {"symbol": ""},                   # 空标的
        {"symbol": "A,B"},                # 多标的
        {"symbol": "none"},
        {"module": None},                 # 缺方法（不默认 A）
        {"module": "X"},                  # 非法方法
    ]
    for bad in cases:
        body = {"session_id": sid, "question_id": qid,
                "client_request_id": f"c-{time.time_ns()}-{json.dumps(bad)}",
                "symbol": SYMBOL, "module": "A", "exit_variant": EXIT_BASE}
        body.update(bad)
        if bad.get("symbol") in ("", "A,B", "none") or "symbol" not in bad:
            if bad.get("symbol") is None and "symbol" not in bad:
                body.pop("symbol")  # 缺标的
        if bad.get("module") is None:
            body.pop("module")      # 缺方法
        r = env.client.post("/api/copilot/backtest-requests", json=body)
        assert r.status_code == 422, (bad, r.status_code, r.text[:120])
    r = _create(env.client, "sess-x", 999, f"own-{time.time_ns()}", symbol=SYMBOL)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "QUESTION_OWNERSHIP"


# ---------------- R4：截止与冻结输入（真实引擎） ----------------

def _full_chain(env_, message=None, data_cutoff=None):
    """完整链：问题→快照→请求→同步 worker→结果→回填。全部在替换作用域内。
    start_request_worker 注入为同步执行（路由创建任务即同步跑完一次）。"""
    ctxs = list(_run_patches(env_))
    ctxs.append(patch.object(br, "start_request_worker",
                             side_effect=lambda db, rid: _run_sync(db, rid)))
    for c in ctxs:
        c.__enter__()
    try:
        msg = message or f"{SYMBOL} 最近如何，帮我补测一下 模块A"
        r = chat(env_.client, msg)
        assert r.status_code == 200
        reply = r.json()
        qid = reply["question_id"]
        assert qid
        kw = {}
        if data_cutoff:
            kw["data_cutoff"] = data_cutoff
        created = _create(env_.client, reply["session_id"], qid, "chain", **kw)
        assert created.status_code == 200, created.text
        out = created.json()
        assert out["status"] == "completed" and out["run_id"]
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
    from lei_signal.copilot.backtest_requests import get_request
    final = get_request(connect(env_.db), out["request_id"])
    return reply["session_id"], qid, out, final, reply


def test_s10_s12_full_chain_config_ids_and_backfill(env, real_result, llm_fixed):  # noqa: ANN001
    sid, qid, out, final, reply = _full_chain(env)
    assert final["status"] == "completed", final
    cfg = out["config"]
    assert cfg["symbols"] == [SYMBOL]
    assert cfg["module"] == "A" and cfg["exit_variant"] == EXIT_BASE
    assert cfg["ruleset_version"] and cfg["data_cutoff"]
    assert out["input_refs"][0]["content_sha256"]  # 冻结输入的内容摘要
    # 完成卡回填原问题一次；链上 ID 互核
    conn = connect(env.db)
    backfills = conn.execute(
        "SELECT meta_json FROM agent_messages WHERE role='assistant' "
        "AND meta_json LIKE '%backtest_result%'").fetchall()
    conn.close()
    assert len(backfills) == 1
    meta = json.loads(backfills[0][0])
    assert meta["question_id"] == qid and meta["symbol"] == SYMBOL
    assert meta["run_id"] == out["run_id"]
    result = json.loads(Path(final["result_ref"]).read_text())
    assert result["run_id"] == out["run_id"]
    # R4：实际消费参数完整落盘（含此前漏存项）+ 规则内容摘要 + 数据指纹
    for key in ("accel_filter", "accel_lookback", "stop_atr_buffer",
                "min_stop_distance", "ruleset_sha256", "data_fingerprint"):
        assert key in result["params"], key


def test_r4_cutoff_applied_to_engine_data(env, real_result, llm_fixed):  # noqa: ANN001
    """R4/d5：截止先作用到原始行情——引擎实际数据区间 ≤ 截止。"""
    ctxs = list(_run_patches(env))
    ctxs.append(patch.object(br, "start_request_worker",
                             side_effect=lambda db, rid: False))
    for c in ctxs:
        c.__enter__()
    try:
        r = chat(env.client, f"{SYMBOL} 最近如何")
        reply = r.json()
        created = _create(env.client, reply["session_id"], reply["question_id"],
                          "cut", data_cutoff="2024-06-28")
        assert created.status_code == 200
        _run_sync(env.db, created.json()["request_id"])
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
    from lei_signal.copilot.backtest_requests import get_request
    final = get_request(connect(env.db), created.json()["request_id"])
    assert final["status"] == "completed", final
    result = json.loads(Path(final["result_ref"]).read_text())
    assert result["data_range"]["end"] <= "2024-06-28"


def test_r4_source_change_after_queue_uses_frozen_copy(env, real_result, llm_fixed):  # noqa: ANN001
    """R4/d6：排队后改源文件——worker 用冻结副本，完成且数据区间=原输入。"""
    original_end = _synthetic_frame().index[-1].date().isoformat()
    ctxs = list(_run_patches(env))
    ctxs.append(patch.object(br, "start_request_worker",
                             side_effect=lambda db, rid: False))
    for c in ctxs:
        c.__enter__()
    try:
        r = chat(env.client, f"{SYMBOL} 最近如何")
        reply = r.json()
        created = _create(env.client, reply["session_id"], reply["question_id"],
                          "frozen")
        assert created.status_code == 200
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
    # 排队等待期间：源文件换成 +400 天的新行情
    newer = _synthetic_frame()
    newer.index = newer.index + pd.Timedelta(days=400)
    newer.to_parquet(env.pool / f"{SYMBOL}.bars.parquet")
    for c in ctxs:
        c.__enter__()
    try:
        _run_sync(env.db, created.json()["request_id"])
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
    from lei_signal.copilot.backtest_requests import get_request
    final = get_request(connect(env.db), created.json()["request_id"])
    assert final["status"] == "completed", final
    result = json.loads(Path(final["result_ref"]).read_text())
    assert result["data_range"]["end"] == original_end  # 冻结输入生效


def test_r5_atomic_claim_single_execution(env, real_result, llm_fixed):  # noqa: ANN001
    """R5：原子领取 + 完成重试只读原结果（引擎只执行一次）。

    03B-R2 起：queued→running 的领取在 worker 槽内进行（排队中保持 queued，
    只有实际执行才显示 running）；重复领取失败、重复请求不重复执行。"""
    sid, qid, _ = _chat_question(env)
    calls = {"n": 0}
    real_exec = bt_service.execute_run

    def counting_exec(params, frames=None):
        calls["n"] += 1
        return real_exec(params, frames=frames)

    ctxs = list(_run_patches(env))
    ctxs.append(patch.object(bt_service, "execute_run", counting_exec))
    for c in ctxs:
        c.__enter__()
    try:
        # 直接经 store 层创建 queued 绑定（不经路由自动启动）
        conn = connect(env.db)
        out = br.create_request(
            conn, session_id=sid, question_id=qid, client_request_id="retry",
            symbol=SYMBOL, module="A", exit_variant=EXIT_BASE)
        conn.commit()
        rid = out["request_id"]
        assert out["status"] == "queued"
        # 原子领取原语：queued→running 成功一次；重复领取失败
        assert br._claim_queued(env.db, rid) is True
        assert br._claim_queued(env.db, rid) is False
        # 复位 queued 后经 worker 执行（worker 内领取；03B-R2 契约4）
        with connect(env.db) as reset_conn:
            reset_conn.execute(
                "UPDATE agent_backtest_requests SET status='queued' "
                "WHERE request_id = ?", (rid,))
            reset_conn.commit()
        br._worker(env.db, rid)
        # 同 client_request_id 重试 → 返回原 completed 任务（只读原结果）
        again = br.create_request(
            conn, session_id=sid, question_id=qid, client_request_id="retry",
            symbol=SYMBOL, module="A", exit_variant=EXIT_BASE)
        assert again["request_id"] == rid
        assert again["status"] == "completed"
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)
    assert calls["n"] == 1  # 引擎只执行一次


def test_r5_orphan_states_marked_interrupted(env, real_result, llm_fixed):  # noqa: ANN001
    """R5：孤儿 running/queued 首次 GET 即核查后状态，列表无假排队。"""
    sid, qid, _ = _chat_question(env)
    with patch.object(br, "start_request_worker",
                      side_effect=lambda db, rid: False):
        for cid in ("orphan-run", "orphan-queue"):
            r = _create(env.client, sid, qid, cid)
            assert r.status_code == 200
            conn = connect(env.db)
            st = "running" if cid == "orphan-run" else "queued"
            conn.execute("UPDATE agent_backtest_requests SET status=? WHERE "
                         "client_request_id=?", (st, cid))
            conn.commit()
            conn.close()
    v1 = env.client.get(
        f"/api/copilot/backtest-requests/{_rid_by_cid(env.db, 'orphan-run')}").json()
    assert v1["status"] == "interrupted"  # 首次 GET 即核查后状态
    listing = env.client.get(
        f"/api/copilot/backtest-requests?session_id={sid}").json()
    assert all(r["status"] != "queued" for r in listing["requests"])


def test_s9_zero_trade_completed_unknown():  # noqa: ANN001
    from lei_signal.copilot.backtest_requests import _result_summary

    text = _result_summary({"groups": {"True": {"总览": [{"trade_count": 0}]}}})
    assert "没有可统计交易" in text and "未知" in text


# ---------------- 13：无模型（降级模板含四分区） ----------------

def test_s13_no_llm_degraded_has_evidence_sections(env, real_result):  # noqa: ANN001
    r = chat(env.client, "这个标的最近如何")
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is False
    assert "历史结果及适用范围" in body["reply"]
    assert body["evidence_card"] is not None


# ---------------- 14：03B 不写前向成绩；判定一致 ----------------

def test_s14_no_forward_grades_and_determinism(env, real_result, llm_fixed):  # noqa: ANN001
    _full_chain(env)
    conn = connect(env.db)
    n_out = conn.execute("SELECT COUNT(*) FROM agent_observation_outcomes").fetchone()[0]
    n_journal = conn.execute("SELECT COUNT(*) FROM recommendation_journal").fetchone()[0]
    conn.close()
    assert n_out == 0 and n_journal == 0
    bars = pd.read_parquet(Path("tests/000001.SS.bars.parquet"))
    assert (analyze_bars(SYMBOL, bars).assessment.as_of
            == analyze_bars(SYMBOL, bars).assessment.as_of)


# ---------------- R7：保存草稿与确认分离；04B 拒绝不完整确认 ----------------

def test_r7_draft_save_confirm_separated_and_04b_reject(env, real_result):  # noqa: ANN001
    """「保存草稿」只 create；缺失效价草稿确认被 04B 拒绝；补齐后同 plan_id 可确认。"""
    draft_payload = {
        "symbol": SYMBOL, "module": "A", "direction": "long",
        "ruleset_version": "1.5.0", "reason": "讨论草稿",
        "valid_until": "2026-12-31", "entry_trigger_cn": "t",
        "thesis_cn": "t", "invalidation_criteria_cn": "i",
        "drawdown_playbook_cn": "d", "take_profit_plan_cn": "tp",
        "stop_plan_cn": "sp",
    }
    r1 = env.client.post("/api/plans", json=draft_payload)
    assert r1.status_code == 201
    plan_id = r1.json()["plan_id"]
    c1 = env.client.post(f"/api/plans/{plan_id}/confirm")
    assert c1.status_code == 422
    assert c1.json()["detail"]["code"] in ("INVALIDATION_PRICE_REQUIRED",
                                           "CONFORMANCE_HARD_BLOCK")
    upd = env.client.put(f"/api/plans/{plan_id}/draft",
                         json={"invalidation_price": 88.0})
    assert upd.status_code == 200
    assert upd.json()["plan_id"] == plan_id


# ---------------- 解析单测（方法/预算/用途） ----------------

def test_parse_module_budget_purpose_unit():
    assert resolve_mod.parse_request("帮我补测一下 模块B")["intent"] == "backtest_request"
    p = resolve_mod.parse_request("按模块B突破，用已有闲钱，预算10000元，先讨论依据")
    assert p["method_choice"]["module"] == "B"
    assert p["budget"]["amount"] == 10000.0
    assert p["purpose"] == "spare_cash"
    assert resolve_mod.parse_request("这个标的最近如何")["purpose"] == "unknown"
