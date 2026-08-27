"""A 股 10 年回填兜底：腾讯日 K 按日期窗口分页（东财被限流时的 Plan B）。

背景：东财 push2his 对本机出现连接重置（限流），而腾讯 fqkline 单次请求
封顶约 640 根；本脚本用 2 年日期窗口分页请求后拼接，复用
TencentPriceProvider 的代码映射与解析器（口径一致：优先 qfqday 前复权，
ETF 缺 qfq 时回退 day 不复权）。

所有窗口的复权口径必须一致（全 qfq 或全 day），混用直接判失败，防止拼出
跳变序列。写入前过 validate_bars，provider 落 "tencent"（可信来源）。
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
SLEEP_SECONDS = 0.5
TRIM_YEARS = 10


def fetch_windowed(provider: TencentPriceProvider, symbol: str) -> tuple[pd.DataFrame, bool]:
    info = resolve_symbol(symbol)
    if not is_a_share(info):
        raise ValueError(f"{symbol} 不是 A 股标的")
    code = provider._tencent_symbol(info)  # noqa: SLF001 - 脚本复用映射逻辑
    frames: list[pd.DataFrame] = []
    adjusted_flags: set[bool] = set()
    empty_windows = 0
    for start, end in WINDOWS:
        params = {"param": f"{code},day,{start},{end},800,qfq"}
        url = f"{provider._HOST}?{urllib.parse.urlencode(params)}"  # noqa: SLF001
        try:
            frame, adjusted = provider._parse_payload(  # noqa: SLF001
                provider._fetch_text(url), symbol  # noqa: SLF001
            )
        except DataUnavailableError as exc:
            # 上市前的窗口返回空数据节点：跳过，不算失败。
            if "未返回 qfqday/day" in str(exc):
                empty_windows += 1
                time.sleep(SLEEP_SECONDS)
                continue
            raise
        if not frame.empty:
            frames.append(frame)
            adjusted_flags.add(adjusted)
        time.sleep(SLEEP_SECONDS)
    if not frames:
        raise ValueError(f"{symbol} 所有窗口均无数据（空窗口 {empty_windows} 个）")
    if len(adjusted_flags) > 1:
        raise ValueError(f"{symbol} 各窗口复权口径不一致: {adjusted_flags}，拒绝拼接")
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    return merged, adjusted_flags.pop()


def trim_years(frame: pd.DataFrame, years: int) -> pd.DataFrame:
    cutoff = frame.index[-1] - pd.DateOffset(years=years)
    return frame[frame.index >= cutoff]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".lei_signal_lab" / "backtest_pool"),
        help="缓存根目录（默认回测深池）",
    )
    args = parser.parse_args()
    symbols = [
        "000001.SS", "000001.SZ", "000300.SS", "000688.SS", "000698.SS",
        "002555.SZ", "159165.SZ", "159652.SZ", "159915.SZ", "510300.SS",
        "512400.SS", "512890.SS", "513870.SS", "515050.SS", "515130.SS",
        "515170.SS", "515300.SS", "515880.SS", "600519.SS",
    ]
    cache = ParquetCache(args.root)
    provider = TencentPriceProvider()
    for symbol in symbols:
        existing = cache.read(symbol, require_trusted_provider=False)
        old_rows = len(existing) if existing is not None else 0
        try:
            merged, adjusted = fetch_windowed(provider, symbol)
            merged = trim_years(merged, TRIM_YEARS)
            bars, _report = validate_bars(
                merged, symbol=symbol, provider="tencent",
                adjusted=adjusted, min_rows=21,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {symbol}: {type(exc).__name__}: {exc}")
            continue
        if len(bars) > old_rows:
            cache.write(symbol, bars, provider="tencent")
            print(
                f"[OK]   {symbol}: {old_rows} -> {len(bars)} 根 "
                f"({bars.index[0].date()} ~ {bars.index[-1].date()}) "
                f"adjusted={adjusted}"
            )
        else:
            print(f"[KEEP] {symbol}: 现有 {old_rows} 根不少于新取 {len(bars)} 根")


if __name__ == "__main__":
    main()
