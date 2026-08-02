"""Task 7 integration tests — market context pipeline end-to-end."""

from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from lei_signal.market_context.breadth import BreadthConfig
from lei_signal.market_context.pipeline import MarketContextRequest, analyze_market_context
from lei_signal.market_context.types import (
    ContextSourceKind,
    ContextSummary,
    MarketId,
    UniverseSnapshot,
)


def _make_ohlcv_frame(dates: list[str], closes: list[float]) -> pd.DataFrame:
    df = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [1000000] * len(closes),
    })
    df.set_index("date", inplace=True)
    return df


def _make_sessions(n: int) -> pd.DatetimeIndex:
    base = pd.to_datetime("2024-01-02")
    dates = []
    current = base
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current)
        current += pd.Timedelta(days=1)
    return pd.DatetimeIndex(dates)


class TestPipeline:
    def test_produces_snapshots_for_csi300_stock(self) -> None:
        """An A-share CSI300 stock gets CN_ALL_A primary + CSI_300 secondary."""
        sessions = _make_sessions(100)
        symbols = ["A.SH", "B.SH", "C.SH"]

        universe = UniverseSnapshot(
            market_id=MarketId.CN_ALL_A,
            as_of=date(2024, 6, 28),
            symbols=tuple(symbols),
            source="test",
            source_version="v1",
            source_kind=ContextSourceKind.FORMAL,
            universe_version="test_hash",
            retrieved_at=datetime.now(timezone.utc),
        )

        np.random.seed(42)
        bars_by_symbol = {}
        for sym in symbols:
            prices = np.linspace(100, 200, 100) + np.random.randn(100) * 2
            bars_by_symbol[sym] = _make_ohlcv_frame(
                sessions.strftime("%Y-%m-%d").tolist(), prices.tolist()
            )

        request = MarketContextRequest(
            symbol="300750.SZ",
            as_of=sessions[99].date(),
            memberships={MarketId.CSI_300, MarketId.CHINEXT},
            universe_snapshot=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            config=BreadthConfig(),
        )

        snapshots = analyze_market_context(request)

        # Should have primary (CN_ALL_A) + secondary (CHINEXT, CSI_300)
        assert len(snapshots) >= 2
        # Primary should be CN_ALL_A
        assert snapshots[0].market_id == MarketId.CN_ALL_A
        # Should produce meaningful values, not unknown
        assert snapshots[0].summary in {
            ContextSummary.TAILWIND, ContextSummary.NEUTRAL,
            ContextSummary.HEADWIND, ContextSummary.UNKNOWN,
        }

    def test_unknown_symbol_produces_incomplete_snapshot(self) -> None:
        """An unknown symbol produces an unknown snapshot."""
        request = MarketContextRequest(
            symbol="UNKNOWN_XYZ",
            as_of=date(2024, 6, 28),
        )

        snapshots = analyze_market_context(request)
        assert len(snapshots) >= 1
        assert snapshots[0].summary == ContextSummary.UNKNOWN

    def test_partial_data_does_not_crash(self) -> None:
        """Missing data should not crash — return unknown snapshots."""
        sessions = _make_sessions(100)

        universe = UniverseSnapshot(
            market_id=MarketId.CSI_300,
            as_of=date(2024, 6, 28),
            symbols=("A.SH",),
            source="test",
            source_version="v1",
            source_kind=ContextSourceKind.FORMAL,
            universe_version="test_hash",
            retrieved_at=datetime.now(timezone.utc),
        )

        # No bars provided — should still produce results
        request = MarketContextRequest(
            symbol="510300.SH",  # CSI300 ETF
            as_of=sessions[99].date(),
            universe_snapshot=universe,
            bars_by_symbol={},  # empty
            sessions=sessions,
            config=BreadthConfig(),
        )

        snapshots = analyze_market_context(request)
        assert len(snapshots) >= 1
        # Missing bars → unknown
        assert snapshots[0].summary == ContextSummary.UNKNOWN
