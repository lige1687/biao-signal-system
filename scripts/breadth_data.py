"""宽度→仓位实验：数据加载工具（json/SQLite/yfinance → DataFrame）。

数据源（2026-08-27 盘点）：
- 美股宽度：~/.lei_signal_lab/lab.db 表 market_breadth_snapshots，market_id='SP500'，
  breadth_50/breadth_200 为百分数（0-100），非空区间 1986-03-13 → 2026-08-14。
  注意 coverage_* 是数据覆盖率不是宽度（stage-b200 报告已澄清）。
- A 股宽度：~/.lei_signal_lab/cache/a_share_ma_breadth_history.json，
  1260 个交易日 2021-06-18 → 2026-08-27，ma20/50/200_pct 为百分数。
  lab.db 的 CN_ALL_A 行是空壳勿用。短样本（晚于 2021-02 峰）须标注。
- 指数价格：
  - 美股长序列本地无（回测池 ^GSPC 仅 2016 起），用 yfinance 拉 ^GSPC
    auto_adjust 收盘，缓存到 raw 目录（离线可复跑）。
  - A 股基准 000300.SS 读回测池 ~/.lei_signal_lab/backtest_pool/。
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

LAB_DB = Path("~/.lei_signal_lab/lab.db").expanduser()
CACHE = Path("~/.lei_signal_lab/cache").expanduser()
POOL = Path("~/.lei_signal_lab/backtest_pool").expanduser()
RAW_DIR = Path(__file__).resolve().parents[1] / "docs/experiments/raw/breadth_position"
GSPC_LONG_PARQUET = RAW_DIR / "gspc_long_close.parquet"


def load_us_breadth() -> pd.DataFrame:
    """SP500 宽度（日频，百分数），index=as_of(date)。"""
    db = sqlite3.connect(LAB_DB)
    try:
        df = pd.read_sql_query(
            "select as_of, breadth_20, breadth_50, breadth_200 "
            "from market_breadth_snapshots where market_id='SP500'",
            db,
        )
    finally:
        db.close()
    df["date"] = pd.to_datetime(df["as_of"]).dt.date
    df = df.dropna(subset=["breadth_50"]).drop(columns=["as_of"]).set_index("date")
    return df.sort_index()


def load_cn_breadth() -> pd.DataFrame:
    """A 股全市场宽度（日频，百分数），2021-06-18 起（短样本）。"""
    with open(CACHE / "a_share_ma_breadth_history.json") as f:
        rows = json.load(f)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.set_index("date").sort_index()


def load_gspc_long(start="1985-01-01") -> pd.Series:
    """长 ^GSPC 收盘（auto_adjust）。首次拉取后缓存 raw 目录。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if GSPC_LONG_PARQUET.exists():
        s = pd.read_parquet(GSPC_LONG_PARQUET)["close"]
        s.index = pd.to_datetime(s.index).date
        return s
    import yfinance as yf

    df = yf.download("^GSPC", start=start, auto_adjust=True, progress=False)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):  # 多列 ticker 侧
        close = close.iloc[:, 0]
    close = close.dropna()
    close.index = pd.to_datetime(close.index).date
    out = pd.DataFrame({"close": close.values}, index=pd.Index(list(close.index), name="date"))
    out.to_parquet(GSPC_LONG_PARQUET)
    return close


def load_pool_close(symbol: str) -> pd.Series:
    """回测池标的收盘价。"""
    df = pd.read_parquet(POOL / f"{symbol}.bars.parquet")
    s = df["close"]
    s.index = pd.to_datetime(s.index).date
    return s.sort_index()


def merge_breadth_price(breadth: pd.DataFrame, price: pd.Series,
                        breadth_col: str) -> pd.DataFrame:
    """按日期内联合并（宽度与价格同日对齐，均基于当日收盘计算）。"""
    b = breadth[[breadth_col]].copy()
    b.columns = ["breadth"]
    p = price.rename("close").to_frame()
    merged = b.join(p, how="inner").dropna()
    return merged


if __name__ == "__main__":
    us = load_us_breadth()
    cn = load_cn_breadth()
    print("US breadth:", len(us), us.index.min(), "→", us.index.max())
    print("CN breadth:", len(cn), cn.index.min(), "→", cn.index.max())
    print("GSPC long:", len(load_gspc_long()))
