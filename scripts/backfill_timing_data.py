#!/usr/bin/env python3
"""宽度择时回测数据回填：指数/ETF 日线 + 全A/SP500 宽度序列。

落盘（~/.lei_signal_lab/cache/timing/）：
  000300/399006/^GSPC/^IXIC/SPY/QQQ/510300/159915.parquet   # index date, columns open/close
  breadth_cn_all.parquet    # 全A B20/B50/B200（由 a_share_klines_full.parquet 重算）
  breadth_sp500.parquet     # 由 sp500_ma_breadth_history.json 转换

用法：
  python3 scripts/backfill_timing_data.py                 # 全部（已存在文件跳过）
  python3 scripts/backfill_timing_data.py --refresh       # 强制重拉
  python3 scripts/backfill_timing_data.py --only breadth  # 只重算宽度
  python3 scripts/backfill_timing_data.py --only a        # 只拉A股
  python3 scripts/backfill_timing_data.py --only us       # 只拉美股
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# ── 绕沙箱代理（必须在 import akshare/yfinance 前）──
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
for k in list(os.environ):
    if "proxy" in k.lower() and k not in ("NO_PROXY", "no_proxy"):
        del os.environ[k]

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import pandas as pd  # noqa: E402
import requests  # noqa: E402

_orig_req = requests.Session.request


def _no_proxy_req(self, *a, **kw):  # type: ignore[no-untyped-def]
    kw.setdefault("proxies", {"http": None, "https": None})
    kw.setdefault("timeout", 30)
    self.trust_env = False
    return _orig_req(self, *a, **kw)


requests.Session.request = _no_proxy_req

from lei_signal.timing_backtest.data import (  # noqa: E402
    INSTRUMENTS,
    TIMING_CACHE_DIR,
    compute_breadth_from_close_matrix,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_timing")

CACHE_ROOT = Path.home() / ".lei_signal_lab/cache"


def _save(df: pd.DataFrame, path: Path) -> None:
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(path)
    logger.info(
        "%s: %d 行  %s → %s", path.name, len(df), df.index.min().date(), df.index.max().date()
    )


def fetch_a_index(fetch_symbol: str) -> pd.DataFrame:
    """A股指数全历史（新浪源，english 列）。"""
    import akshare as ak

    df = ak.stock_zh_index_daily(symbol=fetch_symbol)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[["open", "close"]].astype(float)


def fetch_a_etf(code: str) -> pd.DataFrame:
    """A股 ETF 前复权日线（东财源优先，重试 3 次；失败退新浪源[不复权]并告警）。"""
    import time

    import akshare as ak

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            df = ak.fund_etf_hist_em(
                symbol=code, period="daily",
                start_date="19900101", end_date="20991231", adjust="qfq",
            )
            df["日期"] = pd.to_datetime(df["日期"])
            return df.set_index("日期")[["开盘", "收盘"]].astype(float).rename(
                columns={"开盘": "open", "收盘": "close"}
            )
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    logger.warning("东财源失败(%s)，退新浪源[不复权，分红未计]", last_err)
    prefix = "sh" if code.startswith("5") else "sz"
    df = ak.fund_etf_hist_sina(symbol=prefix + code)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[["open", "close"]].astype(float)


def fetch_us(fetch_symbol: str) -> pd.DataFrame:
    """美股指数/ETF 全历史（yfinance，auto_adjust）。"""
    import yfinance as yf

    hist = yf.Ticker(fetch_symbol).history(period="max", auto_adjust=True)
    hist.index = pd.to_datetime(hist.index).tz_localize(None)
    return hist[["Open", "Close"]].astype(float).rename(
        columns={"Open": "open", "Close": "close"}
    )


def rebuild_cn_breadth() -> None:
    src = CACHE_ROOT / "a_share_klines_full.parquet"
    if not src.exists():
        raise FileNotFoundError(
            f"缺少 {src}，请先运行 scripts/backfill_breadth_full.py --market cn"
        )
    wide = pd.read_parquet(src)
    out = compute_breadth_from_close_matrix(wide)
    _save(out, TIMING_CACHE_DIR / "breadth_cn_all.parquet")


def rebuild_us_breadth() -> None:
    src = CACHE_ROOT / "sp500_ma_breadth_history.json"
    if not src.exists():
        raise FileNotFoundError(
            f"缺少 {src}，请先运行 scripts/backfill_breadth_full.py --market us"
        )
    rows = json.loads(src.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows, index=pd.to_datetime([r["date"] for r in rows]))
    df = df[["breadth_20", "breadth_50", "breadth_200"]].astype(float).rename(
        columns={"breadth_20": "b20", "breadth_50": "b50", "breadth_200": "b200"}
    )
    _save(df, TIMING_CACHE_DIR / "breadth_sp500.parquet")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["a", "us", "breadth"], default=None)
    ap.add_argument("--refresh", action="store_true", help="已存在文件也强制重拉")
    args = ap.parse_args()

    TIMING_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for symbol, spec in INSTRUMENTS.items():
        if args.only == "breadth":
            break
        if args.only == "a" and spec.market != "cn":
            continue
        if args.only == "us" and spec.market != "us":
            continue
        dest = TIMING_CACHE_DIR / spec.data_file
        if dest.exists() and not args.refresh:
            logger.info("跳过已存在 %s（--refresh 强制重拉）", dest.name)
            continue
        try:
            if spec.source == "ak_index":
                df = fetch_a_index(spec.fetch_symbol)
            elif spec.source == "ak_etf":
                df = fetch_a_etf(spec.fetch_symbol)
            else:
                df = fetch_us(spec.fetch_symbol)
            _save(df, dest)
        except Exception:
            logger.exception("拉取 %s(%s) 失败", symbol, spec.name)

    if args.only in (None, "breadth", "a"):
        logger.info("重算全A B20/B50/B200 长历史 …")
        rebuild_cn_breadth()
    if args.only in (None, "breadth", "us"):
        logger.info("转换 SP500 宽度历史 …")
        rebuild_us_breadth()
    logger.info("完成。目录：%s", TIMING_CACHE_DIR)


if __name__ == "__main__":
    main()
