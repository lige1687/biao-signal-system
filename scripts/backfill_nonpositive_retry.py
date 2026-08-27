"""非正价格个股的兜底回填：按窗口从新到旧抓取，遇到非正价格窗口即止。

高股息个股前复权早年价格可能 <= 0（茅台先例）。策略：从最新窗口向前合并，
一旦某窗口出现非正价格，丢弃该窗口及更早的（有效起点后移），记录起点。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.data.cache import ParquetCache  # noqa: E402
from lei_signal.data.providers import (  # noqa: E402
    DataUnavailableError,
    TencentPriceProvider,
)
from lei_signal.data.symbols import is_a_share, resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402

WINDOWS: tuple[tuple[str, str], ...] = (
    ("2024-01-01", "2026-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2018-01-01", "2019-12-31"),
    ("2016-01-01", "2017-12-31"),
)
SLEEP = 0.5
TRIM_YEARS = 10

SYMBOLS = sys.argv[1:]
OUT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/bcd_retrial")


def main() -> None:
    cache = ParquetCache(Path.home() / ".lei_signal_lab" / "backtest_pool")
    provider = TencentPriceProvider()
    report: dict[str, dict] = {}
    for sym in SYMBOLS:
        info = resolve_symbol(sym)
        if not is_a_share(info):
            continue
        code = provider._tencent_symbol(info)
        frames: list[pd.DataFrame] = []
        stopped = False
        for start, end in WINDOWS:
            if stopped:
                break
            params = {"param": f"{code},day,{start},{end},800,qfq"}
            url = f"{provider._HOST}?{urllib.parse.urlencode(params)}"
            try:
                frame, adjusted = provider._parse_payload(
                    provider._fetch_text(url), sym
                )
            except DataUnavailableError as exc:
                if "未返回 qfqday/day" in str(exc):
                    time.sleep(SLEEP)
                    continue
                print(f"[FAIL] {sym}: {exc}", flush=True)
                stopped = True
                break
            time.sleep(SLEEP)
            if frame.empty:
                continue
            positive = (
                (frame[["open", "high", "low", "close"]] > 0).all().all()
            )
            if not positive:
                stopped = True  # 该窗口及更早全部不可用
                break
            frames.append(frame)
        if not frames:
            report[sym] = {"status": "no_data"}
            print(f"[FAIL] {sym}: 无可用窗口", flush=True)
            continue
        merged = pd.concat(frames)
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        cutoff = merged.index[-1] - pd.DateOffset(years=TRIM_YEARS)
        merged = merged[merged.index >= cutoff]
        try:
            validate_bars(
                merged, symbol=sym, provider="tencent", adjusted=bool(adjusted)
            )
        except Exception as exc:  # noqa: BLE001 - 兜底报告用
            report[sym] = {"status": "invalid", "error": str(exc)}
            print(f"[FAIL] {sym}: {exc}", flush=True)
            continue
        old = cache.read(sym, require_trusted_provider=False)
        old_rows = 0 if old is None else len(old)
        if len(merged) > old_rows:
            cache.write(sym, merged, provider="tencent")
            report[sym] = {
                "status": "ok",
                "rows": len(merged),
                "start": str(merged.index[0].date()),
                "end": str(merged.index[-1].date()),
            }
            print(
                f"[OK] {sym}: {old_rows} -> {len(merged)} 根 "
                f"({merged.index[0].date()} ~ {merged.index[-1].date()})",
                flush=True,
            )
        else:
            report[sym] = {"status": "kept_old", "old_rows": old_rows}
            print(f"[KEEP] {sym}: 旧缓存 {old_rows} 根", flush=True)
    fp = OUT / "backfill_nonpositive_retry.json"
    fp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[report -> {fp.name}]", flush=True)


if __name__ == "__main__":
    main()
