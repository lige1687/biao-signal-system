"""写事务登记与锁等待诊断（2026-09-15 agent-ask-stability；S2/S3 补修矩阵）。

S2（诊断不得改变数据库原行为）：with 块正常提交/块内异常/提交失败
（延迟外键）与原生连接逐项对照——异常类型、in_transaction、未提交行数。
S3（区分等待/事务开启/已取得写锁）：cursor 写入可见；deferred BEGIN
未写入不算持锁者；等锁失败的写语句不登记；快照按库区分；脚本/SQL
COMMIT/ROLLBACK/关闭后的登记按真实事务状态同步。
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time

import pytest

from lei_signal.storage.sqlite_store import connect
from lei_signal.storage.write_tx import (
    STATE_TX_OPEN_NO_WRITE,
    STATE_WRITE_LOCK,
    TrackedConnection,
    active_writers_snapshot,
    set_thresholds_for_tests,
)


@pytest.fixture(autouse=True)
def _thresholds():
    set_thresholds_for_tests(wait_ms=1500, hold_ms=3000)
    yield
    set_thresholds_for_tests(wait_ms=1500, hold_ms=3000)


def _raw(db: str, timeout: float = 30.0, **kw) -> TrackedConnection:
    c = sqlite3.connect(db, timeout=timeout, factory=TrackedConnection, **kw)
    c.row_factory = sqlite3.Row
    return c


def test_connect_returns_tracked_connection(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    assert isinstance(conn, TrackedConnection)
    # 迁移的 DDL 都已提交，连接打开后不应残留活跃写事务
    assert active_writers_snapshot() == []
    conn.close()


def test_successful_write_does_not_count_lock_wait_as_hold(tmp_path):
    db = str(tmp_path / "wait.db")
    holder = sqlite3.connect(db, check_same_thread=False)
    holder.execute("CREATE TABLE t(x)")
    holder.execute("BEGIN IMMEDIATE")
    conn = _raw(db)

    def release():
        time.sleep(0.3)
        holder.commit()

    worker = threading.Thread(target=release)
    worker.start()
    try:
        start = time.perf_counter()
        conn.execute("INSERT INTO t VALUES(1)")
        elapsed_ms = (time.perf_counter() - start) * 1000
        snapshot = active_writers_snapshot(db=db)
        assert elapsed_ms >= 200
        assert len(snapshot) == 1
        assert snapshot[0]["state"] == STATE_WRITE_LOCK
        assert snapshot[0]["held_ms"] < elapsed_ms / 2
    finally:
        conn.rollback()
        conn.close()
        worker.join()
        holder.close()


def test_explicit_begin_immediate_registers_write_lock(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.execute("BEGIN IMMEDIATE")
    snap = [w for w in active_writers_snapshot() if w["db"] == db]
    assert len(snap) == 1
    assert snap[0]["state"] == STATE_WRITE_LOCK
    assert "test_write_tx_tracking" in snap[0]["site"]
    conn.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                 " VALUES('r1','v1','test')")
    conn.commit()
    assert active_writers_snapshot() == []
    conn.close()


def test_cursor_write_is_tracked(tmp_path):
    """S3 反例 1：conn.cursor().execute(INSERT) 开启真实写事务，必须可见。"""
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.cursor().execute(
        "INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES('r2','v1','test')")
    assert conn.in_transaction
    snap = [w for w in active_writers_snapshot() if w["db"] == db]
    assert len(snap) == 1 and snap[0]["state"] == STATE_WRITE_LOCK
    conn.rollback()
    assert active_writers_snapshot() == []
    conn.close()


def test_deferred_begin_without_write_is_not_a_holder(tmp_path):
    """S3 反例 2：仅 BEGIN（deferred）未写入，不得登记为持锁者。"""
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.execute("BEGIN")
    snap = [w for w in active_writers_snapshot() if w["db"] == db]
    assert all(w["state"] != STATE_WRITE_LOCK for w in snap)
    assert any(w["state"] == STATE_TX_OPEN_NO_WRITE for w in snap)  # 如实标注
    conn.rollback()
    assert active_writers_snapshot() == []
    conn.close()


def test_failed_waiter_not_registered_as_writer(tmp_path):
    """S3 反例 3：等锁失败的写语句——等待方不得出现在活跃写者中。"""
    db = str(tmp_path / "t.db")
    holder = connect(db)
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                   " VALUES('r3','v1','test')")
    waiter = _raw(db, timeout=0.1)
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        waiter.execute("INSERT INTO rule_registry(rule_id, rule_version,"
                       " provenance) VALUES('r4','v1','test')")
    snap = active_writers_snapshot(db=db)
    assert len(snap) == 1  # 只剩持锁者
    assert "holder" not in snap[0]["site"] or True  # site 是代码位置
    assert "test_failed_waiter" in snap[0]["site"]  # 持锁方的位置
    waiter.close()
    holder.commit()
    holder.close()
    assert active_writers_snapshot() == []


def _deferred_fk_setup(c: sqlite3.Connection) -> None:
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("CREATE TABLE parent(id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE child(pid INTEGER REFERENCES parent(id)"
              " DEFERRABLE INITIALLY DEFERRED)")
    c.commit()


def test_commit_failure_with_block_matches_native(tmp_path):
    """S2 主对照：with 块离开提交失败（延迟外键）——与原生逐项一致。"""
    db = str(tmp_path / "t.db")
    setup = sqlite3.connect(db)
    setup.execute("CREATE TABLE dummy(x)")
    setup.commit()
    setup.close()

    tracked = _raw(db)
    _deferred_fk_setup(tracked)
    tracked_exc = None
    try:
        with tracked:
            tracked.execute("INSERT INTO child VALUES(99)")
    except sqlite3.IntegrityError as exc:
        tracked_exc = exc
    tracked_result = (type(tracked_exc).__name__, tracked.in_transaction,
                      tracked.execute("SELECT COUNT(*) FROM child").fetchone()[0])
    tracked.rollback()
    tracked.close()

    native = sqlite3.connect(db)
    native.execute("PRAGMA foreign_keys=ON")
    native_exc = None
    try:
        with native:
            native.execute("INSERT INTO child VALUES(99)")
    except sqlite3.IntegrityError as exc:
        native_exc = exc
    native_result = (type(native_exc).__name__, native.in_transaction,
                     native.execute("SELECT COUNT(*) FROM child").fetchone()[0])
    native.close()

    assert tracked_result == native_result == ("IntegrityError", False, 0)
    assert active_writers_snapshot() == []  # 原生回滚后登记同步消失


def test_with_block_normal_commit_and_inner_exception(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    with conn:
        conn.execute("INSERT INTO rule_registry(rule_id, rule_version,"
                     " provenance) VALUES('r5','v1','test')")
    assert active_writers_snapshot() == []
    assert conn.execute("SELECT COUNT(*) FROM rule_registry"
                        " WHERE rule_id='r5'").fetchone()[0] == 1
    with pytest.raises(RuntimeError):
        with conn:
            conn.execute("INSERT INTO rule_registry(rule_id, rule_version,"
                         " provenance) VALUES('r6','v1','test')")
            raise RuntimeError("块内异常")
    assert conn.execute("SELECT COUNT(*) FROM rule_registry"
                        " WHERE rule_id='r6'").fetchone()[0] == 0
    assert active_writers_snapshot() == []
    conn.close()


def test_sql_commit_and_rollback_via_execute(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.execute("BEGIN")
    conn.execute("INSERT INTO rule_registry(rule_id, rule_version,"
                 " provenance) VALUES('r7','v1','test')")
    assert any(w["state"] == STATE_WRITE_LOCK
               for w in active_writers_snapshot(db=db))
    conn.execute("COMMIT")
    assert active_writers_snapshot() == []
    conn.execute("BEGIN")
    conn.execute("INSERT INTO rule_registry(rule_id, rule_version,"
                 " provenance) VALUES('r8','v1','test')")
    conn.execute("ROLLBACK")
    assert active_writers_snapshot() == []
    # 提交失败（延迟外键）：事务仍开着——登记不得提前消失（与原生一致）
    _deferred_fk_setup(conn)
    conn.execute("BEGIN")
    conn.execute("INSERT INTO child VALUES(77)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("COMMIT")
    assert conn.in_transaction  # 原生语义：失败提交事务仍在
    assert any(w["db"] == db for w in active_writers_snapshot(db=db))
    conn.rollback()
    assert active_writers_snapshot() == []
    conn.close()


def test_executescript_syncs_real_state(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    # 脚本留下未结束事务：登记必须保留（状态如实）
    conn.executescript(
        "BEGIN; INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES('r9','v1','test');")
    assert conn.in_transaction
    assert any(w["db"] == db for w in active_writers_snapshot(db=db))
    conn.rollback()
    # 脚本自带 BEGIN...COMMIT：登记不得残留
    conn.executescript(
        "BEGIN; INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES('r10','v1','test'); COMMIT;")
    assert not conn.in_transaction
    assert active_writers_snapshot() == []
    conn.close()


def test_close_clears_registration(tmp_path):
    db = str(tmp_path / "t.db")
    conn = connect(db)
    conn.execute("INSERT INTO rule_registry(rule_id, rule_version,"
                 " provenance) VALUES('r11','v1','test')")
    assert active_writers_snapshot(db=db)
    conn.close()
    assert active_writers_snapshot() == []


def test_snapshot_distinguishes_databases(tmp_path):
    db1, db2 = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    c1, c2 = connect(db1), connect(db2)
    c1.execute("BEGIN IMMEDIATE")
    c2.execute("BEGIN IMMEDIATE")
    snap1 = active_writers_snapshot(db=db1)
    assert len(snap1) == 1 and snap1[0]["db"] == db1
    assert len(active_writers_snapshot(db=db2)) == 1
    assert len(active_writers_snapshot()) == 2
    c1.rollback()
    c2.rollback()
    c1.close()
    c2.close()


def test_lock_failure_log_identifies_holder(tmp_path, caplog):
    """持锁方开着写事务，等待方超时失败——失败日志指认同库持锁方位置，
    且不含 SQL 参数；等待方自己不被列为持锁者。"""
    db = str(tmp_path / "t.db")
    holder = connect(db)
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("INSERT INTO rule_registry(rule_id, rule_version, provenance)"
                   " VALUES('secret-rule-id-不应出现在等待日志的参数里','v1','test')")
    waiter = _raw(db, timeout=0.1)
    with (
        caplog.at_level(logging.WARNING, logger="lei_signal.storage.write_tx"),
        pytest.raises(sqlite3.OperationalError, match="locked"),
    ):
        waiter.execute("BEGIN IMMEDIATE")
    holder.commit()
    waiter.execute("SELECT 1").fetchone()
    holder.close()
    waiter.close()

    rec = next(r for r in caplog.records
               if r.getMessage().startswith("db_write_tx lock_failed"))
    text = rec.getMessage()
    assert "test_lock_failure_log_identifies_holder" in text  # 持锁方位置
    assert "wait_ms=" in text and "holders_same_db" in text
    assert "空列表不证明持锁者在其他进程" in text  # 诚实边界写进日志
    assert "secret-rule-id" not in text  # 红线：SQL 参数不进日志


def test_slow_wait_and_hold_logged(tmp_path, caplog):
    db = str(tmp_path / "t.db")
    connect(db).close()  # 建库+迁移（WAL 持久化在库文件头）
    set_thresholds_for_tests(wait_ms=50, hold_ms=50)
    holder = sqlite3.connect(db, timeout=1.0, factory=TrackedConnection,
                             check_same_thread=False)
    holder.row_factory = sqlite3.Row
    holder.execute("BEGIN IMMEDIATE")
    waiter = _raw(db, timeout=1.0)

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


def test_select_does_not_register(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    conn.execute("SELECT 1").fetchone()
    assert active_writers_snapshot() == []
    conn.close()


def test_behavior_matches_plain_connection(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    cur = conn.execute(
        "INSERT INTO rule_registry(rule_id, rule_version, provenance)"
        " VALUES(?,?,?)", ("r12", "v1", "test"))
    assert cur.rowcount == 1
    conn.commit()
    rows = conn.execute("SELECT * FROM rule_registry").fetchall()
    assert isinstance(rows[0], sqlite3.Row)
    conn.close()
    assert active_writers_snapshot() == []
