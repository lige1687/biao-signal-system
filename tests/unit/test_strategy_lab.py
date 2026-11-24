"""单元测试：锁死 Strategy Lab 的核心防线（闭卷考样本外物理隔离 + 活筹码严格无未来函数 + 金融单调性）。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.strategy_lab.chip_trend import compute_live_chip_metrics
from lei_signal.strategy_lab.data_portal import DataPortal, EXPLORE_END, HOLDOUT_START


def _make_synthetic_bars(n: int = 160) -> pd.DataFrame:
    dates = pd.bdate_range("2022-01-03", periods=n)
    # 前100天在 10.0 附近窄幅蓄势换手，后60天放量拉升至 14.0
    close = np.concatenate([
        10.0 + 0.15 * np.sin(np.linspace(0, 8, 100)),
        np.linspace(10.1, 14.0, n - 100),
    ])
    open_ = close * 0.995
    high = close * 1.012
    low = close * 0.988
    vol = np.concatenate([np.full(100, 1_000_000.0), np.full(n - 100, 1_800_000.0)])
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=dates,
    )


def test_live_chip_strictly_no_lookahead() -> None:
    """未来价格翻10倍或暴跌90%，对当天及之前任何一天的活筹码峰和获利盘比例必须零影响。"""
    bars_a = _make_synthetic_bars(160)
    bars_b = bars_a.copy()
    cutoff = 120
    # 篡改第 120 天之后的未来行情（暴跌 80% + 巨量）
    bars_b.iloc[cutoff:, bars_b.columns.get_loc("close")] *= 0.2
    bars_b.iloc[cutoff:, bars_b.columns.get_loc("high")] *= 0.22
    bars_b.iloc[cutoff:, bars_b.columns.get_loc("low")] *= 0.18
    bars_b.iloc[cutoff:, bars_b.columns.get_loc("volume")] *= 20.0

    m_a = compute_live_chip_metrics(bars_a).iloc[:cutoff]
    m_b = compute_live_chip_metrics(bars_b).iloc[:cutoff]

    pd.testing.assert_frame_equal(m_a, m_b, check_exact=False, rtol=1e-12, atol=1e-12)


def test_live_chip_financial_meaning() -> None:
    """底部充分换手后向上突破：获利盘比例应高于85%，且现价位于主筹码峰之上；反之破位暴跌后获利盘趋近0。"""
    bars = _make_synthetic_bars(160)
    m = compute_live_chip_metrics(bars)
    last = m.iloc[-1]
    assert last["profit_ratio"] > 0.90
    assert last["close"] > last["poc_price"]
    assert last["overhead_near10"] < 0.10

    # 若随后连续大跌跌穿原成本区，获利盘应迅速跌向低位
    crash_dates = pd.bdate_range(bars.index[-1] + pd.Timedelta(days=1), periods=15)
    crash_px = np.linspace(13.5, 8.0, 15)
    crash_df = pd.DataFrame(
        {
            "open": crash_px * 1.01,
            "high": crash_px * 1.02,
            "low": crash_px * 0.98,
            "close": crash_px,
            "volume": np.full(15, 1_500_000.0),
        },
        index=crash_dates,
    )
    m2 = compute_live_chip_metrics(pd.concat([bars, crash_df]))
    assert m2["profit_ratio"].iloc[-1] < 0.05


def test_data_portal_holdout_guard(tmp_path) -> None:
    """默认 explore 模式必须物理屏蔽 2024-01-01 及之后的闭卷考数据。"""
    bp_cn = tmp_path / "backtest_pool"
    bp_cn.mkdir()
    dates = pd.date_range("2023-06-01", "2024-06-01", freq="B")
    df = pd.DataFrame(
        {"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 100.0},
        index=dates,
    )
    df.to_parquet(bp_cn / "510300.SS.bars.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)
    exp_df = portal.load_bars("510300.SS", split="explore")
    oos_df = portal.load_bars("510300.SS", split="holdout")

    assert exp_df.index.max() <= pd.Timestamp(EXPLORE_END)
    assert oos_df.index.min() >= pd.Timestamp(HOLDOUT_START)
    assert len(exp_df) + len(oos_df) == len(df)


def test_distinct_sector_funds_no_duplicate_codes() -> None:
    """10只压舱石宽基与18只行业代表基金必须严格去重，绝不同一代码或重复赛道霸榜。"""
    from lei_signal.strategy_lab.fund_evaluator import CORE_BROAD_FUNDS, DISTINCT_SECTOR_FUNDS

    broad_syms = [s for s, _, _ in CORE_BROAD_FUNDS]
    sector_syms = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
    assert len(broad_syms) == len(set(broad_syms)) == 10
    assert len(sector_syms) == len(set(sector_syms)) == 18
    assert set(broad_syms).isdisjoint(set(sector_syms))


def test_portfolio_health_light_rules() -> None:
    """验证持仓健康灯核心金融逻辑：沸腾禁买、破20日线减半锁利、深坑严禁地板割肉、假美股底仓识别。"""
    from lei_signal.strategy_lab.portfolio_doctor import classify_off_exchange_health_light

    # 1. 高于年线 65% 未破线 -> 沸腾禁买红灯
    light1, adv1 = classify_off_exchange_health_light(
        is_pure_passive_us_or_bond=False,
        is_fake_us_base_active=False,
        has_long_hold_c_share=False,
        dist_ma200=0.65,
        recent_15d_max_dist_ma200=0.68,
        drawdown_1y=-0.03,
        above_ma20=True,
        prev_above_ma20=True,
    )
    assert "禁买红灯" in light1
    assert "严禁追高" in adv1

    # 2. 前期高于年线 65% 沸腾后今日首次跌破20日均线 -> 减半锁利红灯
    light2, adv2 = classify_off_exchange_health_light(
        is_pure_passive_us_or_bond=False,
        is_fake_us_base_active=False,
        has_long_hold_c_share=False,
        dist_ma200=0.52,
        recent_15d_max_dist_ma200=0.65,
        drawdown_1y=-0.09,
        above_ma20=False,
        prev_above_ma20=True,
    )
    assert "减半锁利红灯" in light2
    assert "一半" in adv2

    # 3. 距高点深跌 45% 回到年线下方 -> 严禁地板割肉（绝不给出清仓止损指令）
    light3, adv3 = classify_off_exchange_health_light(
        is_pure_passive_us_or_bond=False,
        is_fake_us_base_active=False,
        has_long_hold_c_share=False,
        dist_ma200=-0.15,
        recent_15d_max_dist_ma200=-0.10,
        drawdown_1y=-0.45,
        above_ma20=False,
        prev_above_ma20=False,
    )
    assert "严禁割肉" in light3
    assert "不盲目止损" in adv3

    # 4. 挂名全球但实为低美股占比主动基且处于深坑 -> 提示底色错配但深坑勿割、等回暖换纯指数
    light4, adv4 = classify_off_exchange_health_light(
        is_pure_passive_us_or_bond=False,
        is_fake_us_base_active=True,
        has_long_hold_c_share=True,
        dist_ma200=-0.08,
        recent_15d_max_dist_ma200=-0.05,
        drawdown_1y=-0.38,
        above_ma20=False,
        prev_above_ma20=False,
    )
    assert "底色错配" in light4 and "深坑勿割" in light4
    assert "标普500或纳指100" in adv4


def test_diagnose_user_portfolio_merges_ac_readonly(tmp_path) -> None:
    """验证只读读取持仓库合并同名A/C份额且零写库污染。"""
    import json
    import sqlite3
    from lei_signal.strategy_lab.portfolio_doctor import diagnose_user_portfolio

    db_file = tmp_path / "lab.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE portfolio_groups (group_key TEXT, title TEXT)")
    conn.execute(
        "CREATE TABLE portfolio_holdings (holding_id TEXT, group_key TEXT, code TEXT, name TEXT, market_value REAL, return_pct REAL)"
    )
    conn.execute("INSERT INTO portfolio_groups VALUES ('us_tech_active', '海外全球科技主动')")
    conn.execute("INSERT INTO portfolio_holdings VALUES ('1', 'us_tech_active', '100055', '富国全球科技互联网股票(QDII)A', 7000.0, -30.0)")
    conn.execute("INSERT INTO portfolio_holdings VALUES ('2', 'us_tech_active', '022184', '富国全球科技互联网股票(QDII)C', 13000.0, -30.0)")
    conn.commit()
    conn.close()

    off_dir = tmp_path / "strategy_lab_bars/off_exchange_funds"
    hold_dir = tmp_path / "strategy_lab_bars/off_exchange_holdings"
    off_dir.mkdir(parents=True)
    hold_dir.mkdir(parents=True)
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2025-01-02", periods=260)]
    navs = list(np.linspace(1.0, 2.0, 180)) + list(np.linspace(1.95, 1.15, 80))
    (off_dir / "100055.json").write_text(
        json.dumps({"code": "100055", "name": "富国全球科技", "dates": dates, "unit_nav": navs, "adj_nav": navs}),
        encoding="utf-8",
    )
    (hold_dir / "100055.json").write_text(
        json.dumps({"quarter": "2026Q3", "report_date": "2026-09-30", "market_weights": {"us": 33.9, "cn": 22.9, "hk": 9.3}, "top_names": ["ASMPT(9.3%)"]}),
        encoding="utf-8",
    )

    res = diagnose_user_portfolio(tmp_path)
    assert res["logical_positions_count"] == 1
    assert abs(res["total_market_value"] - 20000.0) < 1e-6
    item = res["items"][0]
    assert "底色错配" in item["health_light"]
    assert "C类份额" in item["penetration_truth_cn"]


def test_universal_symbol_prompt_two_stage_and_landmine(tmp_path) -> None:
    """验证通用单票提示卡：自动识别财务雷区，并根据用户买进价动态切换第一步保命线与第二步拿住大涨线。"""
    from lei_signal.strategy_lab.universal_prompts import evaluate_symbol_smart_prompt

    live_dir = tmp_path / "strategy_lab_bars"
    live_dir.mkdir(parents=True)
    bars = _make_synthetic_bars(160)
    # 模拟底部140天放量充分换手在 10.0 建仓，近20天缩量拉升至 13.2（底下大部队没卖，主成本仍锁在 10.0 附近）
    dates = pd.bdate_range("2022-01-03", periods=160)
    cl_locked = np.concatenate([10.0 + 0.1 * np.sin(np.linspace(0, 10, 140)), np.linspace(10.1, 13.2, 20)])
    bars_locked = pd.DataFrame(
        {
            "open": cl_locked * 0.996,
            "high": cl_locked * 1.008,
            "low": cl_locked * 0.992,
            "close": cl_locked,
            "volume": np.concatenate([np.full(140, 2_000_000.0), np.full(20, 400_000.0)]),
        },
        index=dates,
    )
    bars_locked.to_parquet(live_dir / "600519.SS.bars.parquet")
    bars.to_parquet(live_dir / "600999.SS.bars.parquet")

    fund_df = pd.DataFrame([
        {
            "symbol": "600519.SS", "name": "测试好龙头", "industry": "白酒",
            "mktcap_yi": 500.0, "pe": 20.0, "roe": 22.0, "profit_yoy": 18.0,
            "rev_yoy": 12.0, "ocf_ps": 3.50, "gross_margin": 70.0,
            "ind_mktcap_rank": 1.0, "ind_roe_pct": 0.95,
            "report_date": "2026-09-30", "notice_date": "2026-10-28", "tier": "leader",
        },
        {
            "symbol": "600999.SS", "name": "测试现金流雷股", "industry": "软件开发",
            "mktcap_yi": 90.0, "pe": 55.0, "roe": 3.0, "profit_yoy": -15.0,
            "rev_yoy": -5.0, "ocf_ps": -0.85, "gross_margin": 25.0,
            "ind_mktcap_rank": 20.0, "ind_roe_pct": 0.20,
            "report_date": "2026-09-30", "notice_date": "2026-10-28", "tier": "other",
        },
    ])
    fund_df.to_parquet(live_dir / "fundamentals_latest.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)

    # 1) 刚买进在 13.5（现价 14.0，仅赚 +3.7%，未满 15%）-> 第一步严守保命线
    p_stage1 = evaluate_symbol_smart_prompt(portal, "600519.SS", entry_price=13.5)
    assert p_stage1["available"] is True
    assert "行业真龙头" in str(p_stage1["quality_badge"])
    assert "第一步" in str(p_stage1["hold_stage"])

    # 2) 低位 10.5 买进（现价 14.0，已赚 +33.3% > 15%，且底仓主成本仍在 ~10.0 未上移）-> 第二步放心拿住大涨
    p_stage2 = evaluate_symbol_smart_prompt(portal, "600519.SS", entry_price=10.5)
    assert "第二步" in str(p_stage2["hold_stage"])
    assert "小洗盘别卖早" in str(p_stage2["hold_advice"])

    # 3) 经营现金流为负的公司 -> 自动触发财务排雷红灯
    p_mine = evaluate_symbol_smart_prompt(portal, "600999.SS")
    assert "财务排雷预警" in str(p_mine["quality_badge"])
    assert "财务雷区" in str(p_mine["buy_light"])


def test_smart_prompts_api_routes(tmp_path) -> None:
    """验证 FastAPI 通用智能提示路由端到端可用。"""
    import sqlite3
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from lei_signal.api.routes import smart_prompts

    live_dir = tmp_path / "strategy_lab_bars"
    live_dir.mkdir(parents=True)
    _make_synthetic_bars(160).to_parquet(live_dir / "600519.SS.bars.parquet")

    db_file = tmp_path / "lab.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE portfolio_groups (group_key TEXT, name TEXT)")
    conn.execute(
        "CREATE TABLE portfolio_holdings (holding_id TEXT, group_key TEXT, code TEXT, name TEXT, market_value REAL, return_pct REAL)"
    )
    conn.execute("INSERT INTO portfolio_groups VALUES ('us_index', '海外美股宽基')")
    conn.execute("INSERT INTO portfolio_holdings VALUES ('1', 'us_index', '017641', '摩根标普500指数A', 2000.0, 4.5)")
    conn.commit()
    conn.close()

    test_app = FastAPI()
    test_app.state.portfolio_db_path = str(db_file)
    test_app.include_router(smart_prompts.router)
    client = TestClient(test_app)

    r_sym = client.get("/api/smart-prompts/symbol/600519.SS?entry_price=10.5")
    assert r_sym.status_code == 200
    assert r_sym.json()["available"] is True
    assert "第二步" in r_sym.json()["hold_stage"]

    r_port = client.get("/api/smart-prompts/portfolio?force=true")
    assert r_port.status_code == 200
    assert r_port.json()["portfolio_diagnosis"]["logical_positions_count"] == 1


def test_round3_reckless_debt_expansion_and_risk_budget_sizing(tmp_path) -> None:
    """验证高债盲目扩张精准排雷（不误伤低债高成长）与按风险定单笔仓位的单调性。"""
    from lei_signal.strategy_lab.universal_prompts import evaluate_symbol_smart_prompt

    live_dir = tmp_path / "strategy_lab_bars"
    bal_dir = live_dir / "hist_capital_discipline"
    bal_dir.mkdir(parents=True)

    dates = pd.bdate_range("2024-01-02", periods=160)
    # 1) 稳健低波动股票（日均波动小，离保命线近）
    rng = np.random.default_rng(7)
    calm_ret = 0.0008 + rng.normal(0.0, 0.008, 160)
    calm_cl = 10.0 * np.cumprod(1.0 + calm_ret)
    calm_bars = pd.DataFrame(
        {
            "open": calm_cl * 0.998,
            "high": calm_cl * 1.007,
            "low": calm_cl * 0.993,
            "close": calm_cl,
            "volume": np.full(160, 1_500_000.0),
        },
        index=dates,
    )
    # 2) 上蹿下跳高波动股票（日均波动大，离保命线远）
    wild_ret = 0.0008 + rng.normal(0.0, 0.036, 160)
    wild_cl = 10.0 * np.cumprod(1.0 + wild_ret)
    wild_bars = pd.DataFrame(
        {
            "open": wild_cl * 0.99,
            "high": wild_cl * 1.038,
            "low": wild_cl * 0.962,
            "close": wild_cl,
            "volume": np.full(160, 1_500_000.0),
        },
        index=dates,
    )

    calm_bars.to_parquet(live_dir / "600101.SS.bars.parquet")
    wild_bars.to_parquet(live_dir / "600102.SS.bars.parquet")
    calm_bars.to_parquet(live_dir / "600103.SS.bars.parquet")

    fund_df = pd.DataFrame([
        {
            "symbol": "600101.SS", "name": "稳健低债高成长", "industry": "消费电子",
            "mktcap_yi": 420.0, "pe": 22.0, "roe": 18.0, "profit_yoy": 24.0,
            "rev_yoy": 20.0, "ocf_ps": 1.80, "gross_margin": 35.0,
            "ind_mktcap_rank": 1.0, "ind_roe_pct": 0.90,
            "report_date": "2026-09-30", "notice_date": "2026-10-28", "tier": "leader",
        },
        {
            "symbol": "600102.SS", "name": "高波动科技龙头", "industry": "半导体",
            "mktcap_yi": 380.0, "pe": 35.0, "roe": 15.0, "profit_yoy": 20.0,
            "rev_yoy": 18.0, "ocf_ps": 1.10, "gross_margin": 42.0,
            "ind_mktcap_rank": 2.0, "ind_roe_pct": 0.85,
            "report_date": "2026-09-30", "notice_date": "2026-10-28", "tier": "leader",
        },
        {
            "symbol": "600103.SS", "name": "借债瞎扩张样本", "industry": "光伏设备",
            "mktcap_yi": 350.0, "pe": 25.0, "roe": 12.0, "profit_yoy": 10.0,
            "rev_yoy": 15.0, "ocf_ps": 0.60, "gross_margin": 25.0,
            "ind_mktcap_rank": 2.0, "ind_roe_pct": 0.75,
            "report_date": "2026-09-30", "notice_date": "2026-10-28", "tier": "leader",
        },
    ])
    fund_df.to_parquet(live_dir / "fundamentals_latest.parquet")

    bal_df = pd.DataFrame([
        # 自有资金健康扩张（负债率仅 35%）-> 绝不误杀
        {"symbol": "600101.SS", "asset_growth_yoy": 48.0, "debt_ratio": 35.0},
        {"symbol": "600102.SS", "asset_growth_yoy": 18.0, "debt_ratio": 42.0},
        # 高债大扩张（资产暴增 52% 且负债率 72%）-> 触发精准排雷红灯
        {"symbol": "600103.SS", "asset_growth_yoy": 52.0, "debt_ratio": 72.0},
    ])
    bal_df.to_parquet(bal_dir / "balance_2025.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)

    p_calm = evaluate_symbol_smart_prompt(portal, "600101.SS")
    p_wild = evaluate_symbol_smart_prompt(portal, "600102.SS")
    p_debt = evaluate_symbol_smart_prompt(portal, "600103.SS")

    assert "行业真龙头" in str(p_calm["quality_badge"])
    assert "高债大扩张预警" in str(p_debt["quality_badge"])
    assert float(p_debt["suggested_max_position_pct"]) == 0.0
    assert float(p_calm["suggested_max_position_pct"]) > float(p_wild["suggested_max_position_pct"])
    assert 5.0 <= float(p_wild["suggested_max_position_pct"]) < float(p_calm["suggested_max_position_pct"]) <= 15.0


def test_round3_idle_cash_harbor_states(tmp_path) -> None:
    """验证空仓闲钱去向灯：黄金与高分红分别按近三月均价（60日均线）独立切换。"""
    from lei_signal.strategy_lab.universal_prompts import evaluate_idle_cash_harbor

    live_dir = tmp_path / "strategy_lab_bars"
    live_dir.mkdir(parents=True)
    dates = pd.bdate_range("2025-01-02", periods=90)

    def _save(sym: str, px: np.ndarray) -> None:
        df = pd.DataFrame(
            {"open": px, "high": px * 1.005, "low": px * 0.995, "close": px, "volume": np.full(len(px), 1e6)},
            index=dates,
        )
        df.to_parquet(live_dir / f"{sym}.bars.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)

    # 1) 黄金下跌破60日线、高分红上涨站稳60日线 -> 仅高分红可放闲钱
    _save("518850.SS", np.linspace(8.5, 7.2, 90))
    _save("512890.SS", np.linspace(1.05, 1.25, 90))
    h1 = evaluate_idle_cash_harbor(portal)
    assert h1["gold"]["is_steady"] is False
    assert h1["high_dividend"]["is_steady"] is True
    assert "高分红基金稳在近三月均价上方" in str(h1["headline_cn"])
    assert "黄金先回避" in str(h1["headline_cn"])

    # 2) 两只均站稳60日线 -> 各放一半
    _save("518850.SS", np.linspace(7.2, 8.8, 90))
    h2 = evaluate_idle_cash_harbor(portal)
    assert h2["gold"]["is_steady"] is True
    assert h2["high_dividend"]["is_steady"] is True
    assert "50% 黄金基金 + 50% 高分红" in str(h2["allocation_cn"])

    # 3) 两只均跌破60日线 -> 全部回货币理财保本
    _save("518850.SS", np.linspace(8.8, 7.2, 90))
    _save("512890.SS", np.linspace(1.25, 1.02, 90))
    h3 = evaluate_idle_cash_harbor(portal)
    assert h3["gold"]["is_steady"] is False
    assert h3["high_dividend"]["is_steady"] is False
    assert "货币" in str(h3["allocation_cn"])


def test_round3_rank_top_candidates_industry_cap_and_debt_filter(tmp_path) -> None:
    """验证个股尖子生漏斗强制同行业最多2只（防单一赛道霸榜）且自动过滤高债大扩张雷区。"""
    from lei_signal.strategy_lab.chip_trend import rank_top_candidates

    live_dir = tmp_path / "strategy_lab_bars"
    bal_dir = live_dir / "hist_capital_discipline"
    bal_dir.mkdir(parents=True)

    bars_up = _make_synthetic_bars(160)
    # 沪深300 基准用平稳上涨序列
    dates = bars_up.index
    bench_px = np.linspace(3.8, 4.1, 160)
    pd.DataFrame(
        {"open": bench_px, "high": bench_px * 1.005, "low": bench_px * 0.995, "close": bench_px, "volume": np.full(160, 1e7)},
        index=dates,
    ).to_parquet(live_dir / "510300.SS.bars.parquet")

    rows = []
    # 4只同行业（半导体）+ 1只医药 + 1只高债大扩张（食品饮料）
    specs = [
        ("600201.SS", "半导甲", "半导体", 25.0),
        ("600202.SS", "半导乙", "半导体", 24.0),
        ("600203.SS", "半导丙", "半导体", 23.0),
        ("600204.SS", "半导丁", "半导体", 22.0),
        ("600205.SS", "医药甲", "医药生物", 18.0),
        ("600206.SS", "高债雷", "食品饮料", 28.0),
    ]
    for sym, nm, ind, roe in specs:
        bars_up.to_parquet(live_dir / f"{sym}.bars.parquet")
        rows.append({
            "symbol": sym, "name": nm, "industry": ind,
            "mktcap_yi": 400.0, "pe": 20.0, "roe": roe, "profit_yoy": 20.0,
            "rev_yoy": 15.0, "ocf_ps": 1.5, "gross_margin": 40.0,
            "ind_mktcap_rank": 1.0, "ind_roe_pct": 0.9,
            "report_date": "2026-09-30", "notice_date": "2026-10-28", "tier": "leader",
        })
    pd.DataFrame(rows).to_parquet(live_dir / "fundamentals_latest.parquet")
    pd.DataFrame([
        {"symbol": "600206.SS", "asset_growth_yoy": 60.0, "debt_ratio": 75.0},
    ]).to_parquet(bal_dir / "balance_2025.parquet")

    portal = DataPortal(repo_root=tmp_path, lab_home=tmp_path)
    picks = rank_top_candidates(portal, top_n=5, pool="leader", split="full", max_per_industry=2)
    picked_syms = [p["symbol"] for p in picks]
    semi_count = sum(1 for p in picks if p["industry"] == "半导体")

    assert "600206.SS" not in picked_syms
    assert semi_count == 2
    assert "600205.SS" in picked_syms
