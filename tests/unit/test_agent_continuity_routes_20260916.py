"""C1/C2/C3 路由级固定验收（主控复验 2026-09-16）：真实路由 + 落库原文核对。

不只测文案 helper：经 /api/agent/chat 与 /api/agent/chat/stream 真实路由提问，
再读 /api/agent/sessions/{sid}/messages 核对**落库的**回答原文。
模型不可用（load_ark_config → None），回答走系统确定性/降级直出，断言稳定。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import lei_signal.plans.llm as llm
from lei_signal.api.routes import agent as agent_routes
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.sessions import append_message, create_session
from lei_signal.storage.sqlite_store import connect

SYMBOL = "000300.SS"


def _fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    bars = pd.read_parquet(Path("tests/000300.SS.bars.parquet"))
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name="沪深300", bars=frame, report=report, info=info))


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = str(tmp_path / "t.db")
    connect(db).close()
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db, ttl_seconds=900)
    app = FastAPI()
    app.state.analysis_service = service
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.portfolio_db_path = db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    app.include_router(agent_routes.router)
    monkeypatch.setattr(llm, "load_ark_config", lambda: None)  # 无模型 → 系统直出
    return TestClient(app), db


def _seed_turn(db: str, session_id: str, user_text: str, symbol: str,
               as_of: str, verdict: str, n: int) -> None:
    """播种一轮已落库历史（用户问题 + 带冻结证据卡的 assistant 回答）。"""
    with connect(db) as conn:
        append_message(conn, session_id, "user", user_text, False, {})
        append_message(conn, session_id, "assistant", "（当时的回答）", True, {
            "resolved_symbol": symbol,
            "evidence_card": {"facts": {
                "symbol": symbol, "display_name": "沪深300", "as_of": as_of,
                "verdict_cn": verdict, "buy_point_candidate_n": n}},
        })


def _mk_session(db: str, symbol: str = SYMBOL) -> str:
    with connect(db) as conn:
        return create_session(conn, symbol, "验收会话").session_id


def _chat(client: TestClient, sid: str, message: str, cid: str) -> dict:
    r = client.post("/api/agent/chat", json={
        "session_id": sid, "context_kind": "symbol", "symbol": SYMBOL,
        "message": message, "client_request_id": cid})
    assert r.status_code == 200, r.text
    return r.json()


def _chat_stream(client: TestClient, sid: str, message: str, cid: str) -> tuple[str, dict]:
    text, done = "", {}
    with client.stream("POST", "/api/agent/chat/stream", json={
            "session_id": sid, "context_kind": "symbol", "symbol": SYMBOL,
            "message": message, "client_request_id": cid}) as r:
        et = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                et = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            d = json.loads(line[5:])
            if et == "token":
                text += str(d.get("t") or "")
            elif et == "done":
                done = d
    return text, done


def _saved_replies(client: TestClient, sid: str) -> list[str]:
    msgs = client.get(f"/api/agent/sessions/{sid}/messages").json()
    return [m["content"] for m in msgs if m["role"] == "assistant"]


# ---------------- C1：同日内容变化（普通路由 + 落库原文） ----------------

def test_c1_same_date_content_changed_plain_route(client):
    client, db = client
    sid = _mk_session(db)
    _seed_turn(db, sid, "现在怎么看", SYMBOL, "2026-08-06", "观察中", 0)
    body = _chat(client, sid, "和刚才相比有什么变化？", "c1-plain-1")
    assert "有变化" in body["reply"]
    assert "没有新数据" not in body["reply"]
    saved = _saved_replies(client, sid)
    assert saved[-1] == body["reply"]          # 落库原文 = 响应原文
    assert "有变化" in saved[-1]


def test_c1_date_regression_stream_route(client):
    """日期倒退（当前资料更旧）：流式路由落库原文必须是「退回较旧」。"""
    client, db = client
    sid = _mk_session(db)
    # 旧记录日期比 fixture 当前数据（2026-08-06）更"新"——构成倒退
    _seed_turn(db, sid, "现在怎么看", SYMBOL, "2026-09-01", "可执行", 1)
    text, done = _chat_stream(client, sid, "和刚才相比有什么变化？", "c1-stream-1")
    assert done.get("answer_state") == "answered"
    assert "更旧" in text and "退回较旧" in text
    saved = _saved_replies(client, sid)
    assert "退回较旧" in saved[-1]


def test_c2_atr_change_not_captured(client):
    """C2：ATR 止损变化问题走正常链路，不被资料比较抢答。"""
    client, db = client
    sid = _mk_session(db)
    _seed_turn(db, sid, "现在怎么看", SYMBOL, "2026-08-06", "观察中", 0)
    body = _chat(client, sid, "如果换成ATR止损，胜率会有什么变化？", "c2-plain-1")
    assert "没有新数据" not in body["reply"]
    assert "已比较的字段" not in body["reply"]
    assert "有变化：" not in body["reply"]


# ---------------- C3：会话背景记忆（路由链） ----------------

def test_c3_holding_background_kept(client):
    """固定验收：我已经持有 → 那现在重点看哪里（持仓语境不丢）。"""
    client, db = client
    sid = _mk_session(db)
    first = _chat(client, sid, "我已经持有了。", "c3-h-1")
    assert "持仓管理" in first["reply"]
    second = _chat(client, sid, "那现在重点看哪里？", "c3-h-2")
    assert "持仓管理" in second["reply"]       # 背景继承：不按首次买入
    assert "不适合讨论开新仓" not in second["reply"].split("\n")[0]


def test_c3_budget_purpose_background_kept(client):
    """固定验收：有一万闲钱 → 这笔钱怎么安排（已知事实不丢、不重复追问、
    不被当成写库授权）。"""
    client, db = client
    sid = _mk_session(db)
    first = _chat(client, sid, "我有一万闲钱，能不能买一点？", "c3-b-1")
    assert "闲钱" in first["reply"]            # 本条即识别用途，不追问
    assert "还差一项关键信息" not in first["reply"]
    second = _chat(client, sid, "这笔钱怎么安排？", "c3-b-2")
    assert "10000" in second["reply"] or "1万" in second["reply"]
    assert "闲钱" in second["reply"]
    assert "还差一项关键信息" not in second["reply"]   # 不重复追问
    assert "不会替你下单" in second["reply"]           # 讨论≠成交/授权
    # 落库核对
    saved = _saved_replies(client, sid)
    assert "不会替你下单" in saved[-1]


def test_c3_negation_not_a_fact(client):
    """否定句不写成预算事实。"""
    client, db = client
    sid = _mk_session(db)
    body = _chat(client, sid, "我没有一万元预算", "c3-n-1")
    assert "10000 元" not in body["reply"]
    assert "1 万元" not in body["reply"]


# ---------------- 收口二：语义守卫与精确归属（真实路由 + 临时库真实身份） ----------------

def test_r2_hypothetical_and_third_person_money(client):
    """收口二矩阵：假设的钱/朋友的钱不是用户事实。"""
    client, db = client
    sid = _mk_session(db)
    body = _chat(client, sid, "如果我有一万元，能不能买？", "r2-hyp-1")
    assert "10000 元" not in body["reply"]
    body2 = _chat(client, sid, "朋友有一万元闲钱", "r2-3rd-1")
    assert "10000 元" not in body2["reply"]


def test_r2_cash_is_not_holding(client):
    """收口二矩阵：「我手里有一万元闲钱」是现金不是持仓。"""
    client, db = client
    sid = _mk_session(db)
    body = _chat(client, sid, "我手里有一万元闲钱", "r2-cash-1")
    assert "从持仓管理角度讲" not in body["reply"]


def test_r2_correction_clears_holding(client):
    """收口二矩阵：我已经持有 → 我已经不持有了 → 重点看哪里（清除后不继承）。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "我已经持有了。", "r2-clr-1")
    _chat(client, sid, "我已经不持有了", "r2-clr-2")
    third = _chat(client, sid, "那现在重点看哪里？", "r2-clr-3")
    assert "从持仓管理角度讲" not in third["reply"]


def test_r2_unanswered_declaration_not_inherited(client):
    """收口二矩阵：问题1声明持有但没有回答；问题2切 510300（绑定 question_id=2）
    → 510300 的背景不认领问题1的持仓。"""
    client, db = client
    sid = _mk_session(db)
    # 问题1：只有 user 消息、没有绑定回答（模拟中断后未恢复）
    with connect(db) as conn:
        append_message(conn, sid, "user", "我已经持有了", False, {})
    body = _chat(client, sid, "510300 现在怎么看", "r2-unans-1")
    assert "从持仓管理角度讲" not in body["reply"]
    # 再问一句跟随问题，仍不得把无主声明认领成 510300 持仓
    follow = _chat(client, sid, "那现在重点看哪里？", "r2-unans-2")
    assert "从持仓管理角度讲" not in follow["reply"]


def test_r2_amount_correction_consistent(client):
    """收口二矩阵：本条更正金额——「不是一万，是五千」后背景新值 5000、
    旧值 10000 不再出现（经后续资金问题观察背景一致性）。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "我有一万闲钱，能不能买一点？", "r2-amt-1")
    _chat(client, sid, "不是一万，是五千", "r2-amt-2")
    third = _chat(client, sid, "那这笔钱怎么安排？", "r2-amt-3")
    assert "5000" in third["reply"]
    assert "10000" not in third["reply"]


# ---------------- 三轮收口（主控复核 2026-09-17）：撤销须本人肯定、用途同界 ----------------

def _last_stored_reply(client_test: TestClient, sid: str) -> str:
    msgs = client_test.get(f"/api/agent/sessions/{sid}/messages").json()
    return [m for m in msgs if m["role"] == "assistant"][-1]["content"]


def test_r3_negated_self_clear_preserves_holding(client):
    """「我已经持有了 → 我没有清仓」：否定清仓动作不清除持仓背景，
    后续问题仍按持仓管理口径回答，且落库回答与接口回答一致。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "我已经持有了", "r3-ngc-1")
    _chat(client, sid, "我没有清仓", "r3-ngc-2")
    third = _chat(client, sid, "那现在重点看哪里？", "r3-ngc-3")
    assert "从持仓管理角度讲" in third["reply"]
    assert third["reply"] == _last_stored_reply(client, sid)


def test_r3_friend_clear_does_not_touch_own_background(client):
    """「我已经持有了 → 朋友清仓了」：第三人清仓不动本人持仓背景。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "我已经持有了", "r3-fc-1")
    _chat(client, sid, "朋友清仓了", "r3-fc-2")
    third = _chat(client, sid, "那现在重点看哪里？", "r3-fc-3")
    assert "从持仓管理角度讲" in third["reply"]
    assert third["reply"] == _last_stored_reply(client, sid)


def test_r3_friend_purpose_not_user_background(client):
    """「朋友有一万元闲钱」：金额与用途都不进本人背景——后续资金问题
    不把朋友的闲钱当作用户已声明用途（不出现「你说过…闲钱」）。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "朋友有一万元闲钱", "r3-fp-1")
    second = _chat(client, sid, "那这笔钱怎么安排？", "r3-fp-2")
    assert "10000" not in second["reply"]
    assert "你说过这是一笔已有的闲钱" not in second["reply"]
    assert second["reply"] == _last_stored_reply(client, sid)


# ---- 三轮收口（主控复核 r3）：分句级组合场景（路由级真实绑定链） ----

def test_r4_own_clear_inside_mixed_clause(client):
    """「我已经持有了 → 朋友还持有，但我已经清仓了」：本人分句清仓生效，
    后续不再按持仓管理口径回答；落库回答与接口回答一致。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "我已经持有了", "r4-mix-1")
    _chat(client, sid, "朋友还持有，但我已经清仓了", "r4-mix-2")
    third = _chat(client, sid, "那现在重点看哪里？", "r4-mix-3")
    assert "从持仓管理角度讲" not in third["reply"]
    assert third["reply"] == _last_stored_reply(client, sid)


def test_r4_income_purpose_after_negated_spare(client):
    """「我有一万闲钱 → 我没有闲钱，这是每月工资定投」：闲钱用途撤销、
    本人定投用途生效（不重复追问用途），旧金额不再出现。"""
    client, db = client
    sid = _mk_session(db)
    _chat(client, sid, "我有一万闲钱，能不能买一点？", "r4-inc-1")
    _chat(client, sid, "我没有闲钱，这是每月工资定投", "r4-inc-2")
    third = _chat(client, sid, "那这笔钱怎么安排？", "r4-inc-3")
    assert "10000" not in third["reply"]  # 撤销后旧金额不再出现
    assert "持续投入的新收入" in third["reply"]  # 本人定投用途生效
    assert "你说过这是一笔已有的闲钱" not in third["reply"]
    assert third["reply"] == _last_stored_reply(client, sid)
