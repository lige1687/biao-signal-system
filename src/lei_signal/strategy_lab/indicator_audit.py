"""系统已有市场观测指标“去重与大顶大底真本事体检器”（indicator_audit）。

解决痛点：
1. 系统里塞了 20 多个市场指标，只显示裸数字，看不出到底提供什么信息；
2. 平时很多指标互相矛盾、或者几个指标换着名字说同一句话。

核心做法：
- 不拿市场观测指标去测“明天涨不涨”（平时一律静音当背景）；
- 专门检验当每个指标进入历史最极端的 15% 位置（冰点区 vs 沸腾区）时，
  未来 3 个月（60交易日）和半年（120交易日）宽基指数真实的胜率、平均涨跌幅和平均最大回撤；
- 自动筛出真正能帮你在“大底敢重仓、大顶少挨打”的王牌警报器，并生成今日一句人话天气单。
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .data_portal import DataPortal, IndicatorSeries, SplitMode


@dataclass(frozen=True)
class IndicatorAuditRow:
    id: str
    name_cn: str
    market: str
    plain_meaning: str
    sample_days: int
    start_date: str
    end_date: str
    # 抄底端表现（当指标到达恐慌/便宜极值区时，未来半年宽基表现）
    bottom_zone_label: str
    bottom_events_nonoverlap: int
    bottom_winrate_120d: float
    bottom_mean_ret_120d: float
    base_mean_ret_120d: float
    bottom_edge_120d: float
    # 逃顶/防跌端表现（当指标到达过热/拥挤极值区时，未来3个月宽基表现与最大下探）
    top_zone_label: str
    top_events_nonoverlap: int
    top_mean_ret_60d: float
    base_mean_ret_60d: float
    top_edge_60d: float
    top_worst_dd_60d: float
    # 分级与去重提示
    grade: str
    verdict_cn: str
    duplicate_with: str | None
    tail_jaccard_max: float = 0.0
    bottom_events_raw: int = 0
    top_events_raw: int = 0


def _non_overlapping_indices(mask: np.ndarray, cooldown: int = 20) -> list[int]:
    """按时间顺序提取至少间隔 cooldown 个交易日的触发时点。"""
    picked: list[int] = []
    last_idx = -cooldown - 1
    for i, flag in enumerate(mask):
        if flag and (i - last_idx >= cooldown):
            picked.append(i)
            last_idx = i
    return picked


def _independent_regime_events(mask: np.ndarray, horizon: int) -> list[int]:
    """按评估视窗 horizon 严格提取不重叠的独立周期事件。

    避免用 20 天短冷却把同一轮大底/大顶切碎成 4~5 次假独立样本；
    同时要求两次事件之间至少相隔 horizon 个交易日，保证前向收益窗零重叠。
    """
    return _non_overlapping_indices(mask, cooldown=max(20, int(horizon)))


def _causal_percentile_rank(series: pd.Series, window: int = 1260, min_periods: int = 180) -> pd.Series:
    """严格前缀不变（纯因果）历史分位：窗口宽度固定为 5 年(1260日)，绝不依赖未来总样本长度 n。"""
    return series.rolling(window, min_periods=min_periods).rank(pct=True)


def _extreme_tail_jaccard(
    s1: pd.Series,
    side1: str,
    s2: pd.Series,
    side2: str,
) -> float:
    """计算两个指标在历史极端 15% 警报区（冰点+沸腾并集）的 Jaccard 重合度，防止线性相关误杀拐点指标。"""
    df = pd.DataFrame({"a": s1, "b": s2}).dropna()
    if len(df) < 200:
        return 0.0
    pa = _causal_percentile_rank(df["a"]).to_numpy()
    pb = _causal_percentile_rank(df["b"]).to_numpy()
    valid = np.isfinite(pa) & np.isfinite(pb)
    if valid.sum() < 80:
        return 0.0
    pa, pb = pa[valid], pb[valid]
    ea = (pa >= 0.85) | (pa <= 0.15)
    eb = (pb >= 0.85) | (pb <= 0.15)
    # 同时对齐方向检查（同向冰点或同向过热）
    bot_a = (pa >= 0.85) if side1 == "high" else (pa <= 0.15)
    bot_b = (pb >= 0.85) if side2 == "high" else (pb <= 0.15)
    top_a = (pa <= 0.15) if side1 == "high" else (pa >= 0.85)
    top_b = (pb <= 0.15) if side2 == "high" else (pb >= 0.85)
    inter = int(((bot_a & bot_b) | (top_a & top_b)).sum())
    union = int((ea | eb).sum())
    return float(inter / union) if union > 0 else 0.0


def audit_market_indicators(
    portal: DataPortal,
    *,
    split: SplitMode = "explore",
) -> tuple[list[IndicatorAuditRow], list[tuple[str, str, float]]]:
    """对系统全部已有指标做极端区历史真本事检验与相关性查重。"""
    indicators = portal.load_all_market_indicators(split=split)
    cn_idx = portal.load_bars("510300.SS", market="CN", split=split)["close"]
    us_idx = portal.load_bars("SPY", market="US", split=split)["close"]

    # 1. 两两相关性 + 极端尾部重合度双重查重（防止线性相关误杀只在拐点独立的指标）
    aligned = pd.DataFrame({k: v.series for k, v in indicators.items()})
    corr_mat = aligned.corr(min_periods=120)
    high_corr_pairs: list[tuple[str, str, float]] = []
    dup_map: dict[str, str] = {}
    max_tail_jacc: dict[str, float] = {}
    keys = list(indicators.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            k1, k2 = keys[i], keys[j]
            if indicators[k1].market != indicators[k2].market:
                continue
            r = corr_mat.loc[k1, k2]
            if pd.notna(r) and abs(float(r)) >= 0.72:
                tj = _extreme_tail_jaccard(
                    indicators[k1].series,
                    indicators[k1].expected_bottom_side,
                    indicators[k2].series,
                    indicators[k2].expected_bottom_side,
                )
                max_tail_jacc[k1] = max(max_tail_jacc.get(k1, 0.0), tj)
                max_tail_jacc[k2] = max(max_tail_jacc.get(k2, 0.0), tj)
                if tj >= 0.45 or abs(float(r)) >= 0.88:
                    high_corr_pairs.append((indicators[k1].name_cn, indicators[k2].name_cn, round(float(r), 2)))
                    # 样本更短或排后面的标为重复项
                    if len(indicators[k2].series) <= len(indicators[k1].series):
                        dup_map.setdefault(k2, indicators[k1].name_cn)
                    else:
                        dup_map.setdefault(k1, indicators[k2].name_cn)

    rows: list[IndicatorAuditRow] = []
    for ind_id, meta in indicators.items():
        bench = cn_idx if meta.market == "CN" else us_idx
        df = pd.DataFrame({"val": meta.series}).join(bench.rename("px"), how="inner").dropna()
        if len(df) < 260:
            continue

        px = df["px"].to_numpy()
        val = df["val"].to_numpy()
        n = len(df)

        # 严格前缀不变：固定最多 5 年(1260日)滚动分位，不依赖未来总长度 n
        pct_rank = _causal_percentile_rank(df["val"], window=1260, min_periods=180).to_numpy()

        # 计算未来 60 日与 120 日真实涨跌幅及期间最深回撤（仅用于检验指标成色）
        fwd60 = np.full(n, np.nan)
        fwd120 = np.full(n, np.nan)
        dd60 = np.full(n, np.nan)
        for t in range(n - 61):
            entry = px[t + 1]
            fwd60[t] = px[t + 60] / entry - 1.0
            dd60[t] = np.min(px[t + 1 : t + 61]) / entry - 1.0
        for t in range(n - 121):
            fwd120[t] = px[t + 120] / px[t + 1] - 1.0

        valid_120 = np.isfinite(pct_rank) & np.isfinite(fwd120)
        valid_60 = np.isfinite(pct_rank) & np.isfinite(fwd60)
        if valid_60.sum() < 80:
            continue

        base_60 = float(np.nanmean(fwd60[valid_60]))
        base_120 = float(np.nanmean(fwd120[valid_120])) if valid_120.sum() >= 60 else base_60 * 2

        if meta.expected_bottom_side == "high":
            bot_mask = valid_120 & (pct_rank >= 0.85)
            top_mask = valid_60 & (pct_rank <= 0.15)
            bot_label = "历史高极值(>85%分位)"
            top_label = "历史低极值(<15%分位)"
        else:
            bot_mask = valid_120 & (pct_rank <= 0.15)
            top_mask = valid_60 & (pct_rank >= 0.85)
            bot_label = "历史冰点(<15%分位)"
            top_label = "历史沸腾(>85%分位)"

        # 按评估视窗提取真正零重叠独立事件（120日抄底 / 60日防跌），同时保留 20 日波次供参考
        bot_idx_raw = _non_overlapping_indices(bot_mask, cooldown=20)
        top_idx_raw = _non_overlapping_indices(top_mask, cooldown=20)
        bot_idx = _independent_regime_events(bot_mask, horizon=120)
        top_idx = _independent_regime_events(top_mask, horizon=60)

        if bot_idx:
            bot_rets = fwd120[bot_idx]
            bot_win = float(np.mean(bot_rets > 0))
            bot_mean = float(np.mean(bot_rets))
            bot_edge = bot_mean - base_120
        else:
            bot_win, bot_mean, bot_edge = np.nan, np.nan, 0.0

        if top_idx:
            top_rets = fwd60[top_idx]
            top_dds = dd60[top_idx]
            top_mean = float(np.mean(top_rets))
            top_edge = top_mean - base_60
            top_dd = float(np.mean(top_dds))
        else:
            top_mean, top_edge, top_dd = np.nan, 0.0, np.nan

        # 独立事件不再被20日短冷却虚高，3次以上严格不重叠大底/大顶即具备跨周期观察价值
        good_bottom = len(bot_idx) >= 3 and (bot_win >= 0.70 and bot_edge >= 0.03)
        good_top = len(top_idx) >= 3 and (top_edge <= -0.025 or top_dd <= -0.075)

        dup = dup_map.get(ind_id)
        if good_bottom and good_top:
            grade = "★ 王牌双向警报"
            verdict = "冰点敢抄大底，过热能提前预警回撤"
        elif good_bottom:
            grade = "★ 王牌抄底警报"
            verdict = "跌到冰点后半年胜率与超额显著，专管大底加仓"
        elif good_top:
            grade = "★ 王牌防跌警报"
            verdict = "冲入过热区后3个月易回撤，专管高位收紧止盈"
        elif dup:
            grade = "折叠(重复指标)"
            verdict = f"与【{dup}】高度同源重复，留一个看即可"
        else:
            grade = "普通背景温度计"
            verdict = "仅反映当下盘面状态，极端区无明显提前预测优势，平时别拿它拦买点"

        rows.append(
            IndicatorAuditRow(
                id=ind_id,
                name_cn=meta.name_cn,
                market=meta.market,
                plain_meaning=meta.plain_meaning,
                sample_days=n,
                start_date=str(df.index[0].date()),
                end_date=str(df.index[-1].date()),
                bottom_zone_label=bot_label,
                bottom_events_nonoverlap=len(bot_idx),
                bottom_winrate_120d=round(bot_win, 4) if np.isfinite(bot_win) else -1.0,
                bottom_mean_ret_120d=round(bot_mean, 4) if np.isfinite(bot_mean) else 0.0,
                base_mean_ret_120d=round(base_120, 4),
                bottom_edge_120d=round(bot_edge, 4),
                top_zone_label=top_label,
                top_events_nonoverlap=len(top_idx),
                top_mean_ret_60d=round(top_mean, 4) if np.isfinite(top_mean) else 0.0,
                base_mean_ret_60d=round(base_60, 4),
                top_edge_60d=round(top_edge, 4),
                top_worst_dd_60d=round(top_dd, 4) if np.isfinite(top_dd) else 0.0,
                grade=grade,
                verdict_cn=verdict,
                duplicate_with=dup,
                tail_jaccard_max=round(max_tail_jacc.get(ind_id, 0.0), 3),
                bottom_events_raw=len(bot_idx_raw),
                top_events_raw=len(top_idx_raw),
            )
        )

    priority = {"★ 王牌双向警报": 0, "★ 王牌抄底警报": 1, "★ 王牌防跌警报": 2, "普通背景温度计": 3, "折叠(重复指标)": 4}
    rows.sort(key=lambda r: (0 if r.market == "CN" else 1, priority.get(r.grade, 9), -r.bottom_edge_120d))
    return rows, high_corr_pairs


def render_market_weather(portal: DataPortal) -> dict[str, object]:
    """用最新全量数据把核心指标翻译成‘不打架的一句话市场天气单’。"""
    indicators = portal.load_all_market_indicators(split="full")
    snapshots: list[dict[str, object]] = []
    cn_alarms: list[str] = []
    us_alarms: list[str] = []

    # 只选经历史验证不重复的王牌/核心指标发声（去掉与VIX高度重复的VXN/期限结构，去掉与全A宽度重复的沪深300宽度）
    core_ids = [
        "cn-erp",
        "cn-breadth-b50",
        "cn-daily-amount-top5",
        "vix",
        "hy-oas",
        "naaim",
    ]
    for cid in core_ids:
        if cid not in indicators:
            continue
        meta = indicators[cid]
        s = meta.series
        win = min(1260, max(252, len(s)))
        pct = float(s.tail(win).rank(pct=True).iloc[-1])
        val = float(s.iloc[-1])
        dt = str(s.index[-1].date())

        # 判断是否处于极端 15% 警报区，平时全部归为“正常静音”
        is_bottom_extreme = (pct >= 0.85) if meta.expected_bottom_side == "high" else (pct <= 0.15)
        is_top_extreme = (pct <= 0.15) if meta.expected_bottom_side == "high" else (pct >= 0.85)

        if is_bottom_extreme:
            state_cn = "🟢 极端黄金坑警报（历史底部15%区间）"
            msg = f"{meta.name_cn} 处于近5年 {pct*100:.0f}% 分位（{val:.2f}），进入历史罕见恐慌/低估击球区"
            (cn_alarms if meta.market == "CN" else us_alarms).append(msg)
        elif is_top_extreme:
            state_cn = "🔴 极端过热/脆弱警报（历史顶部15%区间）"
            msg = f"{meta.name_cn} 处于近5年 {pct*100:.0f}% 分位（{val:.2f}），进入过热拥挤/脆弱区，勿追高并收紧止盈"
            (cn_alarms if meta.market == "CN" else us_alarms).append(msg)
        else:
            state_cn = "⚪ 正常区间（静音不干扰波段买卖）"

        snapshots.append(
            {
                "id": cid,
                "market": meta.market,
                "name": meta.name_cn,
                "as_of": dt,
                "latest_value": round(val, 3),
                "history_percentile": f"{pct*100:.0f}%",
                "status": state_cn,
            }
        )

    cn_summary = (
        "；".join(cn_alarms)
        if cn_alarms
        else "A股估值与宽度均处于正常温度带（无大顶/大底极端警报）——不用纠结宏观，专心看筹码峰与均线挑强势票即可。"
    )
    us_summary = (
        "；".join(us_alarms)
        if us_alarms
        else "美股信用利差与情绪未见系统性崩盘信号——美股宽基压舱石底仓安心持有不动。"
    )

    # 连续风险温度计（0=极端冰点黄金坑，50=温和中性，100=极端过热沸腾）与平滑权益仓位上限乘数
    def _heat_and_cap(mkt: str) -> tuple[float, float]:
        heats: list[float] = []
        for snap in snapshots:
            if snap["market"] != mkt:
                continue
            cid = str(snap["id"])
            meta = indicators.get(cid)
            if meta is None:
                continue
            pct = float(str(snap["history_percentile"]).rstrip("%")) / 100.0
            # 统一成“越大越过热、越小越便宜/恐慌”的热度分 [0, 100]
            heat = (1.0 - pct) * 100.0 if meta.expected_bottom_side == "high" else pct * 100.0
            heats.append(heat)
        if not heats:
            return 50.0, 1.0
        avg_heat = float(np.mean(heats))
        # 热度 <= 70 满额开放(1.0)；70~95 线性平滑收紧至 0.45，避免 85% 阈值一刀切跳变
        cap = 1.0 if avg_heat <= 70.0 else float(np.clip(1.0 - (avg_heat - 70.0) / 25.0 * 0.55, 0.45, 1.0))
        return round(avg_heat, 1), round(cap, 2)

    cn_heat, cn_cap = _heat_and_cap("CN")
    us_heat, us_cap = _heat_and_cap("US")
    return {
        "cn_plain_verdict": cn_summary,
        "us_plain_verdict": us_summary,
        "cn_risk_temperature": cn_heat,
        "cn_suggested_equity_cap": cn_cap,
        "us_risk_temperature": us_heat,
        "us_suggested_equity_cap": us_cap,
        "core_thermometers": snapshots,
    }
