"""同源信号层（Single Source of Truth）：历史回测、每日漏斗、前向模拟共用同一套严格因果信号逻辑。

解决旧架构最大隐患“测的是一套、上线跑的却是另一套”：
1. 行业代表基金：历史回测与收盘漏斗共享同一套【板块内部成分股历史共振面板 + 趋势 + 离成本线 + 拥挤度 + 打分权重】；
2. A 股好生意个股：历史回测与收盘漏斗共享同一套【本地 PIT 盈利/现金流/高债大扩张排雷 + 活筹码 + 低波稳健 + 量价健康度 + 两步拿牛止盈规则】；
3. 支持注入自定义因子权重 `weights`，天然支持组件消融（Leave-One-Factor-Out）与等权基准对照。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .chip_trend import compute_live_chip_metrics
from .data_portal import DataPortal, SplitMode
from .portfolio_sim import OpenPosition


DEFAULT_SECTOR_WEIGHTS: dict[str, float] = {
    "resonance": 0.40,
    "near_cost": 0.25,
    "rel_strength": 0.25,
    "low_crowd": 0.10,
}

DEFAULT_STOCK_WEIGHTS: dict[str, float] = {
    "profit_ratio": 0.25,
    "chip_conc": 0.15,
    "low_vol": 0.30,
    "vol_health": 0.10,
    "rel_strength": 0.15,
    "biz_quality": 0.15,
}


def compute_sector_resonance_panel(
    portal: DataPortal,
    sector_funds: list[tuple[str, str, tuple[str, ...]]],
    *,
    split: SplitMode = "full",
    per_sector_top: int = 12,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """构建 18 个行业基金的日频历史【板块内部成分股站上20日均线共振面板】（零未来函数）。

    返回 (ratio_df, up_cnt_df, tot_cnt_df)，行列均为 Date × SectorETF。
    """
    fund_df = portal.load_latest_fundamentals_table()
    # 兼容：若最新静态表缺席，用本地 PIT 面板最近行业归属兜底
    if len(fund_df) == 0:
        pit = portal.load_pit_fundamentals(split=split)
        if len(pit) > 0:
            last_ind = pit.sort_values("decision_date").groupby("symbol").tail(1)
            fund_df = pd.DataFrame({
                "symbol": last_ind["symbol"],
                "industry": last_ind["industry"],
                "mktcap_yi": 100.0,
            })

    if len(fund_df) == 0:
        empty = pd.DataFrame()
        return empty, empty, empty

    sector_members: dict[str, list[str]] = {}
    all_reps: set[str] = set()
    for etf_sym, _, ind_tuple in sector_funds:
        mask = fund_df["industry"].isin(ind_tuple)
        sub = fund_df.loc[mask].sort_values("mktcap_yi", ascending=False).head(per_sector_top)
        syms = sub["symbol"].astype(str).tolist()
        sector_members[etf_sym] = syms
        all_reps.update(syms)

    # 批量加载成分股收盘价并计算各自是否站上20日均线（纯因果）
    above_ma20: dict[str, pd.Series] = {}
    for sym in sorted(all_reps):
        try:
            bars = portal.load_bars(sym, market="CN", split=split)
        except FileNotFoundError:
            continue
        if len(bars) < 25:
            continue
        cl = bars["close"].astype(float)
        ma20 = cl.rolling(20, min_periods=20).mean()
        above_ma20[sym] = (cl > ma20).where(ma20.notna())

    if not above_ma20:
        empty = pd.DataFrame()
        return empty, empty, empty

    stock_flag_df = pd.DataFrame(above_ma20).sort_index()
    ratio_cols: dict[str, pd.Series] = {}
    up_cols: dict[str, pd.Series] = {}
    tot_cols: dict[str, pd.Series] = {}

    for etf_sym, _, _ in sector_funds:
        cols = [s for s in sector_members.get(etf_sym, []) if s in stock_flag_df.columns]
        if not cols:
            continue
        sub_df = stock_flag_df[cols]
        tot = sub_df.notna().sum(axis=1).astype(float)
        up = sub_df.astype(float).fillna(0.0).sum(axis=1)
        ratio_cols[etf_sym] = (up / tot.replace(0.0, np.nan))
        up_cols[etf_sym] = up
        tot_cols[etf_sym] = tot

    return (
        pd.DataFrame(ratio_cols).sort_index(),
        pd.DataFrame(up_cols).sort_index(),
        pd.DataFrame(tot_cols).sort_index(),
    )


def build_sector_etf_signal_panels(
    panel: dict[str, pd.DataFrame],
    bench_close: pd.Series,
    *,
    resonance_ratio: pd.DataFrame | None = None,
    weights: dict[str, float] | None = None,
    require_resonance: bool = True,
    resonance_min: float = 0.50,
    max_dist_ma60: float = 0.12,
    max_crowd_pct: float = 0.85,
) -> dict[str, pd.DataFrame]:
    """向量化构造行业代表基金的同源【右侧起势 / 左侧拐头 / 防守位 / 退出标记】面板。"""
    w = {**DEFAULT_SECTOR_WEIGHTS, **(weights or {})}
    close = panel["close"].sort_index()
    high = panel["high"].reindex_like(close)
    low = panel["low"].reindex_like(close)
    vol = panel["volume"].reindex_like(close)
    amt = close * vol

    ma10 = close.rolling(10, min_periods=10).mean()
    ma20 = close.rolling(20, min_periods=20).mean()
    ema20 = close.ewm(span=20, adjust=False, min_periods=20).mean()
    ma60 = close.rolling(60, min_periods=60).mean()

    prev_c = close.shift(1)
    tr = np.maximum(
        (high - low).abs(),
        np.maximum((high - prev_c).abs(), (low - prev_c).abs()),
    )
    atr20 = tr.rolling(20, min_periods=20).mean()

    price_pct_2y = close.rolling(504, min_periods=180).rank(pct=True)
    high_1y = close.rolling(252, min_periods=120).max()
    drawdown_1y = close / high_1y - 1.0

    amt10 = amt.rolling(10, min_periods=10).mean()
    amt252 = amt.rolling(252, min_periods=100).mean()
    heat_ratio = amt10 / amt252.replace(0.0, np.nan)
    crowd_pct = heat_ratio.rolling(504, min_periods=120).rank(pct=True)

    ret20 = close / close.shift(20) - 1.0
    b_cl = bench_close.astype(float).reindex(close.index).ffill()
    b_ret20 = b_cl / b_cl.shift(20) - 1.0
    rs20 = ret20.sub(b_ret20, axis=0)
    dist_ma60 = close / ma60 - 1.0

    if resonance_ratio is not None and len(resonance_ratio) > 0:
        res_df = resonance_ratio.reindex(index=close.index, columns=close.columns)
    else:
        res_df = pd.DataFrame(np.nan, index=close.index, columns=close.columns)

    # 右侧起势同源硬条件（与 fund_evaluator.evaluate_all_fund_opportunities 完全逐条一致）
    trend_up = (
        (close > ma20)
        & (close >= ma60 * 0.995)
        & (ma20 > ma20.shift(5))
        & (ma60 >= ma60.shift(5) * 0.996)
    )
    # 历史早期某板块尚未有本地成分股覆盖时(res_df is NaN)不误杀，有覆盖则严格校验 >= resonance_min
    res_ok = (~require_resonance) | res_df.isna() | (res_df >= resonance_min)
    near_cost_ok = dist_ma60 <= max_dist_ma60
    not_crowded_ok = crowd_pct < max_crowd_pct
    right_mask = trend_up & res_ok & near_cost_ok & not_crowded_ok

    res_filled = res_df.fillna(0.50)
    near_score = (1.0 - dist_ma60.clip(lower=0.0) / max(max_dist_ma60, 0.01)).clip(0.0, 1.0)
    rs_score = np.tanh(rs20.fillna(0.0) * 5.0)
    crowd_score = (1.0 - crowd_pct.fillna(0.50)).clip(0.0, 1.0)

    raw_right_score = (
        w["resonance"] * res_filled
        + w["near_cost"] * near_score
        + w["rel_strength"] * rs_score
        + w["low_crowd"] * crowd_score
    )
    right_entry_scores = raw_right_score.where(right_mask)

    # 右侧同源出场：过热拥挤或乖离过大破 10 日线锁利；平时跌破 min(MA20, EMA20) - 0.55*ATR20 离场
    right_exit_flags = (
        (((crowd_pct >= 0.90) | (dist_ma60 >= 0.18)) & (close < ma10))
        | (close < np.minimum(ma20, ema20) - 0.55 * atr20)
    ).fillna(False)

    # 左侧深坑拐头同源条件
    left_res_ok = (~require_resonance) | res_df.isna() | (res_df >= 0.35)
    left_mask = (
        (drawdown_1y <= -0.16)
        & (price_pct_2y <= 0.35)
        & (close > ma20)
        & (ma20 >= ma20.shift(3) * 0.999)
        & (crowd_pct < 0.75)
        & left_res_ok
    )
    left_score = (
        0.40 * (-drawdown_1y).clip(0.0, 0.6)
        + 0.30 * (1.0 - price_pct_2y.fillna(0.5))
        + 0.30 * res_filled
    )
    left_entry_scores = left_score.where(left_mask)
    floor_20 = low.rolling(20, min_periods=15).min()
    left_exit_flags = (
        (((dist_ma60 >= 0.16) | (crowd_pct >= 0.90)) & (close < ma10))
        | (close < floor_20.shift(1) * 0.99)
        | (close < ma20 - 0.65 * atr20)
    ).fillna(False)

    # 简单旧办法对照：仅看站上 20 日均线
    plain_ma_mask = (close > ma20) & (ma20 > ma20.shift(1))
    plain_ma_scores = rs20.fillna(0.0).where(plain_ma_mask)
    plain_ma_exits = (~plain_ma_mask).fillna(False)

    stop_prices = np.minimum(ma20, ma60).where(ma20.notna(), ma20)

    return {
        "right_entry_scores": right_entry_scores,
        "right_raw_scores": raw_right_score,
        "right_exit_flags": right_exit_flags,
        "left_entry_scores": left_entry_scores,
        "left_exit_flags": left_exit_flags,
        "plain_ma_scores": plain_ma_scores,
        "plain_ma_exits": plain_ma_exits,
        "stop_prices": stop_prices,
        "ma10": ma10,
        "ma20": ma20,
        "ema20": ema20,
        "ma60": ma60,
        "atr20": atr20,
        "crowd_pct": crowd_pct,
        "dist_ma60": dist_ma60,
        "price_pct_2y": price_pct_2y,
        "drawdown_1y": drawdown_1y,
        "rs20": rs20,
        "resonance_ratio": res_df,
    }


def make_two_stage_stock_exit_callback(
    *,
    profit_unlock_pct: float = 0.15,
    poc_move_limit: float = 0.15,
    stage1_atr_mult: float = 0.55,
    stage2_protect_gain: float = 0.02,
):
    """同源【两步拿牛法】状态出场回调：回测引擎与单票智能提示卡共用同一套核心止盈止损规则。"""

    def _exit_rule(pos: OpenPosition, _dt: pd.Timestamp, ctx: dict[str, float]) -> tuple[bool, str]:
        cl = ctx.get("close", np.nan)
        ma20 = ctx.get("ma20", np.nan)
        ema20 = ctx.get("ema20", np.nan)
        ma60 = ctx.get("ma60", np.nan)
        atr20 = ctx.get("atr20", np.nan)
        poc = ctx.get("poc_price", np.nan)
        if not np.isfinite(cl):
            return False, ""

        # 1) 高位筹码大搬家后跌破新成本峰与 EMA20 -> 派发锁利
        if (
            np.isfinite(poc)
            and np.isfinite(ema20)
            and pos.entry_poc > 0
            and (poc > pos.entry_poc * (1.0 + poc_move_limit))
            and (cl < poc)
            and (cl < ema20)
        ):
            return True, "高位筹码派发破峰锁利"

        max_gain = pos.max_close / max(pos.entry_signal_close, 1e-6) - 1.0
        base_unmoved = (not np.isfinite(poc)) or (pos.entry_poc <= 0) or (poc <= pos.entry_poc * (1.0 + poc_move_limit))

        # 2) 第二步：已赚够 15% 且底部大部队未搬家 -> 放宽改守 60 日均线与保本线(+2%)，防洗盘拿主升浪
        if max_gain >= profit_unlock_pct and base_unmoved and np.isfinite(ma60):
            guard = max(ma60, pos.entry_signal_close * (1.0 + stage2_protect_gain))
            if cl < guard:
                return True, "第二步宽保护线(60日线/保本线)止盈"
            return False, ""

        # 3) 第一步：刚买进或底仓已松动 -> 严守 20 日均线缓冲带防深套
        if np.isfinite(ma20) and np.isfinite(ema20) and np.isfinite(atr20):
            if cl < min(ma20, ema20) - stage1_atr_mult * atr20:
                return True, "第一步20日成本线破位止损"
        return False, ""

    return _exit_rule


def build_stock_funnel_signal_panels(
    portal: DataPortal,
    symbols: list[str],
    *,
    split: SplitMode = "explore",
    weights: dict[str, float] | None = None,
    require_good_biz: bool = True,
    filter_reckless_debt: bool = True,
    quality_pct_min: float = 0.55,
) -> dict[str, object]:
    """构造与 `rank_top_candidates` 完全同源的 A 股日频信号面板（严格使用本地 PIT 基本面）。"""
    w = {**DEFAULT_STOCK_WEIGHTS, **(weights or {})}
    panel = portal.load_panel_bars(symbols, market="CN", split=split, min_rows=150)
    close = panel["close"]
    if close.empty:
        return {"panel": panel, "entry_scores": pd.DataFrame(), "raw_scores": pd.DataFrame()}

    dates = close.index
    valid_syms = list(close.columns)

    bench = portal.load_bars("510300.SS", market="CN", split=split)["close"].reindex(dates).ffill()
    b_ret20 = bench / bench.shift(20) - 1.0

    # PIT 基本面严格按 decision_date <= t 前向填充（杜绝用未来季报或静态最新表污染历史）
    pit = portal.load_stock_business_quality(split="full")
    pit_by_sym: dict[str, pd.DataFrame] = {}
    industry_map: dict[str, str] = {}
    if len(pit) > 0:
        for sym, grp in pit.groupby("symbol"):
            if sym in valid_syms:
                g = grp.sort_values("decision_date").drop_duplicates("decision_date", keep="last").set_index("decision_date")
                pit_by_sym[str(sym)] = g
                if "industry" in g.columns:
                    last_ind = str(g["industry"].dropna().iloc[-1]) if len(g["industry"].dropna()) else ""
                    if last_ind:
                        industry_map[str(sym)] = last_ind

    # 补充最新静态表中的行业名称（仅当 PIT 缺行业时作静态映射）
    fund_latest = portal.load_latest_fundamentals_table()
    if len(fund_latest) > 0 and "industry" in fund_latest.columns:
        for _, row in fund_latest.iterrows():
            s = str(row["symbol"])
            if s in valid_syms and s not in industry_map and pd.notna(row["industry"]):
                industry_map[s] = str(row["industry"])

    score_cols: dict[str, pd.Series] = {}
    raw_score_cols: dict[str, pd.Series] = {}
    stop_cols: dict[str, pd.Series] = {}
    poc_cols: dict[str, pd.Series] = {}
    ma20_cols: dict[str, pd.Series] = {}
    ema20_cols: dict[str, pd.Series] = {}
    ma60_cols: dict[str, pd.Series] = {}
    atr20_cols: dict[str, pd.Series] = {}
    plain_ma_score_cols: dict[str, pd.Series] = {}
    plain_ma_exit_cols: dict[str, pd.Series] = {}

    for sym in valid_syms:
        bars = pd.DataFrame({
            "open": panel["open"][sym],
            "high": panel["high"][sym],
            "low": panel["low"][sym],
            "close": panel["close"][sym],
            "volume": panel["volume"][sym],
        }).dropna(subset=["close", "high", "low", "volume"])
        if len(bars) < 150:
            continue
        if "turnover" in panel and sym in panel["turnover"].columns:
            bars["turnover"] = panel["turnover"][sym].reindex(bars.index)

        m = compute_live_chip_metrics(bars)
        cl = m["close"]
        ma20 = m["ma20"]
        ema20 = m["ema20"]
        ma60 = m["ma60"]
        atr20 = m["atr20"]
        poc = m["poc_price"]
        prof = m["profit_ratio"]
        over10 = m["overhead_near10"]
        conc = m["chip_conc90"]
        r20 = m["ret20"]

        ret_d = cl.pct_change()
        vol60 = ret_d.rolling(60, min_periods=25).std().fillna(0.025)
        low_vol_score = ((0.038 - vol60) / 0.025).clip(0.0, 1.0)

        # 向量化近20日涨时放量跌时缩量（与 rank_top_candidates 完全一致）
        v_ser = bars["volume"].astype(float)
        up_v = v_ser.where(ret_d > 0.0).rolling(20, min_periods=3).mean()
        dn_v = v_ser.where(ret_d <= 0.0).rolling(20, min_periods=3).mean()
        vol_ratio = (up_v / dn_v.clip(lower=1e-6)).clip(0.5, 2.5).fillna(1.0)
        vol_health = np.tanh((vol_ratio - 1.0) * 1.2).clip(lower=0.0)

        rs20 = r20 - b_ret20.reindex(m.index).ffill().fillna(0.0)

        # 对齐严格 PIT 基本面
        if sym in pit_by_sym:
            g = pit_by_sym[sym]
            idx_union = m.index.union(g.index)
            q_pct = g["quality_pct"].reindex(idx_union).sort_index().ffill().reindex(m.index)
            q_cfo = g["cfoa"].reindex(idx_union).sort_index().ffill().reindex(m.index)
            reckless = (
                g["reckless_debt"].astype(float).reindex(idx_union).sort_index().ffill().reindex(m.index).fillna(0.0) > 0.5
                if "reckless_debt" in g.columns
                else pd.Series(False, index=m.index)
            )
            has_pit = True
        else:
            q_pct = pd.Series(np.nan, index=m.index)
            q_cfo = pd.Series(np.nan, index=m.index)
            reckless = pd.Series(False, index=m.index)
            has_pit = False

        ma_trend_ok = (
            (cl > ma20)
            & (ma20 > ma60 * 0.985)
            & (ma20 > ma20.shift(5))
            & (ma60 >= ma60.shift(5) * 0.995)
        )
        chip_clean_ok = (cl >= poc) & (prof >= 0.70) & (over10 <= 0.22)
        not_overext = (cl / ma60 - 1.0) < 0.30

        if require_good_biz:
            biz_ok = has_pit & q_pct.notna() & (q_pct >= quality_pct_min) & (q_cfo.isna() | (q_cfo > 0.0))
        else:
            biz_ok = pd.Series(True, index=m.index)
        if filter_reckless_debt:
            biz_ok = biz_ok & (~reckless)

        biz_bonus = q_pct.fillna(0.5)
        raw_score = (
            w["profit_ratio"] * prof.fillna(0.0)
            + w["chip_conc"] * (1.0 - conc.fillna(0.4) * 2.5).clip(lower=0.0)
            + w["low_vol"] * low_vol_score
            + w["vol_health"] * vol_health
            + w["rel_strength"] * np.tanh(rs20.fillna(0.0) * 2.2)
            + w["biz_quality"] * biz_bonus
        )
        eligible = ma_trend_ok & chip_clean_ok & not_overext & biz_ok

        raw_score_cols[sym] = raw_score.reindex(dates)
        score_cols[sym] = raw_score.where(eligible).reindex(dates)
        stop_cols[sym] = np.minimum(ma20, poc).reindex(dates)
        poc_cols[sym] = poc.reindex(dates)
        ma20_cols[sym] = ma20.reindex(dates)
        ema20_cols[sym] = ema20.reindex(dates)
        ma60_cols[sym] = ma60.reindex(dates)
        atr20_cols[sym] = atr20.reindex(dates)

        plain_ok = (cl > ma20) & (ma20 > ma20.shift(1))
        plain_ma_score_cols[sym] = rs20.fillna(0.0).where(plain_ok).reindex(dates)
        plain_ma_exit_cols[sym] = (~plain_ok).fillna(False).reindex(dates)

    return {
        "panel": panel,
        "bench_close": bench,
        "industry_map": industry_map,
        "pit_start_date": pit["decision_date"].min() if len(pit) > 0 else None,
        "entry_scores": pd.DataFrame(score_cols, index=dates),
        "raw_scores": pd.DataFrame(raw_score_cols, index=dates),
        "stop_prices": pd.DataFrame(stop_cols, index=dates),
        "poc_prices": pd.DataFrame(poc_cols, index=dates),
        "ma20": pd.DataFrame(ma20_cols, index=dates),
        "ema20": pd.DataFrame(ema20_cols, index=dates),
        "ma60": pd.DataFrame(ma60_cols, index=dates),
        "atr20": pd.DataFrame(atr20_cols, index=dates),
        "plain_ma_scores": pd.DataFrame(plain_ma_score_cols, index=dates),
        "plain_ma_exits": pd.DataFrame(plain_ma_exit_cols, index=dates),
    }
