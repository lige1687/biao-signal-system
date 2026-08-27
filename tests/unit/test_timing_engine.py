"""timing_backtest.engine T+1 开盘成交模拟测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.engine import simulate


def _frame() -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=5)
    return pd.DataFrame(
        {
            "open": [100.0, 110.0, 120.0, 130.0, 140.0],
            "close": [105.0, 115.0, 125.0, 135.0, 145.0],
            "b20": 10.0,
            "b50": 10.0,
            "b200": 10.0,
        },
        index=idx,
    )


def test_t_plus_1_open_execution():
    target = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0], index=_frame().index)  # 第2日收盘信号
    res = simulate(_frame(), target, fee_bps=0.0)
    assert res.daily["weight"].iloc[0] == 0.0
    assert res.daily["weight"].iloc[1] == 0.0  # 信号日仍未执行
    assert res.daily["weight"].iloc[2] == pytest.approx(1.0)  # T+1 开盘 120 建仓
    assert res.daily["weight"].iloc[4] == pytest.approx(0.0)  # 第4日信号 → 第5日开盘清仓
    # 建仓日开盘 120 全仓 → 当日收盘 125：净值 = 125/120
    assert res.daily["equity"].iloc[2] == pytest.approx(125.0 / 120.0)
    # 清仓日开盘 140 卖出锁定 → 净值 = 140/120（此后空仓不变）
    assert res.daily["equity"].iloc[4] == pytest.approx(140.0 / 120.0)


def test_fees_reduce_equity():
    target = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0], index=_frame().index)
    free = simulate(_frame(), target, fee_bps=0.0).daily["equity"]
    costly = simulate(_frame(), target, fee_bps=100.0).daily["equity"]  # 1% 单边
    assert costly.iloc[-1] < free.iloc[-1]
    # 手算：建仓 eq_open=1 扣 1% 费 → 0.99 全仓 120；
    # 清仓时 eq_open = 0.99×140/120 再扣 1% 费
    expected = 0.99 * (140.0 / 120.0) * 0.99
    assert costly.iloc[-1] == pytest.approx(expected)


def test_no_lookahead():
    target = pd.Series([0.0, 1.0, 1.0, 1.0, 1.0], index=_frame().index)
    r1 = simulate(_frame(), target, 0.0).daily["equity"]
    tampered = _frame()
    tampered.loc[tampered.index[4], "close"] = 999.0
    r2 = simulate(tampered, target, 0.0).daily["equity"]
    assert list(r1[:4]) == list(r2[:4])  # 未来 close 不影响此前净值


def test_benchmark_buy_and_hold():
    res = simulate(_frame(), pd.Series(1.0, index=_frame().index), 0.0)
    # 与策略同口径：首个可执行日（第 2 日）开盘买入 → 110 建仓
    assert res.daily["benchmark"].iloc[-1] == pytest.approx(145.0 / 110.0)
    assert res.daily["equity"].iloc[-1] == pytest.approx(145.0 / 110.0)
    assert res.trades[0]["date"] == res.daily.index[1].strftime("%Y-%m-%d")
    assert res.trades[0]["price"] == pytest.approx(110.0)
    assert res.trades[0]["new_weight"] == pytest.approx(1.0)


def test_trades_record_details():
    target = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0], index=_frame().index)
    res = simulate(_frame(), target, fee_bps=5.0)
    assert [t["new_weight"] for t in res.trades] == pytest.approx([1.0, 0.0])
    assert res.trades[0]["prev_weight"] == 0.0
    assert res.trades[0]["fee"] > 0.0
    assert res.trades[0]["turnover"] == pytest.approx(1.0)


def test_cash_rate_accrues_on_idle_cash():
    target = pd.Series([0.0] * 5, index=_frame().index)  # 全程空仓
    zero = simulate(_frame(), target, fee_bps=0.0, cash_rate=0.0)
    five_pct = simulate(_frame(), target, fee_bps=0.0, cash_rate=0.05)
    assert zero.daily["equity"].iloc[-1] == pytest.approx(1.0)
    # 4 个计息日（第2日起）：(1+0.05/252)^4
    assert five_pct.daily["equity"].iloc[-1] == pytest.approx((1 + 0.05 / 252) ** 4)
