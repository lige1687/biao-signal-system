#!/usr/bin/env python3
"""SQLite 在线备份 -> 隔离目录恢复 -> 只读业务查询校验 的 fixture 演练脚本。

对应 docs/experiments/sqlite-backup-restore-drill-2026-09-19.md（J2 单）。

流程（全部在临时目录，不触碰 ~/.lei_signal_lab/ 生产路径）：
  1. 用 lei_signal.storage.sqlite_store.connect（真实迁移建库，WAL 模式）
     在 tmp 下建 fixture 源库，灌入 tests/fixtures/backup_drill/seed_events.json；
  2. 用 sqlite3 标准库官方在线备份接口 Connection.backup 做备份；
     备份进行中从另一条连接并发写入一条事件，验证在线备份语义
     （源库被改动时备份会重启，最终得到一个包含该写入的一致快照）；
  3. 备份完成后再补一条「迟到事件」，验证它不进备份——这就是数据缺失窗口；
  4. 把备份文件复制到与源隔离的 restore/ 目录，以只读方式打开，
     用 sqlite_store.count_events + 逐行读回关键事件字段与源库比对，
     并执行 PRAGMA integrity_check 记录结果。

幂等：所有产物在 tempfile 临时目录，结束即清理（--keep 可保留供人工查看）。
可重复执行，不残留脏状态。

用法：
  python3 scripts/archive/sqlite_backup_restore_drill.py [--keep]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lei_signal.domain.types import Direction, Provenance, Severity, SignalEvent  # noqa: E402
from lei_signal.storage import sqlite_store  # noqa: E402

FIXTURE_JSON = REPO_ROOT / "tests" / "fixtures" / "backup_drill" / "seed_events.json"


def _event_from_dict(payload: dict) -> SignalEvent:
    return SignalEvent(
        event_id=payload["event_id"],
        symbol=payload["symbol"],
        timeframe=payload["timeframe"],
        event_date=date.fromisoformat(payload["event_date"]),
        available_date=date.fromisoformat(payload["available_date"]),
        rule_id=payload["rule_id"],
        rule_version=payload["rule_version"],
        direction=Direction(payload["direction"]),
        severity=Severity(payload["severity"]),
        strength=payload["strength"],
        reason_cn=payload["reason_cn"],
        provenance=Provenance(payload["provenance"]),
        evidence=payload.get("evidence", {}),
    )


def _row_signatures(conn: sqlite3.Connection) -> dict[str, tuple]:
    """读回关键业务字段（event_id -> 身份字段元组），用于源/恢复库比对。"""
    rows = conn.execute(
        """
        SELECT event_id, symbol, event_date, available_date, rule_id,
               rule_version, direction, severity, strength
        FROM signal_events ORDER BY event_id
        """
    ).fetchall()
    return {r["event_id"]: tuple(r) for r in rows}


def run_drill(keep_dir: Path | None = None) -> dict:
    fixture = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    seed_events = [_event_from_dict(p) for p in fixture["events"]]
    late_event = _event_from_dict(fixture["late_event"])

    tmp_root = keep_dir or Path(tempfile.mkdtemp(prefix="lei_backup_drill_"))
    tmp_root.mkdir(parents=True, exist_ok=True)
    source_dir = tmp_root / "source"
    backup_dir = tmp_root / "backup"
    restore_dir = tmp_root / "restore"
    for d in (source_dir, backup_dir, restore_dir):
        # 重跑前清空子目录，避免上次残留的 -wal/-shm 造成脏状态
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    source_db = source_dir / "lab.db"
    backup_db = backup_dir / "lab.backup.db"
    restored_db = restore_dir / "lab.db"

    report: dict = {"tmp_root": str(tmp_root)}

    # -- 1. 建源库（真实迁移）并灌入代表性数据行 ------------------------
    src = sqlite_store.connect(source_db)
    write_report = sqlite_store.write_events(src, seed_events, run_id="drill-run-1")
    assert write_report.inserted == len(seed_events)
    report["seed_rows"] = len(seed_events)
    report["source_rows_after_seed"] = sqlite_store.count_events(src)

    # -- 2. 在线备份：备份期间从另一条连接并发写入 ----------------------
    writer = sqlite3.connect(str(source_db), timeout=30.0)
    writer.execute("PRAGMA journal_mode = WAL")
    concurrent_write_happened = False

    def _on_progress(status, remaining, total):
        nonlocal concurrent_write_happened
        if not concurrent_write_happened and remaining > 0:
            # 备份尚未完成时并发写一条：sqlite 在线备份会重启步骤，
            # 最终快照应包含这条写入（在线语义验证）。
            sqlite_store.write_events(writer, [late_event], run_id="drill-run-1")
            concurrent_write_happened = True

    dst = sqlite3.connect(str(backup_db))
    t0 = time.perf_counter()
    src.backup(dst, pages=1, progress=_on_progress)  # pages=1 强制分步，给回调留窗口
    dst.close()
    report["backup_seconds"] = round(time.perf_counter() - t0, 6)
    report["concurrent_write_during_backup"] = concurrent_write_happened

    source_rows_at_backup = sqlite_store.count_events(src)
    report["source_rows_at_backup"] = source_rows_at_backup
    source_sig = _row_signatures(src)
    writer.close()

    # -- 3. 恢复到隔离目录 + 只读业务查询校验 --------------------------
    t0 = time.perf_counter()
    shutil.copyfile(backup_db, restored_db)
    ro = sqlite3.connect(f"file:{restored_db}?mode=ro", uri=True, timeout=30.0)
    ro.row_factory = sqlite3.Row
    restored_rows = sqlite_store.count_events(ro)
    restored_sig = _row_signatures(ro)
    integrity = ro.execute("PRAGMA integrity_check").fetchone()[0]
    report["restore_seconds"] = round(time.perf_counter() - t0, 6)
    report["restored_rows"] = restored_rows
    report["integrity_check"] = integrity

    assert integrity == "ok", f"integrity_check={integrity}"
    assert restored_rows == source_rows_at_backup, (
        f"restored={restored_rows} source={source_rows_at_backup}"
    )
    assert restored_sig == source_sig, "恢复库与源库关键行不一致"
    assert late_event.event_id in restored_sig, "备份期间的并发写入未进入备份快照"
    report["rows_match"] = True

    # -- 4. 迟到事件：备份完成后的写入不进本份备份（缺失窗口演示） ------
    after = sqlite_store.connect(source_db)
    sqlite_store.write_events(after, [
        _event_from_dict({**fixture["late_event"],
                          "event_id": "drill:ev:after-backup"})
    ], run_id="drill-run-1")
    report["late_write_in_backup"] = (
        "drill:ev:after-backup" in _row_signatures(ro)
    )
    assert report["late_write_in_backup"] is False, "备份后写入不应出现在既有备份里"
    after.close()

    ro.close()
    src.close()

    if keep_dir is None:
        shutil.rmtree(tmp_root, ignore_errors=True)
        report["tmp_root"] = f"{tmp_root}（已清理）"
    report["ok"] = True
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep", type=Path, default=None,
        help="保留演练目录到指定路径（默认用完即删的临时目录）",
    )
    args = parser.parse_args()
    report = run_drill(keep_dir=args.keep)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
