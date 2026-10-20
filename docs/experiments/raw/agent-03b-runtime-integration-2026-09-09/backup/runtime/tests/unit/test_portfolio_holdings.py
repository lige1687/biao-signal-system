"""持仓台账单元测试：种子幂等、快照读取、code 保留、加权收益率。

与 test_portfolio.py（回测组合模拟器）区分：本文件测的是「我的持仓」
快照台账（src/lei_signal/portfolio/，2026-09-04 截图录入）。
不依赖真实 lab.db——全部用内存 SQLite（connect 时自动应用迁移）。
"""
from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from lei_signal.portfolio.models import PortfolioHolding
from lei_signal.portfolio.seed import SEED_HOLDINGS, SEED_GROUPS, seed
from lei_signal.portfolio.store import (
    holding_id_for,
    list_groups,
    list_holdings,
    load_snapshot,
    upsert_holding,
)
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn():
    with closing(connect(":memory:")) as c:
        yield c


def test_seed_roundtrip(conn: sqlite3.Connection):
    seed(conn)
    groups = list_groups(conn)
    holdings = list_holdings(conn)
    assert len(groups) == len(SEED_GROUPS) == 8
    assert len(holdings) == len(SEED_HOLDINGS) == 29
    total = round(sum(h.market_value for h in holdings), 2)
    assert total == 85613.10

    snap = load_snapshot(conn)
    assert snap["as_of"] == "2026-09-04"
    assert len(snap["observations"]) == 5
    # 每只持仓都能挂到已存在的分组
    known = {g.group_key for g in snap["groups"]}
    assert {h.group_key for hs in snap["holdings_by_group"].values() for h in hs} <= known


def test_seed_idempotent(conn: sqlite3.Connection):
    seed(conn)
    seed(conn)
    assert len(list_holdings(conn)) == 29
    assert len(list_groups(conn)) == 8


def test_upsert_preserves_backfilled_code(conn: sqlite3.Connection):
    """重跑 seed（code=None）不得清掉手工回填的基金代码。"""
    seed(conn)
    name = SEED_HOLDINGS[0].name
    hid = holding_id_for(name)
    with_code = PortfolioHolding(
        holding_id=hid, group_key=SEED_HOLDINGS[0].group_key, name=name,
        code="000001", market_value=1.0, return_pct=None,
    )
    upsert_holding(conn, with_code)
    conn.commit()

    seed(conn)  # code=None 的种子重写
    got = {h.holding_id: h for h in list_holdings(conn)}[hid]
    assert got.code == "000001"


def test_holding_id_stable():
    assert holding_id_for("易方达信息产业混合A") == holding_id_for("易方达信息产业混合A")
    assert holding_id_for("A") != holding_id_for("B")


def test_weighted_return():
    from lei_signal.api.routes.portfolio import _weighted_return

    hs = [
        PortfolioHolding("a", "g", "甲", None, 1000.0, 10.0),
        PortfolioHolding("b", "g", "乙", None, 3000.0, -2.0),
    ]
    # (1000*10 + 3000*(-2)) / 4000 = 1.0
    assert _weighted_return(hs, 4000.0) == 1.0
    # 全部缺失 → None
    assert _weighted_return([PortfolioHolding("a", "g", "甲", None, 1.0, None)], 1.0) is None
    assert _weighted_return([], 0.0) is None
