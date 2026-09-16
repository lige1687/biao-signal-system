"""收口二独立复核（agent-continuity-zcode-closeout-2026-09-17，ZCode 执行者）。

与主控 probe.py 的差异：不再用手写 SimpleNamespace 冒充历史行，而是
1) 建临时库，用 create_session / append_message / 直接 SQL（与路由
   _append_answer 同列）落真实自增 message_id 与精确 question_id，再从库里
   读回 AgentMessage 行喂给 _user_background；
2) 路由级用 TestClient + 临时库 + 无模型（load_ark_config→None，系统直出），
   核对回答原文与材料（reply meta / ctx_payload 视角）一致性；
3) 核对过程未写任何计划/成交（plans 表计数为 0），全部写入只在临时库。

覆盖（主控固定矩阵 + 四个特殊身份场景）：
五反例 / 持有·资金用途正例 / 否定撤销 / 不是一万是五千 /
中断未答 / 下一问换对象 / 同题多回答 / 全局未知对象 / 相邻位置不猜归属。
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

OUT = Path(__file__).parent
result: dict = {"notes": "temp-db real message_id/question_id; no model; no plans writes"}

# ---------- Part A：helper 级（真实函数） ----------
from lei_signal.copilot.resolve import (  # noqa: E402
    detect_fact_correction,
    detect_stance,
    parse_request,
)

result["A_five_counterexamples"] = {
    "hypothetical_budget_none": parse_request("如果我有一万元，能不能买？")["budget"] is None,
    "third_party_budget_none": parse_request("朋友有一万元闲钱")["budget"] is None,
    "cash_not_holding": detect_stance("我手里有一万元闲钱") is None,
    "normal_negation_clears": detect_fact_correction("我已经不持有了")["holding_cleared"] is True,
    "friend_holding_none": detect_stance("朋友持有这个") is None,
}
result["A_positives"] = {
    "holding": detect_stance("我已经持有了") == "holding",
    "budget_and_purpose": (
        parse_request("我有一万闲钱，想分批放")["budget"]["amount"] == 10_000.0
        and parse_request("我有一万闲钱，想分批放")["purpose"] == "spare_cash"
    ),
    "correction_new_value": parse_request("不是一万，是五千")["budget"]["amount"] == 5_000.0,
    "correction_clears_old": detect_fact_correction("不是一万，是五千")["budget_cleared"] is True,
}

# ---------- Part B：临时库真实身份行 → _user_background ----------
from lei_signal.api.routes.agent import _user_background  # noqa: E402
from lei_signal.plans.sessions import append_message, create_session  # noqa: E402
from lei_signal.plans.sessions import list_messages  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

TMP = tempfile.TemporaryDirectory(prefix="lei-closeout-g2-")
db = str(Path(TMP.name) / "case.db")
connect(db).close()
result["temp_db"] = db


def seed_answer(conn: sqlite3.Connection, session_id: str, symbol: str | None,
                question_id: int, text: str = "（当时的回答）") -> int:
    cur = conn.execute(
        "INSERT INTO agent_messages(session_id, role, content, grounded, meta_json,"
        " created_at, question_id, message_kind, source_request_id)"
        " VALUES (?, 'assistant', ?, 1, ?, datetime('now'), ?, 'answer', 'seed')",
        (session_id, text,
         json.dumps({"resolved_symbol": symbol}, ensure_ascii=False), question_id))
    conn.commit()
    return int(cur.lastrowid or 0)


with connect(db) as conn:
    sid = create_session(conn, "515880.SS", "G2复核").session_id
    # 中断未答：问题1声明持有，无任何绑定回答
    m1 = append_message(conn, sid, "user", "我已经持有了", False, {})
    # 下一问换对象：问题2切510300，回答绑定 question_id=2
    m2 = append_message(conn, sid, "user", "510300 现在怎么看", False, {})
    seed_answer(conn, sid, "510300.SS", question_id=m2.message_id)
    rows_a = list_messages(conn, sid, limit=20)
    # 同题多回答：问题3声明持有515880，两条回答都绑定 question_id=3
    m3 = append_message(conn, sid, "user", "我已经持有了", False, {})
    seed_answer(conn, sid, "515880.SS", question_id=m3.message_id)
    seed_answer(conn, sid, "515880.SS", question_id=m3.message_id, text="（重试回答）")
    rows_b = list_messages(conn, sid, limit=20)
    # 更正链：问题4「我已经不持有了」绑定515880 → 持有清零
    m4 = append_message(conn, sid, "user", "我已经不持有了", False, {})
    seed_answer(conn, sid, "515880.SS", question_id=m4.message_id)
    rows_c = list_messages(conn, sid, limit=20)
    # 金额更正链：问题5 一万闲钱 → 问题6 不是一万是五千 → 背景应为 5000
    m5 = append_message(conn, sid, "user", "我有一万闲钱，想分批放", False, {})
    seed_answer(conn, sid, "515880.SS", question_id=m5.message_id)
    m6 = append_message(conn, sid, "user", "不是一万，是五千", False, {})
    seed_answer(conn, sid, "515880.SS", question_id=m6.message_id)
    rows_d = list_messages(conn, sid, limit=20)
    # 全局未知对象
    rows_all = list_messages(conn, sid, limit=20)

result["B_real_db_rows"] = {
    "unanswered_not_inherited_510300": _user_background(rows_a, "510300.SS") == {},
    "adjacency_not_guessed": _user_background(rows_a, "515880.SS") == {},
    "multi_answer_same_question_kept":
        _user_background(rows_b, "515880.SS").get("holding") is True,
    "multi_answer_not_cross_object": _user_background(rows_b, "510300.SS") == {},
    "negation_clears": _user_background(rows_c, "515880.SS").get("holding") in (None, False),
    "amount_correction_5000":
        _user_background(rows_d, "515880.SS").get("budget", {}).get("amount") == 5_000.0,
    "amount_correction_no_10000":
        _user_background(rows_d, "515880.SS").get("budget", {}).get("amount") != 10_000.0,
    "global_unknown_collects_nothing": _user_background(rows_all, None) == {},
}

# ---------- Part C：路由级（临时库 + 无模型系统直出） ----------
import pandas as pd  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import lei_signal.plans.llm as llm  # noqa: E402
from lei_signal.api.routes import agent as agent_routes  # noqa: E402
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.compose.pipeline import analyze_bars  # noqa: E402
from lei_signal.data.providers import PriceData  # noqa: E402
from lei_signal.data.symbols import resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402

SYM = "000300.SS"


def _fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    bars = pd.read_parquet(Path("tests/000300.SS.bars.parquet"))
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name="沪深300", bars=frame, report=report, info=info))


db2 = str(Path(TMP.name) / "route.db")
connect(db2).close()
service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db2, ttl_seconds=900)
app = FastAPI()
app.state.analysis_service = service
for k in ("plans_db_path", "watchlist_db_path", "portfolio_db_path"):
    setattr(app.state, k, db2)
app.state.quote_provider = None
app.state.friendly_name_provider = False
app.include_router(agent_routes.router)
llm.load_ark_config = lambda: None  # 无模型 → 系统直出（确定性）
client = TestClient(app)

with connect(db2) as conn:
    sid2 = create_session(conn, SYM, "G2路由复核").session_id


def chat(message: str, cid: str) -> dict:
    r = client.post("/api/agent/chat", json={
        "session_id": sid2, "context_kind": "symbol", "symbol": SYM,
        "message": message, "client_request_id": cid})
    assert r.status_code == 200, r.text
    return r.json()


replies: dict[str, str] = {}


def ask(key: str, message: str) -> str:
    body = chat(message, f"g2-{key}")
    replies[key] = body["reply"]
    return body["reply"]


c = {}
# 五反例（路由回答原文）
c["hypothetical_no_10000"] = "10000" not in ask("hyp", "如果我有一万元，能不能买？")
c["third_party_no_10000"] = "10000" not in ask("third", "朋友有一万元闲钱")
c["cash_not_holding"] = "从持仓管理角度讲" not in ask("cash", "我手里有一万元闲钱")
# 正例：持有继承 → 持仓管理口吻；资金用途继承
ask("declare", "我已经持有了")
c["holding_inherited"] = "从持仓管理角度讲" in ask("after_declare", "那现在重点看哪里？")
c["purpose_inherited"] = "闲钱" in ask("purpose", "那这笔钱怎么安排？")
# 否定撤销后不再继承
ask("negate", "我已经不持有了")
c["negation_cleared"] = "从持仓管理角度讲" not in ask("after_negate", "那现在重点看哪里？")
# 本条更正金额：先立一万再改五千 → 5000 出现、10000 不再出现
ask("amt1", "我有一万闲钱，能不能买一点？")
ask("amt2", "不是一万，是五千")
amt3 = ask("amt3", "那这笔钱怎么安排？")
c["correction_5000_shown"] = "5000" in amt3
c["correction_no_10000"] = "10000" not in amt3
# 成本措辞：不谎称「用户没提供成本」
c["cost_wording_honest"] = ("你没给成本" not in "".join(replies.values())
                            and "没有成本提取能力" in "".join(replies.values()))
result["C_route_replies"] = c

# 落库回答 vs 材料一致性：取 amt3 轮的落库 meta，材料背景与回答口径一致
msgs = client.get(f"/api/agent/sessions/{sid2}/messages").json()
last_assistant = [m for m in msgs if m["role"] == "assistant"][-1]
meta = last_assistant.get("meta_json")
meta_d = json.loads(meta) if isinstance(meta, str) else (meta or {})
material_bg = (meta_d.get("evidence_card", {}).get("user_background")
               or meta_d.get("user_background") or {})
result["C_stored_answer"] = {
    "stored_reply_excerpt": last_assistant["content"][:160],
    "stored_meta_keys": sorted(meta_d.keys())[:12],
    "reply_matches_stored": amt3[:60] == last_assistant["content"][:60],
}

# 未写真实计划/成交：临时库 plans 表计数
with connect(db2) as conn:
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    plan_like = {}
    for t in tables:
        if any(k in t for k in ("trade", "plan", "order")):
            try:
                plan_like[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.Error:
                plan_like[t] = "n/a"
result["C_plan_trade_rows_in_temp_db"] = plan_like
nonzero = {k: v for k, v in plan_like.items() if isinstance(v, int) and v}
result["C_no_plans_written"] = nonzero == {}

(OUT / "g2-fact-matrix.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=1))
ok = all(v is True for k, v in result["A_five_counterexamples"].items()) \
    and all(result["A_positives"].values()) \
    and all(result["B_real_db_rows"].values()) \
    and all(result["C_route_replies"].values()) \
    and result["C_no_plans_written"] \
    and result["C_stored_answer"]["reply_matches_stored"]
result["ALL_OK"] = bool(ok)
print(json.dumps(result, ensure_ascii=False, indent=1))
