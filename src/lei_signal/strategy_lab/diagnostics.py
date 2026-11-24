"""L1/L2/L3 统一因子与策略体检引擎（diagnostics）。

把旧版 `research/` 最有价值的统计严谨度无痛融合进 `strategy_lab` 的 3 秒极简体验：
- L1 信息体检层：横截面 Rank IC / ICIR / HAC t 值、多期衰减(5/20/60日)、5组单调性与多头端相对同池超额、两级正交查重（Rank相关 + 尾部Jaccard + 残差IC）；
- L2 真实账户层：复用 `portfolio_sim` 与同源信号层的真实扣费资金账本；
- L3 稳健与消融层：Leave-One-Factor-Out 组件消融 + 纯等权基准对照 + 参数邻域 ±20% 平原测试 + Purged Walk-Forward 逐折验货。
"""
from __future__ import annotations

import math
from typing import Literal
import numpy as np
import pandas as pd
from scipy import stats

from .data_portal import DataPortal, SplitMode
from .fund_evaluator import DISTINCT_SECTOR_FUNDS
from .portfolio_sim import PortfolioSimConfig, simulate_real_portfolio
from .signals import (
    DEFAULT_SECTOR_WEIGHTS,
    DEFAULT_STOCK_WEIGHTS,
    build_sector_etf_signal_panels,
    build_stock_funnel_signal_panels,
    compute_sector_resonance_panel,
    make_two_stage_stock_exit_callback,
)
from .validation import build_purged_walk_forward_folds, newey_west_tstat


def _cross_sectional_rank_ic(
    factor: pd.DataFrame,
    fwd_ret: pd.DataFrame,
    *,
    min_assets: int = 5,
) -> pd.Series:
    """逐日计算横截面 Spearman Rank IC（严禁跨日期拼接混淆时序与截面）。"""
    common_idx = factor.index.intersection(fwd_ret.index)
    common_cols = factor.columns.intersection(fwd_ret.columns)
    f = factor.reindex(index=common_idx, columns=common_cols)
    y = fwd_ret.reindex(index=common_idx, columns=common_cols)

    ics: dict[pd.Timestamp, float] = {}
    for dt in common_idx:
        fv = f.loc[dt].to_numpy(dtype=float)
        yv = y.loc[dt].to_numpy(dtype=float)
        mask = np.isfinite(fv) & np.isfinite(yv)
        if int(mask.sum()) < min_assets:
            continue
        x_m, y_m = fv[mask], yv[mask]
        if np.std(x_m) < 1e-12 or np.std(y_m) < 1e-12:
            continue
        rho, _ = stats.spearmanr(x_m, y_m)
        if np.isfinite(rho):
            ics[dt] = float(rho)
    return pd.Series(ics, dtype=float).sort_index()


def _quantile_group_analysis(
    factor: pd.DataFrame,
    fwd_ret: pd.DataFrame,
    *,
    n_groups: int = 5,
    min_assets: int = 5,
) -> dict[str, object]:
    """按日分组统计各分位组未来收益、多头端相对同池超额、单调性与头部换手。"""
    common_idx = factor.index.intersection(fwd_ret.index)
    common_cols = factor.columns.intersection(fwd_ret.columns)
    f = factor.reindex(index=common_idx, columns=common_cols)
    y = fwd_ret.reindex(index=common_idx, columns=common_cols)

    grp_rets: dict[int, list[float]] = {g: [] for g in range(1, n_groups + 1)}
    pool_means: list[float] = []
    prev_top_set: set[str] | None = None
    top_turnovers: list[float] = []

    for dt in common_idx:
        row_f = f.loc[dt]
        row_y = y.loc[dt]
        valid = row_f.notna() & row_y.notna() & np.isfinite(row_f) & np.isfinite(row_y)
        n_val = int(valid.sum())
        if n_val < max(min_assets, n_groups):
            continue
        sf = row_f.loc[valid]
        sy = row_y.loc[valid]
        if sf.nunique() < 2:
            continue
        # 按排名百分位切分 n_groups 组（1=最低，n_groups=最高）
        pct = sf.rank(method="average", pct=True)
        bins = np.clip(np.ceil(pct * n_groups).astype(int), 1, n_groups)
        pool_means.append(float(sy.mean()))
        for g in range(1, n_groups + 1):
            g_vals = sy.loc[bins == g]
            if len(g_vals) > 0:
                grp_rets[g].append(float(g_vals.mean()))
        top_syms = set(sf.index[bins == n_groups].tolist())
        if prev_top_set is not None and top_syms:
            jacc_keep = len(top_syms & prev_top_set) / max(1, len(top_syms | prev_top_set))
            top_turnovers.append(1.0 - jacc_keep)
        prev_top_set = top_syms

    group_means = {
        f"G{g}": round(float(np.mean(grp_rets[g])), 5) if grp_rets[g] else None
        for g in range(1, n_groups + 1)
    }
    pool_mean = float(np.mean(pool_means)) if pool_means else 0.0
    g_top = group_means.get(f"G{n_groups}")
    g_bot = group_means.get("G1")
    top_vs_pool = round(g_top - pool_mean, 5) if g_top is not None else None
    bot_vs_pool = round(g_bot - pool_mean, 5) if g_bot is not None else None
    ls_spread = round(g_top - g_bot, 5) if (g_top is not None and g_bot is not None) else None

    valid_pairs = [(g, group_means[f"G{g}"]) for g in range(1, n_groups + 1) if group_means[f"G{g}"] is not None]
    mono = 0.0
    if len(valid_pairs) >= 3:
        rho, _ = stats.spearmanr([p[0] for p in valid_pairs], [p[1] for p in valid_pairs])
        mono = round(float(rho), 3) if np.isfinite(rho) else 0.0

    return {
        "n_dates": len(pool_means),
        "pool_mean_ret": round(pool_mean, 5),
        "group_means": group_means,
        "top_vs_pool_excess": top_vs_pool,
        "bottom_vs_pool_excess": bot_vs_pool,
        "long_short_spread": ls_spread,
        "monotonicity_spearman": mono,
        "top_group_daily_churn": round(float(np.mean(top_turnovers)), 4) if top_turnovers else None,
    }


def check_factor_redundancy(
    candidate: pd.DataFrame,
    existing_factors: dict[str, pd.DataFrame],
    *,
    fwd_ret: pd.DataFrame | None = None,
    horizon: int = 20,
    min_assets: int = 5,
) -> dict[str, object]:
    """两级去重门禁：
    1) 一级：逐日横截面 Rank 相关 + Top-20% 头部 Jaccard 重合度；
    2) 二级：横截面正交残差化（剔除已有因子线性投影后），检验残差是否仍有独立 Rank IC。
    """
    if not existing_factors:
        return {
            "status": "🟢 首批因子（无历史对照库）",
            "max_abs_rank_corr": 0.0,
            "max_top20_jaccard": 0.0,
            "most_similar_factor": None,
            "pairwise": [],
            "orthogonal_residual_ic": None,
        }

    pairwise: list[dict[str, object]] = []
    max_corr = 0.0
    max_jacc = 0.0
    most_sim: str | None = None

    for name, ref in existing_factors.items():
        idx = candidate.index.intersection(ref.index)
        cols = candidate.columns.intersection(ref.columns)
        c_df = candidate.reindex(index=idx, columns=cols)
        r_df = ref.reindex(index=idx, columns=cols)

        rhos: list[float] = []
        jaccs: list[float] = []
        for dt in idx:
            cv = c_df.loc[dt].to_numpy(dtype=float)
            rv = r_df.loc[dt].to_numpy(dtype=float)
            m = np.isfinite(cv) & np.isfinite(rv)
            if int(m.sum()) < min_assets:
                continue
            cm, rm = cv[m], rv[m]
            if np.std(cm) < 1e-12 or np.std(rm) < 1e-12:
                continue
            rho, _ = stats.spearmanr(cm, rm)
            if np.isfinite(rho):
                rhos.append(float(rho))
            k = max(1, int(math.ceil(len(cm) * 0.20)))
            top_c = set(np.argsort(cm)[-k:].tolist())
            top_r = set(np.argsort(rm)[-k:].tolist())
            jaccs.append(len(top_c & top_r) / max(1, len(top_c | top_r)))

        mean_rho = float(np.mean(rhos)) if rhos else 0.0
        mean_jacc = float(np.mean(jaccs)) if jaccs else 0.0
        pairwise.append({
            "existing_factor": name,
            "rank_corr": round(mean_rho, 4),
            "top20_jaccard": round(mean_jacc, 4),
            "n_dates": len(rhos),
        })
        if abs(mean_rho) > max_corr:
            max_corr = abs(mean_rho)
            most_sim = name
        if mean_jacc > max_jacc:
            max_jacc = mean_jacc

    # 二级：逐日横截面 OLS 残差化，验证剔除已有因子后残差是否仍具备排序预测增量
    resid_info: dict[str, object] | None = None
    if fwd_ret is not None:
        ref_names = list(existing_factors.keys())
        idx = candidate.index.intersection(fwd_ret.index)
        cols = candidate.columns.intersection(fwd_ret.columns)
        for rn in ref_names:
            idx = idx.intersection(existing_factors[rn].index)
            cols = cols.intersection(existing_factors[rn].columns)
        resid_panel = pd.DataFrame(np.nan, index=idx, columns=cols)
        for dt in idx:
            y_c = candidate.reindex(index=[dt], columns=cols).iloc[0].to_numpy(dtype=float)
            x_mat = np.column_stack([
                existing_factors[rn].reindex(index=[dt], columns=cols).iloc[0].to_numpy(dtype=float)
                for rn in ref_names
            ])
            valid = np.isfinite(y_c) & np.isfinite(x_mat).all(axis=1)
            if int(valid.sum()) < max(min_assets, len(ref_names) + 2):
                continue
            Xv = x_mat[valid]
            yv = y_c[valid]
            # 截距项 + 截面标准化
            X_design = np.column_stack([np.ones(len(yv)), Xv])
            beta, *_ = np.linalg.lstsq(X_design, yv, rcond=None)
            res = yv - X_design @ beta
            row_out = np.full(len(cols), np.nan)
            row_out[valid] = res
            resid_panel.loc[dt] = row_out

        resid_ic_ser = _cross_sectional_rank_ic(resid_panel, fwd_ret, min_assets=min_assets)
        hac = newey_west_tstat(resid_ic_ser, nlags=max(1, horizon - 1)) if len(resid_ic_ser) >= 15 else {"t_stat": 0.0, "p_value": 1.0}
        resid_ic_mean = float(resid_ic_ser.mean()) if len(resid_ic_ser) else 0.0
        resid_ic_std = float(resid_ic_ser.std(ddof=1)) if len(resid_ic_ser) > 1 else 0.0
        resid_info = {
            "residual_rank_ic": round(resid_ic_mean, 4),
            "residual_icir": round(resid_ic_mean / resid_ic_std, 3) if resid_ic_std > 1e-12 else 0.0,
            "residual_hac_t": hac["t_stat"],
            "n_dates": int(len(resid_ic_ser)),
        }

    if max_corr >= 0.75 and (resid_info is None or abs(float(resid_info["residual_hac_t"])) < 1.65):
        status = f"🔴 高度重复（与【{most_sim}】排序相关 {max_corr:.2f} 且残差无显著增量）"
    elif max_corr >= 0.60 or max_jacc >= 0.55:
        status = f"🟡 中度重合（与【{most_sim}】相关 {max_corr:.2f}，需结合残差增量决定替代或剔除）"
    else:
        status = "🟢 低相关独立增量候选"

    pairwise.sort(key=lambda x: abs(float(x["rank_corr"])), reverse=True)
    return {
        "status": status,
        "max_abs_rank_corr": round(max_corr, 4),
        "max_top20_jaccard": round(max_jacc, 4),
        "most_similar_factor": most_sim,
        "pairwise": pairwise,
        "orthogonal_residual_ic": resid_info,
    }


def evaluate_factor_panel_l1(
    factor_panel: pd.DataFrame,
    close_panel: pd.DataFrame,
    *,
    open_panel: pd.DataFrame | None = None,
    horizons: tuple[int, ...] = (5, 20, 60),
    n_groups: int = 5,
    min_assets: int = 5,
    existing_factors: dict[str, pd.DataFrame] | None = None,
) -> dict[str, object]:
    """L1 因子信息层完整体检：多期 Rank IC/ICIR/HAC + 5组单调性与多头端相对同池超额 + 两级正交查重。"""
    close = close_panel.sort_index()
    entry_px = open_panel.reindex_like(close).shift(-1) if open_panel is not None else close
    horizon_results: dict[str, dict[str, object]] = {}
    fwd_for_redundancy: pd.DataFrame | None = None

    for h in horizons:
        # 严格可成交前向收益：T日收盘信号 -> T+1开盘买入 -> T+h收盘卖出
        fwd = close.shift(-h) / entry_px - 1.0
        if h == 20 or fwd_for_redundancy is None:
            fwd_for_redundancy = fwd
        ic_ser = _cross_sectional_rank_ic(factor_panel, fwd, min_assets=min_assets)
        ic_mean = float(ic_ser.mean()) if len(ic_ser) else 0.0
        ic_std = float(ic_ser.std(ddof=1)) if len(ic_ser) > 1 else 0.0
        icir = (ic_mean / ic_std) if ic_std > 1e-12 else 0.0
        ic_win = float((ic_ser > 0.0).mean()) if len(ic_ser) else 0.0
        hac = newey_west_tstat(ic_ser, nlags=max(1, h - 1)) if len(ic_ser) >= 15 else {"t_stat": 0.0, "p_value": 1.0}
        groups = _quantile_group_analysis(factor_panel, fwd, n_groups=n_groups, min_assets=min_assets)

        horizon_results[f"{h}d"] = {
            "horizon_days": h,
            "n_dates": int(len(ic_ser)),
            "rank_ic_mean": round(ic_mean, 4),
            "rank_ic_std": round(ic_std, 4),
            "icir_descriptive": round(icir, 3),
            "ic_positive_rate": round(ic_win, 4),
            "hac_t_stat": hac["t_stat"],
            "hac_p_value": hac["p_value"],
            "quantiles": groups,
        }

    redundancy = check_factor_redundancy(
        factor_panel,
        existing_factors or {},
        fwd_ret=fwd_for_redundancy,
        horizon=20,
        min_assets=min_assets,
    )

    # 生成一句大白话信息层诊断
    h20 = horizon_results.get("20d") or next(iter(horizon_results.values()))
    ic20 = float(h20["rank_ic_mean"])
    t20 = float(h20["hac_t_stat"])
    top_ex = h20["quantiles"].get("top_vs_pool_excess")
    if abs(ic20) >= 0.03 and abs(t20) >= 1.96 and (top_ex is None or top_ex > 0):
        verdict = f"🟢 挑品眼光有效（往后1个月挑出来的靠前品种明显跑赢平均，排序相关={ic20:+.3f}）"
    elif abs(ic20) >= 0.02 and abs(t20) >= 1.2:
        verdict = f"🟡 挑品眼光偏弱（方向偏正但还不够稳，建议结合真实账户看有没有实际增量）"
    else:
        verdict = f"🔴 挑品眼光偏弱（往后1个月排序和真实涨跌关联弱，不建议直接用来选买点）"

    return {
        "horizons": horizon_results,
        "redundancy": redundancy,
        "l1_verdict_cn": verdict,
    }


def run_sector_ablation_and_robustness(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    idle_cash_mode: Literal["cash", "gold_dividend_harbor"] = "gold_dividend_harbor",
) -> dict[str, object]:
    """行业基金右侧策略的 L3 自动体检：Leave-One-Factor-Out 消融 + 等权对照 + 参数±20%高原 + Walk-Forward 逐折验证。"""
    sector_syms = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
    panel = portal.load_panel_bars(sector_syms, market="CN", split=split, min_rows=180)
    close = panel["close"]
    if close.empty:
        return {"available": False, "reason": "行业基金历史行情不足"}

    dates = close.index
    bench = portal.load_bars("510300.SS", market="CN", split=split)["close"].reindex(dates).ffill()
    res_ratio, _, _ = compute_sector_resonance_panel(portal, DISTINCT_SECTOR_FUNDS, split=split)
    harbor_bars: dict[str, pd.DataFrame] = {}
    for key, hsym in (("gold", "518850.SS"), ("dividend", "512890.SS")):
        try:
            harbor_bars[key] = portal.load_bars(hsym, market="CN", split=split)
        except FileNotFoundError:
            pass

    cfg = PortfolioSimConfig(
        max_positions=4,
        max_per_industry=0,
        max_single_weight=0.25,
        risk_budget_per_trade=0.012,
        cost_buy=0.0008,
        cost_sell=0.0008,
        idle_cash_mode=idle_cash_mode,
    )

    def _eval_variant(
        name: str,
        weights: dict[str, float],
        *,
        require_res: bool = True,
        res_min: float = 0.50,
        dist_max: float = 0.12,
        crowd_max: float = 0.85,
    ):
        sigs = build_sector_etf_signal_panels(
            panel, bench,
            resonance_ratio=res_ratio,
            weights=weights,
            require_resonance=require_res,
            resonance_min=res_min,
            max_dist_ma60=dist_max,
            max_crowd_pct=crowd_max,
        )
        return simulate_real_portfolio(
            strategy_name=name,
            plain_rule_desc=name,
            panel=panel,
            entry_scores=sigs["right_entry_scores"],
            exit_flags=sigs["right_exit_flags"],
            stop_prices=sigs["stop_prices"],
            bench_close=bench,
            harbor_bars=harbor_bars,
            config=cfg,
        ), sigs

    # 1) 基准方案 + 纯等权对照 + 逐项剔除消融
    base_res, base_sigs = _eval_variant("当前基准权重(40/25/25/10)", DEFAULT_SECTOR_WEIGHTS)
    base_cagr = float(base_res.metrics["cagr"])
    base_calmar = float(base_res.metrics["calmar"])

    eq_w = {k: 0.25 for k in DEFAULT_SECTOR_WEIGHTS}
    eq_res, _ = _eval_variant("简化对照：四项等权(25/25/25/25)", eq_w)

    ablation_rows: list[dict[str, object]] = [
        {
            "variant": base_res.strategy_name,
            "cagr": base_res.metrics["cagr"],
            "excess_cagr": base_res.metrics["excess_cagr"],
            "max_drawdown": base_res.metrics["max_drawdown"],
            "calmar": base_res.metrics["calmar"],
            "delta_cagr_vs_base": 0.0,
            "verdict_cn": "参照基准",
        },
        {
            "variant": eq_res.strategy_name,
            "cagr": eq_res.metrics["cagr"],
            "excess_cagr": eq_res.metrics["excess_cagr"],
            "max_drawdown": eq_res.metrics["max_drawdown"],
            "calmar": eq_res.metrics["calmar"],
            "delta_cagr_vs_base": round(float(eq_res.metrics["cagr"]) - base_cagr, 4),
            "verdict_cn": (
                "等权已不输手工加权（可简化）"
                if float(eq_res.metrics["calmar"]) >= base_calmar - 0.05
                else "手工加权相对等权有正贡献"
            ),
        },
    ]

    cn_names = {
        "resonance": "板块内部共振",
        "near_cost": "离60日成本近",
        "rel_strength": "相对沪深300领涨",
        "low_crowd": "成交未拥挤清爽度",
    }
    for drop_key, drop_cn in cn_names.items():
        w_drop = {k: (0.0 if k == drop_key else v) for k, v in DEFAULT_SECTOR_WEIGHTS.items()}
        r_drop, _ = _eval_variant(
            f"剔除【{drop_cn}】",
            w_drop,
            require_res=(drop_key != "resonance"),
        )
        dc = round(float(r_drop.metrics["cagr"]) - base_cagr, 4)
        ablation_rows.append({
            "variant": r_drop.strategy_name,
            "cagr": r_drop.metrics["cagr"],
            "excess_cagr": r_drop.metrics["excess_cagr"],
            "max_drawdown": r_drop.metrics["max_drawdown"],
            "calmar": r_drop.metrics["calmar"],
            "delta_cagr_vs_base": dc,
            "verdict_cn": (
                "✅ 正贡献组件（去掉后表现下降）"
                if dc < -0.003 or float(r_drop.metrics["calmar"]) < base_calmar - 0.05
                else "⚠️ 边际贡献偏弱或拖累（可评估精简）"
            ),
        })

    # 2) 参数邻域 ±20% 高原稳健测试
    plateau_specs = [
        ("默认参数(12% / 85% / 50%)", 0.12, 0.85, 0.50),
        ("离成本收紧-20%(9.6%)", 0.096, 0.85, 0.50),
        ("离成本放宽+20%(14.4%)", 0.144, 0.85, 0.50),
        ("拥挤度收紧(78%)", 0.12, 0.78, 0.50),
        ("拥挤度放宽(92%)", 0.12, 0.92, 0.50),
        ("共振门槛收紧(60%)", 0.12, 0.85, 0.60),
        ("共振门槛放宽(40%)", 0.12, 0.85, 0.40),
    ]
    plateau_rows: list[dict[str, object]] = []
    passed_cnt = 0
    for label, dm, cm, rm in plateau_specs:
        pr, _ = _eval_variant(label, DEFAULT_SECTOR_WEIGHTS, res_min=rm, dist_max=dm, crowd_max=cm)
        beats = float(pr.metrics["excess_cagr"]) > 0.0
        if beats:
            passed_cnt += 1
        plateau_rows.append({
            "param_point": label,
            "cagr": pr.metrics["cagr"],
            "excess_cagr": pr.metrics["excess_cagr"],
            "max_drawdown": pr.metrics["max_drawdown"],
            "calmar": pr.metrics["calmar"],
            "beats_bench": beats,
        })
    plateau_pass_rate = round(passed_cnt / len(plateau_specs), 3)

    # 3) Purged Walk-Forward 逐折样本外核验
    folds = build_purged_walk_forward_folds(dates, train_min_days=360, test_days=252, purge_days=20)
    wf_rows: list[dict[str, object]] = []
    for f in folds:
        sub_r = base_res.daily_returns.loc[f.test_start : f.test_end]
        sub_b = bench.pct_change().reindex(sub_r.index).fillna(0.0)
        if len(sub_r) < 30:
            continue
        nav_f = (1.0 + sub_r).cumprod()
        bnav_f = (1.0 + sub_b).cumprod()
        yrs = max(len(sub_r) / 252.0, 0.1)
        cagr_f = float(nav_f.iloc[-1] ** (1.0 / yrs) - 1.0)
        ex_f = float((nav_f.iloc[-1] / bnav_f.iloc[-1]) ** (1.0 / yrs) - 1.0)
        mdd_f = float((nav_f / nav_f.cummax() - 1.0).min())
        wf_rows.append({
            "fold_id": f.fold_id,
            "test_window": f"{f.test_start} ~ {f.test_end}",
            "n_days": len(sub_r),
            "cagr": round(cagr_f, 4),
            "excess_cagr": round(ex_f, 4),
            "max_drawdown": round(mdd_f, 4),
        })

    # 4) L1 信息体检（综合打分对未来 5/20/60 日排序力）
    l1_report = evaluate_factor_panel_l1(
        base_sigs["right_raw_scores"],
        panel["close"],
        open_panel=panel["open"],
        horizons=(5, 20, 60),
        n_groups=4,
        min_assets=6,
    )

    return {
        "available": True,
        "split": split,
        "idle_cash_mode": idle_cash_mode,
        "l1_factor_info": l1_report,
        "l2_base_metrics": base_res.metrics,
        "l2_by_year": base_res.by_year,
        "l2_by_regime": base_res.by_regime,
        "l2_overfit_audit": base_res.overfit_audit,
        "l3_ablation": ablation_rows,
        "l3_parameter_plateau": {
            "pass_rate": plateau_pass_rate,
            "verdict_cn": (
                f"🟢 厚实高原（{passed_cnt}/{len(plateau_specs)} 组邻域参数跑赢基准）"
                if plateau_pass_rate >= 0.70
                else f"🔴 尖峰敏感（仅 {passed_cnt}/{len(plateau_specs)} 组邻域参数跑赢基准，存在过拟合风险）"
            ),
            "points": plateau_rows,
        },
        "l3_walk_forward": wf_rows,
    }


def run_stock_ablation_and_robustness(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    idle_cash_mode: Literal["cash", "gold_dividend_harbor"] = "gold_dividend_harbor",
    max_symbols: int = 120,
) -> dict[str, object]:
    """A 股同源漏斗策略的 L1+L2+L3 一体化体检（含等权 Rank 对照与逐项因子消融）。"""
    stocks = portal.list_cn_stocks()[:max_symbols]
    if not stocks:
        return {"available": False, "reason": "本地个股行情为空"}

    base_sigs = build_stock_funnel_signal_panels(portal, stocks, split=split, require_good_biz=True, filter_reckless_debt=True)
    panel = base_sigs["panel"]
    close = panel["close"]
    if close.empty:
        return {"available": False, "reason": "满足样本长度的个股不足"}

    bench = base_sigs["bench_close"]
    ind_map = base_sigs["industry_map"]
    two_stage_cb = make_two_stage_stock_exit_callback()
    extra_feats = {k: base_sigs[k] for k in ("ma20", "ema20", "ma60", "atr20")}

    harbor_bars: dict[str, pd.DataFrame] = {}
    for key, hsym in (("gold", "518850.SS"), ("dividend", "512890.SS")):
        try:
            harbor_bars[key] = portal.load_bars(hsym, market="CN", split=split)
        except FileNotFoundError:
            pass

    cfg = PortfolioSimConfig(
        max_positions=6,
        max_per_industry=2,
        max_single_weight=0.18,
        risk_budget_per_trade=0.012,
        cost_buy=0.0008,
        cost_sell=0.0018,
        idle_cash_mode=idle_cash_mode,
    )

    def _sim(name: str, sig_dict: dict[str, object]):
        return simulate_real_portfolio(
            strategy_name=name,
            plain_rule_desc=name,
            panel=sig_dict["panel"],
            entry_scores=sig_dict["entry_scores"],
            exit_callback=two_stage_cb,
            stop_prices=sig_dict["stop_prices"],
            poc_prices=sig_dict["poc_prices"],
            extra_features={k: sig_dict[k] for k in ("ma20", "ema20", "ma60", "atr20")},
            industry_map=sig_dict["industry_map"],
            bench_close=sig_dict["bench_close"],
            harbor_bars=harbor_bars,
            config=cfg,
        )

    base_res = _sim("当前同源权重", base_sigs)
    base_cagr = float(base_res.metrics["cagr"])

    # 等权基准 + 关键因子消融（低波动、高债排雷、PIT好生意）
    eq_w = {k: 1.0 / len(DEFAULT_STOCK_WEIGHTS) for k in DEFAULT_STOCK_WEIGHTS}
    eq_sigs = build_stock_funnel_signal_panels(portal, list(close.columns), split=split, weights=eq_w)
    eq_res = _sim("简化对照：六项等权", eq_sigs)

    no_lv_w = {**DEFAULT_STOCK_WEIGHTS, "low_vol": 0.0}
    no_lv_res = _sim("剔除【低波稳健度】", build_stock_funnel_signal_panels(portal, list(close.columns), split=split, weights=no_lv_w))
    no_debt_res = _sim("剔除【高债大扩张排雷】", build_stock_funnel_signal_panels(portal, list(close.columns), split=split, filter_reckless_debt=False))
    no_biz_res = _sim("剔除【PIT好生意过滤】", build_stock_funnel_signal_panels(portal, list(close.columns), split=split, require_good_biz=False, filter_reckless_debt=False))

    ablation_rows = []
    for r in (base_res, eq_res, no_lv_res, no_debt_res, no_biz_res):
        dc = round(float(r.metrics["cagr"]) - base_cagr, 4)
        ablation_rows.append({
            "variant": r.strategy_name,
            "cagr": r.metrics["cagr"],
            "excess_cagr": r.metrics["excess_cagr"],
            "max_drawdown": r.metrics["max_drawdown"],
            "calmar": r.metrics["calmar"],
            "delta_cagr_vs_base": dc,
        })

    l1_report = evaluate_factor_panel_l1(
        base_sigs["raw_scores"],
        panel["close"],
        open_panel=panel["open"],
        horizons=(5, 20, 60),
        n_groups=5,
        min_assets=10,
    )

    return {
        "available": True,
        "split": split,
        "symbols_tested": len(close.columns),
        "idle_cash_mode": idle_cash_mode,
        "l1_factor_info": l1_report,
        "l2_base_metrics": base_res.metrics,
        "l2_by_year": base_res.by_year,
        "l2_by_regime": base_res.by_regime,
        "l2_overfit_audit": base_res.overfit_audit,
        "l3_ablation": ablation_rows,
    }
