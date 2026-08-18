#!/usr/bin/env python3
"""导出 LEI 看盘系统的「个人管理数据」到同步包（JSON + 情绪 CSV）。

导出范围（"全量"口径，均为用户主动维护的数据，不含缓存/派生/密钥）：
  - 自选与分组:  watchlist_groups, watchlist_items
  - 交易计划:    trade_plans, trade_plan_revisions, plan_action_items, plan_annotations
  - 情绪(库内镜像): sentiment_observations
  - 情绪 CSV 文件: $LEI_SENTIMENT_ROOT/*.csv 或 <项目>/data/sentiment/*.csv

刻意【不】导出：.env 密钥、cache 目录、market_breadth_snapshot_revisions /
market_context_assessments 等派生计算快照、feishu_webhook_nonces 一次性令牌。

实现：通用表 dump（用 PRAGMA table_info 读列名），与具体 schema 解耦，
后续加列不影响导出。每个表存为独立 <table>.json，便于 git diff 审阅。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# 仅导出这些「个人管理」表；其余（缓存/派生/密钥）一律跳过。
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


def resolve_project() -> Path:
    # scripts/sync/export_sync.py -> 项目根 = 上两级
    return Path(__file__).resolve().parent.parent.parent


def resolve_sentiment_dir(project: Path) -> Path:
    env = os.environ.get("LEI_SENTIMENT_ROOT")
    if env:
        return Path(env)
    return project / "data" / "sentiment"


def dump_table(conn: sqlite3.Connection, table: str):
    """返回 (rows, error)。rows 为 [{列:值}, ...]。"""
    try:
        cur = conn.execute(f"SELECT * FROM {table}")
    except sqlite3.Error as e:
        return None, f"表不存在或读取失败: {e}"
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows, None


def main() -> None:
    ap = argparse.ArgumentParser(description="导出 LEI 个人管理数据到同步包")
    ap.add_argument("--db", type=Path, default=resolve_db(), help="源 SQLite 路径")
    ap.add_argument("--out", type=Path, required=True, help="同步包输出目录")
    ap.add_argument(
        "--project", type=Path, default=resolve_project(), help="项目根（用于定位情绪 CSV）"
    )
    args = ap.parse_args()

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    csv_dir = out / "sentiment_csv"
    csv_dir.mkdir(exist_ok=True)

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "db_path": str(args.db),
        "tables": {},
    }

    if not args.db.exists():
        print(f"[warn] 数据库不存在: {args.db}", file=sys.stderr)
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2)
        )
        return

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    for t in TABLES:
        rows, err = dump_table(conn, t)
        if err:
            print(f"[skip] {t}: {err}")
            manifest["tables"][t] = {"rows": 0, "error": err}
            continue
        (out / f"{t}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2)
        )
        manifest["tables"][t] = {"rows": len(rows)}
        print(f"[ok]   {t}: {len(rows)} 行")
    conn.close()

    # 情绪 CSV（UI 实际读取的来源）
    sdir = resolve_sentiment_dir(args.project)
    copied = 0
    if sdir.exists():
        for f in sorted(sdir.glob("*.csv")):
            shutil.copy2(f, csv_dir / f.name)
            copied += 1
            print(f"[ok]   情绪CSV: {f.name}")
    else:
        print(f"[warn] 情绪目录不存在: {sdir}")
    manifest["sentiment_csv"] = {"source": str(sdir), "files": copied}

    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    print(f"[done] 同步包已写入 {out}（情绪CSV {copied} 个）")


if __name__ == "__main__":
    main()
