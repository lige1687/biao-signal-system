"""组合层回测——方向④：从单标的各自为战上升到组合仓位（预注册）。

设计：8 个指数 sleeve（创业板/证券/新能车/白酒/有色/银行/通信/沪深300）等权,
每 sleeve 独立跑满历史（起点不同则晚启动、启动前现金），组合日收益=存活 sleeve
日收益等权平均（近似每日再平衡）。变体：
  a 持有组合（全 1.0）
  b 冠军组合（各 sleeve 冠军三档 30/70）
  c 协同组合（冠军预算 × MA20 开关——方向③的回撤控制版）
通过线（预注册）：b/c 组合年化 ≥ 持有组合 −1pp，且回撤改善 ≥10pp。
窗口：全窗/前半/后半/2015 股灾/2018 阴跌/本轮。费用 10bp 每 sleeve。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import align_index_breadth, load_breadth, load_index_bars
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
SLEEVES = [
    ("399006", "创业板"), ("399975", "证券"), ("399976", "新能车"), ("399997", "白酒"),
    ("000819", "有色"), ("399986", "银行"), ("980030", "通信"), ("000300", "沪深300"),
]
VARIANTS = ["持有组合", "冠军组合", "协同组合"]


def perf(eq: pd.Series) -> str:
    p = compute_performance(eq)
    return f"年化{p['cagr']:+6.1%}/回撤{p['mdd']:5.0%}/Calmar{p['calmar']:.2f}"


def main() -> None:
    rets: dict[str, dict[str, pd.Series]] = {v: {} for v in VARIANTS}
    for symbol, name in SLEEVES:
        bars = load_index_bars(symbol)
        aligned = align_index_breadth(bars, load_breadth("cn_all"))
        budget = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        tech = (aligned["close"] > aligned["close"].rolling(20).mean()).astype(float)
        for vtag, tgt in [("持有组合", pd.Series(1.0, index=aligned.index)),
                          ("冠军组合", budget), ("协同组合", budget * tech)]:
            res = simulate(aligned, tgt, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
            rets[vtag][symbol] = res.daily["equity"].pct_change().fillna(0)
        print(f"sleeve ok {name} {aligned.index[0].date()}→{aligned.index[-1].date()}",
              file=sys.stderr)

    port_eq = {}
    for vtag in VARIANTS:
        df = pd.DataFrame(rets[vtag])
        port_eq[vtag] = (1 + df.mean(axis=1, skipna=True)).cumprod()
    start, end = port_eq["持有组合"].index[0], port_eq["持有组合"].index[-1]
    print(f"\n=== 8 sleeve 等权组合 {start.date()}→{end.date()} ===")
    half = port_eq["持有组合"].index[len(port_eq["持有组合"]) // 2]
    wins = [
        ("全窗", None, None), ("前半", None, half), ("后半", half, None),
        ("2015股灾", "2015-06-01", "2016-02-29"),
        ("2018阴跌", "2018-01-01", "2019-01-31"),
        ("本轮科技牛", "2024-09-20", None),
    ]
    for wtag, s, e in wins:
        seg = {v: eq.loc[s:e].dropna() if s else eq for v, eq in port_eq.items()}
        seg = {v: (eq.loc[:e] if e else eq) for v, eq in seg.items()}
        line = [f"[{wtag}]"]
        for vtag in VARIANTS:
            line.append(f"{vtag}: {perf(seg[vtag])}")
        print("  " + " | ".join(line))

    # 组合层面仓位暴露（冠军组合）：平均目标仓位的时间分布
    df_budget = pd.DataFrame(
        {sym: build_target(
            align_index_breadth(load_index_bars(sym), load_breadth("cn_all")),
            LADDER, None, TrendGate(), align_index_breadth(load_index_bars(sym), load_breadth("cn_all")).iloc[:0],
        ) for sym, _ in SLEEVES}
    )
    avg_pos = df_budget.mean(axis=1)
    print(
        f"\n冠军组合平均仓位: 全史均值 {avg_pos.mean():.0%} | 当前 {avg_pos.iloc[-1]:.0%} | "
        f"仓位<20% 时间占比 {(avg_pos < 0.2).mean():.0%} | >80% 占比 {(avg_pos > 0.8).mean():.0%}"
    )


if __name__ == "__main__":
    main()
