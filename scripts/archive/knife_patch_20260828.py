"""接刀格（低·下：B200<43.3 且 价<MA200）补丁验证——预注册三变体。

变体（全部只在「B200<43.3 的低区」内生效，把目标仓位 ×0.5）：
  V1 时间止损：B200 连续 >126 交易日（约6个月）低于 43.3 → 减半
  V2 深度档：B200 < 15（极端深度）→ 减半
  V3 斜率确认：B200<43.3 且 B200 的 20 日变化 <0（还在坠落）→ 减半
对照：冠军原版（无补丁）。
通过标准（预注册）：全窗超额劣化 ≤1pp，且 2018 窗（2018-01→2019-01）回撤改善 ≥10pp，
且后半窗超额仍 >0。三窗 + 2018 窗 + 2024 V底窗 + 当前窗全部报告。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import align_index_breadth, load_breadth, load_index_bars
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
TARGETS = [("399006", "创业板指"), ("399975", "证券指数")]
WINDOWS = [
    ("全窗", None, None), ("2018阴跌", "2018-01-01", "2019-01-31"),
    ("2024V底", "2024-06-01", "2025-03-31"), ("当前", "2026-04-01", None),
]


def patches(aligned: pd.DataFrame, target: pd.Series) -> dict[str, pd.Series]:
    b = aligned["b200"]
    low = b < 43.3
    # V1: 连续低区天数
    streak = low * (low.groupby((~low).cumsum()).cumcount() + 1)
    v1 = (streak > 126) & low
    # V2: 极端深度
    v2 = b < 15
    # V3: 20 日斜率仍向下
    v3 = low & (b - b.shift(20) < 0)
    return {
        "冠军": target,
        "V1时间止损": target.where(~v1, target * 0.5),
        "V2深度档": target.where(~v2, target * 0.5),
        "V3斜率确认": target.where(~v3, target * 0.5),
    }


def main() -> None:
    for symbol, name in TARGETS:
        bars = load_index_bars(symbol)
        aligned = align_index_breadth(bars, load_breadth("cn_all"))
        base = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        variants = patches(aligned, base)
        half = len(aligned) // 2
        print(f"\n=== {name}({symbol}) {aligned.index[0].date()}→{aligned.index[-1].date()} ===")
        for wtag, s, e in WINDOWS:
            if s is None and e is None:
                win, win2 = aligned, aligned.iloc[half:]
            else:
                sl = aligned.loc[s:] if s else aligned
                win = sl.loc[:e] if e else sl
                mid = win.index[len(win) // 2]
                win2 = win.loc[mid:]
            line = [f"[{wtag}]"]
            for vtag, tgt in variants.items():
                res = simulate(win, tgt.loc[win.index], fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
                m = summarize_run(res.daily, res.trades)
                res2 = simulate(win2, tgt.loc[win2.index], fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
                m2 = summarize_run(res2.daily, res2.trades)
                line.append(
                    f"{vtag}:超额{m['excess_cagr']:+.1%}/回撤{m['strategy_mdd']:.0%}(后半{m2['excess_cagr']:+.1%})"
                )
            print("  " + " | ".join(line))


if __name__ == "__main__":
    main()
