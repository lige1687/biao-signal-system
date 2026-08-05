"""LEI 监督员每日催办入口（launchd 触发）。

每个交易日数据更新后由 launchd 触发一次：取数（实时优先，失败回退 fixture 并标
DATA_STALE）-> 对每条 armed/entered 计划跑一轮监督 -> 投递通知。

催办节拍绑 ``last_bar_date`` 前进（见 plans/actions.nag_open_items）：数据不动不催，
长假不误催，DATA_STALE 不递增 nag_count。

用法：
    python3 scripts/daily_nag.py [--symbols 000001.SS,000300.SS] [--dry-run]
        [--db lab.db] [--notifier macos|feishu|both]
不指定 --symbols 时取 watchlist 全部。
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
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
from lei_signal.env import load_env  # noqa: E402
from lei_signal.notify.base import NotificationPayload, Notifier  # noqa: E402
from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier  # noqa: E402
from lei_signal.notify.macos import MacNotifier  # noqa: E402
from lei_signal.notify.render import merge_daily_summaries, render_cycle  # noqa: E402
from lei_signal.plans.actions import run_plan_cycle  # noqa: E402
from lei_signal.plans.context import context_from_result  # noqa: E402
from lei_signal.plans.store import list_plans  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

# 本地/launchd 运行前把 .env 注入 os.environ（不覆盖已设变量）。
load_env()

DEFAULT_FIXTURE_DIR = _PROJECT_ROOT / "tests"


def fetch_context(symbol: str, *, fixture_dir: Path | None = None):  # noqa: ANN201
    """实时优先，失败回退 fixture 并标 DATA_STALE（交接 §6.1 方案 b）。"""
    fixture_dir = fixture_dir or DEFAULT_FIXTURE_DIR
    try:
        result = analyze(symbol)
        return context_from_result(result, cache_fallback_used=False)
    except (DataUnavailableError, Exception):
        fixture_path = fixture_dir / f"{symbol}.bars.parquet"
        if not fixture_path.exists():
            raise
        bars = pd.read_parquet(fixture_path)
        result = analyze_bars(symbol, bars)
        return context_from_result(result, cache_fallback_used=True)


def _build_notifiers(kind: str, *, dry_run: bool) -> list[Notifier]:
    notifiers: list[Notifier] = []
    if kind in ("macos", "both"):
        notifiers.append(MacNotifier(dry_run=dry_run))
    if kind in ("feishu", "both"):
        notifiers.append(
            FeishuWebhookNotifier(
                os.environ.get("FEISHU_WEBHOOK_URL"),
                dry_run=dry_run,
            )
        )
    return notifiers


def _deliver(payload: NotificationPayload, notifiers: Sequence[Notifier]) -> None:
    for notifier in notifiers:
        try:
            notifier.send(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[{type(notifier).__name__}] 投递失败：{exc}", file=sys.stderr)


def run_supervisor(
    symbols: list[str],
    *,
    db_path: str | None = None,
    dry_run: bool = False,
    fixture_dir: Path | None = None,
    notifier_kind: str = "macos",
    notifiers: Sequence[Notifier] | None = None,
) -> int:
    """跑一轮监督。Tier 1 即时投，Tier 2 跨计划合并成每日一张卡。"""
    path = db_path or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    channels = list(notifiers) if notifiers is not None else _build_notifiers(
        notifier_kind, dry_run=dry_run
    )
    action_base_url = os.environ.get("FEISHU_ACTION_BASE_URL", "")
    action_secret = os.environ.get("FEISHU_ACTION_SECRET", "")
    conn = connect(path)
    total_nagged = 0
    tier2_payloads: list[NotificationPayload] = []
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
                result = run_plan_cycle(
                    conn,
                    plan,
                    ctx,
                    calendar=DEFAULT_TRADING_CALENDAR,
                )
                total_nagged += len(result.nagged)
                payloads = render_cycle(
                    plan,
                    result,
                    action_base_url=action_base_url,
                    action_secret=action_secret,
                )
                for payload in payloads:
                    if payload.tier == 1:
                        _deliver(payload, channels)
                    else:
                        tier2_payloads.append(payload)
        summary = merge_daily_summaries(tier2_payloads)
        if summary is not None:
            _deliver(summary, channels)
    finally:
        conn.close()
    return total_nagged


def _watchlist_symbols(conn) -> list[str]:  # noqa: ANN001
    from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

    return [item.symbol for item in list_watchlist(conn)]


def main() -> int:
    parser = argparse.ArgumentParser(description="LEI 监督员每日催办")
    parser.add_argument("--symbols", help="逗号分隔标的；不指定则取 watchlist 全部")
    parser.add_argument("--dry-run", action="store_true", help="不发送，只打印通知载荷")
    parser.add_argument("--db", help="SQLite 路径，默认 LEI_SQLITE_PATH/lab.db")
    parser.add_argument(
        "--notifier",
        choices=("macos", "feishu", "both"),
        default="macos",
        help="通知通道，默认 macos",
    )
    args = parser.parse_args()

    if args.symbols:
        symbols = [symbol.strip() for symbol in args.symbols.split(",") if symbol.strip()]
    else:
        conn = connect(args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path()))
        try:
            symbols = _watchlist_symbols(conn)
        finally:
            conn.close()

    if not symbols:
        print("无标的（watchlist 为空且未指定 --symbols）")
        return 0
    nagged = run_supervisor(
        symbols,
        db_path=args.db,
        dry_run=args.dry_run,
        notifier_kind=args.notifier,
    )
    print(f"完成：催办待办 {nagged} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
