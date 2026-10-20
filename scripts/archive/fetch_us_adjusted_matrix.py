"""抓 SP500 全成分复权收盘矩阵（美股专项 Phase 0）。

源：yfinance auto_adjust（真复权；akshare 美股 qfq 因子已证坏、Stooq/东财被挡）。
- 股票清单取自现有 sp500_klines.parquet 的列（501 只，当前成分）
- 断点续传：逐只追加到 us_qfq_matrix.parquet（ticker 列），每 25 只落盘一次
- 限速自保：每只间隔 1.2s；YFRateLimitError 指数退避（60s×2^n，上限 5 次）
- 校验：单日跌幅 < -40% 视为复权脏数据，该只丢弃并记录（美股个股熔断极限≈-35%）
用法：python3.11 scripts/fetch_us_adjusted_matrix.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
SRC = CACHE / "sp500_klines.parquet"
DEST = CACHE / "us_qfq_matrix.parquet"
BAD_LOG = CACHE / "us_qfq_rejected.txt"


def main() -> int:
    tickers = list(pd.read_parquet(SRC).columns)
    done: dict[str, pd.Series] = {}
    if DEST.exists():
        old = pd.read_parquet(DEST)
        done = {c: old[c].dropna() for c in old.columns}
        print(f"续传：已有 {len(done)} 只", flush=True)
    import yfinance as yf

    bad: list[str] = []
    for i, t in enumerate(tickers):
        if t in done:
            continue
        for attempt in range(5):
            try:
                h = yf.Ticker(t).history(period="max", auto_adjust=True)
                s = h["Close"].astype(float).dropna()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                if len(s) > 250 and s.pct_change().min() > -0.40:
                    done[t] = s
                else:
                    bad.append(t)
                break
            except Exception as e:  # noqa: BLE001
                wait = min(60 * 2**attempt, 600)
                print(f"[{t}] {type(e).__name__} 退避 {wait}s", flush=True)
                time.sleep(wait)
        else:
            bad.append(t)
        time.sleep(1.2)
        if (i + 1) % 25 == 0:
            pd.DataFrame(done).to_parquet(DEST)
            done_n, bad_n = len(done), len(bad)
            print(f"{i + 1}/{len(tickers)} 落盘 累计{done_n} 弃{bad_n}", flush=True)
    pd.DataFrame(done).to_parquet(DEST)
    BAD_LOG.write_text("\n".join(bad), encoding="utf-8")
    print(f"完成：{len(done)} 只 → {DEST.name}，弃 {len(bad)} 只（{BAD_LOG.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
