"""LEI 监督员 · 每日机会雷达扫描 (15:00 收盘后触发).

扫自选里所有标的, 用既有确定性判定 (可交易性门禁 + 条件化场景 + 盈亏比) 汇总成
verdict (actionable / waiting / blocked / none), 整体重写当日 daily_opportunity_scan
表。dashboard 面板 + 顶栏红点读这张表。

**只写扫描结果, 不推通知** (用户决策: 只 dashboard 面板+红点, 不做飞书推送)。
判定权在 Python 规则层; 本脚本不做任何买点判断, 只编排 analyze + 落库。

核心逻辑复用 routes/opportunities.run_opportunity_scan (纯函数, 与 HTTP 路由共用),
本脚本只负责 CLI 入口 (argparse + logging) + AnalysisService 构造 + 系统退出码。

用法:
    python3 scripts/daily_scan.py [--symbols 600519.SS,...] [--dry-run] [--db lab.db]
不指定 --symbols 时取全部自选。
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

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.opportunity_scan import (  # noqa: E402
    count_opportunities,
    today_date,
    upsert_scan_results,
)
from lei_signal.api.routes.opportunities import (  # noqa: E402
    VERDICT_ACTIONABLE,
    VERDICT_BLOCKED,
    VERDICT_NONE,
    VERDICT_WAITING,
    run_opportunity_scan,
)
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.api.watchlist import list_watchlist  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def _count_by_verdict(items: list, verdict: str) -> int:
    return sum(1 for it in items if it.verdict == verdict)


def _resolve_symbols(db: str, cli_symbols: str | None) -> list[str]:
    """解析待扫标的: --symbols 优先, 否则取全部自选。"""
    if cli_symbols:
        return [s.strip() for s in cli_symbols.split(",") if s.strip()]
    from contextlib import closing  # noqa: PLC0415

    with closing(connect(db)) as conn:
        return [item.symbol for item in list_watchlist(conn)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LEI 监督员 · 每日机会雷达扫描 (收盘后)",
    )
    parser.add_argument(
        "--symbols",
        help="逗号分隔标的列表 (默认取全部自选)",
    )
    parser.add_argument("--dry-run", action="store_true", help="不写库, 只打印")
    parser.add_argument("--db", help="SQLite 路径 (默认取 config.sqlite_path)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    symbols = _resolve_symbols(db, args.symbols)
    if not symbols:
        print("完成: 自选为空, 无可扫描标的")
        return 0

    service = AnalysisService(max_workers=8)
    # 串行预热 V8: mini_racer 在多线程并发初始化会触发
    # address_pool_manager 崩溃, 主线程先跑一个标的把 V8 初始化好。
    # (API server 无此问题: 首个请求串行进入自然完成初始化。)
    service.get(symbols[0], refresh=True)

    response = run_opportunity_scan(
        service, db, symbols=symbols, refresh=True, only_with_candidates=True,
    )
    items = response.items

    scan_date = today_date()
    if args.dry_run:
        logging.info("[dry-run] 不写库, 仅打印扫描结果")
    else:
        with connect(db) as conn:
            upsert_scan_results(conn, scan_date, items)
            conn.commit()
            opps = count_opportunities(conn, scan_date)

    actionable = _count_by_verdict(items, VERDICT_ACTIONABLE)
    waiting = _count_by_verdict(items, VERDICT_WAITING)
    blocked = _count_by_verdict(items, VERDICT_BLOCKED)
    none = _count_by_verdict(items, VERDICT_NONE)
    print(
        f"完成: scanned={response.scanned} "
        f"actionable={actionable} waiting={waiting} "
        f"blocked={blocked} none={none} scan_date={scan_date}"
    )
    if not args.dry_run:
        print(f"今日机会 (actionable+waiting): {opps}")
    # mini_racer (V8) 在进程退出清理时会崩溃 (address_pool_manager),
    # 工作已完成、DB 已 commit, 直接 _exit 跳过 V8 teardown。
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
