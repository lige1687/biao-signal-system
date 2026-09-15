"""主控复验反例复测（2026-09-16，执行方编写，不修改主控探针）。

复测方式：逐项执行与主控 probe.py **相同的操作序列**，输出同名字段，
便于与主控 results.json（修前）逐项对照。S1 场景（探针后半段）的复测
说明见 probe-rerun-note.md——未修改的探针副本在其自身同步点
（finished.wait(5)，位于被跳过运行的 fake_prepare 内）报错，这是
「无消费者后不再准备」的新行为所致；该场景的验收由
tests/unit/test_agent_ask_stability.py 矩阵 1 承担（同场景、同断言方向：
state=pending、retry=proceed）。
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from lei_signal.storage.write_tx import (
    STATE_TX_OPEN_NO_WRITE,
    STATE_WRITE_LOCK,
    TrackedConnection,
    active_writers_snapshot,
)

results: dict = {}
with tempfile.TemporaryDirectory() as temp:
    db = str(Path(temp) / "tx.db")
    setup = sqlite3.connect(db)
    setup.execute("CREATE TABLE t (x INTEGER)")
    setup.commit()
    setup.close()

    # —— 反例 1（S3）：cursor 写入必须可见 ——
    c = sqlite3.connect(db, factory=TrackedConnection)
    c.cursor().execute("INSERT INTO t VALUES(1)")
    snap = active_writers_snapshot()
    results["cursor_write"] = {
        "transaction_open": c.in_transaction,
        "tracked": snap,
        "ok": c.in_transaction and any(
            w["state"] == STATE_WRITE_LOCK for w in snap),
    }
    c.rollback()

    # —— 反例 2（S3）：仅 BEGIN 未写入不得算持锁者 ——
    c.execute("BEGIN")
    snap = active_writers_snapshot()
    results["deferred_begin_without_write"] = {
        "tracked": snap,
        "ok": all(w["state"] != STATE_WRITE_LOCK for w in snap)
        and any(w["state"] == STATE_TX_OPEN_NO_WRITE for w in snap),
    }
    c.rollback()

    # —— 反例 3（S3）：等锁失败的写语句不得登记为写者 ——
    holder = sqlite3.connect(db)
    holder.execute("BEGIN IMMEDIATE")
    c.execute("PRAGMA busy_timeout=20")
    try:
        c.execute("INSERT INTO t VALUES(2)")
    except sqlite3.OperationalError as exc:
        snap = active_writers_snapshot()
        results["failed_waiter_registered_as_writer"] = {
            "error": str(exc),
            "tracked": snap,
            "ok": not any("probe-counterexample-recheck" in w["site"]
                          and w["state"] == STATE_WRITE_LOCK
                          for w in snap if ".py:33" in w["site"]),
        }
    c.rollback()
    holder.rollback()
    holder.close()

    # —— S2 主对照：with 块提交失败（延迟外键）与原生逐项一致 ——
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("CREATE TABLE parent(id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE child(pid INTEGER REFERENCES parent(id)"
              " DEFERRABLE INITIALLY DEFERRED)")
    c.commit()
    try:
        with c:
            c.execute("INSERT INTO child VALUES(99)")
    except sqlite3.IntegrityError:
        results["commit_failure"] = {
            "transaction_still_open": c.in_transaction,
            "uncommitted_rows": c.execute(
                "SELECT COUNT(*) FROM child").fetchone()[0],
        }
    c.rollback()
    c.close()
    plain = sqlite3.connect(db)
    plain.execute("PRAGMA foreign_keys=ON")
    try:
        with plain:
            plain.execute("INSERT INTO child VALUES(99)")
    except sqlite3.IntegrityError:
        results["commit_failure_native"] = {
            "transaction_still_open": plain.in_transaction,
            "uncommitted_rows": plain.execute(
                "SELECT COUNT(*) FROM child").fetchone()[0],
        }
    plain.close()
    results["commit_failure_matches_native"] = (
        results["commit_failure"] == results["commit_failure_native"])

out = Path(__file__).with_name("probe-counterexample-recheck.json")
out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(out.read_text())
