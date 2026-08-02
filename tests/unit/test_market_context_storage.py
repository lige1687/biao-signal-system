"""Task 6 unit tests — market context storage."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import date, datetime, timezone

from lei_signal.market_context.storage import (
    write_market_context,
    write_sentiment_observations,
)
from lei_signal.market_context.types import (
    BreadthDirection,
    ContextDataStatus,
    ContextSourceKind,
    ContextSummary,
    HeatState,
    LongRegime,
    MarketContextSnapshot,
    MarketId,
    SentimentLabel,
    SentimentObservation,
)
from lei_signal.storage.sqlite_store import apply_migrations


def _make_snapshot(market_id: MarketId = MarketId.CSI_300) -> MarketContextSnapshot:
    return MarketContextSnapshot(
        market_id=market_id,
        as_of=date(2024, 6, 28),
        available_at=date(2024, 6, 28),
        universe_version="abc123",
        breadth_20=65.0,
        breadth_50=55.0,
        breadth_200=45.0,
        coverage_20=1.0,
        coverage_50=1.0,
        coverage_200=0.95,
        constituent_count=300,
        breadth_direction=BreadthDirection.EXPANDING,
        long_regime=LongRegime.BULL,
        heat_state=HeatState.HOT,
        summary=ContextSummary.TAILWIND,
        reasons=("B20/50 expanding",),
        conflicts=("B200 below 50%",),
        source_kind=ContextSourceKind.FORMAL,
        provenance="test",
        data_status=ContextDataStatus.COMPLETE,
    )


class TestMigration:
    def test_migration_006_creates_tables(self) -> None:
        """Migration 006 must create the 5 market context tables."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.row_factory = sqlite3.Row
            apply_migrations(conn)

            # Verify all 5 tables exist
            tables = {row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            expected = {
                "universe_membership_versions",
                "market_breadth_snapshots",
                "market_context_events",
                "sentiment_observations",
                "market_context_assessments",
            }
            assert expected <= tables, f"Missing: {expected - tables}"

    def test_migration_is_idempotent(self) -> None:
        """Running migration 006 twice must not fail."""
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.row_factory = sqlite3.Row
            apply_migrations(conn)
            # Second run must succeed
            apply_migrations(conn)

            tables = {row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            assert "market_breadth_snapshots" in tables


class TestWriteMarketContext:
    def test_round_trip(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.row_factory = sqlite3.Row
            apply_migrations(conn)

            snap = _make_snapshot()
            result = write_market_context(conn, snap, (), run_id="test_run")
            conn.commit()

            assert result["inserted"] == 2  # snapshot + assessment

            # Read back breadth snapshot
            row = conn.execute(
                "SELECT * FROM market_breadth_snapshots WHERE market_id=? AND as_of=?",
                (snap.market_id.value, str(snap.as_of)),
            ).fetchone()
            assert row is not None
            assert row["breadth_20"] == 65.0
            assert row["coverage_20"] == 1.0

            # Read back assessment
            assessment = conn.execute(
                "SELECT * FROM market_context_assessments WHERE market_id=?",
                (snap.market_id.value,),
            ).fetchone()
            assert assessment is not None
            assert assessment["summary"] == "tailwind"
            assert assessment["long_regime"] == "bull"


class TestWriteSentiment:
    def test_writes_and_reads_back(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            conn.row_factory = sqlite3.Row
            apply_migrations(conn)

            obs = SentimentObservation(
                series_id="NAAIM",
                survey_week=date(2024, 6, 10),
                available_at=datetime(2024, 6, 13, 7, 0, tzinfo=timezone.utc),
                source="official",
                license_status="licensed",
                publication_delay_days=3,
                current_eligible=True,
                exposure_index=80.0,
                percentile=50.0,
                label=SentimentLabel.NEUTRAL,
            )

            count = write_sentiment_observations(conn, [obs])
            conn.commit()
            assert count == 1

            row = conn.execute(
                "SELECT * FROM sentiment_observations WHERE series_id='NAAIM'"
            ).fetchone()
            assert row is not None
            assert row["exposure_index"] == 80.0
