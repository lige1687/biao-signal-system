"""宽度×技术协同回测——方法层③：架构核心假设的直接验证（预注册）。

假设：宽度预算（冠军三档）× 技术执行（代理=收盘>MA20，单一预注册定义不挑选）
优于各自单干；且 MA20 技术止损可补接刀格（2018 型阴跌）——两全检验。
变体：A 纯宽度(冠军) | B 纯技术(MA20上持/下空) | C 协同(冠军预算 × MA20开关)。
通过线（预注册）：C 全窗超额 ≥ A−1pp，且 2018 窗回撤较 A 改善 ≥5pp，且 2024V底
窗超额 ≥ A−10pp（不许把 V 底肉割太多）。费用 10bp，T+1 开盘执行（引擎同口径）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


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
    ("000300", "沪深300"), ("980017", "国证芯片"),
]


def main() -> None:
    for symbol, name in TARGETS:
        bars = load_index_bars(symbol)
        aligned = align_index_breadth(bars, load_breadth("cn_all"))
        budget = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        tech = (aligned["close"] > aligned["close"].rolling(20).mean()).astype(float)
        variants = [
            ("A纯宽度", budget),
            ("B纯技术", tech),
            ("C协同", budget * tech),
        ]
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
                res = simulate(win, tgt.loc[win.index], fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
                m = summarize_run(res.daily, res.trades)
                parts.append(
                    f"{vtag}:年化{m['strategy_cagr']:+6.1%}/回撤{m['strategy_mdd']:5.0%}/超额{m['excess_cagr']:+6.1%}"
                )
            print(f"  [{wtag}] " + " | ".join(parts))


if __name__ == "__main__":
    main()
