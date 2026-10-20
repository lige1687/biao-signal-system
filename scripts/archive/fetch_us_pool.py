"""美股专项 Phase 0 v2：SP500 成分 OHLCV 直接入校准池 + 攒复权收盘矩阵。

每股一次 yfinance 调用，产出两份资产：
  1. ~/.lei_signal_lab/backtest_pool_us/{TICKER}.bars.parquet（OHLCV，provider=yfinance，
     ParquetCache 正规写入含 meta）+ 基准 ^GSPC —— Phase 1 模块校准直接用
  2. ~/.lei_signal_lab/cache/us_qfq_matrix.parquet（收盘矩阵）—— 重建 SP500 宽度用
断点续传：池里已有 bars 文件的跳过（并从其 close 补矩阵）。限速指数退避。
脏数据校验：单日 < -40% 弃。
用法：python3.11 scripts/fetch_us_pool.py [--matrix-only]
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
POOL = Path.home() / ".lei_signal_lab/backtest_pool_us"
REJECTED = CACHE / "us_qfq_rejected.txt"


def fetch_ohlcv(t: str) -> pd.DataFrame | None:
    import yfinance as yf

    h = yf.Ticker(t).history(period="max", auto_adjust=True)
    h.index = pd.to_datetime(h.index).tz_localize(None)
    df = h[["Open", "High", "Low", "Close", "Volume"]].astype(float).rename(
        columns={"Open": "open", "High": "high", "Low": "low",
                 "Close": "close", "Volume": "volume"}
    )
    # -75% 仅挡拆股假摔；真实崩盘（如 AAPL 2000-09-29 -51.9%）必须保留
    return df if len(df) > 250 and df["close"].pct_change().min() > -0.75 else None


def main() -> int:
    matrix_only = "--matrix-only" in sys.argv
    from lei_signal.data.cache import ParquetCache

    POOL.mkdir(parents=True, exist_ok=True)
    cache = ParquetCache(POOL)
    tickers = list(pd.read_parquet(SRC).columns) + ["^GSPC"]
    closes: dict[str, pd.Series] = {}
    if DEST.exists():
        old = pd.read_parquet(DEST)
        closes = {c: old[c].dropna() for c in old.columns}
    bad: list[str] = []
    n_new = 0
    for i, t in enumerate(tickers):
        bar_path = POOL / f"{t}.bars.parquet"
        if bar_path.exists():
            if t not in closes:
                closes[t] = pd.read_parquet(bar_path)["close"].dropna()
            continue
        if matrix_only and t != "^GSPC":
            continue
        for attempt in range(5):
            try:
                df = fetch_ohlcv(t)
                if df is None:
                    bad.append(t)
                    break
                if not matrix_only:
                    cache.write(t, df, kind="bars", provider="yfinance")
                closes[t] = df["close"]
                n_new += 1
                break
            except Exception as e:  # noqa: BLE001
                wait = min(60 * 2 ** attempt, 600)
                print(f"[{t}] {type(e).__name__} 退避{wait}s", flush=True)
                time.sleep(wait)
        else:
            bad.append(t)
        time.sleep(1.2)
        if (i + 1) % 25 == 0:
            pd.DataFrame(closes).to_parquet(DEST)
            print(f"{i + 1}/{len(tickers)} 落盘 累计{len(closes)} 新{n_new} 弃{len(bad)}",
                  flush=True)
    pd.DataFrame(closes).to_parquet(DEST)
    REJECTED.write_text("\n".join(bad), encoding="utf-8")
    print(f"完成：矩阵{len(closes)}只 池新增{n_new} 弃{len(bad)}（{REJECTED.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
