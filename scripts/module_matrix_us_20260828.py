"""美股七姐妹 × 全模块矩阵 × 宽度分区——用户问：为啥只测A？别的模块+宽度呢？

矩阵：模块 A(early)/B(ambush)/B(breakout)/C(v1,v2,v3)/D × 七姐妹（复权价，
limit_guard=False，系统默认 rr_min=3、费用 standard；A/B/D 用 A6① 抵扣价退出，
C 用 B3 双条件退出）。清洗=剔除风险距离<10bp 的复权精度病态单。
宽度叠加：按入场日 SP500 B200 分区（低<43.3 / 中 / 高≥56.7，与 A 股档位线一致），
报告各分区期望 + 「宽度过滤版」（只做 低+中 区信号）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.backtest.service import BacktestParams, execute_run
from lei_signal.timing_backtest.data import load_breadth

MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
CONFIGS = [
    ("A·early", "A", "early", "a6_1_costbasis"),
    ("B·ambush", "B", "ambush", "a6_1_costbasis"),
    ("B·breakout", "B", "breakout", "a6_1_costbasis"),
    ("C·v1", "C", "v1", "b3_dual"),
    ("C·v2", "C", "v2", "b3_dual"),
    ("C·v3", "C", "v3", "b3_dual"),
    ("D·假突破", "D", None, "a6_1_costbasis"),
]


def cell(ts: list[dict]) -> str:
    if not ts:
        return "  —"
    wins = [t for t in ts if (t.get("r_net") or 0) > 0]
    total_r = sum(t.get("r_net") or 0 for t in ts)
    pf_num = sum(t["r_net"] for t in wins)
    pf_den = -sum(t["r_net"] for t in ts if (t.get("r_net") or 0) < 0)
    pf = pf_num / pf_den if pf_den > 0 else float("inf")
    return (
        f"{len(ts):>4}笔/胜率{len(wins) / len(ts):>4.0%}/"
        f"期望{total_r / len(ts):+5.2f}R/PF{pf:4.2f}"
    )


def main() -> None:
    b200 = load_breadth("sp500")["b200"]

    def zone(d: str) -> str | None:
        try:
            v = b200.asof(pd.Timestamp(d))
        except KeyError:
            return None
        if pd.isna(v):
            return None
        return "低" if v < 43.3 else ("高" if v >= 56.7 else "中")

    print(f"{'模块':<10} {'全部(清洗后)':<34} {'低区(<43.3)':<34} {'中区':<34} {'高区(≥56.7)':<34} {'宽度过滤(低+中)':<34}")
    for tag, module, variant, exit_v in CONFIGS:
        res = execute_run(BacktestParams(
            symbols=tuple(MAG7), module=module, rr_min=3.0,
            entry_variant=variant, exit_variant=exit_v, fee_label="standard",
            limit_guard=False,
        ))
        trades = [
            t for t in res["trades"]
            if t["entry_price"] and t["stop_price"]
            and (t["entry_price"] - t["stop_price"]) / t["entry_price"] >= 0.001
        ]
        zones = {"低": [], "中": [], "高": []}
        for t in trades:
            z = zone(t["entry_date"])
            if z:
                zones[z].append(t)
        filt = zones["低"] + zones["中"]
        print(
            f"{tag:<10} {cell(trades):<34} {cell(zones['低']):<34} "
            f"{cell(zones['中']):<34} {cell(zones['高']):<34} {cell(filt):<34}"
        )


if __name__ == "__main__":
    main()
