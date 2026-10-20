"""LEI 监督员 · 提醒订阅 14:45 盘中命中检查 (决策 2, 2026-08-08).

跟 intraday_check.py 共用 launchd 14:45 调度, 但本脚本只关心 watch_subscriptions:
  - kind=price: 14:45 盘中价 ± 0.5% 命中订阅 level 时,
    active -> pending_confirmation, 写 triggered_*
  - kind=state: v1 不实现 (留 TODO)

只读 (取行情 + 写库 = 写 triggered_* + last_checked_at), 不弹通知,
不在 [据此建计划] 按钮按之前落计划 -- Step 3 才接.

核心逻辑复用 api/watch_subscriptions.run_intraday_check, 本脚本只负责
CLI 入口 (argparse + logging) + 系统退出码.

用法:
    python3 scripts/watch_check.py [--dry-run] [--db lab.db]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api import watch_subscriptions as ws  # noqa: E402
from lei_signal.api.config import sqlite_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LEI 监督员 · 14:45 提醒订阅命中检查",
    )
    parser.add_argument("--dry-run", action="store_true", help="不写库, 只打印")
    parser.add_argument("--db", help="SQLite 路径 (默认取 config.sqlite_path)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    report = ws.run_intraday_check(db, dry_run=args.dry_run)
    print(
        f"完成: active={report.total_active} "
        f"触发={len(report.triggered)} 跳过={len(report.skipped)} "
        f"checked_at={report.checked_at}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
