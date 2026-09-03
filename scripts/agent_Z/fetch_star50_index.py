#!/usr/bin/env python3
"""Agent Z · 抓取科创50指数（sh000688）日线到本地 raw 目录（2026-09-03）。

用途：语义三前置验证（反脆弱补偿效应事件研究）需要科创50 的指数口径数据
作为 588000 ETF（2020-11 起）的延长披露口径。方法与阶段二 gap-fill 抓
sh000698 完全同一源（akshare 新浪 stock_zh_index_daily）。

口径披露：科创50指数 2020-07-23 正式发布（基日 2019-12-31），2020-01 起
为发布日回溯计算值。本脚本只写一个新文件，不触碰任何现有文件/缓存。
"""
from __future__ import annotations

from pathlib import Path

import akshare as ak
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/experiments/raw/antifragile/sh000688_index.parquet"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = ak.stock_zh_index_daily(symbol="sh000688")
    df = df.rename(
        columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close"}
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")][["open", "high", "low", "close", "volume"]]
    df.to_parquet(OUT)
    print(f"saved {OUT}: {df.index.min().date()} -> {df.index.max().date()} rows={len(df)}")


if __name__ == "__main__":
    main()
