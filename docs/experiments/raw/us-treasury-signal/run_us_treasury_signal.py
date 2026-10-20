"""美债 10Y / 收益率曲线做美股触发信号 · 探索实验（2026-09-01，Prompt A）。

背景：现有美股信号只用过宽度极值（模块 E）与 ETF 宽度防守，从未用利率类数据
做触发。本轮用东财国债接口的 us_10y / us_10_2_spread（10Y-2Y 利差）测三个
触发层候选。**触发层 = 买卖事件的产生**，与已证伪的"利率档位闸"（中债 10Y
滚动分位→仓位打折，lei-ARCHIVE 第二节）机制不同，本轮不碰仓位系数。

判定标准（事前写死，跑之前落 docstring，跑完不许改）：
- JA（C1 倒挂解除买入触发）：
  - JA1 信息量主判（^GSPC）：事件数 n≥5 才判；mean 12m 前瞻 > 基线 mean 12m
    且 mean 6m 前瞻 > 基线 mean 6m → 通过；mean 12m < 基线 → 证伪（信息反向）；
    其余 → 观察。n<5 → 只报告不判定（沿用 module-e J2 的 n≥5 门槛）。
  - JA2 配置回测（每事件投剩余现金 50%，单边 5bp，无对冲，vs S1 周定投）：
    仅当 JA1 可判定且通过时才判定（终值 ≥ S1 → 通过）；否则 report-only。
  - JA3 QQQ 交叉：同 JA1 口径，n≥5 才判，只标稳健性不定生死。
- JB（C2 10Y 20 日利率冲击·波动预警）：
  - JB1 波动主判（上行臂，^GSPC）：n≥5 且事件后 60 交易日前瞻已实现波动
    （年化）均值 ≥ 全基线同口径均值 × 1.15 → 通过；n<5 只报告。
  - JB1b 方向特异性：下行臂同线检验，若下行臂也过线 → JB1 降级
    「方向不敏感的波动聚类」，记观察、不得采纳为触发信号。
  - JB2 收益侧（上行臂）：n≥5 且事件后 6m 前瞻均值 < 基线 6m 均值
    → 风险预警信息为真（辅助线，单独不采纳）。
  - JB3 触发层回测（report-only）：上行冲击后避开权益 60 交易日（执行日
    开盘离场/窗口末开盘回场，单边 5bp），敏感性 20/126 交易日；
    二元进出=触发层测试，不是仓位系数。
- JC（C3 老化倒挂里程碑，持续倒挂 ≥300 交易日）：预登记为只报告不判定
  （预期 n≈2）；若意外 n≥5，同 JA1 线判定。
- CON（阴性对照，事前）：
  - CON1 安慰剂（^GSPC，主对照）：对进入判定的统计量（JA1 的 mean 12m、
    JB1 的 mean 60d 波动），以同数量随机执行日（同资格日集均匀抽样，
    rng=np.random.default_rng(20260901)，2000 组）构造分布；真实统计量
    ≥95 分位 → 非泛化噪音；90~95 → 边缘（主判降观察）；<90 → 泛化噪音嫌疑
    （主判不得通过）。JB2 若进入判定用下侧分位（≤5 分位）。
  - CON2 跨资产（CSI300，辅助）：同窗口套 CSI300（2016-08 起）；若与 ^GSPC
    同号且效应量 ≥ ^GSPC 效应的 50% → 标「跨资产泛化嫌疑」。C1 在 CSI300
    上预期 n≈1，只报告。黄金不作对照：实际利率通道直接驱动金价，
    对照被机制污染（此选择本身也是事前的）。

候选定义（事前）：
- C1 倒挂解除：倒挂段=spread<0 的连续 run（允许 ≤5 个观测的正值打断，桥接）；
  段长=负值观测数；解除日=段末负值后首个 spread>0 且此后连续 10 个观测
  spread>0 的确认日。事件=解除日（此前段长 ≥ min_len，主判 60 交易日，
  敏感性 0/40/80；段长 <60 的短闪挂不触发）。1989 年倒挂在数据起点
  （1990-12-19）之前，损失该事件，口径内声明。
- C2 利率冲击：d20 = us_10y[t] − us_10y[t−20]（净序列位次差）；分位=
  d20[t] 在 d20[0..t−1]（仅过去）中的秩 ×100，t≥1260（约 5 年最小历史）
  才有效——扩张窗口防全样本分位前视（红线案例教训）。事件=armed 且
  分位 ≥95（上行臂）/ ≤5（下行臂）；触发后 disarm，分位回落到 ≤90/≥10
  连续 60 观测后 re-arm（滞回防簇集）。敏感性分位线 93/97（re-arm=线−5）。
- C3 老化倒挂：倒挂段（同 C1 桥接口径）内负值观测数首次 ≥300 的当日，
  每段一个事件；另报「老化段（≥300）的解除日」子集（= prompt 的
  「倒挂解除后 N 日」事件研究口径）。

口径：
- 信号日（国债日）收盘确认 → 下一价格交易日开盘执行（沿 module-e）。
- 前瞻收益 fwd_ret_H(i)=close[i+H]/open[i]−1；fwd_vol_W(i)=std(ln c_t/c_{t−1},
  t=i+1..i+W)×√252；fwd_dd(i)=min_{j∈[i,i+252]} close[j]/max(open[i],
  max_{k∈[i,j]} close_k)−1。基线=同公式逐日（各候选的资格日集：C1/C3=全窗
  交易日且余量 ≥370 自然日；C2=扩张分位有效起点之后的同范围日）。
- 窗口：1991-01-02→价格序列末（国债起点后首个交易日）；H∈{1m:21,3m:63,
  6m:126,12m:252,24m:504} 交易日；OOS=执行日>2024-08-27（沿 module-e）。
- 费用：模拟单边 5bp；事件研究不含费。

数据（全部落 raw 目录缓存，首跑联网一次，之后离线可复跑）：
- 国债：src/lei_signal/fundamentals/sources.py::fetch_treasury_history（东财
  RPTA_WEB_TREASURYYIELD，只读导入，不改引擎）。2026-09-01 实测全史 9,332 行、
  1990-12-19→2026-08-31；us_10_2_spread 与 us_10y−us_2y 逐日差=0（同源派生）；
  美债字段空值 402 行（中美混合日历的中方单独行），剔除。
- ^GSPC / QQQ：复用 module_e raw 缓存（yfinance auto_adjust，1985-01-02 /
  1999-03-10 → 2026-08-26；价格指数不含股息，信号与基线同源自洽）。
  本轮不刷新——离线复现优先（截至 2026-08-26 声明）。
- CSI300：~/.lei_signal_lab/backtest_pool/000300.SS.bars.parquet
  （2016-08-24→2026-08-24，OHLC）。

输出：本目录（docs/experiments/raw/us-treasury-signal/）
- us_treasury_results.json（全臂+判定+安慰剂）
- treasury_history.parquet / {gspc,qqq,csi300}_ohlc.parquet（数据缓存）
- c{1,2_up,2_down,3_milestone,3_release}_events.csv（事件明细+前瞻收益）
- hash_<seed>.json（每次运行的 SHA256，双跑核对用）

复现：PYTHONHASHSEED=0 python3 run_us_treasury_signal.py（约 1 分钟）
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
MODULE_E_RAW = REPO / "docs/experiments/raw/module_e"
POOL = Path.home() / ".lei_signal_lab/backtest_pool"

COST = 0.0005            # 单边 5bp（沿 module-e）
TRANCHE = 0.50           # C1 配置回测：每事件投剩余现金 50%（沿 module-e E3）
CAPITAL = 1_000_000.0
HORIZONS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252, "24m": 504}
WIN_START = pd.Timestamp("1991-01-02")   # 国债数据 1990-12-19 起点之后首个交易日
OOS_CUT = pd.Timestamp("2024-08-27")     # 沿 module-e：末日回推 2 年

# C1 倒挂解除
BRIDGE_MAX = 5           # 倒挂段允许的正值打断（桥接）观测数
CONFIRM_K = 10           # 解除确认：连续 K 个观测 spread>0
C1_MAIN = 60             # 主判最小段长（负值观测数）
C1_SENS = (0, 40, 80)    # 敏感性段长
# C2 利率冲击
D20 = 20                 # 10Y 20 日变动
MIN_HIST = 1260          # 扩张分位最小历史（≈5 年）
PCT_MAIN = 95            # 主判分位线（上行 ≥95 / 下行 ≤5）
PCT_SENS = (93, 97)
REARM_DROP = 5           # 滞回：分位回落到 线−5 之外
REARM_DAYS = 60          # 连续 60 观测后 re-arm
VOL_W = 60               # JB1 前瞻波动窗口（交易日）
VOL_LINE = 1.15          # JB1：事件后波动 ≥ 基线 ×1.15
AVOID_MAIN = 60          # JB3 避开窗口（交易日）
AVOID_SENS = (20, 126)
# C3 老化倒挂
AGED_TD = 300            # 持续倒挂阈值（负值观测数）
# 对照
PLACEBO_N = 2000
PLACEBO_SEED = 20260901
PLACEBO_PASS = 95.0      # CON1 通过分位线
PLACEBO_EDGE = 90.0      # CON1 边缘下限


# ---------------------------------------------------------------- 数据


def load_treasury() -> pd.DataFrame:
    """东财中美国债全史（只读导入 repo 模块），缓存 parquet。"""
    f = RAW / "treasury_history.parquet"
    if f.exists():
        df = pd.read_parquet(f)
    else:
        sys.path.insert(0, str(REPO / "src"))
        from lei_signal.fundamentals.sources import fetch_treasury_history
        hist = fetch_treasury_history(20000)  # 全史（2026-09 实测 9,332 行）
        df = pd.DataFrame.from_dict(hist, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.to_parquet(f)
    df = df[["us_2y", "us_10y", "us_10_2_spread"]].astype(float)
    return df.dropna()  # 剔除中方单独日历行（us 字段缺失）


def load_price(cache_name: str, src: Path) -> pd.DataFrame:
    """OHLC 缓存：本 raw 目录 → 外部缓存复制（只读源，副本落本目录）。"""
    f = RAW / cache_name
    if not f.exists():
        if not src.exists():
            raise FileNotFoundError(f"缺少价格缓存：{src}")
        df = pd.read_parquet(src)
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df[["open", "close"]].astype(float).to_parquet(f)
    df = pd.read_parquet(f)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["open", "close"]].astype(float)


# ---------------------------------------------------------------- 信号


def invert_episodes(spread: pd.Series) -> list[dict]:
    """倒挂段清单（桥接 ≤BRIDGE_MAX 个正值观测）；返回每段 {start,last_neg,n_neg}。"""
    eps: list[dict] = []
    cur: dict | None = None
    for d, v in spread.items():
        if v < 0:
            if cur is None:
                cur = {"start": d, "last_neg": d, "n_neg": 0, "gap": 0}
            cur["n_neg"] += 1
            cur["last_neg"] = d
            cur["gap"] = 0
        elif cur is not None:
            cur["gap"] += 1
            if cur["gap"] > BRIDGE_MAX:
                eps.append(cur)
                cur = None
    if cur is not None:
        eps.append(cur)  # 末端仍倒挂（无解除）
    return eps


def confirmed_release(spread: pd.Series, after: pd.Timestamp) -> pd.Timestamp | None:
    """after 之后首个 spread>0 且连续 CONFIRM_K 个观测 >0 的确认日。"""
    vals, idx = spread.values, spread.index
    for i in np.flatnonzero(idx > after):
        if vals[i] > 0 and i + CONFIRM_K < len(vals) \
                and (vals[i + 1:i + CONFIRM_K + 1] > 0).all():
            return idx[i]
    return None


def c1_events(spread: pd.Series, min_len: int) -> list[pd.Timestamp]:
    """C1：段长 ≥min_len 的倒挂段的确认解除日。"""
    out = []
    for ep in invert_episodes(spread):
        if ep["n_neg"] >= min_len:
            rel = confirmed_release(spread, ep["last_neg"])
            if rel is not None:
                out.append(rel)
    return sorted(out)


def c3_events(spread: pd.Series) -> tuple[list[pd.Timestamp], list[pd.Timestamp]]:
    """C3：段内负值数首破 AGED_TD 的当日（每段一枚）+ 老化段（≥AGED_TD）的解除日。"""
    aged_days, aged_releases = [], []
    for ep in invert_episodes(spread):
        if ep["n_neg"] >= AGED_TD:
            seg = spread.loc[ep["start"]:ep["last_neg"]]
            neg_days = seg.index[seg.values < 0]
            aged_days.append(neg_days[AGED_TD - 1])
            rel = confirmed_release(spread, ep["last_neg"])
            if rel is not None:
                aged_releases.append(rel)
    return sorted(aged_days), sorted(aged_releases)


def expanding_pct(x: pd.Series, min_hist: int) -> pd.Series:
    """t 日分位 = x[t] 在 x[0..t-1]（仅过去）的秩 ×100，防全样本前视。"""
    v = x.values
    out = np.full(len(v), np.nan)
    for i in range(min_hist, len(v)):
        if np.isnan(v[i]):
            continue
        h = v[:i]
        h = h[~np.isnan(h)]
        if len(h) >= min_hist - 1:
            out[i] = float((h < v[i]).sum() / len(h) * 100.0)
    return pd.Series(out, index=x.index)


def c2_events(pct: pd.Series, hi: bool, line: float) -> list[pd.Timestamp]:
    """C2 单臂事件：armed 且过线触发；分位回到线内侧（±REARM_DROP）连续
    REARM_DAYS 观测后 re-arm（滞回防簇集）。hi=True 上行臂。"""
    armed, calm, out = True, 0, []
    for d, p in pct.items():
        if np.isnan(p):
            continue
        if hi:
            tri, calmed = p >= line, p <= line - REARM_DROP
        else:
            tri, calmed = p <= 100 - line, p >= 100 - line + REARM_DROP
        if armed and tri:
            out.append(d)
            armed, calm = False, 0
        elif not armed:
            calm = calm + 1 if calmed else 0
            if calm >= REARM_DAYS:
                armed = True
    return out


# ---------------------------------------------------------------- 事件研究


def next_exec(signal_days: list[pd.Timestamp], price: pd.DataFrame) -> dict:
    """信号日 → 下一价格交易日（执行日）。"""
    pdays = price.index.values
    out = {}
    for d in signal_days:
        fut = pdays[pdays > np.datetime64(d)]
        if len(fut):
            out[pd.Timestamp(d)] = pd.Timestamp(fut[0])
    return out


def study(price: pd.DataFrame, exec_days: list[pd.Timestamp],
          eligible: pd.DatetimeIndex) -> dict:
    """执行日开盘 → t+H 收盘前瞻收益 + 前瞻波动 + 前瞻回撤；基线=资格日同口径。"""
    opens, closes = price["open"].values, price["close"].values
    idx = price.index
    pos = {d: i for i, d in enumerate(idx)}
    lr = np.log(closes / np.roll(closes, 1))
    lr[0] = np.nan

    def fwd_ret(i: int, h: int) -> float | None:
        j = i + h
        return closes[j] / opens[i] - 1 if j < len(closes) else None

    def fwd_vol(i: int, w: int) -> float | None:
        j = i + w
        return float(np.nanstd(lr[i + 1:j + 1], ddof=1) * np.sqrt(252)) \
            if j < len(closes) else None

    def fwd_dd(i: int, w: int = 252) -> float | None:
        j = min(i + w, len(closes) - 1)
        if j <= i:
            return None
        path = np.concatenate(([opens[i]], closes[i:j + 1]))
        return float((path / np.maximum.accumulate(path)).min() - 1)

    def agg(days) -> dict:
        rows = []
        for d in days:
            i = pos.get(d)
            if i is None:
                continue
            r: dict = {"exec_date": str(d.date())}
            for h, n in HORIZONS.items():
                v = fwd_ret(i, n)
                r[h] = None if v is None else round(v, 4)
            for k, fn in (("vol60", lambda: fwd_vol(i, VOL_W)),
                          ("dd252", lambda: fwd_dd(i))):
                v = fn()
                r[k] = None if v is None else round(v, 4)
            rows.append(r)
        out = {"n_days": len(rows), "signals": rows}
        for h in HORIZONS:
            vals = [r[h] for r in rows if r[h] is not None]
            out[f"mean_{h}"] = round(float(np.mean(vals)), 4) if vals else None
            out[f"win_{h}"] = round(float(np.mean([v > 0 for v in vals])), 3) \
                if vals else None
        for k in ("vol60", "dd252"):
            vals = [r[k] for r in rows if r[k] is not None]
            out[f"mean_{k}"] = round(float(np.mean(vals)), 4) if vals else None
        return out

    res = {"baseline": agg(eligible),
           "events": agg(pd.DatetimeIndex(exec_days).intersection(idx))}
    res["oos_signals"] = [s for s in res["events"]["signals"]
                          if pd.Timestamp(s["exec_date"]) > OOS_CUT]
    return res


# ---------------------------------------------------------------- 安慰剂


def placebo_percentile(price: pd.DataFrame, eligible: pd.DatetimeIndex,
                       n_events: int, stat: str, real_value: float,
                       lower_is_stronger: bool = False) -> dict:
    """CON1：同数量随机执行日 ×PLACEBO_N 组，返回真实统计量的分位。"""
    rng = np.random.default_rng(PLACEBO_SEED)
    opens, closes = price["open"].values, price["close"].values
    pos = {d: i for i, d in enumerate(price.index)}
    lr = np.log(closes / np.roll(closes, 1))
    lr[0] = np.nan

    def stat_of(days) -> float:
        vals = []
        for d in days:
            i = pos.get(d)
            if i is None:
                continue
            if stat == "mean_12m":
                j = i + HORIZONS["12m"]
                v = closes[j] / opens[i] - 1 if j < len(closes) else None
            elif stat == "mean_vol60":
                j = i + VOL_W
                v = np.nanstd(lr[i + 1:j + 1], ddof=1) * np.sqrt(252) \
                    if j < len(closes) else None
            else:
                raise ValueError(stat)
            if v is not None and not np.isnan(v):
                vals.append(v)
        return float(np.mean(vals)) if vals else np.nan

    e = np.array([d for d in eligible if d in pos], dtype="datetime64[ns]")
    draws = []
    for _ in range(PLACEBO_N):
        pick = rng.choice(len(e), size=min(n_events, len(e)), replace=False)
        draws.append(stat_of(pd.DatetimeIndex(e[pick])))
    draws = np.array([d for d in draws if not np.isnan(d)])
    pct = float((draws < real_value).mean() * 100.0)
    if lower_is_stronger:
        pct = 100.0 - pct
    return {"stat": stat, "n_events": int(n_events), "real": round(real_value, 6),
            "placebo_mean": round(float(draws.mean()), 6),
            "placebo_p05": round(float(np.percentile(draws, 5)), 6),
            "placebo_p50": round(float(np.percentile(draws, 50)), 6),
            "placebo_p95": round(float(np.percentile(draws, 95)), 6),
            "real_percentile": round(pct, 2),
            "verdict_line": "pass>=95 / edge>=90 / else fail"}


# ---------------------------------------------------------------- 模拟


def cagr(equity: pd.Series) -> float:
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan


def max_dd(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def sim_bh(price: pd.DataFrame, capital: float = CAPITAL) -> dict:
    amt = capital / (1 + COST)
    units = amt / price["open"].iloc[0]
    s = units * price["close"]
    return {"final": round(float(s.iloc[-1]), 0), "cagr": round(float(cagr(s)), 4),
            "max_dd": round(max_dd(s), 4)}


def sim_dca(price: pd.DataFrame, capital: float = CAPITAL) -> dict:
    """S1 周定投：每周最后交易日收盘投一份；N=min(260, ⌈交易日/2/5⌉)（沿 module-e）。"""
    days = price.index
    weeks = pd.Series(days, index=days).groupby(
        [days.isocalendar().year, days.isocalendar().week]).max()
    invest = list(pd.DatetimeIndex(sorted(set(weeks))))
    n = min(max(1, min(260, math.ceil(len(days) / 2 / 5))), len(invest))
    per = capital / n
    cash, units = capital, 0.0
    eq = {}
    inv = set(invest[:n])
    for d in days:
        if d in inv:
            units += (per - per * COST) / price.at[d, "close"]
            cash -= per
        eq[d] = cash + units * price.at[d, "close"]
    s = pd.Series(eq).sort_index()
    return {"final": round(float(s.iloc[-1]), 0), "cagr": round(float(cagr(s)), 4),
            "max_dd": round(max_dd(s), 4)}


def sim_tranche(price: pd.DataFrame, exec_days: list[pd.Timestamp],
                tranche: float = TRANCHE, capital: float = CAPITAL) -> dict:
    """C1 配置回测：每执行日开盘投剩余现金 ×tranche，只买不卖（沿 module-e E3）。"""
    ex = set(exec_days)
    cash, units, turnover = capital, 0.0, 0.0
    eq = {}
    for d in price.index:
        op, cl = price.at[d, "open"], price.at[d, "close"]
        if d in ex and cash > 1e-9:
            amt = cash * tranche
            units += (amt - amt * COST) / op
            cash -= amt
            turnover += amt
        eq[d] = cash + units * cl
    s = pd.Series(eq).sort_index()
    return {"final": round(float(s.iloc[-1]), 0), "cagr": round(float(cagr(s)), 4),
            "max_dd": round(max_dd(s), 4), "n_signals": len(ex),
            "turnover": round(turnover, 0)}


def sim_avoid(price: pd.DataFrame, event_exec: list[pd.Timestamp],
              avoid_td: int) -> dict:
    """JB3：上行冲击执行日起 avoid_td 交易日避开权益（执行日开盘离场、
    窗口末后开盘回场，出/回各收单边 5bp）。二元进出=触发层，非仓位系数。"""
    days = price.index
    out_mask = pd.Series(False, index=days)
    pos = {d: i for i, d in enumerate(days)}
    for d in event_exec:
        if d in pos:
            i = pos[d]
            out_mask.iloc[i:min(i + avoid_td, len(days))] = True
    cash, units, turnover, eq = CAPITAL, 0.0, 0.0, {}
    holding = False
    for d in days:
        op, cl = price.at[d, "open"], price.at[d, "close"]
        want = not bool(out_mask.at[d])
        if want != holding:
            if want:  # 回场：全现金买入
                amt = cash
                units = (amt - amt * COST) / op
                cash, turnover = 0.0, turnover + amt
            else:     # 离场：全持仓卖出
                amt = units * op
                cash = amt - amt * COST
                units, turnover = 0.0, turnover + amt
            holding = want
        eq[d] = cash + units * cl
    s = pd.Series(eq).sort_index()
    return {"final": round(float(s.iloc[-1]), 0), "cagr": round(float(cagr(s)), 4),
            "max_dd": round(max_dd(s), 4), "exposure": round(float((~out_mask).mean()), 4),
            "turnover": round(turnover, 0)}


# ---------------------------------------------------------------- 主流程


def main() -> None:
    tre = load_treasury()
    spread = tre["us_10_2_spread"]
    gspc = load_price("gspc_ohlc.parquet", MODULE_E_RAW / "us_gspc_ohlc.parquet")
    gspc = gspc[gspc.index >= WIN_START]
    qqq = load_price("qqq_ohlc.parquet", MODULE_E_RAW / "us_qqq_ohlc.parquet")
    csi = load_price("csi300_ohlc.parquet", POOL / "000300.SS.bars.parquet")

    out: dict = {
        "config": dict(
            BRIDGE_MAX=BRIDGE_MAX, CONFIRM_K=CONFIRM_K, C1_MAIN=C1_MAIN,
            C1_SENS=C1_SENS, D20=D20, MIN_HIST=MIN_HIST, PCT_MAIN=PCT_MAIN,
            PCT_SENS=PCT_SENS, REARM_DROP=REARM_DROP, REARM_DAYS=REARM_DAYS,
            VOL_W=VOL_W, VOL_LINE=VOL_LINE, AVOID_MAIN=AVOID_MAIN,
            AVOID_SENS=AVOID_SENS, AGED_TD=AGED_TD, COST=COST, TRANCHE=TRANCHE,
            PLACEBO_N=PLACEBO_N, PLACEBO_SEED=PLACEBO_SEED,
            OOS_CUT=str(OOS_CUT.date()), WIN_START=str(WIN_START.date())),
        "treasury_coverage": {"n_rows": int(len(tre)),
                              "start": str(tre.index[0].date()),
                              "end": str(tre.index[-1].date())},
        "price_coverage": {k: {"start": str(p.index[0].date()), "end": str(p.index[-1].date()),
                               "n": int(len(p))}
                           for k, p in (("gspc", gspc), ("qqq", qqq), ("csi300", csi))},
    }

    # ---- 倒挂段清单（叙述用）----
    eps = invert_episodes(spread)
    out["episodes"] = [{"start": str(e["start"].date()),
                        "last_neg": str(e["last_neg"].date()),
                        "n_neg": int(e["n_neg"])} for e in eps]

    # 资格日集：C1/C3=全窗（余量 ≥370 自然日保证 12m 前瞻可算）
    elig_g = gspc.index[gspc.index <= gspc.index[-1] - pd.Timedelta(days=370)]

    # ---- C1 倒挂解除 ----
    sig_days = c1_events(spread, C1_MAIN)
    emap_g = next_exec(sig_days, gspc)
    emap_q = next_exec(sig_days, qqq)
    emap_c = next_exec(sig_days, csi)
    c1: dict = {
        "events_main": [str(d.date()) for d in sig_days],
        "study_gspc": study(gspc, list(emap_g.values()), elig_g),
        "study_qqq": study(qqq, list(emap_q.values()), qqq.index),
        "study_csi300": study(csi, list(emap_c.values()), csi.index),
        "sim_gspc": sim_tranche(gspc, list(emap_g.values())),
        "baselines_gspc": {"S0_buy_hold": sim_bh(gspc),
                           "S1_weekly_dca": sim_dca(gspc)},
    }
    for ml in C1_SENS:
        sd = c1_events(spread, ml)
        em = next_exec(sd, gspc)
        c1[f"sens_minlen{ml}"] = {
            "n": len(sd), "events": [str(d.date()) for d in sd],
            "study_gspc": study(gspc, list(em.values()), elig_g)}
    out["c1_uninvert_buy"] = c1

    # ---- C2 利率冲击 ----
    d20 = (tre["us_10y"] - tre["us_10y"].shift(D20)).dropna()
    pct = expanding_pct(d20, MIN_HIST)
    pct_valid_from = pct.dropna().index[0]
    # C2 资格日集：扩张分位有效起点之后（同 370 自然日余量）
    elig_c2_g = gspc.index[(gspc.index >= pct_valid_from)
                           & (gspc.index <= gspc.index[-1] - pd.Timedelta(days=370))]
    c2: dict = {"d20_valid_from": str(pct_valid_from.date()),
                "eligible_days_c2": int(len(elig_c2_g))}
    up_exec_main: list[pd.Timestamp] = []
    for line in (PCT_MAIN, *PCT_SENS):
        for hi, arm in ((True, "up"), (False, "down")):
            sd = c2_events(pct, hi, line)
            em = next_exec(sd, gspc)
            blk: dict = {"n": len(sd), "events": [str(d.date()) for d in sd],
                         "study_gspc": study(gspc, list(em.values()), elig_c2_g)}
            if line == PCT_MAIN:
                emq = next_exec(sd, qqq)
                emc = next_exec(sd, csi)
                blk["study_qqq"] = study(qqq, list(emq.values()), qqq.index)
                blk["study_csi300"] = study(csi, list(emc.values()), csi.index)
                if hi:
                    up_exec_main = list(em.values())
            c2[f"line{line}_{arm}"] = blk
    c2["avoid_sims_gspc"] = {f"avoid{w}": sim_avoid(gspc, up_exec_main, w)
                             for w in (AVOID_MAIN, *AVOID_SENS)}
    c2["baseline_bh_gspc"] = sim_bh(gspc)
    out["c2_rate_shock"] = c2

    # ---- C3 老化倒挂 ----
    aged_days, aged_rel = c3_events(spread)
    em_a = next_exec(aged_days, gspc)
    em_r = next_exec(aged_rel, gspc)
    out["c3_aged_inversion"] = {
        "aged_milestone_events": [str(d.date()) for d in aged_days],
        "aged_milestone_study_gspc": study(gspc, list(em_a.values()), elig_g),
        "aged_release_events": [str(d.date()) for d in aged_rel],
        "aged_release_study_gspc": study(gspc, list(em_r.values()), elig_g)}

    # ---- 判定（按 docstring 事前线）----
    v: dict = {}

    def m12_of(st):
        return st["events"]["mean_12m"], st["baseline"]["mean_12m"]

    up = c2[f"line{PCT_MAIN}_up"]
    dn = c2[f"line{PCT_MAIN}_down"]

    n1 = c1["study_gspc"]["events"]["n_days"]
    if n1 < 5:
        ja1 = "report_only_n<5"
    else:
        m12, b12 = m12_of(c1["study_gspc"])
        m6, b6 = (c1["study_gspc"]["events"]["mean_6m"],
                  c1["study_gspc"]["baseline"]["mean_6m"])
        ja1 = "pass" if (m12 > b12 and m6 > b6) else \
            ("falsified" if m12 < b12 else "watch")
    v["JA1_info"] = {"n": n1, "verdict": ja1}
    if n1 >= 5:
        pl = placebo_percentile(gspc, elig_g, n1, "mean_12m",
                                float(c1["study_gspc"]["events"]["mean_12m"]))
        v["JA1_info"]["placebo"] = pl
        if ja1 == "pass" and pl["real_percentile"] < PLACEBO_PASS:
            v["JA1_info"]["verdict"] = ("watch_edge"
                                        if pl["real_percentile"] >= PLACEBO_EDGE
                                        else "fail_generalized_noise")
    nq = c1["study_qqq"]["events"]["n_days"]
    v["JA3_qqq_cross"] = {"n": nq, "verdict": "report_only_n<5" if nq < 5 else
                          ("consistent" if m12_of(c1["study_qqq"])[0]
                           > m12_of(c1["study_qqq"])[1] else "inconsistent")}
    v["JA2_sim"] = {
        "verdict": "report_only(JA1 not pass)" if ja1 != "pass" else
        ("pass" if c1["sim_gspc"]["final"]
         >= c1["baselines_gspc"]["S1_weekly_dca"]["final"] else "falsified")}

    upn = up["study_gspc"]["events"]["n_days"]
    dnn = dn["study_gspc"]["events"]["n_days"]
    mv, bv = up["study_gspc"]["events"]["mean_vol60"], up["study_gspc"]["baseline"]["mean_vol60"]
    mdv, bdv = (dn["study_gspc"]["events"]["mean_vol60"],
                dn["study_gspc"]["baseline"]["mean_vol60"])
    jb1 = "report_only_n<5" if upn < 5 else ("pass" if mv >= bv * VOL_LINE else "falsified")
    dn_pass = bool(dnn >= 5 and mdv is not None and bdv is not None
                   and mdv >= bdv * VOL_LINE)
    if jb1 == "pass" and dn_pass:
        jb1 = "watch_direction_insensitive"
    v["JB1_vol_warning"] = {"n_up": upn, "mean_vol60_events": mv,
                            "mean_vol60_baseline": bv, "down_arm_n": dnn,
                            "down_mean_vol60": mdv, "down_also_pass": dn_pass,
                            "verdict": jb1}
    if upn >= 5 and mv is not None:
        pl = placebo_percentile(gspc, elig_c2_g, upn, "mean_vol60", float(mv))
        v["JB1_vol_warning"]["placebo"] = pl
        if jb1 == "pass" and pl["real_percentile"] < PLACEBO_PASS:
            v["JB1_vol_warning"]["verdict"] = ("watch_edge"
                                               if pl["real_percentile"] >= PLACEBO_EDGE
                                               else "fail_generalized_noise")
    m6u, b6u = up["study_gspc"]["events"]["mean_6m"], up["study_gspc"]["baseline"]["mean_6m"]
    v["JB2_return_side"] = {"n": upn, "verdict": "report_only_n<5" if upn < 5 else
                            ("info_true" if m6u < b6u else "falsified")}
    na = len(out["c3_aged_inversion"]["aged_milestone_events"])
    v["JC1_aged"] = {"n": na,
                     "verdict": "report_only_n<5" if na < 5 else "judge_per_JA1"}

    # ---- CON2 跨资产效应量对比 ----
    def effect(st, k):
        e_, b_ = st["events"].get(f"mean_{k}"), st["baseline"].get(f"mean_{k}")
        return None if (e_ is None or b_ is None) else e_ - b_

    eg, ec = effect(c1["study_gspc"], "12m"), effect(c1["study_csi300"], "12m")
    vg, vc = effect(up["study_gspc"], "vol60"), effect(up["study_csi300"], "vol60")
    v["CON2_cross_asset"] = {
        "c1_12m_effect_gspc": eg, "c1_12m_effect_csi300": ec,
        "c1_generalization_suspect": bool(
            ec is not None and eg is not None and np.sign(ec) == np.sign(eg)
            and abs(ec) >= 0.5 * abs(eg)),
        "c2_vol_effect_gspc": vg, "c2_vol_effect_csi300": vc,
        "c2_generalization_suspect": bool(
            vc is not None and vg is not None and np.sign(vc) == np.sign(vg)
            and abs(vc) >= 0.5 * abs(vg))}
    out["verdicts"] = v

    # ---- 落盘 ----
    res_json = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True,
                          default=str)
    (RAW / "us_treasury_results.json").write_text(res_json)
    for tag, blk, key in (("c1", c1, "study_gspc"),
                          ("c2_up", up, "study_gspc"),
                          ("c2_down", dn, "study_gspc"),
                          ("c3_milestone", out["c3_aged_inversion"],
                           "aged_milestone_study_gspc"),
                          ("c3_release", out["c3_aged_inversion"],
                           "aged_release_study_gspc")):
        rows = blk[key]["events"]["signals"]
        if rows:
            pd.DataFrame(rows).to_csv(RAW / f"{tag}_events.csv", index=False)
    digest = hashlib.sha256(res_json.encode()).hexdigest()
    seed = os.environ.get("PYTHONHASHSEED", "unset")
    (RAW / f"hash_{seed}.json").write_text(json.dumps(
        {"pythonhashseed": seed, "sha256_results": digest}, indent=2))
    print(json.dumps({"treasury": out["treasury_coverage"],
                      "episodes": out["episodes"],
                      "c1_events": c1["events_main"],
                      "c2_up_events": up["events"], "c2_down_events": dn["events"],
                      "c3_aged": out["c3_aged_inversion"]["aged_milestone_events"],
                      "verdicts": v, "sha256": digest},
                     indent=2, ensure_ascii=False, default=str))
    return None


if __name__ == "__main__":
    sys.exit(main())
