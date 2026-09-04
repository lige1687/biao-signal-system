"""持仓快照种子写入（幂等）。

把 2026-09-04 养基宝截图识别出的 29 只基金写入 portfolio_* 三张表。
UPSERT 语义：重跑只更新数值，不清空手工补的 code（COALESCE 保留）。

用法:
    python3 scripts/seed_portfolio.py [--db lab.db]
"""
from __future__ import annotations

import argparse
import os
import sys
from contextlib import closing
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.portfolio.seed import seed  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="写入持仓快照种子数据（幂等）")
    parser.add_argument("--db", help="SQLite 路径 (默认取 config.sqlite_path)")
    args = parser.parse_args()

    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    with closing(connect(db)) as conn:
        counts = seed(conn)
    print(f"已写入 {counts['groups']} 个分组、{counts['holdings']} 只持仓 -> {db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
