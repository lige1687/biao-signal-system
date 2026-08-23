"""signal_alerts 表 CRUD (migration 016)。

设计语义（与 opportunity_scan.py 同模式）：
  launchd 11:35 / 14:45 / 15:05 扫全自选 -> upsert_signal_alerts 整体重写当日
  -> 看盘主页横幅 / 顶栏红点读表。不现场跑 scan（5-10s，轮询不可接受）。

as_of 通过一条 side='meta', kind='as_of' 的元信息行持久化（title 存口径值），
是「今日是否扫过」与「盘中临时 / 收盘」的唯一判据。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime

SIDE_SELL = "sell"
SIDE_UNAVAILABLE = "unavailable"
SIDE_META = "meta"

_TIER_RANK = {"hard": 0, "warn": 1, "soft": 2}


@dataclass(frozen=True, slots=True)
class SignalAlertRow:
    """signal_alerts 一行（key_prices 已反序列化为 dict）。"""

    scan_date: str
    symbol: str
    display_name: str
    side: str
    tier: str
    kind: str
    kind_cn: str = ""
    title: str = ""
    reason_cn: str = ""
    is_new: bool = False
    key_prices: dict[str, float] = field(default_factory=dict)
    provenance: str = "system"
    available_date: str = ""
    error: str | None = None
    generated_at: str = ""


def _insert(conn: sqlite3.Connection, row: SignalAlertRow, generated_at: str) -> None:
    conn.execute(
        """
        INSERT INTO signal_alerts (
            scan_date, symbol, display_name, side, tier, kind, kind_cn,
            title, reason_cn, is_new, key_prices, provenance, available_date,
            error, generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.scan_date, row.symbol, row.display_name, row.side, row.tier,
            row.kind, row.kind_cn, row.title, row.reason_cn,
            1 if row.is_new else 0,
            json.dumps(dict(row.key_prices), ensure_ascii=False),
            row.provenance, row.available_date, row.error,
            row.generated_at or generated_at,
        ),
    )


def upsert_signal_alerts(
    conn: sqlite3.Connection,
    scan_date: str,
    as_of: str,
    rows: list[SignalAlertRow],
) -> int:
    """当日整体重写（含 meta 行），返回写入行数（含 meta）。"""
    conn.execute("DELETE FROM signal_alerts WHERE scan_date = ?", (scan_date,))
    generated_at = datetime.now(UTC).isoformat()
    for row in rows:
        _insert(conn, row, generated_at)
    _insert(
        conn,
        SignalAlertRow(
            scan_date=scan_date, symbol="", display_name="", side=SIDE_META,
            tier="meta", kind="as_of", title=as_of, generated_at=generated_at,
        ),
        generated_at,
    )
    conn.commit()
    return len(rows) + 1


def _row_to_signal(row: sqlite3.Row) -> SignalAlertRow:
    try:
        prices: dict[str, float] = json.loads(row["key_prices"] or "{}")
    except (json.JSONDecodeError, TypeError):
        prices = {}
    return SignalAlertRow(
        scan_date=row["scan_date"], symbol=row["symbol"],
        display_name=row["display_name"], side=row["side"], tier=row["tier"],
        kind=row["kind"], kind_cn=row["kind_cn"], title=row["title"],
        reason_cn=row["reason_cn"], is_new=bool(row["is_new"]),
        key_prices=prices, provenance=row["provenance"],
        available_date=row["available_date"], error=row["error"],
        generated_at=row["generated_at"],
    )


def list_signal_alerts(
    conn: sqlite3.Connection, scan_date: str, *, side: str = SIDE_SELL,
) -> list[SignalAlertRow]:
    """读当日指定 side 的行，按 tier 硬→软、新增优先、symbol 排序。"""
    rows = conn.execute(
        """
        SELECT * FROM signal_alerts
        WHERE scan_date = ? AND side = ?
        ORDER BY CASE tier
            WHEN 'hard' THEN 0
            WHEN 'warn' THEN 1
            WHEN 'soft' THEN 2
            ELSE 3
        END, is_new DESC, symbol
        """,
        (scan_date, side),
    ).fetchall()
    return [_row_to_signal(r) for r in rows]


def get_scan_as_of(conn: sqlite3.Connection, scan_date: str) -> str | None:
    """当日扫描口径（intraday | close）；未扫描返回 None。"""
    row = conn.execute(
        "SELECT title FROM signal_alerts WHERE scan_date = ? AND side = ? AND kind = 'as_of' LIMIT 1",
        (scan_date, SIDE_META),
    ).fetchone()
    return row["title"] if row else None


def count_sell_alerts(
    conn: sqlite3.Connection,
    scan_date: str,
    *,
    tiers: tuple[str, ...] = ("hard", "warn"),
) -> int:
    """当日卖点半数（红点用，默认只计 hard+warn，soft 不打扰）。"""
    placeholders = ",".join("?" for _ in tiers)
    row = conn.execute(
        f"SELECT COUNT(*) FROM signal_alerts WHERE scan_date = ? AND side = ? AND tier IN ({placeholders})",  # noqa: S608
        (scan_date, SIDE_SELL, *tiers),
    ).fetchone()
    return int(row[0]) if row else 0


__all__ = [
    "SIDE_META",
    "SIDE_SELL",
    "SIDE_UNAVAILABLE",
    "SignalAlertRow",
    "count_sell_alerts",
    "get_scan_as_of",
    "list_signal_alerts",
    "upsert_signal_alerts",
]
