"""统一信号扫描：买点（既有 verdict）+ 卖点（四档提取）一次落库。

买点复用 routes/opportunities.run_opportunity_scan 的扫描逻辑，本模块同步重写
daily_opportunity_scan 与 signal_alerts 两表（设计 §3.2 当日整体重写，空自选 = 清空
当日买点行 + 写 meta 行）；卖点紧接着用 refresh=False 读同一份 TTL 缓存做纯提取。
数据不可用的标的显式写 unavailable 行，不静默为「无信号」。
"""
from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
from typing import Any

from lei_signal.api.opportunity_scan import today_date, upsert_scan_results
from lei_signal.api.routes.opportunities import run_opportunity_scan
from lei_signal.api.sell_signals import extract_sell_signals
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    upsert_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect

AS_OF_INTRADAY = "intraday"
AS_OF_CLOSE = "close"


def run_signal_scan(
    service: Any,
    db_path: str,
    *,
    symbols: list[str] | None = None,
    as_of: str = AS_OF_CLOSE,
    refresh: bool = True,
    dry_run: bool = False,
) -> dict:
    """扫全自选（或指定 symbols）：买点 + 卖点 + 数据不可用，整体重写当日两表。"""
    if symbols:
        wanted = list(symbols)
    else:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(connect(db_path)) as conn:
            wanted = [item.symbol for item in list_watchlist(conn)]
    scan_date = today_date()

    rows: list[SignalAlertRow] = []
    buy_items: list[Any] = []
    if wanted:
        buy_response = run_opportunity_scan(
            service, db_path, symbols=wanted, refresh=refresh, only_with_candidates=True,
        )
        buy_items = buy_response.items
        # 买点扫描刚刷新过 TTL 缓存，这里 refresh=False 纯读缓存，不再抓网
        entries = service.get_many(wanted, refresh=False)
        for symbol in wanted:
            entry = entries.get(symbol)
            if entry is None or entry.result is None:
                rows.append(SignalAlertRow(
                    scan_date=scan_date, symbol=symbol, display_name=symbol,
                    side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
                    title="数据不可用",
                    error=(entry.error if entry else "分析不可用"),
                ))
                continue
            for sig in extract_sell_signals(entry.result):
                rows.append(SignalAlertRow(
                    scan_date=scan_date, symbol=symbol,
                    display_name=getattr(entry.result, "display_name", "") or symbol,
                    side=SIDE_SELL, tier=sig.tier, kind=sig.kind,
                    kind_cn=sig.kind_cn, title=sig.title, reason_cn=sig.reason_cn,
                    is_new=sig.is_new, key_prices=dict(sig.key_prices),
                    provenance=sig.provenance, available_date=sig.available_date,
                ))

    if not dry_run:
        with closing(connect(db_path)) as conn:
            # 设计 §3.2 两表整体重写：买点行先落 daily_opportunity_scan（同
            # scripts/daily_scan.py:95-97 模式），再落 signal_alerts（含 as_of meta 行）。
            # 两个 upsert 各自内部 commit，无需额外 commit。
            upsert_scan_results(conn, scan_date, buy_items)
            upsert_signal_alerts(conn, scan_date, as_of, rows)

    return {
        "scan_date": scan_date,
        "as_of": as_of,
        "scanned": len(wanted),
        "sell_rows": sum(1 for r in rows if r.side == SIDE_SELL),
        "unavailable": sum(1 for r in rows if r.side == SIDE_UNAVAILABLE),
        "generated_at": datetime.now(UTC).isoformat(),
    }


__all__ = ["AS_OF_CLOSE", "AS_OF_INTRADAY", "run_signal_scan"]
