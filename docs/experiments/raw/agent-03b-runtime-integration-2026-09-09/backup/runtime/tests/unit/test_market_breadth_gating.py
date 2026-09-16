"""Round 5 A3/A4/A6: exact session deltas, per-horizon coverage gating,
point-in-time percentiles, divergence.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lei_signal.market_context.breadth import (
    breadth_delta,
    rolling_percentile_at,
)
from lei_signal.market_context.classifier import classify_breadth
from lei_signal.market_context.types import (
    BreadthDirection,
    BreadthSnapshot,
    ContextDataStatus,
    ContextSummary,
    HeatState,
    LongRegime,
    MarketId,
)


def _history(dates: list[str], b20: list[float], b50: list[float],
             b200: list[float] | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "breadth_20": b20,
            "breadth_50": b50,
            "breadth_200": b200 if b200 is not None else [50.0] * len(b20),
            "coverage_20": [1.0] * len(b20),
            "coverage_50": [1.0] * len(b20),
            "coverage_200": [1.0] * len(b20),
        },
        index=pd.DatetimeIndex([pd.Timestamp(d) for d in dates], name="date"),
    )
    return frame


def _snapshot(
    *,
    as_of: date = date(2024, 6, 20),
    b20: float | None = 60.0,
    b50: float | None = 55.0,
    b200: float | None = 52.0,
    cov20: float = 1.0,
    cov50: float = 1.0,
    cov200: float = 1.0,
    p20: float | None = None,
    p50: float | None = None,
    market_id: MarketId = MarketId.CSI_300,
) -> BreadthSnapshot:
    return BreadthSnapshot(
        market_id=market_id,
        as_of=as_of,
        available_at=as_of,
        universe_version="v-test",
        constituent_count=10,
        eligible_20=10, eligible_50=10, eligible_200=10,
        missing_20=0, missing_50=0, missing_200=0,
        coverage_20=cov20, coverage_50=cov50, coverage_200=cov200,
        breadth_20=b20, breadth_50=b50, breadth_200=b200,
        percentile_20=p20, percentile_50=p50,
    )


class TestExactSessionDelta:
    """A3: 5/20-day change must use the exact prior trading session,
    never `history.iloc[-1]`."""

    def test_delta_uses_exact_nth_prior_session(self) -> None:
        dates = [f"2024-06-{d:02d}" for d in (3, 4, 5, 6, 7, 10, 11)]
        hist = _history(dates, b20=[10, 20, 30, 40, 50, 60, 70],
                        b50=[10, 20, 30, 40, 50, 60, 70])
        # current as_of = 2024-06-11 (value 70). 5 sessions before = 2024-06-04 (20).
        delta = breadth_delta(hist, "breadth_20", as_of=date(2024, 6, 11), sessions_back=5)
        assert delta == pytest.approx(70.0 - 20.0)

    def test_delta_is_none_when_not_enough_sessions(self) -> None:
        dates = ["2024-06-03", "2024-06-04", "2024-06-05"]
        hist = _history(dates, b20=[10, 20, 30], b50=[10, 20, 30])
        assert breadth_delta(hist, "breadth_20", as_of=date(2024, 6, 5), sessions_back=5) is None

    def test_delta_never_uses_last_row_as_proxy(self) -> None:
        """Regression: last row is 1 session back, not 5 — must not be used."""
        dates = [f"2024-06-{d:02d}" for d in (3, 4, 5, 6, 7, 10)]
        hist = _history(dates, b20=[10, 11, 12, 13, 14, 99],
                        b50=[10, 11, 12, 13, 14, 99])
        # as_of = 2024-06-10 (99); 5 back = 2024-06-03 (10) → 89, not 99-14=85
        assert breadth_delta(hist, "breadth_20", as_of=date(2024, 6, 10),
                             sessions_back=5) == pytest.approx(89.0)

    def test_delta_is_none_when_as_of_absent_from_history(self) -> None:
        dates = ["2024-06-03", "2024-06-04"]
        hist = _history(dates, b20=[10, 20], b50=[10, 20])
        assert breadth_delta(hist, "breadth_20", as_of=date(2024, 7, 1),
                             sessions_back=1) is None


class TestPointInTimePercentile:
    """A6: percentile uses only observations up to and including as_of."""

    def test_percentile_ignores_future_observations(self) -> None:
        dates = pd.bdate_range("2020-01-01", periods=400)
        values = pd.Series(range(400), index=dates, dtype=float)
        as_of = dates[300].date()
        pct = rolling_percentile_at(values, as_of=as_of, lookback=1260, min_periods=252)
        # value at position 300 is the max of everything visible → 100th pct
        assert pct == pytest.approx(100.0)

    def test_percentile_unknown_below_min_periods(self) -> None:
        dates = pd.bdate_range("2020-01-01", periods=100)
        values = pd.Series(range(100), index=dates, dtype=float)
        assert rolling_percentile_at(values, as_of=dates[-1].date(),
                                     lookback=1260, min_periods=252) is None

    def test_appending_future_rows_does_not_change_past_percentile(self) -> None:
        dates = pd.bdate_range("2020-01-01", periods=400)
        values = pd.Series(range(400), index=dates, dtype=float)
        as_of = dates[300].date()
        before = rolling_percentile_at(values, as_of=as_of, lookback=1260, min_periods=252)

        extra = pd.bdate_range(dates[-1] + pd.Timedelta(days=1), periods=100)
        grown = pd.concat([values, pd.Series([9999.0] * 100, index=extra)])
        after = rolling_percentile_at(grown, as_of=as_of, lookback=1260, min_periods=252)
        assert before == after


class TestPerHorizonCoverageGating:
    """A4: coverage is gated per 20/50/200 horizon independently."""

    def test_low_200_coverage_does_not_block_20_50_summary(self) -> None:
        dates = [f"2024-06-{d:02d}" for d in (3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 17)]
        hist = _history(dates, b20=[50.0] * 11, b50=[50.0] * 11)
        snap = _snapshot(as_of=date(2024, 6, 18), b20=60.0, b50=60.0,
                         cov200=0.10)
        hist.loc[pd.Timestamp("2024-06-18")] = {
            "breadth_20": 60.0, "breadth_50": 60.0, "breadth_200": 52.0,
            "coverage_20": 1.0, "coverage_50": 1.0, "coverage_200": 0.1,
        }
        ctx = classify_breadth(snap, hist)
        assert ctx.summary is ContextSummary.TAILWIND
        assert ctx.long_regime is LongRegime.UNKNOWN  # 200 horizon gated out

    def test_low_200_coverage_suppresses_long_extreme_events(self) -> None:
        snap = _snapshot(b50=10.0, b200=10.0, cov200=0.5)
        ctx = classify_breadth(snap, pd.DataFrame())
        types = {e.event_type for e in ctx.extreme_events}
        assert "long_cold_extreme" not in types

    def test_low_20_coverage_suppresses_short_extreme_events(self) -> None:
        snap = _snapshot(b20=10.0, b50=10.0, cov20=0.5)
        ctx = classify_breadth(snap, pd.DataFrame())
        types = {e.event_type for e in ctx.extreme_events}
        assert "short_cold_extreme" not in types

    def test_low_coverage_marks_horizon_incomplete_not_neutral(self) -> None:
        snap = _snapshot(cov20=0.5)
        ctx = classify_breadth(snap, pd.DataFrame())
        assert ctx.summary is ContextSummary.UNKNOWN
        assert ctx.data_status is ContextDataStatus.INCOMPLETE
        assert any("覆盖" in c for c in ctx.conflicts)

    def test_low_coverage_never_produces_cold_heat(self) -> None:
        snap = _snapshot(b20=5.0, b50=5.0, cov20=0.4, cov50=0.4)
        ctx = classify_breadth(snap, pd.DataFrame())
        assert ctx.heat_state is HeatState.UNKNOWN


class TestBreadthDivergence:
    """A3: 20-session divergence between index return and breadth."""

    def _hist_25(self, b20_start: float, b20_end: float,
                 b50_start: float, b50_end: float) -> pd.DataFrame:
        dates = pd.bdate_range("2024-06-03", periods=21)
        b20 = list(pd.Series([b20_start] * 20 + [b20_end]))
        b50 = list(pd.Series([b50_start] * 20 + [b50_end]))
        return _history([str(d.date()) for d in dates], b20=b20, b50=b50)

    def _index(self, first: float, last: float) -> pd.DataFrame:
        dates = pd.bdate_range("2024-06-03", periods=21)
        closes = [first] * 20 + [last]
        return pd.DataFrame({"close": closes}, index=dates)

    def test_negative_divergence_index_up_breadth_down(self) -> None:
        hist = self._hist_25(60.0, 40.0, 60.0, 45.0)
        as_of = hist.index[-1].date()
        snap = _snapshot(as_of=as_of, b20=40.0, b50=45.0)
        ctx = classify_breadth(snap, hist, index_bars=self._index(100.0, 110.0))
        assert "negative_breadth_divergence" in {e.event_type for e in ctx.divergence_events}

    def test_positive_divergence_index_down_breadth_up(self) -> None:
        hist = self._hist_25(40.0, 60.0, 45.0, 60.0)
        as_of = hist.index[-1].date()
        snap = _snapshot(as_of=as_of, b20=60.0, b50=60.0)
        ctx = classify_breadth(snap, hist, index_bars=self._index(110.0, 100.0))
        assert "positive_breadth_divergence" in {e.event_type for e in ctx.divergence_events}

    def test_no_divergence_when_directions_agree(self) -> None:
        hist = self._hist_25(40.0, 60.0, 45.0, 60.0)
        as_of = hist.index[-1].date()
        snap = _snapshot(as_of=as_of, b20=60.0, b50=60.0)
        ctx = classify_breadth(snap, hist, index_bars=self._index(100.0, 110.0))
        assert ctx.divergence_events == ()

    def test_no_divergence_without_index_bars(self) -> None:
        hist = self._hist_25(60.0, 40.0, 60.0, 45.0)
        as_of = hist.index[-1].date()
        snap = _snapshot(as_of=as_of, b20=40.0, b50=45.0)
        ctx = classify_breadth(snap, hist)
        assert ctx.divergence_events == ()

    def test_zero_index_return_produces_no_divergence(self) -> None:
        hist = self._hist_25(60.0, 40.0, 60.0, 45.0)
        as_of = hist.index[-1].date()
        snap = _snapshot(as_of=as_of, b20=40.0, b50=45.0)
        ctx = classify_breadth(snap, hist, index_bars=self._index(100.0, 100.0))
        assert ctx.divergence_events == ()


class TestSummaryUsesExactFiveSessionDelta:
    def test_tailwind_requires_both_deltas_positive(self) -> None:
        dates = [str(d.date()) for d in pd.bdate_range("2024-06-03", periods=7)]
        hist = _history(dates, b20=[10, 20, 30, 40, 50, 60, 70],
                        b50=[10, 20, 30, 40, 50, 60, 70])
        as_of = pd.Timestamp(dates[-1]).date()
        snap = _snapshot(as_of=as_of, b20=70.0, b50=70.0)
        ctx = classify_breadth(snap, hist)
        assert ctx.summary is ContextSummary.TAILWIND
        assert ctx.breadth_direction is BreadthDirection.EXPANDING
        assert ctx.breadth_20_delta_5 == pytest.approx(50.0)

    def test_unknown_when_five_sessions_unavailable(self) -> None:
        dates = [str(d.date()) for d in pd.bdate_range("2024-06-03", periods=3)]
        hist = _history(dates, b20=[10, 20, 30], b50=[10, 20, 30])
        as_of = pd.Timestamp(dates[-1]).date()
        snap = _snapshot(as_of=as_of, b20=30.0, b50=30.0)
        ctx = classify_breadth(snap, hist)
        assert ctx.summary is ContextSummary.UNKNOWN
        assert ctx.breadth_direction is BreadthDirection.UNKNOWN
