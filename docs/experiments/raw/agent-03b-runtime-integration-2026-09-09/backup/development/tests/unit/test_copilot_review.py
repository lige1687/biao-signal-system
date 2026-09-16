"""单笔复盘：纪律面（预案原文+催办/推迟/复议计数）+ 结果面（盈亏/R倍数）。"""
from __future__ import annotations

import pytest

from lei_signal.copilot import review, trades
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _nav(*p):
    return lambda code, page_size=40: [NavPoint(date=d, unit_nav=v) for d, v in p]


def _seed_trade(conn) -> str:
    t1 = trades.create_trade(conn, fund_code="012414", fund_name="T",
                             side="buy", amount=10000.0, trade_date="2026-09-01")
    t2 = trades.create_trade(conn, fund_code="012414", fund_name="T",
                             side="sell", amount=5000.0, trade_date="2026-09-10")
    trades.price_pending_trades(conn, fetch_nav=_nav(
        ("2026-09-10", 1.25), ("2026-09-01", 1.00)))
    assert t1.price_status != "failed"
    return t2.trade_id


def _joined(card) -> str:
    return "\n".join(line for s in card.sections for line in s.lines)


def test_trade_review_without_plan(conn):
    tid = _seed_trade(conn)
    card = review.build_trade_review(conn, tid)
    assert card is not None and card.kind == "trade"
    joined = _joined(card)
    assert "无关联计划" in joined
    assert card.realized_pnl == pytest.approx(1000.0)


def test_trade_review_with_plan_discipline(conn):
    from lei_signal.plans.store import confirm_plan, create_plan

    tid = _seed_trade(conn)
    trade = trades.list_trades(conn)[0]
    plan = create_plan(
        conn,
        symbol="515880", module="A", direction="long",
        ruleset_version="test",
        reason="测试", valid_until="2026-10-01",
        entry_rule_id="pullback_watch",
        thesis_cn="冲通信回调",
        invalidation_criteria_cn="跌破结构C点",
        drawdown_playbook_cn="回踩均线正常",
        take_profit_plan_cn="到前高减半",
        stop_plan_cn="收盘破失效价退出",
        invalidation_price=0.90,
        entry_price_ref=1.00,
    )
    confirm_plan(conn, plan.plan_id)
    conn.execute(
        "UPDATE fund_trades SET plan_id = ? WHERE trade_id = ?",
        (plan.plan_id, tid),
    )
    conn.commit()
    card = review.build_trade_review(conn, tid)
    joined = _joined(card)
    assert "冲通信回调" in joined          # 当初预案原文
    # 风险额 = 卖出金额 × |入场-失效|/入场 = 5000 × 0.10 = 500；盈亏 1000 → R=2
    assert card.r_multiple == pytest.approx(2.0)


def test_review_save_and_get_roundtrip(conn):
    tid = _seed_trade(conn)
    card = review.build_trade_review(conn, tid)
    review.save_review(conn, card)
    got = review.get_review(conn, "trade", tid)
    assert got is not None and got.review_id == card.review_id


def test_review_missing_trade_returns_none(conn):
    assert review.build_trade_review(conn, "ft_x_y_z") is None
