"""行情分段矩阵：什么组合 × 什么标的 × 什么时段（B200 档位 × MA200 趋势格）。

每格可当时判定（无未来函数）：当日 B200 ∈ {低<43.3, 中, 高≥56.7} × 当日收盘
vs 自身 MA200 ∈ {下, 上}。逐格统计：该格天数 / 市场累计 / 策略累计 / 格内超额
（策略与基准在格内日收益分别复利后相减）/ 平均仓位。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.service import compute_run

LADDER = dict(
    strategy="ladder", indicator="b200", n_bands=3, edge_mode="fixed",
    low_edge=30.0, high_edge=70.0, gamma=1.0, min_trade=0.05, fee_bps=10,
)
COMBOS = [
    ("冠军·逆势三档", {**LADDER, "direction": "contrarian"}),
    ("逆势+MA200闸", {**LADDER, "direction": "contrarian", "gate_mode": "ma200", "gate_cap": 0.0}),
    ("顺势三档", {**LADDER, "direction": "momentum"}),
    (
        "防守版(顺+闸+波控)",
        {**LADDER, "direction": "momentum", "gate_mode": "ma200", "gate_cap": 0.0, "vol_target": 0.15},
    ),
    (
        "双极值20/90",
        dict(
            strategy="reversal", indicator="b200", low_extreme=20.0, high_extreme=90.0,
            confirm=5.0, batch_mode="time", batches=5, min_trade=0.05, fee_bps=10,
        ),
    ),
]
INSTRUMENTS = [
    ("399006", "创业板指", None),
    ("000300", "沪深300", None),
    ("399975", "证券指数", None),
    ("399997", "中证白酒", None),
    ("980017", "国证芯片", None),
    ("^GSPC", "标普500", "sp500"),
]
CELLS = ["低·下", "低·上", "中·下", "中·上", "高·下", "高·上"]


def cell_labels(b: pd.Series, close: pd.Series) -> pd.Series:
    ma = close.rolling(200).mean()
    lo = b < 43.3
    hi = b >= 56.7
    zone = np.select([lo, hi], ["低", "高"], default="中")
    side = np.where(close >= ma, "上", "下")
    return pd.Series([f"{z}·{s}" for z, s in zip(zone, side)], index=b.index)


def regime_table(symbol: str, name: str, breadth: str | None) -> None:
    base = None
    print(f"\n{'=' * 100}\n## {name}({symbol})")
    for label, cfg in COMBOS:
        r = compute_run({**cfg, "symbol": symbol, **({"breadth": breadth} if breadth else {})})
        m = r["metrics"]
        d = pd.DataFrame(r["daily"]).set_index("date")
        if base is None:
            base = d
            cells = cell_labels(
                pd.Series(base["breadth"].values, index=base.index, dtype=float),
                pd.Series(base["close"].values, index=base.index, dtype=float),
            )
            print(
                f"窗口 {d.index[0]} → {d.index[-1]}；持有年化 {m['benchmark_cagr']:+.1%} "
                f"回撤 {m['benchmark_mdd']:.0%}。各格天数/市场累计："
            )
            bench_ret = d["benchmark"].pct_change().fillna(0)
            for c in CELLS:
                mask = cells == c
                if mask.sum():
                    cum = (1 + bench_ret[mask.values]).prod() - 1
                    print(f"  {c}: {mask.sum()}天 市场累计{cum:+.0%}", end=";")
            print()
        sr = d["equity"].pct_change().fillna(0)
        br = d["benchmark"].pct_change().fillna(0)
        parts = []
        for c in CELLS:
            mask = (cells == c).values
            if mask.sum() == 0:
                parts.append(f"{c} --")
                continue
            ex = (1 + sr[mask]).prod() - (1 + br[mask]).prod()
            parts.append(f"{c} {ex:+.0%}")
        print(
            f"  {label:<12} 全局: 年化{m['strategy_cagr']:+6.1%} 回撤{m['strategy_mdd']:5.0%} "
            f"超额{m['excess_cagr']:+6.1%} | 格内超额贡献: " + " ".join(parts)
        )


def main() -> None:
    for symbol, name, breadth in INSTRUMENTS:
        try:
            regime_table(symbol, name, breadth)
        except Exception as e:  # noqa: BLE001
            print(f"\n## {name}({symbol}) 失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
