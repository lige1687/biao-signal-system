"""诊断：冠军策略在 2024-09 以来的科技牛里的表现拆解。

问题：用户观察到这一轮科技牛中，逆势三档容易提前卖飞/提前接飞刀。
验证：本轮窗口（2024-09-20 → 今）逐标的：策略 vs 持有，以及仓位档位
（空仓/半仓/满仓）各时段的市场收益归属。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.service import compute_run

CHAMPION = dict(
    strategy="ladder", indicator="b200", n_bands=3, direction="contrarian",
    edge_mode="fixed", low_edge=30.0, high_edge=70.0, gamma=1.0,
    min_trade=0.05, fee_bps=10, breadth="cn_all",
)
MOMENTUM = dict(
    strategy="ladder", indicator="b200", n_bands=3, direction="momentum",
    edge_mode="fixed", low_edge=30.0, high_edge=70.0, gamma=1.0,
    min_trade=0.05, fee_bps=10, breadth="cn_all",
)

TECH = [
    ("399006", "创业板指"),
    ("980017", "国证芯片"),
    ("980030", "通信指数"),
    ("512720", "计算机ETF"),
    ("159819", "人工智能ETF"),
    ("588000", "科创50ETF"),
]

WIN = "2024-09-20"  # 924 行情起点前夜


def regime(v: float) -> str:
    if v <= 0.05:
        return "空仓"
    if v >= 0.95:
        return "满仓"
    return "半仓"


def diag(symbol: str, name: str, cfg: dict, start: str) -> None:
    r = compute_run({**cfg, "symbol": symbol, "start": start})
    m = r["metrics"]
    d = pd.DataFrame(r["daily"])
    d["bench_ret"] = d["benchmark"].pct_change()
    end_date = d["date"].iloc[-1]
    print(f"\n=== {name}({symbol}) {start} → {end_date} · {r['params']['direction']} ===")
    print(
        f"  持有: 年化 {m['benchmark_cagr']:+.1%} 回撤 {m['benchmark_mdd']:.1%} | "
        f"策略: 年化 {m['strategy_cagr']:+.1%} 回撤 {m['strategy_mdd']:.1%} | "
        f"超额(年化) {m['excess_cagr']:+.1%}  交易 {int(m['n_trades'])} 次"
    )
    d["regime"] = d["weight"].map(regime)
    for reg in ["空仓", "半仓", "满仓"]:
        sub = d[d["regime"] == reg]
        if sub.empty:
            print(f"  [{reg}] 无")
            continue
        cum = (1 + sub["bench_ret"].fillna(0)).prod() - 1
        print(
            f"  [{reg}] {len(sub)} 天({len(sub) / len(d):.0%}): "
            f"期间市场累计 {cum:+.1%} · B200 均值 {sub['breadth'].mean():.1f}"
        )
    last = d.iloc[-1]
    print(
        f"  现状: B200={last['breadth']:.1f} → 仓位 {last['weight']:.0%}"
    )


def main() -> None:
    for symbol, name in TECH:
        for label, cfg in [("冠军·逆势", CHAMPION), ("对照·顺势", MOMENTUM)]:
            try:
                diag(symbol, name, cfg, WIN)
            except Exception as e:  # noqa: BLE001
                print(f"\n=== {name}({symbol}) {label} 失败: {type(e).__name__}: {e}")
    # 全历史对照（不只本轮）——看顺势在科技标的上是否结构性更优
    print("\n\n########## 全历史对照（同参数）##########")
    for symbol, name in TECH:
        for label, cfg in [("冠军·逆势", CHAMPION), ("对照·顺势", MOMENTUM)]:
            try:
                diag(symbol, f"{name}·{label}", cfg, "2000-01-01")
            except Exception as e:  # noqa: BLE001
                print(f"\n=== {name}·{label} 失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
