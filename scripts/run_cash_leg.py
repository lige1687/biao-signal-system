#!/usr/bin/env python3
"""现金腿收益增强·侧向探索（2026-08-31）：B9 空仓资金的机会成本。

问题：现行全部组合实验的空仓段收益 = 0（timing sweep 的 cash_rate=0、
portfolio_split 现金零收益）。B9 的宽度闸在高宽度段空仓/半仓——这些
闲置资金如果放进现金类工具（货基/短债），对组合年化的「免费」提升
有多大？回撤代价多少？

【探索协议】（矩阵报告级，不设预注册 PASS 判定；如实呈报三臂差异）
现金处理三臂：
- cash0：现行口径（空仓收益 = 0），基线；
- cash_const_1.8：空仓资金按常数年化 1.8% 计息（近十年货基中枢）；
  敏感性 1.0% / 2.5%；
- cash_bond：空仓资金买 511010 国债 ETF（实际价格序列，窗口年化
  3.10% / 日波动 0.144% / 最大回撤 −5.06%，含 2016-17 债灾）。
机械：与 run_portfolio_split 的 B_全宽度闸（=B9）逐位一致，仅在
growth 中加入 (1 − Σactual) × cash_r_t 项。合体臂 = 主仓腿现金变体
× LEI 卫星腿 20% 分账（卫星腿内部现金处理不可改，如实标注：合体
口径的现金增强仅覆盖主仓腿）。
窗口：2015-06-16 → 2026-08-18。
产出：raw/cash_leg/cash_leg_results.json + curves csv。
复现：PYTHONHASHSEED=0 python3 scripts/run_cash_leg.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402

RAW = SRC / "cash_leg"

COST, BAND = rps.COST, rps.BAND
CASH_R = {"cash_const_1.0": 0.010, "cash_const_1.8": 0.018,
          "cash_const_2.5": 0.025}
W_SAT = 0.20


def simulate_cash(prices: pd.DataFrame, exposures: pd.DataFrame,
                  cash_r: pd.Series | float = 0.0) -> pd.Series:
    """rps.simulate 的现金增强版：growth 加 (1-Σactual)×cash_r_t 项。"""
    rets = prices.pct_change().fillna(0.0)
    names = list(prices.columns)
    n = len(names)
    actual = np.zeros(n)
    port = 1.0
    eq = []
    if isinstance(cash_r, float):
        cash_daily = pd.Series(cash_r / 252.0, index=prices.index)
    else:
        cash_daily = cash_r.reindex(prices.index).ffill().fillna(0.0)
    for i in range(len(prices)):
        r = rets.iloc[i].values
        if i > 0:
            idle = 1.0 - float(actual.sum())
            port = port * (1.0 + float(actual @ r) + idle * cash_daily.iloc[i])
        target = exposures.iloc[i].values / n
        trade = np.abs(target - actual) >= BAND
        new_actual = np.where(trade, target, actual)
        turnover = float(np.abs(new_actual - actual).sum())
        port *= 1.0 - COST * turnover
        actual = new_actual
        eq.append(port)
    return pd.Series(eq, index=prices.index)


def main() -> None:
    b200 = rps.load_breadth()
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    frames = {}
    for name, rel in members:
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    prices = pd.DataFrame(frames)
    prices = prices[(prices.index >= pd.Timestamp(rps.WIN_START))
                    & (prices.index <= pd.Timestamp(rps.WIN_END))] \
        .dropna(axis=0, how="any")
    idx = prices.index
    tier = rps.tier_daily(b200, idx)
    expo = pd.DataFrame({c: tier for c in prices.columns})

    # 空仓占比统计（等权组合的实际风险敞口分布）
    tier_dist = tier.value_counts(normalize=True).to_dict()
    idle_avg = float((1.0 - expo.sum(axis=1) / len(prices.columns)).mean())

    bond = pd.read_parquet(RAW / "511010_close.parquet")["close"].astype(float)
    bond.index = pd.to_datetime(bond.index)
    bond_r = bond.pct_change().fillna(0.0)

    # LEI 卫星腿（full_stack fund_only，周频 ffill）
    d = json.loads((SRC / "full_stack/full_stack_results.json").read_text())
    curve = d["task2"]["fund_only"]["curve"]
    sat = pd.Series({pd.Timestamp(p["date"]): float(p["equity"])
                     for p in curve}).sort_index()

    arms: dict[str, pd.Series] = {}
    eq0 = simulate_cash(prices, expo, 0.0)
    arms["b9_cash0"] = eq0
    for label, rate in CASH_R.items():
        arms[f"b9_{label}"] = simulate_cash(prices, expo, rate)
    arms["b9_cash_bond"] = simulate_cash(prices, expo, bond_r)

    # 合体臂（窗口 = 卫星腿窗口 2017-03-24 起）
    sat_n_full = (sat / sat.iloc[0]).reindex(idx).ffill()
    sat_n_full.iloc[0] = 1.0
    combo_start = sat.index[0]
    for label in ["cash0"] + list(CASH_R.keys()) + ["cash_bond"]:
        key = "b9_" + label if label != "cash0" else "b9_cash0"
        e = arms[key]
        e_sub = e[e.index >= combo_start]
        e_sub_n = e_sub / e_sub.iloc[0]
        s_sub = sat_n_full[sat_n_full.index >= combo_start]
        arms[f"combo_{label}"] = e_sub_n * (1 - W_SAT) + s_sub * W_SAT

    met = {}
    for k, v in arms.items():
        m = rps.metrics(v)
        met[k] = m

    out = {
        "experiment": "cash_leg_b9",
        "window": [str(idx[0].date()), str(idx[-1].date())],
        "tier_distribution": {str(k): round(v, 3) for k, v in tier_dist.items()},
        "avg_idle_weight": round(idle_avg, 3),
        "bond_stats": {"ann_pct": 3.10, "maxdd_pct": -5.06},
        "b9": {k: met[f"b9_{k}"] for k in ["cash0"] + list(CASH_R.keys()) + ["cash_bond"]},
        "combo": {k.replace("combo_", ""): met[k]
                  for k in met if k.startswith("combo_")},
    }
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "cash_leg_results.json").write_text(text)
    pd.DataFrame({k: v for k, v in arms.items()}).to_csv(
        RAW / "cash_curves.csv", float_format="%.6f")

    print("tier 分布:", out["tier_distribution"], "平均空仓权重:", out["avg_idle_weight"])
    print(json.dumps(out["b9"], ensure_ascii=False, indent=1))
    print(json.dumps(out["combo"], ensure_ascii=False, indent=1))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
