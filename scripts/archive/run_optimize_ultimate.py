#!/usr/bin/env python3
"""终极组合优化扫描·侧向探索（2026-08-31）：三个有数据支撑的优化方向。

候选（全部来自当日已发现、未测过的线索）：
- O1 再平衡：合体实验中月度再平衡比分账 +0.7pp（combined_cert），终极版未测；
- O2 权重网格：w_gold 15% 在 gold_expand 中单调更优；w_sat 30% 在
  combined_cert 中更优（Calmar 0.403）——联合小网格 2×2；
- O3 卫星腿 RR 门槛：rr_sensitivity 单模块证据强（门槛 3.0/4.0 样本外
  expR 1.74/3.30 vs 不设 0.85），但组合层卫星腿（fund_only 217 笔）
  一直是 rr_min=None——从未移植。本实验在信号层过滤 reward_risk≥阈值
  （signal_date 当日可知，无前视）→ 重跑资金层（1% + N10/池6 + 降级，
  与 full_stack fund_only 配置逐位一致）。

【探索协议】（后验多臂比较，如实声明：本扫描找方向不定参数；任何
"最优臂"按七折引用，转正需单独预注册认证。）
窗口：2017-03-24 → 2026-08-18（卫星腿窗口，与终极组合页一致）。
产出：raw/ultimate/optimize_results.json + optimize_curves.csv
复现：PYTHONHASHSEED=0 python3 scripts/run_optimize_ultimate.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_cash_leg import simulate_cash  # noqa: E402
from run_combined_cert import rebalance_series  # noqa: E402

from lei_signal.backtest.full_sim import dedup_signals  # noqa: E402
from lei_signal.backtest.portfolio import (  # noqa: E402
    PortfolioConfig,
    simulate_portfolio,
)

RAW = SRC / "ultimate"
SEG_LO, SEG_HI = "2021-06-18", "2024-02-29"
BENCHMARK = "000300.SS"


def seg_dd(eq: pd.Series) -> float:
    seg = eq[(eq.index >= pd.Timestamp(SEG_LO)) & (eq.index <= pd.Timestamp(SEG_HI))]
    base = eq[eq.index < pd.Timestamp(SEG_LO)]
    start = float(base.iloc[-1]) if len(base) else float(seg.iloc[0])
    peak, worst = start, 0.0
    for v in seg.values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return round(worst * 100, 2)


def load_sat_stream(rr_min: float | None) -> tuple[list[dict], dict]:
    """A 门禁 + B' 信号流，可选 RR 门槛（先过滤后去重，符合执行顺序）。"""
    runs = {
        "A": SRC / "portfolio/A_ETF_cm05_shrink.json",
        "B'": SRC / "portfolio/Bp_stocks_30_3_a61.json",
    }
    all_tr: list[dict] = []
    n_none_rr = 0
    for mod, p in runs.items():
        r = json.loads(p.read_text())
        for t in r["trades"]:
            if t["symbol"] == BENCHMARK or t["exit_date"] is None:
                continue
            t = dict(t)
            t["module"] = mod
            all_tr.append(t)
    a_gated = [t for t in all_tr if t["module"] != "A"
               or (t["benchmark_clock_type"] != 3 and t["trend_stage"] >= 4)]
    if rr_min is not None:
        kept = []
        for t in a_gated:
            rr = t.get("reward_risk")
            if rr is None:
                n_none_rr += 1
                continue
            if float(rr) >= rr_min:
                kept.append(t)
        a_gated = kept
    stream, stats = dedup_signals(a_gated)
    stats["rr_none_dropped"] = n_none_rr
    return stream, stats


def sat_curve(stream: list[dict]) -> pd.Series:
    res = simulate_portfolio(
        stream, PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                                pool_concurrent_cap=6, dd_deescalate=True))
    s = pd.Series({pd.Timestamp(p["date"]): float(p["equity"])
                   for p in res["curve"]}).sort_index()
    return s, res


def main() -> None:
    # ── 主仓腿机械（B9+现金+黄金，权重参数化）──
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

    sat_base, _ = sat_curve(load_sat_stream(None)[0])
    sat_rr2, res_rr2 = sat_curve(load_sat_stream(2.0)[0])
    sat_rr3, res_rr3 = sat_curve(load_sat_stream(3.0)[0])

    w_start = sat_base.index[0]
    w_end = pd.Timestamp("2026-08-18")
    idx = prices.index[(prices.index >= w_start) & (prices.index <= w_end)]
    p_win = prices.reindex(idx)
    tier = rps.tier_daily(b200, idx)
    expo = pd.DataFrame({c: tier for c in p_win.columns})
    eq_b9c = simulate_cash(p_win, expo, bond_r)
    b9c_n = eq_b9c / eq_b9c.iloc[0]
    gold_n = (gold.reindex(idx).ffill() / gold.reindex(idx).ffill().iloc[0])

    def main_n(w_gold: float) -> pd.Series:
        return b9c_n * (1 - w_gold) + gold_n * w_gold

    def to_daily(sat: pd.Series) -> pd.Series:
        s = (sat / sat.iloc[0]).reindex(idx).ffill()
        s.iloc[0] = 1.0
        return s

    sat_n = to_daily(sat_base)
    sat2_n = to_daily(sat_rr2)
    sat3_n = to_daily(sat_rr3)

    arms: dict[str, pd.Series] = {}
    for w_gold, wg_tag in ((0.10, "g10"), (0.15, "g15")):
        m = main_n(w_gold)
        for w_sat, ws_tag in ((0.20, "s20"), (0.30, "s30")):
            arms[f"base_{wg_tag}_{ws_tag}"] = m * (1 - w_sat) + sat_n * w_sat
    arms["rebal_g10_s20"] = rebalance_series(main_n(0.10), sat_n, 0.20)
    arms["rebal_g10_s30"] = rebalance_series(main_n(0.10), sat_n, 0.30)
    arms["rr2_g10_s20"] = main_n(0.10) * 0.8 + sat2_n * 0.2
    arms["rr2_g10_s30"] = main_n(0.10) * 0.7 + sat2_n * 0.3
    arms["rr3_g10_s20"] = main_n(0.10) * 0.8 + sat3_n * 0.2
    arms["rr3_g10_s30"] = main_n(0.10) * 0.7 + sat3_n * 0.3
    arms["rr2_rebal_g10_s20"] = rebalance_series(main_n(0.10), sat2_n, 0.20)
    arms["rebal_g15_s30"] = rebalance_series(main_n(0.15), sat_n, 0.30)

    def met(eq: pd.Series) -> dict:
        m = rps.metrics(eq)
        m["seg_dd_pct"] = seg_dd(eq)
        return m

    out = {
        "experiment": "ultimate_optimize_scan",
        "window": [str(idx[0].date()), str(idx[-1].date())],
        "posterior_note": "多臂后验比较找方向不定参数；最优臂七折引用",
        "sat_stream_stats": {
            "rr_none": {"n_taken": res_rr2["n_taken"]},
            "rr2": {"n_taken": res_rr2["n_taken"],
                    "cum_R": round(res_rr2["cum_R_taken"], 1),
                    "final_eq_wan": round(res_rr2["final_equity"] / 1e4, 1)},
            "rr3": {"n_taken": res_rr3["n_taken"],
                    "cum_R": round(res_rr3["cum_R_taken"], 1),
                    "final_eq_wan": round(res_rr3["final_equity"] / 1e4, 1)},
        },
        "arms": {k: met(v) for k, v in arms.items()},
    }
    # 基线（无门槛）流统计
    st0, _ = load_sat_stream(None)
    st2, stats2 = load_sat_stream(2.0)
    st3, stats3 = load_sat_stream(3.0)
    res0 = simulate_portfolio(
        st0, PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                             pool_concurrent_cap=6, dd_deescalate=True))
    out["sat_stream_stats"]["rr_none"] = {
        "n_taken": res0["n_taken"], "cum_R": round(res0["cum_R_taken"], 1),
        "final_eq_wan": round(res0["final_equity"] / 1e4, 1)}
    out["dedup_stats"] = {"rr2": stats2, "rr3": stats3}

    RAW.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "optimize_results.json").write_text(text)
    df = pd.DataFrame(arms)
    df.index.name = "date"
    df.to_csv(RAW / "optimize_curves.csv", float_format="%.6f")

    print(json.dumps(out["sat_stream_stats"], ensure_ascii=False, indent=1))
    print(json.dumps(out["arms"], ensure_ascii=False, indent=1))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
