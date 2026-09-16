"""因子策略化大量回测（2026-08-27）。

设计纪律：
- 防前视：一切信号在 t 收盘计算，t+1 收盘执行；成本按换手双边计。
- 全参数网格全部报告（不做选择性汇报）；含分年表与前后半段切分。
- 现金收益按 1.5%/年（货币基金近似）计提；Sharpe 用同一 rf。
- 板块指数为本机等权合成（当前成分回溯，含成员前视偏差）——只作研究代理，不可直接交易。
- 结果输出 /tmp/factor_backtest_results.txt；报告见 docs/research-factor-backtest.md（2026-08-27 首跑）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import glob
import json

CACHE = "/Users/yongbiaoli/.lei_signal_lab/cache"
RF_ANNUAL = 0.015
RF_DAILY = (1 + RF_ANNUAL) ** (1 / 252) - 1
COST_ETF = 0.001     # 单边 0.1%（ETF 佣金+价差的保守值）
COST_SECTOR = 0.002  # 板块合成指数不可交易，用更高单边做敏感性
OUT = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    OUT.append(s)

# ════════════════════════════════════════════════════════════════════
# 数据加载
# ════════════════════════════════════════════════════════════════════
def load_closes(codes: list[str]) -> pd.DataFrame:
    data = {}
    for c in codes:
        df = pd.read_parquet(f"{CACHE}/{c}.bars.parquet")
        data[c] = df["close"]
    px = pd.DataFrame(data).sort_index()
    return px

SEC_CODES = sorted(
    f.split("/")[-1].split(".SECTOR.bars")[0] + ".SECTOR"
    for f in glob.glob(f"{CACHE}/*.SECTOR.bars.parquet")
)
NAMES = {}
try:
    import sys
    sys.path.insert(0, "/Users/yongbiaoli/lei-signal-sync/src")
    from lei_signal.api.labels import THS_INDUSTRY_NAMES
    NAMES = {f"TH{k}.SECTOR": v for k, v in THS_INDUSTRY_NAMES.items()}
except Exception:
    pass

secpx = load_closes(SEC_CODES).ffill()

# ETF 池（B/C 用；全部 A 股 ETF/指数，按各自历史动态入池）
ETF_POOL = ["510300.SS", "512400.SS", "515050.SS", "515130.SS", "515300.SS",
            "518850.SS", "588000.SS", "515170.SS", "516220.SS", "000688.SS",
            "000300.SS", "000001.SS", "159652.SZ", "512890.SS", "515880.SS",
            "513870.SS", "562590.SS"]
etfpx = load_closes(ETF_POOL).ffill()

# ════════════════════════════════════════════════════════════════════
# 回测引擎（日频权重 → 组合净值；信号 t 收盘，t+1 收盘执行）
# ════════════════════════════════════════════════════════════════════
def run_from_weights(px: pd.DataFrame, w: pd.DataFrame, cost: float) -> pd.Series:
    """w(d) = 当日持仓权重（基于 d-1 收盘信号）；组合日收益 = Σ w·r + 现金·rf - 换手成本。"""
    rets = px.pct_change()
    common = w.index
    wr = w.reindex(common).fillna(0.0)
    rr = rets.reindex(common).fillna(0.0)
    gross = (wr * rr).sum(axis=1)
    idle = (1.0 - wr.sum(axis=1)).clip(lower=0.0)
    net_daily = gross + idle * RF_DAILY
    turnover = wr.diff().abs().sum(axis=1).fillna(wr.iloc[0].abs().sum())
    net_daily = net_daily - turnover * cost
    return (1 + net_daily).cumprod()

def metrics(eq: pd.Series, rf_annual: float = RF_ANNUAL) -> dict:
    r = eq.pct_change().dropna()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    sharpe = (r.mean() * 252 - rf_annual) / vol if vol > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    return {
        "CAGR": cagr, "Vol": vol, "Sharpe": sharpe, "MaxDD": dd,
        "Calmar": cagr / abs(dd) if dd < 0 else np.nan, "Years": yrs,
    }

def yearly(eq: pd.Series) -> pd.Series:
    return eq.resample("YE").last().pct_change().dropna() * 100

def fmt_m(m: dict) -> str:
    return (f"CAGR {m['CAGR']*100:>6.1f}%  Vol {m['Vol']*100:>5.1f}%  "
            f"Sharpe {m['Sharpe']:>5.2f}  MaxDD {m['MaxDD']*100:>6.1f}%  "
            f"Calmar {m['Calmar']:>5.2f}")

def month_ends(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(index=idx)
    return list(s.groupby([idx.year, idx.month]).apply(lambda g: g.index[-1]))

def mom_matrix(px: pd.DataFrame, lookback: int, skip: int) -> pd.DataFrame:
    """每月末的动量矩阵（信号，非执行）。"""
    out = {}
    P = px
    for t in month_ends(px.index):
        pos_now = P.index.get_loc(t)
        if pos_now - lookback < 0:
            continue
        p_now = P.iloc[pos_now - skip]
        p_past = P.iloc[pos_now - lookback]
        with np.errstate(divide="ignore", invalid="ignore"):
            out[t] = (p_now / p_past - 1.0)
    return pd.DataFrame(out).T

def rv_pct_matrix(px: pd.DataFrame, window: int = 20, rank_win: int = 756,
                  min_periods: int = 252) -> pd.DataFrame:
    rv = px.pct_change().rolling(window).std() * np.sqrt(252)
    return rv.rolling(rank_win, min_periods=min_periods).rank(pct=True)

# ════════════════════════════════════════════════════════════════════
# A. 板块 12-1 轮动（2018-09 → 2026-08，20 板块）
# ════════════════════════════════════════════════════════════════════
log("=" * 96)
log("A. 板块 12-1 轮动策略化回测（20 板块合成指数，2018-09 → 2026-08，月频，t+1 收盘执行）")
log(f"   成本假设：单边 {COST_SECTOR*100:.1f}%（合成指数不可交易，偏高取值）；现金收益 {RF_ANNUAL*100:.1f}%/年")
log("=" * 96)

sec_bt = secpx.loc["2017-08-01":]  # 留 warmup
sec_rv_pct = rv_pct_matrix(sec_bt)

def rotate(px, moms, top_n, gate: str, cost):
    """月频轮动。gate: none | rvpct | absmom | both"""
    W = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    rv = sec_rv_pct.reindex(moms.index)
    prev_sig_date = None
    for i, t in enumerate(moms.index):
        m = moms.loc[t]
        elig = m.dropna()
        if len(elig) == 0:
            continue
        # 执行日 = 信号日 t 的下一交易日（权重从执行日收盘起生效 → 次日收益开始计入）
        pos_t = px.index.get_loc(t)
        e = px.index[pos_t + 1] if pos_t + 1 < len(px.index) else None
        if e is None:
            continue
        next_sig = moms.index[i + 1] if i + 1 < len(moms.index) else px.index[-1]
        pos_n = px.index.get_loc(next_sig)
        e_next = px.index[min(pos_n + 1, len(px.index) - 1)]
        cand = elig
        if gate in ("rvpct", "both"):
            r = rv.loc[t].reindex(cand.index)
            cand = cand[~(r >= 0.8)]
        if gate in ("absmom", "both"):
            cand = cand[cand > 0]
        if len(cand) == 0:
            continue  # 全现金（权重 0 已是默认）
        top = cand.sort_values(ascending=False).head(top_n)
        w_row = pd.Series(0.0, index=px.columns)
        w_row[top.index] = 1.0 / len(top)
        # 权重生效区间：(e, e_next] —— 即从执行日次日起吃到下个执行日
        mask = (W.index > e) & (W.index <= e_next)
        W.loc[mask] = w_row.values
    eq = run_from_weights(px, W, cost)
    # 月均换手 = 总换手 / 月数（换手发生在执行日次日，取全期汇总更稳）
    to = W.diff().abs().sum(axis=1)
    me_to = to.sum() / max(len(month_ends(W.index)) - 1, 1)
    return eq, me_to

# 基准
W_eqw = None
me_list = month_ends(sec_bt.index)
sig_dates = [t for t in me_list if t >= pd.Timestamp("2018-09-01") and sec_bt.index.get_loc(t) >= 252]

def eqw_weights(px, sig_dates):
    W = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for i, t in enumerate(sig_dates):
        pos_t = px.index.get_loc(t)
        e = px.index[pos_t + 1] if pos_t + 1 < len(px.index) else None
        if e is None:
            continue
        next_sig = sig_dates[i + 1] if i + 1 < len(sig_dates) else px.index[-1]
        pos_n = px.index.get_loc(next_sig)
        e_next = px.index[min(pos_n + 1, len(px.index) - 1)]
        alive = px.columns[px.loc[:t].notna().any()].tolist()
        hist = px.loc[:t, alive]
        alive = [c for c in alive if hist[c].notna().iloc[-1]]
        w_row = pd.Series(0.0, index=px.columns)
        w_row[alive] = 1.0 / len(alive)
        mask = (W.index > e) & (W.index <= e_next)
        W.loc[mask] = w_row.values
    return W

W_eqw = eqw_weights(sec_bt, sig_dates)
eq_base = run_from_weights(sec_bt, W_eqw, COST_SECTOR)
m0 = metrics(eq_base)
log(f"基准1 等权20板块（月再平衡，含成本）: {fmt_m(m0)}")
cash_series = pd.Series(RF_DAILY, index=sec_bt.loc[sig_dates[0]:].index).dropna()
cash_eq = (1 + cash_series).cumprod()
m_cash = metrics(cash_eq)
log(f"基准2 纯现金:                          {fmt_m(m_cash)}")
log("")

# 主配置网格：N × gate
log("── 主网格（lookback=252, skip=21）────────────────────────────────────────────")
log(f"{'配置':<34}{'年化':>8}{'Sharpe':>8}{'MaxDD':>8}{'Calmar':>8}{'月换手':>8}")
base_rows = {}
for top_n in (1, 3, 5):
    for gate, gate_cn in [("none", "无过滤"), ("rvpct", "RV分位闸"), ("absmom", "绝对动量"), ("both", "双重")]:
        moms = mom_matrix(sec_bt, 252, 21)
        moms = moms.loc[moms.index >= pd.Timestamp("2018-09-01")]
        eq, to = rotate(sec_bt, moms, top_n, gate, COST_SECTOR)
        m = metrics(eq)
        base_rows[(top_n, gate)] = (eq, m, to)
        log(f"top{top_n} · {gate_cn:<20}{m['CAGR']*100:>7.1f}%{m['Sharpe']:>8.2f}{m['MaxDD']*100:>7.1f}%{m['Calmar']:>8.2f}{to:>8.2f}")
log("")

# 参数邻域：skip × lookback（N=3, 无过滤 + RV 闸）
log("── 参数邻域（N=3；上三角=无过滤 / 下三角含 RV 闸仅参考）─────────────────")
hdr = "lookback/skip"
log(f"{hdr:<16}{'skip=0':>14}{'skip=21':>14}{'skip=42':>14}")
for lb in (180, 252, 360):
    row = [f"{lb:<16}"]
    for sk in (0, 21, 42):
        moms = mom_matrix(sec_bt, lb, sk)
        moms = moms.loc[moms.index >= pd.Timestamp("2018-09-01")]
        eq, _ = rotate(sec_bt, moms, 3, "none", COST_SECTOR)
        m = metrics(eq)
        row.append(f"{m['CAGR']*100:>6.1f}%/{m['Sharpe']:.2f}")
    log("".join(row))
log("")

# 分年表（top3 无过滤 vs top3 RV闸 vs 等权）
log("── 分年收益（%）：top3无过滤 / top3·RV闸 / 等权20 ──────────────────────────")
eq3 = base_rows[(3, "none")][0]
eq3r = base_rows[(3, "rvpct")][0]
y1, y2, y3 = yearly(eq3), yearly(base_rows[(3, "rvpct")][0]), yearly(eq_base)
all_y = sorted(set(y1.index) | set(y3.index))
for y in all_y:
    a = y1.get(y, np.nan); b = y2.get(y, np.nan); c = y3.get(y, np.nan)
    log(f"{y.year:<6}{a:>8.1f}{b:>10.1f}{c:>10.1f}")
log("")

# 前后半段切分（top3 无过滤）
log("── 前后半段切分（top3 无过滤）：")
for lo, hi, tag in [("2018-09-01", "2022-12-31", "前半 2018-09~2022-12"), ("2023-01-01", "2026-08-27", "后半 2023-01~2026-08")]:
    seg = eq3.loc[lo:hi]
    m = metrics(seg)
    log(f"  {tag:<26}{fmt_m(m)}")
log("")

# 最差 5 个月（动量崩溃检查）
log("── top3 无过滤的最差 5 个月（动量崩溃检查）：")
mr = eq3.resample("ME").last().pct_change().dropna() * 100
for d, v in mr.nsmallest(5).items():
    log(f"  {d.strftime('%Y-%m')}  {v:>6.1f}%")

# ════════════════════════════════════════════════════════════════════
# B. ETF 池轮动（动态入池，2021-01 → 2026-08）
# ════════════════════════════════════════════════════════════════════
log("")
log("=" * 96)
log("B. ETF 池轮动（动态入池：上市满 253 交易日才候选；2021-01 → 2026-08；单边 0.1%）")
log("=" * 96)

etf_rv_pct = rv_pct_matrix(etfpx)
ema60 = etfpx.ewm(span=60).mean()

def etf_rotate(sig_kind: str, top_n: int, gate: str):
    W = pd.DataFrame(0.0, index=etfpx.index, columns=etfpx.columns)
    mes = [d for d in month_ends(etfpx.index) if d >= pd.Timestamp("2020-10-01")]
    for i, t in enumerate(mes):
        P = etfpx
        pos_t = P.index.get_loc(t)
        if pos_t - 253 < 0:
            continue
        e_idx = pos_t + 1
        if e_idx >= len(P.index):
            continue
        e = P.index[e_idx]
        nt = mes[i + 1] if i + 1 < len(mes) else P.index[-1]
        e_next = P.index[min(P.index.get_loc(nt) + 1, len(P.index) - 1)]
        # 候选：截至 t 有 253 个非空值（ffill 后上市前仍是 NaN，不会误计入池）
        cand_codes = [c for c in P.columns
                      if P[c].loc[:t].notna().sum() >= 253 and pd.notna(P[c].loc[t])]
        if len(cand_codes) < 3:
            continue
        sub = P[cand_codes]
        pt = sub.index.get_loc(t)
        hist = sub.loc[:t]  # 防 mixed 信号未来函数：一切比值只用 ≤t 的数据
        if sig_kind == "12-1":
            sig = pd.Series({c: hist[c].iloc[-22] / hist[c].iloc[-253] - 1 for c in cand_codes})
        elif sig_kind == "mom60":
            sig = pd.Series({c: hist[c].iloc[-1] / hist[c].iloc[-61] - 1 for c in cand_codes})
        else:  # mixed rank（截面排名均值）
            r20 = hist.apply(lambda s: s.iloc[-1] / s.iloc[-21] - 1 if s.notna().sum() >= 21 else np.nan)
            r60 = hist.apply(lambda s: s.iloc[-1] / s.iloc[-61] - 1 if s.notna().sum() >= 61 else np.nan)
            r120 = hist.apply(lambda s: s.iloc[-1] / s.iloc[-121] - 1 if s.notna().sum() >= 121 else np.nan)
            rk = pd.DataFrame({"a": r20, "b": r60, "c": r120}).rank()
            sig = rk.mean(axis=1)
        sig = sig.replace([np.inf, -np.inf], np.nan).dropna()
        if gate in ("rvpct", "both"):
            r = etf_rv_pct.loc[t].reindex(sig.index)
            sig = sig[~(r >= 0.8)]
        if gate in ("ma60", "both"):
            above = (sub.loc[t].reindex(sig.index) > ema60.loc[t].reindex(sig.index))
            sig = sig[above.fillna(False)]
        if len(sig) == 0:
            continue
        top = sig.sort_values(ascending=False).head(top_n)
        w_row = pd.Series(0.0, index=P.columns)
        w_row[top.index] = 1.0 / len(top)
        mask = (W.index > e) & (W.index <= e_next)
        W.loc[mask] = w_row.values
    return run_from_weights(etfpx.loc["2021-01-01":], W.loc["2021-01-01":], COST_ETF)

# 基准：等权动态池
W_b = pd.DataFrame(0.0, index=etfpx.index, columns=etfpx.columns)
mes = [d for d in month_ends(etfpx.index) if d >= pd.Timestamp("2020-10-01")]
for i, t in enumerate(mes):
    P = etfpx
    pos_t = P.index.get_loc(t)
    e_idx = pos_t + 1
    if e_idx >= len(P.index):
        continue
    e = P.index[e_idx]
    nt = mes[i + 1] if i + 1 < len(mes) else P.index[-1]
    e_next = P.index[min(P.index.get_loc(nt) + 1, len(P.index) - 1)]
    cand = [c for c in P.columns
            if P[c].loc[:t].notna().sum() >= 253 and pd.notna(P[c].loc[t])]
    if len(cand) < 3:
        continue
    w_row = pd.Series(0.0, index=P.columns)
    w_row[cand] = 1.0 / len(cand)
    W_b.loc[(W_b.index > e) & (W_b.index <= e_next)] = w_row.values
eq_etf_base = run_from_weights(etfpx.loc["2021-01-01":], W_b.loc["2021-01-01":], COST_ETF)
log(f"基准 等权动态池:        {fmt_m(metrics(eq_etf_base))}")
log(f"{'配置':<30}{'年化':>8}{'Sharpe':>8}{'MaxDD':>8}{'Calmar':>8}")
for kind, kind_cn in [("12-1", "12-1动量"), ("mom60", "60日动量"), ("mixed", "混合20/60/120")]:
    for gate, gate_cn in [("none", ""), ("rvpct", "+RV闸"), ("ma60", "+MA60闸"), ("both", "+双闸")]:
        eq = etf_rotate(kind, 3, gate)
        m = metrics(eq)
        log(f"{kind_cn} top3 {gate_cn:<8}{m['CAGR']*100:>7.1f}%{m['Sharpe']:>8.2f}{m['MaxDD']*100:>7.1f}%{m['Calmar']:>8.2f}")
log("")
log("警示：本 B 段样本仅 ~5.6 年且池内标的后期才齐，统计功效有限，只看方向。")

# ════════════════════════════════════════════════════════════════════
# C. 波动率管理对趋势规则的增益（日频，板块+长史ETF）
# ════════════════════════════════════════════════════════════════════
log("")
log("=" * 96)
log("C. 波动率管理对趋势规则的增益（日频；规则在 t 收盘判定，t+1 生效；单边 0.1%）")
log("=" * 96)

C_ASSETS = SEC_CODES + ["510300.SS", "512400.SS", "515050.SS", "518850.SS", "588000.SS"]
cpx = load_closes(C_ASSETS).ffill()

def trend_variant(px: pd.DataFrame, rule: str, variant: str, start="2018-09-01") -> pd.Series | None:
    """variant: plain | vtarget | gate | half"""
    close = px.loc[start:]
    if len(close) < 300:
        return None
    rets = close.pct_change()
    if rule == "ema20":
        sig = close > close.ewm(span=20).mean()
    elif rule == "ema60":
        sig = close > close.ewm(span=60).mean()
    elif rule == "sma200":
        sig = close > close.rolling(200).mean()
    elif rule == "ema20>ema60":
        sig = close.ewm(span=20).mean() > close.ewm(span=60).mean()
    else:
        return None
    rv20 = rets.rolling(20).std() * np.sqrt(252)
    rv_pct = rv20.rolling(756, min_periods=252).rank(pct=True)
    full_vol = rets.std() * np.sqrt(252)  # 全样本波动做目标（同资产可比）
    w = sig.shift(1).fillna(False).astype(float)  # t 收盘信号 → t+1 生效
    if variant == "vtarget":
        scale = (full_vol / rv20).clip(0.25, 1.0)
        w = w * scale.shift(1).fillna(1.0)
    elif variant == "gate":
        w = w * (~((rv_pct.shift(1) >= 0.8))).astype(float)
    elif variant == "half":
        scale = pd.Series(1.0, index=w.index)
        scale[(rv_pct.shift(1) >= 0.8)] = 0.5
        w = w * scale
    idle = (1 - w).clip(lower=0)
    daily = (w.T * rets.T).sum() + idle["__x__" if "__x__" in idle.columns else idle.columns[0]] * 0  # placeholder
    # 逐资产算，再汇总由调用方处理
    return w  # type: ignore

# 重新实现 C：逐资产独立回测，然后聚合对比（更清晰）
def one_asset_backtest(close: pd.Series, rule: str, variant: str, start="2018-09-01"):
    close = close.loc[start:].dropna()
    if len(close) < 300:
        return None
    rets = close.pct_change()
    if rule == "ema20":
        sig = close > close.ewm(span=20).mean()
    elif rule == "ema60":
        sig = close > close.ewm(span=60).mean()
    elif rule == "sma200":
        sig = close > close.rolling(200).mean() if len(close) > 200 else None
        if sig is None:
            return None
    else:  # ema20>ema60
        sig = close.ewm(span=20).mean() > close.ewm(span=60).mean()
    rv20 = rets.rolling(20).std() * np.sqrt(252)
    rv_pct = rv20.rolling(756, min_periods=252).rank(pct=True)
    full_vol = rets.dropna().std() * np.sqrt(252)
    if not np.isfinite(full_vol) or full_vol == 0:
        return None
    w = sig.shift(1).astype(float)
    if variant == "vtarget":
        scale = (full_vol / rv20).clip(0.25, 1.0)
        w = w * scale.shift(1)
    elif variant == "gate":
        w = w.where(~(rv_pct.shift(1) >= 0.8), 0.0)
    elif variant == "half":
        scale = pd.Series(1.0, index=w.index)
        scale[(rv_pct.shift(1) >= 0.8)] = 0.5
        w = w * scale
    w = w.fillna(0.0)
    idle = (1 - w).clip(lower=0)
    daily = w * rets + idle * RF_DAILY
    to = w.diff().abs().fillna(0.0)
    daily = daily - to * COST_ETF
    eq = (1 + daily.fillna(0)).cumprod()
    return eq

VARIANTS = [("plain", "满仓基线"), ("vtarget", "目标波动"), ("gate", "高波空仓"), ("half", "高波减半")]
RULES = [("ema20", "价>EMA20"), ("ema60", "价>EMA60"), ("sma200", "价>SMA200"), ("ema20>ema60", "EMA20>60")]
agg = {}
for rule, _ in RULES:
    for var, _ in VARIANTS:
        agg[(rule, var)] = {"sharpe": [], "maxdd": [], "cagr": [], "eqs": {}}
log(f"{'资产数':<4} 逐资产 Sharpe（各变体相对满仓基线的提升记 +）")
imp_counts = {v: [0, 0] for v, _ in VARIANTS}  # (better, worse) on Sharpe
for code in C_ASSETS:
    close = cpx[code]
    for rule, _ in RULES:
        base = one_asset_backtest(close, rule, "plain")
        if base is None:
            continue
        mb = metrics(base)
        agg[(rule, "plain")]["sharpe"].append(mb["Sharpe"])
        agg[(rule, "plain")]["eqs"][code] = base
        for var, _ in VARIANTS[1:]:
            eq = one_asset_backtest(close, rule, var)
            if eq is None:
                continue
            m = metrics(eq)
            agg[(rule, var)]["sharpe"].append(m["Sharpe"])
            agg[(rule, var)]["eqs"][code] = eq
            if np.isfinite(m["Sharpe"]) and np.isfinite(mb["Sharpe"]):
                if m["Sharpe"] > mb["Sharpe"]:
                    imp_counts[var][0] += 1
                elif m["Sharpe"] < mb["Sharpe"]:
                    imp_counts[var][1] += 1

log(f"{'规则':<12}{'变体':<10}{'平均Sharpe':>10}{'Sharpe中位':>10}")
for rule, rule_cn in RULES:
    for var, var_cn in VARIANTS:
        v = agg[(rule, var)]["sharpe"]
        if not v:
            continue
        log(f"{rule_cn:<12}{var_cn:<10}{np.nanmean(v):>10.2f}{np.nanmedian(v):>10.2f}")
log("")
log("逐资产 Sharpe 提升计数（各变体 vs 同规则满仓基线）：")
for var, _ in VARIANTS[1:]:
    b, w_ = imp_counts[var]
    log(f"  {var:<8} 提升 {b:>3} / 变差 {w_:>3}  （资产×规则 对数）")
log("")
# 等权组合层面（每规则×变体把 25 个资产等权合成一条曲线，看组合级指标）
log("── 组合层面（25 资产等权合成净值）─────────────────────────────────────────")
log(f"{'规则':<12}{'变体':<10}{'年化':>8}{'Sharpe':>8}{'MaxDD':>8}")
port_eqs = {}
for rule, rule_cn in RULES:
    for var, var_cn in VARIANTS:
        eqs = agg[(rule, var)]["eqs"]
        if len(eqs) < 5:
            continue
        df = pd.DataFrame(eqs)
        idx = df.index
        port = df.pct_change().mean(axis=1).dropna()
        eq = (1 + port).cumprod()
        m = metrics(eq)
        port_eqs[(rule, var)] = (eq, m)
        log(f"{rule_cn:<12}{var_cn:<10}{m['CAGR']*100:>7.1f}%{m['Sharpe']:>8.2f}{m['MaxDD']*100:>7.1f}%")
log("")
# 组合层面分年（ema20 规则）
log("── 组合分年收益（%）规则=价>EMA20：满仓 vs 目标波动 vs 高波减半 ────────────")
if all(k in port_eqs for k in [("ema20", "plain"), ("ema20", "vtarget"), ("ema20", "half"), ("ema20", "gate")]):
    ys = {v: yearly(port_eqs[("ema20", v)][0]) for v in ("plain", "vtarget", "gate", "half")}
    for y in sorted(ys["plain"].index):
        log(f"{y.year:<6}{ys['plain'].get(y, float('nan')):>8.1f}{ys['vtarget'].get(y, float('nan')):>10.1f}{ys['gate'].get(y, float('nan')):>10.1f}{ys['half'].get(y, float('nan')):>10.1f}")

with open("/tmp/factor_backtest_results.txt", "w") as f:
    f.write("\n".join(OUT))
log("")
log("结果已存 /tmp/factor_backtest_results.txt")
