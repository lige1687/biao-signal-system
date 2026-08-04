"""Task 1 unit tests — market context domain types."""

from __future__ import annotations

import pytest

# These imports should fail before implementation, then pass after.
from lei_signal.market_context.types import (
    BreadthSnapshot,
    ContextDataStatus,
    ContextSourceKind,
    ContextSummary,
    MarketContextSnapshot,
    MarketId,
)


class TestMarketId:
    def test_all_required_members_present(self) -> None:
        actual = set(MarketId)
        expected = {
            MarketId.CN_ALL_A,
            MarketId.SSE_50,
            MarketId.CSI_300,
            MarketId.CSI_500,
            MarketId.CSI_1000,
            MarketId.CHINEXT,
            MarketId.STAR_50,
            MarketId.SP500,
            MarketId.NASDAQ_100,
            MarketId.RUSSELL_2000,
        }
        assert actual == expected

    def test_string_identity(self) -> None:
        assert MarketId.CN_ALL_A == "CN_ALL_A"
        assert str(MarketId.SSE_50) == "SSE_50"
        assert MarketId.SP500.value == "SP500"


class TestContextSummary:
    def test_exact_allowed_values(self) -> None:
        assert {item.value for item in ContextSummary} == {
            "tailwind", "neutral", "headwind", "unknown",
        }

    def test_no_buy_sell_or_stage_state(self) -> None:
        values = {item.value for item in ContextSummary}
        forbidden = {"buy", "sell", "hold", "confirmed", "watch", "risk"}
        assert values.isdisjoint(forbidden)


class TestContextSourceKind:
    def test_three_kinds_exist(self) -> None:
        kinds = {ContextSourceKind.FORMAL, ContextSourceKind.EXTERNAL_CHECK, ContextSourceKind.RESEARCH_PROXY}
        assert len(kinds) == 3


class TestContextDataStatus:
    def test_required_statuses(self) -> None:
        required = {"complete", "incomplete", "conflict", "stale", "unavailable"}
        actual = {s.value for s in ContextDataStatus}
        assert required <= actual


class TestBreadthSnapshot:
    def test_frozen_dataclass(self) -> None:
        from datetime import date

        snap = BreadthSnapshot(
            market_id=MarketId.CSI_300,
            as_of=date(2024, 6, 28),
            available_at=date(2024, 6, 28),
            universe_version="abc123",
            constituent_count=300,
            eligible_20=300,
            eligible_50=300,
            eligible_200=290,
            missing_20=0,
            missing_50=0,
            missing_200=10,
            coverage_20=1.0,
            coverage_50=1.0,
            coverage_200=290 / 300,
            breadth_20=65.0,
            breadth_50=55.0,
            breadth_200=45.0,
            source_kind=ContextSourceKind.FORMAL,
            provenance="test",
            data_status=ContextDataStatus.COMPLETE,
        )
        assert snap.coverage_200 == pytest.approx(290 / 300)
        with pytest.raises(Exception):
            snap.coverage_20 = 0.5  # type: ignore[misc]


class TestMarketContextSnapshot:
    def test_does_not_contain_signal_fields(self) -> None:
        """MarketContextSnapshot must not contain structure_id, lifecycle_id, Stage, or RiskState."""
        from dataclasses import fields

        field_names = {f.name for f in fields(MarketContextSnapshot)}
        forbidden = {"structure_id", "lifecycle_id", "opportunity_stage",
                     "risk_state", "stage", "signal_type"}
        assert field_names.isdisjoint(forbidden), f"Found forbidden field in {field_names & forbidden}"

    def test_has_required_snapshot_fields(self) -> None:
        from dataclasses import fields

        field_names = {f.name for f in fields(MarketContextSnapshot)}
        required = {
            "market_id", "as_of", "available_at", "universe_version",
            "breadth_20", "breadth_50", "breadth_200",
            "coverage_20", "coverage_50", "coverage_200",
            "drawdown_from_ath", "long_regime", "heat_state",
            "summary", "reasons", "conflicts",
            "provenance", "data_status",
        }
        assert required <= field_names, f"Missing: {required - field_names}"
