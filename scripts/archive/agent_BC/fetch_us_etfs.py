#!/usr/bin/env python3
"""任务 BC（前置）：美股核心 ETF 池数据抓取 · 名单与校验跑前写死。

【标的池（跑前固化，2026-09-04）】8 只核心美股 ETF + 2 只基准指数：
  SPY(标普500大盘) QQQ(纳指100) DIA(道指) IWM(小盘罗素2000)
  XLK(科技) XLF(金融) XLV(医疗) XLE(能源) + ^GSPC ^IXIC（基准时钟用）
  名单按"当前市场规模/流动性"挑选——美股核心 ETF 不存在 A 股个股式的
  幸存者偏差挑选问题（行业 ETF 按行业覆盖选取，非按历史表现），但仍在
  报告登记"按当前 prominence 挑选"的轻微选择偏差。

【抓取】yfinance auto_adjust 日线（复权 OHLC，与 AD/AJ 任务的既有先例同源
同一方式），落盘本任务池目录（不动共享缓存）：
  docs/experiments/raw/agent_BC/pool/{sym}.bars.parquet
  schema 与 AQ 池一致：小写列 open/close/high/low/volume + DatetimeIndex。

【交叉校验（跑前写死）】
  X1 抓取的 ^GSPC 收益 vs timing 缓存 ^GSPC（1927 起，未复权指数口径同源）
     ——重叠段日收益相关须 ≥0.995，否则数据可疑。
  X2 SPY 日收益 vs ^GSPC 日收益相关须 ≥0.99（ETF 跟踪指数的天然摩擦）。
  X3 QQQ 日收益 vs ^IXIC 日收益相关须 ≥0.99。
  其余 6 只 ETF 无独立第二源，单一源声明如实登记。
  任一校验不过 → 停止，报告数据不足，不得带病进回测。

输出：docs/experiments/raw/agent_BC/pool_manifest.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
POOL_DIR = REPO / "docs/experiments/raw/agent_BC/pool"
MANIFEST = REPO / "docs/experiments/raw/agent_BC/pool_manifest.json"
TIMING = Path.home() / ".lei_signal_lab/cache/timing"

POOL: tuple[tuple[str, str], ...] = (
    ("SPY", "标普500 ETF"), ("QQQ", "纳指100 ETF"), ("DIA", "道指 ETF"),
    ("IWM", "罗素2000 小盘 ETF"), ("XLK", "科技行业 ETF"), ("XLF", "金融行业 ETF"),
    ("XLV", "医疗行业 ETF"), ("XLE", "能源行业 ETF"),
    ("^GSPC", "标普500 指数（基准时钟）"), ("^IXIC", "纳指综合指数（校验用）"),
)


def fetch_one(sym: str) -> pd.DataFrame:
    for attempt in range(3):
        try:
            df = yf.download(sym, auto_adjust=True, progress=False, period="max")
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3)
    if df is None or df.empty:
        raise RuntimeError(f"{sym} 无数据")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def ret_corr(a: pd.Series, b: pd.Series) -> tuple[float, int]:
    j = pd.concat({"a": a, "b": b}, axis=1, join="inner").dropna()
    j = j[(j["a"] != 0) | (j["b"] != 0)]
    return float(j["a"].corr(j["b"])), len(j)


def main() -> None:
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"pool": [], "cross_checks": {}}
    for sym, name in POOL:
        df = fetch_one(sym)
        df.to_parquet(POOL_DIR / f"{sym}.bars.parquet")
        manifest["pool"].append({
            "symbol": sym, "name": name, "rows": int(len(df)),
            "start": str(df.index[0].date()), "end": str(df.index[-1].date()),
        })
        print(f"{sym:>6} {len(df):>6} 根  {df.index[0].date()} -> {df.index[-1].date()}")
        time.sleep(1)

    gspc_new = pd.read_parquet(POOL_DIR / "^GSPC.bars.parquet")["close"]
    gspc_old = pd.read_parquet(TIMING / "^GSPC.parquet")["close"]
    c1, n1 = ret_corr(gspc_new.pct_change(), gspc_old.pct_change())
    spy = pd.read_parquet(POOL_DIR / "SPY.bars.parquet")["close"]
    c2, n2 = ret_corr(spy.pct_change(), gspc_new.pct_change())
    ixic_new = pd.read_parquet(POOL_DIR / "^IXIC.bars.parquet")["close"]
    qqq = pd.read_parquet(POOL_DIR / "QQQ.bars.parquet")["close"]
    c3, n3 = ret_corr(qqq.pct_change(), ixic_new.pct_change())

    manifest["cross_checks"] = {
        "X1_gspc_vs_timingcache": {"corr": round(c1, 5), "overlap_days": n1,
                                   "pass": c1 >= 0.995},
        "X2_spy_vs_gspc": {"corr": round(c2, 5), "overlap_days": n2,
                           "pass": c2 >= 0.99},
        "X3_qqq_vs_ixic": {"corr": round(c3, 5), "overlap_days": n3,
                           "pass": c3 >= 0.99},
        "single_source_declared": ["DIA", "IWM", "XLK", "XLF", "XLV", "XLE"],
    }
    all_pass = all(v["pass"] for v in manifest["cross_checks"].values() if isinstance(v, dict))
    manifest["all_cross_checks_pass"] = all_pass
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps(manifest["cross_checks"], ensure_ascii=False, indent=1))
    print("ALL_PASS:", all_pass)


if __name__ == "__main__":
    main()
