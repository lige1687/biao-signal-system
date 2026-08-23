"""signal_alerts 表 CRUD（migration 016）门禁。

当日重扫 = 整体重写（先 DELETE 当日再 INSERT，与 daily_opportunity_scan 同语义）；
as_of 通过 meta 行持久化，读 API 据此判断「今日是否扫过」与盘中/收盘口径。
"""
from __future__ import annotations

import sqlite3

from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    count_sell_alerts,
    get_scan_as_of,
    list_signal_alerts,
    upsert_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect


def _conn() -> sqlite3.Connection:
    return connect(":memory:")


def _sell_row(**kw) -> SignalAlertRow:
    base = dict(
        scan_date="2026-08-21", symbol="600519.SS", display_name="贵州茅台",
        side=SIDE_SELL, tier="hard", kind="exit_proxy", kind_cn="退出代理",
        title="收盘同破 EMA20 与 20 日抵扣价", reason_cn="x（研究代理）",
        is_new=True, key_prices={"ema20": 10.5}, provenance="research_proxy",
        available_date="2026-08-21",
    )
    base.update(kw)
    return SignalAlertRow(**base)


def test_upsert_writes_rows_and_as_of_meta() -> None:
    conn = _conn()
    n = upsert_signal_alerts(conn, "2026-08-21", "intraday", [_sell_row()])
    assert n == 2  # 1 条信号 + 1 条 meta
    assert get_scan_as_of(conn, "2026-08-21") == "intraday"
    rows = list_signal_alerts(conn, "2026-08-21", side=SIDE_SELL)
    assert len(rows) == 1
    assert rows[0].key_prices == {"ema20": 10.5}
    assert rows[0].is_new is True


def test_rescan_rewrites_day_and_updates_as_of() -> None:
    conn = _conn()
    upsert_signal_alerts(conn, "2026-08-21", "intraday", [_sell_row()])
    upsert_signal_alerts(conn, "2026-08-21", "close", [])  # 收盘版无卖点信号
    assert get_scan_as_of(conn, "2026-08-21") == "close"
    assert list_signal_alerts(conn, "2026-08-21", side=SIDE_SELL) == []


def test_meta_and_unavailable_not_in_sell_list() -> None:
    conn = _conn()
    unavailable = SignalAlertRow(
        scan_date="2026-08-21", symbol="bad.SS", display_name="bad.SS",
        side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
        title="数据不可用", error="DATA_UNAVAILABLE: 行情获取失败",
    )
    upsert_signal_alerts(conn, "2026-08-21", "close", [unavailable])
    assert list_signal_alerts(conn, "2026-08-21", side=SIDE_SELL) == []
    unavailable_rows = list_signal_alerts(conn, "2026-08-21", side=SIDE_UNAVAILABLE)
    assert len(unavailable_rows) == 1
    assert unavailable_rows[0].error == "DATA_UNAVAILABLE: 行情获取失败"


def test_count_sell_alerts_hard_and_warn_only() -> None:
    conn = _conn()
    upsert_signal_alerts(conn, "2026-08-21", "close", [
        _sell_row(),
        _sell_row(symbol="000001.SZ", tier="warn", kind="key_wave_black"),
        _sell_row(symbol="300750.SZ", tier="soft", kind="color_black"),
    ])
    assert count_sell_alerts(conn, "2026-08-21") == 2  # hard + warn，soft 不计
    assert count_sell_alerts(conn, "2026-08-21", tiers=("hard",)) == 1


def test_no_scan_today_returns_none_and_zero() -> None:
    conn = _conn()
    assert get_scan_as_of(conn, "2026-08-21") is None
    assert count_sell_alerts(conn, "2026-08-21") == 0
