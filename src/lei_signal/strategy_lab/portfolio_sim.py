"""真实资金组合回测账本引擎（portfolio_sim）。

彻底替代旧版 `nav_panel.pct_change().mean(axis=1)`（隐式每日零成本等权再平衡、掩盖资金冲突与集中度）：
1. 真实资金账户 + 持仓上限 + 同行业上限 + 按止损距离倒推的单笔风险预算仓位上限；
2. A 股实盘交易约束：T 日收盘信号 -> T+1 开盘成交、一字涨停买不进、一字跌停卖不出顺延、停牌锁仓、T+1 卖出限制、差异化买/卖双边费率；
3. 闲钱避风港联动：空仓资金可选 0 收益现金 / 货币理财 / 稳在 60 日均线上方的黄金(518850)+红利低波(512890)过渡池（含真实切换成本）；
4. 强制交付完整决策账本：相对基准扣费净超额、信息比率、年化换手率、剔除最赚 Top 3 交易压力测试、最长水下天数、分年度/分体制明细与过拟合体检。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable, Literal
import numpy as np
import pandas as pd

from .chip_trend import StrategyLedgerSummary
from .validation import overfitting_risk_audit, slice_performance_by_year_and_regime


@dataclass(frozen=True)
class PortfolioSimConfig:
    initial_cash: float = 1_000_000.0
    max_positions: int = 5
    max_per_industry: int = 2
    max_single_weight: float = 0.25
    risk_budget_per_trade: float | None = 0.012  # 单笔看错最多亏总资金比例（None 表示等权上限）
    cost_buy: float = 0.0008
    cost_sell: float = 0.0008
    enforce_a_share_limits: bool = True
    idle_cash_mode: Literal["cash", "money_market", "gold_dividend_harbor"] = "cash"
    money_market_annual_yield: float = 0.020
    harbor_switch_cost: float = 0.0006  # 黄金/红利基金切换单边成本
    partial_take_profit_pct: float | None = None   # 例如 0.15 表示浮盈满15%次日开盘兑现一半仓位锁利
    partial_sell_fraction: float = 0.50
    replace_score_margin: float | None = None      # 机会成本置换：满仓时新候选打分领先最弱老仓超过该差值且老仓滞涨时腾笼换鸟
    replace_min_hold_days: int = 15


@dataclass
class OpenPosition:
    symbol: str
    industry: str
    shares: float
    entry_date: pd.Timestamp
    entry_idx: int
    entry_price: float          # 实际次日开盘含费成本价
    entry_signal_close: float   # T日触发收盘价
    entry_poc: float
    stop_price: float
    max_close: float
    entry_notional: float
    partial_taken: bool = False
    meta: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TradeRecord:
    symbol: str
    industry: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    entry_weight: float
    net_return: float
    pnl_yuan: float
    holding_days: int
    exit_reason: str


@dataclass
class PortfolioBacktestResult:
    strategy_name: str
    plain_rule_desc: str
    config: PortfolioSimConfig
    nav_series: pd.Series
    daily_returns: pd.Series
    bench_nav: pd.Series | None
    trades: list[TradeRecord]
    metrics: dict[str, object]
    by_year: list[dict[str, object]]
    by_regime: list[dict[str, object]]
    overfit_audit: dict[str, object]

    def to_ledger_summary(self) -> StrategyLedgerSummary:
        m = self.metrics
        return StrategyLedgerSummary(
            strategy_name=self.strategy_name,
            plain_rule_desc=self.plain_rule_desc,
            trades_count=int(m["trades_count"]),
            win_rate=float(m["win_rate"]),
            avg_win_pct=float(m["avg_win_pct"]),
            avg_loss_pct=float(m["avg_loss_pct"]),
            payoff_ratio=float(m["payoff_ratio"]),
            cagr=float(m["cagr"]),
            max_drawdown=float(m["max_drawdown"]),
            calmar=float(m["calmar"]),
            avg_holding_days=float(m["avg_holding_days"]),
            exposure_pct=float(m["avg_equity_exposure"]),
        )


ExitCallback = Callable[[OpenPosition, pd.Timestamp, dict[str, float]], tuple[bool, str]]


def _limit_pct_for_symbol(symbol: str) -> float:
    """A 股板块涨跌停幅度（创业板/科创板 20%，其余主板及普通 ETF 10%）。"""
    code = symbol.split(".")[0]
    if code.startswith(("300", "301", "688", "588", "159915")):
        return 0.195  # 留 0.5% 缓冲识别一字板开盘
    return 0.095


def _longest_underwater(nav: pd.Series) -> int:
    peak = nav.cummax()
    underwater = nav < peak * (1.0 - 1e-9)
    max_run = 0
    cur = 0
    for flag in underwater.to_numpy():
        if flag:
            cur += 1
            if cur > max_run:
                max_run = cur
        else:
            cur = 0
    return int(max_run)


def _prepare_harbor_state(
    dates: pd.DatetimeIndex,
    harbor_bars: dict[str, pd.DataFrame] | None,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """预计算黄金与红利低波基金的日收益率及是否稳在60日均线上方（严格只用 T-1 收盘判定 T 日持有）。"""
    empty_r = pd.Series(0.0, index=dates)
    empty_ok = pd.Series(False, index=dates)
    if not harbor_bars:
        return empty_r, empty_ok, empty_r, empty_ok

    def _one(key: str) -> tuple[pd.Series, pd.Series]:
        df = harbor_bars.get(key)
        if df is None or len(df) < 70 or "close" not in df.columns:
            return empty_r, empty_ok
        cl = df["close"].astype(float).sort_index()
        ma60 = cl.rolling(60, min_periods=60).mean()
        # 严格用前一日收盘判断是否站稳60日均线，避免当日偷看收盘价（用 float 过渡避免 Pandas object 向下转型警告）
        steady_prev = (cl > ma60).astype(float).shift(1).reindex(dates).ffill().fillna(0.0) > 0.5
        daily_ret = cl.pct_change(fill_method=None).reindex(dates).fillna(0.0)
        return daily_ret, steady_prev

    g_ret, g_ok = _one("gold")
    d_ret, d_ok = _one("dividend")
    return g_ret, g_ok, d_ret, d_ok


def simulate_real_portfolio(
    *,
    strategy_name: str,
    plain_rule_desc: str,
    panel: dict[str, pd.DataFrame],
    entry_scores: pd.DataFrame,
    exit_flags: pd.DataFrame | None = None,
    exit_callback: ExitCallback | None = None,
    stop_prices: pd.DataFrame | None = None,
    poc_prices: pd.DataFrame | None = None,
    extra_features: dict[str, pd.DataFrame] | None = None,
    industry_map: dict[str, str] | None = None,
    bench_close: pd.Series | None = None,
    harbor_bars: dict[str, pd.DataFrame] | None = None,
    equity_cap_series: pd.Series | None = None,
    config: PortfolioSimConfig | None = None,
    n_trials: int = 1,
) -> PortfolioBacktestResult:
    """在真实单账户资金账本下逐日回放交易信号（T日收盘决策 -> T+1日开盘成交）。"""
    cfg = config or PortfolioSimConfig()
    open_df = panel["open"].sort_index()
    close_df = panel["close"].sort_index()
    dates = close_df.index.intersection(entry_scores.index).sort_values()

    if len(dates) < 30:
        empty_nav = pd.Series([1.0], index=dates[:1] if len(dates) else pd.DatetimeIndex([pd.Timestamp("2020-01-02")]))
        empty_ret = pd.Series([0.0], index=empty_nav.index)
        return PortfolioBacktestResult(
            strategy_name=strategy_name,
            plain_rule_desc=plain_rule_desc,
            config=cfg,
            nav_series=empty_nav,
            daily_returns=empty_ret,
            bench_nav=None,
            trades=[],
            metrics={
                "cagr": 0.0, "bench_cagr": 0.0, "excess_cagr": 0.0,
                "total_return": 0.0, "bench_total_return": 0.0,
                "max_drawdown": 0.0, "bench_max_drawdown": 0.0,
                "calmar": 0.0, "sharpe": 0.0, "info_ratio": 0.0,
                "trades_count": 0, "win_rate": 0.0, "avg_win_pct": 0.0,
                "avg_loss_pct": 0.0, "payoff_ratio": 0.0, "avg_holding_days": 0.0,
                "annual_turnover": 0.0, "avg_equity_exposure": 0.0,
                "avg_harbor_exposure": 0.0, "avg_cash_exposure": 1.0,
                "longest_underwater_days": 0, "blocked_buy_limit_up": 0,
                "blocked_sell_limit_down": 0, "ex_top3_trades_cagr": 0.0,
                "ex_top3_trades_win_rate": 0.0, "top3_profit_share": 0.0,
            },
            by_year=[],
            by_regime=[],
            overfit_audit={"risk_light": "样本不足"},
        )

    open_df = open_df.reindex(dates)
    close_df = close_df.reindex(dates)
    prev_close_df = close_df.shift(1)
    scores_df = entry_scores.reindex(index=dates, columns=close_df.columns)
    exits_df = exit_flags.reindex(index=dates, columns=close_df.columns) if exit_flags is not None else None
    stops_df = stop_prices.reindex(index=dates, columns=close_df.columns) if stop_prices is not None else None
    pocs_df = poc_prices.reindex(index=dates, columns=close_df.columns) if poc_prices is not None else None
    extras = {
        k: v.reindex(index=dates, columns=close_df.columns)
        for k, v in (extra_features or {}).items()
    }
    ind_map = industry_map or {}
    cap_ser = (
        equity_cap_series.reindex(dates).ffill().fillna(1.0).clip(0.0, 1.0)
        if equity_cap_series is not None
        else pd.Series(1.0, index=dates)
    )

    g_ret, g_ok, d_ret, d_ok = _prepare_harbor_state(dates, harbor_bars)
    mm_daily = (1.0 + cfg.money_market_annual_yield) ** (1.0 / 252.0) - 1.0

    cash = float(cfg.initial_cash)
    positions: dict[str, OpenPosition] = {}
    pending_sells: dict[str, str] = {}
    pending_partial_sells: dict[str, str] = {}
    trades: list[TradeRecord] = []

    nav_vals = np.ones(len(dates), dtype=float)
    eq_exp_vals = np.zeros(len(dates), dtype=float)
    harbor_exp_vals = np.zeros(len(dates), dtype=float)
    traded_notional_total = 0.0
    blocked_buy_limit = 0
    blocked_sell_limit = 0
    prev_harbor_alloc = (0.0, 0.0)  # (gold_frac, div_frac) of idle cash

    # 预先转为字典/ndarray 提速（比逐行 pandas loc 快 20x+）
    symbols = list(close_df.columns)
    sym_to_col = {s: idx for idx, s in enumerate(symbols)}
    open_arr = open_df.to_numpy(dtype=float)
    close_arr = close_df.to_numpy(dtype=float)
    prev_close_arr = prev_close_df.to_numpy(dtype=float)
    score_arr = scores_df.to_numpy(dtype=float)
    exit_arr = exits_df.to_numpy(dtype=bool) if exits_df is not None else None
    stop_arr = stops_df.to_numpy(dtype=float) if stops_df is not None else None
    poc_arr = pocs_df.to_numpy(dtype=float) if pocs_df is not None else None
    extra_arrs = {k: v.to_numpy(dtype=float) for k, v in extras.items()}
    cap_arr = cap_ser.to_numpy(dtype=float)
    g_ret_arr = g_ret.to_numpy(dtype=float)
    g_ok_arr = g_ok.to_numpy(dtype=bool)
    d_ret_arr = d_ret.to_numpy(dtype=float)
    d_ok_arr = d_ok.to_numpy(dtype=bool)

    for t in range(len(dates)):
        dt = dates[t]

        # 1) 闲钱过渡收益结算（T-1 收盘已决定的闲钱在 T 日产生的收益）
        if t > 0 and cash > 0.0:
            if cfg.idle_cash_mode == "money_market":
                cash *= (1.0 + mm_daily)
            elif cfg.idle_cash_mode == "gold_dividend_harbor":
                g_flag = bool(g_ok_arr[t])
                d_flag = bool(d_ok_arr[t])
                if g_flag and d_flag:
                    alloc = (0.5, 0.5)
                    h_ret = 0.5 * float(g_ret_arr[t]) + 0.5 * float(d_ret_arr[t])
                elif g_flag:
                    alloc = (1.0, 0.0)
                    h_ret = float(g_ret_arr[t])
                elif d_flag:
                    alloc = (0.0, 1.0)
                    h_ret = float(d_ret_arr[t])
                else:
                    alloc = (0.0, 0.0)
                    h_ret = mm_daily
                # 仅在黄金/红利配比发生切换时扣除真实单边交易成本
                delta_alloc = abs(alloc[0] - prev_harbor_alloc[0]) + abs(alloc[1] - prev_harbor_alloc[1])
                if delta_alloc > 1e-6:
                    switch_fee = cash * (0.5 * delta_alloc) * cfg.harbor_switch_cost
                    cash = max(0.0, cash - switch_fee)
                prev_harbor_alloc = alloc
                cash *= (1.0 + h_ret)

        # 2) 开盘执行 T-1 收盘产生的卖出指令（先卖后买释放现金与名额）
        if t > 0 and pending_sells:
            still_pending: dict[str, str] = {}
            for sym, reason in list(pending_sells.items()):
                pos = positions.get(sym)
                if pos is None:
                    continue
                if pos.entry_idx >= t:
                    # A 股 T+1 约束
                    still_pending[sym] = reason
                    continue
                c_idx = sym_to_col[sym]
                op = open_arr[t, c_idx]
                prev_c = prev_close_arr[t, c_idx]
                if not (np.isfinite(op) and op > 0.0):
                    # 停牌锁仓，顺延至下一个可成交开盘日
                    still_pending[sym] = reason
                    continue
                if cfg.enforce_a_share_limits and np.isfinite(prev_c) and prev_c > 0.0:
                    lim = _limit_pct_for_symbol(sym)
                    if op <= prev_c * (1.0 - lim):
                        # 一字跌停开盘卖不出，顺延
                        blocked_sell_limit += 1
                        still_pending[sym] = reason
                        continue
                gross = pos.shares * op
                net_proceeds = gross * (1.0 - cfg.cost_sell)
                cash += net_proceeds
                traded_notional_total += gross
                exit_px_net = op * (1.0 - cfg.cost_sell)
                trade_ret = exit_px_net / pos.entry_price - 1.0
                pnl_yuan = net_proceeds - pos.entry_notional
                trades.append(
                    TradeRecord(
                        symbol=sym,
                        industry=pos.industry,
                        entry_date=str(pos.entry_date.date()),
                        exit_date=str(dt.date()),
                        entry_price=round(pos.entry_price, 4),
                        exit_price=round(exit_px_net, 4),
                        entry_weight=round(pos.entry_notional / max(cfg.initial_cash, 1.0), 4),
                        net_return=round(float(trade_ret), 5),
                        pnl_yuan=round(float(pnl_yuan), 2),
                        holding_days=int(t - pos.entry_idx),
                        exit_reason=reason,
                    )
                )
                del positions[sym]
            pending_sells = still_pending

        # 2b) 开盘执行分批锁利半仓卖出（不清空名额，但立即回笼一半现金并锁定成本）
        if t > 0 and pending_partial_sells:
            still_partial: dict[str, str] = {}
            for sym, reason in list(pending_partial_sells.items()):
                pos = positions.get(sym)
                if pos is None or pos.partial_taken or pos.entry_idx >= t:
                    continue
                c_idx = sym_to_col[sym]
                op = open_arr[t, c_idx]
                prev_c = prev_close_arr[t, c_idx]
                if not (np.isfinite(op) and op > 0.0):
                    still_partial[sym] = reason
                    continue
                if cfg.enforce_a_share_limits and np.isfinite(prev_c) and prev_c > 0.0:
                    if op <= prev_c * (1.0 - _limit_pct_for_symbol(sym)):
                        blocked_sell_limit += 1
                        still_partial[sym] = reason
                        continue
                frac = float(np.clip(cfg.partial_sell_fraction, 0.1, 0.9))
                sell_shares = pos.shares * frac
                sell_notional = pos.entry_notional * frac
                gross = sell_shares * op
                net_proceeds = gross * (1.0 - cfg.cost_sell)
                cash += net_proceeds
                traded_notional_total += gross
                exit_px_net = op * (1.0 - cfg.cost_sell)
                trade_ret = exit_px_net / pos.entry_price - 1.0
                trades.append(
                    TradeRecord(
                        symbol=sym,
                        industry=pos.industry,
                        entry_date=str(pos.entry_date.date()),
                        exit_date=str(dt.date()),
                        entry_price=round(pos.entry_price, 4),
                        exit_price=round(exit_px_net, 4),
                        entry_weight=round(sell_notional / max(cfg.initial_cash, 1.0), 4),
                        net_return=round(float(trade_ret), 5),
                        pnl_yuan=round(float(net_proceeds - sell_notional), 2),
                        holding_days=int(t - pos.entry_idx),
                        exit_reason=reason,
                    )
                )
                pos.shares -= sell_shares
                pos.entry_notional -= sell_notional
                pos.partial_taken = True
            pending_partial_sells = still_partial

        # 3) 开盘执行 T-1 收盘选出的新买进候选（按打分降序，严守仓位/行业/风险预算/涨停限制）
        if t > 0:
            # 计算当日开盘前总权益（用于仓位与风险预算）
            open_holdings_val = 0.0
            for sym, pos in positions.items():
                c_idx = sym_to_col[sym]
                px_ref = open_arr[t, c_idx] if np.isfinite(open_arr[t, c_idx]) and open_arr[t, c_idx] > 0 else prev_close_arr[t, c_idx]
                if np.isfinite(px_ref) and px_ref > 0:
                    open_holdings_val += pos.shares * px_ref
            total_eq_open = cash + open_holdings_val
            day_eq_cap = float(cap_arr[t - 1])
            max_equity_notional = total_eq_open * day_eq_cap
            avail_equity_budget = max(0.0, min(cash, max_equity_notional - open_holdings_val))

            slots_left = max(0, cfg.max_positions - len(positions))
            if slots_left > 0 and avail_equity_budget > total_eq_open * 0.02:
                prev_scores = score_arr[t - 1]
                valid_cols = np.where(np.isfinite(prev_scores) & (prev_scores > -1e9))[0]
                if len(valid_cols) > 0:
                    order = valid_cols[np.argsort(prev_scores[valid_cols])[::-1]]
                    ind_counts: dict[str, int] = {}
                    for p in positions.values():
                        if p.industry:
                            ind_counts[p.industry] = ind_counts.get(p.industry, 0) + 1

                    for c_idx in order:
                        if slots_left <= 0 or avail_equity_budget <= total_eq_open * 0.02:
                            break
                        sym = symbols[c_idx]
                        if sym in positions:
                            continue
                        ind = ind_map.get(sym, "")
                        if ind and cfg.max_per_industry > 0 and ind_counts.get(ind, 0) >= cfg.max_per_industry:
                            continue
                        op = open_arr[t, c_idx]
                        prev_c = prev_close_arr[t, c_idx]
                        if not (np.isfinite(op) and op > 0.0):
                            continue
                        if cfg.enforce_a_share_limits and np.isfinite(prev_c) and prev_c > 0.0:
                            lim = _limit_pct_for_symbol(sym)
                            if op >= prev_c * (1.0 + lim):
                                blocked_buy_limit += 1
                                continue

                        # 计算目标单笔仓位：基础等分权重与风险预算倒推权重取较小值
                        base_w = min(cfg.max_single_weight, day_eq_cap / max(1, cfg.max_positions))
                        target_w = base_w
                        stop_px = float(stop_arr[t - 1, c_idx]) if (stop_arr is not None and np.isfinite(stop_arr[t - 1, c_idx])) else np.nan
                        if cfg.risk_budget_per_trade is not None and np.isfinite(stop_px) and 0.0 < stop_px < op:
                            stop_dist = max((op - stop_px) / op, 0.03)
                            risk_w = cfg.risk_budget_per_trade / stop_dist
                            target_w = min(target_w, risk_w)
                        target_w = float(np.clip(target_w, 0.03, cfg.max_single_weight))

                        alloc_cash = min(avail_equity_budget, total_eq_open * target_w)
                        if alloc_cash <= total_eq_open * 0.02:
                            continue
                        invest = alloc_cash / (1.0 + cfg.cost_buy)
                        fee = alloc_cash - invest
                        shares = invest / op
                        cash -= (invest + fee)
                        avail_equity_budget -= (invest + fee)
                        traded_notional_total += invest

                        poc_val = float(poc_arr[t - 1, c_idx]) if (poc_arr is not None and np.isfinite(poc_arr[t - 1, c_idx])) else op
                        sig_cl = float(prev_c) if (np.isfinite(prev_c) and prev_c > 0) else op
                        positions[sym] = OpenPosition(
                            symbol=sym,
                            industry=ind,
                            shares=shares,
                            entry_date=dt,
                            entry_idx=t,
                            entry_price=op * (1.0 + cfg.cost_buy),
                            entry_signal_close=sig_cl,
                            entry_poc=poc_val,
                            stop_price=stop_px if np.isfinite(stop_px) else op * 0.92,
                            max_close=sig_cl,
                            entry_notional=invest + fee,
                        )
                        if ind:
                            ind_counts[ind] = ind_counts.get(ind, 0) + 1
                        slots_left -= 1

        # 4) 收盘估值与触发次日开盘卖出信号判定（严格仅用截至当日 T 收盘数据）
        close_holdings_val = 0.0
        for sym, pos in list(positions.items()):
            c_idx = sym_to_col[sym]
            cl = close_arr[t, c_idx]
            if not (np.isfinite(cl) and cl > 0.0):
                # 停牌按前收估值
                cl = prev_close_arr[t, c_idx] if np.isfinite(prev_close_arr[t, c_idx]) else pos.entry_price
            close_holdings_val += pos.shares * cl
            if cl > pos.max_close:
                pos.max_close = float(cl)

            if sym not in pending_sells:
                should_exit = False
                exit_reason = ""
                if exit_arr is not None and bool(exit_arr[t, c_idx]):
                    should_exit = True
                    exit_reason = "规则出场信号"
                if not should_exit and exit_callback is not None:
                    row_ctx: dict[str, float] = {"close": float(cl)}
                    if poc_arr is not None and np.isfinite(poc_arr[t, c_idx]):
                        row_ctx["poc_price"] = float(poc_arr[t, c_idx])
                    for k, arr in extra_arrs.items():
                        val = arr[t, c_idx]
                        if np.isfinite(val):
                            row_ctx[k] = float(val)
                    should_exit, exit_reason = exit_callback(pos, dt, row_ctx)
                if should_exit:
                    pending_sells[sym] = exit_reason or "止损/止盈"
                elif (
                    cfg.partial_take_profit_pct is not None
                    and not pos.partial_taken
                    and sym not in pending_partial_sells
                    and (cl / max(pos.entry_signal_close, 1e-6) - 1.0) >= cfg.partial_take_profit_pct
                ):
                    pending_partial_sells[sym] = f"浮盈满{cfg.partial_take_profit_pct*100:.0f}%分批锁利半仓"

        # 4b) 机会成本缓冲换仓：满仓时若最弱老持仓持满最短天数且滞涨，而新候选显著更强则次日开盘置换
        if (
            cfg.replace_score_margin is not None
            and len(positions) >= cfg.max_positions
            and len(pending_sells) == 0
        ):
            cur_scores = score_arr[t]
            valid_cands = [
                (float(cur_scores[idx]), symbols[idx])
                for idx in np.where(np.isfinite(cur_scores) & (cur_scores > -1e9))[0]
                if symbols[idx] not in positions
            ]
            if valid_cands:
                best_new_score, _ = max(valid_cands, key=lambda x: x[0])
                weakest_sym = None
                weakest_score = float("inf")
                for sym, pos in positions.items():
                    if (t - pos.entry_idx) < cfg.replace_min_hold_days:
                        continue
                    c_idx = sym_to_col[sym]
                    cl_now = close_arr[t, c_idx]
                    # 仅对当前处于滞涨/微亏/回吐态（低于入场价*1.08）的老仓考虑置换，绝不误杀大牛主升浪
                    if np.isfinite(cl_now) and cl_now >= pos.entry_signal_close * 1.08:
                        continue
                    s_old = float(cur_scores[c_idx]) if np.isfinite(cur_scores[c_idx]) else 0.0
                    if s_old < weakest_score:
                        weakest_score = s_old
                        weakest_sym = sym
                if weakest_sym is not None and (best_new_score - weakest_score) >= cfg.replace_score_margin:
                    pending_sells[weakest_sym] = "机会成本置换(新候选显著领先)"

        total_eq_close = max(cash + close_holdings_val, 1e-6)
        nav_vals[t] = total_eq_close / cfg.initial_cash
        eq_exp_vals[t] = close_holdings_val / total_eq_close
        if cfg.idle_cash_mode == "gold_dividend_harbor" and (prev_harbor_alloc[0] + prev_harbor_alloc[1]) > 0:
            harbor_exp_vals[t] = cash / total_eq_close

    nav_series = pd.Series(nav_vals, index=dates, name=strategy_name)
    daily_returns = nav_series.pct_change().fillna(0.0)

    # 绩效与风险统计
    years = max((dates[-1] - dates[0]).days / 365.25, 1.0 / 12.0)
    tot_ret = float(nav_series.iloc[-1] - 1.0)
    cagr = float(nav_series.iloc[-1] ** (1.0 / years) - 1.0) if nav_series.iloc[-1] > 0 else -1.0
    mdd = float((nav_series / nav_series.cummax() - 1.0).min())
    calmar = float(cagr / abs(mdd)) if mdd < -1e-9 else 0.0
    sd = float(daily_returns.std(ddof=1))
    sharpe = float((daily_returns.mean() / sd) * math.sqrt(252.0)) if sd > 1e-12 else 0.0

    # 基准与相对净超额
    bench_nav: pd.Series | None = None
    bench_cagr = 0.0
    bench_tot = 0.0
    bench_mdd = 0.0
    excess_cagr = cagr
    info_ratio = 0.0
    bench_rets: pd.Series | None = None
    if bench_close is not None and len(bench_close) > 10:
        bc = bench_close.astype(float).reindex(dates).ffill().bfill()
        if bc.iloc[0] > 0:
            bench_nav = bc / bc.iloc[0]
            bench_rets = bench_nav.pct_change().fillna(0.0)
            bench_tot = float(bench_nav.iloc[-1] - 1.0)
            bench_cagr = float(bench_nav.iloc[-1] ** (1.0 / years) - 1.0) if bench_nav.iloc[-1] > 0 else -1.0
            bench_mdd = float((bench_nav / bench_nav.cummax() - 1.0).min())
            rel_wealth = float(nav_series.iloc[-1] / bench_nav.iloc[-1]) if bench_nav.iloc[-1] > 0 else 1.0
            excess_cagr = float(rel_wealth ** (1.0 / years) - 1.0) if rel_wealth > 0 else -1.0
            active = daily_returns - bench_rets
            te = float(active.std(ddof=1))
            info_ratio = float((active.mean() / te) * math.sqrt(252.0)) if te > 1e-12 else 0.0

    # 交易级统计 + 剔除最赚 Top 3 交易压力测试（盈利集中度防伪）
    wins = [tr.net_return for tr in trades if tr.net_return > 0]
    losses = [tr.net_return for tr in trades if tr.net_return <= 0]
    win_rate = len(wins) / len(trades) if trades else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    payoff = (avg_win / abs(avg_loss)) if avg_loss < 0 else 0.0
    avg_hold = float(np.mean([tr.holding_days for tr in trades])) if trades else 0.0

    avg_equity_yuan = float(np.mean(nav_vals) * cfg.initial_cash)
    annual_turnover = float((traded_notional_total / 2.0) / max(avg_equity_yuan, 1.0) / years)

    # 剔除最赚 Top 3 交易的利润贡献后的近似复利与胜率
    if len(trades) > 3:
        sorted_by_pnl = sorted(trades, key=lambda x: x.pnl_yuan, reverse=True)
        top3_pnl = sum(max(0.0, tr.pnl_yuan) for tr in sorted_by_pnl[:3])
        total_pos_pnl = sum(max(0.0, tr.pnl_yuan) for tr in trades)
        top3_share = float(top3_pnl / total_pos_pnl) if total_pos_pnl > 1e-6 else 0.0
        rem_trades = sorted_by_pnl[3:]
        ex_top3_wr = sum(1 for tr in rem_trades if tr.net_return > 0) / len(rem_trades)
        ex_top3_final_eq = max(1e-6, nav_series.iloc[-1] * cfg.initial_cash - top3_pnl)
        ex_top3_cagr = float((ex_top3_final_eq / cfg.initial_cash) ** (1.0 / years) - 1.0)
    else:
        top3_share = 1.0 if trades else 0.0
        ex_top3_wr = win_rate
        ex_top3_cagr = 0.0

    slices = (
        slice_performance_by_year_and_regime(daily_returns, bench_close)
        if bench_close is not None and len(bench_close) > 60
        else {"by_year": [], "by_regime": []}
    )
    audit = overfitting_risk_audit(daily_returns, bench_returns=bench_rets, n_trials=n_trials)

    avg_eq_exp = float(np.mean(eq_exp_vals))
    avg_hb_exp = float(np.mean(harbor_exp_vals))
    avg_cash_exp = max(0.0, 1.0 - avg_eq_exp - avg_hb_exp)

    metrics: dict[str, object] = {
        "cagr": round(cagr, 4),
        "bench_cagr": round(bench_cagr, 4),
        "excess_cagr": round(excess_cagr, 4),
        "total_return": round(tot_ret, 4),
        "bench_total_return": round(bench_tot, 4),
        "max_drawdown": round(mdd, 4),
        "bench_max_drawdown": round(bench_mdd, 4),
        "calmar": round(calmar, 2),
        "sharpe": round(sharpe, 2),
        "info_ratio": round(info_ratio, 2),
        "trades_count": len(trades),
        "win_rate": round(win_rate, 4),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "payoff_ratio": round(payoff, 2),
        "avg_holding_days": round(avg_hold, 1),
        "annual_turnover": round(annual_turnover, 2),
        "avg_equity_exposure": round(avg_eq_exp, 4),
        "avg_harbor_exposure": round(avg_hb_exp, 4),
        "avg_cash_exposure": round(avg_cash_exp, 4),
        "longest_underwater_days": _longest_underwater(nav_series),
        "blocked_buy_limit_up": int(blocked_buy_limit),
        "blocked_sell_limit_down": int(blocked_sell_limit),
        "ex_top3_trades_cagr": round(ex_top3_cagr, 4),
        "ex_top3_trades_win_rate": round(ex_top3_wr, 4),
        "top3_profit_share": round(top3_share, 4),
    }

    return PortfolioBacktestResult(
        strategy_name=strategy_name,
        plain_rule_desc=plain_rule_desc,
        config=cfg,
        nav_series=nav_series,
        daily_returns=daily_returns,
        bench_nav=bench_nav,
        trades=trades,
        metrics=metrics,
        by_year=slices["by_year"],
        by_regime=slices["by_regime"],
        overfit_audit=audit,
    )
