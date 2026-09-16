"""全标的终审扩容（第十四轮）：所有可用 A 股标的 × {冠军, 冠军+MA200闸} × 三窗。

目的：把进攻/防守名单扩到全部可测标的（用户方向：更多标的、更好收益或更低回撤）。
入选标准（预注册，沿用第八轮）：进攻 = 三窗超额全>0；防守位 = 回撤较持有大幅改善
（减半或 >20pp）且回撤较无闸版再降。已排除标的（AI/半导体/中证500/消费/黄金）照旧。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import INSTRUMENTS
from lei_signal.timing_backtest.service import TimingDataUnavailable, compute_run

BASE = dict(
    strategy="ladder", indicator="b200", n_bands=3, edge_mode="fixed",
    low_edge=30.0, high_edge=70.0, gamma=1.0, direction="contrarian",
    min_trade=0.05, fee_bps=10, breadth="cn_all",
)
VARIANTS = [
    ("冠军", BASE),
    ("冠军+闸", {**BASE, "gate_mode": "ma200", "gate_cap": 0.0}),
]
EXCLUDED = {"159819", "980017", "510500", "000932", "518880"}  # 已入册排除名单


def half_date(symbol: str) -> str:
    r = compute_run({**BASE, "symbol": symbol})
    d = r["daily"]["date"]
    return d[len(d) // 2]


def audit(symbol: str, name: str) -> list[dict]:
    mid = half_date(symbol)
    rows = []
    for tag, cfg in VARIANTS:
        full = compute_run({**cfg, "symbol": symbol})["metrics"]
        h1 = compute_run({**cfg, "symbol": symbol, "end": mid})["metrics"]
        h2 = compute_run({**cfg, "symbol": symbol, "start": mid})["metrics"]
        rows.append(dict(
            标的=name, 变体=tag,
            全窗超额=f"{full['excess_cagr']:+.1%}", 全窗回撤=f"{full['strategy_mdd']:.0%}",
            持有回撤=f"{full['benchmark_mdd']:.0%}",
            前半超额=f"{h1['excess_cagr']:+.1%}", 后半超额=f"{h2['excess_cagr']:+.1%}",
        ))
    return rows


def main() -> None:
    rows, skipped = [], []
    for symbol, spec in INSTRUMENTS.items():
        if spec.market != "cn":
            continue
        if symbol in EXCLUDED:
            skipped.append(f"{spec.name}(排除名单)")
            continue
        try:
            rows.extend(audit(symbol, spec.name))
            print(f"ok {spec.name}", file=sys.stderr)
        except (TimingDataUnavailable, FileNotFoundError) as e:
            skipped.append(f"{spec.name}({type(e).__name__})")
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    print("\n跳过:", "、".join(skipped))
    df.to_csv(Path(__file__).parents[1] / "docs/timing-sweep/full_audit_20260827.csv", index=False)


if __name__ == "__main__":
    main()
