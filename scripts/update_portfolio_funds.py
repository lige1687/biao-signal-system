"""持仓基金数据每日更新：代码回填 + 净值刷新 + 季报穿透。

用法:
    python3 scripts/update_portfolio_funds.py [--db lab.db] [--only codes|nav|top10]

默认全跑。代码回填只补 code 为空的持仓（已有代码的不动）；净值刷新
先锚定（快照日净值/反推份额/推算成本）再每日更新市值与收益；季报
穿透每只基金只保留最新一期。全部幂等，可挂在 launchd 每日执行。
"""
from __future__ import annotations

import argparse
import os
import sys
from contextlib import closing
from dataclasses import replace
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.portfolio.funddata import match_fund_code  # noqa: E402
from lei_signal.portfolio.holdings_report import refresh_top10  # noqa: E402
from lei_signal.portfolio.nav_update import update_nav  # noqa: E402
from lei_signal.portfolio.store import list_holdings  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def backfill_codes(conn) -> dict:  # noqa: ANN001
    """名称 -> 代码自动匹配。匹配不上的打印出来人工处理，绝不猜。"""
    from lei_signal.portfolio.store import upsert_holding

    stats = {"filled": 0, "already": 0, "unmatched": []}
    for h in list_holdings(conn):
        if h.code:
            stats["already"] += 1
            continue
        match = match_fund_code(h.name)
        if match is None:
            stats["unmatched"].append(h.name)
            continue
        code, _official_name = match
        upsert_holding(conn, replace(h, code=code))
        conn.commit()
        stats["filled"] += 1
        print(f"  代码回填：{h.name} -> {code}")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="持仓基金数据更新（代码/净值/季报）")
    parser.add_argument("--db", help="SQLite 路径 (默认取 config.sqlite_path)")
    parser.add_argument("--only", choices=["codes", "nav", "top10"],
                        help="只跑其中一步（默认全跑）")
    args = parser.parse_args()

    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    with closing(connect(db)) as conn:
        steps = [args.only] if args.only else ["codes", "nav", "top10"]
        if "codes" in steps:
            print("[1/3] 基金代码回填 …")
            stats = backfill_codes(conn)
            print(f"  新填 {stats['filled']}，已有 {stats['already']}，"
                  f"未匹配 {len(stats['unmatched'])}")
            for name in stats["unmatched"]:
                print(f"  ✗ 未匹配：{name}")
        if "nav" in steps:
            print("[2/3] 净值刷新 …")
            stats = update_nav(conn)
            print(f"  锚定 {stats['anchored']}，刷新 {stats['refreshed']}，"
                  f"跳过(无代码) {stats['skipped']}，失败 {stats['failed']}")
        if "top10" in steps:
            print("[3/3] 季报穿透（前十大持仓）…")
            stats = refresh_top10(conn)
            print(f"  拉取 {stats['fetched']}，无股票持仓 {stats['empty']}，"
                  f"跳过(无代码) {stats['skipped']}，失败 {stats['failed']}")
    print(f"完成 -> {db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
