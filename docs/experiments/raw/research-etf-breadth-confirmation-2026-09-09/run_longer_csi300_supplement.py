"""Longer CSI300-only window; deliberately separate from the common-window matrix."""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_backtest as rb  # noqa: E402

rb.START = "2015-02-09"
out = HERE / "results" / "longer-csi300-only-2015-02-09"
out.mkdir(parents=True, exist_ok=True)
width = pd.read_parquet(HERE / "prepared/breadth_csi300.parquet")
rows = []
for fee in [0.001, 0.002]:
    for method in ["W0", "W1", "W2", "W3", "B0", "B1", "B2"]:
        source = "csi300" if method.startswith("W") else "baseline"
        summary, daily, trades, signals, rejects, waits, dd = rb.simulate("510300", method, fee, width if method.startswith("W") else None)
        summary.update(width_source=source, account_id=f"510300-{source}-{method}-{int(fee*10000)}bp-longer")
        rows.append(summary)
        daily.to_parquet(out / f"{summary['account_id']}-daily.parquet", index=False)
pd.DataFrame(rows).to_csv(out / "summary.csv", index=False)
print(pd.DataFrame(rows)[["method", "fee_rate", "end_equity", "cagr", "max_drawdown"]].to_string(index=False))
