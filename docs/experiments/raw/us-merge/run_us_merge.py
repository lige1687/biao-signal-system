"""美股 ETF 防守版 × 模块 E 买入侧 · 分账合并 v0（2026-09-03）。

任务来源：lei-ARCHIVE-2026-09-01 下一步 3——"美股 ETF 池×模块 E 买入侧合并：
买入侧（模块 E）与防守侧（31 轮防守版）从未在同一账户形态里合测。预期：
美股腿形成「极值买入+宽度防守」完整形态；风险：双重参数叠加的多重比较税。"

设计（合体组范式：两条独立运作的腿 50/50 分账，月度再平衡；不做交互式
资金流——那是语义二的事，本轮不碰）：
- 腿 1 = 美股指数防守版（SPY 40/80·vol0.15·MA200 闸，40 年认证产品，
  回撤 −15~-23% 量级，保费 4-8pp/年）：raw/kuandu-quanzhan/us_defense.json
  ^GSPC daily.equity（1986-01-02 起，日频，含其引擎费率）。
- 腿 2 = 模块 E v1+对冲50%（B20&B50≤15 极值买入 + 顶部区对冲，module-e
  认证 J1-J3 通过）：raw/module_e/us_monthly_equity.csv v1_hedge50 列
  （1986-10-31 起，月频，含 5bp 费）。
- 共同窗：1986-10-31→2026-08（月频对齐；腿 1 日频取月末值）。

判定标准（事前写死，跑完不许改）：
- JCorr（正交性基础）：两腿月收益 Pearson |ρ| ≤ 0.30 →「低相关基础成立」；
  0.30~0.60 → 中度（组合价值打折解读）；>0.60 → 高相关（合测先验弱）。
- JCombo（合并增量·主判）：组合(50/50 月度再平衡) Calmar（年化/|最大回撤|）
  ≥ 1.10 × max(两腿单腿 Calmar) →「合测有增量」；≥ max（1.00×）→「持平
  登记」；< max →「无增量（判负）」。
- JDefense（防守属性保留）：组合 MDD ≤ 腿 1 单腿 MDD + 3pp → 通过；
  否则「E 腿摧毁防守属性」标注（与 JCombo 独立报告）。
- 分段（只报告）：前半/后半；OOS=2024-09 及以后月度。
- 敏感性：60/40 与 40/60 权重、不再平衡（买入持有各自一半）。
- 组合再平衡不另计费（月频、金额小，声明；两腿自身费率已含于净值）。

口径：月频 Calmar 用月度净值计算（回撤略浅于日频，两腿同源公平）；
腿 1 月末值由日频净值取月末最后可得日。

输出：本目录（docs/experiments/raw/us-merge/）
复现：PYTHONHASHSEED=0 python3 run_us_merge.py（离线，秒级）
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
DEFENSE = REPO / "docs/experiments/raw/kuandu-quanzhan/us_defense.json"
E_CSV = REPO / "docs/experiments/raw/module_e/us_monthly_equity.csv"

CORR_LINE = 0.30
CORR_HIGH = 0.60
COMBO_PASS = 1.10
COMBO_FLAT = 1.00
DEFENSE_DD_TOL = 0.03
OOS_CUT = pd.Timestamp("2024-09-01")


def load_legs() -> tuple[pd.Series, pd.Series]:
    d = json.loads(DEFENSE.read_text())
    g = d["instruments"]["^GSPC"]["daily"]
    leg1 = pd.Series(g["equity"], index=pd.to_datetime(g["date"]),
                     dtype=float).sort_index()
    e = pd.read_csv(E_CSV, index_col=0)
    leg2 = pd.Series(e["v1_hedge50"].to_numpy(), index=pd.to_datetime(e.index),
                     dtype=float).sort_index()
    # 月频对齐：腿 1 取月末最后可得日
    leg1m = leg1.groupby(leg1.index.to_period("M")).last()
    leg2m = leg2.groupby(leg2.index.to_period("M")).last()
    common = leg1m.index.intersection(leg2m.index)
    return leg1m[common].copy(), leg2m[common].copy()


def perf(nav: pd.Series) -> dict:
    nav = nav / nav.iloc[0]
    ret = nav.pct_change().dropna()
    yrs = (nav.index[-1].end_time - nav.index[0].start_time).days / 365.25
    cagr = float(nav.iloc[-1] ** (1 / yrs) - 1)
    mdd = float((nav / nav.cummax() - 1).min())
    return {"cagr": round(cagr, 4), "max_dd": round(mdd, 4),
            "calmar": round(cagr / abs(mdd), 4) if mdd < 0 else None}


def combo(leg1: pd.Series, leg2: pd.Series, w1: float,
          rebalance: bool = True) -> pd.Series:
    """分账组合：rebalance=True 每月恢复 w1/w2；否则买入持有各半。"""
    r1 = leg1.pct_change().fillna(0.0)
    r2 = leg2.pct_change().fillna(0.0)
    if rebalance:
        rc = w1 * r1 + (1 - w1) * r2
        return (1 + rc).cumprod()
    a, b = w1, 1 - w1
    nav = a * (leg1 / leg1.iloc[0]) + b * (leg2 / leg2.iloc[0])
    return nav


def main() -> None:
    leg1, leg2 = load_legs()
    r1 = leg1.pct_change().dropna()
    r2 = leg2.pct_change().dropna()
    corr_p = float(r1.corr(r2))
    corr_s = float(r1.corr(r2, method="spearman"))

    p1, p2 = perf(leg1), perf(leg2)
    main_combo = combo(leg1, leg2, 0.5)
    pc = perf(main_combo)
    verdicts: dict = {}
    verdicts["JCorr"] = {
        "pearson": round(corr_p, 4), "spearman": round(corr_s, 4),
        "verdict": ("low_corr_base" if abs(corr_p) <= CORR_LINE
                    else ("mid" if abs(corr_p) <= CORR_HIGH else "high_corr"))}
    best_single = max(p1["calmar"], p2["calmar"])
    ratio = pc["calmar"] / best_single if best_single else None
    verdicts["JCombo"] = {
        "ratio_vs_best_single": round(ratio, 4),
        "verdict": ("increment" if ratio >= COMBO_PASS
                    else ("flat" if ratio >= COMBO_FLAT else "no_increment"))}
    verdicts["JDefense"] = {
        "combo_mdd": pc["max_dd"], "leg1_mdd": p1["max_dd"],
        "verdict": ("kept" if pc["max_dd"] >= p1["max_dd"] - DEFENSE_DD_TOL
                    else "defense_destroyed")}

    # 分段（只报告）
    mid = leg1.index[len(leg1) // 2]
    seg = {}
    for name, sl in (("first_half", leg1.index < mid),
                     ("second_half", leg1.index >= mid),
                     ("oos_2024_09", leg1.index >= OOS_CUT.to_period("M"))):
        if sl.sum() < 6:
            continue
        seg[name] = {"leg1": perf(leg1[sl]), "leg2": perf(leg2[sl]),
                     "combo50": perf(combo(leg1[sl], leg2[sl], 0.5))}
    sens = {}
    for w1 in (0.6, 0.4):
        sens[f"w{int(w1*100)}"] = perf(combo(leg1, leg2, w1))
    sens["no_rebalance_5050"] = perf(combo(leg1, leg2, 0.5, rebalance=False))
    # 与 100% 防守腿对照（自然基准：防守腿+现金拖底的替代）
    sens["leg1_only_for_reference"] = p1

    out = {
        "config": dict(CORR_LINE=CORR_LINE, CORR_HIGH=CORR_HIGH,
                       COMBO_PASS=COMBO_PASS, COMBO_FLAT=COMBO_FLAT,
                       DEFENSE_DD_TOL=DEFENSE_DD_TOL, OOS_CUT=str(OOS_CUT.date())),
        "window": [str(leg1.index[0]), str(leg1.index[-1])],
        "n_months": int(len(leg1)),
        "leg1_defense": p1, "leg2_module_e_v1h50": p2,
        "combo_5050": pc,
        "verdicts": verdicts, "segments": seg, "sensitivity": sens,
    }
    res_json = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True,
                          default=str)
    (RAW / "us_merge_results.json").write_text(res_json)
    pd.DataFrame({"leg1_defense": leg1, "leg2_module_e": leg2,
                  "combo_5050": main_combo.values},
                 index=leg1.index.astype(str)).to_csv(
        RAW / "us_merge_monthly_nav.csv")
    digest = hashlib.sha256(res_json.encode()).hexdigest()
    seed = os.environ.get("PYTHONHASHSEED", "unset")
    (RAW / f"hash_{seed}.json").write_text(json.dumps(
        {"pythonhashseed": seed, "sha256_results": digest}, indent=2))
    print(json.dumps(out | {"sha256": digest}, indent=2, ensure_ascii=False))
    return None


if __name__ == "__main__":
    sys.exit(main())
