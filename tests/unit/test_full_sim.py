"""full_sim 单测：信号去重规则 + 宽度档位 cap + 周频 t+1 + cap_fn 接线。"""
from __future__ import annotations

from lei_signal.backtest.full_sim import (
    TIERS_V1,
    cap_fn_from_map,
    dedup_signals,
    filter_by_sector,
    position_cap_map,
    tier_cap,
)
from lei_signal.backtest.portfolio import PortfolioConfig, simulate_portfolio


def _t(sym, sig, entry, exit_, r=1.0, module="A"):
    return {"symbol": sym, "signal_date": sig, "entry_date": entry,
            "exit_date": exit_, "r_net": r, "module": module}


# ---------------------------------------------------------------- 去重

def test_dedup_exact_duplicate():
    trades = [_t("X", "2024-01-02", "2024-01-03", "2024-02-01", 2.0),
              _t("X", "2024-01-02", "2024-01-03", "2024-02-01", 2.0)]
    kept, st = dedup_signals(trades)
    assert len(kept) == 1 and st["dup_exact"] == 1


def test_dedup_overlap_open():
    # 后到信号落在上一笔 [signal, exit] 生命周期内 → 丢弃
    trades = [_t("X", "2024-01-02", "2024-01-03", "2024-02-01", 1.0),
              _t("X", "2024-01-20", "2024-01-22", "2024-03-01", 5.0),
              # 上一笔已退出（signal > exit）→ 保留
              _t("X", "2024-02-05", "2024-02-06", "2024-03-01", 1.0)]
    kept, st = dedup_signals(trades)
    assert st["overlap_open"] == 1
    assert [t["r_net"] for t in kept] == [1.0, 1.0]


def test_dedup_same_day_module_priority():
    trades = [_t("X", "2024-01-02", "2024-01-05", "2024-02-01", 1.0, module="C"),
              _t("X", "2024-01-02", "2024-01-03", "2024-03-01", 3.0, module="A"),
              _t("X", "2024-01-02", "2024-01-04", "2024-03-01", 2.0, module="B'")]
    kept, st = dedup_signals(trades)
    assert st["same_day_module"] == 2
    assert kept[0]["module"] == "A"


def test_dedup_different_symbols_independent():
    trades = [_t("X", "2024-01-02", "2024-01-03", "2024-02-01"),
              _t("Y", "2024-01-03", "2024-01-04", "2024-02-01")]
    kept, st = dedup_signals(trades)
    assert len(kept) == 2 and st["dropped_total"] == 0


# ---------------------------------------------------------------- 档位

def test_tier_cap_levels_v1():
    assert tier_cap(10, TIERS_V1) == 1.0
    assert tier_cap(20, TIERS_V1) == 1.0   # 边界含
    assert tier_cap(40, TIERS_V1) == 0.8
    assert tier_cap(60, TIERS_V1) == 0.6
    assert tier_cap(85, TIERS_V1) == 0.4
    assert tier_cap(99, TIERS_V1) == 0.2


def test_tier_cap_missing_data_returns_one():
    assert tier_cap(float("nan"), TIERS_V1) == 1.0


def test_position_cap_map_weekly_t_plus_one():
    # 一周内三天宽度数据；周五（最后一天）信号，次交易日生效
    breadth = {"2024-01-08": 50.0, "2024-01-10": 55.0, "2024-01-12": 30.0,
               "2024-01-15": 90.0}  # 下周一
    cmap = position_cap_map(breadth, TIERS_V1)
    assert cmap == {"2024-01-15": 0.8}  # 30→0.8 档，t+1 生效


def test_cap_fn_forward_fill_and_before_start():
    fn = cap_fn_from_map({"2024-02-01": 0.4, "2024-03-01": 1.0})
    assert fn("2024-01-15") == 1.0   # 首个生效日前不追溯缩放
    assert fn("2024-02-01") == 0.4
    assert fn("2024-02-20") == 0.4
    assert fn("2024-03-05") == 1.0


# ---------------------------------------------------------------- cap_fn 接线

def _stream(n=3):
    return [{"symbol": f"S{i}", "signal_date": "2024-01-02",
             "entry_date": "2024-01-03", "exit_date": "2024-02-01",
             "r_net": 1.0, "entry_price": 110.0, "stop_price": 100.0,
             "pool": "main"} for i in range(n)]


def test_cap_fn_none_matches_historical_behavior():
    base = PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                           pool_concurrent_cap=6, dd_deescalate=True)
    r = simulate_portfolio(_stream(), base)
    assert r["taken"][0]["cap"] == 1.0
    assert abs(r["taken"][0]["budget"] - 10_000.0) < 1e-6


def test_cap_fn_scales_budget_and_concurrency():
    cfg = PortfolioConfig(risk_pct=0.01, max_concurrent=2,
                          pool_concurrent_cap=6, dd_deescalate=True,
                          cap_fn=lambda d: 0.5)
    r = simulate_portfolio(_stream(3), cfg)
    # 预算减半；N_max = ceil(2*0.5)=1 → 第 2、3 笔被容量丢弃
    assert abs(r["taken"][0]["budget"] - 5_000.0) < 1e-6
    assert r["n_taken"] == 1
    assert r["dropped_by_reason"]["capacity_full"]["n"] == 2


def test_cap_fn_zero_cap_floor_one_concurrent():
    # cap 极小：预算趋零，N/池上限均钳到下限 1 → 同日只放 1 笔
    cfg = PortfolioConfig(risk_pct=0.01, max_concurrent=5,
                          pool_concurrent_cap=6, dd_deescalate=True,
                          cap_fn=lambda d: 0.01)
    r = simulate_portfolio(_stream(3), cfg)
    assert r["n_taken"] == 1
    assert r["taken"][0]["budget"] < 200.0
    assert r["dropped_by_reason"]["capacity_full"]["n"] == 2


def test_cap_fn_only_shrinks_new_positions():
    # 已持仓不受 cap 影响：入场后 cap 下降，仓位不平、损益按原预算结算
    trades = [{"symbol": "S", "signal_date": "2024-01-02",
               "entry_date": "2024-01-03", "exit_date": "2024-03-01",
               "r_net": 2.0, "entry_price": 110.0, "stop_price": 100.0,
               "pool": "main"},
              {"symbol": "T", "signal_date": "2024-01-02",
               "entry_date": "2024-02-15", "exit_date": "2024-03-01",
               "r_net": 1.0, "entry_price": 55.0, "stop_price": 50.0,
               "pool": "main"}]
    cfg = PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                          pool_concurrent_cap=None, dd_deescalate=False,
                          cap_fn=lambda d: 0.2 if d >= "2024-02-01" else 1.0)
    r = simulate_portfolio(trades, cfg)
    by_sym = {t["symbol"]: t for t in r["taken"]}
    assert abs(by_sym["S"]["budget"] - 10_000.0) < 1e-6   # cap=1 入场（1%×100 万）
    assert by_sym["T"]["cap"] == 0.2                       # 新仓被缩


# ---------------------------------------------------------------- 板块过滤

def test_filter_by_sector_keeps_and_counts():
    trades = [_t("512800", "2024-01-02", "2024-01-03", "2024-02-01", 1.0),
              _t("512690", "2024-01-05", "2024-01-08", "2024-02-01", 2.0),
              _t("512690", "2024-03-01", "2024-03-04", "2024-04-01", 3.0)]
    # 只放行银行 ETF（512800）；未映射/未入选一律 False 由调用方决定
    keep = {"512800"}
    kept, st = filter_by_sector(
        trades, lambda d, s: s in keep)
    assert [t["r_net"] for t in kept] == [1.0]
    assert st == {"input": 3, "dropped_sector": 2,
                  "dropped_by_symbol": {"512690": 2}, "kept": 1}


def test_filter_by_sector_empty_pass_keeps_all():
    trades = [_t("X", "2024-01-02", "2024-01-03", "2024-02-01")]
    kept, st = filter_by_sector(trades, lambda d, s: True)
    assert len(kept) == 1 and st["dropped_sector"] == 0
