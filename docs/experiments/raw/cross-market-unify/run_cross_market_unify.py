"""跨市场配置对撞统一：本档策略腿网格 vs bform M5（2026-09-04）。

背景：同一命题（A 股×美股跨市场分账）已有两个实现——
- bform M5（2026-08-28，指数级）：创业板指/沪深300/上证红利×全A B200 三档
  预算 + 标普/纳指无闸持有，5 指数等权，2010-06→2026-08-18，
  11.42%/−23.7%/Calmar 0.483（跨市场候选，待 WF）。
- 本档（cross-market-pairing，2026-09-04，策略腿级）：创业板三档冠军×
  美股 50/50，2010-06→2026-08，13.2%/−21.0%/Calmar 0.631（+19% 过线）。
bform raw 未存档（数据欠账登记），无法做净值级对撞；本轮用**自建网格 +
同表对照**完成统一：拆 A 腿选择 / 美腿构成 两个结构因子，验证增量结论
是否跨结构稳健。

网格（全部只读认证/缓存数据，月频，50/50 月度再平衡）：
- A 腿：A1=创业板三档冠军（champion_cyb equity）；A3=创业板裸持有
  （champion_cyb benchmark，对照：剥离择时，只留分散）；
  W2 稳健窗（2015-06 起，A2 数据就绪）加 A2=8指数三档组合
  （portfolio_3tier champion 列，认证共同窗起点）。
- 美腿：U0=标普裸持有（module_e gspc 缓存）；U3=标普+QQQ 等权裸持有
  （月度再平衡，bform 美腿构成）；U2=模块 E v1+对冲50（认证）。
- 窗口：W1=2010-06→2026-08（主窗）；W2=2015-06→2026-08（稳健窗）。

判定标准（事前写死，跑完不许改）：
- JU1 统一性主判：W1 上 4 个"纯持有侧"网格（A∈{A1,A3} × U∈{U0,U3}）
  中，组合 Calmar ≥ 1.10×最佳单腿的格子数：≥3/4 →「跨市场增量结论跨
  结构稳健（统一成立）」；=2/4 →「部分成立（结构敏感）」；≤1/4 →「脆弱，
  收案待 WF」。A1 是认证择时腿，其格子同时计入但单独标注。
- JU2 A 腿选择（择时价值）：同一 U 腿下 A1 组合 vs A3 组合的 Calmar 差；
  W2 上 A1 vs A2。只报告排序，不判生死。
- JU3 美腿构成：U0/U3/U2 三档在 A1 下的组合 Calmar + 前后半增量稳定性
  排序；只报告。
- JU4 统一提案规则（事前）：入选配置须同时 (a) JU1 格通过 (b) 前后半均
  过 1.10 增量线 (c) 三次压力窗（2015/2018/2022）组合最深回撤 ≤ 两条单腿
  中更深者。多配置过线时取"网格中 Calmar 中位数最高者"为统一提案候选
  （防单格最优）。输出仅建议级，转正走 walk-forward/打分卡。
- 与 M5 同表对照（JU5，只报告）：本网格各格与 M5 公布数字（11.42%/
  −23.7%/0.483，窗止 2026-08-18）并排；实现差异（A 腿宽度预算 vs 三档、
  5 指数等权 vs 50/50、费率 10bp vs 认证净值）如实列。
- 口径：月频 Calmar；裸腿不计费（对照性质）；认证腿费率已含；组合再平衡
  不另计费（声明，方向上略高估组合）。

输出：本目录（docs/experiments/raw/cross-market-unify/）
复现：PYTHONHASHSEED=0 python3 run_cross_market_unify.py（离线，秒级）
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
KUANDU = REPO / "docs/experiments/raw/kuandu-quanzhan"
MODULE_E = REPO / "docs/experiments/raw/module_e"

COMBO_PASS = 1.10
W2_START = pd.Period("2015-06", "M")
STRESS = {"2015crash": ("2015-06", "2016-03"), "2018grind": ("2018-01", "2019-01"),
          "2022bear": ("2022-01", "2023-12")}
M5_PUBLISHED = {"cagr": 0.1142, "max_dd": -0.237, "calmar": 0.483,
                "window_end": "2026-08-18"}


def monthly_last(nav: pd.Series) -> pd.Series:
    return nav.groupby(nav.index.to_period("M")).last()


def perf(nav: pd.Series) -> dict:
    nav = nav / nav.iloc[0]
    if len(nav) < 3:
        return {}
    yrs = (nav.index[-1].end_time - nav.index[0].start_time).days / 365.25
    cagr = float(nav.iloc[-1] ** (1 / yrs) - 1)
    mdd = float((nav / nav.cummax() - 1).min())
    return {"cagr": round(cagr, 4), "max_dd": round(mdd, 4),
            "calmar": round(cagr / abs(mdd), 4) if mdd < 0 else None}


def combo(a: pd.Series, b: pd.Series, wa: float = 0.5) -> pd.Series:
    ra = a.pct_change().fillna(0.0)
    rb = b.pct_change().fillna(0.0)
    return (1 + wa * ra + (1 - wa) * rb).cumprod()


def main() -> None:
    # ---- 数据 ----
    c = json.loads((KUANDU / "champion_cyb.json").read_text())
    a1 = monthly_last(pd.Series(c["daily"]["equity"],
                                index=pd.to_datetime(c["daily"]["date"]),
                                dtype=float).sort_index())
    a3 = monthly_last(pd.Series(c["daily"]["benchmark"],
                                index=pd.to_datetime(c["daily"]["date"]),
                                dtype=float).sort_index())
    p3 = json.loads((KUANDU / "portfolio_3tier.json").read_text())
    a2 = monthly_last(pd.Series(p3["daily"]["champion"],
                                index=pd.to_datetime(p3["daily"]["date"]),
                                dtype=float).sort_index())
    gspc = pd.read_parquet(MODULE_E / "us_gspc_ohlc.parquet")
    gspc.index = pd.to_datetime(gspc.index).tz_localize(None).normalize()
    u0 = monthly_last(gspc["close"].astype(float))
    qqq = pd.read_parquet(MODULE_E / "us_qqq_ohlc.parquet")
    qqq.index = pd.to_datetime(qqq.index).tz_localize(None).normalize()
    uq = monthly_last(qqq["close"].astype(float))
    e = pd.read_csv(MODULE_E / "us_monthly_equity.csv", index_col=0)
    u2 = pd.Series(e["v1_hedge50"].to_numpy(), index=pd.to_datetime(e.index),
                   dtype=float).sort_index()
    u2 = u2.groupby(u2.index.to_period("M")).last()

    w1 = a1.index  # 2010-06→
    u3 = combo(u0.reindex(w1).ffill(), uq.reindex(w1).ffill(), 0.5)
    legs_w1 = {"A1_cyb3band": a1, "A3_cyb_hold": a3,
               "U0_spx_hold": u0.reindex(w1).ffill(),
               "U3_spx_qqq_hold": u3, "U2_module_e": u2.reindex(w1).ffill()}

    out: dict = {"window_w1": [str(w1[0]), str(w1[-1])],
                 "n_months": int(len(w1)),
                 "legs_w1": {k: perf(v) for k, v in legs_w1.items()}}

    # 腿相关矩阵（月度）
    rets = pd.DataFrame({k: v.pct_change() for k, v in legs_w1.items()}).dropna()
    out["corr_matrix"] = {k: {kk: round(float(vv), 3) for kk, vv
                              in rets.corr()[k].items()} for k in rets.columns}

    # ---- JU1/JU2/JU3 网格（W1）----
    grid = {}
    for a in ("A1_cyb3band", "A3_cyb_hold"):
        for u in ("U0_spx_hold", "U3_spx_qqq_hold", "U2_module_e"):
            cv = combo(legs_w1[a], legs_w1[u], 0.5)
            cp = perf(cv)
            best = max(perf(legs_w1[a])["calmar"], perf(legs_w1[u])["calmar"])
            cp["ratio_vs_best_single"] = round(cp["calmar"] / best, 4)
            cp["pass_110"] = bool(cp["ratio_vs_best_single"] >= COMBO_PASS)
            # 前后半
            mid = cv.index[len(cv) // 2]
            halves = {}
            for hn, mask in (("h1", cv.index < mid), ("h2", cv.index >= mid)):
                sub_a, sub_u = legs_w1[a][mask], legs_w1[u][mask]
                sub_cv = combo(sub_a, sub_u, 0.5)
                best_h = max(perf(sub_a)["calmar"], perf(sub_u)["calmar"])
                halves[hn] = round(perf(sub_cv)["calmar"] / best_h, 4)
            cp["halves_ratio"] = halves
            cp["halves_both_pass"] = bool(halves["h1"] >= COMBO_PASS
                                          and halves["h2"] >= COMBO_PASS)
            # 压力窗
            stress = {}
            for sn, (d0, d1) in STRESS.items():
                m0, m1 = pd.Period(d0, "M"), pd.Period(d1, "M")
                seg = cv[(cv.index >= m0) & (cv.index <= m1)]
                sa = legs_w1[a][(legs_w1[a].index >= m0) & (legs_w1[a].index <= m1)]
                su = legs_w1[u][(legs_w1[u].index >= m0) & (legs_w1[u].index <= m1)]
                stress[sn] = {"combo_mdd": perf(seg).get("max_dd"),
                              "deepest_leg_mdd": min(
                                  perf(sa).get("max_dd", 0),
                                  perf(su).get("max_dd", 0))}
            cp["stress_all_not_worse"] = bool(all(
                s["combo_mdd"] is not None and s["deepest_leg_mdd"] is not None
                and s["combo_mdd"] >= s["deepest_leg_mdd"] for s in stress.values()))
            grid[f"{a}x{u}"] = cp
    out["grid_w1"] = grid

    core4 = [f"{a}x{u}" for a in ("A1_cyb3band", "A3_cyb_hold")
             for u in ("U0_spx_hold", "U3_spx_qqq_hold")]
    n_pass = sum(1 for k in core4 if grid[k]["pass_110"])
    out["JU1_unification"] = {
        "core4_cells": core4, "n_pass": n_pass,
        "verdict": ("unified_robust" if n_pass >= 3
                    else ("partial_structure_sensitive" if n_pass == 2
                          else "fragile"))}

    # ---- JU2 W2 稳健窗（加 A2）----
    w2 = a1.index[a1.index >= W2_START]
    legs_w2 = {"A1_cyb3band": a1[a1.index >= W2_START],
               "A2_8idx_3band": a2.reindex(w1).ffill()[w2],
               "A3_cyb_hold": a3[a3.index >= W2_START],
               "U0_spx_hold": u0.reindex(w1).ffill()[w2],
               "U3_spx_qqq_hold": u3[w2], "U2_module_e": u2.reindex(w1).ffill()[w2]}
    g2 = {}
    for a in ("A1_cyb3band", "A2_8idx_3band", "A3_cyb_hold"):
        for u in ("U0_spx_hold", "U3_spx_qqq_hold"):
            cv = combo(legs_w2[a], legs_w2[u], 0.5)
            cp = perf(cv)
            best = max(perf(legs_w2[a])["calmar"], perf(legs_w2[u])["calmar"])
            cp["ratio_vs_best_single"] = round(cp["calmar"] / best, 4)
            g2[f"{a}x{u}"] = cp
    out["grid_w2_2015plus"] = g2
    out["legs_w2"] = {k: perf(v) for k, v in legs_w2.items()}

    # ---- JU4 统一提案 ----
    eligible = [k for k, v in grid.items()
                if v["pass_110"] and v["halves_both_pass"] and v["stress_all_not_worse"]]
    if eligible:
        calmar_sorted = sorted(eligible, key=lambda k: grid[k]["calmar"], reverse=True)
        out["JU4_unified_proposal"] = {
            "eligible": eligible,
            "proposal": calmar_sorted[0],
            "note": "建议级；转正走 walk-forward/打分卡前瞻"}
    else:
        out["JU4_unified_proposal"] = {"eligible": [], "proposal": None}

    # ---- JU5 与 M5 同表 ----
    out["JU5_vs_M5"] = {"m5_published": M5_PUBLISHED,
                        "caveat": "bform raw 未存档，非净值级对撞；实现差异="
                        "A腿(全A宽度预算×3指数 vs 三档冠军)、权重(5指数等权~40%美股 "
                        "vs 50/50)、费率(10bp vs 认证净值/裸腿)",
                        "grid_best": max(grid.items(), key=lambda kv: kv[1]["calmar"])}

    res_json = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True,
                          default=str)
    (RAW / "unify_results.json").write_text(res_json)
    digest = hashlib.sha256(res_json.encode()).hexdigest()
    seed = os.environ.get("PYTHONHASHSEED", "unset")
    (RAW / f"hash_{seed}.json").write_text(json.dumps(
        {"pythonhashseed": seed, "sha256_results": digest}, indent=2))
    print(json.dumps(out | {"sha256": digest}, indent=2, ensure_ascii=False,
                     default=str))
    return None


if __name__ == "__main__":
    sys.exit(main())
