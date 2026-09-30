"""聊天请求的身份固定与回答精确绑定（03B-R2 契约1 + 03B-R3 S4，2026-09-08）。

统一事务入口：在创建会话、落问题、调用模型**之前**处理同编号请求的重试
与冲突——

- 首次 session_id 为空的同编号重试：返回**原会话、原问题、原回答**（按
  ``answer_message_id`` 精确取回，不按「问题之后第一条 assistant」猜——
  多问题交错/补测卡插入时会认错回答）；
- 指定了会话则必须与原归属一致；同编号换消息/对象/上下文 → 409 冲突；
- 身份核对走 ``agent_chat_requests`` 的精确主键（迁移 028/029），不做全库
  LIKE 模糊查询；并发第一次请求由主键约束兜底，只有一个问题；
- 回答状态机（迁移 029 + 2026-09-15 补修二）：``pending→generating→answered``
  或 ``→incomplete``（流中断/未正常收尾/截断：部分原文绑定保留，但不算完成）。
  生成前原子领取（pending/incomplete→generating；过期 generating 可凭
  state_at 比对领取回收），回答插入与 answered 标记同一事务——崩溃或中断
  窗口留下明确状态，重试返回**未完成**、对原问题**重新生成**或按固定逻辑
  恢复**原问题**，绝不复用下一问题或补测卡，也不把半截话回充当完成。

request_hash 是业务内容摘要：消息原文 + 上下文类型 + 传入对象。会话归属
**不**进哈希（首次为空的重试要能命中原会话）；解析出的标的也不进（那是
本轮派生结果，不是请求身份）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

__all__ = [
    "ChatClaim",
    "chat_request_hash",
    "enter_chat_request",
    "attach_question_to_claim",
    "build_replay",
    "build_incomplete",
    "mark_answered",
    "mark_incomplete",
    "release_generation",
    "retry_identity_for",
    "ChatRequestConflict",
]

#: 生成租约：generating 状态超过该秒数且无绑定回答，视为生成方失联，
#: 重试可凭 state_at 比对领取并按固定逻辑恢复原问题。
ANSWER_LEASE_SECONDS = 600


class ChatRequestConflict(ValueError):
    """同编号不同业务内容/不同会话归属——API 层映射 409。"""


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def chat_request_hash(*, message: str, context_kind: str | None,
                      symbol: str | None) -> str:
    """请求业务内容摘要（稳定序列化；会话归属不参与）。"""
    payload = json.dumps(
        {"message": message or "", "context_kind": context_kind or "",
         "symbol": symbol or ""},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChatClaim:
    client_request_id: str
    session_id: str
    question_id: int
    request_hash: str
    answer_message_id: int | None = None
    answer_state: str = "pending"
    state_at: str = ""


def _claim_from_row(row: sqlite3.Row) -> ChatClaim:
    return ChatClaim(
        client_request_id=row["client_request_id"],
        session_id=row["session_id"],
        question_id=int(row["question_id"]),
        request_hash=row["request_hash"],
        answer_message_id=(int(row["answer_message_id"])
                           if row["answer_message_id"] else None),
        answer_state=str(row["answer_state"] or "pending"),
        state_at=str(row["state_at"] or ""),
    )


def find_claim(conn: sqlite3.Connection, client_request_id: str) -> ChatClaim | None:
    row = conn.execute(
        "SELECT * FROM agent_chat_requests WHERE client_request_id = ?",
        (client_request_id,)).fetchone()
    return _claim_from_row(row) if row else None


@dataclass(frozen=True)
class EnterOutcome:
    """统一入口结果：
    replay=按精确绑定复用原回答（调用方直接返回，不再准备/建模）；
    proceed=新问题正常往下走（claim_cid 非 None 表示需回填问题号）；
    resume=原问题回答缺失，按固定逻辑继续生成**该问题**的回答
    （question_id 已定，调用方不得再落新 user 消息）；
    incomplete=回答正在生成中（未完成明确状态），调用方原样返回。"""

    kind: str                      # "replay" | "proceed" | "resume" | "incomplete"
    session_id: str | None = None
    claim_cid: str | None = None
    question_id: int | None = None
    replay_reply: dict[str, Any] | None = None
    incomplete_reply: dict[str, Any] | None = None
    #: 本次领号后 claim 行的 state_at（仅 proceed/resume=本次持有生成权时非空）。
    #: 失败释放（release_generation）凭它做 CAS，避免误伤租约回收后的新主。
    claim_state_at: str | None = None


def _assistant_by_id(conn: sqlite3.Connection,
                     message_id: int | None) -> sqlite3.Row | None:
    if not message_id:
        return None
    return conn.execute(
        "SELECT * FROM agent_messages WHERE message_id = ?", (message_id,)).fetchone()


def _replay_payload(conn: sqlite3.Connection, claim: ChatClaim) -> dict[str, Any]:
    """命中重试：按 claim 绑定的**原回答消息号**精确取回（含证据卡与归属），
    不按相邻位置猜。旧记录未绑定回答（answer_message_id 为空）→ 未完成。"""
    row = _assistant_by_id(conn, claim.answer_message_id)
    if row is None:
        return build_incomplete(claim, reason="原回答未生成或归属不可考（旧记录不补猜）")
    try:
        meta = json.loads(row["meta_json"] or "{}")
    except (TypeError, ValueError):
        meta = {}
    # 归属自证：回答行上绑定的 question_id 与领号不一致 → 标未知，不复用
    bound_qid = row["question_id"]
    if bound_qid is not None and int(bound_qid) != claim.question_id:
        return build_incomplete(claim, reason="原回答归属无法证明（不补猜）")
    return {
        "session_id": claim.session_id,
        "question_id": claim.question_id,
        "reply": row["content"],
        "grounded": bool(row["grounded"]),
        "trace": meta.get("trace") or [],
        "resolved_symbol": meta.get("resolved_symbol"),
        "evidence_card": meta.get("evidence_card"),
        # T3：同一问题的原产物随重试一起回来（不重读新材料重建成另一份）
        "plan_artifact": meta.get("plan_artifact"),
        "answer_state": "answered",
        # UX 第一期：当时的下一步动作随重试原样回来
        "next_steps": meta.get("next_steps") or [],
    }


def build_incomplete(claim: ChatClaim, *, reason: str) -> dict[str, Any]:
    """同一问题未生成回答时的**明确未完成**出口（不复用下一问题/补测卡）。"""
    return {
        "session_id": claim.session_id,
        "question_id": claim.question_id or None,
        "reply": f"该问题的回答尚未生成完成（{reason}）；请稍后重试，系统将只对原问题恢复生成。",
        "grounded": False,
        "trace": [],
        "resolved_symbol": None,
        "evidence_card": None,
        "answer_state": claim.answer_state or "pending",
    }


def _lease_expired(claim: ChatClaim) -> bool:
    if not claim.state_at:
        return True  # 旧记录无时间戳：可回收（无绑定回答时）
    try:
        started = datetime.fromisoformat(claim.state_at)
    except ValueError:
        return True
    return _now() - started > timedelta(seconds=ANSWER_LEASE_SECONDS)


def _claim_generation(conn: sqlite3.Connection, claim: ChatClaim) -> str | None:
    """原子领取生成权：pending/incomplete→generating，或过期 generating 凭
    state_at 比对回收（CAS）。返回 None=他人正在生成（未完成出口）；
    成功时返回本次写入的 state_at（供失败释放做 CAS，不误伤新主）。
    ``incomplete`` 是上次生成以未完成收场的状态：重试凭本 CAS 重新领取，
    并发重复重试只有一个胜出、不重复生成。"""
    now = _now_iso()
    if claim.answer_state == "pending":
        cur = conn.execute(
            "UPDATE agent_chat_requests SET answer_state='generating', state_at=? "
            "WHERE client_request_id=? AND answer_state='pending'",
            (now, claim.client_request_id))
    elif claim.answer_state == "incomplete":
        cur = conn.execute(
            "UPDATE agent_chat_requests SET answer_state='generating', state_at=? "
            "WHERE client_request_id=? AND answer_state='incomplete'",
            (now, claim.client_request_id))
    else:  # generating 且租约已过期：CAS 回收
        cur = conn.execute(
            "UPDATE agent_chat_requests SET answer_state='generating', state_at=? "
            "WHERE client_request_id=? AND answer_state='generating' AND state_at=?",
            (now, claim.client_request_id, claim.state_at))
    conn.commit()
    return now if cur.rowcount == 1 else None


def release_generation(conn: sqlite3.Connection, client_request_id: str, *,
                       expected_state_at: str | None = None) -> bool:
    """生成方以**失败/断连收场且未留下任何回答**时，把生成权放回
    ``pending``（2026-09-15 agent-ask-stability）。

    修前：准备失败/问题落库失败/回答保存失败/客户端断连后，claim 停在
    ``generating``——同身份重试在租约（600 秒）内只得到「回答正在生成或
    重试中」，用户无法立即继续处理原问题。释放后重试按既有 CAS
    （pending→generating）立即恢复。

    ``expected_state_at`` 给出领号时的 state_at：CAS 防误伤——若租约已被
    他人回收重领（state_at 已变），本次释放不生效。只从 generating 放回
    pending；已有终态（answered/incomplete）不动。"""
    if expected_state_at is not None:
        cur = conn.execute(
            "UPDATE agent_chat_requests SET answer_state='pending' "
            "WHERE client_request_id=? AND answer_state='generating' AND state_at=?",
            (client_request_id, expected_state_at))
    else:
        cur = conn.execute(
            "UPDATE agent_chat_requests SET answer_state='pending' "
            "WHERE client_request_id=? AND answer_state='generating'",
            (client_request_id,))
    conn.commit()
    return cur.rowcount == 1


def mark_answered(conn: sqlite3.Connection, client_request_id: str,
                  message_id: int) -> None:
    """回答落库后绑定（与回答插入同一事务时由调用方控制；单独调用兜底）。"""
    conn.execute(
        "UPDATE agent_chat_requests SET answer_state='answered', "
        "answer_message_id=?, state_at=? WHERE client_request_id=?",
        (int(message_id), _now_iso(), client_request_id))
    conn.commit()


def mark_incomplete(conn: sqlite3.Connection, client_request_id: str,
                    message_id: int) -> None:
    """回答以**未完成**收场（流中断/未正常收尾/截断，主控复核 2026-09-15
    固定补修二）：部分原文照常绑定，但状态记 ``incomplete`` 而非 answered——
    同编号重试按 :func:`_claim_generation` 重新领取生成权，对原问题再生成，
    不回放半截话。"""
    conn.execute(
        "UPDATE agent_chat_requests SET answer_state='incomplete', "
        "answer_message_id=?, state_at=? WHERE client_request_id=?",
        (int(message_id), _now_iso(), client_request_id))
    conn.commit()


def _check_claim(conn: sqlite3.Connection, claim: ChatClaim, *,
                 request_hash: str, session_id: str | None) -> EnterOutcome:
    """领到的号与本次请求核对：内容/会话不一致即冲突；一致则按回答状态分流。"""
    if claim.request_hash != request_hash:
        raise ChatRequestConflict(
            "同一请求编号已用于不同内容（消息/对象/上下文不一致）；"
            "请换新编号或恢复原内容，不重复回答也不错挂原问题")
    if session_id and session_id != claim.session_id:
        raise ChatRequestConflict(
            f"同一请求编号已归属会话 {claim.session_id}，与传入会话 "
            f"{session_id} 不一致；不能把原问题挂到另一会话")
    if claim.answer_state == "answered" and claim.answer_message_id:
        return EnterOutcome(kind="replay",
                            replay_reply=_replay_payload(conn, claim))
    # 未生成 / 生成中 / 上次未完成：先判租约，再原子领取生成权
    if claim.answer_state == "generating" and not _lease_expired(claim):
        return EnterOutcome(
            kind="incomplete", session_id=claim.session_id,
            question_id=claim.question_id or None,
            incomplete_reply=build_incomplete(claim, reason="回答正在生成或重试中"))
    claimed_at = _claim_generation(conn, claim)
    if claimed_at is None:
        return EnterOutcome(
            kind="incomplete", session_id=claim.session_id,
            question_id=claim.question_id or None,
            incomplete_reply=build_incomplete(claim, reason="回答正在生成或重试中"))
    if claim.question_id:
        # 原问题已落库、回答缺失：按固定逻辑恢复**该问题**（不复用下一问题）
        return EnterOutcome(kind="resume", session_id=claim.session_id,
                            claim_cid=claim.client_request_id,
                            question_id=claim.question_id,
                            claim_state_at=claimed_at)
    # 领号后、问题落库前崩溃：续用原会话正常走流程，稍后补挂问题号
    return EnterOutcome(kind="proceed", session_id=claim.session_id,
                        claim_cid=claim.client_request_id,
                        claim_state_at=claimed_at)


def enter_chat_request(
    conn: sqlite3.Connection, *, client_request_id: str | None,
    request_hash: str, session_id: str | None,
    new_session_symbol: str | None, new_session_title: str,
    request_message: str = "", request_context_kind: str = "",
    request_symbol: str = "",
) -> EnterOutcome:
    """统一事务入口（契约1/S4）：核对/领取请求编号，必要时在同一写事务内
    创建会话并领取生成权；返回重试复用/恢复/未完成/继续执行的裁决。

    二轮复验（2026-09-15 遗漏二）：领号时保存原始请求三输入（消息/上下文
    类型/对象），供历史接口为 incomplete 回答投影可核实的重试身份。"""
    if client_request_id:
        existing = find_claim(conn, client_request_id)
        if existing is not None:
            return _check_claim(conn, existing, request_hash=request_hash,
                                session_id=session_id)
    if session_id:
        # 已指定会话（存在性由调用方核对）：领号 + 领取生成权同事务
        if client_request_id:
            now = _now_iso()
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO agent_chat_requests(client_request_id,"
                    " session_id, question_id, request_hash, created_at,"
                    " answer_state, state_at, request_message,"
                    " request_context_kind, request_symbol)"
                    " VALUES (?,?,0,?,?,'generating',?,?,?,?)",
                    (client_request_id, session_id, request_hash, now, now,
                     request_message or "", request_context_kind or "",
                     request_symbol or ""))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.rollback()
                winner = find_claim(conn, client_request_id)
                if winner is None:
                    raise
                return _check_claim(conn, winner, request_hash=request_hash,
                                    session_id=session_id)
        return EnterOutcome(kind="proceed", session_id=session_id,
                            claim_cid=client_request_id,
                            claim_state_at=now if client_request_id else None)
    # 需要新建会话：领号、建会话、领生成权同事务（并发重复编号只有一个成功）
    now = _now_iso()
    new_sid = f"sess_{uuid.uuid4().hex[:12]}"
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "INSERT INTO agent_sessions(session_id, symbol, title_cn, "
            "created_at, last_active_at) VALUES (?,?,?,?,?)",
            (new_sid, new_session_symbol, new_session_title, now, now))
        if client_request_id:
            conn.execute(
                "INSERT INTO agent_chat_requests(client_request_id, session_id,"
                " question_id, request_hash, created_at, answer_state, state_at,"
                " request_message, request_context_kind, request_symbol)"
                " VALUES (?,?,0,?,?,'generating',?,?,?,?)",
                (client_request_id, new_sid, request_hash, now, now,
                 request_message or "", request_context_kind or "",
                 request_symbol or ""))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        if not client_request_id:
            raise
        winner = find_claim(conn, client_request_id)
        if winner is None:
            raise
        return _check_claim(conn, winner, request_hash=request_hash,
                            session_id=session_id)
    return EnterOutcome(kind="proceed", session_id=new_sid,
                        claim_cid=client_request_id,
                        claim_state_at=now if client_request_id else None)


def attach_question_to_claim(conn: sqlite3.Connection,
                             client_request_id: str, question_id: int) -> None:
    """问题落库后把真实问题号回填到领号记录（崩溃窗口的收口）。"""
    conn.execute(
        "UPDATE agent_chat_requests SET question_id = ? "
        "WHERE client_request_id = ? AND question_id = 0",
        (int(question_id), client_request_id))
    conn.commit()


def build_replay(conn: sqlite3.Connection, client_request_id: str) -> dict[str, Any]:
    """按编号取原问题与原回答（并发首撞输家/重试共用的出口）。"""
    claim = find_claim(conn, client_request_id)
    if claim is None:
        return {}
    if claim.answer_state == "answered" and claim.answer_message_id:
        return _replay_payload(conn, claim)
    return build_incomplete(claim, reason="原回答尚未生成")


def retry_identity_for(conn: sqlite3.Connection,
                       client_request_id: str | None,
                       *, message_id: int | None = None) -> dict[str, Any] | None:
    """历史接口的**原问题重试身份**投影（二轮复验 2026-09-15 遗漏二）。

    仅当领号记录处于 ``incomplete``（上次生成未完成收场）且原始三输入已
    保存、问题号已回填时投影；``message_id`` 给出时还须与绑定的部分原文
    一致。已完成（answered）/旧记录（输入为空）/未回填问题号一律返回
    None——不可考=明确不可原问题重试，不伪造字段。"""
    if not client_request_id:
        return None
    claim = find_claim(conn, client_request_id)
    if claim is None or claim.answer_state != "incomplete":
        return None
    if not claim.question_id:
        return None
    if message_id is not None and claim.answer_message_id != message_id:
        return None
    row = conn.execute(
        "SELECT request_message, request_context_kind, request_symbol "
        "FROM agent_chat_requests WHERE client_request_id=?",
        (client_request_id,)).fetchone()
    if row is None or not row["request_message"]:
        return None
    return {
        "client_request_id": client_request_id,
        "message": row["request_message"],
        "context_kind": row["request_context_kind"] or "global",
        "symbol": row["request_symbol"] or None,
    }
