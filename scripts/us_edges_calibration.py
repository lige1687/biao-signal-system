"""美股宽度边界本土化标定——用户：放宽到 75/25、80/20 等组合，找适合美股的宽度档位。

背景：A 股档位线 43.3/56.7 源自 30/70 边界；美股 B200 均值 66、高区占比 75%，
A 股尺子不适配。家族固定为「防守版」结构（顺势三档 + MA200 闸 + 波动控制），
只动边界与两个稳健旋钮（预注册，全部展示不挑选）：
  边界网格 low/high: 20/80, 25/75, 30/70(基准), 35/85, 40/80, 40/90, 45/95, 50/90, 60/95
  preq 分位模式（滚动分位自适应，A 股侧已实现的机制）单列对照
  vol_target: 0.10 / 0.15 | gamma: 1.0 / 1.5
标的：^GSPC / ^IXIC（复权宽度 1986→2026-08-31）。
通过线（预注册）：全窗年化 ≥ 持有−4pp，回撤 ≤ -20%，且三窗 Calmar 一致为正、
邻域（相邻边界组合）中位 Calmar 进前 50%（防孤峰）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.service import compute_run

EDGES = [(20, 80), (25, 75), (30, 70), (35, 85), (40, 80), (40, 90), (45, 95), (50, 90),
         (60, 95)]
VOLS = [0.10, 0.15]
GAMMAS = [1.0, 1.5]


def main() -> None:
    for symbol, name, bench_cagr_ref in [("^GSPC", "标普500", None), ("^IXIC", "纳指", None)]:
        rows = []
        for lo, hi in EDGES:
            for vt in VOLS:
                for g in GAMMAS:
                    cfg = dict(
                        strategy="ladder", indicator="b200", n_bands=3,
                        direction="momentum", low_edge=float(lo), high_edge=float(hi),
                        gamma=g, vol_target=vt, gate_mode="ma200",
                        min_trade=0.05, fee_bps=10, breadth="sp500",
                    )
                    r = compute_run({**cfg, "symbol": symbol})
                    m = r["metrics"]
                    mid = r["daily"]["date"][len(r["daily"]["date"]) // 2]
                    h1 = compute_run({**cfg, "symbol": symbol, "end": mid})["metrics"]
                    h2 = compute_run({**cfg, "symbol": symbol, "start": mid})["metrics"]
                    rows.append(dict(
                        lo=lo, hi=hi, vol=vt, gamma=g,
                        cagr=m["strategy_cagr"], mdd=m["strategy_mdd"],
                        calmar=m["calmar"],
                        calmar1=h1["calmar"], calmar2=h2["calmar"],
                        bench=m["benchmark_cagr"], bench_mdd=m["benchmark_mdd"],
                    ))
        for vt in VOLS:
            for g in GAMMAS:
                cfg = dict(
                    strategy="ladder", indicator="b200", n_bands=3,
                    direction="momentum", edge_mode="preq",
                    low_edge=20.0, high_edge=80.0,
                    gamma=g, vol_target=vt, gate_mode="ma200",
                    min_trade=0.05, fee_bps=10, breadth="sp500",
                )
                r = compute_run({**cfg, "symbol": symbol})
                m = r["metrics"]
                mid = r["daily"]["date"][len(r["daily"]["date"]) // 2]
                h1 = compute_run({**cfg, "symbol": symbol, "end": mid})["metrics"]
                h2 = compute_run({**cfg, "symbol": symbol, "start": mid})["metrics"]
                rows.append(dict(
                    lo="preq", hi="", vol=vt, gamma=g,
                    cagr=m["strategy_cagr"], mdd=m["strategy_mdd"],
                    calmar=m["calmar"],
                    calmar1=h1["calmar"], calmar2=h2["calmar"],
                    bench=m["benchmark_cagr"], bench_mdd=m["benchmark_mdd"],
                ))
        df = pd.DataFrame(rows)
        df["ok"] = (
            (df["cagr"] >= df["bench"] - 0.04) & (df["mdd"] >= -0.20)
            & (df["calmar1"] > 0) & (df["calmar2"] > 0)
        )
        print(f"\n===== {name}（持有年化 {df['bench'].iloc[0]:+.1%} / 回撤 "
              f"{df['bench_mdd'].iloc[0]:.0%}）=====")
        top = df.sort_values("calmar", ascending=False)
        cols = ["lo", "hi", "vol", "gamma", "cagr", "mdd", "calmar", "calmar1", "calmar2", "ok"]
        print(top[cols].head(12).to_string(
            index=False, float_format=lambda x: f"{x:+.2f}" if abs(x) < 10 else f"{x:.2f}"
        ))
        out = Path(__file__).parents[1] / f"docs/timing-sweep/us_edges_{symbol.strip('^')}.csv"
        df.to_csv(out, index=False)


if __name__ == "__main__":
    main()
