"""SP500 ingestion via akshare (Sina source) — sandbox-friendly.

Replaces `ingest_sp500.py`, which pulls constituents from Wikipedia and
bars from Yahoo; both are blocked in the WorkBuddy sandbox. Here we:

  1. Read the 503 S&P 500 constituents from the existing
     `tests/fixtures/market_context/universes/SP500.parquet`
     (avoids Wikipedia entirely).
  2. Fetch full daily history per constituent via
     `akshare.stock_us_daily` (Sina backend — reachable in sandbox),
     crop to `--lookback-years`.
  3. Fetch the index via `ak.stock_us_daily(".INX")`.
  4. Write `component_bars/{sym}.parquet` + `indices/SP500.parquet`
     in the exact format `LocalMarketBarsProvider` expects
     (columns: date, open, high, low, close, volume; date datetime64).

Then run the backfill to populate `~/.lei_signal_lab/lab.db`:

    LEI_CACHE_ROOT=<repo>/tests \\
        python scripts/round5_repro/backfill_breadth_history.py

(The backfill reads `config.cache_root()/fixtures/market_context`, so we
point LEI_CACHE_ROOT at `<repo>/tests` to hit these fixtures; the DB path
defaults to `~/.lei_signal_lab/lab.db`, which the running backend also
uses.)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import akshare as ak

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "market_context"
UNI_PATH = FIXTURE_ROOT / "universes" / "SP500.parquet"
COMP_ROOT = FIXTURE_ROOT / "component_bars"
IDX_PATH = FIXTURE_ROOT / "indices" / "SP500.parquet"
MARKET_ID = "SP500"
INDEX_SYMBOL = ".INX"  # Sina SP500 index
EXPECTED_COLS = ["date", "open", "high", "low", "close", "volume"]


def load_symbols() -> list[str]:
    df = pd.read_parquet(UNI_PATH)
    return sorted(df["symbol"].astype(str).tolist())


def fetch_bars(symbol: str, lookback_years: int) -> pd.DataFrame | None:
    raw = ak.stock_us_daily(symbol=symbol, adjust="")
    if raw is None or len(raw) == 0:
        return None
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"].astype(str))
    df = df.sort_values("date").reset_index(drop=True)
    if lookback_years and lookback_years > 0:
        cutoff = pd.Timestamp(datetime.now(timezone.utc).date()) - pd.DateOffset(
            years=lookback_years
        )
        df = df[df["date"] >= cutoff]
    cols = [c for c in EXPECTED_COLS if c in df.columns]
    return df[cols].reset_index(drop=True)


def atomic_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lookback-years", type=int, default=2,
                   help="每只成分股 / 指数保留的最大年数(默认2年，够MA200且有真实波动，回填快)")
    p.add_argument("--sleep", type=float, default=0.08, help="每只请求间隔(秒)，防Sina限流")
    p.add_argument("--max-tries", type=int, default=2)
    args = p.parse_args(argv)

    syms = load_symbols()
    print(f"[ingest_sp500_akshare] loaded {len(syms)} symbols from universe", file=sys.stderr)
    COMP_ROOT.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    for i, sym in enumerate(syms):
        done = False
        for attempt in range(args.max_tries):
            try:
                bars = fetch_bars(sym, args.lookback_years)
                if bars is None or len(bars) == 0:
                    break
                atomic_write(bars, COMP_ROOT / f"{sym}.parquet")
                ok += 1
                done = True
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 0:
                    print(f"  {sym} try1 fail: {e}", file=sys.stderr)
                time.sleep(0.5)
        if not done:
            fail += 1
        time.sleep(args.sleep)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(syms)} ok={ok} fail={fail}", file=sys.stderr)
    print(f"[ingest_sp500_akshare] components done: ok={ok} fail={fail}", file=sys.stderr)

    # Index
    print("[ingest_sp500_akshare] fetching index .INX …", file=sys.stderr)
    idx = fetch_bars(INDEX_SYMBOL, args.lookback_years)
    if idx is None or len(idx) == 0:
        print("[ingest_sp500_akshare] ERROR: index fetch failed", file=sys.stderr)
        return 1
    atomic_write(idx, IDX_PATH)
    print(
        f"[ingest_sp500_akshare] index written: {len(idx)} rows "
        f"{idx['date'].min().date()}..{idx['date'].max().date()}",
        file=sys.stderr,
    )
    print("[ingest_sp500_akshare] DONE — next run backfill_breadth_history.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
