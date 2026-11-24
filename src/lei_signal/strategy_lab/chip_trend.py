"""换手衰减活筹码峰（Active Chip Cost Profile）+ 均线成本趋势引擎与尖子生漏斗。

金融含义（拒绝没有经济逻辑的几何参数凑数）：
1. 为什么旧版 120 日固定框筹码分布不管用？
   旧版把 119 天前早就换手卖光的老成交量和昨天同等看待，到了第 121 天又突然清零。
2. 真实市场里的【活筹码】怎么动？
   每天新成交的量落在当天价格区间（向收盘重心聚集），同时场内老筹码随着当天的换手强度自然衰减：
   放巨量换手 = 老筹码大量转移给新买家（成本搬家快）；极度缩量 = 场内筹码锁仓不动（成本保留久）。
3. 凭什么靠【筹码峰 + 均线】赚钱、靠什么保住利润？
   - 买点逻辑（上无套牢大山 + 脚踩成本大本营 + 平均成本抬升）：
     股价站稳主筹码峰（全场最大持仓成本区）上方，场内获利盘 >= 80%（上方套牢盘已洗净），
     同时 20/60 日均线成本向上——往下有获利盘/新主力成本垫底，往上无解套抛压，拉升阻力最小。
   - 卖点保利润逻辑（解决大跌吐回利润痛点）：
     ① 趋势破位走人：跌破 20 日均线与主筹码峰缓冲带；
     ② 高位筹码派发/乖离锁利：大涨后低位筹码搬家到高位，一旦跌破高位新筹码峰（高位接盘资金集体变套牢盘），
        或者短期暴涨偏离 60 日均线过远后破 10 日线，立刻兑现锁住整段波段利润，绝不坐电梯回原点。
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from typing import Literal
from .data_portal import ASSET_NAMES, DataPortal, ETF_NAMES, SplitMode


@dataclass(frozen=True)
class StrategyLedgerSummary:
    strategy_name: str
    plain_rule_desc: str
    trades_count: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    payoff_ratio: float
    cagr: float
    max_drawdown: float
    calmar: float
    avg_holding_days: float
    exposure_pct: float


def compute_live_chip_metrics(
    bars: pd.DataFrame,
    *,
    grid_bins: int = 120,
    base_turnover_decay: float = 0.045,
) -> pd.DataFrame:
    """严格因果（逐日递推、零未来函数）计算换手衰减活筹码峰与均线成本特征。"""
    df = bars.copy()
    c = df["close"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    v = df["volume"].to_numpy(dtype=float)
    has_real_turnover = "turnover" in df.columns
    turn_raw = pd.to_numeric(df["turnover"], errors="coerce").to_numpy(dtype=float) if has_real_turnover else None
    n = len(df)

    out = pd.DataFrame(index=df.index)
    s_close = pd.Series(c, index=df.index)
    out["close"] = s_close
    out["ma10"] = s_close.rolling(10, min_periods=10).mean()
    out["ma20"] = s_close.rolling(20, min_periods=20).mean()
    out["ema20"] = s_close.ewm(span=20, adjust=False, min_periods=20).mean()
    out["ma60"] = s_close.rolling(60, min_periods=60).mean()

    prev_c = s_close.shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_c).abs(),
            (df["low"] - prev_c).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr20"] = tr.rolling(20, min_periods=20).mean()
    vol_ma60 = pd.Series(v, index=df.index).rolling(60, min_periods=20).mean().to_numpy()

    profit_ratio = np.full(n, np.nan)
    poc_price = np.full(n, np.nan)
    chip_conc90 = np.full(n, np.nan)
    overhead_near10 = np.full(n, np.nan)

    # 使用对数价格自适应网格，避免十倍股或长周期价格跨度失真；网格只随历史极值单向外扩（严格无未来函数）
    valid_init = np.where((l > 0) & (h > 0) & np.isfinite(c))[0]
    if len(valid_init) < 60:
        out["profit_ratio"] = profit_ratio
        out["poc_price"] = poc_price
        out["chip_conc90"] = chip_conc90
        out["overhead_near10"] = overhead_near10
        return out

    i0 = int(valid_init[0])
    p_min = max(l[i0] * 0.5, 1e-4)
    p_max = h[i0] * 2.0
    grid = np.geomspace(p_min, p_max, grid_bins)
    chips = np.zeros(grid_bins, dtype=float)

    for t in range(i0, n):
        if not (np.isfinite(c[t]) and h[t] > 0 and l[t] > 0):
            continue
        # 若价格创出当前网格边界，先把旧筹码重映射到外扩后的新网格（纯历史操作）
        if l[t] <= grid[1] or h[t] >= grid[-2]:
            new_min = min(grid[0], max(l[t] * 0.6, 1e-4))
            new_max = max(grid[-1], h[t] * 1.8)
            new_grid = np.geomspace(new_min, new_max, grid_bins)
            if chips.sum() > 0:
                new_chips = np.zeros(grid_bins, dtype=float)
                idx_map = np.clip(np.searchsorted(new_grid, grid), 0, grid_bins - 1)
                np.add.at(new_chips, idx_map, chips)
                chips = new_chips
            grid = new_grid

        # 当日换手衰减率：若行情含真实流通股换手率则优先使用，否则退化为相对成交量代理
        if turn_raw is not None and np.isfinite(turn_raw[t]) and turn_raw[t] > 0:
            # 兼容百分比口径（如 3.5 表示 3.5%）与小数口径（如 0.035）
            t_rate = turn_raw[t] / 100.0 if turn_raw[t] > 0.5 else turn_raw[t]
            alpha = float(np.clip(t_rate, 0.005, 0.35))
        else:
            v_ref = vol_ma60[t] if (np.isfinite(vol_ma60[t]) and vol_ma60[t] > 0) else v[t]
            rel_vol = (v[t] / v_ref) if (v_ref and v_ref > 0) else 1.0
            alpha = float(np.clip(base_turnover_decay * rel_vol, 0.008, 0.25))

        # 当日成交量按三角核聚集在典型成交重心 (H + L + 2*C)/4
        pivot = 0.25 * (h[t] + l[t] + 2.0 * c[t])
        mask = (grid >= l[t] * 0.997) & (grid <= h[t] * 1.003)
        if not np.any(mask):
            nearest = int(np.argmin(np.abs(grid - c[t])))
            day_dist = np.zeros(grid_bins, dtype=float)
            day_dist[nearest] = 1.0
        else:
            half_span = max(h[t] - l[t], c[t] * 0.005)
            tri = np.maximum(0.0, 1.0 - np.abs(grid - pivot) / half_span) * mask
            if tri.sum() <= 0:
                tri = mask.astype(float)
            day_dist = tri / tri.sum()

        if chips.sum() <= 0:
            chips = day_dist.copy()
        else:
            chips = (1.0 - alpha) * chips + alpha * day_dist
            chips /= chips.sum()

        if t >= i0 + 50:
            profit_ratio[t] = float(chips[grid <= c[t]].sum())
            poc_idx = int(np.argmax(chips))
            poc_price[t] = float(grid[poc_idx])
            near_upper = (grid > c[t]) & (grid <= c[t] * 1.10)
            overhead_near10[t] = float(chips[near_upper].sum())

            cdf = np.cumsum(chips)
            p05 = float(np.interp(0.05, cdf, grid))
            p95 = float(np.interp(0.95, cdf, grid))
            chip_conc90[t] = (p95 - p05) / max(p95 + p05, 1e-8)

    out["profit_ratio"] = profit_ratio
    out["poc_price"] = poc_price
    out["chip_conc90"] = chip_conc90
    out["overhead_near10"] = overhead_near10
    out["ret20"] = s_close / s_close.shift(20) - 1.0
    out["ret60"] = s_close / s_close.shift(60) - 1.0
    return out


def _simulate_single_asset_trades(
    open_px: np.ndarray,
    close_px: np.ndarray,
    signal_on: np.ndarray,
    cost_oneway: float = 0.0012,
) -> tuple[np.ndarray, list[tuple[float, int]]]:
    """单标的次日开盘成交逐笔算账（返回净值序列与每笔完整交易收益率/持仓天数）。"""
    n = len(close_px)
    nav = np.ones(n, dtype=float)
    holding = False
    entry_open = 0.0
    entry_idx = 0
    cash = 1.0
    shares = 0.0
    trades: list[tuple[float, int]] = []

    for t in range(1, n):
        want_hold = bool(signal_on[t - 1])  # 昨天收盘决定今天开盘动作
        op = open_px[t]
        cl = close_px[t]
        if not (np.isfinite(op) and op > 0 and np.isfinite(cl) and cl > 0):
            nav[t] = nav[t - 1]
            continue

        if not holding and want_hold:
            fee = cash * cost_oneway
            invest = cash - fee
            shares = invest / op
            cash = 0.0
            holding = True
            entry_open = op * (1.0 + cost_oneway)
            entry_idx = t
        elif holding and not want_hold:
            gross = shares * op
            net = gross * (1.0 - cost_oneway)
            cash = net
            shares = 0.0
            holding = False
            trade_ret = (op * (1.0 - cost_oneway)) / entry_open - 1.0
            trades.append((float(trade_ret), int(t - entry_idx)))

        nav[t] = cash + shares * cl

    return nav, trades


def compare_chip_ma_strategies_detailed(
    portal: DataPortal,
    symbols: list[str] | None = None,
    *,
    split: SplitMode = "explore",
    cost_oneway: float = 0.0012,
    n_trials: int = 1,
):
    """在核心宽基与行业 ETF 池上，基于真实单账户资金账本对比筹码峰+均线战法（含闲钱避风港对照）。"""
    from .portfolio_sim import PortfolioSimConfig, simulate_real_portfolio

    if symbols is None:
        symbols = [
            "510300.SS", "510500.SS", "159915.SZ", "588000.SS",
            "512480.SS", "515880.SS", "512010.SS", "159928.SZ",
            "512400.SS", "512660.SS", "512890.SS", "513100.SS",
        ]

    panel = portal.load_panel_bars(symbols, market="CN", split=split, min_rows=200)
    close = panel["close"]
    if close.empty:
        return []
    dates = close.index
    valid_syms = list(close.columns)

    bench_close = portal.load_bars("510300.SS", market="CN", split=split)["close"].reindex(dates).ffill()
    inds = portal.load_all_market_indicators(split=split)
    b50_ser = inds["cn-breadth-b50"].series.reindex(dates).ffill(limit=5) if "cn-breadth-b50" in inds else pd.Series(np.nan, index=dates)
    erp_ser = inds["cn-erp"].series if "cn-erp" in inds else pd.Series(dtype=float)
    erp_pct_ser = erp_ser.rolling(1260, min_periods=180).rank(pct=True).reindex(dates).ffill(limit=10) if len(erp_ser) else pd.Series(np.nan, index=dates)

    # 闲钱过渡避风港行情（黄金 + 红利低波）
    harbor_bars: dict[str, pd.DataFrame] = {}
    for key, hsym in (("gold", "518850.SS"), ("dividend", "512890.SS")):
        try:
            harbor_bars[key] = portal.load_bars(hsym, market="CN", split=split)
        except FileNotFoundError:
            pass

    bh_scores = pd.DataFrame(1.0, index=dates, columns=valid_syms)
    bh_exits = pd.DataFrame(False, index=dates, columns=valid_syms)

    ma_scores_d: dict[str, pd.Series] = {}
    ma_exits_d: dict[str, pd.Series] = {}
    fort_scores_d: dict[str, pd.Series] = {}
    fort_exits_d: dict[str, pd.Series] = {}
    fort_macro_scores_d: dict[str, pd.Series] = {}
    fort_macro_exits_d: dict[str, pd.Series] = {}
    stop_d: dict[str, pd.Series] = {}
    poc_d: dict[str, pd.Series] = {}

    for sym in valid_syms:
        bars = pd.DataFrame({
            "open": panel["open"][sym], "high": panel["high"][sym],
            "low": panel["low"][sym], "close": panel["close"][sym],
            "volume": panel["volume"][sym],
        }).dropna(subset=["close", "high", "low", "volume"])
        if len(bars) < 150:
            continue
        m = compute_live_chip_metrics(bars)
        cl, ma20, ema20, ma60, atr = m["close"], m["ma20"], m["ema20"], m["ma60"], m["atr20"]
        poc, prof, r20 = m["poc_price"], m["profit_ratio"], m["ret20"]

        ma_ok = (cl > ma20) & (ma20 > ma20.shift(1))
        ma_scores_d[sym] = r20.fillna(0.0).where(ma_ok).reindex(dates)
        ma_exits_d[sym] = (~ma_ok).fillna(False).reindex(dates)

        ma20_up = (cl > ma20) & (ma20 > ma20.shift(2))
        near_fortress = (cl >= poc) & ((cl / poc - 1.0) <= 0.10) & (prof >= 0.60)
        trend_rejoin = ma20_up & (ma20 > ma60) & (prof >= 0.80) & ((cl / ma20 - 1.0) <= 0.05)
        fort_ok = ma20_up & (near_fortress | trend_rejoin)
        fort_score = (0.50 * prof.fillna(0.0) + 0.50 * np.tanh(r20.fillna(0.0) * 3.0))

        fort_scores_d[sym] = fort_score.where(fort_ok).reindex(dates)
        fort_exits_d[sym] = (cl < np.minimum(ma20, ema20) - 0.55 * atr).fillna(False).reindex(dates)

        b50_al = b50_ser.reindex(m.index)
        erp_al = erp_pct_ser.reindex(m.index)
        overheated = b50_al.notna() & (b50_al > 80.0)
        expensive = erp_al.notna() & (erp_al < 0.15) & (prof < 0.80)
        tight_mode = (b50_al.notna() & (b50_al > 82.0)) | (erp_al.notna() & (erp_al < 0.15))
        buf = np.where(tight_mode, 0.15 * atr, 0.55 * atr)
        fort_macro_scores_d[sym] = fort_score.where(fort_ok & (~overheated) & (~expensive)).reindex(dates)
        fort_macro_exits_d[sym] = (cl < np.minimum(ma20, ema20) - buf).fillna(False).reindex(dates)

        stop_d[sym] = np.minimum(ma20, poc).reindex(dates)
        poc_d[sym] = poc.reindex(dates)

    base_cfg = PortfolioSimConfig(
        max_positions=4,
        max_per_industry=0,
        max_single_weight=0.25,
        risk_budget_per_trade=0.012,
        cost_buy=cost_oneway,
        cost_sell=cost_oneway,
        idle_cash_mode="cash",
    )
    bh_cfg = PortfolioSimConfig(
        max_positions=len(valid_syms),
        max_per_industry=0,
        max_single_weight=1.0 / max(1, len(valid_syms)),
        risk_budget_per_trade=None,
        cost_buy=cost_oneway,
        cost_sell=cost_oneway,
        idle_cash_mode="cash",
    )
    harbor_cfg = PortfolioSimConfig(
        max_positions=4,
        max_per_industry=0,
        max_single_weight=0.25,
        risk_budget_per_trade=0.012,
        cost_buy=cost_oneway,
        cost_sell=cost_oneway,
        idle_cash_mode="gold_dividend_harbor",
    )
    stops_df = pd.DataFrame(stop_d, index=dates)
    pocs_df = pd.DataFrame(poc_d, index=dates)

    runs = [
        ("一直死拿不动(等权全池)", "真实资金等额买入全池一直拿着不动", bh_scores, bh_exits, bh_cfg),
        ("普通20日均线买卖(限4只)", "站上20日线买、跌破卖，最多拿4只，空仓留现金", pd.DataFrame(ma_scores_d, index=dates), pd.DataFrame(ma_exits_d, index=dates), base_cfg),
        ("贴近筹码峰起跳+风险预算", "贴近主筹码峰起跳买+顺20日线拿主升浪，单笔风险<=1.2%", pd.DataFrame(fort_scores_d, index=dates), pd.DataFrame(fort_exits_d, index=dates), base_cfg),
        ("贴近筹码峰+大盘过热保护", "同上，外加全A过热(>80%)或ERP极贵时收紧保护", pd.DataFrame(fort_macro_scores_d, index=dates), pd.DataFrame(fort_macro_exits_d, index=dates), base_cfg),
        ("★筹码峰+过热保护+闲钱避风港", "同上，空仓闲钱交由稳在60日线上的黄金与红利低波过渡", pd.DataFrame(fort_macro_scores_d, index=dates), pd.DataFrame(fort_macro_exits_d, index=dates), harbor_cfg),
    ]

    results = []
    for name, desc, sc, ex, cfg in runs:
        results.append(
            simulate_real_portfolio(
                strategy_name=name,
                plain_rule_desc=desc,
                panel=panel,
                entry_scores=sc,
                exit_flags=ex,
                stop_prices=stops_df,
                poc_prices=pocs_df,
                bench_close=bench_close,
                harbor_bars=harbor_bars,
                config=cfg,
                n_trials=n_trials,
            )
        )
    return results


def compare_chip_ma_strategies(
    portal: DataPortal,
    symbols: list[str] | None = None,
    *,
    split: SplitMode = "explore",
    cost_oneway: float = 0.0012,
) -> list[StrategyLedgerSummary]:
    """在核心宽基与代表性行业 ETF 池上，基于真实资金组合账本对比进出场规则（向后兼容旧摘要返回）。"""
    return [r.to_ledger_summary() for r in compare_chip_ma_strategies_detailed(portal, symbols, split=split, cost_oneway=cost_oneway)]


def compare_stock_strategies_detailed(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    cost_buy: float = 0.0008,
    cost_sell: float = 0.0018,  # A股个股卖出含印花税与滑点
    n_trials: int = 1,
):
    """基于本地 PIT 财报与与生产漏斗同源的信号面板，在真实单账户账本上验证 A 股好生意+两步拿牛法。"""
    from .portfolio_sim import PortfolioSimConfig, simulate_real_portfolio
    from .signals import build_stock_funnel_signal_panels, make_two_stage_stock_exit_callback

    stocks = portal.list_cn_stocks()
    if not stocks:
        return []

    sig_good = build_stock_funnel_signal_panels(
        portal, stocks, split=split, require_good_biz=True, filter_reckless_debt=True
    )
    panel = sig_good["panel"]
    close = panel["close"]
    if close.empty:
        return []

    sig_all = build_stock_funnel_signal_panels(
        portal, list(close.columns), split=split, require_good_biz=False, filter_reckless_debt=False
    )

    # 严格对齐共同 PIT 生效起点，杜绝“有PIT组在早期无财报期静默空仓、无PIT组多跑两年”的不公平对比
    pit_start = sig_good.get("pit_start_date")
    if pit_start is not None and pd.notna(pit_start):
        common_start = pd.Timestamp(pit_start)
        if common_start > close.index[0] and int((close.index >= common_start).sum()) >= 120:
            panel = {k: v.loc[v.index >= common_start] for k, v in panel.items()}
            close = panel["close"]
            for d_obj in (sig_good, sig_all):
                for key in ("entry_scores", "raw_scores", "stop_prices", "poc_prices", "ma20", "ema20", "ma60", "atr20", "plain_ma_scores", "plain_ma_exits"):
                    if key in d_obj and isinstance(d_obj[key], pd.DataFrame):
                        d_obj[key] = d_obj[key].loc[d_obj[key].index >= common_start]
                if "bench_close" in d_obj and isinstance(d_obj["bench_close"], pd.Series):
                    d_obj["bench_close"] = d_obj["bench_close"].loc[d_obj["bench_close"].index >= common_start]

    dates = close.index
    valid_syms = list(close.columns)
    bench_close = sig_good["bench_close"]
    ind_map = sig_good["industry_map"]

    harbor_bars: dict[str, pd.DataFrame] = {}
    for key, hsym in (("gold", "518850.SS"), ("dividend", "512890.SS")):
        try:
            harbor_bars[key] = portal.load_bars(hsym, market="CN", split=split)
        except FileNotFoundError:
            pass

    bh_scores = pd.DataFrame(1.0, index=dates, columns=valid_syms)
    bh_exits = pd.DataFrame(False, index=dates, columns=valid_syms)
    stage1_only_exit = (
        close < np.minimum(sig_good["ma20"], sig_good["ema20"]) - 0.55 * sig_good["atr20"]
    ).fillna(False)
    two_stage_cb = make_two_stage_stock_exit_callback()
    extra_feats = {
        "ma20": sig_good["ma20"],
        "ema20": sig_good["ema20"],
        "ma60": sig_good["ma60"],
        "atr20": sig_good["atr20"],
    }

    bh_cfg = PortfolioSimConfig(
        max_positions=min(20, len(valid_syms)),
        max_per_industry=0,
        max_single_weight=1.0 / max(1, min(20, len(valid_syms))),
        risk_budget_per_trade=None,
        cost_buy=cost_buy,
        cost_sell=cost_sell,
    )
    stock_cfg = PortfolioSimConfig(
        max_positions=6,
        max_per_industry=2,
        max_single_weight=0.18,
        risk_budget_per_trade=0.012,
        cost_buy=cost_buy,
        cost_sell=cost_sell,
        idle_cash_mode="cash",
    )
    stock_harbor_cfg = PortfolioSimConfig(
        max_positions=6,
        max_per_industry=2,
        max_single_weight=0.18,
        risk_budget_per_trade=0.012,
        cost_buy=cost_buy,
        cost_sell=cost_sell,
        idle_cash_mode="gold_dividend_harbor",
    )

    return [
        simulate_real_portfolio(
            strategy_name="个股等权死拿不动",
            plain_rule_desc="池内股票分散买入一直拿着不动（真实成本）",
            panel=panel,
            entry_scores=bh_scores,
            exit_flags=bh_exits,
            industry_map=ind_map,
            bench_close=bench_close,
            config=bh_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="不挑生意只看20日均线",
            plain_rule_desc="不看财报与排雷，站上20日线按强度买前6只，破线卖",
            panel=panel,
            entry_scores=sig_good["plain_ma_scores"],
            exit_flags=sig_good["plain_ma_exits"],
            stop_prices=sig_good["stop_prices"],
            industry_map=ind_map,
            bench_close=bench_close,
            config=stock_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="不挑生意但看同源筹码+低波",
            plain_rule_desc="同源筹码低波量价排序(同业<=2只)，但不做PIT好生意与高债排雷",
            panel=panel,
            entry_scores=sig_all["entry_scores"],
            exit_flags=stage1_only_exit,
            stop_prices=sig_good["stop_prices"],
            poc_prices=sig_good["poc_prices"],
            industry_map=ind_map,
            bench_close=bench_close,
            config=stock_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="好生意排雷+破20日线即卖",
            plain_rule_desc="本地PIT好生意+高债排雷+同源低波筹码排序(限6只/同业<=2)，破20日线即卖",
            panel=panel,
            entry_scores=sig_good["entry_scores"],
            exit_flags=stage1_only_exit,
            stop_prices=sig_good["stop_prices"],
            poc_prices=sig_good["poc_prices"],
            industry_map=ind_map,
            bench_close=bench_close,
            config=stock_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="★同源好生意+两步拿牛法",
            plain_rule_desc="与生产漏斗100%同源打分+PIT排雷+两步拿牛止盈(满15%且底峰未移改守60日线)",
            panel=panel,
            entry_scores=sig_good["entry_scores"],
            exit_callback=two_stage_cb,
            stop_prices=sig_good["stop_prices"],
            poc_prices=sig_good["poc_prices"],
            extra_features=extra_feats,
            industry_map=ind_map,
            bench_close=bench_close,
            config=stock_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="★同源两步拿牛+闲钱避风港",
            plain_rule_desc="同上，叠加空仓闲钱交由黄金/红利低波稳态过渡池",
            panel=panel,
            entry_scores=sig_good["entry_scores"],
            exit_callback=two_stage_cb,
            stop_prices=sig_good["stop_prices"],
            poc_prices=sig_good["poc_prices"],
            extra_features=extra_feats,
            industry_map=ind_map,
            bench_close=bench_close,
            harbor_bars=harbor_bars,
            config=stock_harbor_cfg,
            n_trials=n_trials,
        ),
    ]


def compare_stock_quality_chip_strategies(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    cost_oneway: float = 0.0015,
) -> list[StrategyLedgerSummary]:
    """在 A 股个股池上使用本地 PIT 财报与真实资金账本验证好生意+两步拿牛法（向后兼容旧摘要返回）。"""
    return [
        r.to_ledger_summary()
        for r in compare_stock_strategies_detailed(
            portal, split=split, cost_buy=min(cost_oneway, 0.0010), cost_sell=max(cost_oneway, 0.0015)
        )
    ]


def rank_top_candidates(
    portal: DataPortal,
    *,
    top_n: int = 10,
    pool: Literal["etf", "leader", "small_giant", "stock"] = "etf",
    split: SplitMode = "full",
    max_per_industry: int = 2,
) -> list[dict[str, object]]:
    """收盘‘前 10 名尖子生漏斗’：支持【场内基金】【各行业真龙头(300亿+)】【细分行业小巨人(80~300亿)】分池筛选。

    结合第 3 轮跨年验货升级：
    1. 淘汰纯追近 20 日猛涨的短线排序，改为优先挑选【近三月波动稳 + 涨时放量跌时缩量 + 刚站稳成本区】的稳健领涨股；
    2. 非金融个股自动剔除“年报总资产暴增超 35% 且负债率超 60%”的高债大扩张雷区；
    3. 同一行业最多入选 `max_per_industry` 只（默认 2 只），防止单一过热赛道霸榜集中踩踏。
    """
    bench = portal.load_bars("510300.SS", market="CN", split=split)["close"]
    latest_market_dt = bench.index[-1]
    b_ret20 = float(bench.iloc[-1] / bench.iloc[-21] - 1.0) if len(bench) > 21 else 0.0

    fund_table = portal.load_latest_fundamentals_table()
    fund_by_sym: dict[str, dict] = {}
    if len(fund_table) > 0:
        for _, r in fund_table.iterrows():
            fund_by_sym[str(r["symbol"])] = r.to_dict()

    # 若本地已有年报资产负债表缓存，自动筛掉高债盲目扩张雷区（金融/电力除外）
    reckless_debt_set: set[str] = set()
    bal_dir = portal.lab_home / "strategy_lab_bars/hist_capital_discipline"
    bal_files = sorted(bal_dir.glob("balance_*.parquet")) if bal_dir.exists() else []
    if bal_files:
        try:
            latest_bal = pd.read_parquet(bal_files[-1])
            bad_mask = (latest_bal["asset_growth_yoy"] > 35.0) & (latest_bal["debt_ratio"] > 60.0)
            reckless_debt_set = set(latest_bal.loc[bad_mask, "symbol"].astype(str).tolist())
        except Exception:
            reckless_debt_set = set()

    if pool == "etf":
        symbols = portal.list_cn_etfs()
    elif pool in ("leader", "small_giant") and len(fund_table) > 0:
        symbols = sorted(fund_table.loc[fund_table["tier"] == pool, "symbol"].astype(str).tolist())
    else:
        symbols = portal.list_cn_stocks()

    qual_latest: dict[str, tuple[float, float]] = {}
    if pool == "stock" and not fund_by_sym:
        qdf = portal.load_stock_business_quality(split=split)
        if len(qdf) > 0:
            last_q = qdf.sort_values("decision_date").groupby("symbol").tail(1)
            for _, row in last_q.iterrows():
                qual_latest[str(row["symbol"])] = (
                    float(row["quality_pct"]) if pd.notna(row["quality_pct"]) else np.nan,
                    float(row["cfoa"]) if pd.notna(row["cfoa"]) else np.nan,
                )

    candidates: list[dict[str, object]] = []
    for sym in symbols:
        try:
            bars = portal.load_bars(sym, market="CN", split=split)
        except FileNotFoundError:
            continue
        if len(bars) < 150:
            continue
        if (latest_market_dt - bars.index[-1]).days > 7:
            continue
        cn_name = portal.get_asset_name(sym)
        if "ST" in cn_name.upper() or "退" in cn_name:
            continue
        m = compute_live_chip_metrics(bars)
        last = m.iloc[-1]
        prev5 = m.iloc[-5]
        if pd.isna(last["poc_price"]) or pd.isna(last["ma60"]):
            continue

        biz_tag = ""
        biz_bonus = 0.0
        industry_cn = ""
        mktcap_yi = None
        if sym in fund_by_sym:
            finfo = fund_by_sym[sym]
            industry_cn = str(finfo.get("industry") or "")
            is_fin = any(k in industry_cn for k in ("银行", "保险", "证券", "电力"))
            if not is_fin and sym in reckless_debt_set:
                continue
            mktcap_val = float(finfo.get("mktcap_yi") or 0.0)
            mktcap_yi = round(mktcap_val, 0) if np.isfinite(mktcap_val) else None
            roe = float(finfo.get("roe") or 0.0)
            pyoy = float(finfo.get("profit_yoy") or 0.0)
            ocf = float(finfo.get("ocf_ps") or 0.0)
            ind_rk = int(finfo.get("ind_mktcap_rank") or 99)
            rk_str = f"（{industry_cn}市值第{ind_rk}）" if ind_rk <= 3 else f"（{industry_cn}）"
            biz_tag = (
                f"总市值 {mktcap_val:.0f}亿{rk_str}，三季报净资产回报 {roe:.1f}%、"
                f"净利同比 {pyoy:+.1f}%、每股经营现金流 {ocf:.2f}元；"
            )
            biz_bonus = 0.08 * min(roe / 15.0, 1.5) + 0.07 * float(np.tanh(pyoy / 30.0))
        elif pool == "stock" and sym in qual_latest:
            q_pct, q_cfo = qual_latest[sym]
            if np.isfinite(q_pct) and q_pct < 0.50:
                continue
            if np.isfinite(q_cfo) and q_cfo <= 0.0:
                continue
            if np.isfinite(q_pct):
                biz_tag = f"同行赚钱能力排前 {max(1, int(round((1.0 - q_pct)*100)))}%、经营现金流健康；"
                biz_bonus = 0.15 * q_pct

        cl = float(last["close"])
        ma20 = float(last["ma20"])
        ma60 = float(last["ma60"])
        poc = float(last["poc_price"])
        prof = float(last["profit_ratio"])
        over10 = float(last["overhead_near10"])
        conc = float(last["chip_conc90"])
        r20 = float(last["ret20"])

        ma_trend_ok = (cl > ma20 > ma60 * 0.985) and (ma20 > float(prev5["ma20"])) and (ma60 >= float(prev5["ma60"]) * 0.995)
        chip_clean_ok = (cl >= poc) and (prof >= 0.70) and (over10 <= 0.22)
        not_overextended = (cl / ma60 - 1.0) < (0.25 if pool == "etf" else 0.30)

        if not (ma_trend_ok and chip_clean_ok and not_overextended):
            continue

        # 低波动稳健度（60日日均波动率）+ 涨时放量跌时缩量（近20日量比）
        ret_ser = bars["close"].astype(float).pct_change()
        vol60_val = float(ret_ser.rolling(60, min_periods=25).std().iloc[-1])
        vol60 = vol60_val if np.isfinite(vol60_val) else 0.025
        low_vol_score = float(np.clip((0.038 - vol60) / 0.025, 0.0, 1.0))

        recent_r = ret_ser.iloc[-20:]
        recent_v = bars["volume"].astype(float).iloc[-20:]
        up_v = float(recent_v[recent_r > 0].mean()) if bool((recent_r > 0).any()) else 1.0
        dn_v = float(recent_v[recent_r <= 0].mean()) if bool((recent_r <= 0).any()) else 1.0
        vol_ratio = float(np.clip(up_v / max(dn_v, 1e-6), 0.5, 2.5))
        vol_health = float(np.tanh((vol_ratio - 1.0) * 1.2))

        rs20 = r20 - b_ret20
        score = (
            0.25 * prof
            + 0.15 * max(0.0, 1.0 - conc * 2.5)
            + 0.30 * low_vol_score
            + 0.10 * max(0.0, vol_health)
            + 0.15 * float(np.tanh(rs20 * 2.2))
            + biz_bonus
        )
        dist_to_poc = (cl / poc - 1.0) * 100.0
        stop_ref = round(min(ma20, poc), 3)
        clean_code = sym.split(".")[0]

        candidates.append(
            {
                "symbol": sym,
                "code": clean_code,
                "name": cn_name,
                "industry": industry_cn,
                "mktcap_yi": mktcap_yi,
                "as_of": str(m.index[-1].date()),
                "close": round(cl, 3),
                "main_chip_peak": round(poc, 3),
                "profit_chips_pct": f"{prof*100:.1f}%",
                "overhead_trapped_10pct": f"{over10*100:.1f}%",
                "vs_hs300_20d": f"{rs20*100:+.1f}%",
                "daily_vol_pct": round(vol60 * 100.0, 2),
                "stop_defense_price": stop_ref,
                "rank_score": round(float(score), 4),
                "plain_reason": (
                    f"{biz_tag}现价站在多数人成本价 {poc:.2f} 上方（高出 {dist_to_poc:.1f}%），"
                    f"场内 {prof*100:.0f}% 的人赚钱、头顶一成套牢卖压仅 {over10*100:.1f}%；"
                    f"近三月日均晃动 {vol60*100:.1f}%、20与60日均线同步向上，近一月跑赢大盘 {rs20*100:+.1f}%。保命参考价 {stop_ref}。"
                ),
            }
        )

    candidates.sort(key=lambda x: float(x["rank_score"]), reverse=True)
    if pool != "etf" and max_per_industry > 0:
        diversified: list[dict[str, object]] = []
        ind_counts: dict[str, int] = {}
        for cand in candidates:
            ind_key = str(cand.get("industry") or "").strip()
            if ind_key:
                if ind_counts.get(ind_key, 0) >= max_per_industry:
                    continue
                ind_counts[ind_key] = ind_counts.get(ind_key, 0) + 1
            diversified.append(cand)
            if len(diversified) >= top_n:
                break
        return diversified
    return candidates[:top_n]
