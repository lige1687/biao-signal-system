"""Task 1 unit tests — reference-market mapping."""

from __future__ import annotations

import pytest

from lei_signal.market_context.mapping import map_reference_markets
from lei_signal.market_context.types import MarketId


class TestMapReferenceMarkets:
    def test_a_share_defaults_to_all_a_and_keeps_secondary_memberships(self) -> None:
        mapping = map_reference_markets(
            "300750.SZ",
            memberships={MarketId.CHINEXT, MarketId.CSI_300},
        )
        assert mapping.primary_market_id is MarketId.CN_ALL_A
        assert set(mapping.secondary_market_ids) == {MarketId.CHINEXT, MarketId.CSI_300}
        assert not mapping.mapping_incomplete

    def test_chinext_etf_uses_tracking_index_as_primary(self) -> None:
        mapping = map_reference_markets("159915.SZ")
        assert mapping.primary_market_id is MarketId.CHINEXT
        assert set(mapping.secondary_market_ids) == {MarketId.CN_ALL_A}
        assert not mapping.mapping_incomplete

    def test_sse50_etf_primary_is_index(self) -> None:
        mapping = map_reference_markets("510050.SH")
        assert mapping.primary_market_id is MarketId.SSE_50
        assert MarketId.CN_ALL_A in mapping.secondary_market_ids

    def test_csi300_etf_primary_is_index(self) -> None:
        mapping = map_reference_markets("510300.SH")
        assert mapping.primary_market_id is MarketId.CSI_300
        assert MarketId.CN_ALL_A in mapping.secondary_market_ids

    def test_csi500_etf_primary_is_index(self) -> None:
        mapping = map_reference_markets("510500.SH")
        assert mapping.primary_market_id is MarketId.CSI_500
        assert MarketId.CN_ALL_A in mapping.secondary_market_ids

    def test_csi1000_etf_primary_is_index(self) -> None:
        mapping = map_reference_markets("512100.SH")
        assert mapping.primary_market_id is MarketId.CSI_1000
        assert MarketId.CN_ALL_A in mapping.secondary_market_ids

    def test_us_stock_with_known_membership(self) -> None:
        mapping = map_reference_markets(
            "AAPL",
            memberships={MarketId.SP500, MarketId.NASDAQ_100},
        )
        assert mapping.primary_market_id is MarketId.SP500
        assert MarketId.NASDAQ_100 in mapping.secondary_market_ids
        assert not mapping.mapping_incomplete

    def test_us_nasdaq_stock_defaults_nasdaq_primary(self) -> None:
        mapping = map_reference_markets(
            "NVDA",
            memberships={MarketId.NASDAQ_100},
        )
        assert mapping.primary_market_id is MarketId.NASDAQ_100
        assert not mapping.mapping_incomplete

    def test_unknown_symbol_marks_incomplete(self) -> None:
        mapping = map_reference_markets("SOME_RANDOM_SYMBOL")
        assert mapping.primary_market_id is None
        assert mapping.mapping_incomplete
        assert "mapping_incomplete" in mapping.reason_cn.lower() or len(mapping.reason_cn) > 0

    def test_us_stock_without_membership_marks_incomplete(self) -> None:
        mapping = map_reference_markets("AAPL", memberships=set())
        assert mapping.primary_market_id is None
        assert mapping.mapping_incomplete

    def test_mapping_is_frozen(self) -> None:
        mapping = map_reference_markets("300750.SZ")
        with pytest.raises(Exception):
            mapping.primary_market_id = MarketId.CSI_300  # type: ignore[misc]

    def test_secondary_market_ids_are_sorted_tuple(self) -> None:
        mapping = map_reference_markets(
            "300750.SZ",
            memberships={MarketId.CSI_300, MarketId.CHINEXT},
        )
        secondary = mapping.secondary_market_ids
        # Must be tuple, sorted by enum definition order
        assert isinstance(secondary, tuple)
        # In MarketId enum: CSI_300 (index 2) defined before CHINEXT (index 5)
        assert secondary.index(MarketId.CSI_300) < secondary.index(MarketId.CHINEXT)

    def test_reason_cn_must_be_string(self) -> None:
        mapping = map_reference_markets("159915.SZ")
        assert isinstance(mapping.reason_cn, str)
        assert len(mapping.reason_cn) > 0
