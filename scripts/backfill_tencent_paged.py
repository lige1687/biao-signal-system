"""腾讯分页兜底回填（东财被限流时 Plan B）：支持任意 A 股标的列表。

复用 scripts/backfill_tencent_windows.py 的窗口分页与代码映射，但参数化
标的列表；provider 落 "tencent"（可信来源）。
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.data.cache import ParquetCache  # noqa: E402
from lei_signal.data.providers import DataUnavailableError, TencentPriceProvider  # noqa: E402
from lei_signal.data.symbols import is_a_share, resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402

WINDOWS: tuple[tuple[str, str], ...] = (
    ("2016-01-01", "2017-12-31"),
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2026-12-31"),
)
SLEEP = 0.5
TRIM_YEARS = 10


def fetch_windowed(provider: TencentPriceProvider, symbol: str) -> tuple[pd.DataFrame, bool]:
    info = resolve_symbol(symbol)
    if not is_a_share(info):
        raise ValueError(f"{symbol} 不是 A 股标的")
    code = provider._tencent_symbol(info)
    frames: list[pd.DataFrame] = []
    adjusted_flags: set[bool] = set()
    empty = 0
    for start, end in WINDOWS:
        params = {"param": f"{code},day,{start},{end},800,qfq"}
        url = f"{provider._HOST}?{urllib.parse.urlencode(params)}"
        try:
            frame, adjusted = provider._parse_payload(provider._fetch_text(url), symbol)
        except DataUnavailableError as exc:
            if "未返回 qfqday/day" in str(exc):
                empty += 1
                time.sleep(SLEEP)
                continue
            raise
        if not frame.empty:
            frames.append(frame)
            adjusted_flags.add(adjusted)
        time.sleep(SLEEP)
    if not frames:
        raise ValueError(f"{symbol} 所有窗口均无数据（空 {empty} 个）")
    if len(adjusted_flags) > 1:
        raise ValueError(f"{symbol} 复权口径不一致: {adjusted_flags}")
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    return merged, adjusted_flags.pop()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+", help="A 股代码列表（如 512000.SS 513500.SS）")
    ap.add_argument("--root", default=str(Path.home() / ".lei_signal_lab" / "backtest_pool"))
    args = ap.parse_args()

    cache = ParquetCache(args.root)
    provider = TencentPriceProvider()

    for sym in args.symbols:
        existing = cache.read(sym, require_trusted_provider=False)
        old_rows = len(existing) if existing is not None else 0
        try:
            merged, adjusted = fetch_windowed(provider, sym)
            cutoff = merged.index[-1] - pd.DateOffset(years=TRIM_YEARS)
            merged = merged[merged.index >= cutoff]
            bars, _ = validate_bars(merged, symbol=sym, provider="tencent",
                                    adjusted=adjusted, min_rows=21)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {sym}: {type(exc).__name__}: {exc}")
            continue
        if len(bars) > old_rows:
            cache.write(sym, bars, provider="tencent")
            print(
                f"[OK]   {sym}: {old_rows} -> {len(bars)} 根 "
                f"({bars.index[0].date()} ~ {bars.index[-1].date()}) adj={adjusted}"
            )
        else:
            print(f"[KEEP] {sym}: 现 {old_rows} 根 >= 新 {len(bars)} 根")


if __name__ == "__main__":
    main()
