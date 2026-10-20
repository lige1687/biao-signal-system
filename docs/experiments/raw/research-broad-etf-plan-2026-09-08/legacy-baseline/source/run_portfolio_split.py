#!/usr/bin/env python3
"""组合层适配性分账·预注册实验（2026-08-28，跑前写死，跑后不改）。

背景：本日三连负（siphon-detector / rs26-detector / knife-timestop 报告）证明
宽度层补丁路线穷尽；结构牛缺口与阴跌防守的答案都在宽度层之外——趋势型标的
不设宽度闸 + 执行层止损。本实验在组合层直接检验该架构主张。

【预注册协议】
标的池（9 只，来自交接书适配地图与冠军战绩单，排除名单不入选）：
- 缓周期腿（宽度闸）：sh000300 沪深300、sh000016 上证50、sz399997 中证白酒、
  sz399393 国证地产。
- 趋势腿（无闸+Donchian）：399006 创业板指、399975 证券公司、sz399976 新能车、
  sz399989 中证医疗、sz399395 国证有色。
公共窗口：2015-06-16（白酒上市日）→2026-08-18（B200 快照末日）。

覆盖规则（冻结）：
- 宽度闸 = 冠军三档（B200<43.3→1.0，<56.7→0.5，≥56.7→0），周频信号
  （周内最后交易日收盘）→ 次一交易日收盘生效。
- Donchian 60 日：收盘 < 前 60 日收盘最低 → 次日空仓；收盘 > 前 60 日收盘
  最高 → 次日再入。窗口起点状态=在场（指标用全历史计算，无暖机问题）。
- 组合机械（三臂完全相同）：等权目标 1/9 × 覆盖系数；5% 最小调仓阈值
  （|目标−实际|≥5pp 才调该腿）；单边成本 10bp 按换手计；现金零收益。

臂：
- A 等权持有（覆盖全 1）
- B 等权 + 全部宽度闸
- C 等权 + 适配分账（缓周期腿宽度闸 × 档位；趋势腿 Donchian）

判定（冻结，主窗 2015-06-16→2026-08-18）：
- C1（对持有）：C 最大回撤较 A 改善 ≥10pp 且 年化 ≥ A − 1.0pp。
- C2（对全闸）：C 年化 ≥ B 年化 + 1.0pp 且 Calmar(C) ≥ Calmar(B) − 0.02。
- C3（留一稳健）：去掉任一标的，C1∧C2 判定布尔不变 ≥7/9。
- C4（分窗）：前半窗(→2020-12-31)与后半窗(2021-01-01→) C 的 maxDD
  均不深于 B（回撤优势非单窗驱动）。
- **总 PASS = C1∧C2∧C3∧C4。** 附分腿归因与分年收益（报告项，不设判定）。

输出：docs/experiments/raw/portfolio_split/portfolio_split_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_portfolio_split.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw/portfolio_split"
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

from run_siphon_detector import COST, MID, HIGH, tier_weight, weekly_last  # noqa: E402

# ── 冻结配置 ──
WIN_START, WIN_END = "2015-06-16", "2026-08-18"
GATED = {
    "沪深300": "portfolio_split/sh000300_close.parquet",
    "上证50": "portfolio_split/sh000016_close.parquet",
    "中证白酒": "portfolio_split/sz399997_close.parquet",
    "国证地产": "portfolio_split/sz399393_close.parquet",
}
TREND = {
    "创业板指": "siphon_detector/cyb_399006_close.parquet",
    "证券公司": "siphon_detector/sec_399975_close.parquet",
    "新能车": "portfolio_split/sz399976_close.parquet",
    "中证医疗": "portfolio_split/sz399989_close.parquet",
    "国证有色": "portfolio_split/sz399395_close.parquet",
}
DC_WIN, BAND = 60, 0.05
C1_DD, C1_ANN, C2_ANN, C2_CAL, C3_TH = 10.0, 1.0, 1.0, 0.02, 7
SPLIT_YEAR = "2021-01-01"


def load_breadth() -> pd.Series:
    with open(SRC / "breadth_overlay/a_share_breadth_33y_snapshot.json") as f:
        rows = json.load(f)
    s = pd.Series({pd.Timestamp(r["date"]): r["ma200_pct"]
                   for r in rows if r.get("ma200_pct") is not None}).astype(float)
    return s.sort_index()


def tier_daily(b200_daily: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """周频三档 → 次一交易日生效的日频档位序列。"""
    bw, bsig = weekly_last(b200_daily)
    tiers = bw.map(tier_weight)
    out = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(bsig.values))
    for p, w in zip(pos, tiers.values):
        if p + 1 < len(dates):
            out.iloc[p + 1] = w
    return out.ffill().fillna(0.0)


def donchian_daily(price_full: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """Donchian 60 日止损/再入，次日生效；起点在场。"""
    lo = price_full.rolling(DC_WIN).min().shift(1)
    hi = price_full.rolling(DC_WIN).max().shift(1)
    p = price_full.reindex(dates)
    lo, hi = lo.reindex(dates), hi.reindex(dates)
    out = pd.Series(1.0, index=dates)
    state = True
    for i in range(len(dates)):
        out.iloc[i] = 1.0 if state else 0.0
        v, l, h = p.iloc[i], lo.iloc[i], hi.iloc[i]
        if v != v:
            continue
        if state and l == l and v < l:
            state = False
        elif not state and h == h and v > h:
            state = True
    return out


def simulate(prices: pd.DataFrame, exposures: pd.DataFrame) -> dict:
    """等权×覆盖 + 5% 调仓带 + 10bp 成本的组合模拟。"""
    rets = prices.pct_change().fillna(0.0)
    names = list(prices.columns)
    n = len(names)
    actual = np.zeros(n)
    eq, cost_ser = [], []
    port = 1.0
    for i in range(len(prices)):
        r = rets.iloc[i].values
        if i > 0:
            growth = port * (1.0 + float(actual @ r))
            port = growth
        target = exposures.iloc[i].values / n
        trade = np.abs(target - actual) >= BAND
        new_actual = np.where(trade, target, actual)
        turnover = float(np.abs(new_actual - actual).sum())
        port *= 1.0 - COST * turnover
        actual = new_actual
        eq.append(port)
        cost_ser.append(COST * turnover)
    eq = pd.Series(eq, index=prices.index)
    return {"eq": eq, "cost_drag_total": float(np.sum(cost_ser))}


def metrics(eq: pd.Series, rf0: bool = True) -> dict:
    n = len(eq)
    ann = float(eq.iloc[-1] ** (252.0 / n) - 1.0) * 100
    dd = float((eq / eq.cummax() - 1.0).min()) * 100
    r = eq.pct_change().dropna()
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan
    return {"ann_pct": round(ann, 2), "maxdd_pct": round(dd, 2),
            "calmar": round(ann / abs(dd), 3) if dd < 0 else None,
            "sharpe": round(sharpe, 2)}


def build_universe(b200: pd.Series, names: list[tuple[str, str]]) -> tuple:
    frames = {}
    for name, rel in names:
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    prices = pd.DataFrame(frames).dropna(how="all")
    prices = prices[(prices.index >= pd.Timestamp(WIN_START))
                    & (prices.index <= pd.Timestamp(WIN_END))].dropna(axis=0, how="any")
    dates = prices.index
    tier = tier_daily(b200, dates)
    split, allgate = {}, {}
    for name, _ in names:
        dc = donchian_daily(frames[name], dates) if name in TREND else None
        split[name] = tier if name in GATED else dc
        allgate[name] = tier
    return prices, pd.DataFrame(split).reindex(dates), pd.DataFrame(allgate).reindex(dates)


def arms_for(members: list[tuple[str, str]], b200: pd.Series) -> dict:
    prices, expo_split, expo_allgate = build_universe(b200, members)
    ones = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    return {
        "A_等权持有": simulate(prices, ones),
        "B_全宽度闸": simulate(prices, expo_allgate),
        "C_适配分账": simulate(prices, expo_split),
    }, prices


def main() -> None:
    b200 = load_breadth()
    members = [(k, v) for k, v in {**GATED, **TREND}.items()]
    out, prices = arms_for(members, b200)
    arms = {k: metrics(v["eq"]) for k, v in out.items()}

    a, b, c = arms["A_等权持有"], arms["B_全宽度闸"], arms["C_适配分账"]
    c1 = (a["maxdd_pct"] - c["maxdd_pct"] >= C1_DD) and (c["ann_pct"] >= a["ann_pct"] - C1_ANN)
    c2 = (c["ann_pct"] >= b["ann_pct"] + C2_ANN) and (c["calmar"] >= b["calmar"] - C2_CAL)

    # C3 留一
    loo_ok = 0
    loo_detail = {}
    for drop in dict(members):
        sub = [m for m in members if m[0] != drop]
        o2, _ = arms_for(sub, b200)
        m2 = {k: metrics(v["eq"]) for k, v in o2.items()}
        a2, b2, c2m = m2["A_等权持有"], m2["B_全宽度闸"], m2["C_适配分账"]
        j1 = (a2["maxdd_pct"] - c2m["maxdd_pct"] >= C1_DD) and (c2m["ann_pct"] >= a2["ann_pct"] - C1_ANN)
        j2 = (c2m["ann_pct"] >= b2["ann_pct"] + C2_ANN) and (c2m["calmar"] >= b2["calmar"] - C2_CAL)
        ok = (j1 == c1) and (j2 == c2)
        loo_ok += int(ok)
        loo_detail[drop] = {"C1": bool(j1), "C2": bool(j2), "kept": bool(ok)}

    # C4 分窗
    eqC, eqB = out["C_适配分账"]["eq"], out["B_全宽度闸"]["eq"]
    half1 = prices.index < pd.Timestamp(SPLIT_YEAR)
    ddC1 = float((eqC[half1] / eqC[half1].cummax() - 1).min()) * 100
    ddB1 = float((eqB[half1] / eqB[half1].cummax() - 1).min()) * 100
    ddC2_ = float((eqC[~half1] / eqC[~half1].cummax() - 1).min()) * 100
    ddB2_ = float((eqB[~half1] / eqB[~half1].cummax() - 1).min()) * 100
    c4 = (ddC1 >= ddB1) and (ddC2_ >= ddB2_)

    verdict = {
        "C1_vs_hold": {"dd_improve": round(a["maxdd_pct"] - c["maxdd_pct"], 2),
                       "ann_gap": round(c["ann_pct"] - a["ann_pct"], 2), "pass": bool(c1)},
        "C2_vs_allgate": {"ann_gap": round(c["ann_pct"] - b["ann_pct"], 2),
                          "calmar_C": c["calmar"], "calmar_B": b["calmar"], "pass": bool(c2)},
        "C3_loo": {"kept": loo_ok, "pass": bool(loo_ok >= C3_TH), "detail": loo_detail},
        "C4_halfwin": {"ddC_h1": round(ddC1, 2), "ddB_h1": round(ddB1, 2),
                       "ddC_h2": round(ddC2_, 2), "ddB_h2": round(ddB2_, 2), "pass": bool(c4)},
        "VERDICT": "PASS" if (c1 and c2 and loo_ok >= C3_TH and c4) else "FAIL",
    }

    # 分年收益（报告项）
    yearly = {}
    for arm_name, sim in out.items():
        eq = sim["eq"]
        yr = eq.groupby(eq.index.year).last()
        base = eq.groupby(eq.index.year).first()
        yearly[arm_name] = {int(k): round((v / b0 - 1) * 100, 1)
                            for k, v, b0 in zip(yr.index, yr.values, base.values)}

    result = {"meta": {"date": "2026-08-28", "protocol": "预注册见脚本 docstring",
                       "window": f"{WIN_START}→{WIN_END}", "targets": len(members),
                       "cost": "10bp 单边", "band": "5%"},
              "arms": arms, "yearly_pct": yearly, "verdict": verdict,
              "cost_drag": {k: round(v["cost_drag_total"] * 100, 2) for k, v in out.items()}}
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "portfolio_split_results.json"
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)

    print(json.dumps(arms, ensure_ascii=False, indent=1))
    print(json.dumps(verdict, ensure_ascii=False, indent=1)[:1500])
    print("\n分年收益%:")
    for k, v in yearly.items():
        print(f"  {k}: {v}")
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
