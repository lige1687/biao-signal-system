#!/usr/bin/env python3
"""Generate demo market context data for CSI_300 research_proxy demonstration.

Creates:
  - CSI_300 universe membership (current constituents, research_proxy)
  - 300 days of synthetic OHLCV for 10 CSI_300 stocks
  - 300 days of CSI_300 index data

Usage:
  /opt/homebrew/bin/python3.11 scripts/round4_repro/setup_demo_data.py

Then set env vars:
  export LEI_UNIVERSE_ROOT=tests/fixtures/market_context/universes
  export LEI_COMPONENT_BARS_ROOT=tests/fixtures/market_context/component_bars
  export LEI_INDEX_BARS_ROOT=tests/fixtures/market_context/indices
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT / "tests" / "fixtures" / "market_context"

UNIVERSE_DIR = FIXTURES / "universes"
COMPONENT_DIR = FIXTURES / "component_bars"
INDEX_DIR = FIXTURES / "indices"
SENTIMENT_DIR = FIXTURES / "sentiment"

# 10 well-known CSI 300 constituents (real codes)
CSI300_STOCKS = [
    "600519.SH",  # 贵州茅台
    "000858.SZ",  # 五粮液
    "601318.SH",  # 中国平安
    "600036.SH",  # 招商银行
    "000333.SZ",  # 美的集团
    "600276.SH",  # 恒瑞医药
    "000651.SZ",  # 格力电器
    "002415.SZ",  # 海康威视
    "600887.SH",  # 伊利股份
    "300750.SZ",  # 宁德时代
]

N_DAYS = 300
START_DATE = "2024-06-01"


def _make_business_days(n: int, start: str) -> pd.DatetimeIndex:
    base = pd.Timestamp(start)
    dates = []
    current = base
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += pd.Timedelta(days=1)
    return pd.DatetimeIndex(dates)


def _make_ohlcv(dates: pd.DatetimeIndex, base_price: float,
                trend: float = 15.0, volatility: float = 0.02,
                seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV with realistic random walk."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    drift = np.linspace(0, trend, n)
    noise = rng.normal(0, volatility * base_price, n).cumsum()
    closes = base_price + drift + noise
    closes = np.maximum(closes, base_price * 0.5)  # floor

    opens = closes * (1 + rng.normal(0, 0.005, n))
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.01, n)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.01, n)))
    volumes = rng.integers(5_000_000, 50_000_000, n)

    df = pd.DataFrame({
        "date": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })
    return df


def main() -> None:
    print("=" * 60)
    print("Setting up CSI_300 demo data (research_proxy)")
    print("=" * 60)

    # Create directories
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    COMPONENT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    SENTIMENT_DIR.mkdir(parents=True, exist_ok=True)

    dates = _make_business_days(N_DAYS, START_DATE)

    # 1. Universe membership
    print(f"\n1. Creating CSI_300 universe: {len(CSI300_STOCKS)} stocks")
    end_date = dates[-1].strftime("%Y-%m-%d")
    universe_rows = []
    for sym in CSI300_STOCKS:
        universe_rows.append({
            "universe_id": "CSI_300",
            "symbol": sym,
            "effective_from": START_DATE,
            "effective_until": "9999-12-31",
            "source": "demo_current_snapshot",
            "source_version": "2026-08-demo",
            "source_kind": "research_proxy",
        })
    df_universe = pd.DataFrame(universe_rows)
    out = UNIVERSE_DIR / "CSI_300.parquet"
    df_universe.to_parquet(out, index=False)
    print(f"   → {out}")

    # Also make a CN_ALL_A (same stocks for simplicity)
    df_universe["universe_id"] = "CN_ALL_A"
    out_cn = UNIVERSE_DIR / "CN_ALL_A.parquet"
    df_universe.to_parquet(out_cn, index=False)
    print(f"   → {out_cn}")

    # 2. Component bars
    print(f"\n2. Creating component bars for {len(CSI300_STOCKS)} stocks")
    base_prices = {
        "600519.SH": 1600, "000858.SZ": 140, "601318.SH": 45,
        "600036.SH": 38, "000333.SZ": 60, "600276.SH": 45,
        "000651.SZ": 40, "002415.SZ": 32, "600887.SH": 28,
        "300750.SZ": 200,
    }
    for i, sym in enumerate(CSI300_STOCKS):
        base = base_prices.get(sym, 100)
        trend = 10 + i * 2  # different trends for variety
        df = _make_ohlcv(dates, base, trend=trend, seed=42 + i)
        df.to_parquet(COMPONENT_DIR / f"{sym}.parquet", index=False)
    print(f"   → {COMPONENT_DIR}/ (10 parquet files)")

    # 3. Index bars
    print("\n3. Creating CSI_300 index bars")
    idx_df = _make_ohlcv(dates, 3900, trend=200, volatility=0.015, seed=99)
    idx_df.to_parquet(INDEX_DIR / "CSI_300.parquet", index=False)
    # Also CN_ALL_A index (same shape for demo)
    idx_df.to_parquet(INDEX_DIR / "CN_ALL_A.parquet", index=False)
    print(f"   → {INDEX_DIR}/ (2 parquet files)")

    # 4. Compute breadth as a quick sanity check
    print("\n4. Computing breadth for last date...")
    sys.path.insert(0, str(PROJECT / "src"))
    from lei_signal.market_context.breadth import BreadthConfig, compute_breadth_snapshot
    from lei_signal.market_context.classifier import classify_breadth
    from lei_signal.market_context.types import (
        ContextSourceKind,
        MarketId,
        UniverseSnapshot,
    )
    from lei_signal.market_context.universe import LocalUniverseProvider

    provider = LocalUniverseProvider(UNIVERSE_DIR)
    universe_snap = provider.snapshot(MarketId.CSI_300, dates[-1].date())

    # Load bars
    from lei_signal.market_context.data_sources import LocalMarketBarsProvider
    bars_provider = LocalMarketBarsProvider(COMPONENT_DIR, INDEX_DIR)
    bars_result = bars_provider.load_components(
        set(universe_snap.symbols), dates[-1].date()
    )

    snap = compute_breadth_snapshot(
        universe=universe_snap,
        bars_by_symbol=bars_result.bars_by_symbol,
        sessions=dates,
        as_of=dates[-1].date(),
        config=BreadthConfig(),
    )

    # Build history (last 10 days)
    history_records = []
    for d in dates[-10:]:
        as_of_d = d.date()
        us = provider.snapshot(MarketId.CSI_300, as_of_d)
        br = bars_provider.load_components(set(us.symbols), as_of_d)
        s = compute_breadth_snapshot(
            universe=us, bars_by_symbol=br.bars_by_symbol,
            sessions=dates, as_of=as_of_d,
        )
        history_records.append({
            "date": as_of_d,
            "breadth_20": s.breadth_20,
            "breadth_50": s.breadth_50,
            "breadth_200": s.breadth_200,
        })
    history_df = pd.DataFrame(history_records).set_index("date")

    # Classify
    ctx = classify_breadth(snap, history_df)

    print(f"\n   Market: {ctx.market_id.value}")
    print(f"   Breadth20: {ctx.breadth_20:.1f}%")
    print(f"   Breadth50: {ctx.breadth_50:.1f}%")
    print(f"   Breadth200: {ctx.breadth_200:.1f}%")
    print(f"   Coverage: 20={ctx.coverage_20:.1%} 50={ctx.coverage_50:.1%} 200={ctx.coverage_200:.1%}")
    print(f"   Summary: {ctx.summary.value}")
    print(f"   Direction: {ctx.breadth_direction.value}")
    print(f"   Long regime: {ctx.long_regime.value}")
    print(f"   Heat: {ctx.heat_state.value}")
    if ctx.reasons:
        print(f"   Reasons: {', '.join(ctx.reasons)}")
    if ctx.conflicts:
        print(f"   Conflicts: {', '.join(ctx.conflicts)}")

    # Drawdown
    idx_frame = pd.read_parquet(INDEX_DIR / "CSI_300.parquet")
    idx_frame.set_index("date", inplace=True)
    from lei_signal.market_context.drawdown import compute_drawdown
    dd = compute_drawdown(idx_frame, dates[-1].date(), MarketId.CSI_300)
    print(f"   Drawdown: {dd.drawdown_from_ath:.2%} (ATH={dd.ath_close:.0f} on {dd.ath_date})")

    print("\n" + "=" * 60)
    print("DEMO DATA READY")
    print("=" * 60)
    print(f"\nTo use in Streamlit, set environment variables:")
    print(f"  export LEI_UNIVERSE_ROOT={UNIVERSE_DIR}")
    print(f"  export LEI_COMPONENT_BARS_ROOT={COMPONENT_DIR}")
    print(f"  export LEI_INDEX_BARS_ROOT={INDEX_DIR}")
    print(f"  export LEI_SENTIMENT_ROOT={SENTIMENT_DIR}")
    print(f"\nThen restart Streamlit.")
    print(f"\nNote: This is RESEARCH_PROXY data (current constituents backfilled).")
    print(f"Point-in-time historical constituents would be needed for FORMAL.")
    print(f"See ROUND4_DELIVERY_REPORT.md for details.")


if __name__ == "__main__":
    main()
