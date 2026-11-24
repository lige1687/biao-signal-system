"""Strategy Lab v2 全链路单测：覆盖 P0(PIT解耦/指标因果/锁箱/真实资金账本/A股限制) + P1(L1体检/两级去重/前向对账) + P2(AST算子/自动验漏/多腿与失血诊断)。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.strategy_lab.data_portal import DataPortal
from lei_signal.strategy_lab.diagnostics import check_factor_redundancy, evaluate_factor_panel_l1
from lei_signal.strategy_lab.factor_engine import (
    evaluate_factor_expression,
    expression_fingerprint,
    verify_expression_no_lookahead,
)
from lei_signal.strategy_lab.forward_tracker import ForwardTracker
from lei_signal.strategy_lab.indicator_audit import _causal_percentile_rank, _independent_regime_events
from lei_signal.strategy_lab.multi_leg import diagnose_strategy_bleeding
from lei_signal.strategy_lab.portfolio_sim import PortfolioSimConfig, simulate_real_portfolio
from lei_signal.strategy_lab.validation import (
    HoldoutVault,
    build_purged_walk_forward_folds,
    classify_market_regimes,
    overfitting_risk_audit,
)


def _make_panel(n_days: int = 260, n_assets: int = 8, seed: int = 11) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_days)
    syms = [f"600{100 + i}.SS" for i in range(n_assets)]
    close_d, open_d, high_d, low_d, vol_d = {}, {}, {}, {}, {}
    for i, s in enumerate(syms):
        drift = 0.0002 + 0.00015 * (i - n_assets / 2)
        rets = drift + rng.normal(0.0, 0.015, n_days)
        cl = 10.0 * np.cumprod(1.0 + rets)
        op = cl * (1.0 + rng.normal(0.0, 0.003, n_days))
        hi = np.maximum(op, cl) * 1.01
        lo = np.minimum(op, cl) * 0.99
        vol = rng.uniform(5e5, 2e6, n_days)
        close_d[s], open_d[s], high_d[s], low_d[s], vol_d[s] = cl, op, hi, lo, vol
    panel = {
        "open": pd.DataFrame(open_d, index=dates),
        "high": pd.DataFrame(high_d, index=dates),
        "low": pd.DataFrame(low_d, index=dates),
        "close": pd.DataFrame(close_d, index=dates),
        "volume": pd.DataFrame(vol_d, index=dates),
    }
    panel["amount"] = panel["close"] * panel["volume"]
    return panel


def test_local_pit_fundamentals_offline_and_strict_split(tmp_path) -> None:
    """验证本地 PIT 财报面板脱离外盘独立工作，且 explore 模式严格隔离 2024+ 财报。"""
    q_dir = tmp_path / "strategy_lab_bars/hist_q_reports"
    c_dir = tmp_path / "strategy_lab_bars/hist_capital_discipline"
    q_dir.mkdir(parents=True)
    c_dir.mkdir(parents=True)

    pd.DataFrame([
        {
            "SECURITY_CODE": "600519", "SECURITY_NAME_ABBR": "贵州茅台",
            "REPORTDATE": "2023-06-30", "NOTICE_DATE": "2023-08-03",
            "BASIC_EPS": 28.0, "WEIGHTAVG_ROE": 16.5, "YSTZ": 20.0, "SJLTZ": 21.0,
            "MGJYXJJE": 24.0, "XSMLL": 91.0, "PUBLISHNAME": "白酒",
        },
        {
            "SECURITY_CODE": "600999", "SECURITY_NAME_ABBR": "高债样票",
            "REPORTDATE": "2023-06-30", "NOTICE_DATE": "2023-08-15",
            "BASIC_EPS": 0.5, "WEIGHTAVG_ROE": 6.0, "YSTZ": 5.0, "SJLTZ": 2.0,
            "MGJYXJJE": 0.2, "XSMLL": 20.0, "PUBLISHNAME": "光伏设备",
        },
    ]).to_parquet(q_dir / "rpt_2023-06-30.parquet")

    pd.DataFrame([
        {
            "SECURITY_CODE": "600519", "SECURITY_NAME_ABBR": "贵州茅台",
            "REPORTDATE": "2024-06-30", "NOTICE_DATE": "2024-08-09",
            "BASIC_EPS": 33.0, "WEIGHTAVG_ROE": 18.0, "YSTZ": 18.0, "SJLTZ": 16.0,
            "MGJYXJJE": 29.0, "XSMLL": 92.0, "PUBLISHNAME": "白酒",
        },
    ]).to_parquet(q_dir / "rpt_2024-06-30.parquet")

    pd.DataFrame([
        {"symbol": "600519.SS", "report_year": 2022, "notice_date": "2023-03-31", "asset_growth_yoy": 12.0, "debt_ratio": 21.0},
        {"symbol": "600999.SS", "report_year": 2022, "notice_date": "2023-04-20", "asset_growth_yoy": 55.0, "debt_ratio": 74.0},
    ]).to_parquet(c_dir / "balance_2022.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)
    q_exp = portal.load_stock_business_quality(split="explore")
    q_oos = portal.load_stock_business_quality(split="holdout")

    assert len(q_exp) == 2
    assert q_exp["decision_date"].max() <= pd.Timestamp("2023-12-31")
    assert len(q_oos) == 1
    assert q_oos["decision_date"].min() >= pd.Timestamp("2024-01-01")
    # 高债大扩张标记准确命中 600999.SS，不误伤低债 600519.SS
    by_sym = q_exp.set_index("symbol")
    assert bool(by_sym.loc["600999.SS", "reckless_debt"]) is True
    assert bool(by_sym.loc["600519.SS", "reckless_debt"]) is False


def test_indicator_audit_prefix_invariant_and_horizon_dedup() -> None:
    """验证修复后的滚动分位严格前缀不变（不依赖总长度n）且独立事件按评估视窗零重叠。"""
    rng = np.random.default_rng(1)
    idx_short = pd.bdate_range("2018-01-02", periods=600)
    idx_long = pd.bdate_range("2018-01-02", periods=1600)
    vals_long = pd.Series(rng.normal(0.0, 1.0, len(idx_long)), index=idx_long)
    vals_short = vals_long.iloc[:600]

    p_short = _causal_percentile_rank(vals_short)
    p_long_head = _causal_percentile_rank(vals_long).iloc[:600]
    pd.testing.assert_series_equal(p_short, p_long_head, check_exact=False, rtol=1e-12, atol=1e-12)

    # 连续 90 天处于底部极值区：按 120 日视窗只应算 1 次独立大底事件，绝不能切碎成 4~5 次
    mask = np.zeros(300, dtype=bool)
    mask[10:100] = True
    mask[250:280] = True
    ev_120 = _independent_regime_events(mask, horizon=120)
    assert len(ev_120) == 2
    assert ev_120[1] - ev_120[0] >= 120


def test_holdout_vault_one_shot_seal_and_downgrade(tmp_path) -> None:
    """验证闭卷考锁箱：首次消费放行 -> 二次默认拒绝 -> 显式允许复看时强制降级为已看探索。"""
    vault = HoldoutVault(tmp_path)
    g1 = vault.check_or_consume("backtest-funds", rule_fingerprint="aaa111")
    assert g1["allowed"] is True and g1["status"] == "virgin_holdout_consumed"

    g2 = vault.check_or_consume("backtest-funds", rule_fingerprint="bbb222", allow_repeek_as_explore=False)
    assert g2["allowed"] is False and g2["blocked"] is True and g2["status"] == "holdout_already_consumed"

    g3 = vault.check_or_consume("backtest-funds", rule_fingerprint="bbb222", allow_repeek_as_explore=True)
    assert g3["allowed"] is True and g3["status"] == "downgraded_to_explore_seen"
    assert g3["open_count"] == 2


def test_purged_walk_forward_and_causal_regimes() -> None:
    """验证 Purged Walk-Forward 存在严格净空隔离期，且市场体制划分严格零未来函数。"""
    dates = pd.bdate_range("2018-01-02", periods=1500)
    folds = build_purged_walk_forward_folds(dates, train_min_days=504, test_days=252, purge_days=20)
    assert len(folds) >= 3
    for f in folds:
        assert pd.Timestamp(f.train_end) < pd.Timestamp(f.purge_end) < pd.Timestamp(f.test_start)
        assert pd.Timestamp(f.test_start) <= pd.Timestamp(f.test_end)

    rng = np.random.default_rng(9)
    px = pd.Series(100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.012, 500)), index=dates[:500])
    reg_a = classify_market_regimes(px).iloc[:350]
    px_tampered = px.copy()
    px_tampered.iloc[350:] *= 0.3
    reg_b = classify_market_regimes(px_tampered).iloc[:350]
    pd.testing.assert_series_equal(reg_a, reg_b)

    aud = overfitting_risk_audit(px.pct_change().dropna(), n_trials=20)
    assert "risk_light" in aud and 0.0 <= float(aud["deflated_sharpe_prob"]) <= 1.0


def test_real_portfolio_sim_limits_caps_and_harbor() -> None:
    """验证真实资金账本：行业上限、一字涨停买不进、一字跌停顺延卖出、闲钱黄金红利过渡与失血诊断。"""
    dates = pd.bdate_range("2022-01-03", periods=140)
    # 3只股票（前2只同行业，第3只异行业），第 20 天把第 1 只做成一字涨停(+10.5%)测试买单拦截
    px_a = np.linspace(10.0, 12.0, 140)
    px_b = np.linspace(10.0, 11.5, 140)
    px_c = np.linspace(10.0, 11.8, 140)
    open_a = px_a.copy()
    open_a[20] = px_a[19] * 1.105  # 一字涨停

    panel = {
        "open": pd.DataFrame({"600001.SS": open_a, "600002.SS": px_b, "600003.SS": px_c}, index=dates),
        "high": pd.DataFrame({"600001.SS": px_a * 1.01, "600002.SS": px_b * 1.01, "600003.SS": px_c * 1.01}, index=dates),
        "low": pd.DataFrame({"600001.SS": px_a * 0.99, "600002.SS": px_b * 0.99, "600003.SS": px_c * 0.99}, index=dates),
        "close": pd.DataFrame({"600001.SS": px_a, "600002.SS": px_b, "600003.SS": px_c}, index=dates),
        "volume": pd.DataFrame({"600001.SS": 1e6, "600002.SS": 1e6, "600003.SS": 1e6}, index=dates),
    }
    # 仅在第 19 天收盘发买单，第 60 天收盘全卖
    scores = pd.DataFrame(np.nan, index=dates, columns=["600001.SS", "600002.SS", "600003.SS"])
    scores.iloc[19] = [0.95, 0.90, 0.85]
    exits = pd.DataFrame(False, index=dates, columns=["600001.SS", "600002.SS", "600003.SS"])
    exits.iloc[60] = True

    # 构造一条稳步上涨的黄金避风港曲线（恒高于60日线）
    gold_px = np.linspace(4.0, 5.2, 140)
    harbor = {
        "gold": pd.DataFrame({"open": gold_px, "close": gold_px}, index=dates),
    }
    bench = pd.Series(np.linspace(4000.0, 4050.0, 140), index=dates)

    res_cash = simulate_real_portfolio(
        strategy_name="现金空仓",
        plain_rule_desc="测试现金空仓",
        panel=panel,
        entry_scores=scores,
        exit_flags=exits,
        industry_map={"600001.SS": "半导体", "600002.SS": "半导体", "600003.SS": "医药"},
        bench_close=bench,
        config=PortfolioSimConfig(max_positions=2, max_per_industry=1, idle_cash_mode="cash"),
    )
    res_harbor = simulate_real_portfolio(
        strategy_name="黄金避风港",
        plain_rule_desc="测试黄金过渡",
        panel=panel,
        entry_scores=scores,
        exit_flags=exits,
        industry_map={"600001.SS": "半导体", "600002.SS": "半导体", "600003.SS": "医药"},
        bench_close=bench,
        harbor_bars=harbor,
        config=PortfolioSimConfig(max_positions=2, max_per_industry=1, idle_cash_mode="gold_dividend_harbor"),
    )

    assert res_cash.metrics["blocked_buy_limit_up"] >= 1
    assert res_harbor.metrics["total_return"] > res_cash.metrics["total_return"]
    assert res_harbor.metrics["avg_harbor_exposure"] > 0.1
    diag = diagnose_strategy_bleeding(res_cash, bench)
    assert diag["available"] is True and len(diag["next_mining_hypotheses"]) >= 1


def test_factor_engine_ast_security_no_lookahead_and_l1_redundancy() -> None:
    """验证声明式算子库安全门禁、无未来函数自动验漏与两级正交查重。"""
    panel = _make_panel(n_days=220, n_assets=10)

    # 1) 拒绝任意代码调用与负滞后未来函数
    with pytest.raises(ValueError):
        evaluate_factor_expression("__import__('os').system('echo hi')", panel)
    with pytest.raises(ValueError):
        evaluate_factor_expression("ts_delay(close, -5)", panel)

    # 2) 合法表达式通过自动前缀不变性验漏且指纹稳定
    expr = "cs_rank(price_efficiency(close, 20) * risk_adj_mom(close, 40))"
    assert expression_fingerprint(expr) == expression_fingerprint("cs_rank(  price_efficiency(close,20)*risk_adj_mom(close,40) )")
    leak = verify_expression_no_lookahead(expr, panel)
    assert leak["passed"] is True

    # 3) 两级查重必须识别出完全重复的因子，并给独立因子放行
    f1 = evaluate_factor_expression(expr, panel)
    f_dup = evaluate_factor_expression("2.0 * cs_rank(price_efficiency(close, 20) * risk_adj_mom(close, 40)) + 1.0", panel)
    f_orth = evaluate_factor_expression("cs_rank(vol_asym(close, volume, 20))", panel)

    fwd20 = panel["close"].shift(-20) / panel["open"].shift(-1) - 1.0
    red_dup = check_factor_redundancy(f_dup, {"base_eff": f1}, fwd_ret=fwd20, min_assets=5)
    red_orth = check_factor_redundancy(f_orth, {"base_eff": f1}, fwd_ret=fwd20, min_assets=5)
    assert red_dup["max_abs_rank_corr"] > 0.99
    assert "高度重复" in str(red_dup["status"])
    assert red_orth["max_abs_rank_corr"] < 0.60

    l1 = evaluate_factor_panel_l1(f1, panel["close"], open_panel=panel["open"], horizons=(5, 20), n_groups=5, min_assets=5)
    assert "5d" in l1["horizons"] and "20d" in l1["horizons"]


def test_forward_tracker_freeze_reconcile_and_drift(tmp_path) -> None:
    """验证前向跟踪器：同日幂等冻结、5日/20日成熟结算而60日未到期保持None、纸面袖套账目恒等式通过。"""
    live_dir = tmp_path / "strategy_lab_bars"
    live_dir.mkdir(parents=True)
    dates = pd.bdate_range("2025-01-02", periods=95)
    bench_px = np.linspace(4.0, 4.15, 95)
    stock_px = np.concatenate([np.linspace(10.0, 11.0, 65), np.linspace(11.1, 13.0, 30)])

    for sym, px in (("510300.SS", bench_px), ("512480.SS", stock_px), ("600519.SS", stock_px)):
        pd.DataFrame(
            {"open": px * 0.998, "high": px * 1.01, "low": px * 0.99, "close": px, "volume": np.full(95, 1e6)},
            index=dates,
        ).to_parquet(live_dir / f"{sym}.bars.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)
    tracker = ForwardTracker(portal)

    sig_date = str(dates[64].date())  # 后面恰好有 30 个交易日：5日/20日到期，60日未到期
    snap = {
        "fund_opportunities": {
            "right_side_sector_picks": [
                {"code": "512480", "name": "半导体基金", "as_of": sig_date, "close": float(stock_px[64]), "rank_score": 0.88}
            ]
        },
        "top_industry_leaders": [
            {"symbol": "600519.SS", "code": "600519", "name": "贵州茅台", "as_of": sig_date, "close": float(stock_px[64]), "rank_score": 0.91}
        ],
        "top_small_giants": [],
    }
    r1 = tracker.record_snapshot(snap)
    r2 = tracker.record_snapshot(snap)
    assert r1["recorded"] is True and r1["recommendations_frozen"] == 2
    assert r2["recorded"] is False and r2["reason"] == "already_frozen_for_date"

    recon = tracker.reconcile()
    assert recon["reconciled"] is True
    assert recon["recommendations_updated"] == 2

    rep = tracker.drift_report()
    sec_st = rep["sleeve_forward_stats"]["sector_etf"]
    assert sec_st["matured_5d"] == 1
    assert sec_st["matured_20d"] == 1
    assert sec_st["matured_60d"] == 0  # 未到期绝不填 0
    assert sec_st["mean_excess_20d"] > 0.0
    assert rep["open_positions_count"] == 2


def test_knowledge_base_and_lifecycle_gates(tmp_path) -> None:
    """验证反例知识库检索与五态生命周期程序门禁（严禁绕过 SHADOW 直通 LIVE 或低高原晋级）。"""
    from lei_signal.strategy_lab.knowledge_base import KnowledgeBase
    from lei_signal.strategy_lab.lifecycle import LifecycleRegistry

    kb = KnowledgeBase(path=tmp_path / "kb.json")
    kb.record_entry(
        "anti_patterns",
        {"id": "ap-test", "title": "测试滞后季报追高", "keywords": ["季报", "ΔROE"], "evidence": "t=-2.59"},
    )
    hits = kb.query("ΔROE 加速")
    assert len(hits["anti_patterns"]) == 1

    reg = LifecycleRegistry(path=tmp_path / "reg.json")
    reg.register_explore(
        item_id="strat.demo",
        name="演示策略",
        kind="sector_etf",
        financial_hypothesis="低拥挤+中期动量",
        simple_baseline="等权死拿",
    )
    # 高原通过率不足 60% 必须被拦截
    with pytest.raises(ValueError, match="高原"):
        reg.promote_to_candidate(
            "strat.demo",
            no_lookahead_passed=True,
            beats_simple_baseline=True,
            plateau_pass_rate=0.40,
            evidence_summary={},
            reason="测试拦截",
        )
    # 严禁从 EXPLORE/CANDIDATE 绕过 SHADOW 直通 LIVE
    reg.promote_to_candidate(
        "strat.demo",
        no_lookahead_passed=True,
        beats_simple_baseline=True,
        plateau_pass_rate=0.85,
        evidence_summary={"cagr": 0.08},
        reason="通过开发期检验",
    )
    with pytest.raises(ValueError, match="SHADOW"):
        reg.promote_to_live("strat.demo", matured_shadow_obs=20, drift_ok=True, reason="试图偷渡上线")

    reg.promote_to_shadow("strat.demo", code_fingerprint="abc123", reason="冻结进入前向观察")
    with pytest.raises(ValueError, match="最低到期样本"):
        reg.promote_to_live("strat.demo", matured_shadow_obs=5, drift_ok=True, reason="样本未满")
    live = reg.promote_to_live("strat.demo", matured_shadow_obs=20, drift_ok=True, reason="前向达标正式上线")
    assert live["state"] == "LIVE"
    deg = reg.mark_degraded("strat.demo", reason="前向负漂移")
    assert deg["state"] == "DEGRADED"


def test_bear_gate_strict_causality_and_partial_profit() -> None:
    """验证熊市动态闸门严格前缀不变（零未来函数），以及真实账户分批锁利与机会成本换仓正常执行。"""
    from lei_signal.strategy_lab.campaigns import build_bear_regime_cap_series

    dates = pd.bdate_range("2020-01-02", periods=300)
    rng = np.random.default_rng(3)
    bench = pd.Series(4000.0 * np.cumprod(1.0 + rng.normal(0.0, 0.012, 300)), index=dates)
    b50 = pd.Series(np.clip(50.0 + np.cumsum(rng.normal(0.0, 4.0, 300)), 5.0, 95.0), index=dates)

    for mode in ("breadth_smooth", "bear_regime_ice_exempt", "hs300_ma120_simple"):
        c_a = build_bear_regime_cap_series(bench, b50, mode=mode).iloc[:220]
        bench_t = bench.copy(); bench_t.iloc[220:] *= 0.4
        b50_t = b50.copy(); b50_t.iloc[220:] = 5.0
        c_b = build_bear_regime_cap_series(bench_t, b50_t, mode=mode).iloc[:220]
        pd.testing.assert_series_equal(c_a, c_b)

    # 分批锁利检验：股价稳步涨 30% 时应触发一次半仓锁利交易且仍持有余仓
    d2 = pd.bdate_range("2022-01-03", periods=80)
    px = np.linspace(10.0, 13.5, 80)
    panel = {
        "open": pd.DataFrame({"600001.SS": px}, index=d2),
        "high": pd.DataFrame({"600001.SS": px * 1.01}, index=d2),
        "low": pd.DataFrame({"600001.SS": px * 0.99}, index=d2),
        "close": pd.DataFrame({"600001.SS": px}, index=d2),
        "volume": pd.DataFrame({"600001.SS": 1e6}, index=d2),
    }
    scores = pd.DataFrame(np.nan, index=d2, columns=["600001.SS"])
    scores.iloc[5] = 1.0
    exits = pd.DataFrame(False, index=d2, columns=["600001.SS"])
    res = simulate_real_portfolio(
        strategy_name="分批测试", plain_rule_desc="分批锁利",
        panel=panel, entry_scores=scores, exit_flags=exits,
        config=PortfolioSimConfig(max_positions=1, max_single_weight=1.0, risk_budget_per_trade=None, partial_take_profit_pct=0.15, partial_sell_fraction=0.50),
    )
    assert len(res.trades) == 1
    assert "分批锁利" in res.trades[0].exit_reason
    assert res.trades[0].net_return >= 0.14

