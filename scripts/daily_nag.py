"""LEI 监督员每日催办入口（launchd 触发）。

每个交易日数据更新后由 launchd 触发一次：取数（实时优先，失败回退 fixture 并标
DATA_STALE）-> 对每条 armed/entered 计划跑一轮监督 -> 投递 macOS 通知 + 落地待办清单。

催办节拍绑 ``last_bar_date`` 前进（见 plans/actions.nag_open_items）：数据不动不催，
长假不误催，DATA_STALE 不递增 nag_count。微信推送归 v2（届时只加一个投递器）。

用法：
    python3 scripts/daily_nag.py [--symbols 000001.SS,000300.SS] [--dry-run] [--db lab.db]
不指定 --symbols 时取 watchlist 全部。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

# 让 `python3 scripts/daily_nag.py` 也能 import lei_signal
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.compose.pipeline import analyze, analyze_bars  # noqa: E402
from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR  # noqa: E402
from lei_signal.data.validation import DataUnavailableError  # noqa: E402
from lei_signal.plans.actions import run_plan_cycle  # noqa: E402
from lei_signal.plans.context import context_from_result  # noqa: E402
from lei_signal.plans.store import list_plans  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

DEFAULT_FIXTURE_DIR = _PROJECT_ROOT / "tests"


def fetch_context(symbol: str, *, fixture_dir: Path | None = None):
    """实时优先，失败回退 fixture 并标 DATA_STALE（交接 §6.1 方案 b）。"""
    fixture_dir = fixture_dir or DEFAULT_FIXTURE_DIR
    try:
        result = analyze(symbol)
        return context_from_result(result, cache_fallback_used=False)
    except (DataUnavailableError, Exception):
        # 回退 fixture：监督链不能因网络抖动断；代价是强制 DATA_STALE
        fixture_path = fixture_dir / f"{symbol}.bars.parquet"
        if not fixture_path.exists():
            raise
        bars = pd.read_parquet(fixture_path)
        result = analyze_bars(symbol, bars)
        return context_from_result(result, cache_fallback_used=True)


def notify(title: str, body: str, *, dry_run: bool = False) -> None:
    """best-effort macOS 通知。优先 terminal-notifier，回退 osascript。"""
    if dry_run:
        print(f"[dry-run] 通知 | {title}: {body}")
        return
    for cmd in (
        ["terminal-notifier", "-title", title, "-message", body],
        ["osascript", "-e", f'display notification "{body}" with title "{title}"'],
    ):
        try:
            subprocess.run(cmd, check=False, timeout=5)  # noqa: S603
            return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue


def run_supervisor(
    symbols: list[str],
    *,
    db_path: str | None = None,
    dry_run: bool = False,
    fixture_dir: Path | None = None,
) -> int:
    """跑一轮监督。返回催办待办总数。"""
    path = db_path or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    conn = connect(path)
    total_nagged = 0
    try:
        for symbol in symbols:
            try:
                ctx = fetch_context(symbol, fixture_dir=fixture_dir)
            except Exception as exc:  # noqa: BLE001
                print(f"[{symbol}] 取数失败：{exc}", file=sys.stderr)
                continue
            for plan in list_plans(conn, symbol=symbol):
                if plan.state not in ("armed", "entered"):
                    continue
                result = run_plan_cycle(conn, plan, ctx, calendar=DEFAULT_TRADING_CALENDAR)
                for item in result.nagged:
                    total_nagged += 1
                    alert = next(
                        (a for a in result.alerts if a.action_kind == item.kind),
                        None,
                    )
                    body = f"{plan.symbol} {item.kind} 待办（第 {item.nag_count} 次）"
                    if alert:
                        body += f"：{alert.next_step_cn}"
                    notify("LEI 监督员", body, dry_run=dry_run)
                if result.revived:
                    notify("LEI 监督员",
                           f"{plan.symbol} 推迟项复活 {len(result.revived)} 条",
                           dry_run=dry_run)
    finally:
        conn.close()
    return total_nagged


def _watchlist_symbols(conn) -> list[str]:  # noqa: ANN001
    from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415
    return [item.symbol for item in list_watchlist(conn)]


def main() -> int:
    parser = argparse.ArgumentParser(description="LEI 监督员每日催办")
    parser.add_argument("--symbols", help="逗号分隔标的；不指定则取 watchlist 全部")
    parser.add_argument("--dry-run", action="store_true", help="不弹通知，只打印")
    parser.add_argument("--db", help="SQLite 路径，默认 LEI_SQLITE_PATH/lab.db")
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        conn = connect(args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path()))
        try:
            symbols = _watchlist_symbols(conn)
        finally:
            conn.close()

    if not symbols:
        print("无标的（watchlist 为空且未指定 --symbols）")
        return 0
    nagged = run_supervisor(symbols, db_path=args.db, dry_run=args.dry_run)
    print(f"完成：催办待办 {nagged} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
