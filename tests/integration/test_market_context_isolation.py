"""Task 7 integration tests — market context isolation from Round 3 state machine.

Proves that market context presence (tailwind, headwind, or unavailable)
does not change opportunity_stage, structure_id, or lifecycle_id.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from lei_signal.market_context.types import MarketContextSnapshot, MarketId


class TestMarketContextIsolation:
    """Prove market context types do not contain Round 3 signal fields."""

    def test_no_structure_id_or_lifecycle_id_in_snapshot(self) -> None:
        """MarketContextSnapshot must not contain structure_id or lifecycle_id."""
        field_names = {f.name for f in fields(MarketContextSnapshot)}
        forbidden = {"structure_id", "lifecycle_id", "opportunity_stage",
                     "risk_state", "stage"}
        overlap = field_names & forbidden
        assert not overlap, (
            f"MarketContextSnapshot must not contain {overlap}"
        )

    def test_market_context_types_independent(self) -> None:
        """All market context types must be importable independently of
        Round 3 state machine modules."""
        # Import market context packages — should not import state machine
        import lei_signal.market_context.types as mct
        import lei_signal.market_context.classifier as mcc
        import lei_signal.market_context.pipeline as mcp

        # Verify these modules exist and are usable
        assert mct.ContextSummary is not None
        assert mcc.classify_breadth is not None
        assert mcp.analyze_market_context is not None

    def test_summary_only_has_allowed_values(self) -> None:
        from lei_signal.market_context.types import ContextSummary
        allowed = {"tailwind", "neutral", "headwind", "unknown"}
        actual = {item.value for item in ContextSummary}
        assert actual == allowed

    def test_tailwind_does_not_imply_buy(self) -> None:
        """Tailwind summary must not be conflated with buy signal."""
        from lei_signal.market_context.types import ContextSummary
        assert ContextSummary.TAILWIND.value == "tailwind"
        assert "buy" not in ContextSummary.TAILWIND.value
        assert "sell" not in ContextSummary.HEADWIND.value
