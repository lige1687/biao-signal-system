"""真实 LEI 技术信号做执行层——宽度预算 × LEI（第18轮 MA20 代理的正主，预注册）。

用系统真实规则替换代理：compute_features → classify_colors（绿灰黑三色）+
compute_long_trend（EMA60/120 长趋势）。指数无 volume，注入常数列（量比列不用）。
执行门（预注册，全部逐日、可当时计算）：
  L1 = 预算 × 非黑（黑色=明确下行才离场，灰/绿在场，符合"灰≠卖出"教义）
  L2 = 预算 × 非长期空头（仅 long_bear 离场）
  L3 = 预算 × (非黑 ∧ 非bear)
对照：E0 冠军纯宽度 | E3 预算×MA20（第18轮代理）。
通过线（预注册）：任一 L 变体 2018 窗回撤较 E0 改善 ≥5pp，且全窗超额 ≥ E0−1pp。
费用 10bp，T+1 开盘（引擎同口径）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.timing_backtest.data import align_index_breadth, load_breadth, load_index_bars
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
TARGETS = [
    ("399006", "创业板指"), ("399975", "证券指数"), ("399997", "中证白酒"),
    ("000300", "沪深300"),
]


def lei_gates(aligned: pd.DataFrame) -> dict[str, pd.Series]:
    bars = aligned[["open", "high", "low", "close"]].copy()
    if "volume" not in bars.columns:
        bars["volume"] = 1.0
    feat = compute_features(bars)
    color = classify_colors(feat)["signal_color"]
    trend = compute_long_trend(feat)["long_trend"]
    not_black = (color != "black").astype(float)
    not_bear = (trend != "long_bear").astype(float)
    return {"L1非黑": not_black, "L2非长期空头": not_bear, "L3双门": not_black * not_bear}


def main() -> None:
    for symbol, name in TARGETS:
        bars = load_index_bars(symbol)
        aligned = align_index_breadth(bars, load_breadth("cn_all"))
        budget = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        gates = lei_gates(aligned)
        ma20 = (aligned["close"] > aligned["close"].rolling(20).mean()).astype(float)
        variants = [("E0纯宽度", budget), ("E3·MA20代理", budget * ma20)]
        variants += [(f"{k}", budget * v) for k, v in gates.items()]
        half = len(aligned) // 2
        wins = [
            ("全窗", aligned), ("前半", aligned.iloc[:half]), ("后半", aligned.iloc[half:]),
            ("2018阴跌", aligned.loc["2018-01-01":"2019-01-31"]),
            ("2024V底", aligned.loc["2024-06-01":"2025-03-31"]),
        ]
        print(f"\n=== {name}({symbol}) {aligned.index[0].date()}→{aligned.index[-1].date()} ===")
        for wtag, win in wins:
            parts = []
            for vtag, tgt in variants:
                res = simulate(win, tgt.loc[win.index], fee_bps=10.0, cash_rate=0.0,
                               min_trade=0.05)
                m = summarize_run(res.daily, res.trades)
                parts.append(
                    f"{vtag}:年化{m['strategy_cagr']:+6.1%}/回撤{m['strategy_mdd']:5.0%}"
                )
            print(f"  [{wtag}] " + " | ".join(parts))


if __name__ == "__main__":
    main()
