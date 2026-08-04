"""自选股与分组 CRUD（SQLite 迁移 7/8 的 watchlist_items / watchlist_groups）。

分组语义
--------
- 用户自建组存在 ``watchlist_groups``；``watchlist_items.group_id`` 指向它。
- ``group_id IS NULL`` = 未分组，左栏归入「未分组」，是合法状态。
- 内置「大盘」组不入库（见 api/config.DASHBOARD_INDICES），不可删改。
- 删组时把成员置 NULL（保留标的），不级联删除——删组不该丢自选。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class WatchlistGroup:
    group_id: int
    name: str
    sort_order: int
    created_at: str


@dataclass(frozen=True, slots=True)
class WatchlistItem:
    symbol: str  # resolve_symbol 后的 Yahoo 口径
    display_name: str | None
    market: str
    note: str | None
    sort_order: int
    added_at: str
    group_id: int | None = None


# ---------------------------------------------------------------- 分组


def list_groups(conn: sqlite3.Connection) -> list[WatchlistGroup]:
    rows = conn.execute(
        "SELECT group_id, name, sort_order, created_at "
        "FROM watchlist_groups ORDER BY sort_order, group_id"
    ).fetchall()
    return [
        WatchlistGroup(
            group_id=row["group_id"],
            name=row["name"],
            sort_order=row["sort_order"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def create_group(conn: sqlite3.Connection, name: str) -> WatchlistGroup:
    """新建分组。组名重复时返回既有组（幂等，不报错）。"""
    clean = name.strip()
    if not clean:
        raise ValueError("分组名不能为空")
    existing = conn.execute(
        "SELECT group_id, name, sort_order, created_at FROM watchlist_groups WHERE name = ?",
        (clean,),
    ).fetchone()
    if existing:
        return WatchlistGroup(
            group_id=existing["group_id"],
            name=existing["name"],
            sort_order=existing["sort_order"],
            created_at=existing["created_at"],
        )
    next_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 AS n FROM watchlist_groups"
    ).fetchone()["n"]
    created_at = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        "INSERT INTO watchlist_groups (name, sort_order, created_at) VALUES (?, ?, ?)",
        (clean, next_order, created_at),
    )
    conn.commit()
    return WatchlistGroup(
        group_id=int(cursor.lastrowid or 0),
        name=clean,
        sort_order=next_order,
        created_at=created_at,
    )


def rename_group(conn: sqlite3.Connection, group_id: int, name: str) -> bool:
    clean = name.strip()
    if not clean:
        raise ValueError("分组名不能为空")
    cursor = conn.execute(
        "UPDATE watchlist_groups SET name = ? WHERE group_id = ?", (clean, group_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_group(conn: sqlite3.Connection, group_id: int) -> bool:
    """删组。组内标的转为未分组（group_id=NULL），不删标的本身。"""
    conn.execute(
        "UPDATE watchlist_items SET group_id = NULL WHERE group_id = ?", (group_id,)
    )
    cursor = conn.execute(
        "DELETE FROM watchlist_groups WHERE group_id = ?", (group_id,)
    )
    conn.commit()
    return cursor.rowcount > 0


def reorder_groups(conn: sqlite3.Connection, group_ids: list[int]) -> None:
    """按给定顺序重排分组。未列出的组保持原相对顺序排在后面。"""
    for index, gid in enumerate(group_ids, start=1):
        conn.execute(
            "UPDATE watchlist_groups SET sort_order = ? WHERE group_id = ?", (index, gid)
        )
    conn.commit()


# ---------------------------------------------------------------- 标的


def list_watchlist(conn: sqlite3.Connection) -> list[WatchlistItem]:
    rows = conn.execute(
        "SELECT symbol, display_name, market, note, sort_order, added_at, group_id "
        "FROM watchlist_items ORDER BY sort_order, added_at"
    ).fetchall()
    return [
        WatchlistItem(
            symbol=row["symbol"],
            display_name=row["display_name"],
            market=row["market"],
            note=row["note"],
            sort_order=row["sort_order"],
            added_at=row["added_at"],
            group_id=row["group_id"],
        )
        for row in rows
    ]


def upsert_watchlist(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    display_name: str | None,
    market: str,
    note: str | None = None,
    group_id: int | None = None,
) -> WatchlistItem:
    """按 symbol 幂等 upsert；重复添加保留原 added_at 与 sort_order。"""
    existing = conn.execute(
        "SELECT sort_order, added_at FROM watchlist_items WHERE symbol = ?", (symbol,)
    ).fetchone()
    if existing:
        sort_order, added_at = existing["sort_order"], existing["added_at"]
    else:
        sort_row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next FROM watchlist_items"
        ).fetchone()
        sort_order = sort_row["next"]
        added_at = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO watchlist_items "
        "(symbol, display_name, market, note, sort_order, added_at, group_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (symbol, display_name, market, note, sort_order, added_at, group_id),
    )
    conn.commit()
    return WatchlistItem(
        symbol=symbol,
        display_name=display_name,
        market=market,
        note=note,
        sort_order=sort_order,
        added_at=added_at,
        group_id=group_id,
    )


def move_to_group(
    conn: sqlite3.Connection, symbol: str, group_id: int | None
) -> bool:
    """把标的移到指定分组；group_id=None 表示移出分组。"""
    cursor = conn.execute(
        "UPDATE watchlist_items SET group_id = ? WHERE symbol = ?", (group_id, symbol)
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_watchlist(conn: sqlite3.Connection, symbol: str) -> bool:
    """删除自选股。幂等：返回是否真的删掉了行。"""
    cursor = conn.execute("DELETE FROM watchlist_items WHERE symbol = ?", (symbol,))
    conn.commit()
    return cursor.rowcount > 0
