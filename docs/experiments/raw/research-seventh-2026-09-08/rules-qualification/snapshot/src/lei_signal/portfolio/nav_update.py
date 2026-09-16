"""持仓净值每日更新：反推份额锚点 + 刷新市值/收益。

口径（写死，防止后人重新发明）：
- 锚点：快照日市值来自 App 截图，实际对应 as_of 当日或前一日的已发布净值
  （QDII T+1）。取「≤ as_of 的最近一个净值日」为 snapshot_nav，
  implied_shares = 快照市值 / snapshot_nav，一次写定不再改。
- 成本：cost_value = 快照市值 / (1 + 截图持有收益率/100)，一次写定。
- 每日刷新：最新净值 -> market_value = implied_shares × latest_nav，
  return_pct = market_value / cost_value - 1。
- 缺最新净值（QDII 未发布）时沿用上一次 latest_nav，只更新日期口径不动数。
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from lei_signal.portfolio.funddata import fetch_nav_history
from lei_signal.portfolio.store import list_holdings


def _now() -> str:
    return datetime.now(UTC).isoformat()


def update_nav(conn: sqlite3.Connection, *, page_size: int = 40) -> dict[str, int]:
    """全量刷新。返回 {anchored, refreshed, skipped, failed}。"""
    stats = {"anchored": 0, "refreshed": 0, "skipped": 0, "failed": 0}
    for h in list_holdings(conn):
        if not h.code:
            stats["skipped"] += 1
            continue
        try:
            navs = fetch_nav_history(h.code, page_size=page_size)
        except Exception:  # noqa: BLE001 - 网络失败跳过单只，不中断批次
            stats["failed"] += 1
            continue
        if not navs:
            stats["failed"] += 1
            continue

        row = conn.execute(
            "SELECT 1 FROM portfolio_holdings_nav WHERE holding_id = ?",
            (h.holding_id,),
        ).fetchone()

        if row is None:
            # 首次锚定：找 ≤ as_of 的最近净值日
            snapshot_navs = [p for p in navs if p.date <= h.as_of] or navs[-1:]
            snap = snapshot_navs[0]
            if h.return_pct is not None and (1 + h.return_pct / 100.0) > 0:
                cost = h.market_value / (1 + h.return_pct / 100.0)
            else:
                cost = h.market_value
            conn.execute(
                """
                INSERT INTO portfolio_holdings_nav
                    (holding_id, code, snapshot_nav, snapshot_nav_date,
                     implied_shares, cost_value, latest_nav, latest_nav_date,
                     updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (h.holding_id, h.code, snap.unit_nav, snap.date,
                 h.market_value / snap.unit_nav, cost,
                 navs[0].unit_nav, navs[0].date, _now()),
            )
            stats["anchored"] += 1
        else:
            conn.execute(
                """
                UPDATE portfolio_holdings_nav
                SET latest_nav = ?, latest_nav_date = ?, updated_at = ?
                WHERE holding_id = ?
                """,
                (navs[0].unit_nav, navs[0].date, _now(), h.holding_id),
            )
            stats["refreshed"] += 1

        # 刷新市值/收益（无论首次还是例行）
        navrow = conn.execute(
            """
            SELECT implied_shares, cost_value, latest_nav
            FROM portfolio_holdings_nav WHERE holding_id = ?
            """,
            (h.holding_id,),
        ).fetchone()
        mv = navrow["implied_shares"] * navrow["latest_nav"]
        ret = (mv / navrow["cost_value"] - 1.0) * 100.0 if navrow["cost_value"] > 0 else None
        conn.execute(
            """
            UPDATE portfolio_holdings
            SET market_value = ?, return_pct = ?, updated_at = ?
            WHERE holding_id = ?
            """,
            (round(mv, 2), round(ret, 2) if ret is not None else None,
             _now(), h.holding_id),
        )
    conn.commit()
    return stats
