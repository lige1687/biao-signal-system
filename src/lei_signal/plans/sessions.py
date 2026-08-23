"""agent 会话层 CRUD（append-only）。多轮记忆的持久化载体。"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

__all__ = [
    "AgentMessage",
    "AgentSession",
    "append_message",
    "create_session",
    "get_session",
    "list_messages",
    "list_sessions",
]


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class AgentSession:
    session_id: str
    symbol: str | None
    title_cn: str
    created_at: str
    last_active_at: str


@dataclass(frozen=True, slots=True)
class AgentMessage:
    message_id: int
    session_id: str
    role: str
    content: str
    grounded: bool
    meta_json: str
    created_at: str


def create_session(
    conn: sqlite3.Connection, symbol: str | None, title_cn: str
) -> AgentSession:
    now = _utcnow()
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO agent_sessions(session_id, symbol, title_cn, created_at, last_active_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (session_id, symbol, title_cn, now, now),
    )
    conn.commit()
    return AgentSession(session_id, symbol, title_cn, now, now)


def _row_to_session(row: sqlite3.Row) -> AgentSession:
    return AgentSession(row["session_id"], row["symbol"], row["title_cn"],
                        row["created_at"], row["last_active_at"])


def get_session(conn: sqlite3.Connection, session_id: str) -> AgentSession | None:
    row = conn.execute(
        "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    return _row_to_session(row) if row else None


def list_sessions(
    conn: sqlite3.Connection, symbol: str | None = None, limit: int = 30
) -> list[AgentSession]:
    if symbol is None:
        rows = conn.execute(
            "SELECT * FROM agent_sessions ORDER BY last_active_at DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM agent_sessions WHERE symbol = ?"
            " ORDER BY last_active_at DESC, rowid DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    return [_row_to_session(r) for r in rows]


def append_message(
    conn: sqlite3.Connection,
    session_id: str,
    role: str,
    content: str,
    grounded: bool,
    meta: dict,
) -> AgentMessage:
    if role not in ("user", "assistant"):
        raise ValueError(f"role 非法: {role}")
    now = _utcnow()
    cur = conn.execute(
        "INSERT INTO agent_messages(session_id, role, content, grounded, meta_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, role, content, int(grounded), json.dumps(meta, ensure_ascii=False), now),
    )
    conn.execute(
        "UPDATE agent_sessions SET last_active_at = ? WHERE session_id = ?",
        (now, session_id),
    )
    conn.commit()
    return AgentMessage(
        int(cur.lastrowid or 0), session_id, role, content, grounded,
        json.dumps(meta, ensure_ascii=False), now,
    )


def list_messages(
    conn: sqlite3.Connection, session_id: str, limit: int = 20
) -> list[AgentMessage]:
    rows = conn.execute(
        "SELECT * FROM ("
        "  SELECT * FROM agent_messages WHERE session_id = ?"
        "  ORDER BY message_id DESC LIMIT ?"
        ") ORDER BY message_id ASC",
        (session_id, limit),
    ).fetchall()
    return [
        AgentMessage(r["message_id"], r["session_id"], r["role"], r["content"],
                     bool(r["grounded"]), r["meta_json"], r["created_at"])
        for r in rows
    ]
