#!/usr/bin/env python3
"""vt 目标波动缩放 · 落地细节网格（Prompt H，2026-09-01）。

任务书：新方向探索 Prompt H——vt 是环境组唯一 passed 且三次独立复验的仓位机制，
但其落地细节（目标水平/RV 估计器/调整频率/作用层）从未网格化，当前通过结论依赖
单一实现、邻域未扫。本脚本补这个洞：不重验 vt 本身是否有效，只回答——
  ① 现行实现是否处于参数高原而非孤峰；
  ② 组合层（huanjing 引擎）与单资产层（C 节引擎）最优参数是否一致。

引擎复用（未改动任何现有脚本，本文件为独立新增）：
  - 组合层 = scripts/archive_huanjing_cangwei.py 的 build/run_from_weights 原样移植；
  - 单资产层 = lei-signal-sync scripts/repro_factor_backtest.py 的 one_asset_backtest
    （C 节）原样移植，仅把 vt 缩放的「目标/估计器/更新频率」参数化。

════════════════════════════════════════════════════════════════════════
判定标准（跑前固化，跑完不改；单元格判定延续 huanjing-ARCHIVE 固化公式）
════════════════════════════════════════════════════════════════════════

单元格判定（两层各自独立，基准=同层现行频率的等权满仓、同费用口径）：
  改善比 r = Calmar(单元格) / Calmar(基准) − 1
  - passed（通过）  ：r > +10% 且 CAGR ≥ 基准 CAGR
  - watch（中性观察）：不满足通过、且 r > −10% 且 CAGR ≥ 基准 CAGR − 3pp
  - falsified（证伪）：其余
  基准：组合层 = 等权满仓月频（huanjing base）；单资产层 = 价>EMA20 趋势满仓
  日频合成（C 节 plain）。费用压力档（单边 0.2%）用同费用档的基准判。

网格形状判定（本任务核心问题——孤峰 vs 高原，事前固化）：
  A. 目标维度：固定（估计器=rv20、频率=现行）扫 8 档目标
     {10, 12.5, 15, 16.5, 17.5, 20, 22.5%} + full 锚点（=基准全样本波动），
     非 falsified（passed|watch）≥5/8 → 「高原」；≤2/8 → 「孤峰/窄带」；
     其余 → 「过渡带」。
  B. 估计器维度：{rv20, ewma94, ewma97, garch 固定参数} 4 种中 ≥3 种在
     （目标=full 锚点、频率=现行）非 falsified → 「稳健」；否则「估计器敏感」。
  C. 频率维度：组合层 {月/周/季}、单资产层 {日/周/月} 3 档中 ≥2 档在
     （目标=full 锚点、估计器=rv20）非 falsified → 「稳健」。
  D. 层间一致：两层在（估计器=rv20、频率=现行）下的最优目标档（Calmar 最大，
     档位梯子 [10,12.5,15,16.5,17.5,20,≈22.08(full),22.5]）相差 ≤1 档 →
     「层间一致」；否则「分层需异参」（=新发现，单独标注）。
  E. 费用稳健：单边 0.2%（vs 现行 0.1%）下 full 锚点单元格 verdict 不降为
     falsified → 「稳健」。

复现校验（内部效度，跑即核对）：
  R1 组合层 full 锚点（full/rv20/月频/0.1%）必须复现 raw/huanjing/vt.json 指标
     （CAGR 0.16437109566646702、Calmar 0.44680461266349153，容差 1e-6；
      超差即中止，环境漂移会使全部结论无效）。
  R2 单资产层 full 锚点（own/rv20/日频）复现 C 节口径量级：组合级（ema20 规则）
     Sharpe plain ≈0.79 → vt ≈0.84、逐资产×规则 Sharpe 提升计数 ≈53↑/47↓
     （容差 ±2 计数 / ±0.02 Sharpe；超差不中止但如实标注，供归档解读）。

已知局限（结论解读必带）：
  ① full 锚点目标=基准/资产全样本波动（轻前视，同 huanjing ③、C 节归档口径）；
     固定目标档无此问题——若固定档与 full 锚点结论一致，落地可弃用全样本依赖。
  ② garch 估计器为固定参数 (α,β)=(0.05,0.90)、ω 锚定滚动 756 日方差的滤波版，
     未做滚动 MLE 重估（arch 包不可用；重估的数值稳定性/成本取舍）——它只代表
     「GARCH 族的简化滤波」，不代表完整 GARCH。EWMA 用 pandas ewm.std
     （含无偏修正），λ=0.94（RiskMetrics 日）/0.97（慢）两档。
  ③ 环境层 a_share_klines_full 含幸存者偏差（同 huanjing ④）；ETF 池偏成长行业
     （同 huanjing ⑤）；C 节 25 资产中板块指数为等权合成含成员前视（同 C 节声明）。
  ④ 网格内所有格子共享同一样本区间（同轮多重比较，同 huanjing ⑥）；A-E 形状
     判据即为对抗「挑最优格子」的设计，报告必须呈现整张网格而非只报最优点。
  ⑤ 单资产层「频率」仅指 vt 缩放系数的更新频率（趋势信号保持日频）；
     组合层「频率」=再平衡频率（池子/权重/E 同步），与 huanjing 原实现同构。

防未来函数：信号/估计均在再平衡日 t 收盘计算，t+1 收盘执行；EWMA/GARCH/rv20
只用截至 t 的数据；现金 1.5%/年；单边成本 0.1%（主）/0.2%（压力）。

复现：cd docs/experiments/raw/vt-grid && PYTHONHASHSEED=0 python3 run_vt_grid.py
双跑：PYTHONHASHSEED=0 与 =42 各跑一次，比对两次打印的哈希（并落 hash_0/42.json）。
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CACHE = Path("/Users/yongbiaoli/.lei_signal_lab/cache")
REF_HUANJING = REPO / "docs/experiments/raw/huanjing"

RF_ANNUAL = 0.015
RF_DAILY = (1 + RF_ANNUAL) ** (1 / 252) - 1
COSTS = [("cost10", 0.001), ("cost20", 0.002)]
START_MAIN, START_ALT, END = "2020-01-01", "2021-01-01", "2026-08-18"

ETF_POOL = ["510300.SS", "588000.SS", "512400.SS", "515050.SS", "515130.SS",
            "515300.SS", "515170.SS", "516220.SS", "159652.SZ", "562590.SS", "515880.SS"]

TARGETS = [0.10, 0.125, 0.15, 0.165, 0.175, 0.20, 0.225]  # + "full" 锚点
TARGET_LADDER = [0.10, 0.125, 0.15, 0.165, 0.175, 0.20, 22.08e-2, 0.225]  # full≈0.2208 排 20 与 22.5 之间
ESTIMATORS = ["rv20", "ewma94", "ewma97", "garch"]
FREQS_PORT = ["monthly", "weekly", "quarterly"]
FREQS_SA = ["daily", "weekly", "monthly"]

SA_START = "2018-09-01"
C_ASSETS = sorted(
    Path(f).name.split(".SECTOR.bars")[0] + ".SECTOR"
    for f in glob.glob(str(CACHE / "*.SECTOR.bars.parquet"))
) + ["510300.SS", "512400.SS", "515050.SS", "518850.SS", "588000.SS"]

CRITERIA_CN = (
    "单元格：r=Calmar变体/Calmar基准−1；passed: r>+10%且CAGR≥基准；"
    "watch: −10%<r≤+10%且CAGR≥基准−3pp；falsified: 其余（基准=同层现行频率等权满仓、同费用）。"
    "形状：A 目标8档非falsified≥5→高原/≤2→孤峰；B 估计器4种≥3非falsified→稳健；"
    "C 频率3档≥2非falsified→稳健；D 两层最优目标档差≤1档→层间一致；"
    "E 0.2%费用下full锚点不降为falsified→费用稳健。"
)


# ── 指标（与 huanjing/C 节同口径）────────────────────────────────────────
def metrics(eq: pd.Series) -> dict:
    r = eq.pct_change().dropna()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(252)
    dd = float((eq / eq.cummax() - 1).min())
    return {"CAGR": float(cagr), "Vol": float(vol),
            "Sharpe": float((r.mean() * 252 - RF_ANNUAL) / vol) if vol > 0 else None,
            "MaxDD": dd, "Calmar": float(cagr / abs(dd)) if dd < 0 else None}


def verdict_of(m: dict, base: dict) -> tuple[str, float]:
    r = m["Calmar"] / base["Calmar"] - 1
    if r > 0.10 and m["CAGR"] >= base["CAGR"]:
        return "passed", r
    if r > -0.10 and m["CAGR"] >= base["CAGR"] - 0.03:
        return "watch", r
    return "falsified", r


# ── 波动率估计器（日收益序列 → 年化波动估计）──────────────────────────────
def vol_series(rets: pd.Series, kind: str) -> pd.Series:
    if kind == "rv20":
        return rets.rolling(20).std() * np.sqrt(252.0)
    if kind == "ewma94":
        return rets.ewm(alpha=0.06, min_periods=20).std() * np.sqrt(252.0)
    if kind == "ewma97":
        return rets.ewm(alpha=0.03, min_periods=20).std() * np.sqrt(252.0)
    if kind == "garch":
        a, b = 0.05, 0.90
        r = rets.to_numpy(dtype=float)
        V = rets.rolling(756, min_periods=252).var().to_numpy(dtype=float)
        n = len(r)
        s2 = np.full(n, np.nan)
        t0 = 0
        while t0 < n and not np.isfinite(V[t0]):
            t0 += 1
        if t0 < n:
            s2[t0] = V[t0]
            for t in range(t0 + 1, n):
                prev_r2 = r[t - 1] ** 2 if np.isfinite(r[t - 1]) else s2[t - 1]
                v = V[t - 1] if np.isfinite(V[t - 1]) else s2[t - 1]
                s2[t] = (1 - a - b) * v + a * prev_r2 + b * s2[t - 1]
        return pd.Series(np.sqrt(s2 * 252.0), index=rets.index)
    raise ValueError(kind)


# ── 再平衡日（各频率最后一个交易日）──────────────────────────────────────
def rebal_dates(idx: pd.DatetimeIndex, freq: str) -> list[pd.Timestamp]:
    s = pd.Series(index=idx)
    if freq == "monthly":
        return list(s.groupby([idx.year, idx.month]).apply(lambda g: g.index[-1]))
    if freq == "quarterly":
        return list(s.groupby([idx.year, idx.quarter]).apply(lambda g: g.index[-1]))
    if freq == "weekly":
        iso = idx.isocalendar()
        return list(s.groupby([iso.year, iso.week]).apply(lambda g: g.index[-1]))
    raise ValueError(freq)


# ══════════════════════════════════════════════════════════════════════
# 组合层引擎（archive_huanjing_cangwei.py 原样移植，参数化 target/est/freq/cost）
# ══════════════════════════════════════════════════════════════════════
def load_env() -> tuple[pd.Series, pd.Series]:
    stock = pd.read_parquet(CACHE / "a_share_klines_full.parquet").loc["2015-01-01":]
    close = stock.astype(float)
    valid = close.notna()
    sma50 = close.rolling(50).mean()
    b50 = ((close > sma50).where(valid).sum(axis=1) / valid.sum(axis=1))
    daily = close.pct_change(fill_method=None).where(valid).mean(axis=1, skipna=True)
    rv20 = daily.rolling(20).std() * np.sqrt(252.0)
    rv_pct = rv20.rolling(756, min_periods=252).rank(pct=True)
    return b50, rv_pct


def load_px() -> pd.DataFrame:
    etf = {c: pd.read_parquet(CACHE / f"{c}.bars.parquet")["close"].astype(float)
           for c in ETF_POOL}
    return pd.DataFrame(etf).sort_index().ffill()


def run_from_weights(p: pd.DataFrame, w: pd.DataFrame, cost: float) -> pd.Series:
    rets = p.pct_change(fill_method=None)
    wr = w.reindex(p.index).fillna(0.0)
    rr = rets.reindex(p.index).fillna(0.0)
    net = (wr * rr).sum(axis=1) + (1.0 - wr.sum(axis=1)).clip(lower=0.0) * RF_DAILY
    to = wr.diff().abs().sum(axis=1).fillna(wr.iloc[0].abs().sum())
    return (1 + net - to * cost).cumprod()


def build_port(px, b50, rv_pct, notna_cum, est_vol, start, target, freq, cost):
    """月末/周末/季末 t 收盘信号，t+1 收盘执行；target=None 表示基准（E≡1）。"""
    p = px.loc[:END]
    W = pd.DataFrame(0.0, index=p.index, columns=p.columns)
    E_daily = pd.Series(np.nan, index=p.index)
    dates = [d for d in rebal_dates(p.index, freq) if pd.Timestamp(start) <= d <= pd.Timestamp(END)]
    for i, t in enumerate(dates):
        e_idx = p.index.get_loc(t) + 1
        if e_idx >= len(p.index):
            continue
        e, nt = p.index[e_idx], (dates[i + 1] if i + 1 < len(dates) else p.index[-1])
        e_next = p.index[min(p.index.get_loc(nt) + 1, len(p.index) - 1)]
        counts = notna_cum.loc[t]
        cand = [c for c in p.columns
                if counts[c] >= 253 and pd.notna(p[c].loc[t])]
        if len(cand) < 2:
            continue
        E, b_t, r_t = 1.0, b50.asof(t), rv_pct.asof(t)
        if target is not None and pd.notna(b_t) and pd.notna(r_t):
            est = est_vol.asof(t)
            if pd.notna(est) and est > 0:
                E = float(np.clip(target / est, 0.25, 1.0))
        w_row = pd.Series(0.0, index=p.columns)
        w_row[cand] = E / len(cand)
        mask = (W.index > e) & (W.index <= e_next)
        W.loc[mask] = w_row.values
        E_daily.loc[mask] = E
    eq = run_from_weights(p.loc[start:], W.loc[start:], cost)
    return eq, E_daily.loc[start:]


# ══════════════════════════════════════════════════════════════════════
# 单资产层引擎（repro_factor_backtest.py one_asset_backtest 原样移植）
# ══════════════════════════════════════════════════════════════════════
def sig_of(close: pd.Series, rule: str) -> pd.Series | None:
    if rule == "ema20":
        return close > close.ewm(span=20).mean()
    if rule == "ema60":
        return close > close.ewm(span=60).mean()
    if rule == "sma200":
        return close > close.rolling(200).mean() if len(close) > 200 else None
    if rule == "ema20>ema60":
        return close.ewm(span=20).mean() > close.ewm(span=60).mean()
    raise ValueError(rule)


def one_asset(close, est, sig, target, freq, cost):
    """close/est/sig 已对齐同一指数；target=None 表示 plain 基线（无 vt 缩放）。"""
    rets = close.pct_change()
    w = sig.shift(1).astype(float)
    if target is not None:
        scale_raw = (target / est).clip(0.25, 1.0)
        if freq == "daily":
            scale_lag = scale_raw.shift(1)
        else:
            bd = rebal_dates(close.index, freq)
            scale_lag = scale_raw.loc[bd].reindex(close.index).ffill().shift(1)
        w = w * scale_lag
    w = w.fillna(0.0)
    idle = (1 - w).clip(lower=0)
    daily = w * rets + idle * RF_DAILY
    to = w.diff().abs().fillna(0.0)
    daily = daily - to * cost
    return (1 + daily.fillna(0)).cumprod()


def combined(eqs: dict) -> pd.Series | None:
    if len(eqs) < 5:
        return None
    df = pd.DataFrame(eqs)
    port = df.pct_change().mean(axis=1).dropna()
    return (1 + port).cumprod()


# ══════════════════════════════════════════════════════════════════════
# 核心
# ══════════════════════════════════════════════════════════════════════
def compute_all() -> dict:
    out: dict = {"meta": {
        "task": "Prompt H: vt 落地细节网格（目标×估计器×频率×作用层）",
        "pool_port": ETF_POOL, "assets_sa": C_ASSETS,
        "window_port": f"{START_MAIN}→{END}（主）+ {START_ALT}→{END}（辅助）",
        "window_sa": f"{SA_START}→末根（C 节同窗）",
        "targets": TARGETS + ["full"], "estimators": ESTIMATORS,
        "freqs_port": FREQS_PORT, "freqs_sa": FREQS_SA,
        "costs": dict(COSTS), "rf": RF_ANNUAL, "criteria_cn": CRITERIA_CN}}

    # ── R1 复现校验（先于网格；超差中止）──────────────────────────────
    ref_vt = json.loads((REF_HUANJING / "vt.json").read_text())
    ref_base = json.loads((REF_HUANJING / "base.json").read_text())

    b50, rv_pct = load_env()
    px = load_px()
    p_end = px.loc[:END]
    port_ret = p_end.pct_change(fill_method=None).mean(axis=1)
    notna_cum = p_end.notna().cumsum()
    est_port = {k: vol_series(port_ret, k) for k in ESTIMATORS}

    port_res: dict = {"bases": {}, "cells": {}, "anchor_detail": {}}
    # 基准（现行频率=月频）与各频率同款满仓基线
    base_eqs = {}
    for cost_tag, cost in COSTS:
        for freq in FREQS_PORT:
            eq, _ = build_port(px, b50, rv_pct, notna_cum, None, START_MAIN, None, freq, cost)
            base_eqs[(cost_tag, freq)] = eq
            port_res["bases"][f"{cost_tag}:{freq}"] = metrics(eq)
    full_target = port_res["bases"]["cost10:monthly"]["Vol"]  # = 基准全样本波动（full 锚点）

    # R1：full/rv20/monthly/cost10 必须复现 vt.json
    eq_r1, _ = build_port(px, b50, rv_pct, notna_cum, est_port["rv20"], START_MAIN,
                          full_target, "monthly", 0.001)
    m_r1 = metrics(eq_r1)
    r1 = {
        "ref_cagr": ref_vt["metrics"]["CAGR"], "got_cagr": m_r1["CAGR"],
        "ref_calmar": ref_vt["metrics"]["Calmar"], "got_calmar": m_r1["Calmar"],
        "ref_base_cagr": ref_base["metrics"]["CAGR"],
        "got_base_cagr": port_res["bases"]["cost10:monthly"]["CAGR"],
        "full_target_used": full_target,
        "max_abs_delta": max(abs(m_r1["CAGR"] - ref_vt["metrics"]["CAGR"]),
                             abs(m_r1["Calmar"] - ref_vt["metrics"]["Calmar"])),
        "pass": None}
    r1["pass"] = bool(r1["max_abs_delta"] < 1e-6
                      and abs(port_res["bases"]["cost10:monthly"]["CAGR"]
                              - ref_base["metrics"]["CAGR"]) < 1e-6)
    out["replication_R1"] = r1
    if not r1["pass"]:
        print(json.dumps(r1, indent=1))
        sys.exit("R1 复现失败：环境与 huanjing 归档漂移，中止（结论无效）")

    # 组合层网格
    anchor_key = None
    for cost_tag, cost in COSTS:
        base_m = port_res["bases"][f"{cost_tag}:monthly"]
        for freq in FREQS_PORT:
            for est_kind in ESTIMATORS:
                ev = est_port[est_kind]
                for tgt in TARGETS + ["full"]:
                    t_val = full_target if tgt == "full" else tgt
                    eq, e_daily = build_port(px, b50, rv_pct, notna_cum, ev,
                                             START_MAIN, t_val, freq, cost)
                    m = metrics(eq)
                    v, r = verdict_of(m, base_m)
                    key = f"{cost_tag}:{freq}:{est_kind}:{tgt}"
                    port_res["cells"][key] = {"metrics": m, "verdict": v,
                                              "r": round(r, 4)}
                    eq_alt, _ = build_port(px, b50, rv_pct, notna_cum, ev,
                                           START_ALT, t_val, freq, cost)
                    port_res["cells"][key]["alt_metrics"] = metrics(eq_alt)
                    if (cost_tag, freq, est_kind, tgt) == ("cost10", "monthly", "rv20", "full"):
                        anchor_key = key
                        port_res["anchor_detail"]["E_series"] = [
                            None if pd.isna(x) else round(float(x), 4) for x in e_daily]
                        port_res["anchor_detail"]["dates"] = [
                            str(d.date()) for d in e_daily.index]
                        port_res["anchor_detail"]["nav"] = [
                            round(float(x), 8) for x in eq]
    out["portfolio_layer"] = port_res

    # ── 单资产层 ────────────────────────────────────────────────────────
    cpx = {c: pd.read_parquet(CACHE / f"{c}.bars.parquet")["close"].astype(float)
           for c in C_ASSETS}
    sa_prep = {}
    for c, close in cpx.items():
        cl = close.loc[SA_START:].dropna()
        if len(cl) < 300:
            continue
        rets = cl.pct_change()
        sa_prep[c] = {
            "close": cl, "full_vol": float(rets.dropna().std() * np.sqrt(252.0)),
            "sig": {rule: sig_of(cl, rule) for rule in
                    ["ema20", "ema60", "sma200", "ema20>ema60"]},
            "est": {k: vol_series(rets, k) for k in ESTIMATORS}}

    sa_res: dict = {"bases": {}, "cells": {}, "anchor_detail": {}}
    # 基线：plain（无 vt），ema20 规则（C 节组合级口径）
    sa_base_eq = {}
    for cost_tag, cost in COSTS:
        eqs = {c: one_asset(d["close"], d["est"]["rv20"], d["sig"]["ema20"],
                            None, "daily", cost)
               for c, d in sa_prep.items()}
        sa_base_eq[cost_tag] = eqs
        ceq = combined(eqs)
        sa_res["bases"][cost_tag] = metrics(ceq)

    for cost_tag, cost in COSTS:
        base_m = sa_res["bases"][cost_tag]
        for freq in FREQS_SA:
            for est_kind in ESTIMATORS:
                for tgt in TARGETS + ["full"]:
                    eqs = {}
                    imp_cnt = [0, 0]
                    for c, d in sa_prep.items():
                        t_val = d["full_vol"] if tgt == "full" else tgt
                        eq = one_asset(d["close"], d["est"][est_kind], d["sig"]["ema20"],
                                       t_val, freq, cost)
                        eqs[c] = eq
                        mb = metrics(sa_base_eq[cost_tag][c])
                        mv = metrics(eq)
                        if np.isfinite(mv["Sharpe"]) and np.isfinite(mb["Sharpe"]):
                            if mv["Sharpe"] > mb["Sharpe"]:
                                imp_cnt[0] += 1
                            elif mv["Sharpe"] < mb["Sharpe"]:
                                imp_cnt[1] += 1
                    ceq = combined(eqs)
                    m = metrics(ceq)
                    v, r = verdict_of(m, base_m)
                    sa_res["cells"][f"{cost_tag}:{freq}:{est_kind}:{tgt}"] = {
                        "metrics": m, "verdict": v, "r": round(r, 4),
                        "n_assets": len(eqs),
                        "per_asset_sharpe_up_down": imp_cnt}
                    if (cost_tag, freq, est_kind, tgt) == ("cost10", "daily", "rv20", "full"):
                        sa_res["anchor_detail"]["nav"] = [
                            round(float(x), 8) for x in ceq]
                        sa_res["anchor_detail"]["per_asset_sharpe_up_down"] = imp_cnt

    # R2：四规则全量复现 C 节（own/rv20/daily/cost10）
    r2_counts = [0, 0]
    r2_combo = {}
    for rule in ["ema20", "ema60", "sma200", "ema20>ema60"]:
        eqs_p, eqs_v = {}, {}
        for c, d in sa_prep.items():
            sg = d["sig"][rule]
            if sg is None:
                continue
            ep = one_asset(d["close"], d["est"]["rv20"], sg, None, "daily", 0.001)
            ev_ = one_asset(d["close"], d["est"]["rv20"], sg, d["full_vol"], "daily", 0.001)
            if ep is None or ev_ is None:
                continue
            eqs_p[c], eqs_v[c] = ep, ev_
            mp_, mv_ = metrics(ep), metrics(ev_)
            if np.isfinite(mp_["Sharpe"]) and np.isfinite(mv_["Sharpe"]):
                if mv_["Sharpe"] > mp_["Sharpe"]:
                    r2_counts[0] += 1
                elif mv_["Sharpe"] < mp_["Sharpe"]:
                    r2_counts[1] += 1
        r2_combo[rule] = {"plain": metrics(combined(eqs_p)),
                          "vtarget": metrics(combined(eqs_v))}
    out["replication_R2"] = {
        "ref_sharpe_ema20_plain": 0.79, "ref_sharpe_ema20_vtarget": 0.84,
        "got": {k: {"plain_sharpe": round(v["plain"]["Sharpe"], 4),
                    "vtarget_sharpe": round(v["vtarget"]["Sharpe"], 4)}
                for k, v in r2_combo.items()},
        "ref_counts": [53, 47], "got_counts": r2_counts,
        "tolerance": "Sharpe ±0.02、计数 ±2（超差不中止，如实标注）"}
    out["single_asset_layer"] = sa_res
    return out


def _round_floats(obj):
    if isinstance(obj, float):
        return round(obj, 10)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v) for v in obj]
    return obj


def results_hash(res: dict) -> str:
    payload = json.dumps(_round_floats(res), sort_keys=True).encode()
    return hashlib.md5(payload).hexdigest()


# ══════════════════════════════════════ main ══════════════════════════
if __name__ == "__main__":
    res = compute_all()
    h = results_hash(res)
    print(f"HASH seed={os.environ.get('PYTHONHASHSEED', '(unset)')}: {h}")
    print(f"R1 replication pass: {res['replication_R1']['pass']}"
          f" (max_abs_delta={res['replication_R1']['max_abs_delta']:.2e},"
          f" full_target={res['replication_R1']['full_target_used']:.4f})")

    if "--dump-hash" in sys.argv:
        sys.exit(0)

    # 形状判定（按 docstring 固化判据 A–E，机械执行）
    port_cells = res["portfolio_layer"]["cells"]
    sa_cells = res["single_asset_layer"]["cells"]
    shape = {}

    def nonfals(cells, keys):
        return [cells[k]["verdict"] in ("passed", "watch") for k in keys]

    for tag, cells, cur_freq in [("port", port_cells, "monthly"), ("sa", sa_cells, "daily")]:
        tgt_keys = [f"cost10:{cur_freq}:rv20:{t}" for t in TARGETS + ["full"]]
        nf = nonfals(cells, tgt_keys)
        shape[f"A_{tag}_target_slice_nonfals"] = sum(nf)
        shape[f"A_{tag}_target_slice_verdicts"] = [cells[k]["verdict"] for k in tgt_keys]
        est_keys = [f"cost10:{cur_freq}:{e}:full" for e in ESTIMATORS]
        shape[f"B_{tag}_estimator_nonfals"] = sum(nonfals(cells, est_keys))
        frq = FREQS_PORT if tag == "port" else FREQS_SA
        frq_keys = [f"cost10:{f}:rv20:full" for f in frq]
        shape[f"C_{tag}_freq_nonfals"] = sum(nonfals(cells, frq_keys))
        best_t, best_c = None, -1e9
        for t in TARGETS + ["full"]:
            m = cells[f"cost10:{cur_freq}:rv20:{t}"]["metrics"]
            if m["Calmar"] > best_c:
                best_c, best_t = m["Calmar"], t
        shape[f"D_{tag}_best_target"] = {"target": best_t, "calmar": round(best_c, 4)}
    lad = {"0.1": 0, "0.125": 1, "0.15": 2, "0.165": 3, "0.175": 4, "0.2": 5,
           "full": 6, "0.225": 7}
    d_dist = abs(lad[str(shape["D_port_best_target"]["target"])]
                 - lad[str(shape["D_sa_best_target"]["target"])])
    shape["D_layer_consistent"] = bool(d_dist <= 1)
    shape["D_ladder_distance"] = d_dist
    shape["E_anchor_cost20_port"] = port_cells["cost20:monthly:rv20:full"]["verdict"]
    shape["E_anchor_cost20_sa"] = sa_cells["cost20:daily:rv20:full"]["verdict"]
    res["shape_verdicts"] = shape

    # 单元格总览
    for tag, cells in [("组合层", port_cells), ("单资产层", sa_cells)]:
        vs = [v["verdict"] for v in cells.values()]
        print(f"{tag}: cells={len(vs)} passed={vs.count('passed')} "
              f"watch={vs.count('watch')} falsified={vs.count('falsified')}")
    print(json.dumps({k: v for k, v in shape.items()
                      if not k.endswith("verdicts")}, ensure_ascii=False, indent=1))

    (HERE / "vt_grid_results.json").write_text(
        json.dumps(_round_floats(res), ensure_ascii=False))
    seed = os.environ.get("PYTHONHASHSEED", "0")
    (HERE / f"hash_{seed}.json").write_text(
        json.dumps({"seed": seed, "hash": h}, ensure_ascii=False))
    print(f"raw → {HERE}/vt_grid_results.json + hash_{seed}.json")
