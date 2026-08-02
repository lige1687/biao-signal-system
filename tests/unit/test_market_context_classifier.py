"""Task 4 unit tests — drawdown, breadth events, direction, and summary.

Design spec sections 7, 8, 9, 11.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from lei_signal.market_context.classifier import (
    BreadthDirection,
    ContextSummary,
    HeatState,
    LongRegime,
    classify_breadth,
)
from lei_signal.market_context.drawdown import compute_drawdown
from lei_signal.market_context.types import (
    BreadthSnapshot,
    ContextDataStatus,
    ContextSourceKind,
    MarketId,
)


# ── Fixture helpers ───────────────────────────────────────────────────


def _make_snap(
    breadth_20: float | None = 50.0,
    breadth_50: float | None = 50.0,
    breadth_200: float | None = 50.0,
    coverage_20: float = 1.0,
    coverage_50: float = 1.0,
    coverage_200: float = 1.0,
    market_id: MarketId = MarketId.CSI_300,
    source_kind: ContextSourceKind = ContextSourceKind.FORMAL,
    **kwargs,
) -> BreadthSnapshot:
    """Create a BreadthSnapshot with minimal required fields."""
    return BreadthSnapshot(
        market_id=market_id,
        as_of=date(2024, 6, 28),
        available_at=date(2024, 6, 28),
        universe_version="test",
        constituent_count=100,
        eligible_20=100,
        eligible_50=100,
        eligible_200=100,
        missing_20=0,
        missing_50=0,
        missing_200=0,
        coverage_20=coverage_20,
        coverage_50=coverage_50,
        coverage_200=coverage_200,
        breadth_20=breadth_20,
        breadth_50=breadth_50,
        breadth_200=breadth_200,
        source_kind=source_kind,
        provenance="test",
        data_status=ContextDataStatus.COMPLETE,
        **kwargs,
    )


def _make_history(
    dates: list[str],
    breadth_20: list[float],
    breadth_50: list[float],
    breadth_200: list[float],
) -> pd.DataFrame:
    """Create a minimal breadth history DataFrame."""
    df = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "breadth_20": breadth_20,
        "breadth_50": breadth_50,
        "breadth_200": breadth_200,
    })
    df.set_index("date", inplace=True)
    return df


# ── Drawdown tests ────────────────────────────────────────────────────


class TestDrawdown:
    def test_basic_drawdown(self) -> None:
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
        closes = [100.0, 110.0, 95.0, 105.0]
        df = pd.DataFrame({"close": closes}, index=dates)

        # At 2024-01-05: ATH was 110 on 2024-01-03
        dd = compute_drawdown(df, date(2024, 1, 5))
        assert dd.drawdown_from_ath == pytest.approx(105.0 / 110.0 - 1)  # ≈ -0.0455
        assert dd.ath_close == 110.0
        assert dd.current_close == 105.0

    def test_at_all_time_high(self) -> None:
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        closes = [100.0, 110.0, 120.0]
        df = pd.DataFrame({"close": closes}, index=dates)

        dd = compute_drawdown(df, date(2024, 1, 4))
        assert dd.drawdown_from_ath == pytest.approx(0.0)
        assert dd.ath_close == 120.0

    def test_future_highs_not_visible(self) -> None:
        """Future closing highs must not change earlier drawdown."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        closes = [100.0, 80.0, 150.0]  # ATH at the end
        df = pd.DataFrame({"close": closes}, index=dates)

        # At 2024-01-03, the ATH is 100 (not 150)
        dd = compute_drawdown(df, date(2024, 1, 3))
        assert dd.drawdown_from_ath == pytest.approx(80.0 / 100.0 - 1)  # -0.20
        assert dd.ath_close == 100.0

    def test_uses_close_only_not_intraday(self) -> None:
        """Drawdown uses closing highs only, not intraday highs."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        closes = [100.0, 95.0]
        df = pd.DataFrame({"close": closes, "high": [105.0, 96.0]}, index=dates)

        dd = compute_drawdown(df, date(2024, 1, 3))
        # ATH close = 100, current close = 95
        assert dd.drawdown_from_ath == pytest.approx(95.0 / 100.0 - 1)
        assert dd.ath_close == 100.0  # not 105.0


# ── Threshold tests ────────────────────────────────────────────────────


class TestLEIThresholds:
    def test_short_hot_extreme(self) -> None:
        """Breadth20 >= 85 AND Breadth50 >= 85 → short_hot_extreme."""
        snap = _make_snap(breadth_20=85.0, breadth_50=85.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        events = [e.event_type for e in ctx.extreme_events]
        assert "short_hot_extreme" in events

    def test_short_hot_extreme_at_boundary(self) -> None:
        """85.0 is inclusive."""
        snap = _make_snap(breadth_20=85.0, breadth_50=85.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        events = [e.event_type for e in ctx.extreme_events]
        assert "short_hot_extreme" in events

    def test_just_below_short_hot(self) -> None:
        """84.999 is NOT a short hot extreme."""
        snap = _make_snap(breadth_20=84.999, breadth_50=84.999)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        events = [e.event_type for e in ctx.extreme_events]
        assert "short_hot_extreme" not in events

    def test_short_cold_extreme(self) -> None:
        """Breadth20 <= 15 AND Breadth50 <= 15 → short_cold_extreme."""
        snap = _make_snap(breadth_20=15.0, breadth_50=15.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        events = [e.event_type for e in ctx.extreme_events]
        assert "short_cold_extreme" in events

    def test_long_hot_extreme(self) -> None:
        """Breadth50 >= 85 AND Breadth200 >= 85 → long_hot_extreme."""
        snap = _make_snap(breadth_20=80.0, breadth_50=85.0, breadth_200=85.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        events = [e.event_type for e in ctx.extreme_events]
        assert "long_hot_extreme" in events

    def test_long_cold_extreme(self) -> None:
        """Breadth50 <= 15 AND Breadth200 <= 15 → long_cold_extreme."""
        snap = _make_snap(breadth_20=20.0, breadth_50=15.0, breadth_200=15.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        events = [e.event_type for e in ctx.extreme_events]
        assert "long_cold_extreme" in events

    def test_breadth200_exactly_50_is_neither_bull_nor_bear(self) -> None:
        """Breadth200 == 50 is neither bull nor bear."""
        snap = _make_snap(breadth_200=50.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.long_regime == LongRegime.UNKNOWN

    def test_breadth200_above_50_is_bull(self) -> None:
        snap = _make_snap(breadth_200=50.1)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.long_regime == LongRegime.BULL

    def test_breadth200_below_50_is_bear(self) -> None:
        snap = _make_snap(breadth_200=49.9)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.long_regime == LongRegime.BEAR

    def test_ashare_thresholds_marked_research(self) -> None:
        """A-share fixed thresholds must have threshold_origin='lei_threshold_research'."""
        snap = _make_snap(
            breadth_20=85.0,
            breadth_50=85.0,
            market_id=MarketId.CSI_300,
            source_kind=ContextSourceKind.RESEARCH_PROXY,
        )
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        for event in ctx.extreme_events:
            assert event.threshold_origin == "lei_threshold_research", (
                f"Event {event.event_type} should have threshold_origin='lei_threshold_research'"
            )


# ── Summary direction tests ─────────────────────────────────────────────


class TestSummary:
    def test_tailwind(self) -> None:
        """B20 +2, B50 +1 → tailwind."""
        history = _make_history(
            ["2024-06-21"],  # 5 sessions ago (previous observation)
            [48.0], [49.0], [45.0],
        )
        snap = _make_snap(breadth_20=50.0, breadth_50=50.0)
        ctx = classify_breadth(snap, history)
        assert ctx.summary == ContextSummary.TAILWIND
        assert ctx.breadth_direction == BreadthDirection.EXPANDING

    def test_headwind(self) -> None:
        """B20 -2, B50 -1 → headwind."""
        history = _make_history(
            ["2024-06-21"],
            [52.0], [51.0], [45.0],
        )
        snap = _make_snap(breadth_20=50.0, breadth_50=50.0)
        ctx = classify_breadth(snap, history)
        assert ctx.summary == ContextSummary.HEADWIND
        assert ctx.breadth_direction == BreadthDirection.CONTRACTING

    def test_neutral_diverging(self) -> None:
        """B20 +2, B50 -1 → neutral / diverging."""
        history = _make_history(
            ["2024-06-21"],
            [48.0], [51.0], [45.0],
        )
        snap = _make_snap(breadth_20=50.0, breadth_50=50.0)
        ctx = classify_breadth(snap, history)
        assert ctx.summary == ContextSummary.NEUTRAL
        assert ctx.breadth_direction == BreadthDirection.DIVERGING

    def test_zero_change_is_diverging(self) -> None:
        """B20 0, B50 +1 → neutral / diverging."""
        history = _make_history(
            ["2024-06-21"],
            [50.0], [49.0], [45.0],
        )
        snap = _make_snap(breadth_20=50.0, breadth_50=50.0)
        ctx = classify_breadth(snap, history)
        assert ctx.summary == ContextSummary.NEUTRAL
        assert ctx.breadth_direction == BreadthDirection.DIVERGING

    def test_coverage_failure_gives_unknown(self) -> None:
        """Coverage below threshold → unknown summary."""
        snap = _make_snap(coverage_20=0.5, coverage_50=0.5)
        # Empty history — any 5-day lookback will fail
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.summary == ContextSummary.UNKNOWN

    def test_breath200_does_not_change_v1_summary(self) -> None:
        """Breadth200 bear regime must not change the v1 summary from tailwind to headwind."""
        history = _make_history(
            ["2024-06-21"],  # 5 sessions ago
            [48.0], [49.0], [30.0],  # Breadth200 was 30 (bear) 5 sessions ago
        )
        snap = _make_snap(breadth_20=50.0, breadth_50=50.0, breadth_200=30.0)
        ctx = classify_breadth(snap, history)
        # Breadth20/50 5-day direction is tailwind
        assert ctx.summary == ContextSummary.TAILWIND, (
            "Breadth200 bear regime should not override v1 tailwind summary"
        )
        # But long_regime should be bear
        assert ctx.long_regime == LongRegime.BEAR
        # And there should be a conflict about the bear regime
        assert any("熊" in c or "bear" in c.lower() for c in ctx.conflicts), (
            f"Expected conflict about bear regime, got: {ctx.conflicts}"
        )


# ── Heat state tests ────────────────────────────────────────────────────


class TestHeatState:
    def test_extreme_cold_by_percentile(self) -> None:
        """Median percentile <= 10 → extreme_cold."""
        snap = _make_snap(
            breadth_20=10.0, breadth_50=10.0,
            percentile_20=5.0, percentile_50=8.0,
        )
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.heat_state == HeatState.EXTREME_COLD

    def test_cold_by_percentile(self) -> None:
        snap = _make_snap(percentile_20=20.0, percentile_50=22.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.heat_state == HeatState.COLD

    def test_extreme_hot_by_percentile(self) -> None:
        snap = _make_snap(percentile_20=92.0, percentile_50=91.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.heat_state == HeatState.EXTREME_HOT

    def test_hot_by_percentile(self) -> None:
        snap = _make_snap(percentile_20=80.0, percentile_50=78.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.heat_state == HeatState.HOT

    def test_neutral_heat(self) -> None:
        snap = _make_snap(percentile_20=50.0, percentile_50=50.0)
        ctx = classify_breadth(snap, _make_history([], [], [], []))
        assert ctx.heat_state == HeatState.NEUTRAL
