"""条件引擎验证：冠军三档，唯「高·上格」(B200≥56.7 且 收盘≥MA200) 改为持有。

假设来源：第十二轮矩阵——冠军的全部落后都发生在高·上格（动量牛空仓），
而该格可当时判定。若假设成立：创业板应大幅改善且回撤可控。
对照：同窗口冠军原版 + 持有。三窗（全/前半/后半）报告。
警示：该规则由同一段历史的事后分格归纳而来，属在样本内构造，结果需打折。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import INSTRUMENTS, align_index_breadth, load_breadth, load_index_bars
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
TARGETS = [
    ("399006", "创业板指", None), ("000300", "沪深300", None), ("399975", "证券指数", None),
    ("399997", "中证白酒", None), ("000819", "有色金属", None), ("980017", "国证芯片", None),
]


def run_variant(aligned: pd.DataFrame, target_full: pd.Series, window: pd.DataFrame,
                tag: str) -> dict:
    target = target_full.loc[window.index]
    res = simulate(window, target, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
    m = summarize_run(res.daily, res.trades)
    return {
        "变体": tag, "年化": f"{m['strategy_cagr']:+.1%}", "回撤": f"{m['strategy_mdd']:.0%}",
        "持有年化": f"{m['benchmark_cagr']:+.1%}", "持有回撤": f"{m['benchmark_mdd']:.0%}",
        "超额": f"{m['excess_cagr']:+.1%}",
    }


def main() -> None:
    for symbol, name, _ in TARGETS:
        bars = load_index_bars(symbol)
        breadth = load_breadth("cn_all")
        aligned = align_index_breadth(bars, breadth)
        target_full = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        ma200 = aligned["close"].rolling(200).mean()
        hold_zone = (aligned["b200"] >= 56.7) & (aligned["close"] >= ma200)
        cond = target_full.where(~hold_zone, 1.0)

        half = len(aligned) // 2
        windows = [
            ("全窗", aligned), ("前半", aligned.iloc[:half]), ("后半", aligned.iloc[half:]),
        ]
        print(f"\n=== {name}({symbol}) {aligned.index[0].date()}→{aligned.index[-1].date()} ===")
        rows = []
        for wtag, win in windows:
            rows.append(run_variant(aligned, target_full, win, f"{wtag}·冠军"))
            rows.append(run_variant(aligned, cond, win, f"{wtag}·条件引擎"))
        print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
