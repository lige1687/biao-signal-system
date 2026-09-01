#!/usr/bin/env python3
"""终极组合合成·展示性实验（2026-08-31）：全部通过组件的叠加曲线。

组合定义（零新参数，全部为当日已通过/已认证组件）：
- 主仓腿 = B9 × 0.9 + 黄金518880 × 0.1（gold_expand 的 gold_10 臂）
  + 空仓资金按 511010 国债 ETF 实际序列计息（cash_leg 的 cash_bond 臂）；
- 卫星腿 = LEI fund_only（full_stack 留痕曲线）× 0.2；
- 分账合成：终极 = 主仓终极 × 0.8 + LEI × 0.2。

标注：本合成不设新判定（各组件已各自过审）；黄金 10% 在 gold_expand
中为 G5 FAIL 的「配置型可选」档——本页把它作为展示选项呈现，最终
拍板时可用开关去掉。窗口 = 卫星腿窗口 2017-03-24→2026-07-17。

产出：raw/ultimate/ultimate_results.json + ultimate_curves.csv
复现：PYTHONHASHSEED=0 python3 scripts/run_ultimate_combo.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_cash_leg import simulate_cash  # noqa: E402

RAW = SRC / "ultimate"
W_SAT, W_GOLD = 0.20, 0.10
SEG_LO, SEG_HI = "2021-06-18", "2024-02-29"


def seg_dd(eq: pd.Series, lo: str, hi: str) -> float:
    seg = eq[(eq.index >= pd.Timestamp(lo)) & (eq.index <= pd.Timestamp(hi))]
    base = eq[eq.index < pd.Timestamp(lo)]
    start = float(base.iloc[-1]) if len(base) else float(seg.iloc[0])
    peak, worst = start, 0.0
    for v in seg.values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return round(worst * 100, 2)


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

    bond = pd.read_parquet(SRC / "cash_leg/511010_close.parquet")["close"].astype(float)
    bond.index = pd.to_datetime(bond.index)
    bond_r = bond.pct_change().fillna(0.0)
    gold = pd.read_parquet(SRC / "gold_expand/518880_close.parquet")["close"].astype(float)
    gold.index = pd.to_datetime(gold.index)

    d = json.loads((SRC / "full_stack/full_stack_results.json").read_text())
    curve = d["task2"]["fund_only"]["curve"]
    sat = pd.Series({pd.Timestamp(p["date"]): float(p["equity"])
                     for p in curve}).sort_index()
    w_start = sat.index[0]
    w_end = pd.Timestamp("2026-08-18")
    idx = prices.index[(prices.index >= w_start) & (prices.index <= w_end)]

    p_win = prices.reindex(idx)
    tier = rps.tier_daily(b200, idx)
    expo = pd.DataFrame({c: tier for c in p_win.columns})
    ones = pd.DataFrame(1.0, index=idx, columns=p_win.columns)

    eq_hold = rps.simulate(p_win, ones)["eq"]
    eq_b9 = rps.simulate(p_win, expo)["eq"]
    eq_b9_cash = simulate_cash(p_win, expo, bond_r)
    gold_w = gold.reindex(idx).ffill()

    hold_n = eq_hold / eq_hold.iloc[0]
    b9_n = eq_b9 / eq_b9.iloc[0]
    b9c_n = eq_b9_cash / eq_b9_cash.iloc[0]
    gold_n = gold_w / gold_w.iloc[0]
    main_ult = b9c_n * (1 - W_GOLD) + gold_n * W_GOLD          # B9+现金+黄金
    sat_n = (sat / sat.iloc[0]).reindex(idx).ffill()
    sat_n.iloc[0] = 1.0

    arms = {
        "hold": hold_n,
        "b9": b9_n,
        "b9_cash": b9c_n,
        "main_ult": main_ult,
        "lei": sat_n,
        "combo20": b9_n * 0.8 + sat_n * 0.2,
        "ultimate": main_ult * (1 - W_SAT) + sat_n * W_SAT,
    }

    def met(eq: pd.Series) -> dict:
        m = rps.metrics(eq)
        m["seg_dd_pct"] = seg_dd(eq, SEG_LO, SEG_HI)
        return m

    out = {
        "experiment": "ultimate_combo_display",
        "window": [str(idx[0].date()), str(idx[-1].date())],
        "definition": ("main = B9*0.9 + gold*0.1 with idle cash in 511010; "
                       "ultimate = main*0.8 + LEI_fund_only*0.2"),
        "arms": {k: met(v) for k, v in arms.items()},
        "no_new_params": True,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "ultimate_results.json").write_text(text)
    df = pd.DataFrame(arms)
    df.index.name = "date"
    df.to_csv(RAW / "ultimate_curves.csv", float_format="%.6f")

    print(json.dumps(out["arms"], ensure_ascii=False, indent=1))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
