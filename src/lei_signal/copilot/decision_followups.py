"""Confirmed, append-only follow-ups to a user's saved judgment.

Associations freeze source rows for later reading. They never change plans,
transactions, positions, or the original judgment.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from lei_signal.copilot import decision_journal as journal

SHANGHAI = ZoneInfo("Asia/Shanghai")
KINDS = frozenset({"wait", "no_action", "review", "plan", "trade"})
REFERENCE_KINDS = frozenset({"plan", "trade"})
PLAN_STATE_CN = {
    "draft": "草稿",
    "armed": "已确认，等待条件",
    "entered": "已进入",
    "exited": "已退出",
    "invalidated": "已失效",
    "superseded": "已被新计划替代",
    "abandoned": "已放弃",
}


class FollowupConflict(ValueError):
    """The request or current source conflicts with the saved judgment."""


def _fact(review: dict, key: str) -> str | None:
    for fact in review.get("facts") or []:
        if fact.get("key") == key and fact.get("value"):
            return str(fact["value"])
    return None


def _latest_confirmed(conn: sqlite3.Connection, decision_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT c.review_id,c.choice,c.decision_note,c.confirmed_at,r.payload_json "
        "FROM decision_confirmations c JOIN decision_reviews r ON r.review_id=c.review_id "
        "WHERE c.decision_id=? ORDER BY c.confirmed_at DESC,c.rowid DESC LIMIT 1",
        (decision_id,),
    ).fetchone()


def _initial_day(conn: sqlite3.Connection, decision_id: str) -> date:
    row = conn.execute(
        "SELECT confirmed_at FROM decision_confirmations WHERE decision_id=? "
        "ORDER BY confirmed_at,rowid LIMIT 1",
        (decision_id,),
    ).fetchone()
    if row is None:
        raise FollowupConflict("判断尚未由用户确认")
    value = datetime.fromisoformat(row["confirmed_at"])
    if value.tzinfo is None:
        raise FollowupConflict("原确认时间缺少时区，无法核对日期")
    return value.astimezone(SHANGHAI).date()


def _snapshot(row: sqlite3.Row) -> dict:
    # Freeze the complete saved row. A fixed field list silently misses new or
    # amended exit conditions. This is a local association snapshot, not a
    # claim about what the plan looked like at an earlier execution.
    return dict(row)


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _reference(conn: sqlite3.Connection, decision: dict, kind: str, ref_id: str) -> dict | None:
    table, key = ("trade_plans", "plan_id") if kind == "plan" else ("fund_trades", "trade_id")
    row = conn.execute(f"SELECT * FROM {table} WHERE {key}=?", (ref_id,)).fetchone()
    if row is None:
        return None
    subject = decision["subject"]
    review = decision["latest_review"] or {}
    if kind == "plan":
        if subject["kind"] == "symbol":
            valid = row["symbol"] == subject["id"]
        else:
            # The saved, confirmed same-holding material is the only authority
            # for this mapping. A code suffix or fund-name guess is insufficient.
            valid = _fact(review, "plan_id") == ref_id and bool(_fact(review, "holding_code"))
        if not valid:
            return None
        name = str(subject.get("name") or "产品名称待核")
        state = PLAN_STATE_CN.get(row["state"], "状态待核")
        created = str(row["created_at"] or "")[:10]
        try:
            created = date.fromisoformat(created).isoformat()
        except ValueError:
            created = "建立日期未记录"
        reason = " ".join(str(row["reason"] or "").split())
        brief = reason[:24] + ("…" if len(reason) > 24 else "")
        label = f"{name}计划 · {state} · {created}建立"
        if brief:
            label += f" · {brief}"
        href = f"/plans?plan_id={quote(ref_id, safe='')}"
    else:
        valid = subject["kind"] == "holding" and _fact(review, "holding_code") == row["fund_code"]
        if not valid:
            return None
        label = (
            f"{row['trade_date']} {row['fund_name']} {'买入' if row['side'] == 'buy' else '卖出'}"
        )
        href = "/portfolio?tab=trades"
    snapshot = _snapshot(row)
    fingerprint = journal.digest({"kind": kind, "id": ref_id, "snapshot": snapshot})
    return {
        "kind": kind,
        "reference_id": ref_id,
        "reference_fingerprint": fingerprint,
        "label": label,
        "snapshot": snapshot,
        "href": href,
    }


def options(conn: sqlite3.Connection, decision_id: str) -> dict:
    decision = journal.record(conn, decision_id)
    if decision is None:
        raise LookupError("判断记录不存在")
    initial_day = _initial_day(conn, decision_id).isoformat()
    items: list[dict] = []
    limitations: list[str] = []
    subject = decision["subject"]
    plans = []
    if not _has_table(conn, "trade_plans"):
        limitations.append("计划台账尚未建立，暂不能关联计划")
    elif subject["kind"] == "symbol":
        plans = conn.execute(
            "SELECT plan_id FROM trade_plans WHERE symbol=? ORDER BY created_at DESC,plan_id",
            (subject["id"],),
        ).fetchall()
    else:
        plan_id = _fact(decision["latest_review"] or {}, "plan_id")
        plans = (
            conn.execute("SELECT plan_id FROM trade_plans WHERE plan_id=?", (plan_id,)).fetchall()
            if plan_id
            else []
        )
        if not plan_id:
            limitations.append("已确认材料中没有同一持仓的计划编号，暂不能关联计划")
    for row in plans:
        if item := _reference(conn, decision, "plan", row["plan_id"]):
            items.append(item)
    code = (
        _fact(decision["latest_review"] or {}, "holding_code")
        if subject["kind"] == "holding"
        else None
    )
    if not _has_table(conn, "fund_trades"):
        limitations.append("基金成交台账尚未建立，暂不能关联成交")
    elif code:
        trades = conn.execute(
            "SELECT trade_id FROM fund_trades WHERE fund_code=? AND trade_date>=? "
            "ORDER BY trade_date DESC,created_at DESC,trade_id",
            (code, initial_day),
        ).fetchall()
        for row in trades:
            if item := _reference(conn, decision, "trade", row["trade_id"]):
                items.append(item)
    else:
        limitations.append("已确认材料中没有可核对的基金代码，暂不能关联成交")
    return {"items": items, "limitations": limitations}


def append(
    conn: sqlite3.Connection,
    *,
    decision_id: str,
    review_id: str,
    kind: str,
    request_id: str,
    confirmed: bool,
    occurred_on: str,
    note: str,
    reference_id: str | None,
    reference_fingerprint: str | None,
) -> dict:
    payload = {
        "decision_id": decision_id,
        "review_id": review_id,
        "kind": kind,
        "confirmed": confirmed,
        "occurred_on": occurred_on,
        "note": note,
        "reference_id": reference_id,
        "reference_fingerprint": reference_fingerprint,
    }
    request_hash = journal.digest(payload)
    conn.execute("BEGIN IMMEDIATE")
    try:
        duplicate = conn.execute(
            "SELECT request_hash,decision_id FROM decision_followups WHERE client_request_id=?",
            (request_id,),
        ).fetchone()
        if duplicate is not None:
            if duplicate["request_hash"] != request_hash:
                raise FollowupConflict("相同请求编号对应不同后续记录")
            result = journal.record(conn, duplicate["decision_id"])
            conn.commit()
            return result
        if not confirmed or kind not in KINDS:
            raise ValueError("请确认后续记录的类型和内容")
        if kind == "review" and not note.strip():
            raise ValueError("复盘需填写实际观察或认识")
        if (kind in REFERENCE_KINDS and not (reference_id and reference_fingerprint)) or (
            kind not in REFERENCE_KINDS
            and (reference_id is not None or reference_fingerprint is not None)
        ):
            raise ValueError("计划或成交关联须选择完整候选；普通记录不应关联候选")
        try:
            day = date.fromisoformat(occurred_on)
        except ValueError as exc:
            raise ValueError("日期格式须为 YYYY-MM-DD") from exc
        if day.isoformat() != occurred_on or day > datetime.now(SHANGHAI).date():
            raise ValueError("记录日期不能晚于今天")
        decision = journal.record(conn, decision_id)
        if decision is None:
            raise LookupError("判断记录不存在")
        if day < _initial_day(conn, decision_id):
            raise FollowupConflict("记录日期早于原判断确认日期")
        latest = _latest_confirmed(conn, decision_id)
        if latest is None or latest["review_id"] != review_id:
            raise FollowupConflict("判断已有新的确认审核，请刷新后再记录")
        reference = None
        if kind in REFERENCE_KINDS:
            candidate = _reference(conn, decision, kind, reference_id)
            if candidate is None:
                raise FollowupConflict("原计划或成交与此判断的产品身份不符")
            if candidate["reference_fingerprint"] != reference_fingerprint:
                raise FollowupConflict("计划或成交内容已变化，请刷新候选后确认")
            if kind == "trade":
                trade_day = date.fromisoformat(candidate["snapshot"]["trade_date"])
                if trade_day != day or trade_day < _initial_day(conn, decision_id):
                    raise FollowupConflict("成交日期须等于记录日期，且不早于原判断")
            reference = {
                "id": reference_id,
                "fingerprint": reference_fingerprint,
                "snapshot": candidate["snapshot"],
                "href": candidate["href"],
            }
        confirmed_review = json.loads(latest["payload_json"])
        decision_snapshot = {
            "decision_id": decision_id,
            "subject": decision["subject"],
            "intent": decision["intent"],
            "thought": decision["thought"],
            "watch_for": decision["watch_for"],
            "choice": latest["choice"],
            "decision_note": latest["decision_note"],
            "confirmed_at": latest["confirmed_at"],
            "review_id": review_id,
            "review_fingerprint": confirmed_review["fingerprint"],
            "review_facts": confirmed_review.get("facts") or [],
            "review_limitations": confirmed_review.get("limitations") or [],
        }
        conn.execute(
            "INSERT INTO decision_followups VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                "dfu_" + uuid.uuid4().hex,
                request_id,
                request_hash,
                decision_id,
                review_id,
                kind,
                occurred_on,
                note,
                journal.canonical(decision_snapshot),
                journal.canonical(reference) if reference else None,
                journal.now_iso(),
            ),
        )
        result = journal.record(conn, decision_id)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
