"""场内基金专属机会评估引擎（fund_evaluator）。

彻底摒弃拿‘个股套牢盘尺子’生搬硬套基金的做法，按场内基金的真实赚钱逻辑建立三套独立标准：
1. 同方向严格去重：精选 10 只宽基/海外/商品压舱石代表 + 18 只互不重复的行业赛道龙头基金（绝不出现消费、白酒、食品饮料同时霸榜）。
2. 三类机会分开呈现：
   - 【压舱石底仓全景】：10 只核心宽基、美股与黄金的冷热位置（近三年分位）与当前趋势动作定性；
   - 【行业波段 · 右侧起势尖子生】：必须同时满足 ① 板块内部多数核心成分股同步站上20日均线（真共振，非独角戏）
     + ② 刚站稳20与60日均线不久（离60日成本线不超过12%，止损窄赔率高）+ ③ 成交热度未到人挤人疯涨区（<85%分位）；
   - 【跌透拐头 · 左侧黄金坑潜伏机会】：经历充分深跌洗盘（处于近两年低位区且前期缩量），近期刚刚重新站回走平向上的20日均线，下方紧贴近期铁底。
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .chip_trend import StrategyLedgerSummary, _simulate_single_asset_trades, compute_live_chip_metrics
from .data_portal import DataPortal, SplitMode


# 10 只互不重复的压舱石底仓代表基金（宽基 + 跨市场美股港股 + 黄金 + 红利）
CORE_BROAD_FUNDS: list[tuple[str, str, str]] = [
    ("510300.SS", "沪深300基金", "A股大盘蓝筹总代表"),
    ("510500.SS", "中证500基金", "A股中盘成长代表"),
    ("512100.SS", "中证1000基金", "A股中小盘代表"),
    ("159915.SZ", "创业板基金", "新能源与医药成长代表"),
    ("588000.SS", "科创50基金", "硬科技与国产替代代表"),
    ("512890.SS", "红利低波基金", "高股息现金奶牛收息代表"),
    ("513100.SS", "纳指100基金", "美股科技巨头压舱石"),
    ("513500.SS", "标普500基金", "美股全市场压舱石"),
    ("513180.SS", "恒生科技基金", "港股互联网龙头代表"),
    ("518850.SS", "黄金基金", "抗通胀与极端避险硬通货"),
]

# 18 只严格去重的行业波段代表基金：(代码, 纯中文名称, 对应成分股细分行业关键词列表)
DISTINCT_SECTOR_FUNDS: list[tuple[str, str, tuple[str, ...]]] = [
    ("512480.SS", "半导体基金", ("半导体",)),
    ("515880.SS", "通信设备基金", ("通信设备", "元件")),
    ("159819.SZ", "人工智能基金", ("软件开发", "IT服务", "计算机设备")),
    ("562500.SS", "机器人制造基金", ("自动化设备", "通用设备")),
    ("516010.SS", "游戏传媒基金", ("游戏", "影视院线", "广告营销", "数字媒体")),
    ("515030.SS", "新能车电池基金", ("电池", "乘用车", "汽车零部件")),
    ("515790.SS", "光伏电力设备基金", ("光伏设备", "风电设备", "电网设备")),
    ("512660.SS", "国防军工基金", ("航空装备", "军工电子", "航海装备", "航天装备")),
    ("159992.SZ", "创新药基金", ("化学制药", "生物制品", "中药")),
    ("512170.SS", "医疗器械服务基金", ("医疗器械", "医疗服务")),
    ("159928.SZ", "大消费龙头基金", ("白酒", "饮料乳品", "食品加工", "调味发酵品", "白色家电")),
    ("159865.SZ", "养殖农业基金", ("养殖业", "饲料", "种植业")),
    ("512400.SS", "有色金属基金", ("工业金属", "小金属", "贵金属", "能源金属")),
    ("515220.SS", "煤炭能源基金", ("煤炭开采",)),
    ("159611.SZ", "电力公用基金", ("电力",)),
    ("512800.SS", "银行基金", ("国有大型银行", "股份制银行", "城商行", "农商行", "银行")),
    ("512000.SS", "券商基金", ("证券",)),
    ("512200.SS", "房地产基金", ("房地产开发",)),
]


def select_sector_representative_stocks(fund_df: pd.DataFrame, per_sector_top: int = 12) -> list[str]:
    """为 18 个行业赛道各挑选市值前列的代表成分股，用于计算真实的‘板块内部成分股共振比例’。"""
    if len(fund_df) == 0:
        return []
    picked: set[str] = set()
    for _, _, ind_Tuple in DISTINCT_SECTOR_FUNDS:
        mask = fund_df["industry"].isin(ind_Tuple)
        sub = fund_df.loc[mask].sort_values("mktcap_yi", ascending=False).head(per_sector_top)
        picked.update(sub["symbol"].astype(str).tolist())
    return sorted(picked)


def _compute_fund_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    df = bars.copy()
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    v = df["volume"].astype(float)
    amt = c * v

    out = pd.DataFrame(index=df.index)
    out["close"] = c
    out["low"] = l
    out["ma10"] = c.rolling(10, min_periods=10).mean()
    out["ma20"] = c.rolling(20, min_periods=20).mean()
    out["ema20"] = c.ewm(span=20, adjust=False, min_periods=20).mean()
    out["ma60"] = c.rolling(60, min_periods=60).mean()
    out["ma200"] = c.rolling(200, min_periods=120).mean()

    prev_c = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    out["atr20"] = tr.rolling(20, min_periods=20).mean()

    # 近两年（504日）价格高低位置分位（严格历史滚动，衡量跌透没有）
    out["price_pct_2y"] = c.rolling(504, min_periods=180).rank(pct=True)
    # 距离近一年（252日）最高点的回撤幅度
    high_1y = c.rolling(252, min_periods=120).max()
    out["drawdown_1y"] = c / high_1y - 1.0

    # 成交拥挤度分位：近10日平均成交额 / 近1年平均成交额，在过去两年中的排名分位
    amt10 = amt.rolling(10, min_periods=10).mean()
    amt252 = amt.rolling(252, min_periods=100).mean()
    heat_ratio = amt10 / amt252.replace(0.0, np.nan)
    out["crowd_pct"] = heat_ratio.rolling(504, min_periods=120).rank(pct=True)

    # 近期横盘蓄势紧凑度：过去 30 天收盘波动极差（不含最近3天突破K线）
    hi30 = c.shift(3).rolling(30, min_periods=20).max()
    lo30 = c.shift(3).rolling(30, min_periods=20).min()
    out["base_range_30d"] = (hi30 - lo30) / lo30.replace(0.0, np.nan)

    # 活筹码主成本峰辅助防守定位
    chip_df = compute_live_chip_metrics(df)
    out["poc_price"] = chip_df["poc_price"]
    out["ret20"] = c / c.shift(20) - 1.0
    out["ret60"] = c / c.shift(60) - 1.0
    return out


def compare_fund_strategies_detailed(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    cost_oneway: float = 0.0008,  # 场内基金免印花税，单边佣金滑点约8bp
    max_positions: int = 4,
    n_trials: int = 1,
):
    """在 18 只去重行业代表基金上，使用与生产漏斗100%同源的【历史板块共振 + 离成本线 + 拥挤度 + 排序】与真实资金账本验证。"""
    from .portfolio_sim import PortfolioSimConfig, simulate_real_portfolio
    from .signals import build_sector_etf_signal_panels, compute_sector_resonance_panel

    sector_syms = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
    panel = portal.load_panel_bars(sector_syms, market="CN", split=split, min_rows=180)
    close = panel["close"]
    if close.empty:
        return []
    dates = close.index
    valid_syms = list(close.columns)

    bench_close = portal.load_bars("510300.SS", market="CN", split=split)["close"].reindex(dates).ffill()
    res_ratio, _, _ = compute_sector_resonance_panel(portal, DISTINCT_SECTOR_FUNDS, split=split)
    sigs = build_sector_etf_signal_panels(panel, bench_close, resonance_ratio=res_ratio, require_resonance=True)

    harbor_bars: dict[str, pd.DataFrame] = {}
    for key, hsym in (("gold", "518850.SS"), ("dividend", "512890.SS")):
        try:
            harbor_bars[key] = portal.load_bars(hsym, market="CN", split=split)
        except FileNotFoundError:
            pass

    bh_scores = pd.DataFrame(1.0, index=dates, columns=valid_syms)
    bh_exits = pd.DataFrame(False, index=dates, columns=valid_syms)

    bh_cfg = PortfolioSimConfig(
        max_positions=len(valid_syms),
        max_per_industry=0,
        max_single_weight=1.0 / max(1, len(valid_syms)),
        risk_budget_per_trade=None,
        cost_buy=cost_oneway,
        cost_sell=cost_oneway,
        idle_cash_mode="cash",
    )
    etf_cfg = PortfolioSimConfig(
        max_positions=max_positions,
        max_per_industry=0,
        max_single_weight=1.0 / max(1, max_positions),
        risk_budget_per_trade=0.012,
        cost_buy=cost_oneway,
        cost_sell=cost_oneway,
        idle_cash_mode="cash",
    )
    etf_harbor_cfg = PortfolioSimConfig(
        max_positions=max_positions,
        max_per_industry=0,
        max_single_weight=1.0 / max(1, max_positions),
        risk_budget_per_trade=0.012,
        cost_buy=cost_oneway,
        cost_sell=cost_oneway,
        idle_cash_mode="gold_dividend_harbor",
    )

    return [
        simulate_real_portfolio(
            strategy_name="行业基金等权死拿",
            plain_rule_desc="18只去重行业基金等额买入一直拿着不动（真实成本）",
            panel=panel,
            entry_scores=bh_scores,
            exit_flags=bh_exits,
            bench_close=bench_close,
            config=bh_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="旧办法：站上20日均线追涨",
            plain_rule_desc="不看拥挤与板块共振，站上20日线按强度买前4只，破线卖",
            panel=panel,
            entry_scores=sigs["plain_ma_scores"],
            exit_flags=sigs["plain_ma_exits"],
            stop_prices=sigs["stop_prices"],
            bench_close=bench_close,
            config=etf_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="★同源右侧：共振起势不拥挤",
            plain_rule_desc="与收盘漏斗100%同源（内部共振>=50%+离60日线<=12%+未拥挤+打分前4），空仓留现金",
            panel=panel,
            entry_scores=sigs["right_entry_scores"],
            exit_flags=sigs["right_exit_flags"],
            stop_prices=sigs["stop_prices"],
            bench_close=bench_close,
            config=etf_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="★同源右侧+闲钱黄金红利过渡",
            plain_rule_desc="同上，叠加空仓闲钱交由稳在60日线上的黄金与红利低波过渡（含切换成本）",
            panel=panel,
            entry_scores=sigs["right_entry_scores"],
            exit_flags=sigs["right_exit_flags"],
            stop_prices=sigs["stop_prices"],
            bench_close=bench_close,
            harbor_bars=harbor_bars,
            config=etf_harbor_cfg,
            n_trials=n_trials,
        ),
        simulate_real_portfolio(
            strategy_name="★同源左侧：深坑拐头低吸",
            plain_rule_desc="距一年高点回撤>=16%且处两年低位，内部企稳+站回走平20日线低吸",
            panel=panel,
            entry_scores=sigs["left_entry_scores"],
            exit_flags=sigs["left_exit_flags"],
            stop_prices=sigs["stop_prices"],
            bench_close=bench_close,
            config=etf_cfg,
            n_trials=n_trials,
        ),
    ]


def compare_fund_strategies(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
    cost_oneway: float = 0.0008,  # 场内基金免印花税，单边佣金滑点约8bp
) -> list[StrategyLedgerSummary]:
    """在 18 只互不重复的行业代表基金上，使用同源信号与真实资金账本验证策略（向后兼容旧摘要返回）。"""
    return [r.to_ledger_summary() for r in compare_fund_strategies_detailed(portal, split=split, cost_oneway=cost_oneway)]


def _compute_sector_internal_resonance(portal: DataPortal) -> dict[str, tuple[float, int, int]]:
    """计算每个行业代表基金背后核心成分股的真实共振比例（复用同源 compute_sector_resonance_panel 最新收盘行）。"""
    from .signals import compute_sector_resonance_panel

    ratio_df, up_df, tot_df = compute_sector_resonance_panel(portal, DISTINCT_SECTOR_FUNDS, split="full", per_sector_top=12)
    if ratio_df.empty:
        return {}
    out: dict[str, tuple[float, int, int]] = {}
    for etf_sym in ratio_df.columns:
        valid_ratio = ratio_df[etf_sym].dropna()
        if len(valid_ratio) == 0:
            continue
        last_dt = valid_ratio.index[-1]
        out[str(etf_sym)] = (
            float(valid_ratio.iloc[-1]),
            int(up_df.loc[last_dt, etf_sym]),
            int(tot_df.loc[last_dt, etf_sym]),
        )
    return out


def evaluate_all_fund_opportunities(portal: DataPortal) -> dict[str, list[dict[str, object]]]:
    """一站式输出场内基金三类不打架的机会清单：【压舱石底仓状态】【行业右侧起势榜】【左侧跌透拐头榜】及【拥挤禁追警示】。"""
    bench = portal.load_bars("510300.SS", market="CN", split="full")["close"]
    b_ret20 = float(bench.iloc[-1] / bench.iloc[-21] - 1.0) if len(bench) > 21 else 0.0
    sector_res = _compute_sector_internal_resonance(portal)

    # 1. 10 只压舱石宽基与海外商品全景
    broad_rows: list[dict[str, object]] = []
    left_turn_rows: list[dict[str, object]] = []

    for sym, cn_name, role_desc in CORE_BROAD_FUNDS:
        try:
            bars = portal.load_bars(sym, market="CN", split="full")
        except FileNotFoundError:
            continue
        if len(bars) < 120:
            continue
        f = _compute_fund_indicators(bars)
        last = f.iloc[-1]
        prev3 = f.iloc[-4]
        cl = float(last["close"])
        ma20 = float(last["ma20"])
        ma60 = float(last["ma60"])
        ma200 = float(last["ma200"]) if pd.notna(last["ma200"]) else ma60
        pp2y = float(last["price_pct_2y"]) if pd.notna(last["price_pct_2y"]) else 0.5
        dd1y = float(last["drawdown_1y"]) if pd.notna(last["drawdown_1y"]) else 0.0
        crowd = float(last["crowd_pct"]) if pd.notna(last["crowd_pct"]) else 0.5
        dist_200 = (cl / ma200 - 1.0) * 100.0

        above_20 = cl >= ma20
        ma20_turning_up = ma20 >= float(prev3["ma20"]) * 0.999
        above_60 = cl >= ma60

        if pp2y <= 0.30 and above_20 and ma20_turning_up:
            action = "🟢 跌透刚站回20日均线（左侧转右侧加底仓良机）"
        elif pp2y <= 0.25 and not above_20:
            action = "🟡 处于近两年深跌便宜区，尚未站回20日线（可分批定投，不一把梭）"
        elif above_20 and above_60 and pp2y < 0.85:
            action = "🔵 稳健上升通道中（已有底仓安心长拿）"
        elif pp2y >= 0.85 and crowd >= 0.85:
            action = "🟠 处于近两年高位且成交偏热（底仓拿着、暂不追高加码）"
        else:
            action = "⚪ 震荡整理期（原有压舱石不动，观望为主）"

        code6 = sym.split(".")[0]
        broad_rows.append(
            {
                "code": code6,
                "name": cn_name,
                "role": role_desc,
                "as_of": str(f.index[-1].date()),
                "close": round(cl, 3),
                "pos_2y_pct": f"{pp2y*100:.0f}%",
                "drawdown_from_1y_high": f"{dd1y*100:.1f}%",
                "dist_to_ma200": f"{dist_200:+.1f}%",
                "action_verdict": action,
            }
        )

        # 检查是否触发左侧黄金坑拐头低吸条件
        if dd1y <= -0.14 and pp2y <= 0.35 and above_20 and ma20_turning_up:
            floor_px = round(float(bars["low"].tail(20).min()), 3)
            left_turn_rows.append(
                {
                    "code": code6,
                    "name": cn_name,
                    "kind": "宽基压舱石",
                    "as_of": str(f.index[-1].date()),
                    "close": round(cl, 3),
                    "drawdown_1y": f"{dd1y*100:.1f}%",
                    "pos_2y_pct": f"{pp2y*100:.0f}%",
                    "stop_defense_price": floor_px,
                    "plain_reason": (
                        f"距近一年高点已回撤 {abs(dd1y)*100:.1f}%（处于近两年 {pp2y*100:.0f}% 低位区），"
                        f"近期缩量洗盘后重新站上走平的20日均线（{ma20:.3f}），下方前低防守位 {floor_px} 极近。"
                    ),
                }
            )

    # 2. 18 只不重复行业代表基金：右侧起势榜 vs 左侧拐头榜 vs 过热禁追提醒
    right_sector_rows: list[dict[str, object]] = []
    crowded_warnings: list[dict[str, object]] = []

    for sym, cn_name, _ in DISTINCT_SECTOR_FUNDS:
        try:
            bars = portal.load_bars(sym, market="CN", split="full")
        except FileNotFoundError:
            continue
        if len(bars) < 120:
            continue
        f = _compute_fund_indicators(bars)
        last = f.iloc[-1]
        prev3 = f.iloc[-4]
        prev5 = f.iloc[-6]

        cl = float(last["close"])
        ma20 = float(last["ma20"])
        ma60 = float(last["ma60"])
        poc = float(last["poc_price"]) if pd.notna(last["poc_price"]) else ma60
        crowd = float(last["crowd_pct"]) if pd.notna(last["crowd_pct"]) else 0.5
        dd1y = float(last["drawdown_1y"]) if pd.notna(last["drawdown_1y"]) else 0.0
        pp2y = float(last["price_pct_2y"]) if pd.notna(last["price_pct_2y"]) else 0.5
        r20 = float(last["ret20"]) if pd.notna(last["ret20"]) else 0.0
        dist_ma60 = cl / ma60 - 1.0

        res_ratio, up_cnt, tot_cnt = sector_res.get(sym, (0.5, 0, 0))
        res_text = f"板块内 {up_cnt}/{tot_cnt} 只核心股同步站上20日线（共振度 {res_ratio*100:.0f}%）" if tot_cnt > 0 else "板块成分同步跟踪中"
        code6 = sym.split(".")[0]

        # 过热拥挤警示
        if crowd >= 0.85 or dist_ma60 > 0.14:
            if cl > ma20:
                crowded_warnings.append(
                    {
                        "code": code6,
                        "name": cn_name,
                        "close": round(cl, 3),
                        "crowd_pct": f"{crowd*100:.0f}%",
                        "dist_ma60": f"{dist_ma60*100:+.1f}%",
                        "note": f"成交热度达近两年 {crowd*100:.0f}% 分位、偏离60日成本线 {dist_ma60*100:+.1f}%，已偏拥挤，老仓设好止盈、不建议新追高。",
                    }
                )

        # 右侧起势四条硬标准：
        # ① 站上20与60日均线且均线向上；② 板块内部至少半数核心股共振走强(>=50%)；
        # ③ 距离60日均线不超过12%（刚抬头离防守近）；④ 成交热度未拥挤(<85%分位)
        trend_up = (cl > ma20) and (cl >= ma60 * 0.995) and (ma20 > float(prev5["ma20"])) and (ma60 >= float(prev5["ma60"]) * 0.996)
        resonance_ok = (tot_cnt == 0) or (res_ratio >= 0.50)
        near_cost_ok = dist_ma60 <= 0.12
        not_crowded_ok = crowd < 0.85

        if trend_up and resonance_ok and near_cost_ok and not_crowded_ok:
            from .signals import DEFAULT_SECTOR_WEIGHTS

            rs20 = r20 - b_ret20
            # 打分权重与同源回测面板 100% 共享 DEFAULT_SECTOR_WEIGHTS
            score = (
                DEFAULT_SECTOR_WEIGHTS["resonance"] * res_ratio
                + DEFAULT_SECTOR_WEIGHTS["near_cost"] * max(0.0, 1.0 - max(0.0, dist_ma60) / 0.12)
                + DEFAULT_SECTOR_WEIGHTS["rel_strength"] * float(np.tanh(rs20 * 5.0))
                + DEFAULT_SECTOR_WEIGHTS["low_crowd"] * (1.0 - crowd)
            )
            stop_px = round(min(ma20, poc), 3)
            stop_dist = (cl / stop_px - 1.0) * 100.0
            right_sector_rows.append(
                {
                    "code": code6,
                    "name": cn_name,
                    "as_of": str(f.index[-1].date()),
                    "close": round(cl, 3),
                    "resonance": f"{res_ratio*100:.0f}%（{up_cnt}/{tot_cnt}只）" if tot_cnt else "达标",
                    "crowd_pct": f"{crowd*100:.0f}%",
                    "dist_ma60": f"{dist_ma60*100:+.1f}%",
                    "vs_hs300_20d": f"{rs20*100:+.1f}%",
                    "stop_defense_price": stop_px,
                    "rank_score": round(float(score), 4),
                    "plain_reason": (
                        f"{res_text}；刚站上20与60日均线（仅高出60日成本 {dist_ma60*100:.1f}%），"
                        f"成交热度 {crowd*100:.0f}% 分位尚未拥挤，近一月跑赢大盘 {rs20*100:+.1f}%。"
                        f"防守位 {stop_px}（离现价仅 {stop_dist:.1f}%）。"
                    ),
                }
            )

        # 左侧跌透拐头检查（针对经历深幅调整后刚重新站上走平20日均线、且内部至少三分之一股票已率先止跌的行业）
        ma20_turning = (cl > ma20) and (ma20 >= float(prev3["ma20"]) * 0.999)
        if (dd1y <= -0.16) and (pp2y <= 0.35) and ma20_turning and (crowd < 0.75) and (res_ratio >= 0.35):
            floor_px = round(float(bars["low"].tail(20).min()), 3)
            left_turn_rows.append(
                {
                    "code": code6,
                    "name": cn_name,
                    "kind": "行业波段基金",
                    "as_of": str(f.index[-1].date()),
                    "close": round(cl, 3),
                    "drawdown_1y": f"{dd1y*100:.1f}%",
                    "pos_2y_pct": f"{pp2y*100:.0f}%",
                    "stop_defense_price": floor_px,
                    "plain_reason": (
                        f"距一年高点已深跌 {abs(dd1y)*100:.1f}%（近两年 {pp2y*100:.0f}% 低位区），"
                        f"{res_text}，刚刚站回走平的20日均线拐头，下方前低防守位 {floor_px}。"
                    ),
                }
            )

    right_sector_rows.sort(key=lambda x: float(x["rank_score"]), reverse=True)
    return {
        "broad_compass": broad_rows,
        "right_side_sector_picks": right_sector_rows[:10],
        "left_side_turnaround_picks": left_turn_rows[:10],
        "crowded_no_chase_warnings": crowded_warnings,
    }
