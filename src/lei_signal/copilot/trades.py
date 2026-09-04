"""基金成交台账：手动报单 → 净值定价 → 份额/盈亏核算。

口径（设计定稿 D1，2026-09-05 用户拍板）：
- 只做基金（场外与 ETF 统一按天天基金「单位净值」定价；ETF 的折溢价差异
  在 disclaimer 里说明，不引入第二条行情数据链路）。
- 报单默认收盘口径：找 ≤ trade_date 的最近一个净值日（QDII T+1 缺日属正常）。
- 份额 = 金额 ÷ 定价净值；买入累成本，卖出按持仓均价结转；
  已实现盈亏 = 卖出金额 −（均价成本 × 卖出份额）。
- 无净值可依时保持 pending，跑批次日补（不猜数）。
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from typing import Callable

from lei_signal.api.schemas import FundPositionDTO, FundTradeDTO
from lei_signal.portfolio.funddata import NavPoint, fetch_nav_history

NavFetcher = Callable[[str], list[NavPoint]]

_STATUS_CN = {"pending": "待定价", "priced": "已定价", "failed": "定价失败"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_dto(row: sqlite3.Row) -> FundTradeDTO:
    return FundTradeDTO(
        trade_id=row["trade_id"],
        fund_code=row["fund_code"],
        fund_name=row["fund_name"],
        side=row["side"],
        side_cn="申购" if row["side"] == "buy" else "赎回",
        amount=float(row["amount"]),
        trade_date=row["trade_date"],
        priced_nav=float(row["priced_nav"]) if row["priced_nav"] is not None else None,
        price_status=row["price_status"],
        price_status_cn=_STATUS_CN.get(row["price_status"], row["price_status"]),
        plan_id=row["plan_id"],
        source=row["source"],
        note=row["note"] or "",
        created_at=row["created_at"],
    )


def _nav_on_or_before(navs: list[NavPoint], day: str) -> float | None:
    for p in navs:  # 最新在前：第一个 date <= day 即答案
        if p.date <= day:
            return p.unit_nav
    return None


def create_trade(
    conn: sqlite3.Connection,
    *,
    fund_code: str,
    fund_name: str,
    side: str,
    amount: float,
    trade_date: str,
    plan_id: str | None = None,
    source: str = "web",
    note: str = "",
) -> FundTradeDTO:
    if side not in ("buy", "sell"):
        raise ValueError(f"side 只能是 buy/sell，收到 {side}")
    if amount <= 0:
        raise ValueError("amount 必须为正数（单位：元）")
    created = _now()
    h = hashlib.sha1(
        f"{fund_code}{side}{amount}{trade_date}{created}".encode()
    ).hexdigest()[:8]
    trade_id = f"ft_{fund_code}_{trade_date}_{h}"
    conn.execute(
        """INSERT INTO fund_trades
           (trade_id, fund_code, fund_name, side, amount, trade_date,
            priced_nav, price_status, plan_id, source, note, created_at, updated_at)
           VALUES (?,?,?,?,?,?,NULL,'pending',?,?,?,?,?)""",
        (trade_id, fund_code, fund_name, side, amount, trade_date,
         plan_id, source, note, created, created),
    )
    row = conn.execute(
        "SELECT * FROM fund_trades WHERE trade_id = ?", (trade_id,)
    ).fetchone()
    return _row_to_dto(row)


def price_pending_trades(
    conn: sqlite3.Connection, *, fetch_nav: NavFetcher = fetch_nav_history
) -> int:
    """补定价所有 pending 成交。无净值数据保持 pending（次日跑批再试），不猜数。"""
    rows = conn.execute(
        "SELECT * FROM fund_trades WHERE price_status = 'pending' ORDER BY trade_date"
    ).fetchall()
    nav_cache: dict[str, list[NavPoint]] = {}
    priced = 0
    for row in rows:
        code = row["fund_code"]
        if code not in nav_cache:
            try:
                nav_cache[code] = fetch_nav(code)
            except Exception:  # noqa: BLE001  网络失败：留 pending 次日再试
                nav_cache[code] = []
        nav = _nav_on_or_before(nav_cache[code], row["trade_date"])
        if nav is None:
            continue
        conn.execute(
            "UPDATE fund_trades SET priced_nav = ?, price_status = 'priced', "
            "updated_at = ? WHERE trade_id = ?",
            (nav, _now(), row["trade_id"]),
        )
        priced += 1
    return priced


def list_trades(
    conn: sqlite3.Connection, fund_code: str | None = None
) -> list[FundTradeDTO]:
    if fund_code:
        rows = conn.execute(
            "SELECT * FROM fund_trades WHERE fund_code = ? "
            "ORDER BY trade_date, created_at",
            (fund_code,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM fund_trades ORDER BY trade_date DESC, created_at DESC"
        ).fetchall()
    return [_row_to_dto(r) for r in rows]


def position_summary(
    conn: sqlite3.Connection, *, fetch_nav: NavFetcher = fetch_nav_history
) -> list[FundPositionDTO]:
    """按基金汇总：份额/成本/浮盈/已实现（只按已定价成交计算，pending 不计）。"""
    rows = conn.execute(
        "SELECT * FROM fund_trades WHERE price_status = 'priced' "
        "ORDER BY trade_date, created_at"
    ).fetchall()
    by_code: dict[str, dict] = {}
    for row in rows:
        st = by_code.setdefault(row["fund_code"], {
            "name": row["fund_name"], "shares": 0.0, "cost": 0.0, "realized": 0.0,
        })
        nav = float(row["priced_nav"])
        shares_delta = float(row["amount"]) / nav
        if row["side"] == "buy":
            st["shares"] += shares_delta
            st["cost"] += float(row["amount"])
        else:
            avg = st["cost"] / st["shares"] if st["shares"] > 0 else 0.0
            st["realized"] += float(row["amount"]) - avg * shares_delta
            st["shares"] -= shares_delta
            st["cost"] -= avg * shares_delta
    out: list[FundPositionDTO] = []
    for code, st in sorted(by_code.items()):
        latest: NavPoint | None = None
        try:
            navs = fetch_nav(code)
            latest = navs[0] if navs else None
        except Exception:  # noqa: BLE001
            latest = None
        mv = st["shares"] * latest.unit_nav if latest else None
        out.append(FundPositionDTO(
            fund_code=code,
            fund_name=st["name"],
            shares=st["shares"],
            cost=st["cost"],
            latest_nav=latest.unit_nav if latest else None,
            latest_nav_date=latest.date if latest else "",
            market_value=mv,
            unrealized_pnl=(mv - st["cost"]) if mv is not None else None,
            realized_pnl=st["realized"],
            note="只按已定价成交核算；待定价记录不计入",
        ))
    return out


def realized_pnl_of(conn: sqlite3.Connection, trade_id: str) -> dict:
    """单笔卖出的已实现盈亏明细（复盘用；买入或未定价返回空字段）。"""
    row = conn.execute(
        "SELECT * FROM fund_trades WHERE trade_id = ?", (trade_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"成交不存在: {trade_id}")
    prior = conn.execute(
        "SELECT * FROM fund_trades WHERE fund_code = ? AND price_status='priced' "
        "AND (trade_date < ? OR (trade_date = ? AND created_at <= ?)) "
        "ORDER BY trade_date, created_at",
        (row["fund_code"], row["trade_date"], row["trade_date"], row["created_at"]),
    ).fetchall()
    shares = cost = 0.0
    for r in prior:
        nav = float(r["priced_nav"])
        delta = float(r["amount"]) / nav
        if r["side"] == "buy":
            shares += delta
            cost += float(r["amount"])
        else:
            avg = cost / shares if shares > 0 else 0.0
            shares -= delta
            cost -= avg * delta
    nav = float(row["priced_nav"]) if row["priced_nav"] is not None else None
    if row["side"] != "sell" or nav is None:
        return {"priced_nav": nav, "shares_sold": None, "avg_cost": None,
                "realized_pnl": None}
    shares_sold = float(row["amount"]) / nav
    avg = cost / shares if shares > 0 else 0.0
    return {
        "priced_nav": nav,
        "shares_sold": shares_sold,
        "avg_cost": avg,
        "realized_pnl": float(row["amount"]) - avg * shares_sold,
    }
