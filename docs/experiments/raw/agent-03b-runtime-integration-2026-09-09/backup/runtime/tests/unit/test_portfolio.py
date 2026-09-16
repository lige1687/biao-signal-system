"""组合层模拟器测试（src/lei_signal/backtest/portfolio.py）。

全部用合成交易 dict（与 execute_run 的 trades JSON 同构），不依赖真实
数据，逐条验证手册 6.3 规则：仓位算法 / 并发上限 / 同池上限 / 回撤降级
（含档位边界与创新高恢复）/ 无约束对照口径。
"""
from __future__ import annotations

import pytest

from lei_signal.backtest.portfolio import (
    PortfolioConfig,
    simulate_portfolio,
    unconstrained_config,
)

EQ0 = 1_000_000.0


def _t(symbol: str, entry: str, exit_: str, r_net: float, *,
       signal: str | None = None, pool: str = "A",
       entry_price: float = 11.0, stop_price: float = 10.0) -> dict:
    return {
        "symbol": symbol, "signal_date": signal or entry,
        "entry_date": entry, "exit_date": exit_, "r_net": r_net,
        "entry_price": entry_price, "stop_price": stop_price, "pool": pool,
    }


# ---------------------------------------------------------------- 仓位算法
def test_sizing_budget_shares_and_pnl() -> None:
    r = simulate_portfolio(
        [_t("AAA", "2024-01-02", "2024-02-01", 2.0)], PortfolioConfig())
    tk = r["taken"][0]
    assert tk["budget"] == pytest.approx(10_000.0)      # 1e6 × 1%
    assert tk["shares"] == pytest.approx(10_000.0)      # 10000 / (11−10)
    assert tk["pnl"] == pytest.approx(20_000.0)         # 预算 × r_net
    assert tk["factor"] == pytest.approx(1.0)
    assert r["final_equity"] == pytest.approx(1_020_000.0)
    assert r["total_return_pct"] == pytest.approx(2.0)
    assert r["cum_R_taken"] == pytest.approx(2.0)
    assert r["n_dropped"] == 0


def test_sequential_trades_compound() -> None:
    trades = [
        _t("AAA", "2024-01-02", "2024-02-01", 2.0),
        _t("BBB", "2024-02-02", "2024-03-01", 1.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    # 第二笔预算按第一笔结算后的权益计：1.02e6 × 1% = 10,200
    assert r["taken"][1]["budget"] == pytest.approx(10_200.0)
    assert r["final_equity"] == pytest.approx(1_000_000.0 * 1.02 * 1.01)
    assert r["cum_R_taken"] == pytest.approx(3.0)


def test_unconstrained_takes_all_overlaps() -> None:
    trades = [
        _t("AAA", "2024-01-02", "2024-03-01", 1.0),
        _t("BBB", "2024-01-02", "2024-02-01", -1.0),
        _t("CCC", "2024-01-02", "2024-04-01", 1.0),
    ]
    r = simulate_portfolio(trades, unconstrained_config(0.01))
    assert r["n_taken"] == 3 and r["n_dropped"] == 0
    # 三笔均在权益 1e6 时入场，预算各 10,000
    assert all(t["budget"] == pytest.approx(10_000.0) for t in r["taken"])
    # 结算按退出日：BBB(−) → AAA(+) → CCC(+)
    assert r["final_equity"] == pytest.approx(1_010_000.0)
    assert r["max_drawdown_pct"] == pytest.approx(1.0)   # 1e6 → 990k


# ---------------------------------------------------------------- 并发与分池
def test_nmax_drops_in_signal_order_and_releases() -> None:
    trades = [
        _t("AAA", "2024-01-02", "2024-02-01", 1.0, signal="2024-01-01"),
        _t("BBB", "2024-01-02", "2024-02-05", -0.5, signal="2024-01-01"),
        _t("BBB", "2024-02-02", "2024-02-20", 1.0),   # AAA 平仓后可进
    ]
    r = simulate_portfolio(
        trades, PortfolioConfig(max_concurrent=1))
    assert [t["symbol"] for t in r["taken"]] == ["AAA", "BBB"]
    d = r["dropped"][0]
    assert d["symbol"] == "BBB" and d["reason"] == "capacity_full"
    assert r["dropped_by_reason"]["capacity_full"]["n"] == 1
    assert r["dropped_by_reason"]["capacity_full"]["forfeited_R"] == pytest.approx(-0.5)
    assert r["concurrency"]["max_open"] == 1


def test_same_entry_day_earlier_signal_wins() -> None:
    trades = [
        _t("LATE", "2024-01-02", "2024-03-01", 5.0, signal="2024-01-01"),
        _t("EARLY", "2024-01-02", "2024-03-01", -5.0, signal="2023-12-29"),
    ]
    r = simulate_portfolio(trades, PortfolioConfig(max_concurrent=1))
    assert r["taken"][0]["symbol"] == "EARLY"
    assert r["dropped"][0]["symbol"] == "LATE"


def test_pool_cap_limits_same_pool_only() -> None:
    trades = [
        _t("A1", "2024-01-02", "2024-03-01", 1.0, pool="A"),
        _t("A2", "2024-01-02", "2024-03-01", -1.0, pool="A"),
        _t("B1", "2024-01-02", "2024-03-01", 2.0, pool="B"),
    ]
    r = simulate_portfolio(
        trades, PortfolioConfig(max_concurrent=None, pool_concurrent_cap=1))
    assert [t["symbol"] for t in r["taken"]] == ["A1", "B1"]
    assert r["dropped"][0]["reason"] == "pool_cap"
    assert r["concurrency"]["pool_max"] == {"A": 1, "B": 1}


def test_same_symbol_open_blocks_new_signal() -> None:
    trades = [
        _t("AAA", "2024-01-02", "2024-03-01", 1.0),
        _t("AAA", "2024-02-01", "2024-04-01", 2.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    assert r["n_taken"] == 1
    assert r["dropped"][0]["reason"] == "same_symbol_open"


def test_same_day_exit_does_not_leak_capacity() -> None:
    trades = [
        _t("AAA", "2024-01-02", "2024-01-02", -1.0),   # 当日开当日平
        _t("BBB", "2024-01-02", "2024-02-01", 1.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig(max_concurrent=1))
    assert r["n_taken"] == 2 and r["n_dropped"] == 0
    assert r["taken"][0]["settle"] == "same_day"
    assert r["final_equity"] == pytest.approx(EQ0 * 0.99 * 1.01)


# ---------------------------------------------------------------- 回撤降级
def test_deescalation_factor_levels() -> None:
    trades = [
        _t("T1", "2024-01-02", "2024-01-10", -15.0),   # dd 15% → 档1
        _t("T2", "2024-01-11", "2024-01-20", -25.0),   # dd 32% → 档3
        _t("T3", "2024-01-21", "2024-01-30", -1.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    budgets = [t["budget"] for t in r["taken"]]
    factors = [t["factor"] for t in r["taken"]]
    assert budgets[0] == pytest.approx(10_000.0)
    assert budgets[1] == pytest.approx(850_000 * 0.01 * 0.8)
    assert budgets[2] == pytest.approx(680_000 * 0.01 * 0.8**3)
    assert factors == pytest.approx([1.0, 0.8, 0.8**3])


def test_deescalation_recovers_on_new_high() -> None:
    trades = [
        _t("T1", "2024-01-02", "2024-01-10", -15.0),   # dd 15% → 档1
        _t("T2", "2024-01-11", "2024-01-20", 30.0),    # 创新高
        _t("T3", "2024-01-21", "2024-01-30", 1.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    t2, t3 = r["taken"][1], r["taken"][2]
    assert t2["budget"] == pytest.approx(850_000 * 0.01 * 0.8)
    assert t3["factor"] == pytest.approx(1.0)
    assert t3["budget"] == pytest.approx(r["final_equity"] / 1.01 / 1 * 0.01 * 1.0)


def test_deescalation_boundary_strictly_over_threshold() -> None:
    # −10R 单笔把权益打到恰 −10.0%（未「超过」→ 不降级），下一笔预算全额；
    # 该笔结算后回撤 10.9% > 10% → 再下一笔降档 ×0.8。
    trades = [
        _t("T1", "2024-01-02", "2024-01-10", -10.0),
        _t("T2", "2024-01-11", "2024-01-20", -1.0),
        _t("T3", "2024-01-21", "2024-01-30", -1.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    budgets = [t["budget"] for t in r["taken"]]
    factors = [t["factor"] for t in r["taken"]]
    assert budgets[0] == pytest.approx(10_000.0)          # dd 0% → 档0
    assert budgets[1] == pytest.approx(900_000 * 0.01)    # dd 恰 10.0% 未超 → 档0
    assert factors[2] == pytest.approx(0.8)               # dd 10.9% → 档1
    assert budgets[2] == pytest.approx(891_000 * 0.01 * 0.8)


def test_deescalation_off_is_control() -> None:
    trades = [_t("T1", "2024-01-02", "2024-01-10", -15.0),
              _t("T2", "2024-01-11", "2024-01-20", -1.0)]
    r = simulate_portfolio(trades, PortfolioConfig(dd_deescalate=False))
    assert r["taken"][1]["budget"] == pytest.approx(850_000 * 0.01)


# ---------------------------------------------------------------- 输入边界
def test_open_and_invalid_trades_excluded() -> None:
    trades = [
        _t("OK", "2024-01-02", "2024-02-01", 1.0),
        {**_t("OPEN", "2024-01-02", "2024-02-01", 1.0), "exit_date": None},
        {**_t("NOR", "2024-01-02", "2024-02-01", None), "r_net": None},
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    assert r["input_stats"]["excluded_open"] == 1
    assert r["input_stats"]["excluded_no_rnet"] == 1
    assert r["n_taken"] == 1


def test_duplicate_signals_deduped() -> None:
    t = _t("AAA", "2024-01-02", "2024-02-01", 1.0)
    r = simulate_portfolio([t, dict(t)], PortfolioConfig())
    assert r["input_stats"]["excluded_dedup"] == 1
    assert r["n_taken"] == 1


def test_bust_guard_drops_rest() -> None:
    trades = [
        _t("T1", "2024-01-02", "2024-01-03", -3.0),
        _t("T2", "2024-01-04", "2024-02-01", 1.0),
    ]
    cfg = PortfolioConfig(risk_pct=0.5, max_concurrent=None,
                          pool_concurrent_cap=None, dd_deescalate=False)
    r = simulate_portfolio(trades, cfg)
    assert r["busted"] is True
    assert r["dropped"][0]["reason"] == "bust"


def test_config_validation() -> None:
    with pytest.raises(ValueError, match="risk_pct"):
        PortfolioConfig(risk_pct=0.0)
    with pytest.raises(ValueError, match="max_concurrent"):
        PortfolioConfig(max_concurrent=0)
    with pytest.raises(ValueError, match="pool_concurrent_cap"):
        PortfolioConfig(pool_concurrent_cap=0)


# ---------------------------------------------------------------- 分年与回撤口径
def test_by_year_metrics_and_2026_drawdown() -> None:
    trades = [
        _t("W25", "2025-12-01", "2025-12-20", 50.0),    # 1e6 → 1.5e6
        _t("W26", "2026-01-02", "2026-03-01", 20.0),    # 1.5e6 → 1.8e6
        _t("L26", "2026-04-01", "2026-05-01", -20.0),   # 1.8e6 → 1.44e6
    ]
    r = simulate_portfolio(trades, PortfolioConfig())
    y26 = r["by_year"]["2026"]
    assert y26["return_pct"] == pytest.approx(-4.0, abs=0.01)   # 1.44/1.5−1
    assert y26["max_drawdown_pct"] == pytest.approx(20.0, abs=0.01)
    assert y26["cum_R"] == pytest.approx(0.0)
    assert r["by_year"]["2025"]["return_pct"] == pytest.approx(50.0)
    # 全局回撤以初始权益为种子：峰 1.8e6 → 谷 1.44e6
    assert r["max_drawdown_pct"] == pytest.approx(20.0, abs=0.01)
    assert r["final_equity"] == pytest.approx(1_440_000.0)


def test_curve_and_concurrency_stats() -> None:
    trades = [
        _t("AAA", "2024-01-02", "2024-03-01", 1.0),
        _t("BBB", "2024-01-02", "2024-02-01", 1.0),
    ]
    r = simulate_portfolio(trades, PortfolioConfig(max_concurrent=2))
    assert r["concurrency"]["max_open"] == 2
    # 时权均值：(30天×2仓 + 29天×1仓) / 59天 ≈ 1.51 → 利用率 ≈ 0.75
    assert r["concurrency"]["avg_open"] == pytest.approx(89 / 59, abs=0.02)
    assert r["concurrency"]["avg_utilization"] == pytest.approx(89 / 118, abs=0.02)
    assert r["curve"][0]["date"] == "2024-01-02"
    assert r["curve"][-1]["cum_R"] == pytest.approx(2.0)
