"""跨市场配对 · A 股认证腿 × 美股三种形态腿的分账对照（2026-09-04）。

问题定位：bform-global（M5，2026-08-28）已在指数等权层面确立"美股=持有
资产，不是择时资产"（美腿任何闸均毁损：G5/M5D 双证伪）。但**认证策略腿
层面**未测：与 A 股认证核心（创业板三档冠军）配对时，美股资金的正确形态
是裸持有（U0）、防守版保险（U1，40 年认证但保费 4-8pp）还是模块 E 极值
入场（U2，J1 认证、低频配置）？us-merge（2026-09-03）已证 U1×U2 同市场
合并判负（相关 0.57），本实验把配对换成跨市场。

数据（全部只读复用认证产物，月频对齐，共同窗 2010-06→2026-08，195 个月）：
- A1 = 创业板三档冠军（raw/kuandu-quanzhan/champion_cyb.json daily.equity）
- U0 = 标普裸持有（raw/module_e/us_gspc_ohlc.parquet close 月频；不计费，
  对照基准性质，声明）
- U1 = 美股防守版（raw/kuandu-quanzhan/us_defense.json ^GSPC daily.equity，
  引擎费率已含）
- U2 = 模块 E v1+对冲50（raw/module_e/us_monthly_equity.csv v1_hedge50，
  5bp 已含）

判定标准（事前写死，跑完不许改）：
- JX1 相关（每对月收益 Pearson）：≤0.30 低（合体组先例量级）/ 0.30~0.60
  中 / >0.60 高。
- JX2 主判（美股腿形态选择）：三个 50/50 月度再平衡组合（A1×U0 / A1×U1 /
  A1×U2）中，若 max(Calmar(A1×U1), Calmar(A1×U2)) > Calmar(A1×U0)
  →「认证美腿形态在 A 股配对下优于裸持有」；否则「美股=持有资产」在策略
  腿层面再获确认（bform 结论升级）。同时报告各组合 vs 各自最佳单腿的
  比值（1.10 增量 / 1.00 持平 线，沿 us-merge 口径）。
- JX3 机械分散对照（防"低相关=免费午餐"假象）：对 U0 月收益做 36 个月
  循环块自助重采样（200 次，rng=default_rng(20260904)）构造伪美股腿
  （保留收益分布、破坏与 A1 的危机同步），伪组合 Calmar 分布的中位记为
  "消除同步后的假想基线"；真实 A1×U0 Calmar ≥ 伪中位 →「结构性错峰
  （配置价值为真）」；< 伪中位 →「表面增量主要是机械分散，真实危机同步
  在侵蚀它」。伪分布 p90 一并报告。
- JX4 配置面（report-only）：胜出形态下 US 权重 w∈{0,.2,.4,.5,.6,.8,1}，
  Calmar/CAGR/MDD 表 + 前后半稳定性；预登记 actionable 线：存在
  w∈[0.2,0.6] 使 Calmar ≥ 1.10×Calmar(w=0) →「美股配置对 A 股核心有
  性价比增量（建议级）」。
- JX5 压力窗（只报告）：2015 股灾 / 2018 阴跌 / 2022-23 段各腿与 50/50。
- 口径：月频 Calmar（回撤略浅于日频，全腿同源公平）；组合月度再平衡
  不另计费（月频小额，声明）。

输出：本目录（docs/experiments/raw/cross-market-pairing/）
复现：PYTHONHASHSEED=0 python3 run_cross_market_pairing.py（离线，秒级）
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
CHAMP = REPO / "docs/experiments/raw/kuandu-quanzhan/champion_cyb.json"
DEFENSE = REPO / "docs/experiments/raw/kuandu-quanzhan/us_defense.json"
E_CSV = REPO / "docs/experiments/raw/module_e/us_monthly_equity.csv"
GSPC = REPO / "docs/experiments/raw/module_e/us_gspc_ohlc.parquet"

CORR_LOW, CORR_HIGH = 0.30, 0.60
COMBO_PASS, COMBO_FLAT = 1.10, 1.00
BOOT_N, BOOT_BLOCK = 200, 36
BOOT_SEED = 20260904
W_GRID = (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)
W_ACTION_LO, W_ACTION_HI, W_ACTION_LINE = 0.2, 0.6, 1.10
STRESS = {"2015crash": ("2015-06", "2016-03"), "2018grind": ("2018-01", "2019-01"),
          "2022bear": ("2022-01", "2023-12")}


def monthly_last(nav: pd.Series) -> pd.Series:
    return nav.groupby(nav.index.to_period("M")).last()


def perf(nav: pd.Series) -> dict:
    nav = nav / nav.iloc[0]
    yrs = (nav.index[-1].end_time - nav.index[0].start_time).days / 365.25
    cagr = float(nav.iloc[-1] ** (1 / yrs) - 1)
    mdd = float((nav / nav.cummax() - 1).min())
    return {"cagr": round(cagr, 4), "max_dd": round(mdd, 4),
            "calmar": round(cagr / abs(mdd), 4) if mdd < 0 else None}


def combo(a: pd.Series, b: pd.Series, wa: float) -> pd.Series:
    """月度再平衡分账：组合月收益 = wa·r_a + (1−wa)·r_b。"""
    ra = a.pct_change().fillna(0.0)
    rb = b.pct_change().fillna(0.0)
    return (1 + wa * ra + (1 - wa) * rb).cumprod()


def main() -> None:
    # ---- 数据装配（月频）----
    c = json.loads(CHAMP.read_text())
    a1 = monthly_last(pd.Series(c["daily"]["equity"],
                                index=pd.to_datetime(c["daily"]["date"]),
                                dtype=float).sort_index())
    d = json.loads(DEFENSE.read_text())
    g = d["instruments"]["^GSPC"]["daily"]
    u1 = monthly_last(pd.Series(g["equity"], index=pd.to_datetime(g["date"]),
                                dtype=float).sort_index())
    px = pd.read_parquet(GSPC)
    px.index = pd.to_datetime(px.index).tz_localize(None).normalize()
    u0 = monthly_last(px["close"].astype(float))
    e = pd.read_csv(E_CSV, index_col=0)
    u2 = pd.Series(e["v1_hedge50"].to_numpy(), index=pd.to_datetime(e.index),
                   dtype=float).sort_index()
    u2 = u2.groupby(u2.index.to_period("M")).last()  # 对齐 Period 索引
    legs = {"A1_cyb_champion": a1, "U0_spx_hold": u0,
            "U1_us_defense": u1, "U2_module_e": u2}
    idx = a1.index
    for k in legs:
        legs[k] = legs[k].reindex(idx).ffill()
    # 共同窗从 A1 起
    legs = {k: v[v.index >= idx[0]] for k, v in legs.items()}

    out: dict = {"window": [str(idx[0]), str(legs["A1_cyb_champion"].index[-1])],
                 "n_months": int(len(idx)),
                 "legs": {k: perf(v) for k, v in legs.items()}}

    # ---- JX1 相关 ----
    ra = legs["A1_cyb_champion"].pct_change().dropna()
    jx1 = {}
    for k in ("U0_spx_hold", "U1_us_defense", "U2_module_e"):
        jx1[k] = {"pearson": round(float(ra.corr(legs[k].pct_change().dropna())), 4)}
    for k in jx1:
        p = jx1[k]["pearson"]
        jx1[k]["band"] = "low" if abs(p) <= CORR_LOW else (
            "mid" if abs(p) <= CORR_HIGH else "high")
    out["JX1_corr"] = jx1

    # ---- JX2 主判 ----
    pairs = {"A1xU0": ("A1_cyb_champion", "U0_spx_hold"),
             "A1xU1": ("A1_cyb_champion", "U1_us_defense"),
             "A1xU2": ("A1_cyb_champion", "U2_module_e")}
    combos = {}
    for tag, (ka, kb) in pairs.items():
        cv = combo(legs[ka], legs[kb], 0.5)
        combos[tag] = cv
        best_single = max(perf(legs[ka])["calmar"], perf(legs[kb])["calmar"])
        cp = perf(cv)
        cp["ratio_vs_best_single"] = round(cp["calmar"] / best_single, 4)
        cp["verdict_vs_single"] = ("increment" if cp["ratio_vs_best_single"] >= COMBO_PASS
                                   else ("flat" if cp["ratio_vs_best_single"] >= COMBO_FLAT
                                         else "no_increment"))
        combos[tag] = cv  # keep series for later
        out.setdefault("JX2_pairs", {})[tag] = {
            "combo": cp, "legA": perf(legs[ka]), "legB": perf(legs[kb])}
    c0 = out["JX2_pairs"]["A1xU0"]["combo"]["calmar"]
    c1 = out["JX2_pairs"]["A1xU1"]["combo"]["calmar"]
    c2 = out["JX2_pairs"]["A1xU2"]["combo"]["calmar"]
    out["JX2_pairs"]["main_verdict"] = {
        "calmar_A1xU0": c0, "calmar_A1xU1": c1, "calmar_A1xU2": c2,
        "verdict": ("certified_leg_beats_hold" if max(c1, c2) > c0
                    else "hold_confirmed_at_strategy_level")}

    # ---- JX3 机械分散对照（U0 伪腿块自助）----
    rng = np.random.default_rng(BOOT_SEED)
    r_u0 = legs["U0_spx_hold"].pct_change().dropna().to_numpy()
    n = len(r_u0)
    ra_full = legs["A1_cyb_champion"].pct_change().fillna(0.0).to_numpy()
    pseudo = []
    for _ in range(BOOT_N):
        blocks = []
        while sum(len(b) for b in blocks) < n:
            s = rng.integers(0, n)
            blocks.append(np.roll(r_u0, -s)[:BOOT_BLOCK])
        pseudo_r = np.concatenate(blocks)[:n]
        rc = 0.5 * ra_full[1:] + 0.5 * pseudo_r  # 对齐长度（各去首月）
        nav = np.concatenate(([1.0], np.cumprod(1 + rc)))
        mdd = float((nav / np.maximum.accumulate(nav) - 1).min())
        yrs = n / 12.0
        cagr = nav[-1] ** (1 / yrs) - 1
        pseudo.append(cagr / abs(mdd))
    pseudo = np.array(pseudo)
    real_c = out["JX2_pairs"]["A1xU0"]["combo"]["calmar"]
    out["JX3_bootstrap"] = {
        "real_A1xU0_calmar": real_c,
        "pseudo_median": round(float(np.median(pseudo)), 4),
        "pseudo_p90": round(float(np.percentile(pseudo, 90)), 4),
        "verdict": ("structural_decoupling" if real_c >= float(np.median(pseudo))
                    else "mechanical_diversification")}

    # ---- JX4 配置面（report-only，用 JX2 胜者或默认 U0）----
    best_us = max(("U0_spx_hold", "U1_us_defense", "U2_module_e"),
                  key=lambda k: out["JX2_pairs"][
                      {"U0_spx_hold": "A1xU0", "U1_us_defense": "A1xU1",
                       "U2_module_e": "A1xU2"}[k]]["combo"]["calmar"])
    surf = {}
    for w in W_GRID:
        cv = combo(legs["A1_cyb_champion"], legs[best_us], 1 - w)  # w=US 权重
        surf[f"us{int(w*100)}"] = perf(cv)
    calmar0 = surf["us0"]["calmar"]
    action_ok = any(W_ACTION_LO <= w <= W_ACTION_HI
                    and surf[f"us{int(w*100)}"]["calmar"] >= W_ACTION_LINE * calmar0
                    for w in W_GRID)
    # 前后半稳定性（docstring 承诺）：各自半窗重算权重面
    mid = legs["A1_cyb_champion"].index[len(idx) // 2]
    halves = {}
    for hname, mask in (("first_half", legs["A1_cyb_champion"].index < mid),
                        ("second_half", legs["A1_cyb_champion"].index >= mid)):
        hs = {}
        for w in W_GRID:
            cv = combo(legs["A1_cyb_champion"][mask], legs[best_us][mask], 1 - w)
            hs[f"us{int(w*100)}"] = perf(cv)
        halves[hname] = hs
    out["JX4_weight_surface"] = {"us_leg": best_us, "surface": surf,
                                 "halves": halves,
                                 "actionable_verdict": (
                                     "us_allocation_increment" if action_ok
                                     else "no_increment_or_preference")}

    # ---- JX5 压力窗（只报告）----
    stress = {}
    for name, (d0, d1) in STRESS.items():
        m0, m1 = pd.Period(d0, "M"), pd.Period(d1, "M")
        seg = {k: perf(v[(v.index >= m0) & (v.index <= m1)])
               for k, v in legs.items()}
        seg["A1xU0_5050"] = perf(
            combos["A1xU0"][(combos["A1xU0"].index >= m0)
                            & (combos["A1xU0"].index <= m1)])
        stress[name] = seg
    out["JX5_stress"] = stress

    # ---- 落盘 ----
    res_json = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True,
                          default=str)
    (RAW / "cross_market_results.json").write_text(res_json)
    pd.DataFrame({k: v.values for k, v in
                  [("A1", legs["A1_cyb_champion"]), ("U0", legs["U0_spx_hold"]),
                   ("U1", legs["U1_us_defense"]), ("U2", legs["U2_module_e"]),
                   ("A1xU0", combos["A1xU0"]), ("A1xU1", combos["A1xU1"]),
                   ("A1xU2", combos["A1xU2"])]},
                 index=legs["A1_cyb_champion"].index.astype(str)).to_csv(
        RAW / "cross_market_monthly_nav.csv")
    digest = hashlib.sha256(res_json.encode()).hexdigest()
    seed = os.environ.get("PYTHONHASHSEED", "unset")
    (RAW / f"hash_{seed}.json").write_text(json.dumps(
        {"pythonhashseed": seed, "sha256_results": digest}, indent=2))
    print(json.dumps(out | {"sha256": digest}, indent=2, ensure_ascii=False,
                     default=str))
    return None


if __name__ == "__main__":
    sys.exit(main())
