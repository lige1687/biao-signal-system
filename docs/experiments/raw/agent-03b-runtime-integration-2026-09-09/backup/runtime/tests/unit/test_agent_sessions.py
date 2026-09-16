# tests/unit/test_agent_sessions.py
"""会话层 CRUD：append-only、最近 N 条、按标的过滤。"""
import sqlite3

import pytest

from lei_signal.plans.sessions import (
    append_message,
    create_session,
    get_session,
    list_messages,
    list_sessions,
)
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    connection = connect(str(tmp_path / "lab.db"))
    yield connection
    connection.close()


def test_create_and_get_session(conn):
    s = create_session(conn, "000300.SS", "沪深300 讨论")
    assert s.symbol == "000300.SS"
    got = get_session(conn, s.session_id)
    assert got is not None and got.title_cn == "沪深300 讨论"


def test_global_session_symbol_nullable(conn):
    s = create_session(conn, None, "全局")
    assert s.symbol is None


def test_append_and_list_messages_recent_first_window(conn):
    s = create_session(conn, "IGV", "t")
    for i in range(15):
        append_message(conn, s.session_id, "user" if i % 2 == 0 else "assistant", f"m{i}", i % 2 == 0, {"i": i})
    msgs = list_messages(conn, s.session_id, limit=6)
    assert len(msgs) == 6
    assert [m.content for m in msgs] == ["m9", "m10", "m11", "m12", "m13", "m14"]


def test_append_updates_last_active(conn):
    s = create_session(conn, "IGV", "t")
    append_message(conn, s.session_id, "user", "hi", False, {})
    got = get_session(conn, s.session_id)
    assert got.last_active_at >= s.created_at


def test_list_sessions_filters_symbol_and_sorts(conn):
    a = create_session(conn, "IGV", "a")
    b = create_session(conn, "SOXX", "b")
    append_message(conn, b.session_id, "user", "x", False, {})
    only_igv = list_sessions(conn, symbol="IGV")
    assert [s.session_id for s in only_igv] == [a.session_id]
    all_sessions = list_sessions(conn)
    assert all_sessions[0].session_id == b.session_id  # 最近活跃在前
