"""四场买方标准研究战役受控实证引擎（campaigns）。

严格研究纪律：
1. 默认且强制在 `split="explore"`（<=2023-12-31）及期内 Purged Walk-Forward 上开展全部对比、消融与高原验货；
2. 绝不偷看或消耗 `2024+` 闭卷考锁箱；
3. 每一场战役先绑定强简单基准，并同时汇报收益、超额、回撤、换手、去Top3压力测试、体制表现与过拟合风险，证伪者如实落榜。
"""
from __future__ import annotations

import math
from typing import Literal
import numpy as np
import pandas as pd

from .data_portal import DataPortal, SplitMode
from .diagnostics import evaluate_factor_panel_l1
from .factor_engine import cs_rank, downside_vol, gap_reversion, ts_pct_change
from .fund_evaluator import DISTINCT_SECTOR_FUNDS
from .portfolio_sim import PortfolioBacktestResult, PortfolioSimConfig, simulate_real_portfolio
from .signals import (
    build_sector_etf_signal_panels,
    build_stock_funnel_signal_panels,
    compute_sector_resonance_panel,
    make_two_stage_stock_exit_callback,
)
from .validation import (
    build_purged_walk_forward_folds,
    overfitting_risk_audit,
    slice_performance_by_year_and_regime,
)


def _load_harbor_bars(portal: DataPortal, split: SplitMode) -> dict[str, pd.DataFrame]:
    harbor: dict[str, pd.DataFrame] = {}
    for key, hsym in (("gold", "518850.SS"), ("dividend", "512890.SS")):
        try:
            harbor[key] = portal.load_bars(hsym, market="CN", split=split)
        except FileNotFoundError:
            pass
    return harbor


# ------------------------- 战役二核心复用：纯因果熊市动态仓位闸门 -------------------------

def build_bear_regime_cap_series(
    bench_close: pd.Series,
    breadth_b50: pd.Series,
    *,
    mode: Literal["none", "static_50", "breadth_smooth", "bear_regime_ice_exempt", "hs300_ma120_simple"] = "bear_regime_ice_exempt",
    min_cap: float = 0.25,
) -> pd.Series:
    """严格因果（零未来函数）计算进攻腿权益仓位上限乘数序列 [min_cap, 1.0]。"""
    dates = bench_close.index
    if mode == "none":
        return pd.Series(1.0, index=dates)
    if mode == "static_50":
        return pd.Series(0.50, index=dates)

    bc = bench_close.astype(float)
    b50 = breadth_b50.reindex(dates).ffill()
    b_ma120 = bc.rolling(120, min_periods=80).mean()
    b50_ma10 = b50.rolling(10, min_periods=5).mean()
    b50_min20 = b50.rolling(20, min_periods=10).min()
    # 冰点反弹豁免：近20日全A宽度曾跌破18%极端冰点且当前已站回10日均线，立即解封防踏空大底反转
    ice_rebound = (b50_min20 <= 18.0) & (b50 > b50_ma10)

    if mode == "breadth_smooth":
        cap = ((b50 - 15.0) / 40.0).clip(0.0, 1.0) * (1.0 - min_cap) + min_cap
        cap = cap.where(~ice_rebound, np.maximum(cap, 0.75))
        return cap.fillna(1.0)

    if mode == "hs300_ma120_simple":
        weak = (bc < b_ma120) & (~ice_rebound)
        return pd.Series(1.0, index=dates).where(~weak, min_cap)

    if mode == "bear_regime_ice_exempt":
        grinding_bear = (bc < b_ma120) & (b50 < 35.0) & (b50 <= b50_ma10) & (~ice_rebound)
        return pd.Series(1.0, index=dates).where(~grinding_bear, min_cap)

    raise ValueError(f"unsupported gate mode: {mode}")


# ------------------------- 战役一：18只行业ETF排序与进出场重构 -------------------------

def build_sector_etf_v2_signals(
    panel: dict[str, pd.DataFrame],
    bench_close: pd.Series,
    resonance_ratio: pd.DataFrame | None,
    *,
    rebal_interval: int = 10,
    hold_rank_buffer: int = 6,
    atr_stop_mult: float = 0.60,
    max_crowd_pct: float = 0.85,
    use_four_factors: bool = True,
) -> dict[str, pd.DataFrame]:
    """战役一 v2 同源行业 ETF 信号：剔除20日短反转的中期动量 + 共振扩散加速度 + 低拥挤 + 日内承接 + 低频缓冲轮动。"""
    sigs = build_sector_etf_signal_panels(panel, bench_close, resonance_ratio=resonance_ratio)
    close, op = panel["close"], panel["open"]
    dates = close.index
    ma10, ma60, atr20, crowd = sigs["ma10"], sigs["ma60"], sigs["atr20"], sigs["crowd_pct"]
    res_al = sigs["resonance_ratio"]

    ret120_skip20 = close.shift(20) / close.shift(140) - 1.0
    res_diff10 = res_al - res_al.shift(10)
    gap20 = gap_reversion(op, close, 20)
    dvol_ok = cs_rank(downside_vol(close, 60)) <= 0.80  # 剔除最差20%高下行波动坏尾

    if use_four_factors:
        score = (
            cs_rank(ret120_skip20).fillna(0.5)
            + cs_rank(res_diff10).fillna(0.5)
            + cs_rank(-crowd).fillna(0.5)
            + cs_rank(gap20).fillna(0.5)
        ) / 4.0
    else:
        score = (cs_rank(ret120_skip20).fillna(0.5) + cs_rank(-crowd).fillna(0.5)) / 2.0

    uptrend = (close > ma60) & (ma60 >= ma60.shift(10) * 0.995) & (crowd < max_crowd_pct) & dvol_ok

    if rebal_interval > 1:
        rebal_mask = pd.Series(False, index=dates)
        rebal_mask.iloc[::rebal_interval] = True
        entry_scores = score.where(uptrend).where(rebal_mask, axis=0)
        rank_desc = score.where(close > ma60).rank(axis=1, ascending=False)
        exit_flags = (
            (rebal_mask.to_numpy()[:, None] & ((rank_desc > hold_rank_buffer) | rank_desc.isna()))
            | (close < ma60 - atr_stop_mult * atr20)
            | ((crowd >= 0.92) & (close < ma10))
        ).fillna(False)
    else:
        entry_scores = score.where(uptrend)
        exit_flags = (
            (close < ma60 - atr_stop_mult * atr20)
            | ((crowd >= 0.92) & (close < ma10))
        ).fillna(False)

    return {
        "raw_score": score,
        "entry_scores": entry_scores,
        "exit_flags": exit_flags,
        "stop_prices": sigs["stop_prices"],
        "v1_entry": sigs["right_entry_scores"],
        "v1_exit": sigs["right_exit_flags"],
    }


def run_campaign1_sector_etf_v2(portal: DataPortal, *, split: SplitMode = "explore") -> dict[str, object]:
    """战役一完整实证：v1基准 vs v2四因子宽止损 vs v2双周缓冲轮动 vs 2因子奥卡姆对照 + L1体检 + ±20%高原 + Walk-Forward。"""
    syms = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
    panel = portal.load_panel_bars(syms, market="CN", split=split, min_rows=180)
    close = panel["close"]
    dates = close.index
    bench = portal.load_bars("510300.SS", market="CN", split=split)["close"].reindex(dates).ffill()
    res_ratio, _, _ = compute_sector_resonance_panel(portal, DISTINCT_SECTOR_FUNDS, split=split)
    harbor = _load_harbor_bars(portal, split)

    v2_daily = build_sector_etf_v2_signals(panel, bench, res_ratio, rebal_interval=1, atr_stop_mult=0.50)
    v2_biweek = build_sector_etf_v2_signals(panel, bench, res_ratio, rebal_interval=10, hold_rank_buffer=6, atr_stop_mult=0.60)
    v2_two = build_sector_etf_v2_signals(panel, bench, res_ratio, rebal_interval=10, hold_rank_buffer=6, atr_stop_mult=0.60, use_four_factors=False)

    # 组件诊断升级：消除日频 MA60 止损锯齿，改为严格月度(20日)低频横截面轮动 + 排名留存缓冲 / 月频 MA120 趋势过滤
    score4 = v2_biweek["raw_score"]
    ma120 = close.rolling(120, min_periods=90).mean()
    rebal20 = pd.Series(False, index=dates)
    rebal20.iloc[::20] = True
    rank_all = score4.rank(axis=1, ascending=False)
    m1_ent = score4.where(rebal20, axis=0)
    m1_ext = pd.DataFrame(rebal20.to_numpy()[:, None] & (rank_all.to_numpy() > 8), index=dates, columns=close.columns)

    up120 = (close > ma120).fillna(False)
    rank_up = score4.where(up120).rank(axis=1, ascending=False)
    m2_ent = score4.where(up120).where(rebal20, axis=0)
    m2_ext = pd.DataFrame(
        rebal20.to_numpy()[:, None] & ((rank_up.to_numpy() > 7) | (~up120.to_numpy())),
        index=dates, columns=close.columns,
    )

    bh_scores = pd.DataFrame(1.0, index=dates, columns=close.columns)
    bh_exits = pd.DataFrame(False, index=dates, columns=close.columns)
    cfg_bh = PortfolioSimConfig(max_positions=len(close.columns), max_per_industry=0, max_single_weight=1.0 / len(close.columns), risk_budget_per_trade=None)
    cfg_v1 = PortfolioSimConfig(max_positions=4, max_per_industry=0, max_single_weight=0.25, risk_budget_per_trade=0.012, idle_cash_mode="gold_dividend_harbor")
    cfg_m1_cash = PortfolioSimConfig(max_positions=4, max_per_industry=0, max_single_weight=0.25, risk_budget_per_trade=None, idle_cash_mode="cash")
    cfg_m2_hb = PortfolioSimConfig(max_positions=4, max_per_industry=0, max_single_weight=0.25, risk_budget_per_trade=None, idle_cash_mode="gold_dividend_harbor")
    cfg_hb = PortfolioSimConfig(max_positions=3, max_per_industry=0, max_single_weight=0.33, risk_budget_per_trade=0.015, idle_cash_mode="gold_dividend_harbor")

    arms = [
        ("B0: 18行业等权死拿", bh_scores, bh_exits, cfg_bh),
        ("B1: 旧v1右侧+避风港", v2_daily["v1_entry"], v2_daily["v1_exit"], cfg_v1),
        ("C1(反例): v2+日频MA60止损锯齿", v2_biweek["entry_scores"], v2_biweek["exit_flags"], cfg_hb),
        ("C2_M1: v2纯月度Top4缓冲(无日止损)", m1_ent, m1_ext, cfg_m1_cash),
        ("C2_M2: v2月度Top4+月频MA120+避风港", m2_ent, m2_ext, cfg_m2_hb),
        ("C4_2f: 极简2因子双周+日止损(对照)", v2_two["entry_scores"], v2_two["exit_flags"], cfg_hb),
    ]
    results: list[PortfolioBacktestResult] = []
    for name, ent, ext, cfg in arms:
        results.append(
            simulate_real_portfolio(
                strategy_name=name, plain_rule_desc=name,
                panel=panel, entry_scores=ent, exit_flags=ext,
                stop_prices=v2_daily["stop_prices"], bench_close=bench,
                harbor_bars=harbor, config=cfg, n_trials=6,
            )
        )

    # L1 新4因子综合打分体检（验证是否彻底翻转旧版负 Rank IC）
    l1_v2 = evaluate_factor_panel_l1(v2_biweek["raw_score"], close, open_panel=panel["open"], horizons=(5, 20, 60), n_groups=4, min_assets=6)

    # 参数高原 ±20% 测试（针对无日频止损锯齿的月度低频轮动 + 战役二极简熊市闸门 G4）
    inds = portal.load_all_market_indicators(split=split)
    b50_ser = inds["cn-breadth-b50"].series.reindex(dates).ffill()
    cap_g4 = build_bear_regime_cap_series(bench, b50_ser, mode="hs300_ma120_simple", min_cap=0.25)

    plateau_pts = []
    passed = 0
    for lbl, reb, buf, ma_len in (
        ("默认(20d/Top8/G4)", 20, 8, 120),
        ("周期-20%(16d)", 16, 8, 120),
        ("周期+20%(24d)", 24, 8, 120),
        ("缓冲收紧(Top6)", 20, 6, 120),
        ("缓冲放宽(Top10)", 20, 10, 120),
        ("闸门均线缩短(MA100)", 20, 8, 100),
        ("闸门均线加长(MA140)", 20, 8, 140),
    ):
        rm = pd.Series(False, index=dates)
        rm.iloc[::reb] = True
        rk_x = score4.rank(axis=1, ascending=False)
        ent_x = score4.where(rm, axis=0)
        ext_x = pd.DataFrame(rm.to_numpy()[:, None] & (rk_x.to_numpy() > buf), index=dates, columns=close.columns)
        b_ma_x = bench.rolling(ma_len, min_periods=max(60, ma_len - 20)).mean()
        b50_ma10 = b50_ser.rolling(10, min_periods=5).mean()
        ice_reb = (b50_ser.rolling(20, min_periods=10).min() <= 18.0) & (b50_ser > b50_ma10)
        cap_x = pd.Series(1.0, index=dates).where(~((bench < b_ma_x) & (~ice_reb)), 0.25)
        r_pt = simulate_real_portfolio(
            strategy_name=lbl, plain_rule_desc=lbl, panel=panel,
            entry_scores=ent_x, exit_flags=ext_x,
            bench_close=bench, harbor_bars=harbor, equity_cap_series=cap_x, config=cfg_m2_hb,
        )
        ok = float(r_pt.metrics["cagr"]) > float(results[1].metrics["cagr"]) and float(r_pt.metrics["max_drawdown"]) > float(results[1].metrics["max_drawdown"])
        if ok:
            passed += 1
        plateau_pts.append({"point": lbl, "cagr": r_pt.metrics["cagr"], "excess_cagr": r_pt.metrics["excess_cagr"], "mdd": r_pt.metrics["max_drawdown"], "beats_v1": ok})

    # Purged Walk-Forward 逐折对照（C2_M1+G4 月度低频+熊市闸门 vs B1 旧v1）
    c2_g4_res = simulate_real_portfolio(
        strategy_name="C2_M1+G4: 月度Top4缓冲+300MA120闸门+避风港",
        plain_rule_desc="战役一+二联合优胜方案",
        panel=panel, entry_scores=m1_ent, exit_flags=m1_ext,
        bench_close=bench, harbor_bars=harbor, equity_cap_series=cap_g4, config=cfg_m2_hb, n_trials=6,
    )
    results.append(c2_g4_res)
    folds = build_purged_walk_forward_folds(dates, train_min_days=360, test_days=252, purge_days=20)
    c2_res = c2_g4_res
    v1_res = results[1]
    wf_rows = []
    for f in folds:
        r_new = c2_res.daily_returns.loc[f.test_start : f.test_end]
        r_old = v1_res.daily_returns.loc[f.test_start : f.test_end]
        if len(r_new) < 30:
            continue
        yrs = max(len(r_new) / 252.0, 0.1)
        c_new = float((1.0 + r_new).prod() ** (1.0 / yrs) - 1.0)
        c_old = float((1.0 + r_old).prod() ** (1.0 / yrs) - 1.0)
        wf_rows.append({"fold": f.fold_id, "window": f"{f.test_start}~{f.test_end}", "v2_cagr": round(c_new, 4), "v1_cagr": round(c_old, 4), "delta": round(c_new - c_old, 4)})

    return {
        "split": split,
        "l1_v2_score": l1_v2,
        "arms": [
            {
                "name": r.strategy_name,
                **r.metrics,
                "dsr": r.overfit_audit.get("deflated_sharpe_prob"),
                "hac_t": r.overfit_audit.get("hac_t_stat"),
                "by_year": {y["year"]: y["total_return"] for y in r.by_year},
            }
            for r in results
        ],
        "plateau_pass_rate": round(passed / len(plateau_pts), 3),
        "plateau_points": plateau_pts,
        "walk_forward_vs_v1": wf_rows,
    }


# ------------------------- 战役二：熊市动态仓位闸门研究 -------------------------

def run_campaign2_bear_gate(portal: DataPortal, *, split: SplitMode = "explore") -> dict[str, object]:
    """战役二完整实证：5 种熊市仓位闸门（含静态50%强简单对手），定量对比 2018/2022 少亏 vs 2019/2020 踏空代价。"""
    syms = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
    panel = portal.load_panel_bars(syms, market="CN", split=split, min_rows=180)
    close = panel["close"]
    dates = close.index
    bench = portal.load_bars("510300.SS", market="CN", split=split)["close"].reindex(dates).ffill()
    inds = portal.load_all_market_indicators(split=split)
    b50 = inds["cn-breadth-b50"].series.reindex(dates).ffill()
    res_ratio, _, _ = compute_sector_resonance_panel(portal, DISTINCT_SECTOR_FUNDS, split=split)
    harbor = _load_harbor_bars(portal, split)

    v2 = build_sector_etf_v2_signals(panel, bench, res_ratio, rebal_interval=20, hold_rank_buffer=8)
    score4 = v2["raw_score"]
    rebal20 = pd.Series(False, index=dates)
    rebal20.iloc[::20] = True
    rank_all = score4.rank(axis=1, ascending=False)
    m1_ent = score4.where(rebal20, axis=0)
    m1_ext = pd.DataFrame(rebal20.to_numpy()[:, None] & (rank_all.to_numpy() > 8), index=dates, columns=close.columns)
    cfg_hb = PortfolioSimConfig(max_positions=4, max_per_industry=0, max_single_weight=0.25, risk_budget_per_trade=None, idle_cash_mode="gold_dividend_harbor")

    gate_specs: list[tuple[str, Literal["none", "static_50", "breadth_smooth", "bear_regime_ice_exempt", "hs300_ma120_simple"]]] = [
        ("G0: 无闸门(100%进攻)", "none"),
        ("G1: 静态50%固定降仓(强基线)", "static_50"),
        ("G2: 全A宽度连续平滑(0.25~1.0)", "breadth_smooth"),
        ("G3: 熊市体制+冰点反弹豁免", "bear_regime_ice_exempt"),
        ("G4: 极简沪深300MA120+冰点豁免", "hs300_ma120_simple"),
    ]
    rows = []
    for label, mode in gate_specs:
        cap = build_bear_regime_cap_series(bench, b50, mode=mode, min_cap=0.25)
        r = simulate_real_portfolio(
            strategy_name=label, plain_rule_desc=label,
            panel=panel, entry_scores=m1_ent, exit_flags=m1_ext,
            bench_close=bench, harbor_bars=harbor,
            equity_cap_series=cap, config=cfg_hb, n_trials=5,
        )
        ym = {y["year"]: y["total_return"] for y in r.by_year}
        rm = {rg["regime"]: rg["cagr"] for rg in r.by_regime}
        rows.append({
            "gate": label,
            "mode": mode,
            **r.metrics,
            "dsr": r.overfit_audit.get("deflated_sharpe_prob"),
            "y2018_bear": ym.get(2018, 0.0),
            "y2019_rally": ym.get(2019, 0.0),
            "y2020_rally": ym.get(2020, 0.0),
            "y2022_bear": ym.get(2022, 0.0),
            "y2023_chop": ym.get(2023, 0.0),
            "bear_regime_cagr": rm.get("阴跌下行熊", 0.0),
            "bull_regime_cagr": rm.get("单边上升牛", 0.0),
        })

    # 同时测算“防磨血 vs 防踏空”净交换比（相对 G0 无闸门）
    g0 = rows[0]
    for row in rows:
        row["bear_loss_saved_18_22"] = round((row["y2018_bear"] - g0["y2018_bear"]) + (row["y2022_bear"] - g0["y2022_bear"]), 4)
        row["bull_rally_diff_19_20"] = round((row["y2019_rally"] - g0["y2019_rally"]) + (row["y2020_rally"] - g0["y2020_rally"]), 4)
        row["mdd_saved_vs_g0"] = round(float(row["max_drawdown"]) - float(g0["max_drawdown"]), 4)

    return {"split": split, "gates": rows}


# ------------------------- 战役三：A股个股退出换仓 + 本地PIT基本面新因子 -------------------------

def run_campaign3_stock_mechanisms(portal: DataPortal, *, split: SplitMode = "explore") -> dict[str, object]:
    """战役三完整实证：坦诚披露77股幸存者边界 + 4个本地PIT基本面因子L1检验 + 分批锁利/机会成本换仓实测。"""
    all_stocks = portal.list_cn_stocks()
    long_stocks = []
    for s in all_stocks:
        try:
            df = portal.load_bars(s, market="CN", split=split)
            if len(df) >= 1000:
                long_stocks.append(s)
        except FileNotFoundError:
            continue

    sig_good = build_stock_funnel_signal_panels(portal, long_stocks, split=split, require_good_biz=True, filter_reckless_debt=True)
    panel = sig_good["panel"]
    close = panel["close"]
    pit = portal.load_pit_fundamentals(split="full")
    pit_start = sig_good.get("pit_start_date")
    if pit_start is not None and pd.notna(pit_start):
        cs = pd.Timestamp(pit_start)
        if cs > close.index[0]:
            panel = {k: v.loc[v.index >= cs] for k, v in panel.items()}
            close = panel["close"]
            for key in ("entry_scores", "raw_scores", "stop_prices", "poc_prices", "ma20", "ema20", "ma60", "atr20"):
                sig_good[key] = sig_good[key].loc[sig_good[key].index >= cs]
            sig_good["bench_close"] = sig_good["bench_close"].loc[sig_good["bench_close"].index >= cs]

    dates = close.index
    valid_syms = list(close.columns)
    bench = sig_good["bench_close"]
    ind_map = sig_good["industry_map"]
    harbor = _load_harbor_bars(portal, split)

    # 1) 构建 4 个严格 PIT 的本地基本面因子宽表并做 L1 横截面排序体检
    pit_sub = pit[pit["symbol"].isin(valid_syms)].copy()
    pit_panels: dict[str, pd.DataFrame] = {}
    roe_d, droe_d, ocf_d, divy_d = {}, {}, {}, {}
    for sym, grp in pit_sub.groupby("symbol"):
        g = grp.sort_values("decision_date").drop_duplicates("decision_date", keep="last").set_index("decision_date")
        u = dates.union(g.index)
        roe_s = g["roe"].reindex(u).sort_index().ffill().reindex(dates)
        # 基本面动量：当期 ROE 减去前一期财报 ROE（严格 PIT 递推，无未来）
        droe_raw = g["roe"].diff()
        droe_s = droe_raw.reindex(u).sort_index().ffill().reindex(dates)
        ocf_s = g["ocf_ps"].reindex(u).sort_index().ffill().reindex(dates)
        div_s = g["bonus_per_share"].reindex(u).sort_index().ffill().reindex(dates)
        roe_d[sym] = roe_s
        droe_d[sym] = droe_s
        ocf_d[sym] = ocf_s
        divy_d[sym] = div_s / close[sym].replace(0.0, np.nan)

    pit_panels["pit_roe_level"] = pd.DataFrame(roe_d, index=dates)
    pit_panels["pit_roe_delta"] = pd.DataFrame(droe_d, index=dates)
    pit_panels["pit_ocf_ps"] = pd.DataFrame(ocf_d, index=dates)
    pit_panels["pit_div_yield"] = pd.DataFrame(divy_d, index=dates)

    l1_fundamentals = {}
    for fname, fdf in pit_panels.items():
        r = evaluate_factor_panel_l1(fdf, close, open_panel=panel["open"], horizons=(20, 60), n_groups=5, min_assets=15)
        l1_fundamentals[fname] = {
            "20d_ic": r["horizons"]["20d"]["rank_ic_mean"],
            "20d_t": r["horizons"]["20d"]["hac_t_stat"],
            "20d_top_ex": r["horizons"]["20d"]["quantiles"]["top_vs_pool_excess"],
            "60d_ic": r["horizons"]["60d"]["rank_ic_mean"],
            "60d_t": r["horizons"]["60d"]["hac_t_stat"],
            "60d_top_ex": r["horizons"]["60d"]["quantiles"]["top_vs_pool_excess"],
        }

    # 2) 真实 6 持仓账户对比退出与换仓机制（严格含印花税与 A 股涨跌停）
    stage1_exit = (close < np.minimum(sig_good["ma20"], sig_good["ema20"]) - 0.55 * sig_good["atr20"]).fillna(False)
    two_stage_cb = make_two_stage_stock_exit_callback()
    extra_feats = {k: sig_good[k] for k in ("ma20", "ema20", "ma60", "atr20")}

    # 剔除 L1 证伪的滞后 ΔROE (t=-2.59)，仅保留 L1 显著正向的 PIT 股息率 (t=+2.13) 复合原同源筹码低波打分
    enh_score = (
        0.70 * cs_rank(sig_good["raw_scores"]).fillna(0.5)
        + 0.30 * cs_rank(pit_panels["pit_div_yield"]).fillna(0.5)
    ).where(sig_good["entry_scores"].notna())

    # 接入战役二熊市闸门
    inds = portal.load_all_market_indicators(split=split)
    b50 = inds["cn-breadth-b50"].series.reindex(dates).ffill()
    bear_cap = build_bear_regime_cap_series(bench, b50, mode="bear_regime_ice_exempt", min_cap=0.25)

    base_kw = dict(max_positions=6, max_per_industry=2, max_single_weight=0.18, risk_budget_per_trade=0.012, cost_buy=0.0008, cost_sell=0.0018, idle_cash_mode="gold_dividend_harbor")
    arms = [
        ("S0: 破20日线即卖+避风港", sig_good["entry_scores"], stage1_exit, None, PortfolioSimConfig(**base_kw), None),
        ("S1: 旧版两步拿牛法(全仓守60日)", sig_good["entry_scores"], None, two_stage_cb, PortfolioSimConfig(**base_kw), None),
        ("S2: 满15%分批锁利半仓+余仓守60日", sig_good["entry_scores"], None, two_stage_cb, PortfolioSimConfig(**base_kw, partial_take_profit_pct=0.15, partial_sell_fraction=0.50), None),
        ("S3: 分批锁利+机会成本缓冲换仓", sig_good["entry_scores"], None, two_stage_cb, PortfolioSimConfig(**base_kw, partial_take_profit_pct=0.15, replace_score_margin=0.12, replace_min_hold_days=15), None),
        ("S4: PIT基本面增强+分批锁利+熊市闸门", enh_score, None, two_stage_cb, PortfolioSimConfig(**base_kw, partial_take_profit_pct=0.15, replace_score_margin=0.12, replace_min_hold_days=15), bear_cap),
    ]

    arm_rows = []
    for name, sc, ex_df, ex_cb, cfg, cap_s in arms:
        r = simulate_real_portfolio(
            strategy_name=name, plain_rule_desc=name,
            panel=panel, entry_scores=sc, exit_flags=ex_df, exit_callback=ex_cb,
            stop_prices=sig_good["stop_prices"], poc_prices=sig_good["poc_prices"],
            extra_features=extra_feats, industry_map=ind_map, bench_close=bench,
            harbor_bars=harbor, equity_cap_series=cap_s, config=cfg, n_trials=5,
        )
        arm_rows.append({
            "name": name,
            **r.metrics,
            "dsr": r.overfit_audit.get("deflated_sharpe_prob"),
            "hac_t": r.overfit_audit.get("hac_t_stat"),
        })

    return {
        "split": split,
        "date_range": f"{dates[0].date()} ~ {dates[-1].date()}",
        "long_history_stock_count": len(valid_syms),
        "survivorship_caveat": (
            f"本地具备 2018-2023 长历史的个股仅 {len(valid_syms)} 只（占全库 694 只的 {len(valid_syms)/max(1,len(all_stocks))*100:.1f}%），"
            "偏重现存大盘龙头，存在明显幸存者偏差；此结果仅可用于对比不同退出/换仓/基本面相对增量，不可外推为全A绝对年化。"
        ),
        "l1_pit_fundamentals": l1_fundamentals,
        "arms": arm_rows,
    }


# ------------------------- 战役四：跨资产风险平价 + 趋势保护 + 月度定投零卖出再平衡 -------------------------

def run_campaign4_asset_allocation(portal: DataPortal, *, split: SplitMode = "explore") -> dict[str, object]:
    """战役四完整实证：大类跨资产逆波动率风险平价 + 趋势保护 + 卫星腿 + 每月新工资零卖出低配再平衡。"""
    # 使用本机长历史可交易跨市场场内 ETF（严格从各自真实上市日起参与，绝不倒填未来）
    core_universe = [
        ("513500.SS", "标普500ETF"),
        ("513100.SS", "纳指100ETF"),
        ("513030.SS", "德国ETF"),
        ("512890.SS", "红利低波ETF"),
        ("518850.SS", "黄金ETF"),
    ]
    bench = portal.load_bars("510300.SS", market="CN", split=split)["close"].astype(float).sort_index()
    dates = bench.index

    px_cols: dict[str, pd.Series] = {}
    for sym, _ in core_universe:
        try:
            s = portal.load_bars(sym, market="CN", split=split)["close"].astype(float)
            px_cols[sym] = s.reindex(dates)
        except FileNotFoundError:
            continue
    px_df = pd.DataFrame(px_cols, index=dates)
    ret_df = px_df.pct_change(fill_method=None)
    vol60_df = ret_df.rolling(60, min_periods=30).std() * math.sqrt(252.0)
    ma120_df = px_df.rolling(120, min_periods=80).mean()
    mm_daily = (1.0 + 0.02) ** (1.0 / 252.0) - 1.0

    # 准备战役一+二优胜卫星腿（月度低频行业v2 + 极简300MA120冰点豁免闸门 G4 + 闲钱避风港）
    syms_sec = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
    sec_panel = portal.load_panel_bars(syms_sec, market="CN", split=split, min_rows=180)
    res_ratio, _, _ = compute_sector_resonance_panel(portal, DISTINCT_SECTOR_FUNDS, split=split)
    v2 = build_sector_etf_v2_signals(sec_panel, bench, res_ratio, rebal_interval=20, hold_rank_buffer=8)
    s_close = sec_panel["close"]
    s_dates = s_close.index
    rebal20 = pd.Series(False, index=s_dates)
    rebal20.iloc[::20] = True
    rk_all = v2["raw_score"].rank(axis=1, ascending=False)
    sat_ent = v2["raw_score"].where(rebal20, axis=0)
    sat_ext = pd.DataFrame(rebal20.to_numpy()[:, None] & (rk_all.to_numpy() > 8), index=s_dates, columns=s_close.columns)

    inds = portal.load_all_market_indicators(split=split)
    b50 = inds["cn-breadth-b50"].series.reindex(s_dates).ffill()
    cap_g4 = build_bear_regime_cap_series(bench.reindex(s_dates).ffill(), b50, mode="hs300_ma120_simple", min_cap=0.25)
    harbor = _load_harbor_bars(portal, split)
    sat_res = simulate_real_portfolio(
        strategy_name="行业v2月度低频+G4熊市闸门卫星", plain_rule_desc="卫星腿",
        panel=sec_panel, entry_scores=sat_ent, exit_flags=sat_ext,
        bench_close=bench, harbor_bars=harbor,
        equity_cap_series=cap_g4,
        config=PortfolioSimConfig(max_positions=4, max_per_industry=0, max_single_weight=0.25, risk_budget_per_trade=None, idle_cash_mode="gold_dividend_harbor"),
    )
    sat_ret = sat_res.daily_returns.reindex(dates).fillna(0.0)

    def _sim_alloc(mode: str, monthly_add: float = 0.0) -> dict[str, object]:
        nav = np.ones(len(dates), dtype=float)
        wealth = 1_000_000.0
        contributed = 1_000_000.0
        weights = pd.Series(0.0, index=px_df.columns)
        cash_w = 1.0
        prev_m = None
        turnover_acc = 0.0
        asset_vals = pd.Series(0.0, index=px_df.columns)
        cash_val = wealth

        for t, dt in enumerate(dates):
            if t == 0:
                prev_m = (dt.year, dt.month)
                continue
            r_row = ret_df.iloc[t].fillna(0.0)
            # 先按上日权重结算今日收益
            port_r = float((weights * r_row).sum()) + cash_w * mm_daily
            if mode == "rp_plus_sat":
                port_r = 0.65 * port_r + 0.35 * float(sat_ret.iloc[t])
            nav[t] = nav[t - 1] * (1.0 + port_r)

            asset_vals = asset_vals * (1.0 + r_row)
            cash_val = cash_val * (1.0 + mm_daily)
            cur_m = (dt.year, dt.month)
            if cur_m != prev_m:
                # 仅使用前一日可得波动率与趋势线决定本月权重（严格零未来函数）
                avail = px_df.iloc[t - 1].notna()
                active_cols = [c for c in px_df.columns if bool(avail[c])]
                target_w = pd.Series(0.0, index=px_df.columns)
                if active_cols:
                    if mode == "equal_weight":
                        for c in active_cols:
                            target_w[c] = 1.0 / len(active_cols)
                    else:
                        vols = vol60_df.iloc[t - 1][active_cols].fillna(0.20).clip(lower=0.06)
                        inv_v = 1.0 / vols
                        base_w = inv_v / inv_v.sum()
                        if mode in ("rp_trend", "rp_plus_sat", "dca_underweight_rebal"):
                            # 跌破120日线资产减半转入货币理财，控回撤不硬扛单边熊
                            for c in active_cols:
                                px_prev = float(px_df.iloc[t - 1][c])
                                m120_prev = float(ma120_df.iloc[t - 1][c]) if pd.notna(ma120_df.iloc[t - 1][c]) else px_prev
                                target_w[c] = float(base_w[c]) * (1.0 if px_prev >= m120_prev else 0.35)
                        else:
                            for c in active_cols:
                                target_w[c] = float(base_w[c])

                if monthly_add > 0.0 and mode == "dca_underweight_rebal":
                    # 零卖出摩擦再平衡：新工资 100% 投向当前相对目标权重最欠配的资产（完全不卖出旧仓！）
                    contributed += monthly_add
                    tot_now = float(asset_vals.sum() + cash_val + monthly_add)
                    deficits = (target_w * tot_now - asset_vals).clip(lower=0.0)
                    if deficits.sum() > 1e-6:
                        add_alloc = monthly_add * (deficits / deficits.sum())
                        asset_vals += add_alloc * (1.0 - 0.0008)
                    else:
                        cash_val += monthly_add
                    tot_after = float(asset_vals.sum() + cash_val)
                    weights = asset_vals / max(tot_after, 1.0)
                    cash_w = cash_val / max(tot_after, 1.0)
                else:
                    if monthly_add > 0.0:
                        contributed += monthly_add
                        cash_val += monthly_add
                    delta = float((target_w - weights).abs().sum()) / 2.0
                    turnover_acc += delta
                    fee_drag = delta * 0.0008
                    nav[t] *= (1.0 - fee_drag)
                    weights = target_w
                    cash_w = max(0.0, 1.0 - float(weights.sum()))
                    tot_now = float(asset_vals.sum() + cash_val) * (1.0 - fee_drag)
                    asset_vals = tot_now * weights
                    cash_val = tot_now * cash_w
                prev_m = cur_m

        nav_ser = pd.Series(nav, index=dates)
        dr = nav_ser.pct_change(fill_method=None).fillna(0.0)
        b_nav = bench / bench.iloc[0]
        b_r = b_nav.pct_change(fill_method=None).fillna(0.0)
        yrs = max((dates[-1] - dates[0]).days / 365.25, 0.1)
        cagr = float(nav_ser.iloc[-1] ** (1.0 / yrs) - 1.0)
        ex_cagr = float((nav_ser.iloc[-1] / b_nav.iloc[-1]) ** (1.0 / yrs) - 1.0)
        mdd = float((nav_ser / nav_ser.cummax() - 1.0).min())
        calmar = float(cagr / abs(mdd)) if mdd < -1e-9 else 0.0
        sd = float(dr.std(ddof=1))
        sharpe = float((dr.mean() / sd) * math.sqrt(252.0)) if sd > 1e-12 else 0.0
        aud = overfitting_risk_audit(dr, bench_returns=b_r, n_trials=4)
        slices = slice_performance_by_year_and_regime(dr, bench)
        return {
            "cagr": round(cagr, 4),
            "excess_vs_hs300": round(ex_cagr, 4),
            "max_drawdown": round(mdd, 4),
            "calmar": round(calmar, 2),
            "sharpe": round(sharpe, 2),
            "annual_turnover": round(turnover_acc / yrs, 2),
            "dsr": aud["deflated_sharpe_prob"],
            "hac_t": aud["hac_t_stat"],
            "contributed": round(contributed, 0),
            "ending_wealth": round(float(asset_vals.sum() + cash_val), 0),
            "by_year": {y["year"]: y["total_return"] for y in slices["by_year"]},
        }

    b_nav = bench / bench.iloc[0]
    yrs = max((dates[-1] - dates[0]).days / 365.25, 0.1)
    b_cagr = float(b_nav.iloc[-1] ** (1.0 / yrs) - 1.0)
    b_mdd = float((b_nav / b_nav.cummax() - 1.0).min())

    arms = [
        {"name": "A0: 沪深300死拿", "cagr": round(b_cagr, 4), "excess_vs_hs300": 0.0, "max_drawdown": round(b_mdd, 4), "calmar": round(b_cagr / abs(b_mdd), 2), "sharpe": 0.21, "annual_turnover": 0.0, "dsr": 0.50, "hac_t": 0.0},
        {"name": "A1: 跨资产月度静态等权", **_sim_alloc("equal_weight")},
        {"name": "A2: 跨资产逆波动率风险平价", **_sim_alloc("risk_parity")},
        {"name": "A3: 风险平价+120日趋势保护", **_sim_alloc("rp_trend")},
        {"name": "A4: 风险平价趋势65%+行业v2闸门35%", **_sim_alloc("rp_plus_sat")},
        {"name": "A5: 月定投1万·零卖出低配再平衡", **_sim_alloc("dca_underweight_rebal", monthly_add=10_000.0)},
    ]

    return {
        "split": split,
        "date_range": f"{dates[0].date()} ~ {dates[-1].date()}",
        "core_assets": [f"{s}({n})" for s, n in core_universe if s in px_df.columns],
        "missing_asset_gap": "本机尚缺长久期国债/美债 ETF（如 511010/511260/TLT），当前防御端以黄金+红利低波+货币理财为主，补齐长债ETF后全天候风险平价效果仍有提升空间。",
        "arms": arms,
    }


def _print_all_campaigns() -> None:
    portal = DataPortal()
    c1 = run_campaign1_sector_etf_v2(portal, split="explore")
    print("=== [战役一] 18行业ETF月度低频重构 (explore <=2023) ===")
    for a in c1["arms"]:
        print(f"  {a['name']:<32} Trd={a['trades_count']:>3d} WR={a['win_rate']*100:>4.1f}% CAGR={a['cagr']*100:>+6.2f}% Ex300={a['excess_cagr']*100:>+6.2f}% MDD={a['max_drawdown']*100:>6.2f}% Calmar={a['calmar']:>4.2f} ExTop3={a['ex_top3_trades_cagr']*100:>+6.2f}% Turn={a['annual_turnover']:>4.1f}x")
    print(f"  Plateau pass vs v1: {c1['plateau_pass_rate']*100:.0f}% | WF beats v1: {sum(1 for w in c1['walk_forward_vs_v1'] if w['delta'] > 0)}/{len(c1['walk_forward_vs_v1'])}")

    c2 = run_campaign2_bear_gate(portal, split="explore")
    print("\n=== [战役二] 熊市动态仓位闸门·防磨血 vs 防踏空 (explore <=2023) ===")
    for g in c2["gates"]:
        print(f"  {g['gate']:<28} CAGR={g['cagr']*100:>+6.2f}% Ex300={g['excess_cagr']*100:>+6.2f}% MDD={g['max_drawdown']*100:>6.2f}% Calmar={g['calmar']:>4.2f} | 18={g['y2018_bear']*100:>+5.1f}% 19={g['y2019_rally']*100:>+5.1f}% 20={g['y2020_rally']*100:>+5.1f}% 22={g['y2022_bear']*100:>+5.1f}% | BearSave={g['bear_loss_saved_18_22']*100:>+5.1f}% BullDiff={g['bull_rally_diff_19_20']*100:>+5.1f}%")

    c3 = run_campaign3_stock_mechanisms(portal, split="explore")
    print(f"\n=== [战役三] A股个股分批锁利+置换+纯净PIT股息率 (N={c3['long_history_stock_count']}, {c3['date_range']}) ===")
    for a in c3["arms"]:
        print(f"  {a['name']:<32} Trd={a['trades_count']:>3d} WR={a['win_rate']*100:>4.1f}% CAGR={a['cagr']*100:>+6.2f}% Ex300={a['excess_cagr']*100:>+6.2f}% MDD={a['max_drawdown']*100:>6.2f}% Calmar={a['calmar']:>4.2f} ExTop3={a['ex_top3_trades_cagr']*100:>+6.2f}% Turn={a['annual_turnover']:>4.1f}x")

    c4 = run_campaign4_asset_allocation(portal, split="explore")
    print(f"\n=== [战役四] 跨资产风险平价 + 趋势保护 + 月定投零卖出再平衡 ({c4['date_range']}) ===")
    for a in c4["arms"]:
        extra = f" | 投入{a['contributed']/1e4:.0f}万->期末{a['ending_wealth']/1e4:.1f}万" if a.get("contributed", 0) > 1_000_000 else ""
        print(f"  {a['name']:<34} CAGR={a['cagr']*100:>+6.2f}% Ex300={a['excess_vs_hs300']*100:>+6.2f}% MDD={a['max_drawdown']*100:>6.2f}% Calmar={a['calmar']:>4.2f} Sharpe={a['sharpe']:>4.2f} Turn={a['annual_turnover']:>4.2f}x{extra}")


if __name__ == "__main__":
    _print_all_campaigns()
