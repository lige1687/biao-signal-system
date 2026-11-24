"""个人账户级多腿联合模拟器（Core + Satellite + Cash Harbor + 月度现金流）与弱项驱动失血诊断器（multi_leg）。

解决两大战略短板：
1. 把压舱石底仓（美股/红利）、行业右侧波段进攻腿、A股好生意龙头进攻腿、黄金/红利闲钱过渡池与每月工资定投
   放进同一本真实资金账本里做相关性与回撤联防模拟；
2. 弱项驱动（Error-Driven）失血诊断器：自动定位策略历史 Top 3 最深回撤区间、最失血体制与最亏交易，
   定向生成下一轮因子挖掘的金融假说清单，把研究真正变成自我纠偏的进化闭环。
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

from .chip_trend import compare_stock_strategies_detailed
from .data_portal import DataPortal, SplitMode
from .fund_evaluator import compare_fund_strategies_detailed
from .portfolio_sim import PortfolioBacktestResult
from .validation import classify_market_regimes, overfitting_risk_audit, slice_performance_by_year_and_regime


@dataclass(frozen=True)
class MultiLegConfig:
    initial_capital: float = 1_000_000.0
    core_weight: float = 0.35          # 压舱石底仓（如标普500/纳指100 + 红利低波）
    sector_etf_weight: float = 0.40    # 18只去重行业基金右侧波段 + 闲钱避风港
    stock_leader_weight: float = 0.25  # A股PIT好生意+两步拿牛法 + 闲钱避风港（设为0即纯基金组合）
    monthly_contribution: float = 0.0  # 可选：每月新增工资定投金额（元，如 10000）
    rebalance_freq: str = "Q"          # 季度再平衡防单一腿偏离过大
    rebalance_cost: float = 0.0008


def diagnose_strategy_bleeding(
    result: PortfolioBacktestResult,
    bench_close: pd.Series,
) -> dict[str, object]:
    """弱项驱动（Error-Driven）失血诊断：自动找出最痛回撤、最弱市场体制与定向因子挖掘建议。"""
    nav = result.nav_series.astype(float).dropna()
    if len(nav) < 30:
        return {"available": False, "reason": "净值序列过短"}

    regimes = classify_market_regimes(bench_close).reindex(nav.index).ffill().fillna("温和横盘震荡")
    bc = bench_close.astype(float).reindex(nav.index).ffill()

    # 1) 提取历史 Top 3 独立回撤谷段（按峰-谷-恢复切分）
    peak = nav.cummax()
    dd = nav / peak - 1.0
    episodes: list[dict[str, object]] = []
    in_dd = False
    start_pos = 0
    for i in range(len(nav)):
        if dd.iloc[i] < -1e-4 and not in_dd:
            in_dd = True
            start_pos = max(0, i - 1)
        elif (dd.iloc[i] >= -1e-6 or i == len(nav) - 1) and in_dd:
            seg_dd = dd.iloc[start_pos : i + 1]
            trough_dt = seg_dd.idxmin()
            depth = float(seg_dd.min())
            if depth <= -0.04:
                peak_dt = nav.index[start_pos]
                end_dt = nav.index[i]
                dom_regime = str(regimes.loc[peak_dt:trough_dt].mode().iloc[0])
                b_chg = float(bc.loc[trough_dt] / bc.loc[peak_dt] - 1.0) if bc.loc[peak_dt] > 0 else 0.0
                episodes.append({
                    "peak_date": str(peak_dt.date()),
                    "trough_date": str(trough_dt.date()),
                    "recovered_date": str(end_dt.date()) if dd.iloc[i] >= -1e-6 else "期末未恢复",
                    "drawdown_pct": round(depth, 4),
                    "duration_days": int((trough_dt - peak_dt).days),
                    "dominant_regime": dom_regime,
                    "bench_return_during_dd": round(b_chg, 4),
                })
            in_dd = False
    episodes.sort(key=lambda x: float(x["drawdown_pct"]))
    top3_dd = episodes[:3]

    # 2) 最亏的 5 笔交易及退出原因归因
    worst_trades = sorted(result.trades, key=lambda x: x.net_return)[:5]
    loss_reasons: dict[str, int] = {}
    for tr in result.trades:
        if tr.net_return < 0:
            loss_reasons[tr.exit_reason] = loss_reasons.get(tr.exit_reason, 0) + 1

    # 3) 最失血的市场体制
    worst_regime = min(result.by_regime, key=lambda x: float(x["cagr"])) if result.by_regime else None
    worst_year = min(result.by_year, key=lambda x: float(x["cagr"])) if result.by_year else None

    # 4) 根据失血画像生成下一轮 AI 因子挖掘的定向假说建议
    hypotheses: list[str] = []
    if worst_regime and float(worst_regime["cagr"]) < -0.02:
        reg_name = str(worst_regime["regime"])
        if reg_name == "急涨急跌剧震":
            hypotheses.append("【防剧震洗盘】最大亏钱集中在剧烈震荡期，优先考虑避开高开低走和上蹿下跳的假突破。")
        elif reg_name == "阴跌下行熊":
            hypotheses.append("【熊市主动少买点】最大亏钱集中在阴跌熊市，大盘跌破半年线时主动压缩进攻仓位，把闲钱转去黄金或红利低波。")
        else:
            hypotheses.append(f"【{reg_name}适配】在「{reg_name}」阶段表现最弱（每年平均 {float(worst_regime['cagr'])*100:+.1f}%），建议补充更抗跌的高股息或低波动标的。")

    if float(result.metrics.get("top3_profit_share", 0.0)) > 0.50:
        hypotheses.append("【别把收益押在少数两三笔大涨上】利润过度集中在最赚的 3 笔交易，建议把资金分得更散，并搭配稳健分红品种平抑起伏。")

    if float(result.metrics.get("avg_equity_exposure", 0.0)) < 0.45 and result.config.idle_cash_mode == "cash":
        hypotheses.append("【别让空仓闲钱躺着睡觉】超过一半时间空仓，把闲钱放进稳在季线上的黄金与红利基金，比反复调买卖点管用得多。")

    if not hypotheses:
        hypotheses.append("当前各种牛熊环境下回撤比较均衡，下一步继续跟盘观察真实表现，并优先补齐场内基金每日申赎份额与国债基金数据。")

    return {
        "available": True,
        "strategy_name": result.strategy_name,
        "top3_drawdown_episodes": top3_dd,
        "worst_regime": worst_regime,
        "worst_year": worst_year,
        "loss_exit_reason_counts": loss_reasons,
        "worst_5_trades": [
            {
                "symbol": tr.symbol,
                "entry_date": tr.entry_date,
                "exit_date": tr.exit_date,
                "net_return": tr.net_return,
                "holding_days": tr.holding_days,
                "exit_reason": tr.exit_reason,
            }
            for tr in worst_trades
        ],
        "next_mining_hypotheses": hypotheses,
    }


def simulate_multi_leg_account(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    config: MultiLegConfig | None = None,
) -> dict[str, object]:
    """把【海外+红利压舱石底仓 + 18行业右侧波段(含闲钱避风港) + A股PIT好生意龙头(含闲钱避风港)】放进同一张总账本联合回测。"""
    cfg = config or MultiLegConfig()
    w_sum = cfg.core_weight + cfg.sector_etf_weight + cfg.stock_leader_weight
    if w_sum <= 0:
        raise ValueError("三腿权重之和必须大于 0")
    w_core = cfg.core_weight / w_sum
    w_sec = cfg.sector_etf_weight / w_sum
    w_stk = cfg.stock_leader_weight / w_sum

    bench_close = portal.load_bars("510300.SS", market="CN", split=split)["close"].astype(float).sort_index()

    # 1) 压舱石底仓腿：美股宽基（优先 513500/513100，若缺则用 SPY）+ 国内红利低波 512890 等权持有
    core_rets_list: list[pd.Series] = []
    core_used: list[str] = []
    for sym, mkt in (("513100.SS", "CN"), ("513500.SS", "CN"), ("512890.SS", "CN")):
        try:
            b = portal.load_bars(sym, market=mkt, split=split)["close"].astype(float)
            if len(b) >= 120:
                core_rets_list.append(b.pct_change().rename(sym))
                core_used.append(sym)
        except FileNotFoundError:
            continue
    if not core_rets_list:
        core_rets_list.append(bench_close.pct_change().rename("510300.SS"))
        core_used.append("510300.SS")
    core_daily = pd.concat(core_rets_list, axis=1).mean(axis=1).fillna(0.0).rename("稳健底仓部分")

    # 2) 18行业右侧波段 + 闲钱避风港
    fund_runs = compare_fund_strategies_detailed(portal, split=split)
    sec_res = next((r for r in fund_runs if "闲钱黄金红利过渡" in r.strategy_name), fund_runs[-1] if fund_runs else None)
    sec_daily = sec_res.daily_returns.rename("行业波段+避风港") if sec_res is not None else pd.Series(0.0, index=bench_close.index, name="行业波段+避风港")

    # 3) A股好生意 + 两步拿牛 + 闲钱避风港
    stk_res = None
    if w_stk > 1e-6:
        stk_runs = compare_stock_strategies_detailed(portal, split=split)
        stk_res = next((r for r in stk_runs if "两步拿牛+闲钱避风港" in r.strategy_name), stk_runs[-1] if stk_runs else None)
    stk_daily = stk_res.daily_returns.rename("个股好生意+避风港") if stk_res is not None else pd.Series(0.0, index=bench_close.index, name="个股好生意+避风港")

    # 对齐共同交易日
    common_idx = core_daily.index.intersection(sec_daily.index)
    if w_stk > 1e-6 and stk_res is not None:
        common_idx = common_idx.intersection(stk_daily.index)
    common_idx = common_idx.sort_values()

    legs_df = pd.DataFrame({
        "稳健底仓部分": core_daily.reindex(common_idx).fillna(0.0),
        "行业波段+避风港": sec_daily.reindex(common_idx).fillna(0.0),
        "个股好生意+避风港": stk_daily.reindex(common_idx).fillna(0.0),
    })

    # 季度再平衡 + 可选每月定投现金流的真实资金路径
    targets = np.array([w_core, w_sec, w_stk], dtype=float)
    leg_vals = cfg.initial_capital * targets
    total_contributed = cfg.initial_capital
    nav_unit = np.ones(len(common_idx), dtype=float)
    wealth_vals = np.zeros(len(common_idx), dtype=float)
    prev_q = None
    prev_m = None

    r_mat = legs_df.to_numpy(dtype=float)
    for t, dt in enumerate(common_idx):
        if t > 0:
            prev_eq = float(leg_vals.sum())
            leg_vals = leg_vals * (1.0 + r_mat[t])
            cur_eq = float(leg_vals.sum())
            step_ret = (cur_eq / prev_eq - 1.0) if prev_eq > 0 else 0.0

            # 季度再平衡扣真实切换成本
            cur_q = (dt.year, (dt.month - 1) // 3)
            if prev_q is not None and cur_q != prev_q and cur_eq > 0:
                desired = cur_eq * targets
                turnover = float(np.abs(desired - leg_vals).sum()) / 2.0
                fee = turnover * cfg.rebalance_cost
                leg_vals = np.maximum(0.0, desired - fee * targets)
                step_ret = (float(leg_vals.sum()) / prev_eq - 1.0) if prev_eq > 0 else step_ret
            prev_q = cur_q

            nav_unit[t] = nav_unit[t - 1] * (1.0 + step_ret)

            # 每月首个交易日注入新工资现金流（按目标比例补低配腿）
            cur_m = (dt.year, dt.month)
            if cfg.monthly_contribution > 0 and prev_m is not None and cur_m != prev_m:
                leg_vals += cfg.monthly_contribution * targets
                total_contributed += cfg.monthly_contribution
            prev_m = cur_m
        else:
            prev_q = (dt.year, (dt.month - 1) // 3)
            prev_m = (dt.year, dt.month)
        wealth_vals[t] = float(leg_vals.sum())

    nav_ser = pd.Series(nav_unit, index=common_idx, name="LEI多腿联合账户")
    daily_r = nav_ser.pct_change().fillna(0.0)
    b_aligned = bench_close.reindex(common_idx).ffill().bfill()
    b_nav = b_aligned / b_aligned.iloc[0]
    b_r = b_nav.pct_change().fillna(0.0)

    years = max((common_idx[-1] - common_idx[0]).days / 365.25, 1.0 / 12.0)
    cagr = float(nav_ser.iloc[-1] ** (1.0 / years) - 1.0)
    b_cagr = float(b_nav.iloc[-1] ** (1.0 / years) - 1.0)
    ex_cagr = float((nav_ser.iloc[-1] / b_nav.iloc[-1]) ** (1.0 / years) - 1.0)
    mdd = float((nav_ser / nav_ser.cummax() - 1.0).min())
    b_mdd = float((b_nav / b_nav.cummax() - 1.0).min())
    calmar = float(cagr / abs(mdd)) if mdd < -1e-9 else 0.0
    sd = float(daily_r.std(ddof=1))
    sharpe = float((daily_r.mean() / sd) * math.sqrt(252.0)) if sd > 1e-12 else 0.0

    # 各腿相关性矩阵（验证是否真正做到低相关分散）
    active_legs = [c for c, w in zip(legs_df.columns, targets) if w > 1e-6]
    corr_dict = legs_df[active_legs].corr().round(3).to_dict()

    # 包装轻量 PortfolioBacktestResult 以便复用统一失血诊断器
    fake_res = PortfolioBacktestResult(
        strategy_name="LEI多腿联合账户",
        plain_rule_desc=f"压舱石{w_core*100:.0f}% + 行业波段{w_sec*100:.0f}% + 个股好生意{w_stk*100:.0f}%",
        config=sec_res.config if sec_res is not None else None,  # type: ignore[arg-type]
        nav_series=nav_ser,
        daily_returns=daily_r,
        bench_nav=b_nav,
        trades=(sec_res.trades if sec_res else []) + (stk_res.trades if stk_res else []),
        metrics={"top3_profit_share": 0.0, "avg_equity_exposure": 1.0},
        by_year=slice_performance_by_year_and_regime(daily_r, bench_close)["by_year"],
        by_regime=slice_performance_by_year_and_regime(daily_r, bench_close)["by_regime"],
        overfit_audit=overfitting_risk_audit(daily_r, bench_returns=b_r, n_trials=1),
    )

    return {
        "split": split,
        "date_range": f"{common_idx[0].date()} ~ {common_idx[-1].date()}",
        "core_assets_used": core_used,
        "weights": {"core": round(w_core, 2), "sector_etf": round(w_sec, 2), "stock_leader": round(w_stk, 2)},
        "summary_metrics": {
            "cagr": round(cagr, 4),
            "bench_hs300_cagr": round(b_cagr, 4),
            "excess_cagr_vs_hs300": round(ex_cagr, 4),
            "max_drawdown": round(mdd, 4),
            "bench_hs300_mdd": round(b_mdd, 4),
            "calmar": round(calmar, 2),
            "sharpe": round(sharpe, 2),
            "total_contributed_yuan": round(total_contributed, 2),
            "ending_wealth_yuan": round(float(wealth_vals[-1]), 2),
        },
        "leg_correlation_matrix": corr_dict,
        "by_year": fake_res.by_year,
        "by_regime": fake_res.by_regime,
        "overfit_audit": fake_res.overfit_audit,
        "bleeding_diagnosis": diagnose_strategy_bleeding(fake_res, bench_close),
    }
