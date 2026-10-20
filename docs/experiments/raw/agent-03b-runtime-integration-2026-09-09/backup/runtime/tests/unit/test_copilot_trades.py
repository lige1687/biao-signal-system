"""基金台账：创建/定价/盈亏三件套。fetch_nav 全部注入假数据，不打网络。"""
from __future__ import annotations

import pytest

from lei_signal.copilot import trades
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _nav(*points: tuple[str, float]):
    def fetch(code, page_size=40):
        return [NavPoint(date=d, unit_nav=v) for d, v in points]
    return fetch


def test_create_trade_pending(conn):
    t = trades.create_trade(conn, fund_code="012414", fund_name="测试基金",
                            side="buy", amount=10000.0, trade_date="2026-09-04")
    assert t.price_status == "pending" and t.priced_nav is None


def test_price_pending_uses_nav_on_or_before_date(conn):
    trades.create_trade(conn, fund_code="012414", fund_name="测试",
                        side="buy", amount=10000.0, trade_date="2026-09-04")
    n = trades.price_pending_trades(
        conn,
        fetch_nav=_nav(("2026-09-05", 1.25), ("2026-09-04", 1.20), ("2026-09-03", 1.18)),
    )
    assert n == 1
    rows = trades.list_trades(conn)
    assert rows[0].priced_nav == pytest.approx(1.20)
    assert rows[0].price_status == "priced"


def test_price_pending_qdii_missing_day_falls_back_latest(conn):
    """QDII T+1：当日净值未发布时用 ≤ 日期的最近净值（与 nav_update 口径一致）。"""
    trades.create_trade(conn, fund_code="270042", fund_name="QDII",
                        side="buy", amount=5000.0, trade_date="2026-09-05")
    trades.price_pending_trades(conn, fetch_nav=_nav(("2026-09-03", 2.00)))
    rows = trades.list_trades(conn)
    assert rows[0].priced_nav == pytest.approx(2.00)


def test_price_pending_no_nav_keeps_pending(conn):
    trades.create_trade(conn, fund_code="000000", fund_name="无数据",
                        side="buy", amount=1000.0, trade_date="2026-09-05")
    n = trades.price_pending_trades(conn, fetch_nav=lambda code, page_size=40: [])
    assert n == 0
    assert trades.list_trades(conn)[0].price_status == "pending"  # 次日再试


def test_position_summary_buy_sell_realized(conn):
    # 买 10000 @1.00 -> 份额10000；卖 5000 @1.25 -> 份额4000，实现 5000-4000*1.0
    trades.create_trade(conn, fund_code="012414", fund_name="T", side="buy",
                        amount=10000.0, trade_date="2026-09-01")
    trades.create_trade(conn, fund_code="012414", fund_name="T", side="sell",
                        amount=5000.0, trade_date="2026-09-10")
    trades.price_pending_trades(conn, fetch_nav=_nav(
        ("2026-09-10", 1.25), ("2026-09-01", 1.00)))
    pos = trades.position_summary(conn, fetch_nav=_nav(("2026-09-10", 1.25)))
    assert len(pos) == 1
    p = pos[0]
    assert p.shares == pytest.approx(10000.0 - 4000.0)
    assert p.realized_pnl == pytest.approx(5000.0 - 4000.0 * 1.00)
    assert p.market_value == pytest.approx(6000.0 * 1.25)


def test_realized_pnl_of(conn):
    trades.create_trade(conn, fund_code="012414", fund_name="T", side="buy",
                        amount=10000.0, trade_date="2026-09-01")
    sell = trades.create_trade(conn, fund_code="012414", fund_name="T", side="sell",
                               amount=5000.0, trade_date="2026-09-10")
    trades.price_pending_trades(conn, fetch_nav=_nav(
        ("2026-09-10", 1.25), ("2026-09-01", 1.00)))
    info = trades.realized_pnl_of(conn, sell.trade_id)
    assert info["priced_nav"] == pytest.approx(1.25)
    assert info["realized_pnl"] == pytest.approx(1000.0)


def test_create_rejects_bad_side_and_amount(conn):
    with pytest.raises(ValueError):
        trades.create_trade(conn, fund_code="012414", fund_name="T",
                            side="hold", amount=1.0, trade_date="2026-09-04")
    with pytest.raises(ValueError):
        trades.create_trade(conn, fund_code="012414", fund_name="T",
                            side="buy", amount=-5, trade_date="2026-09-04")
