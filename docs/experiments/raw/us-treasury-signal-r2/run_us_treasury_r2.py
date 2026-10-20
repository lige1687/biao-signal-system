"""美债利率做美股信号 · 第二轮：水平压制诊断 + 股债双杀组合 + 分批建仓（2026-09-03）。

用户问题：5Y/10Y/30Y 高收益按理压制股市，为何第一轮测不出效果？要不要换
组合语义（如股债双杀状态）或换执行方式（分批建仓）再测？

与第一轮/前人工作的边界（先读）：
- 第一轮（raw/us-treasury-signal/，us-treasury-ARCHIVE-2026-09-01.md）测的是
  曲线形态触发（倒挂解除/20日变动冲击），全部未过；其样本=东财 1990-12 起。
- 本轮新增维度一：**利率水平**（5Y/10Y/30Y 绝对高位的扩张分位）从未在美股
  直接测过（红线案例 lei-ARCHIVE 测的是中债水平→仓位打折，机制不同；本轮
  水平只用于定义事件，不碰任何仓位系数）。
- 本轮新增维度二：**时代外推**——FRED DGS10 官方史自 1962 年起，覆盖
  1966-1982 高利率时代（水平压制机制理论上唯一该生效的年代）；此前全部
  判负（触发层/确认层/仓位层 × 中美共 5 次）都只用了 1990 后样本。
- 本轮新增维度三：**分批建仓**（语义九执行层，A 股侧由 Prompt AE 另测；
  本轮只在美股利率事件上做执行层对照，不设计正式规则）。
- 数据源换 FRED（与前人 ERP 任务同源）；东财↔FRED 1990 后差异做核对。

判定标准（事前写死，跑之前落 docstring，跑完不许改）：
- RA（水平压制·诊断，DGS10 主判）：
  - 水平分位=扩张窗口（仅过去，暖机 1260 交易日）；高水位事件=分位 ≥85
    连续段首日（滞回：回落 <80 连续 60 交易日可再触发）；低水位 ≤15 镜像。
  - RA1 全样本线：n≥5 且 高水位事件后 12 个月平均前瞻收益 < 基线均值 −2pp
    且 该均值在安慰剂（同资格日抽同数日 ×2000）下侧 ≥90 分位（即比 90%
    的随机抽样更差）→「水平有压制信息」；否则「全样本无压制信息」。
  - RA2 时代分层线（1985-01-01 切分，机制理由=沃尔克反通胀确立后股债关系
    结构性转变，非数据偷看）：pre-1985 满足 RA1 型线（n≥5；n∈[3,5) 只报告
    方向）且 post-1985 不满足 →「压制曾存在、已消亡」（叙事登记）；
    pre-1985 也不满足 →「64 年样本内水平直觉从未成立」。
  - RA3：DGS5/DGS30 同线只报告（DGS30 含 2002-06~2006-01 官方缺口，剔除）。
- RB（股债双杀·组合语义触发）：
  - 状态=①GSPC 20 交易日收益 < −5% 且 ②DGS10 的 d20（20 日变动）扩张分位
    ≥80 且 d20>0（股跌 × 利率快升）。事件=进入状态首日；离场连续 60 交易
    日后可再触发。
  - RB1 风险信息线：n≥5 且 (a) 事件后 6 个月平均前瞻 < 基线 −2pp 且
    (b) 事件后 252 交易日路径最大回撤均值 ≤ 基线 −3pp（更深）且
    (c) 6 个月均值安慰剂下侧 ≥90 分位 →「双杀有风险信息」；
    (a)+(c) 而 (b) 不满足 →「观察级」；其余 →「无信息/证伪」。
  - RB2 二元防守模拟（report-only）：双杀状态在场即空仓（次日开盘执行，
    单边 5bp），vs 买入持有；敏感性小邻域=权益腿 −8%/−3% × 利率腿 75/85。
- RC（分批建仓·下行臂执行层）：
  - 事件集=DGS10 d20 扩张分位 ≤5（第一轮同参数，滞回 re-arm），暖机后
    全史，且有 ≥252 交易日前瞻数据的子集。
  - 每事件三执行（独立小账本，买入各收单边 5bp，期末收盘平仓不计费）：
    全仓一次（执行日开盘）/ 3 批（0/+20/+60 交易日各 1/3）/ 5 批
    （0/+20/+40/+60/+80 各 1/5），持有至 +252 交易日收盘。
  - RC1 判定线：3 批相对全仓，平均每事件收益改善 >0 **且** 最差事件改善 >0
    →「分批有实质改善（均值与尾部同向）」；仅一维 →「无实质增量」；
    两维皆负 →「分批吃亏（V 型反弹罚金）」。n≥5 才判；5 批只作敏感性。
  - RC2 分组（只报告不判定）：伴生模块 E v1 买入信号（±10 交易日，
    orthogonality-check 口径）vs 独立事件，分组均值。
  - RC3 上行臂对照（事前预期登记：上行臂前瞻偏弱、若分批在弱臂都无改善，
    则分批对利率事件入场无普适价值）：同线判定。
- 纪律：安慰剂 rng=default_rng(20260903) ×2000；双跑哈希（PYTHONHASHSEED=
  0/42）；全程触发/执行层，无任何仓位系数；判定用语不构成买卖指令。

口径：
- 信号日收盘确认 → 下一 GSPC 交易日开盘执行（沿第一轮/module-e）。
- 前瞻收益 fwd_ret_H(i)=close[i+H]/open[i]−1；fwd_dd(i)=自执行日开盘起
  252 交易日路径最大回撤；基线=同公式逐日（水平分位有效的资格日集，
  ≥370 自然日前瞻余量）。
- 窗口 1962-01-02→价格末；价格 ^GSPC auto_adjust（不含股息，信号与基线
  同源自洽）；利率 FRED DGS10/DGS5/DGS30 日频收盘（截至 2026-09-01）。
- OOS 标注=执行日 > 2024-08-27（沿第一轮）。

数据（落 raw 缓存，首跑联网，之后离线）：
- FRED fredgraph.csv：DGS10（1962-01 起）、DGS5（1962-01 起）、DGS30
  （1977-02 起，2002-06~2006-01 官方缺口剔除）。
- ^GSPC OHLC 1961-12 起（yfinance auto_adjust）。
- 模块 E v1 信号 33 枚：docs/experiments/raw/module_e/module_e_results.json
  （只读复用）。
- 东财↔FRED 核对：1990-12 后 DGS10 vs 东财 us_10y 逐日差（报最大/均值）。

输出：本目录（docs/experiments/raw/us-treasury-signal-r2/）
复现：PYTHONHASHSEED=0 python3 run_us_treasury_r2.py（首跑联网，之后离线）
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
R1_RAW = REPO / "docs/experiments/raw/us-treasury-signal"
MODULE_E_RAW = REPO / "docs/experiments/raw/module_e"

WIN_START = pd.Timestamp("1962-01-02")
WARMUP = 1260          # 扩张分位暖机（≈5 年）
OOS_CUT = pd.Timestamp("2024-08-27")
COST = 0.0005          # 单边 5bp（沿 module-e / 第一轮）
HORIZONS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}
# RA 水平
RA_HI, RA_LO = 85.0, 15.0
RA_REARM_DROP = 5.0    # 滞回：分位回落到 80 以下 / 20 以上
RA_REARM_DAYS = 60
RA_LINE_PP = 0.02      # 12m 低于基线 2pp
ERA_CUT = pd.Timestamp("1985-01-01")   # 沃尔克反通胀后（机制切分）
# RB 双杀
RB_EQ_TH = -0.05       # 权益 20 日收益阈值
RB_PCT_TH = 80.0       # d20 分位阈值
RB_REARM_DAYS = 60
RB_LINE_PP = 0.02      # 6m 低于基线 2pp
RB_DD_PP = 0.03        # dd252 深于基线 3pp
RB_SENS = ((-0.08, 80.0), (-0.03, 80.0), (-0.05, 75.0), (-0.05, 85.0))
# RC 分批
D20 = 20
RC_LINE, RC_REARM_DROP, RC_REARM_DAYS = 5.0, 5.0, 60   # 下行臂（第一轮同参）
RC_HOLD = 252
TRANCHE3 = (0, 20, 60)
TRANCHE5 = (0, 20, 40, 60, 80)
RC_LINE_UP = 95.0      # 上行臂对照
# 安慰剂
PLACEBO_N = 2000
PLACEBO_SEED = 20260903
PLACEBO_LOW_PASS = 90.0   # 下侧 ≥90 分位


# ---------------------------------------------------------------- 数据


def fetch_fred(series: str) -> pd.Series:
    """FRED fredgraph.csv → 日频 Series（数值，缺测 NaN）。"""
    import requests
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    # 本机代理为白名单模式：绕过系统代理直连（沿 sources.py trust_env=False 先例）
    sess = requests.Session()
    sess.trust_env = False
    txt = sess.get(url, timeout=30,
                   headers={"User-Agent": "Mozilla/5.0"}).text
    f = RAW / f"fred_{series.lower()}.csv"
    f.write_text(txt)
    df = pd.read_csv(f)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    s = pd.to_numeric(df["value"], errors="coerce")
    s.index = df["date"]
    return s.sort_index().dropna()


def load_fred(series: str) -> pd.Series:
    f = RAW / f"fred_{series.lower()}.csv"
    if not f.exists():
        return fetch_fred(series)
    df = pd.read_csv(f)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    s = pd.to_numeric(df["value"], errors="coerce")
    s.index = df["date"]
    return s.sort_index().dropna()


def load_gspc() -> pd.DataFrame:
    f = RAW / "gspc_ohlc_1962.parquet"
    if not f.exists():
        import yfinance as yf
        raw = yf.download("^GSPC", start="1961-12-01", auto_adjust=True,
                          progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = [c[0].lower() for c in raw.columns]
        else:
            raw.columns = [str(c).lower() for c in raw.columns]
        df = raw[["open", "close"]].dropna()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df.to_parquet(f)
    df = pd.read_parquet(f)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["open", "close"]].astype(float)


# ---------------------------------------------------------------- 信号机械


def expanding_pct(x: pd.Series, min_hist: int) -> pd.Series:
    """t 日分位 = x[t] 在 x[0..t-1]（仅过去）的秩 ×100。"""
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


def hysteresis_events(cond: pd.Series, rearm_cond: pd.Series,
                      rearm_days: int) -> list[pd.Timestamp]:
    """armed 且 cond 触发；触发后 disarm，rearm_cond 连续 rearm_days 后复位。"""
    armed, calm, out = True, 0, []
    for d, c in cond.items():
        if pd.isna(c):
            continue
        if armed and bool(c):
            out.append(d)
            armed, calm = False, 0
        elif not armed:
            r = rearm_cond.get(d, np.nan)
            calm = calm + 1 if (not pd.isna(r) and bool(r)) else 0
            if calm >= rearm_days:
                armed = True
    return out


def next_exec(signal_days: list[pd.Timestamp], price: pd.DataFrame) -> list[pd.Timestamp]:
    pdays = price.index.values
    out = []
    for d in signal_days:
        fut = pdays[pdays > np.datetime64(d)]
        if len(fut):
            out.append(pd.Timestamp(fut[0]))
    return out


# ---------------------------------------------------------------- 度量


def study(price: pd.DataFrame, exec_days: list[pd.Timestamp],
          eligible: pd.DatetimeIndex) -> dict:
    opens, closes = price["open"].values, price["close"].values
    idx = price.index
    pos = {d: i for i, d in enumerate(idx)}

    def fwd_ret(i, h):
        j = i + h
        return closes[j] / opens[i] - 1 if j < len(closes) else None

    def fwd_dd(i, w=252):
        j = min(i + w, len(closes) - 1)
        if j <= i:
            return None
        path = np.concatenate(([opens[i]], closes[i:j + 1]))
        return float((path / np.maximum.accumulate(path)).min() - 1)

    def agg(days):
        rows = []
        for d in days:
            i = pos.get(d)
            if i is None:
                continue
            r: dict = {"exec_date": str(d.date())}
            for h, n in HORIZONS.items():
                v = fwd_ret(i, n)
                r[h] = None if v is None else round(v, 4)
            v = fwd_dd(i)
            r["dd252"] = None if v is None else round(v, 4)
            rows.append(r)
        out = {"n_days": len(rows), "signals": rows}
        for h in HORIZONS:
            vals = [r[h] for r in rows if r[h] is not None]
            out[f"mean_{h}"] = round(float(np.mean(vals)), 4) if vals else None
            out[f"win_{h}"] = round(float(np.mean([v > 0 for v in vals])), 3) \
                if vals else None
        vals = [r["dd252"] for r in rows if r["dd252"] is not None]
        out["mean_dd252"] = round(float(np.mean(vals)), 4) if vals else None
        return out

    ev = agg(exec_days)
    return {"baseline": agg(eligible), "events": ev,
            "oos_signals": [s for s in ev["signals"]
                            if pd.Timestamp(s["exec_date"]) > OOS_CUT]}


def placebo_low_pct(price: pd.DataFrame, eligible: pd.DatetimeIndex,
                    n_events: int, stat_h: str, real_value: float) -> dict:
    """安慰剂：同资格日抽同数执行日 ×2000，返回真实值在分布中的位置。
    low_pct = 比真实值更差的抽样比例×100（下侧强度），≥90 为过线。"""
    rng = np.random.default_rng(PLACEBO_SEED)
    opens, closes = price["open"].values, price["close"].values
    pos = {d: i for i, d in enumerate(price.index)}
    h = HORIZONS[stat_h]
    e = np.array([d for d in eligible if d in pos], dtype="datetime64[ns]")

    def stat_of(days):
        vals = []
        for d in days:
            i = pos.get(d)
            if i is not None and i + h < len(closes):
                vals.append(closes[i + h] / opens[i] - 1)
        return float(np.mean(vals)) if vals else np.nan

    draws = []
    for _ in range(PLACEBO_N):
        pick = rng.choice(len(e), size=min(n_events, len(e)), replace=False)
        draws.append(stat_of(pd.DatetimeIndex(e[pick])))
    draws = np.array([d for d in draws if not np.isnan(d)])
    below = float((draws < real_value).mean() * 100.0)
    return {"stat": f"mean_{stat_h}", "real": round(real_value, 6),
            "placebo_p05": round(float(np.percentile(draws, 5)), 6),
            "placebo_p50": round(float(np.percentile(draws, 50)), 6),
            "placebo_p95": round(float(np.percentile(draws, 95)), 6),
            "low_pct": round(100.0 - below, 2),
            "line": "low_pct>=90 pass"}


# ---------------------------------------------------------------- 模拟


def cagr(s: pd.Series) -> float:
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan


def max_dd(s: pd.Series) -> float:
    return float((s / s.cummax() - 1).min())


def sim_bh(price: pd.DataFrame) -> dict:
    amt = CAPITAL / (1 + COST)
    units = amt / price["open"].iloc[0]
    s = units * price["close"]
    return {"final": round(float(s.iloc[-1]), 0), "cagr": round(float(cagr(s)), 4),
            "max_dd": round(max_dd(s), 4)}


CAPITAL = 1_000_000.0


def sim_state_exit(price: pd.DataFrame, state: pd.Series) -> dict:
    """RB2：状态（收盘确认）在场则次日开盘空仓，二元、单边 5bp。"""
    days = price.index
    want = ~state.shift(1, fill_value=False).reindex(days, fill_value=True)
    cash, units, holding, eq = CAPITAL, 0.0, False, {}
    for d in days:
        op, cl = price.at[d, "open"], price.at[d, "close"]
        w = bool(want.at[d])
        if w != holding:
            if w:
                amt = cash
                units = (amt - amt * COST) / op
                cash = 0.0
            else:
                amt = units * op
                cash = amt - amt * COST
                units = 0.0
            holding = w
        eq[d] = cash + units * cl
    s = pd.Series(eq).sort_index()
    return {"final": round(float(s.iloc[-1]), 0), "cagr": round(float(cagr(s)), 4),
            "max_dd": round(max_dd(s), 4), "exposure": round(float(want.mean()), 4)}


def tranche_returns(price: pd.DataFrame, exec_days: list[pd.Timestamp],
                    tranches: tuple[int, ...], hold: int = RC_HOLD) -> list[float]:
    """每事件独立小账本：offsets 批等权买入（各 5bp），持有 hold 交易日收盘估值。
    返回每事件净收益率列表（无期末卖出费，与全仓同口径）。"""
    pos = {d: i for i, d in enumerate(price.index)}
    opens, closes = price["open"].values, price["close"].values
    out = []
    for d in exec_days:
        i = pos.get(d)
        if i is None or i + hold >= len(closes):
            continue
        p_exit = closes[i + hold]
        mult = 0.0
        for off in tranches:
            j = i + off
            mult += (p_exit / opens[j])
        out.append(float((1 - COST) * mult / len(tranches) - 1))
    return out


# ---------------------------------------------------------------- 主流程


def main() -> None:
    dgs10 = load_fred("DGS10")
    dgs5 = load_fred("DGS5")
    dgs30 = load_fred("DGS30")
    px = load_gspc()
    px = px[px.index >= WIN_START]

    # 东财↔FRED 核对（只读第一轮缓存）
    em = pd.read_parquet(R1_RAW / "treasury_history.parquet")
    em.index = pd.to_datetime(em.index)
    j = pd.concat([em["us_10y"].rename("em"), dgs10.rename("fred")], axis=1).dropna()
    diff = (j["em"] - j["fred"]).abs()

    out: dict = {
        "config": dict(WIN_START=str(WIN_START.date()), WARMUP=WARMUP,
                       RA_HI=RA_HI, RA_LO=RA_LO, RA_LINE_PP=RA_LINE_PP,
                       ERA_CUT=str(ERA_CUT.date()), RB_EQ_TH=RB_EQ_TH,
                       RB_PCT_TH=RB_PCT_TH, RB_LINE_PP=RB_LINE_PP,
                       RB_DD_PP=RB_DD_PP, RC_HOLD=RC_HOLD,
                       TRANCHE3=TRANCHE3, TRANCHE5=TRANCHE5,
                       PLACEBO_N=PLACEBO_N, PLACEBO_SEED=PLACEBO_SEED,
                       COST=COST, OOS_CUT=str(OOS_CUT.date())),
        "coverage": {
            "dgs10": [str(dgs10.index[0].date()), str(dgs10.index[-1].date()), int(len(dgs10))],
            "dgs5": [str(dgs5.index[0].date()), str(dgs5.index[-1].date()), int(len(dgs5))],
            "dgs30": [str(dgs30.index[0].date()), str(dgs30.index[-1].date()), int(len(dgs30))],
            "gspc": [str(px.index[0].date()), str(px.index[-1].date()), int(len(px))],
        },
        "fred_vs_eastmoney_dgs10": {
            "n_overlap": int(len(j)), "mean_abs_diff_bp": round(float(diff.mean() * 100), 2),
            "max_abs_diff_bp": round(float(diff.max() * 100), 2)},
    }

    # ---- RA 水平分位（DGS10 主判）----
    pct10 = expanding_pct(dgs10, WARMUP)
    pvf = pct10.dropna().index[0]
    hi_ev = hysteresis_events(pct10 >= RA_HI, pct10 <= RA_HI - RA_REARM_DROP,
                              RA_REARM_DAYS)
    lo_ev = hysteresis_events(pct10 <= RA_LO, pct10 >= RA_LO + RA_REARM_DROP,
                              RA_REARM_DAYS)
    elig = px.index[(px.index >= pvf)
                    & (px.index <= px.index[-1] - pd.Timedelta(days=370))]
    hi_exec = next_exec(hi_ev, px)
    lo_exec = next_exec(lo_ev, px)
    ra: dict = {
        "pct_valid_from": str(pvf.date()),
        "hi_events": [str(d.date()) for d in hi_ev],
        "lo_events": [str(d.date()) for d in lo_ev],
        "study_hi": study(px, hi_exec, elig),
        "study_lo": study(px, lo_exec, elig),
    }
    # RA1 全样本判定
    n_hi = ra["study_hi"]["events"]["n_days"]
    m12, b12 = ra["study_hi"]["events"]["mean_12m"], ra["study_hi"]["baseline"]["mean_12m"]
    ra1 = None
    if n_hi >= 5 and m12 is not None:
        pl = placebo_low_pct(px, elig, n_hi, "12m", float(m12))
        ra["placebo_hi_12m"] = pl
        ra1 = "suppression_info" if (m12 < b12 - RA_LINE_PP
                                     and pl["low_pct"] >= PLACEBO_LOW_PASS) \
            else "no_suppression_full_sample"
    ra["RA1"] = {"n": n_hi, "verdict": ra1}
    # RA2 时代分层
    pre_exec = [d for d in hi_exec if d < ERA_CUT]
    post_exec = [d for d in hi_exec if d >= ERA_CUT]
    st_pre = study(px, pre_exec, elig)
    st_post = study(px, post_exec, elig)
    ra["era_split"] = {"pre1985_n": len(pre_exec), "post1985_n": len(post_exec),
                       "pre1985_mean_12m": st_pre["events"]["mean_12m"],
                       "post1985_mean_12m": st_post["events"]["mean_12m"],
                       "baseline_12m": b12}
    ra2 = None
    npre = st_pre["events"]["n_days"]
    if npre >= 3:
        pre_pass = st_pre["events"]["mean_12m"] is not None and \
            st_pre["events"]["mean_12m"] < b12 - RA_LINE_PP
        if npre >= 5:
            pl = placebo_low_pct(px, elig, npre, "12m",
                                 float(st_pre["events"]["mean_12m"]))
            ra["placebo_pre1985_12m"] = pl
            pre_pass = pre_pass and pl["low_pct"] >= PLACEBO_LOW_PASS
        post_pass = st_post["events"]["mean_12m"] is not None and \
            st_post["events"]["mean_12m"] < b12 - RA_LINE_PP
        if 3 <= npre < 5:  # 事前条款：n∈[3,5) 只报告方向，不下最终标签
            ra2 = "direction_only_pre3to5"
        else:
            ra2 = ("existed_then_died" if (pre_pass and not post_pass)
                   else ("never_existed_64y" if not pre_pass else "still_alive"))
    ra["RA2"] = {"verdict": ra2}
    # RA3 5Y/30Y 只报告
    for nm, s in (("dgs5", dgs5), ("dgs30", dgs30)):
        p = expanding_pct(s, WARMUP)
        if p.dropna().empty:
            continue
        ev = hysteresis_events(p >= RA_HI, p <= RA_HI - RA_REARM_DROP, RA_REARM_DAYS)
        ex = next_exec(ev, px)
        el = px.index[(px.index >= p.dropna().index[0])
                      & (px.index <= px.index[-1] - pd.Timedelta(days=370))]
        ra[f"{nm}_hi_report_only"] = {
            "n": len(ev), "events": [str(d.date()) for d in ev],
            "study": study(px, ex, el)}
    out["ra_level"] = ra

    # ---- RB 股债双杀 ----
    d20 = (dgs10 - dgs10.shift(D20)).dropna()
    pctd = expanding_pct(d20, WARMUP)
    ret20 = px["close"] / px["close"].shift(20) - 1
    rb: dict = {}
    for tag, eq_th, pct_th in (("main", RB_EQ_TH, RB_PCT_TH),
                               *((f"s{a}_{int(b)}", a, b) for a, b in RB_SENS)):
        eq_leg = ret20 < eq_th
        rt_leg = (pctd >= pct_th) & (d20 > 0)
        state = (eq_leg & rt_leg).reindex(px.index, fill_value=False)
        out_of_state = ~state
        ev = hysteresis_events(state, out_of_state, RB_REARM_DAYS)
        ex = next_exec(ev, px)
        st = study(px, ex, elig)
        blk: dict = {"n": len(ev), "events": [str(d.date()) for d in ev],
                     "study": st}
        if tag == "main":
            n = st["events"]["n_days"]
            m6, b6 = st["events"]["mean_6m"], st["baseline"]["mean_6m"]
            mdd, bdd = st["events"]["mean_dd252"], st["baseline"]["mean_dd252"]
            rb1 = None
            if n >= 5 and m6 is not None:
                pl = placebo_low_pct(px, elig, n, "6m", float(m6))
                blk["placebo_6m"] = pl
                a_ok = m6 < b6 - RB_LINE_PP
                b_ok = (mdd is not None and bdd is not None
                        and mdd <= bdd - RB_DD_PP)
                c_ok = pl["low_pct"] >= PLACEBO_LOW_PASS
                rb1 = ("risk_info" if (a_ok and b_ok and c_ok)
                       else ("watch_partial" if (a_ok and c_ok) else "no_info"))
            blk["RB1"] = {"n": n, "verdict": rb1}
            blk["sim_state_exit"] = sim_state_exit(px, state)
            blk["baseline_bh"] = sim_bh(px)
        rb[tag] = blk
    out["rb_double_kill"] = rb

    # ---- RC 分批建仓（下行臂主测 + 上行臂对照）----
    mod_e_v1 = set(pd.to_datetime(json.loads(
        (MODULE_E_RAW / "module_e_results.json").read_text())
        ["us"]["arms"]["v1_hedge50"]["signals"]).normalize())
    rc: dict = {}
    for arm, line in (("down", RC_LINE), ("up", RC_LINE_UP)):
        if arm == "down":
            cond = pctd <= line
            rearm = pctd >= line + RC_REARM_DROP
        else:
            cond = pctd >= line
            rearm = pctd <= line - RC_REARM_DROP
        ev = hysteresis_events(cond, rearm, RC_REARM_DAYS)
        ex = next_exec(ev, px)
        r_all = tranche_returns(px, ex, (0,))
        r_t3 = tranche_returns(px, ex, TRANCHE3)
        r_t5 = tranche_returns(px, ex, TRANCHE5)
        # 与模块 E 伴生分组（信号日 ±10 交易日）
        near_e = []
        for d in ex:
            w0 = d - pd.Timedelta(days=14)
            w1 = d + pd.Timedelta(days=14)
            near_e.append(any(w0 <= s <= w1 for s in mod_e_v1))
        blk: dict = {
            "n_events_evaluable": len(r_all),
            "all_events": [str(d.date()) for d in ex],
            "module_e_coincident_flags": near_e,
            "allin": {"mean": round(float(np.mean(r_all)), 4) if r_all else None,
                      "median": round(float(np.median(r_all)), 4) if r_all else None,
                      "worst": round(float(np.min(r_all)), 4) if r_all else None},
            "tranche3": {"mean": round(float(np.mean(r_t3)), 4) if r_t3 else None,
                         "median": round(float(np.median(r_t3)), 4) if r_t3 else None,
                         "worst": round(float(np.min(r_t3)), 4) if r_t3 else None},
            "tranche5_sens": {"mean": round(float(np.mean(r_t5)), 4) if r_t5 else None,
                              "median": round(float(np.median(r_t5)), 4) if r_t5 else None,
                              "worst": round(float(np.min(r_t5)), 4) if r_t5 else None},
        }
        if len(r_all) >= 5:
            mean_up = np.mean(r_t3) > np.mean(r_all)
            worst_up = np.min(r_t3) > np.min(r_all)
            blk["RC_verdict"] = ("substantial_improvement" if (mean_up and worst_up)
                                 else ("no_increment" if (mean_up or worst_up)
                                       else "vshape_penalty"))
        else:
            blk["RC_verdict"] = "report_only_n<5"
        # 分组均值（只报告）
        for name, flags in (("with_mod_e", near_e), ("independent",
                                                     [not f for f in near_e])):
            idxs = [i for i, f in enumerate(flags) if f]
            if idxs:
                blk[name] = {
                    "n": len(idxs),
                    "allin_mean": round(float(np.mean([r_all[i] for i in idxs])), 4),
                    "tranche3_mean": round(float(np.mean([r_t3[i] for i in idxs])), 4)}
        rc[arm] = blk
    out["rc_tranche"] = rc

    # ---- 落盘 ----
    res_json = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True,
                          default=str)
    (RAW / "us_treasury_r2_results.json").write_text(res_json)
    pd.DataFrame(ra["study_hi"]["events"]["signals"]).to_csv(
        RAW / "ra_hi_events.csv", index=False)
    pd.DataFrame(rb["main"]["study"]["events"]["signals"]).to_csv(
        RAW / "rb_events.csv", index=False)
    digest = hashlib.sha256(res_json.encode()).hexdigest()
    seed = os.environ.get("PYTHONHASHSEED", "unset")
    (RAW / f"hash_{seed}.json").write_text(json.dumps(
        {"pythonhashseed": seed, "sha256_results": digest}, indent=2))
    print(json.dumps({
        "coverage": out["coverage"],
        "fred_vs_em": out["fred_vs_eastmoney_dgs10"],
        "RA_hi_events": ra["hi_events"], "RA_lo_events": ra["lo_events"],
        "RA1": ra["RA1"], "RA2": ra["RA2"],
        "era": ra["era_split"],
        "RB_main_n": rb["main"]["n"], "RB1": rb["main"]["RB1"],
        "RB_sim": rb["main"]["sim_state_exit"],
        "RC_down": {k: rc["down"][k] for k in
                    ("n_events_evaluable", "allin", "tranche3", "RC_verdict",
                     "with_mod_e", "independent")},
        "RC_up": {k: rc["up"][k] for k in
                  ("n_events_evaluable", "allin", "tranche3", "RC_verdict")},
        "sha256": digest}, indent=2, ensure_ascii=False, default=str))
    return None


if __name__ == "__main__":
    sys.exit(main())
