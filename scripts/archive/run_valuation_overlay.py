#!/usr/bin/env python3
"""Prompt T · 估值层确认事件研究（预注册 2026-09-02，跑前写死，跑后不改）。

背景：宽基宽度择时（两只版，139笔创业板信号）已通过；基本面触发信号三连证伪
（美债/VIX/A股宏观）。本实验测「估值分位作为宽度择时信号的确认层」——同样
的择时信号，触发时估值状态（便宜/中性/昂贵）不同，后续表现是否有统计上可信
的差异。不是让估值产生买卖点，不是仓位系数映射（那是已判负机制类别）。

【预注册协议】

数据（全部离线，来自 docs/experiments/raw/）：
- 两只版 139 笔事件：重建口径=run_portfolio_split.tier_daily（B200 三档
  43.3/56.7，周频信号次一交易日生效，冻结口径）+ 虹吸豁免（融资余额20日
  增速 756 日滚动分位≥90% 连续 20 交易日→空仓档改半仓；锚点校验：
  events=139、sip_on_frac≈0.024 对齐 ashare_axes_results B_DUO）。
  窗口 2010-06-02→2026-08-18（WIN_END 冻结）。run_m5_walkforward.tier_for /
  run_ashare_axes.siphon_daily 原实现已随 2026-09-01 回退丢失，重建过程
  双锚点验证，见报告。
- 创业板估值代理：创业板50（399673.SZ）滚动市盈率 PE_TTM，月频月末，
  乐咕乐股 via akshare.stock_index_pe_lg，2009-10→2026-09（204 obs）。
  ⚠ 399006 创业板指本尊估值无公开可得源（akshare 无、东财 dcfm 主机
  不可达、国证官网无公开 API、韭圈儿接口已从 akshare 移除）——声明为
  数据工程欠账。399673 与 399006 同板块大盘股（50/100 只，价格相关
  0.99，近期点位差 +3~8%），作为创业板估值环境代理；不用沪深300冒充。
- 沪深300 PE（同源同频）：仅用于 (a) 代理检验 (b) 错市场安慰剂。
- 中债10Y 月末（东财 datacenter-web EMM00166466，2002→）。
- 前瞻收益：399006 收盘（raw/siphon_detector parquet，截至 2026-08-27）。

估值分位（无前视）：扩张窗口分位 pct_t = #{s≤t: PE_s ≤ PE_t} / n_t，
月频；标注起点 n_t≥36（3 年历史）；事件 d 的标注取最后一个 pe_date<d
的 pct（决策时点信息：信号在上周末收盘决策、事件日语行执行）。
分档：pct<0.30 便宜 / [0.30,0.70) 中性 / ≥0.70 昂贵。
阈值依据（非拍脑袋）：本仓库三档切分惯例（宽度三档 30/70 边界→冠军档位
线 43.3/56.7 的同一收缩框架；融资余额虹吸用 90 分位、利率闸用 85 分位，
均为分位阈值先例），对称于中位数；敏感性另测 1/3-2/3 三分位与 20/80。

前瞻收益：fwd_H = close[i+H]/close[i]−1，H∈{20,60,120} 交易日，
i=事件日在 399006 序列中的位置；事件接近数据尾部不足 H 根时按 H 剔除
（计数入报告）。

判定标准（冻结）：
- H1（主判定，唯一带 PASS 门）：买入事件（▲）fwd60，
  diff = mean(便宜) − mean(昂贵)，双侧置换检验（两组内随机重排标签，
  10000 次，rng seed=20260902）p<0.05 且 |diff|≥3pp → PASS。
  3pp 线沿用 siphon-detector P2 的 spread 门先例。PASS 才进入第二步
  （美股 ERP 同框架）；FAIL 直接归档证伪。
- H2（次要，探索性，无门）：卖出事件（▼）同口径对比，仅报告，多重
  比较不作门。预期方向（若估值调制卖出质量）：昂贵档卖出后续收益更差
  → diff<0，但双侧报告。
- H3（背景）：H1 样本三档 Kruskal-Wallis（omnibus）；便宜 vs 昂贵
  分组 bootstrap 90% CI（组内重抽样 10000 次，同 seed）。
- 阴性对照=上述置换检验本身（打乱估值标签重分组，真实效应须落在
  随机噪音分布之外）；另加错市场安慰剂：同批买入事件改用沪深300 PE
  分位标注做同一对比（诊断共享宏观因子假象，无门）。
- 敏感性（探索性，无门）：S1 三分位阈值；S2 20/80；S3 滚动60月分位；
  S4 ERP=100/PE−中债10Y 分位标注；S5 历史门槛降至24月；S6 fwd20/fwd120；
  S7 聚类去重（60 交易日窗口内同方向只留首笔）。

复现：PYTHONHASHSEED=0 python3 scripts/run_valuation_overlay.py
（运行环境：pandas 3.0.5 / numpy / scipy / pyarrow，见 SOURCES.json）

输出：docs/experiments/raw/valuation_overlay/valuation_overlay_results.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw"
SRC = RAW / "valuation_overlay"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_siphon_detector import weekly_last  # noqa: E402

# ── 冻结参数 ──
START, WIN_END = "2010-06-01", "2026-08-18"
MIN_HIST = 36           # 扩张分位最少月频观测数（3 年）
LO_TH, HI_TH = 0.30, 0.70
N_PERM, N_BOOT = 10000, 10000
SEED = 20260902
SPREAD_GATE = 3.0       # pp，PASS 线
ALPHA = 0.05
HORIZONS = (20, 60, 120)
H_PRIMARY = 60


# ── 两只版事件重建（锚点：events=139 / sip_on_frac≈0.024）──
def siphon_condition_daily() -> pd.Series:
    m = pd.read_csv(RAW / "ashare_axes/margin_sh.csv", parse_dates=["日期"]).set_index("日期")
    bal = m["融资余额"].astype(float).sort_index()
    chg20 = bal.pct_change(20)
    pct = chg20.rolling(756, min_periods=756).apply(
        lambda x: float((x[-1] >= x).mean()), raw=True
    )
    return (pct >= 0.90).fillna(False)


def siphon_daily_rebuilt(dates: pd.DatetimeIndex) -> pd.Series:
    """虹吸：融资余额20日增速756日滚动分位≥90% 连续20交易日。"""
    cond = siphon_condition_daily()
    on = cond.rolling(20).min() == 1.0
    return on.reindex(dates).fillna(False).astype(bool)


def rebuild_events() -> tuple[pd.DatetimeIndex, pd.Series, list[dict]]:
    b200 = rps.load_breadth()
    cyb = pd.read_parquet(RAW / "siphon_detector/cyb_399006_close.parquet")["close"].astype(float)
    cyb.index = pd.to_datetime(cyb.index)
    cyb = cyb[(cyb.index >= pd.Timestamp(START)) & (cyb.index <= pd.Timestamp(WIN_END))]
    dates = cyb.index
    t0 = rps.tier_daily(b200, dates)
    sip = siphon_daily_rebuilt(dates)
    bud = t0.copy()
    bud[(t0 <= 0.001) & sip] = 0.5
    ch = bud.diff().fillna(0)
    ev: list[dict] = []
    for d in dates[ch != 0]:
        i = dates.get_loc(d)
        prev = float(bud.iloc[i - 1]) if i else 1.0
        cur = float(bud.iloc[i])
        ev.append({"date": d, "dir": "buy" if cur > prev else "sell",
                   "prev_w": prev, "cur_w": cur})
    return dates, bud, ev


# ── 估值序列与扩张分位 ──
def load_pe(fname: str, col: str = "滚动市盈率") -> pd.Series:
    df = pd.read_csv(SRC / fname, parse_dates=["日期"])
    s = df.set_index("日期")[col].astype(float)
    return s[s > 0].sort_index()


def expanding_pct(s: pd.Series, min_hist: int = MIN_HIST) -> pd.Series:
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if i + 1 >= min_hist:
            out[i] = float((vals[: i + 1] <= vals[i]).mean())
    return pd.Series(out, index=s.index)


def rolling_pct(s: pd.Series, win: int = 60, min_hist: int = MIN_HIST) -> pd.Series:
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        lo = max(0, i - win + 1)
        w = vals[lo: i + 1]
        if len(w) >= min_hist:
            out[i] = float((w <= vals[i]).mean())
    return pd.Series(out, index=s.index)


def bucket_of(pct: float | None, lo: float = LO_TH, hi: float = HI_TH) -> str | None:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return None
    if pct < lo:
        return "cheap"
    if pct < hi:
        return "neutral"
    return "expensive"


def asof_before(series: pd.Series, d: pd.Timestamp):
    sub = series[series.index < d]
    if sub.empty:
        return None, None
    dt = sub.index[-1]
    return dt, float(sub.iloc[-1])


def label_events(events: list[dict], pct_series: pd.Series) -> list[dict]:
    for e in events:
        dt, pct = asof_before(pct_series, e["date"])
        e["pe_date"] = dt
        e["pct"] = pct
        e["bucket"] = bucket_of(pct)
    return events


def fwd_returns(events: list[dict], close: pd.Series, horizons=HORIZONS) -> list[dict]:
    pos = {d: i for i, d in enumerate(close.index)}
    n = len(close)
    for e in events:
        i = pos.get(e["date"])
        for h in horizons:
            e[f"fwd{h}"] = (float(close.iloc[i + h] / close.iloc[i]) - 1.0) * 100.0 \
                if (i is not None and i + h < n) else None
    return events


# ── 统计 ──
def perm_test(a: np.ndarray, b: np.ndarray, n_perm: int = N_PERM, seed: int = SEED):
    """双侧置换：两组标签随机重排，diff=mean(a)-mean(b)。"""
    obs = float(a.mean() - b.mean())
    rng = np.random.default_rng(seed)
    pool = np.concatenate([a, b])
    na = len(a)
    cnt = 0
    diffs = np.empty(n_perm)
    for k in range(n_perm):
        idx = rng.permutation(len(pool))
        d = pool[idx[:na]].mean() - pool[idx[na:]].mean()
        diffs[k] = d
        if abs(d) >= abs(obs) - 1e-12:
            cnt += 1
    p = (cnt + 1) / (n_perm + 1)
    return obs, p, diffs


def boot_ci(a: np.ndarray, b: np.ndarray, n: int = N_BOOT, seed: int = SEED):
    rng = np.random.default_rng(seed + 1)
    da = rng.choice(a, (n, len(a)), replace=True).mean(axis=1)
    db = rng.choice(b, (n, len(b)), replace=True).mean(axis=1)
    d = da - db
    return float(np.percentile(d, 5)), float(np.percentile(d, 95))


def contrast(events: list[dict], horizon: int = H_PRIMARY,
             buckets: tuple[str, str] = ("cheap", "expensive")) -> dict:
    """两组对比 + 置换 + bootstrap CI（None 自动剔除：无标注或前瞻不足）。"""
    xs = {b: [e[f"fwd{horizon}"] for e in events if e["bucket"] == b
              and e[f"fwd{horizon}"] is not None] for b in ("cheap", "neutral", "expensive")}
    a, b = np.array(xs[buckets[0]]), np.array(xs[buckets[1]])
    out: dict = {"n": {k: len(v) for k, v in xs.items()},
                 "mean": {k: (round(float(np.mean(v)), 4) if len(v) else None)
                          for k, v in xs.items()},
                 "median": {k: (round(float(np.median(v)), 4) if len(v) else None)
                            for k, v in xs.items()}}
    if len(a) < 5 or len(b) < 5:
        out["note"] = "组样本 <5，不作检验"
        out["pass"] = False
        return out
    obs, p, null = perm_test(a, b)
    ci5, ci95 = boot_ci(a, b)
    kw = stats.kruskal(*[np.array(v) for v in xs.values() if len(v) >= 3])
    out.update({
        "diff_ce": round(obs, 4), "perm_p": round(p, 5),
        "null_p95_abs": round(float(np.percentile(np.abs(null), 95)), 4),
        "boot_ci90": [round(ci5, 4), round(ci95, 4)],
        "kw_p": round(float(kw.pvalue), 5),
        "pass": bool(p < ALPHA and abs(obs) >= SPREAD_GATE),
    })
    return out


def main() -> None:
    # 1) 事件重建 + 锚点
    dates, bud, ev = rebuild_events()
    buys = [e for e in ev if e["dir"] == "buy"]
    sells = [e for e in ev if e["dir"] == "sell"]
    sip_frac = float(siphon_daily_rebuilt(dates).mean())
    anchors = {"n_events": len(ev), "n_buy": len(buys), "n_sell": len(sells),
               "sip_on_frac": round(sip_frac, 4),
               "win": [str(dates[0].date()), str(dates[-1].date())],
               "events_139_ok": len(ev) == 139}

    # 2) 估值序列与代理检验
    pe_cyb = load_pe("pe_cyb50_lg.csv")
    pe_hs = load_pe("pe_hs300_lg.csv")
    cn10 = pd.read_csv(SRC / "cn10y_monthly.csv", parse_dates=[0], index_col=0).iloc[:, 0]
    pct_cyb = expanding_pct(pe_cyb)
    pct_hs = expanding_pct(pe_hs)
    erp_cyb = 100.0 / pe_cyb - cn10.reindex(pe_cyb.index).ffill()
    pct_erp = expanding_pct(erp_cyb.dropna())
    j = pd.DataFrame({"cyb": pct_cyb, "hs": pct_hs}).dropna()
    rho = float(j["cyb"].corr(j["hs"], method="spearman"))
    rho_lvl = float(pe_cyb.reindex(j.index).corr(pe_hs.reindex(j.index), method="spearman"))
    proxy = {"spearman_pct": round(rho, 4), "spearman_level": round(rho_lvl, 4),
             "n_months": len(j),
             "hs300_as_proxy": "rejected(<0.80)" if rho < 0.80 else "acceptable(≥0.80)"}

    # 3) 标注 + 前瞻收益
    cyb_full = pd.read_parquet(RAW / "siphon_detector/cyb_399006_close.parquet")["close"].astype(float)
    cyb_full.index = pd.to_datetime(cyb_full.index)
    ev = label_events(ev, pct_cyb)
    ev = fwd_returns(ev, cyb_full)
    n_nahist_buy = sum(1 for e in buys if e["bucket"] is None)
    n_nahist_sell = sum(1 for e in sells if e["bucket"] is None)
    n_tail60_buy = sum(1 for e in buys if e["bucket"] is not None and e[f"fwd{H_PRIMARY}"] is None)

    # 4) 判定
    H1 = contrast(buys, H_PRIMARY)           # 主判定（PASS 门）
    H2 = contrast(sells, H_PRIMARY)          # 次要探索
    # 错市场安慰剂：同批买入事件用沪深300分位标注
    buys_pl = label_events([dict(e) for e in buys], pct_hs)
    placebo = contrast(buys_pl, H_PRIMARY)

    # 5) 敏感性（探索性）
    sens: dict[str, dict] = {}
    for name, (series, lo, hi, min_h, horizon, dedup) in {
        "S1_tercile": (pct_cyb, 1 / 3, 2 / 3, MIN_HIST, H_PRIMARY, False),
        "S2_2080": (pct_cyb, 0.20, 0.80, MIN_HIST, H_PRIMARY, False),
        "S3_roll60m": (rolling_pct(pe_cyb), LO_TH, HI_TH, MIN_HIST, H_PRIMARY, False),
        "S4_erp": (pct_erp, LO_TH, HI_TH, MIN_HIST, H_PRIMARY, False),
        "S5_min24": (expanding_pct(pe_cyb, 24), LO_TH, HI_TH, 24, H_PRIMARY, False),
        "S6a_fwd20": (pct_cyb, LO_TH, HI_TH, MIN_HIST, 20, False),
        "S6b_fwd120": (pct_cyb, LO_TH, HI_TH, MIN_HIST, 120, False),
        "S7_dedup60": (pct_cyb, LO_TH, HI_TH, MIN_HIST, H_PRIMARY, True),
    }.items():
        evs = [dict(e) for e in buys]
        evs = label_events(evs, series)
        for e in evs:  # 阈值重切
            e["bucket"] = bucket_of(e["pct"], lo, hi)
        if dedup:
            keep, last = [], None
            for e in evs:  # 60 交易日内同方向只留首笔（近似：90 日历日）
                if last is None or (e["date"] - last).days > 90:
                    keep.append(e)
                    last = e["date"]
            evs = keep
        evs = fwd_returns(evs, cyb_full)
        sens[name] = contrast(evs, horizon)

    # 6) 事件表落盘（NaN 统一序列化为 null，保持严格 JSON）
    table = [{k: (str(v.date()) if isinstance(v, pd.Timestamp) else
                  (None if isinstance(v, float) and np.isnan(v) else
                   round(v, 6) if isinstance(v, float) else v))
              for k, v in e.items()} for e in ev]

    res = {
        "task": "Prompt T 估值层确认事件研究（两只版139笔）",
        "anchors": anchors,
        "proxy_check": proxy,
        "labeling": {"n_nahist_buy": n_nahist_buy, "n_nahist_sell": n_nahist_sell,
                     "n_tail_drop_buy_fwd60": n_tail60_buy,
                     "bucket_counts_buy": H1.get("n"), "bucket_counts_sell": H2.get("n")},
        "H1_buy_fwd60_PRIMARY": H1,
        "H2_sell_fwd60_secondary": H2,
        "placebo_hs300_labels": placebo,
        "sensitivities": sens,
        "params": {"min_hist": MIN_HIST, "lo": LO_TH, "hi": HI_TH,
                   "n_perm": N_PERM, "n_boot": N_BOOT, "seed": SEED,
                   "spread_gate_pp": SPREAD_GATE, "alpha": ALPHA,
                   "horizons": list(HORIZONS)},
        "events": table,
    }
    out = SRC / "valuation_overlay_results.json"
    txt = json.dumps(res, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    out.write_text(txt)
    h = hashlib.sha256(txt.encode()).hexdigest()
    print("written:", out)
    print("sha256:", h)
    print("anchors:", anchors)
    print("proxy:", proxy)
    print("H1:", json.dumps(H1, ensure_ascii=False))
    print("H2:", json.dumps(H2, ensure_ascii=False))
    print("placebo:", json.dumps(placebo, ensure_ascii=False))
    for k, v in sens.items():
        print(k, "diff_ce=", v.get("diff_ce"), "p=", v.get("perm_p"), "n=", v.get("n"))


if __name__ == "__main__":
    main()
