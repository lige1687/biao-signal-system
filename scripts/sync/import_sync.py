#!/usr/bin/env python3
"""从同步包恢复「个人管理数据」到本机 SQLite + 情绪 CSV。

恢复策略：
  - 恢复前自动备份目标 db 到 <db>.bak-<时间戳>（可回滚）
  - 对每个表执行「整表替换」(DELETE + INSERT)：远端覆盖本机，适合镜像模型
  - 情绪 CSV 覆盖写入 $LEI_SENTIMENT_ROOT 目录
  - 需要后端已停止（否则 db 被占用会失败）；脚本会做预检

安全：绝不触碰 .env 等密钥；只写同步包内明确的表与 CSV。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 与 export_sync.py 保持一致
TABLES = [
    "watchlist_groups",
    "watchlist_items",
    "trade_plans",
    "trade_plan_revisions",
    "plan_action_items",
    "plan_annotations",
    "sentiment_observations",
]


def resolve_db() -> Path:
    p = os.environ.get("LEI_SQLITE_PATH")
    return Path(p) if p else (Path.home() / ".lei_signal_lab" / "lab.db")


def resolve_sentiment_dir(project: Path) -> Path:
    env = os.environ.get("LEI_SENTIMENT_ROOT")
    return Path(env) if env else (project / "data" / "sentiment")


def is_backend_running(port: int = 8000) -> bool:
    import socket

    s = socket.socket()
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def import_table(conn: sqlite3.Connection, table: str, rows: list[dict]) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if not cur.fetchone():
        print(f"[skip] 目标库无表 {table}（schema 不一致？跳过）")
        return False
    # 以目标表真实列为准，只写入同步包中存在的列
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    valid_cols = cols
    if rows:
        valid_cols = [c for c in rows[0].keys() if c in cols]
    conn.execute(f"DELETE FROM {table}")
    if rows:
        ph = ",".join("?" * len(valid_cols))
        col_sql = ",".join(valid_cols)
        sql = f"INSERT INTO {table} ({col_sql}) VALUES ({ph})"
        conn.executemany(sql, [[r.get(c) for c in valid_cols] for r in rows])
    conn.commit()
    print(f"[ok]   {table}: 写入 {len(rows)} 行")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="从同步包恢复个人管理数据")
    ap.add_argument("--db", type=Path, default=resolve_db(), help="目标 SQLite 路径")
    ap.add_argument("--in", dest="indir", type=Path, required=True, help="同步包目录")
    ap.add_argument(
        "--project", type=Path, default=Path(__file__).resolve().parent.parent.parent
    )
    ap.add_argument("--port", type=int, default=8000, help="后端端口（占用则拒绝导入）")
    ap.add_argument("--no-backend-check", action="store_true", help="跳过后端占用检查")
    args = ap.parse_args()

    bundle: Path = args.indir
    if not (bundle / "manifest.json").exists():
        print(f"[error] 同步包缺失 manifest.json: {bundle}", file=sys.stderr)
        sys.exit(1)

    if not args.no_backend_check and is_backend_running(args.port):
        print(
            "[error] 后端正在运行（占用 db）。请先停止后再拉取：biao stop",
            file=sys.stderr,
        )
        sys.exit(2)

    # 备份目标 db
    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        bak = args.db.with_suffix(f".db.bak-{int(time.time())}")
        shutil.copy2(args.db, bak)
        print(f"[backup] 已备份本机 db -> {bak}")
    else:
        print(f"[info] 目标 db 不存在，将新建: {args.db}")

    conn = sqlite3.connect(str(args.db), timeout=15)
    conn.execute("PRAGMA foreign_keys=OFF")  # 整表替换期间跳过 FK 校验
    for t in TABLES:
        p = bundle / f"{t}.json"
        if not p.exists():
            print(f"[skip] {t}: 同步包无此文件")
            continue
        rows = json.loads(p.read_text())
        import_table(conn, t, rows)
    conn.close()

    # 情绪 CSV
    sdir = resolve_sentiment_dir(args.project)
    sdir.mkdir(parents=True, exist_ok=True)
    src = bundle / "sentiment_csv"
    n = 0
    if src.exists():
        for f in src.glob("*.csv"):
            shutil.copy2(f, sdir / f.name)
            n += 1
            print(f"[ok]   情绪CSV: {f.name}")
    print(f"[done] 情绪CSV 恢复 {n} 个 -> {sdir}")
    print(
        f"[done] 导入完成 @ {datetime.now(timezone.utc).isoformat()}。"
        f"可启动后端查看：biao start"
    )


if __name__ == "__main__":
    main()
