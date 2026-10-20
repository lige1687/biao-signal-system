"""刷新全A宽表尾巴：用每日增量缓存 a_share_klines.parquet 补 a_share_klines_full.parquet。

背景：全量表按「整只股票跳过」断点续传，老股票尾巴永不更新；而 16:30 的
precompute_a_share_ma 每天增量更新长表缓存（截至当日）。本脚本只把宽表末日之后
的新日期从长表拼上去（不碰历史，避免新浪/腾讯口径混叠；新股作为新列自然进入，
含幸存者偏差与全量表一致）。写盘原子替换。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
FULL = CACHE / "a_share_klines_full.parquet"
LONG = CACHE / "a_share_klines.parquet"


def main() -> int:
    if not FULL.exists():
        print(f"缺 {FULL}，先跑 scripts/backfill_breadth_full.py --market cn")
        return 1
    wide = pd.read_parquet(FULL)
    long_df = pd.read_parquet(LONG)
    codes = long_df["symbol"].astype(str).str.replace(r"^[A-Za-z]+", "", regex=True)
    piv = long_df.assign(code=codes, date=pd.to_datetime(long_df["date"])).pivot(
        index="date", columns="code", values="close"
    )
    tail = piv.loc[piv.index > wide.index.max()]
    if tail.empty:
        print(f"宽表已最新（{wide.index.max().date()}），长表截至 {piv.index.max().date()}")
        return 0
    merged = pd.concat([wide, tail.reindex(columns=wide.columns.union(tail.columns))])
    merged = merged.sort_index()
    tmp = FULL.with_suffix(".parquet.tmp")
    merged.to_parquet(tmp)
    tmp.replace(FULL)
    print(
        f"宽表 {wide.index.max().date()} → {merged.index.max().date()}"
        f"（+{len(tail)} 天，列 {wide.shape[1]}→{merged.shape[1]}）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
