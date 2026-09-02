#!/usr/bin/env python3
"""持仓基金 × 已验证宽度标的 相关性研究·预注册（2026-09-02，跑前写死，跑后不改）。

Prompt W：用户持仓（富国全球科技互联网A 100055 / 易方达全球成长精选A 012920 /
易方达信息产业A 001513 / 财通成长优选A 001480 / 有色按512400 ETF算 / 恒生科技按
513180 ETF算）与系统已验证宽度择时规则标的的相关性，判定哪些持仓可复用参考规则。

【数据口径】
- 基金日收益 = 天天基金 pingzhongdata 的 equityReturn（日净值增长率，含分红
  再投口径），非单位净值水平差分；抓取时间 2026-09-02。
- 候选标的 = src/lei_signal/timing_backtest 本地缓存（~/.lei_signal_lab/cache/
  timing/）收盘价日收益（A股截至 2026-08-27，美股 ETF 截至 2026-08-26/31）。
- 513180 = 腾讯 qfq 日线（2021-05-25→2026-09-02，抓取时间 2026-09-02）。
- 对齐 = 共同交易日 inner join（A股基金×A股标的同日；QDII×美股见滞后条款）。

【滞后条款（QDII 净值时区，跑前写死）】
QDII 基金 T 日净值反映美东 T-1 收盘。QDII×美股配对计算两档：
lag0（同日）与 lag1（美股 T-1 对基金 T），有效相关 = 两档 Pearson 较高者，
两档数字均披露。A股基金×A股标的不适用滞后（同市场同日）。

【判定标准（预注册，跑前写死）】
- 主判定线：全共同窗日收益 Pearson ≥ 0.75 且 Spearman ≥ 0.70
  → 「高相关：可复用该标的已验证规则作为参考」。
- 0.55 ≤ Pearson < 0.75 → 「中相关：仅方向参考，档位输出误差可能大」。
- Pearson < 0.55 → 「不可复用」。
- 最少重叠：全窗 < 120 共同交易日 → 「样本不足，不下判定」（012920 仅
  2022-03 起、513180 仅 2021-05 起，预计多个候选触发此条，如实报告）。
- 滚动年窗稳定性：按日历年分窗 Pearson；「稳定」= 全部年窗 ≥ 0.50 且中位数
  ≥ 0.70（年窗样本 < 100 共同日的不计入判定，仅披露）；任一年窗 < 0.30 或
  为负 → 「不稳定」：即使全窗过主判定线也降级表述为「高相关但不稳定」。
- 灵敏度面：主阈值在 {0.60, 0.65, 0.70, 0.75, 0.80, 0.85} 逐档重判并
  报告每持仓的高相关候选数变化——展示结论对阈值的敏感度，不用于事后选阈值。

【阈值 0.75 的依据（跑前论证，不因结果调整）】
1. R²≈0.56：持仓约 56% 方差与参考标的共动。宽度档位规则管的是市场 beta
   部分，移植语义要求共动部分过半。
2. 结构参照：ETF 对自身跟踪指数典型 >0.95；A股跨行业指数对典型 0.5-0.8；
   主动行业基金对行业指数典型 0.6-0.85；0.75 位于「主动基金可达到的上沿
   区域」，不用 0.80（Prompt T 的指数↔指数代理线）是因为本任务面对主动
   基金/QDII，净值噪声天然更大，且用途是「参考规则」而非「数据代理」。
3. 0.55 下限：R²≈0.30，A股任意两个宽基日收益相关性常达 0.5+，低于 0.55
   无区分度（与黄金对照的区分意义也在此）。

【红线遵守】本脚本只输出统计数字，不产生任何买卖指令、不合成数据、
不给综合建议；规则读数查询用系统现成 build_signals()（另一脚本段）。

输出：docs/experiments/raw/holdings_correlation/correlation_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_holdings_correlation.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw/holdings_correlation"
TIMING = Path.home() / ".lei_signal_lab/cache/timing"

sys.path.insert(0, str(REPO / "scripts"))

# ── 预注册常量（跑前写死）──
PEARSON_HI = 0.75   # 高相关主判定线
SPEARMAN_HI = 0.70  # 交叉验证线
PEARSON_MID = 0.55  # 中相关下限
MIN_OVERLAP = 120   # 全窗最少共同交易日
YEAR_MIN_DAYS = 100  # 年窗计入判定的最少共同日
STAB_YEAR_MIN = 0.50  # 年窗全部须 ≥
STAB_MEDIAN_MIN = 0.70  # 年窗中位数须 ≥
STAB_BREAK = 0.30   # 任一年窗低于此 → 不稳定
SENS_GRID = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

# ── 持仓（用户提供 2026-09-02）──
HOLDINGS = {
    "100055": {"name": "富国全球科技互联网股票(QDII)A", "kind": "fund", "market": "qdii"},
    "012920": {"name": "易方达全球成长精选混合(QDII)人民币A", "kind": "fund", "market": "qdii"},
    "001513": {"name": "易方达信息产业混合A", "kind": "fund", "market": "cn"},
    "001480": {"name": "财通成长优选混合A", "kind": "fund", "market": "cn"},
    "512400": {"name": "有色ETF（按ETF算）", "kind": "etf", "market": "cn"},
    "513180": {"name": "恒生科技ETF（按ETF算）", "kind": "etf", "market": "cn"},
}

# ── 候选清单（execution_playbook_20260827.md 终审表 + kuandu-quanzhan-ARCHIVE
#    提取的「已验证规则标的」；规则性质逐条标注，防误读）──
CANDIDATES = {
    # A股·冠军三档 B200 逆势（已验证；()内为现行执行配置边界）
    "399006":  {"name": "创业板指", "rule": "三档30/70→43.3/56.7", "verdict": "✅主仓"},
    "399975":  {"name": "证券公司", "rule": "三档30/70→43.3/56.7", "verdict": "✅稳健"},
    "399976":  {"name": "新能源车", "rule": "三档40/60→46.7/53.3", "verdict": "✅稳健"},
    "399997":  {"name": "中证白酒", "rule": "三档40/60→46.7/53.3", "verdict": "✅稳健"},
    "000819":  {"name": "有色金属(中证申万)", "rule": "三档40/60→46.7/53.3", "verdict": "✅稳健"},
    "399986":  {"name": "中证银行", "rule": "三档40/60→46.7/53.3", "verdict": "✅稳健"},
    "512200":  {"name": "房地产ETF", "rule": "三档30/70", "verdict": "✅强适配"},
    "159766":  {"name": "旅游ETF", "rule": "三档+MA200闸", "verdict": "✅适配"},
    "159992":  {"name": "创新药ETF", "rule": "三档30/70", "verdict": "✅(14轮)"},
    "515170":  {"name": "食品饮料ETF", "rule": "三档+MA200闸", "verdict": "✅(14轮)"},
    "515210":  {"name": "钢铁ETF", "rule": "三档+MA200闸", "verdict": "✅(14轮)"},
    "515180":  {"name": "红利ETF沪", "rule": "三档30/70", "verdict": "✅低波(14轮)"},
    "512100":  {"name": "中证1000ETF", "rule": "三档30/70 无闸", "verdict": "✅(14轮)"},
    "588000":  {"name": "科创50ETF", "rule": "三档30/70", "verdict": "✅样本短"},
    "399967":  {"name": "中证军工", "rule": "三档30/70", "verdict": "⚠️弱稳健"},
    "980030":  {"name": "通信(国证)", "rule": "三档30/70", "verdict": "⚠️弱稳健·RS灯亮"},
    "512010":  {"name": "医药ETF", "rule": "三档", "verdict": "⚖️近年有效"},
    "000015":  {"name": "上证红利", "rule": "三档", "verdict": "⚖️前半有效"},
    "510300":  {"name": "沪深300ETF", "rule": "攻守(反转+闸)", "verdict": "防守位"},
    "512480":  {"name": "半导体芯片ETF", "rule": "三档", "verdict": "❌近年失效·独立牛市"},
    "518880":  {"name": "黄金ETF", "rule": "无(阴性对照)", "verdict": "对照·预期低相关"},
    # 美股·防守版（性质=回撤保险，非择时增强；年化保费4-8pp）
    "SPY":     {"name": "SPY", "rule": "防守A 40/80 vol0.15", "verdict": "保险定性"},
    "QQQ":     {"name": "QQQ", "rule": "防守 20/80 5档", "verdict": "保险定性"},
    "SMH":     {"name": "SMH 半导体", "rule": "防守版(31轮)", "verdict": "保险定性"},
    "XLK":     {"name": "XLK 科技", "rule": "防守版(31轮)", "verdict": "保险定性"},
    "XLF":     {"name": "XLF 金融", "rule": "防守版(31轮)", "verdict": "保险定性"},
    "XLE":     {"name": "XLE 能源", "rule": "防守版(31轮)", "verdict": "保险定性"},
}
US_CANDS = {"SPY", "QQQ", "SMH", "XLK", "XLF", "XLE"}


def load_fund_returns(code: str) -> pd.Series:
    df = pd.read_parquet(RAW / f"{code}_nav.parquet").set_index("date")
    ret = df["eqret_pct"].astype(float) / 100.0
    return ret.dropna()


def load_etf_returns(code: str, kind: str) -> pd.Series:
    if code == "513180":
        df = pd.read_parquet(RAW / "sh513180_bars.parquet")
    elif kind == "etf":  # 512400 从 timing 缓存
        df = pd.read_parquet(TIMING / f"{code}.parquet")
    else:
        df = pd.read_parquet(TIMING / f"{code}.parquet")
    return df["close"].astype(float).pct_change().dropna()


def load_cand_returns(code: str) -> pd.Series:
    df = pd.read_parquet(TIMING / f"{code}.parquet")
    return df["close"].astype(float).pct_change().dropna()


def pair_stats(a: pd.Series, b: pd.Series) -> dict | None:
    """共同窗日收益 Pearson/Spearman + 滚动年窗。a=持仓, b=候选。"""
    both = pd.concat([a, b], axis=1, join="inner").dropna()
    n = len(both)
    if n < MIN_OVERLAP:
        return {"n": n, "verdict": "样本不足",
                "note": f"共同交易日 {n} < {MIN_OVERLAP}，不下相关性判定"}
    pear = float(both.corr().iloc[0, 1])
    spear = float(both.corr(method="spearman").iloc[0, 1])
    # 滚动年窗
    years, year_pears = [], []
    for yr, g in both.groupby(both.index.year):
        if len(g) >= YEAR_MIN_DAYS:
            years.append(int(yr))
            year_pears.append((int(yr), len(g), float(g.corr().iloc[0, 1])))
        else:
            year_pears.append((int(yr), len(g), None))
    vals = [v for _, _, v in year_pears if v is not None]
    if vals:
        med = float(np.median(vals))
        stable = (min(vals) >= STAB_YEAR_MIN and med >= STAB_MEDIAN_MIN
                  and min(vals) > STAB_BREAK)
    else:
        med, stable = None, False
    # 判定（预注册线）
    if pear >= PEARSON_HI and spear >= SPEARMAN_HI:
        verdict = "高相关" if stable else "高相关但不稳定"
    elif pear >= PEARSON_MID:
        verdict = "中相关·方向参考"
    else:
        verdict = "不可复用"
    return {
        "n": n, "start": str(both.index.min().date()), "end": str(both.index.max().date()),
        "pearson": round(pear, 4), "spearman": round(spear, 4),
        "year_windows": [(y, m, None if v is None else round(v, 3)) for y, m, v in year_pears],
        "year_median": None if med is None else round(med, 3),
        "stable": bool(stable),
        "verdict": verdict,
    }


def sensitivity(hold_ret: pd.Series, cand_rets: dict, is_qdii_us: bool) -> dict:
    """灵敏度面：各阈值下的高相关候选数。"""
    out = {}
    for th in SENS_GRID:
        cnt = 0
        for c, cr in cand_rets.items():
            both = pd.concat([hold_ret, cr], axis=1, join="inner").dropna()
            if len(both) < MIN_OVERLAP:
                continue
            p = float(both.corr().iloc[0, 1])
            if is_qdii_us:  # 滞后条款取高者
                b2 = pd.concat([hold_ret, cr.shift(1)], axis=1, join="inner").dropna()
                if len(b2) >= MIN_OVERLAP:
                    p = max(p, float(b2.corr().iloc[0, 1]))
            if p >= th:
                cnt += 1
        out[str(th)] = cnt
    return out


def main() -> None:
    results = {"criteria": {
        "pearson_hi": PEARSON_HI, "spearman_hi": SPEARMAN_HI,
        "pearson_mid": PEARSON_MID, "min_overlap": MIN_OVERLAP,
        "year_min_days": YEAR_MIN_DAYS, "stab_year_min": STAB_YEAR_MIN,
        "stab_median_min": STAB_MEDIAN_MIN, "stab_break": STAB_BREAK,
        "sens_grid": SENS_GRID,
        "qdii_lag_rule": "QDII×美股: lag0/lag1 双算取Pearson高者，均披露",
    }, "holdings": {}}

    cand_rets = {c: load_cand_returns(c) for c in CANDIDATES}

    for hcode, meta in HOLDINGS.items():
        if meta["kind"] == "fund":
            hret = load_fund_returns(hcode)
        else:
            hret = load_etf_returns(hcode, "etf")
        entry = {"name": meta["name"], "kind": meta["kind"],
                 "data_start": str(hret.index.min().date()),
                 "data_end": str(hret.index.max().date()),
                 "data_note": ("基金净值来源=天天基金equityReturn(含分红再投)，"
                               "抓取2026-09-02" if meta["kind"] == "fund"
                               else "ETF收盘价（513180=腾讯qfq 2026-09-02抓取；"
                                    "512400=本地timing缓存截至2026-08-27）"),
                 "candidates": {}}
        for ccode, cmeta in CANDIDATES.items():
            stat = {"cand_name": cmeta["name"], "rule": cmeta["rule"],
                    "verdict_ref": cmeta["verdict"]}
            if meta["market"] == "qdii" and ccode in US_CANDS:
                # 滞后条款：lag0 与 lag1 双算，取高者
                s0 = pair_stats(hret, cand_rets[ccode])
                s1 = pair_stats(hret, cand_rets[ccode].shift(1))
                if s0.get("pearson") is not None and s1.get("pearson") is not None:
                    if s1["pearson"] > s0["pearson"]:
                        s0, s1 = s1, s0
                    stat.update(s0)
                    stat["lag"] = "lag1(美股T-1 vs 基金T)" if "start" in s0 else None
                    stat["other_lag"] = {"pearson": s1["pearson"], "n": s1["n"]}
                else:
                    stat.update(s0 if s0.get("pearson") is not None else s1)
            else:
                stat.update(pair_stats(hret, cand_rets[ccode]))
            entry["candidates"][ccode] = stat
        entry["sensitivity_n_high_corr"] = sensitivity(
            hret, cand_rets, meta["market"] == "qdii")
        results["holdings"][hcode] = entry
        # 控制台摘要
        top = sorted(
            ((c, s.get("pearson"), s["verdict"]) for c, s in entry["candidates"].items()
             if s.get("pearson") is not None),
            key=lambda x: -(x[1] or 0))[:5]
        print(f"\n=== {hcode} {meta['name']} ===")
        for c, p, v in top:
            print(f"  {c:8s} {CANDIDATES[c]['name']:14s} pearson={p:.3f}  {v}")

    out_path = RAW / "correlation_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(json.dumps(results, sort_keys=True,
                                  ensure_ascii=False).encode()).hexdigest()
    print(f"\n输出: {out_path}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
