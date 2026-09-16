"""Round 5 A1: STAR_50 must be its own market, never proxied by SSE_50."""

from __future__ import annotations

import pytest

from lei_signal.market_context.mapping import (
    map_reference_markets,
    to_repo_symbol,
)
from lei_signal.market_context.types import MarketId


class TestStar50Market:
    def test_star_50_is_a_declared_market(self) -> None:
        assert MarketId.STAR_50.value == "STAR_50"

    @pytest.mark.parametrize("symbol", ["588000.SS", "588000.SH", "588080.SH", "588080.SS"])
    def test_star_etfs_map_to_star_50_not_sse_50(self, symbol: str) -> None:
        mapping = map_reference_markets(symbol)
        assert mapping.primary_market_id is MarketId.STAR_50
        assert MarketId.SSE_50 not in mapping.secondary_market_ids
        assert MarketId.SSE_50 is not mapping.primary_market_id

    def test_sse_50_etf_still_maps_to_sse_50(self) -> None:
        mapping = map_reference_markets("510050.SH")
        assert mapping.primary_market_id is MarketId.SSE_50

    def test_star_50_is_an_a_share_market(self) -> None:
        from lei_signal.market_context.mapping import A_SHARE_MARKETS

        assert MarketId.STAR_50 in A_SHARE_MARKETS


class TestRepoSymbolCanonicalization:
    """The repository's canonical Shanghai suffix is `.SS` (resolve_symbol)."""

    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("600519.SH", "600519.SS"),
            ("600519.SS", "600519.SS"),
            ("588000.SH", "588000.SS"),
            ("300750.SZ", "300750.SZ"),
            ("AAPL", "AAPL"),
        ],
    )
    def test_to_repo_symbol(self, given: str, expected: str) -> None:
        assert to_repo_symbol(given) == expected

    def test_repo_symbol_resolves_as_a_share(self) -> None:
        from lei_signal.data.symbols import is_a_share, resolve_symbol

        assert is_a_share(resolve_symbol(to_repo_symbol("600519.SH")))
