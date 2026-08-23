"""LEI 今日自选信号统一扫描 (launchd 交易日 11:35 / 14:45 / 15:05).

买点行 -> daily_opportunity_scan (既有表, /grid 面板同步受益);
卖点行 + 数据不可用 -> signal_alerts (看盘主页「今日自选信号」横幅读).
as_of 按触发时刻自动定: 15:00 及以后 = close (当日最终口径), 之前 = intraday (盘中临时).

**只写扫描结果, 不推通知** (用户决策: 只面板+红点).
判定权在 Python 规则层; 本脚本只编排 analyze + 落库 (与 daily_scan.py 同模式).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.signal_scan import (  # noqa: E402
    AS_OF_CLOSE,
    AS_OF_INTRADAY,
    run_signal_scan,
)
from lei_signal.api.watchlist import list_watchlist  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def _default_as_of() -> str:
    return AS_OF_CLOSE if datetime.now().hour >= 15 else AS_OF_INTRADAY


def main() -> int:
    parser = argparse.ArgumentParser(description="LEI 今日自选信号统一扫描")
    parser.add_argument("--symbols", help="逗号分隔标的列表 (默认全部自选)")
    parser.add_argument(
        "--as-of", choices=[AS_OF_INTRADAY, AS_OF_CLOSE], default=None,
        help="口径 (默认按当前时间: >=15 点为 close)",
    )
    parser.add_argument("--dry-run", action="store_true", help="不写库, 只打印")
    parser.add_argument("--db", help="SQLite 路径 (默认 config.sqlite_path)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        with connect(db) as conn:
            symbols = [i.symbol for i in list_watchlist(conn)]
    if not symbols:
        print("完成: 自选为空, 无可扫描标的")
        return 0

    from lei_signal.api.services import AnalysisService  # noqa: PLC0415

    service = AnalysisService(max_workers=8)
    # 串行预热 V8 (与 daily_scan.py 同因: mini_racer 并发初始化会崩, 先跑一个标的)
    service.get(symbols[0], refresh=True)

    summary = run_signal_scan(
        service, db, symbols=symbols,
        as_of=args.as_of or _default_as_of(),
        refresh=True, dry_run=args.dry_run,
    )
    print(f"完成: {summary}")
    # mini_racer (V8) 进程退出清理崩溃, 工作已完成, 直接 _exit 跳过 teardown
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
