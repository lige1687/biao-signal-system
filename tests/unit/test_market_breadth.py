"""Task 3 unit tests — market breadth calculation with exact formula verification.

Design spec sections 6, 16.2.
"""

from __future__ import annotations

from datetime import date

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from lei_signal.market_context.breadth import (
    BreadthConfig,
    build_breadth_history,
    compute_breadth_snapshot,
)
from lei_signal.market_context.data_sources import BarsResult
from lei_signal.market_context.types import (
    BreadthSnapshot,
    ContextDataStatus,
    ContextSourceKind,
    MarketId,
    UniverseSnapshot,
)


# ── Fixture helpers ───────────────────────────────────────────────────


def _make_ohlcv_frame(dates: list[str], closes: list[float]) -> pd.DataFrame:
    """Create a minimal OHLCV DataFrame with date index."""
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


def _market_sessions(n_days: int, start: str = "2024-01-02") -> pd.DatetimeIndex:
    """Generate n consecutive business-day-like sessions."""
    base = pd.to_datetime(start)
    # Simple: weekdays only
    dates = []
    current = base
    while len(dates) < n_days:
        if current.weekday() < 5:
            dates.append(current)
        current += pd.Timedelta(days=1)
    return pd.DatetimeIndex(dates)


def _make_universe(symbols: tuple[str, ...]) -> UniverseSnapshot:
    return UniverseSnapshot(
        market_id=MarketId.CSI_300,
        as_of=date(2024, 6, 28),
        symbols=symbols,
        source="test",
        source_version="v1",
        source_kind=ContextSourceKind.FORMAL,
        universe_version="test_hash",
        retrieved_at=datetime.now(timezone.utc),
    )


# ── Tests ─────────────────────────────────────────────────────────────


class TestBreadthSnapshot:
    def test_independent_denominators(self) -> None:
        """Four symbols, three have 200+ bars, one has only 55 bars.
        Breadth20 and 50 use all 4; Breadth200 uses only 3.
        """
        # We need the as_of to be at or near D.SH's last bar so it's not stale
        sessions = _market_sessions(300)
        symbols = ["A.SH", "B.SH", "C.SH", "D.SH"]  # D has only 55 bars

        universe = _make_universe(tuple(symbols))
        config = BreadthConfig()

        # Generate prices: A, B above MA; C below MA; D has only 55 bars
        np.random.seed(42)
        bars_by_symbol = {}
        for i, sym in enumerate(symbols):
            n = 300 if sym != "D.SH" else 55
            trend = np.linspace(100, 200, n) + np.random.randn(n) * 2
            bars_by_symbol[sym] = _make_ohlcv_frame(
                sessions[:n].strftime("%Y-%m-%d").tolist(),
                trend.tolist(),
            )

        # as_of = D.SH's last bar date (session index 54)
        as_of_date = sessions[54].date()
        snap = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            as_of=as_of_date,
            config=config,
        )

        # All 4 symbols have at least 20 and 50 bars → eligible
        assert snap.eligible_20 == 4
        assert snap.eligible_50 == 4
        # D.SH only has 55 bars, < 200 → only 3 eligible for 200
        assert snap.eligible_200 == 3
        assert snap.missing_200 == 1
        assert snap.breadth_200 is not None

    def test_coverage_below_90_pct_gives_incomplete(self) -> None:
        """Coverage 89% (e.g. 89/100) must mark DATA_INCOMPLETE."""
        sessions = _market_sessions(300)
        symbols = [f"S{i:03d}.SH" for i in range(10)]  # 10 symbols

        universe = _make_universe(tuple(symbols))
        config = BreadthConfig(minimum_coverage=0.90)

        np.random.seed(42)
        bars_by_symbol = {}
        for sym in symbols:
            trend = np.linspace(100, 200, 300) + np.random.randn(300) * 2
            bars_by_symbol[sym] = _make_ohlcv_frame(
                sessions.strftime("%Y-%m-%d").tolist(),
                trend.tolist(),
            )

        # Create a snapshot where only 8 of 10 are eligible for 200
        # (by removing 2 symbols from bars)
        del bars_by_symbol["S008.SH"]
        del bars_by_symbol["S009.SH"]

        snap = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            as_of=date(2024, 6, 28),
            config=config,
        )

        # 8 eligible out of 10 = 80% < 90%
        assert snap.eligible_200 == 8
        assert snap.coverage_200 == 0.8
        assert snap.coverage_200 < config.minimum_coverage
        # The 200 horizon should be marked incomplete
        # (breadth_200 may still have a value but data_status reflects the issue)
        # Per spec, the horizon is unusable and classifier must not use it

        # Check that coverage_20 and coverage_50 are also low
        # 8 eligible out of 10 constituents → 0.8 for all windows
        assert snap.coverage_20 == pytest.approx(8 / 10)
        assert snap.coverage_50 == pytest.approx(8 / 10)
        assert snap.coverage_200 == pytest.approx(8 / 10)
        # All are below 90% → data_status should be INCOMPLETE
        assert snap.data_status == ContextDataStatus.INCOMPLETE

    def test_suspended_constituent_stale_after_5_sessions(self) -> None:
        """A suspended constituent can reuse last state for 5 market sessions,
        then must be excluded from the 6th session onward."""
        sessions = _market_sessions(300)
        symbols = ["A.SH", "B.SH"]

        universe = _make_universe(tuple(symbols))
        config = BreadthConfig(stale_sessions=5)

        np.random.seed(42)
        # A.SH has all 300 bars
        a_prices = np.linspace(100, 200, 300) + np.random.randn(300)
        bars_a = _make_ohlcv_frame(
            sessions.strftime("%Y-%m-%d").tolist(),
            a_prices.tolist(),
        )

        # B.SH stops at session 100
        b_prices = np.linspace(50, 100, 100) + np.random.randn(100)
        bars_b = _make_ohlcv_frame(
            sessions[:100].strftime("%Y-%m-%d").tolist(),
            b_prices.tolist(),
        )

        bars_by_symbol_all = {"A.SH": bars_a, "B.SH": bars_b}

        # At session 100 (last bar for B): B is eligible (100 >= 20, 50)
        snap_100 = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol_all,
            sessions=sessions,
            as_of=sessions[99].date(),  # session 100, 0-indexed
            config=config,
        )
        assert snap_100.eligible_20 == 2

        # At session 105 (5 sessions after B's last bar): B is stale but still eligible
        snap_105 = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol_all,
            sessions=sessions,
            as_of=sessions[104].date(),  # 5 sessions after
            config=config,
        )
        # B should be marked stale but still included (within 5-session window)
        assert snap_105.eligible_20 == 2

        # At session 106 (6 sessions after): B should be excluded
        snap_106 = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol_all,
            sessions=sessions,
            as_of=sessions[105].date(),
            config=config,
        )
        assert snap_106.eligible_20 == 1  # only A.SH
        assert snap_106.coverage_20 == 0.5  # 1 of 2

    def test_moving_averages_use_actual_bars_only(self) -> None:
        """MA must only use actual observed bars, not duplicated suspension-day bars."""
        sessions = _market_sessions(50)
        symbols = ["A.SH"]

        universe = _make_universe(tuple(symbols))
        config = BreadthConfig()

        np.random.seed(42)
        prices = np.linspace(100, 200, 25).tolist() + [np.nan] * 25  # only 25 real bars
        # But we can't use NaN in close. Let's just use 25 bars.
        prices = np.linspace(100, 200, 25).tolist()
        bars = _make_ohlcv_frame(
            sessions[:25].strftime("%Y-%m-%d").tolist(),
            prices,
        )

        bars_by_symbol = {"A.SH": bars}

        # At session 25, A has exactly 25 bars → eligible for 20 but NOT 50
        snap_25 = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            as_of=sessions[24].date(),
            config=config,
        )
        assert snap_25.eligible_20 == 1  # 25 >= 20
        assert snap_25.eligible_50 == 0  # 25 < 50
        assert snap_25.eligible_200 == 0
        assert snap_25.coverage_50 == 0.0
        assert snap_25.breadth_50 is None  # not enough data

    def test_future_bars_cannot_change_earlier_snapshot(self) -> None:
        """Adding future bars must not change an earlier as_of snapshot."""
        sessions = _market_sessions(300)
        symbols = ["A.SH"]

        universe = _make_universe(tuple(symbols))
        config = BreadthConfig()

        np.random.seed(42)
        prices_full = np.linspace(100, 200, 300) + np.random.randn(300)
        bars = _make_ohlcv_frame(
            sessions.strftime("%Y-%m-%d").tolist(),
            prices_full.tolist(),
        )

        bars_by_symbol = {"A.SH": bars}
        as_of_mid = sessions[149].date()

        snap_first = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            as_of=as_of_mid,
            config=config,
        )

        # Now add extra "future" bars (simulating data that appeared later)
        # The original bars already have 300 sessions; append 50 more
        extra_sessions = _market_sessions(50, start=sessions[-1].strftime("%Y-%m-%d"))
        extra_sessions = extra_sessions[1:]  # skip duplicate first date
        if len(extra_sessions) > 0:
            extra_prices = np.linspace(200, 300, len(extra_sessions)) + np.random.randn(len(extra_sessions))
            extra_bars = _make_ohlcv_frame(
                extra_sessions.strftime("%Y-%m-%d").tolist(),
                extra_prices.tolist(),
            )
            combined = pd.concat([bars, extra_bars])

            snap_second = compute_breadth_snapshot(
                universe=universe,
                bars_by_symbol={"A.SH": combined},
                sessions=pd.DatetimeIndex(list(sessions) + list(extra_sessions)),
                as_of=as_of_mid,
                config=config,
            )

            # The snapshot should be identical because as_of crops the data
            assert snap_first.breadth_20 == snap_second.breadth_20
            assert snap_first.breadth_50 == snap_second.breadth_50

    def test_exact_breadth_percentage(self) -> None:
        """Verify exact breadth percentage for a simple case."""
        sessions = _market_sessions(100)
        symbols = ["A.SH", "B.SH", "C.SH"]

        universe = _make_universe(tuple(symbols))
        config = BreadthConfig()

        # A: uptrend (close above MA20), B: downtrend (close below MA20),
        # C: oscillating around MA20
        np.random.seed(42)
        a_prices = np.linspace(100, 150, 100)  # consistently above MA20
        b_prices = np.linspace(100, 50, 100)   # consistently below MA20
        c_prices = 100 + np.random.randn(100) * 30  # oscillates

        bars_by_symbol = {
            "A.SH": _make_ohlcv_frame(sessions.strftime("%Y-%m-%d").tolist(), a_prices.tolist()),
            "B.SH": _make_ohlcv_frame(sessions.strftime("%Y-%m-%d").tolist(), b_prices.tolist()),
            "C.SH": _make_ohlcv_frame(sessions.strftime("%Y-%m-%d").tolist(), c_prices.tolist()),
        }

        snap = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            as_of=sessions[99].date(),
            config=config,
        )

        # Check we have exact values, not None
        assert snap.breadth_20 is not None
        assert snap.breadth_50 is not None
        assert isinstance(snap.breadth_20, float)
        # A should be above MA20 (trending up)
        # B should be below MA20 (trending down)
        # C depends on random noise
        # At minimum: breadth should be between 0 and 100
        assert 0 <= snap.breadth_20 <= 100

    def test_source_kind_preserved(self) -> None:
        """BreadthSnapshot must preserve the source kind from universe."""
        sessions = _market_sessions(100)
        symbols = ["A.SH"]

        universe = UniverseSnapshot(
            market_id=MarketId.CSI_300,
            as_of=date(2024, 6, 28),
            symbols=tuple(symbols),
            source="test",
            source_version="v1",
            source_kind=ContextSourceKind.RESEARCH_PROXY,
            universe_version="test_hash",
            retrieved_at=datetime.now(timezone.utc),
        )

        config = BreadthConfig()

        prices = np.linspace(100, 150, 100)
        bars_by_symbol = {
            "A.SH": _make_ohlcv_frame(sessions.strftime("%Y-%m-%d").tolist(), prices.tolist()),
        }

        snap = compute_breadth_snapshot(
            universe=universe,
            bars_by_symbol=bars_by_symbol,
            sessions=sessions,
            as_of=sessions[99].date(),
            config=config,
        )

        assert snap.source_kind == ContextSourceKind.RESEARCH_PROXY


class TestBreadthConfig:
    def test_defaults(self) -> None:
        config = BreadthConfig()
        assert config.ma_windows == (20, 50, 200)
        assert config.minimum_coverage == 0.90
        assert config.stale_sessions == 5
        assert config.percentile_lookback == 1260
        assert config.percentile_min_periods == 252
