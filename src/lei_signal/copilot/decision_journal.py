"""Confirmed user judgments and their later reviews, separate from trade plans.

The original question, evidence snapshot, and answer remain in agent_messages.
These tables only bind that source to a review card and append user confirmations.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decision_reviews (
            review_id TEXT PRIMARY KEY,
            client_request_id TEXT NOT NULL UNIQUE,
            request_hash TEXT NOT NULL,
            decision_id TEXT,
            session_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            answer_message_id INTEGER,
            subject_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decision_review_claims (
            client_request_id TEXT PRIMARY KEY,
            request_hash TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','complete')),
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decision_records (
            decision_id TEXT PRIMARY KEY,
            initial_review_id TEXT NOT NULL UNIQUE,
            subject_key TEXT NOT NULL,
            subject_json TEXT NOT NULL,
            intent TEXT NOT NULL,
            thought TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decision_confirmations (
            confirmation_id TEXT PRIMARY KEY,
            client_request_id TEXT NOT NULL UNIQUE,
            request_hash TEXT NOT NULL,
            decision_id TEXT NOT NULL,
            review_id TEXT NOT NULL UNIQUE,
            choice TEXT NOT NULL,
            decision_note TEXT NOT NULL,
            watch_for TEXT NOT NULL,
            confirmed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_decision_conf_history
            ON decision_confirmations(decision_id, confirmed_at);
        CREATE TABLE IF NOT EXISTS decision_followups (
            followup_id TEXT PRIMARY KEY,
            client_request_id TEXT NOT NULL UNIQUE,
            request_hash TEXT NOT NULL,
            decision_id TEXT NOT NULL,
            review_id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('wait','no_action','review','plan','trade')),
            occurred_on TEXT NOT NULL,
            note TEXT NOT NULL,
            decision_snapshot_json TEXT NOT NULL,
            reference_json TEXT,
            recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_decision_followups_history
            ON decision_followups(decision_id, occurred_on, recorded_at);
    """)


def claim_review(conn: sqlite3.Connection, request_id: str, request_hash: str) -> bool:
    """Only one request calls the agent; an abandoned claim can be resumed."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT * FROM decision_review_claims WHERE client_request_id=?",
            (request_id,),
        ).fetchone()
        if row:
            if row["request_hash"] != request_hash:
                raise ValueError("相同请求编号对应不同审核内容")
            if row["status"] == "complete":
                raise ValueError("审核已完成但记录缺失，请核对存证")
            try:
                expired = datetime.fromisoformat(row["updated_at"]) < datetime.now(UTC) - timedelta(
                    minutes=10
                )
            except ValueError:
                expired = False
            if not expired:
                conn.commit()
                return False
            conn.execute(
                "UPDATE decision_review_claims SET updated_at=? WHERE client_request_id=?",
                (now_iso(), request_id),
            )
        else:
            conn.execute(
                "INSERT INTO decision_review_claims VALUES (?,?,?,?)",
                (request_id, request_hash, "pending", now_iso()),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise


def get_review_by_request(
    conn: sqlite3.Connection, request_id: str, request_hash: str
) -> dict | None:
    row = conn.execute(
        "SELECT request_hash,payload_json FROM decision_reviews WHERE client_request_id=?",
        (request_id,),
    ).fetchone()
    if row is None:
        return None
    if row["request_hash"] != request_hash:
        raise ValueError("相同请求编号对应不同审核内容")
    return json.loads(row["payload_json"])


def save_review(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    request_hash: str,
    review: dict,
    answer_message_id: int | None,
) -> dict:
    payload = {
        **review,
        "fingerprint": digest({k: v for k, v in review.items() if k != "fingerprint"}),
    }
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = get_review_by_request(conn, request_id, request_hash)
        if existing is not None:
            conn.commit()
            return existing
        conn.execute(
            "INSERT INTO decision_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                payload["review_id"],
                request_id,
                request_hash,
                payload["decision_id"],
                payload["answer"]["session_id"],
                payload["answer"]["question_id"],
                answer_message_id,
                payload["subject"]["key"],
                canonical(payload),
                payload["fingerprint"],
                payload["created_at"],
            ),
        )
        conn.execute(
            "UPDATE decision_review_claims SET status='complete',updated_at=? "
            "WHERE client_request_id=? AND request_hash=?",
            (now_iso(), request_id, request_hash),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return payload


def review_row(conn: sqlite3.Connection, review_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM decision_reviews WHERE review_id=?", (review_id,)).fetchone()


def record(conn: sqlite3.Connection, decision_id: str) -> dict | None:
    root = conn.execute(
        "SELECT * FROM decision_records WHERE decision_id=?", (decision_id,)
    ).fetchone()
    if root is None:
        return None
    rows = conn.execute(
        "SELECT c.*,r.payload_json FROM decision_confirmations c "
        "JOIN decision_reviews r ON r.review_id=c.review_id "
        "WHERE c.decision_id=? ORDER BY c.confirmed_at,c.rowid",
        (decision_id,),
    ).fetchall()
    history = [
        {
            "review": json.loads(row["payload_json"]),
            "choice": row["choice"],
            "decision_note": row["decision_note"],
            "confirmed_at": row["confirmed_at"],
        }
        for row in rows
    ]
    first = history[0] if history else None
    latest = history[-1] if history else None
    current_check = {
        "status": "unknown",
        "checked_at": now_iso(),
        "changes": [],
        "note": "尚未读取当前缓存；历史复核保留在 history 中",
    }
    return {
        "decision_id": decision_id,
        "subject": json.loads(root["subject_json"]),
        "intent": root["intent"],
        "thought": root["thought"],
        "watch_for": first["review"].get("watch_for", "") if first else "",
        "choice": latest["choice"] if latest else "observe",
        "decision_note": latest["decision_note"] if latest else "",
        "confirmed_at": first["confirmed_at"] if first else root["created_at"],
        "latest_review": latest["review"] if latest else None,
        "history": history,
        "followups": [
            {
                "followup_id": row["followup_id"],
                "kind": row["kind"],
                "occurred_on": row["occurred_on"],
                "note": row["note"],
                "recorded_at": row["recorded_at"],
                "review_id": row["review_id"],
                "decision_snapshot": json.loads(row["decision_snapshot_json"]),
                "reference": json.loads(row["reference_json"]) if row["reference_json"] else None,
            }
            for row in conn.execute(
                "SELECT * FROM decision_followups WHERE decision_id=? "
                "ORDER BY occurred_on, recorded_at, rowid", (decision_id,)
            ).fetchall()
        ],
        "current_check": current_check,
    }


def list_records(conn: sqlite3.Connection, limit: int = 30) -> list[dict]:
    rows = conn.execute(
        "SELECT decision_id FROM decision_records ORDER BY created_at DESC,rowid DESC LIMIT ?",
        (min(max(limit, 1), 30),),
    ).fetchall()
    return [item for row in rows if (item := record(conn, row["decision_id"]))]


def confirm(
    conn: sqlite3.Connection,
    *,
    review_id: str,
    fingerprint: str,
    choice: str,
    decision_note: str,
    request_id: str,
) -> dict:
    request_hash = digest(
        {
            "review_id": review_id,
            "fingerprint": fingerprint,
            "choice": choice,
            "decision_note": decision_note,
        }
    )
    conn.execute("BEGIN IMMEDIATE")
    try:
        duplicate = conn.execute(
            "SELECT * FROM decision_confirmations WHERE client_request_id=?",
            (request_id,),
        ).fetchone()
        if duplicate:
            if duplicate["request_hash"] != request_hash:
                raise ValueError("相同确认编号对应不同内容")
            result = record(conn, duplicate["decision_id"])
            conn.commit()
            return result
        confirmed_review = conn.execute(
            "SELECT * FROM decision_confirmations WHERE review_id=?", (review_id,)
        ).fetchone()
        if confirmed_review:
            if confirmed_review["request_hash"] != request_hash:
                raise ValueError("这张审核卡已有不同确认内容")
            result = record(conn, confirmed_review["decision_id"])
            conn.commit()
            return result
        row = review_row(conn, review_id)
        if row is None:
            raise LookupError("审核记录不存在")
        review = json.loads(row["payload_json"])
        if row["fingerprint"] != fingerprint or review["fingerprint"] != fingerprint:
            raise ValueError("审核内容已变化，请重新核对")
        if not review["can_confirm"]:
            raise ValueError("审核依据或回答未完成，不能确认")
        # Check the original question and exact answer once more at write time.
        q = conn.execute(
            "SELECT session_id,role,content,meta_json FROM agent_messages WHERE message_id=?",
            (row["question_id"],),
        ).fetchone()
        a = (
            conn.execute(
                "SELECT session_id,role,question_id,content,grounded,meta_json FROM agent_messages "
                "WHERE message_id=?",
                (row["answer_message_id"],),
            ).fetchone()
            if row["answer_message_id"]
            else None
        )
        if (
            not q
            or not a
            or q["session_id"] != row["session_id"]
            or a["session_id"] != row["session_id"]
            or a["question_id"] != row["question_id"]
            or q["role"] != "user"
            or a["role"] != "assistant"
            or not a["grounded"]
            or a["content"] != review["answer"]["text"]
        ):
            raise ValueError("原问题或回答身份无法核实")
        try:
            saved_evidence = json.loads(a["meta_json"] or "{}").get("evidence_card")
        except (TypeError, ValueError):
            saved_evidence = None
        if (
            not review.get("evidence_fingerprint")
            or digest(saved_evidence) != review["evidence_fingerprint"]
        ):
            raise ValueError("原回答依据已变化，请重新审核")
        try:
            snapshot = json.loads(q["meta_json"] or "{}").get("discussion_v1") or {}
        except (TypeError, ValueError):
            snapshot = {}
        subject = review["subject"]
        if review["thought"] not in q["content"] or (
            snapshot.get("portfolio_holding_id") != subject["id"]
            if subject["kind"] == "holding"
            else snapshot.get("symbol") != subject["id"]
        ):
            raise ValueError("原话或提问时产品材料无法核实")
        if row["decision_id"]:
            root = conn.execute(
                "SELECT * FROM decision_records WHERE decision_id=?", (row["decision_id"],)
            ).fetchone()
            if (
                root is None
                or root["subject_key"] != row["subject_key"]
                or root["thought"] != review["thought"]
            ):
                raise ValueError("原判断或产品身份无法核实")
            original = record(conn, row["decision_id"])
            if review["subject"]["kind"] == "holding":
                first_facts = original["history"][0]["review"].get("facts") or []
                original_code = next(
                    (f["value"] for f in first_facts if f["key"] == "holding_code"), None
                )
                new_code = next(
                    (f["value"] for f in review.get("facts", []) if f["key"] == "holding_code"),
                    None,
                )
                if original_code != new_code:
                    raise ValueError("原判断与本次审核的基金身份不同")
            decision_id = row["decision_id"]
        else:
            decision_id = "dec_" + uuid.uuid4().hex
            conn.execute(
                "INSERT INTO decision_records VALUES (?,?,?,?,?,?,?)",
                (
                    decision_id,
                    review_id,
                    row["subject_key"],
                    canonical(review["subject"]),
                    review["intent"],
                    review["thought"],
                    now_iso(),
                ),
            )
        when = now_iso()
        conn.execute(
            "INSERT INTO decision_confirmations VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "dco_" + uuid.uuid4().hex,
                request_id,
                request_hash,
                decision_id,
                review_id,
                choice,
                decision_note,
                review["watch_for"],
                when,
            ),
        )
        conn.commit()
        return record(conn, decision_id)
    except Exception:
        conn.rollback()
        raise
