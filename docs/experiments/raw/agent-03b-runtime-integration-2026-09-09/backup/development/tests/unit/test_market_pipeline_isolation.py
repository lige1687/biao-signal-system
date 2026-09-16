"""Round 5 A2 + A6: pipeline must serve each market its own data, and
the breadth history it uses for percentiles must be a real-session axis.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from lei_signal.market_context.pipeline import (
    MarketContextRequest,
    analyze_market_context,
)
from lei_signal.market_context.types import (
    ContextDataStatus,
    ContextSourceKind,
    ContextSummary,
    MarketId,
    UniverseSnapshot,
)


class _PerMarketProvider:
    """Test double that records which market_id it was asked about, and serves
    each market only its own data. Replaying a CSI_300 universe to a STAR_50
    call would be a bug — this provider refuses, so the test catches that."""

    def __init__(self, *, data: dict[MarketId, dict]) -> None:
        self._data = data
        self.calls: list[tuple[MarketId, str]] = []

    def universe(self, market_id: MarketId, as_of: date) -> UniverseSnapshot | None:
        self.calls.append((market_id, "universe"))
        return self._data.get(market_id, {}).get("universe")

    def sessions(self, market_id: MarketId) -> pd.DatetimeIndex:
        return self._data.get(market_id, {}).get(
            "sessions", pd.DatetimeIndex([], name="date"),
        )

    def index_bars(self, market_id: MarketId, as_of: date) -> pd.DataFrame:
        self.calls.append((market_id, "index_bars"))
        return self._data.get(market_id, {}).get("index_bars", pd.DataFrame())

    def breadth_history(
        self, market_id: MarketId, *, up_to: date,
    ) -> pd.DataFrame:
        self.calls.append((market_id, "breadth_history"))
        return self._data.get(market_id, {}).get("breadth_history", pd.DataFrame())

    def component_bars(
        self, market_id: MarketId, symbols: tuple[str, ...], as_of: date,
    ) -> dict[str, pd.DataFrame]:
        self.calls.append((market_id, "component_bars"))
        return self._data.get(market_id, {}).get("bars", {})


def _universe(market_id: MarketId, symbols: tuple[str, ...]) -> UniverseSnapshot:
    return UniverseSnapshot(
        market_id=market_id,
        as_of=date(2024, 6, 28),
        symbols=symbols,
        source="test",
        source_version="v1",
        source_kind=ContextSourceKind.RESEARCH_PROXY,
        retrieved_at=datetime(2024, 6, 28, tzinfo=UTC),
        universe_version=f"{market_id.value}-v1",
    )


def _bars(symbol: str, prices: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=len(prices))
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": [1_000_000] * len(prices),
        },
        index=dates,
    )


class TestPipelineDataIsolation:
    def test_each_market_uses_its_own_universe(self) -> None:
        csi300 = _universe(MarketId.CSI_300, ("600000.SS", "600036.SS"))
        star50 = _universe(MarketId.STAR_50, ("688981.SS", "688041.SS"))
        sessions = pd.bdate_range("2024-01-02", periods=120)
        provider = _PerMarketProvider(data={
            MarketId.CSI_300: {
                "universe": csi300, "sessions": sessions,
                "bars": {
                    "600000.SS": _bars("600000.SS", [10.0 + i * 0.1 for i in range(120)]),
                    "600036.SS": _bars("600036.SS", [20.0 + i * 0.2 for i in range(120)]),
                },
            },
            MarketId.STAR_50: {
                "universe": star50, "sessions": sessions,
                "bars": {
                    "688981.SS": _bars("688981.SS", [50.0 + i * 0.5 for i in range(120)]),
                    "688041.SS": _bars("688041.SS", [80.0 + i * 0.3 for i in range(120)]),
                },
            },
            MarketId.CN_ALL_A: {
                "universe": _universe(MarketId.CN_ALL_A, ("600000.SS",)),
                "sessions": sessions,
                "bars": {"600000.SS": _bars("600000.SS", [10.0 + i * 0.1 for i in range(120)])},
            },
        })

        # Use a known dashboard index (000300.SS = 沪深300) so the
        # mapping's "known index" branch picks the first non-CN_ALL_A
        # membership as primary; here CSI_300 wins by enum order.
        req = MarketContextRequest(
            symbol="000300.SS",
            as_of=date(2024, 6, 28),
            memberships={MarketId.CSI_300, MarketId.STAR_50},
            provider=provider,
        )
        snapshots = analyze_market_context(req)

        seen_markets = {snap.market_id for snap in snapshots}
        assert MarketId.CSI_300 in seen_markets
        assert MarketId.STAR_50 in seen_markets

        # CRITICAL: each market must have its OWN constituent count, never
        # a snapshot-wide shared value.
        by_market = {s.market_id: s for s in snapshots}
        assert by_market[MarketId.CSI_300].constituent_count == 2
        assert by_market[MarketId.STAR_50].constituent_count == 2

        # Primary should be the first non-CN_ALL_A membership by enum
        # order — CSI_300 is declared before STAR_50 in MarketId.
        assert snapshots[0].market_id is MarketId.CSI_300

        # The provider must have been queried for each market separately.
        queried_markets = {c[0] for c in provider.calls}
        assert {MarketId.CSI_300, MarketId.STAR_50} <= queried_markets

    def test_secondary_market_with_no_provider_data_is_unknown(self) -> None:
        """When the provider has data for the primary only, secondaries fall
        to an explicit unknown snapshot — they must not silently inherit
        the primary's breadth reading."""
        csi300 = _universe(MarketId.CSI_300, ("600000.SS",))
        sessions = pd.bdate_range("2024-01-02", periods=120)
        provider = _PerMarketProvider(data={
            MarketId.CSI_300: {
                "universe": csi300, "sessions": sessions,
                "bars": {"600000.SS": _bars("600000.SS", [10.0 + i * 0.1 for i in range(120)])},
            },
        })
        req = MarketContextRequest(
            symbol="000001.SZ",
            as_of=date(2024, 6, 28),
            memberships={MarketId.CSI_300, MarketId.STAR_50},
            provider=provider,
        )
        snapshots = analyze_market_context(req)
        by_market = {s.market_id: s for s in snapshots}
        assert by_market[MarketId.CSI_300].breadth_20 is not None
        assert by_market[MarketId.STAR_50].breadth_20 is None
        assert by_market[MarketId.STAR_50].summary is ContextSummary.UNKNOWN
        assert by_market[MarketId.STAR_50].data_status is ContextDataStatus.UNAVAILABLE


class TestBreadthHistoryRealSessions:
    """A6: `breadth_history` is iterated over real sessions, no synthetic
    business-day rows, and percentiles are point-in-time (no future leak)."""

    def test_breadth_history_uses_session_index_not_business_day_range(self) -> None:
        """A history built from the pipeline uses the actual session axis
        provided by the provider; pd.bdate_range would invent sessions
        that never traded."""
        # Real sessions with a weekend + an exchange holiday gap.
        sessions = pd.DatetimeIndex([
            "2024-01-02", "2024-01-03", "2024-01-05",  # weekend
            "2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
        ])
        # Bars covering 200+ sessions so all MA windows are populated.
        n = 220
        bar_dates = pd.bdate_range("2023-01-02", periods=n)
        prices = [10.0 + i * 0.1 for i in range(n)]
        provider = _PerMarketProvider(data={
            MarketId.CSI_300: {
                "universe": _universe(MarketId.CSI_300, ("600000.SS",)),
                "sessions": sessions,
                "bars": {"600000.SS": _bars("600000.SS", prices).set_index(bar_dates)},
                "breadth_history": pd.DataFrame(
                    {"breadth_20": [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0]},
                    index=pd.DatetimeIndex(sessions, name="date"),
                ),
            },
        })
        req = MarketContextRequest(
            symbol="510300.SS",  # 沪深300ETF — primary is CSI_300
            as_of=date(2024, 1, 12),
            memberships={MarketId.CSI_300},
            provider=provider,
        )
        snap = analyze_market_context(req)[0]

        # 5 sessions back from 2024-01-12 = 2024-01-05 (60.0). The
        # synthetic 2024-01-04 / 2024-01-06 rows pd.bdate_range would
        # have inserted must NOT appear here.
        assert snap.market_id is MarketId.CSI_300
        assert snap.breadth_20 == 100.0  # 1/1 constituent above MA20
        # breadth_history[2024-01-05] = 60.0, current = 100.0 → +40
        assert snap.breadth_20_delta_5 == pytest.approx(40.0)
