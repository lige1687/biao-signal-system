"""10 年历史行情回填（决策点 2：A 股 + 美股都回填 10 年）。

背景（docs/data-sufficiency-audit-2026-08-24.md）：默认行情链的腾讯源
对个股 qfq 只给约 641 根、指数 1500 根，美股走 yahoo_v8 默认 2y，导致
现状最长 8.6 年、美股仅 2 年，无法支撑 V2 §16 的分年份/牛熊分组统计。

本脚本按标的类型选长历史源，一次性回填本地缓存：
- A 股（沪深个股/ETF/指数）：东方财富 push2his，fqt=1 前复权，全量后裁 10 年；
- 同花顺板块指数（THxxxxxx.SECTOR）：THSBoardProvider(start_year=2016)；
- 美股 ETF / 海外指数：YahooV8PriceProvider(range_param="10y")。

写入规则（防退化）：
- 新数据行数多于现有缓存 -> 覆盖；
- 现有缓存 provider 不可信（parquet_cache / local_upload 等）且新抓取成功
  -> 覆盖（来源洗白，行数即使持平也接受）；
- 其余情况保留现有缓存，只记录跳过。
所有写入走 ParquetCache.write，provider 落 meta.json（可信来源标记）。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.data.cache import UNTRUSTED_PROVIDERS, ParquetCache  # noqa: E402
from lei_signal.data.providers import (  # noqa: E402
    EastmoneyPriceProvider,
    THSBoardProvider,
    YahooV8PriceProvider,
)
from lei_signal.data.symbols import is_a_share, resolve_symbol  # noqa: E402

TRIM_YEARS = 10


def provider_trusted(provider: str) -> bool:
    """与 cache.py 一致：整串精确匹配黑名单（组合名如
    parquet_cache+tencent_rt 不在名单内，视为可信）。"""
    return provider.strip().lower() not in UNTRUSTED_PROVIDERS


def trim_years(frame: pd.DataFrame, years: int) -> pd.DataFrame:
    frame.index = pd.to_datetime(frame.index)
    last = frame.index[-1]
    cutoff = last - pd.DateOffset(years=years)
    return frame[frame.index >= cutoff].sort_index()


def classify(symbol: str) -> str:
    if THSBoardProvider.supports(symbol):
        return "ths_board"
    info = resolve_symbol(symbol)
    if is_a_share(info):
        return "eastmoney"
    return "yahoo_v8"


def fetch(symbol: str, kind: str, *, eastmoney_max_bars: int = 6000) -> tuple[pd.DataFrame, str]:
    if kind == "ths_board":
        provider = THSBoardProvider(start_year=2016)
    elif kind == "eastmoney":
        # max_bars 限定只取最近 N 根：fqt=1 全量前复权在早年可能含非正价
        # （如 600519 大比例分红后的 2000 年代价格），validate_bars 会拒绝。
        provider = EastmoneyPriceProvider(max_bars=eastmoney_max_bars)
    else:
        provider = YahooV8PriceProvider(range_param="10y")
    data = provider.fetch(symbol)
    return data.bars, provider.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbols", nargs="*", help="只回填指定标的（默认全部缓存标的）")
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".lei_signal_lab" / "backtest_pool"),
        help="缓存根目录（默认回测深池，与 live 缓存隔离）",
    )
    parser.add_argument("--sleep", type=float, default=0.4, help="标的间休眠秒数")
    parser.add_argument(
        "--eastmoney-max-bars",
        type=int,
        default=6000,
        help="东财源 lmt 上限（限定最近 N 根，避开早年非正复权价）",
    )
    args = parser.parse_args()

    cache = ParquetCache(args.root)
    live = ParquetCache()
    symbols = args.symbols or sorted({
        path.name[: -len(".bars.parquet")]
        for root in (live._root, cache._root)
        for path in root.glob("*.bars.parquet")  # noqa: SLF001
    })
    print(f"待回填标的 {len(symbols)} 个（含不可信来源重取）\n")
    updated = 0
    kept: list[str] = []
    failed: list[str] = []

    for symbol in symbols:
        kind = classify(symbol)
        existing = cache.read(symbol, require_trusted_provider=False)
        old_rows = len(existing) if existing is not None else 0
        old_provider = str((cache.read_meta(symbol) or {}).get("provider", "?"))
        try:
            new_frame, provider_name = fetch(
                symbol, kind, eastmoney_max_bars=args.eastmoney_max_bars
            )
        except Exception as exc:  # noqa: BLE001 - 单标的失败不阻断整体
            failed.append(f"{symbol} ({kind}): {type(exc).__name__}: {exc}")
            print(f"[FAIL] {symbol} ({kind}): {exc}")
            time.sleep(args.sleep)
            continue

        new_frame = trim_years(new_frame, TRIM_YEARS)
        new_rows = len(new_frame)
        trusted_old = provider_trusted(old_provider)
        if new_rows > old_rows or (not trusted_old and new_rows > 0):
            cache.write(symbol, new_frame, provider=provider_name)
            updated += 1
            first = new_frame.index[0].date()
            last = new_frame.index[-1].date()
            print(
                f"[OK]   {symbol}: {old_rows} -> {new_rows} 根 "
                f"({first} ~ {last}) [{old_provider} -> {provider_name}]"
            )
        else:
            kept.append(f"{symbol}: 现有 {old_rows} 根不少于新取 {new_rows} 根")
            print(f"[KEEP] {symbol}: 现有 {old_rows} 根，新取 {new_rows} 根")
        time.sleep(args.sleep)

    print(f"\n更新 {updated} / 保留 {len(kept)} / 失败 {len(failed)}")
    if failed:
        print("失败明细：")
        for line in failed:
            print(f"  {line}")


if __name__ == "__main__":
    main()
