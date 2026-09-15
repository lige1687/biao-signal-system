"""写事务登记与锁等待诊断（2026-09-15 agent-ask-stability）。

固定矩阵：
- 显式 BEGIN IMMEDIATE 与隐式事务（首个 DML 起）都会登记/注销；
- 持锁期间第二个连接的 BEGIN IMMEDIATE 等待失败时，日志快照指认持锁方
  （位置/线程/持有毫秒），不含 SQL 参数；
- 慢等待/慢持有按阈值记日志；
- 行为与原生连接一致（返回值、行内容、with conn: 语义）。
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time

import pytest

from lei_signal.storage import write_tx
from lei_signal.storage.sqlite_store import connect
from lei_signal.storage.write_tx import (
    TrackedConnection,
    active_writers_snapshot,
    set_thresholds_for_tests,
)


@pytest.fixture(autouse=True)
def _thresholds():
    set_thresholds_for_tests(wait_ms=1500, hold_ms=3000)
    yield
    set_thresholds_for_tests(wait_ms=1500, hold_ms=3000)


def test_connect_returns_tracked_connection(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    assert isinstance(conn, TrackedConnection)
    # 迁移的 DDL 都已提交，连接打开后不应残留活跃写事务
    assert active_writers_snapshot() == []
    conn.close()


def test_explicit_begin_immediate_registers_and_unregisters(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    conn.execute("BEGIN IMMEDIATE")
    snap = active_writers_snapshot()
    assert len(snap) == 1
    assert snap[0]["explicit"] is True
    assert "test_write_tx_tracking" in snap[0]["site"]
    conn.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                 " VALUES('r1','v1','test')")
    conn.commit()
    assert active_writers_snapshot() == []
    conn.close()


def test_implicit_write_transaction_tracked_until_commit(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    conn.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                 " VALUES('r2','v1','test')")
    snap = active_writers_snapshot()
    assert len(snap) == 1 and snap[0]["explicit"] is False
    conn.rollback()
    assert active_writers_snapshot() == []
    conn.close()


def test_select_does_not_register(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    conn.execute("SELECT 1").fetchone()
    assert active_writers_snapshot() == []
    conn.close()


def test_lock_failure_log_identifies_holder(tmp_path, caplog):
    """持锁 35s 场景的缩小版：持锁方开着写事务，等待方超时失败——
    失败日志必须指认持锁方位置（这是上轮「只定位等待方」缺的那半）。"""
    db = str(tmp_path / "t.db")
    holder = connect(db)
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                   " VALUES('secret-rule-id-不应出现在等待日志的参数里','v1','test')")
    # 等待方把 busy_timeout 压到 100ms，避免测试真的等 30 秒
    waiter = sqlite3.connect(db, timeout=0.1, factory=TrackedConnection)
    waiter.row_factory = sqlite3.Row
    with caplog.at_level(logging.WARNING, logger="lei_signal.storage.write_tx"):
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            waiter.execute("BEGIN IMMEDIATE")
    conn_sql = "SELECT 1"  # noqa: F841  占位：确认等待方之后仍可用
    holder.commit()
    waiter.execute("SELECT 1").fetchone()
    holder.close()
    waiter.close()

    rec = next(r for r in caplog.records
               if r.getMessage().startswith("db_write_tx lock_failed"))
    text = rec.getMessage()
    assert "test_lock_failure_log_identifies_holder" in text  # 持锁方位置
    assert "wait_ms=" in text and "active_writers_in_process" in text
    # 红线：SQL 参数（业务内容）不得进日志
    assert "secret-rule-id" not in text


def test_slow_wait_and_hold_logged(tmp_path, caplog):
    db = str(tmp_path / "t.db")
    connect(db).close()  # 建库+迁移（WAL 持久化在库文件头）
    set_thresholds_for_tests(wait_ms=50, hold_ms=50)
    # holder 在另一线程提交：check_same_thread=False（仅测试需要）
    holder = sqlite3.connect(db, timeout=1.0, factory=TrackedConnection,
                             check_same_thread=False)
    holder.row_factory = sqlite3.Row
    holder.execute("BEGIN IMMEDIATE")
    waiter = sqlite3.connect(db, timeout=1.0, factory=TrackedConnection)
    waiter.row_factory = sqlite3.Row

    def _release_later():
        time.sleep(0.15)
        holder.commit()

    t = threading.Thread(target=_release_later)
    t.start()
    with caplog.at_level(logging.INFO, logger="lei_signal.storage.write_tx"):
        waiter.execute("BEGIN IMMEDIATE")  # 等 ~150ms 拿到锁 → slow_wait
        time.sleep(0.1)
        waiter.commit()  # 持有 ~100ms → slow_hold
    t.join()
    holder.close()
    waiter.close()
    msgs = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("db_write_tx slow_wait") for m in msgs)
    assert any(m.startswith("db_write_tx slow_hold") for m in msgs)


def test_with_conn_block_uses_tracked_commit(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    with conn:
        conn.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                     " VALUES('r3','v1','test')")
    assert active_writers_snapshot() == []
    row = conn.execute(
        "SELECT rule_id FROM rule_registry WHERE rule_id='r3'").fetchone()
    assert row["rule_id"] == "r3"  # 行为与原生一致：with 块正常提交
    conn.close()


def test_behavior_matches_plain_connection(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    cur = conn.execute(
        "INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES(?,?,?)", ("r4", "v1", "test"))
    assert cur.rowcount == 1
    conn.commit()
    rows = conn.execute("SELECT * FROM rule_registry").fetchall()
    assert isinstance(rows[0], sqlite3.Row)
    conn.close()
    assert active_writers_snapshot() == []
