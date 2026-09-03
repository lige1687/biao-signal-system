#!/usr/bin/env python3
"""Prompt U · 美股 ERP 确认层事件研究（预注册 2026-09-02，跑前写死，跑后不改）。

背景：Prompt T（A股估值分位确认层）已证伪（置换 p=0.981，敏感性 8 项全无效），
按其预注册纪律"第一步 FAIL 则不测美股腿"，本任务单独补测从未执行的第二步：
同一假设（估值分位作为宽度择时信号的确认层）在美股侧是否成立。A股/美股
估值-宽度关系可能本质不同，不能照搬证伪结论，需独立验证。

【预注册协议】

数据（全部离线）：
- 美股估值：S&P500 盈利收益率 EY 月频 1871→2026-09，multpl.com by-month 表
  （生产 fetch_us_erp() 主源同族；表内带 † 的估计值如实保留）。
  行情月"Mmm 1, YYYY"记为该月**月末**（保守无前视：真实测度即使为月初，
  也只用下一月起的信息，宁迟勿早）。
- 无风险利率：美债10Y 日频 1962→2026-08-31，FRED DGS10（官方），取每月末。
- ERP = EY − DGS10（%），月频；与生产 fetch_us_erp() 同一定义（multpl EY − us10y）。
  yfinance trailingPE 无历史（Prompt 预判的数据欠账成立）——但 multpl/FRED
  提供真实历史序列，无需插值/合成。FRED SP500EY 端点已 404（弃用），如实用
  multpl 表替代（已在 SOURCES.json 备案）。
- 信号源一（防守版 SPY 档）：momentum 三档 40/80（档位线 53.3/66.7）、
  gamma=1.5（档位权重 0/0.5^1.5/1）、vol_target=0.15、MA200 闸（cap=0）、
  fee 10bp、min_trade=0.05——已认证配置（us_edges_GSPC.csv 40/80 vol0.15
  gamma1.5 行与 raw/kuandu-quanzhan/us_defense.json 指标逐位一致：
  CAGR 0.050938080239245176 / MDD -0.20361346650430556）。
  ⚠ 宽度 breadth_sp500.parquet 已随 2026-09-01 回退丢失，无法重算档位；
  本脚本从认证产物 us_defense.json 的逐日 equity 序列（10241 天）+ 保留的
  ^GSPC OHLC（raw/module_e/）+ 引擎精确机制（src/lei_signal/timing_backtest/
  engine.py 逐行口径）**反演**逐日执行权重与档位：束搜索（束宽 3/10/20
  结果必须逐日一致，否则 abort），按引擎精确费用/涨跌停口径前向模拟，
  拟合 RMS/天 <1e-6 且终值误差 <1e-4 为通过门（反演不是合成数据——恢复
  的是认证运行自身的执行决策序列）。
- 信号源二（模块 E 手册口径）：已认证信号清单 raw/module_e/
  us_event_signals_v1_hedge0.csv（v1 双线 B20/B50≤15，33 笔）与
  us_event_signals_v3_hedge50.csv（v3 三线 ≤15，14 笔），次日开盘执行，
  exec_date 为事件日。
- 前瞻收益：^GSPC 收盘（raw/module_e/us_gspc_ohlc.parquet，auto_adjust），
  H∈{20,60,120} 交易日，尾部不足 H 者剔除并计数。
- 安慰剂标签：创业板50 PE_TTM 扩张分位（Prompt T raw，只读复用）——
  错市场安慰剂。

ERP 分位（无前视）：扩张窗口分位 pct_t = #{s≤t: ERP_s ≤ ERP_t}/n_t，月频，
标注起点 n_t≥36；事件 d 的标注取最后一个月末 <d 的 pct（决策时点信息，
继承 Prompt T 规避"全样本分位前视"的同一纪律）。
分档：pct<0.30 便宜 / [0.30,0.70) 中性 / ≥0.70 昂贵（阈值依据与 T 相同：
本仓库分位阈值先例 30/70 对称框架）。

判定标准（冻结）：
- H1-A（主判定·防守版）：防守版**加仓事件**（有效档位上行，含 MA200 闸
  重开与档位上穿）fwd60，diff = mean(便宜) − mean(昂贵)，双侧置换检验
  （10000 次，rng seed=20260902）p<0.05 且 |diff|≥3pp → PASS。
- H1-B（主判定·模块E v1）：v1 买入信号 fwd60，同 diff 定义同 PASS 线。
  两个主判定各自带门，结果不一致时如实并列报告，不选择性引用。
- H1-C（次要）：模块E v3（n=14，组样本<5 时声明"不作检验"）。
- H2（次要，探索性，无门）：防守版**减仓事件** fwd60 同口径，仅报告。
- H3（背景）：主判定样本三档 Kruskal-Wallis；便宜 vs 昂贵 bootstrap 90% CI
  （组内重抽样 10000 次，seed+1）。
- 阴性对照=置换检验本身；另加错市场安慰剂（创业板50 PE 分位标注同批事件）。
- 敏感性（探索性，无门）：S1 三分位 1/3-2/3；S2 20/80；S3 EY-only 分位
  （剥离利率项——红线1"ERP含利率"的结构性诊断）；S4 美债10Y-only 分位
  （利率-only 诊断：若利率分位也能分层则效应属利率非估值）；S5 fwd20；
  S6 fwd120；S7 90 日历日去重。全部同时跑在 H1-A 与 H1-B 两个事件集上。
- 组样本 <5 不作检验（继承 T）。
- 冗余度检查：防守版月末有效档位（0/1/2）× ERP 分位 Spearman（T 的
  B200×估值正交性检查对应物）。

复现：PYTHONHASHSEED=0 python3 scripts/run_us_erp_overlay.py
（运行环境：pandas 3.0.5 / numpy 2.5.2 / scipy 1.18.1 / pyarrow 25.0.1，
与 Prompt T 同版本族，见 SOURCES.json）

输出：docs/experiments/raw/us_erp_overlay/us_erp_overlay_results.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw"
SRC = RAW / "us_erp_overlay"

# ── 冻结参数（继承 Prompt T）──
MIN_HIST = 36           # 扩张分位最少月频观测数（3 年）
LO_TH, HI_TH = 0.30, 0.70
N_PERM, N_BOOT = 10000, 10000
SEED = 20260902
SPREAD_GATE = 3.0       # pp，PASS 线
ALPHA = 0.05
HORIZONS = (20, 60, 120)
H_PRIMARY = 60
MIN_GROUP = 5           # 组样本 <5 不作检验

# 防守版认证配置（冻结）
GAMMA = 1.5
L1 = 0.5 ** 1.5
LEVELS = np.array([0.0, L1, 1.0])
VOL_TARGET = 0.15
FEE = 0.001             # fee_bps=10 → 0.001
MIN_TRADE = 0.05


# ══ 1. ERP 历史序列 ══
def load_ey_monthly() -> pd.Series:
    html = (SRC / "us_ey_multpl.html").read_text()
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
    out = {}
    for r in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        if len(cells) < 2:
            continue
        m = re.match(r"\s*([A-Z][a-z]{2}) 1, (\d{4})\s*$", cells[0])
        if not m:
            continue
        val = re.search(r"(\d+\.\d+)%", re.sub(r"<[^>]*>", "", cells[1]))
        if not val:
            continue
        ts = pd.Timestamp(f"{int(m.group(2))}-{m.group(1)}-01") + pd.offsets.MonthEnd(0)
        out[ts] = float(val.group(1))
    s = pd.Series(out).sort_index()
    return s[~s.index.duplicated(keep="last")]


def load_us10y_monthend() -> pd.Series:
    df = pd.read_csv(SRC / "us10y_dgs10_daily.csv", parse_dates=[0], index_col=0)
    s = df.iloc[:, 0]
    s = s[s > 0].sort_index()
    last = s.groupby([s.index.year, s.index.month]).last()
    idx = pd.to_datetime(["%d-%d-01" % (y, m) for y, m in last.index]) \
        + pd.offsets.MonthEnd(0)
    last.index = pd.DatetimeIndex(idx)
    return last


def expanding_pct(s: pd.Series, min_hist: int = MIN_HIST) -> pd.Series:
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if i + 1 >= min_hist:
            out[i] = float((vals[: i + 1] <= vals[i]).mean())
    return pd.Series(out, index=s.index)


# ══ 2. 防守版事件反演（束搜索，引擎精确口径）══
def invert_defense() -> dict:
    d = json.loads((RAW / "kuandu-quanzhan/us_defense.json").read_text())
    g = d["instruments"]["^GSPC"]
    dates = pd.to_datetime(g["daily"]["date"])
    eq = np.array(g["daily"]["equity"], dtype=float)
    bench = np.array(g["daily"]["benchmark"], dtype=float)
    bars = pd.read_parquet(RAW / "module_e/us_gspc_ohlc.parquet")
    bars = bars[~bars.index.duplicated(keep="last")].sort_index().reindex(dates)
    if bars["close"].isna().any():
        raise SystemExit("反演前置失败：认证日历日与保留 OHLC 不齐")
    op = bars["open"].to_numpy(dtype=float)
    cl = bars["close"].to_numpy(dtype=float)
    n = len(eq)

    # 锚点1：基准比率同一性（认证运行的 close == 保留 close，比例层面）
    rb = bench[1:] / bench[:-1]
    rc = cl[1:] / cl[:-1]
    rel = np.abs(rb / rc - 1.0)
    if np.percentile(rel, 99) > 1e-5:
        raise SystemExit("反演前置失败：基准与 OHLC 比率不同一")

    close_s = pd.Series(cl, index=dates)
    realized = close_s.pct_change().rolling(20, min_periods=20).std() * np.sqrt(252.0)
    scale = (VOL_TARGET / realized).clip(upper=1.0).fillna(1.0).to_numpy()
    ma200 = close_s.rolling(200, min_periods=200).mean()
    gate = np.where(ma200.isna() | (close_s >= ma200), 1.0, 0.0)

    def feas(s: int) -> list[tuple[int, float]]:
        if gate[s] == 0.0:
            return [(0, 0.0)]
        return [(t, float(min(LEVELS[t] * scale[s], 1.0))) for t in (0, 1, 2)]

    def beam(K: int):
        branches = [(0.0, 1.0, 0.0, 0.0, [None])]
        for i in range(1, n):
            s = i - 1
            eqi = eq[i]
            r = cl[i] / op[i]
            newb = []
            for cum, cash, units, w_prev, acts in branches:
                eq_open = cash + units * op[i]
                pred = cash + units * cl[i]
                newb.append((cum + (pred - eqi) ** 2, cash, units, w_prev,
                             acts + [None]))
                for tier, w in feas(s):
                    if abs(w - w_prev) <= MIN_TRADE:
                        continue
                    e = eq_open * (1 - abs(w - w_prev) * FEE)
                    pred = e * (1 - w + w * r)
                    newb.append((cum + (pred - eqi) ** 2, e * (1 - w),
                                 e * w / op[i], w, acts + [tier]))
            best = {}
            for b in newb:
                key = (round(b[3], 5), round(b[1], 4), round(b[2], 8))
                if key not in best or b[0] < best[key][0]:
                    best[key] = b
            branches = sorted(best.values(), key=lambda x: x[0])[:K]
        return branches[0]

    seqs = {}
    for K in (3, 10, 20):
        cum, cash, units, _, acts = beam(K)
        eff = np.zeros(n - 1, dtype=int)
        last = 0
        for s in range(n - 1):
            a = acts[s + 1]
            if a is not None:
                last = int(a)
            eff[s] = 0 if gate[s] == 0.0 else last
        seqs[K] = eff
        rms = float((cum / n) ** 0.5)
        final_err = abs(float(cash + units * cl[-1]) - eq[-1])
    # 反演通过门（冻结）：束宽无关 + RMS + 终值
    if not (np.array_equal(seqs[3], seqs[10]) and np.array_equal(seqs[10], seqs[20])):
        raise SystemExit("反演失败：束宽 3/10/20 事件序列不一致")
    if rms >= 1e-6 or final_err >= 1e-4:
        raise SystemExit(f"反演失败：rms={rms:.2e} final_err={final_err:.2e}")

    eff = seqs[10]
    chg = np.diff(eff)
    ev_idx = np.nonzero(chg != 0)[0]
    events = []
    for k in ev_idx:
        s = int(k)
        events.append({
            "date": dates[s + 1],            # 执行日（引擎 T 收盘信号 → T+1 开盘）
            "sig_date": dates[s],
            "dir": "buy" if chg[k] > 0 else "sell",
            "prev_tier": int(eff[k]),
            "cur_tier": int(eff[k + 1]),
            "gate_flip": bool(gate[s + 1] != gate[s]) or bool(gate[s] != gate[s - 1]) if s >= 1 else False,
        })
    n_trades = int(sum(1 for a in acts[1:] if a is not None))
    return {
        "events": events,
        "eff_tier": pd.Series(eff, index=dates[:-1]),
        "dates": dates,
        "close": close_s,
        "validation": {
            "rms_per_day": rms,
            "final_equity_err": final_err,
            "beam_unique_k3_k10_k20": True,
            "n_trades_recovered": n_trades,
            "n_days": int(n),
            "window": [str(dates[0].date()), str(dates[-1].date())],
            "final_eff_tier": int(eff[-1]),
        },
    }


# ══ 3. 标注 / 前瞻收益 / 统计（复用 Prompt T 逻辑）══
def bucket_of(pct, lo: float = LO_TH, hi: float = HI_TH):
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
    return sub.index[-1], float(sub.iloc[-1])


def label_events(events: list[dict], pct_series: pd.Series) -> list[dict]:
    for e in events:
        dt, pct = asof_before(pct_series, e["date"])
        e["val_date"] = dt
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


def perm_test(a: np.ndarray, b: np.ndarray, n_perm: int = N_PERM, seed: int = SEED):
    obs = float(a.mean() - b.mean())
    rng = np.random.default_rng(seed)
    pool = np.concatenate([a, b])
    na = len(a)
    cnt = 0
    diffs = np.empty(n_perm)
    for k in range(n_perm):
        idx = rng.permutation(len(pool))
        dd = pool[idx[:na]].mean() - pool[idx[na:]].mean()
        diffs[k] = dd
        if abs(dd) >= abs(obs) - 1e-12:
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
    xs = {b: [e[f"fwd{horizon}"] for e in events if e["bucket"] == b
              and e[f"fwd{horizon}"] is not None] for b in ("cheap", "neutral", "expensive")}
    a, b = np.array(xs[buckets[0]]), np.array(xs[buckets[1]])
    out: dict = {"n": {k: len(v) for k, v in xs.items()},
                 "mean": {k: (round(float(np.mean(v)), 4) if len(v) else None)
                          for k, v in xs.items()},
                 "median": {k: (round(float(np.median(v)), 4) if len(v) else None)
                            for k, v in xs.items()}}
    if len(a) < MIN_GROUP or len(b) < MIN_GROUP:
        out["note"] = f"组样本 <{MIN_GROUP}，不作检验"
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


def dedup90(events: list[dict]) -> list[dict]:
    keep, last = [], None
    for e in events:
        if last is None or (e["date"] - last).days > 90:
            keep.append(e)
            last = e["date"]
    return keep


def sanitize(o):
    if isinstance(o, dict):
        return {k: sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if np.isnan(f) else round(f, 6)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


# ══ 主流程 ══
def main() -> None:
    # 1) ERP 序列
    ey = load_ey_monthly()
    us10 = load_us10y_monthend()
    erp = ey - us10.reindex(ey.index).ffill()
    pct_erp = expanding_pct(erp.dropna())
    pct_ey = expanding_pct(ey)
    pct_10y = expanding_pct(us10.reindex(ey.index).ffill())
    # 安慰剂：创业板50 PE 分位（Prompt T raw 只读复用）
    pe_cyb = pd.read_csv(RAW / "valuation_overlay/pe_cyb50_lg.csv",
                         parse_dates=["日期"]).set_index("日期")["滚动市盈率"].astype(float)
    pe_cyb = pe_cyb[pe_cyb > 0].sort_index()
    pct_cyb = expanding_pct(pe_cyb)
    data_summary = {
        "ey_range": [str(ey.index[0].date()), str(ey.index[-1].date()), len(ey)],
        "dgs10_range": [str(us10.index.min().date()), str(us10.index.max().date()), len(us10)],
        "erp_range": [str(erp.dropna().index[0].date()), str(erp.dropna().index[-1].date()),
                      int(erp.notna().sum())],
        "pct_available_from": str(pct_erp.dropna().index[0].date()),
    }

    # 2) 防守版事件（反演）
    dfn = invert_defense()
    close = dfn["close"]
    def_events = dfn["events"]
    def_buys = [dict(e) for e in def_events if e["dir"] == "buy"]
    def_sells = [dict(e) for e in def_events if e["dir"] == "sell"]

    # 3) 模块E事件（已认证清单）
    def load_me(fname: str) -> list[dict]:
        csv = pd.read_csv(RAW / f"module_e/{fname}", parse_dates=["exec_date"])
        return [{"date": d, "sig_date": d} for d in csv["exec_date"]]
    me_v1 = load_me("us_event_signals_v1_hedge0.csv")
    me_v3 = load_me("us_event_signals_v3_hedge50.csv")

    # 4) 标注 + 前瞻
    for evs in (def_events, def_buys, def_sells, me_v1, me_v3):
        label_events(evs, pct_erp)
        fwd_returns(evs, close)

    # 5) 判定
    H1A = contrast(def_buys, H_PRIMARY)
    H1B = contrast(me_v1, H_PRIMARY)
    H1C = contrast(me_v3, H_PRIMARY)
    H2 = contrast(def_sells, H_PRIMARY)

    # 错市场安慰剂（两个主判定事件集）
    pl_a = contrast(label_events([dict(e) for e in def_buys], pct_cyb), H_PRIMARY)
    pl_b = contrast(label_events([dict(e) for e in me_v1], pct_cyb), H_PRIMARY)

    # 冗余度：防守版月末有效档位 × ERP 分位
    mo = dfn["eff_tier"].groupby([dfn["eff_tier"].index.year,
                                  dfn["eff_tier"].index.month]).last()
    mo.index = pd.to_datetime(["%d-%d-01" % (y, m) for y, m in mo.index]) + pd.offsets.MonthEnd(0)
    j = pd.DataFrame({"tier": mo, "pct": pct_erp}).dropna()
    ortho = {
        "spearman_tier_vs_erp_pct": round(float(j["tier"].corr(j["pct"], method="spearman")), 4),
        "n_months": len(j),
    }

    # 敏感性（H1-A 与 H1-B 两套事件集）
    sens: dict[str, dict] = {}
    for tag, evs in (("A_defense", def_buys), ("B_moduleE_v1", me_v1)):
        base = label_events([dict(e) for e in evs], pct_erp)
        for name, (series, lo, hi, horizon, dd) in {
            "S1_tercile": (pct_erp, 1 / 3, 2 / 3, H_PRIMARY, False),
            "S2_2080": (pct_erp, 0.20, 0.80, H_PRIMARY, False),
            "S3_ey_only": (pct_ey, LO_TH, HI_TH, H_PRIMARY, False),
            "S4_us10y_only": (pct_10y, LO_TH, HI_TH, H_PRIMARY, False),
            "S5_fwd20": (pct_erp, LO_TH, HI_TH, 20, False),
            "S6_fwd120": (pct_erp, LO_TH, HI_TH, 120, False),
            "S7_dedup90": (pct_erp, LO_TH, HI_TH, H_PRIMARY, True),
        }.items():
            evs2 = label_events([dict(e) for e in evs], series)
            for e in evs2:
                e["bucket"] = bucket_of(e["pct"], lo, hi)
            if dd:
                evs2 = dedup90(evs2)
            evs2 = fwd_returns(evs2, close)
            sens.setdefault(name, {})[tag] = contrast(evs2, horizon)

    # 6) 落盘
    res = {
        "task": "Prompt U 美股ERP确认层事件研究（防守版SPY档 + 模块E）",
        "params": {"min_hist": MIN_HIST, "lo": LO_TH, "hi": HI_TH,
                   "n_perm": N_PERM, "n_boot": N_BOOT, "seed": SEED,
                   "spread_gate_pp": SPREAD_GATE, "alpha": ALPHA,
                   "horizons": list(HORIZONS), "min_group": MIN_GROUP,
                   "defense_cfg": {"momentum_3band_40_80": True, "gamma": GAMMA,
                                   "vol_target": VOL_TARGET, "gate": "ma200_cap0",
                                   "fee_bps": 10, "min_trade": MIN_TRADE}},
        "data_summary": data_summary,
        "defense_inversion": dfn["validation"],
        "events_summary": {
            "defense_total": len(def_events),
            "defense_buys": len(def_buys),
            "defense_sells": len(def_sells),
            "module_e_v1": len(me_v1),
            "module_e_v3": len(me_v3),
        },
        "H1A_defense_buy_fwd60_PRIMARY": H1A,
        "H1B_moduleE_v1_buy_fwd60_PRIMARY": H1B,
        "H1C_moduleE_v3_fwd60_secondary": H1C,
        "H2_defense_sell_fwd60_secondary": H2,
        "placebo_cyb50_labels": {"H1A_set": pl_a, "H1B_set": pl_b},
        "orthogonality": ortho,
        "sensitivities": sens,
        "events": {
            "defense": sanitize(def_events),
            "module_e_v1": sanitize(me_v1),
            "module_e_v3": sanitize(me_v3),
        },
    }
    out = SRC / "us_erp_overlay_results.json"
    txt = json.dumps(sanitize(res), ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"))
    out.write_text(txt)
    h = hashlib.sha256(txt.encode()).hexdigest()
    print("written:", out)
    print("sha256:", h)
    print("inversion:", json.dumps(dfn["validation"], ensure_ascii=False))
    print("events:", res["events_summary"])
    print("H1A:", json.dumps(H1A, ensure_ascii=False))
    print("H1B:", json.dumps(H1B, ensure_ascii=False))
    print("H1C:", json.dumps(H1C, ensure_ascii=False))
    print("H2:", json.dumps(H2, ensure_ascii=False))
    print("placebo:", json.dumps({"A": pl_a, "B": pl_b}, ensure_ascii=False))
    print("ortho:", json.dumps(ortho, ensure_ascii=False))
    for k, v in sens.items():
        for tag, c in v.items():
            print(k, tag, "diff_ce=", c.get("diff_ce"), "p=", c.get("perm_p"),
                  "n=", c.get("n"))


if __name__ == "__main__":
    main()
