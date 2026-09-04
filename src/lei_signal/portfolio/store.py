"""持仓台账 SQLite CRUD。

照 ``plans/store.py`` 的连接模式（函数取 ``conn: sqlite3.Connection``）。
读写都很轻：这是低频更新的快照数据，v1 只需要 list + upsert + meta。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

from lei_signal.portfolio.models import (
    META_AS_OF,
    META_DATA_SOURCE,
    META_OBSERVATIONS,
    PortfolioGroup,
    PortfolioHolding,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def holding_id_for(name: str) -> str:
    """稳定 holding_id：名称哈希前 12 位。seed 重跑幂等（INSERT OR REPLACE）
    与后续按名更新都依赖它稳定，不用 uuid。"""
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]


def upsert_group(
    conn: sqlite3.Connection,
    group: PortfolioGroup,
) -> None:
    conn.execute(
        """
        INSERT INTO portfolio_groups
            (group_key, name, market, sort_order, verdict_cn, verdict_basis, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(group_key) DO UPDATE SET
            name = excluded.name,
            market = excluded.market,
            sort_order = excluded.sort_order,
            verdict_cn = excluded.verdict_cn,
            verdict_basis = excluded.verdict_basis,
            updated_at = excluded.updated_at
        """,
        (
            group.group_key,
            group.name,
            group.market,
            group.sort_order,
            group.verdict_cn,
            group.verdict_basis,
            _now(),
        ),
    )


def upsert_holding(
    conn: sqlite3.Connection,
    holding: PortfolioHolding,
) -> None:
    conn.execute(
        """
        INSERT INTO portfolio_holdings
            (holding_id, group_key, name, code, market_value, return_pct,
             tags, note, as_of, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(holding_id) DO UPDATE SET
            group_key = excluded.group_key,
            name = excluded.name,
            code = COALESCE(excluded.code, portfolio_holdings.code),
            market_value = excluded.market_value,
            return_pct = excluded.return_pct,
            tags = excluded.tags,
            note = excluded.note,
            as_of = excluded.as_of,
            updated_at = excluded.updated_at
        """,
        (
            holding.holding_id,
            holding.group_key,
            holding.name,
            holding.code,
            holding.market_value,
            holding.return_pct,
            json.dumps(list(holding.tags), ensure_ascii=False),
            holding.note,
            holding.as_of,
            _now(),
        ),
    )


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO portfolio_meta (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, value, _now()),
    )


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM portfolio_meta WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else None


def list_groups(conn: sqlite3.Connection) -> list[PortfolioGroup]:
    rows = conn.execute(
        """
        SELECT group_key, name, market, sort_order, verdict_cn, verdict_basis
        FROM portfolio_groups ORDER BY sort_order, group_key
        """
    ).fetchall()
    return [
        PortfolioGroup(
            group_key=r["group_key"],
            name=r["name"],
            market=r["market"],
            sort_order=r["sort_order"],
            verdict_cn=r["verdict_cn"],
            verdict_basis=r["verdict_basis"],
        )
        for r in rows
    ]


def list_holdings(conn: sqlite3.Connection) -> list[PortfolioHolding]:
    rows = conn.execute(
        """
        SELECT holding_id, group_key, name, code, market_value, return_pct,
               tags, note, as_of
        FROM portfolio_holdings ORDER BY market_value DESC, name
        """
    ).fetchall()
    out: list[PortfolioHolding] = []
    for r in rows:
        try:
            tags = tuple(json.loads(r["tags"] or "[]"))
        except (TypeError, ValueError):
            tags = ()
        out.append(
            PortfolioHolding(
                holding_id=r["holding_id"],
                group_key=r["group_key"],
                name=r["name"],
                code=r["code"],
                market_value=float(r["market_value"]),
                return_pct=float(r["return_pct"]) if r["return_pct"] is not None else None,
                tags=tags,
                note=r["note"] or "",
                as_of=r["as_of"] or "",
            )
        )
    return out


def load_snapshot(conn: sqlite3.Connection) -> dict:
    """整份持仓快照：分组（含挂好的持仓）+ meta。route 层直接序列化。"""
    groups = list_groups(conn)
    holdings = list_holdings(conn)
    by_group: dict[str, list[PortfolioHolding]] = {g.group_key: [] for g in groups}
    for h in holdings:
        # 分组被删后残留的持仓挂到列表外（不丢数据，route 会显式提示）
        by_group.setdefault(h.group_key, []).append(h)
    observations_raw = get_meta(conn, META_OBSERVATIONS)
    try:
        observations = json.loads(observations_raw) if observations_raw else []
    except (TypeError, ValueError):
        observations = []
    return {
        "as_of": get_meta(conn, META_AS_OF) or "",
        "data_source_cn": get_meta(conn, META_DATA_SOURCE) or "",
        "observations": observations,
        "groups": groups,
        "holdings_by_group": by_group,
    }
