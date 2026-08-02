"""Market context persistence — Round 4.

Independent storage for market context data: universe membership versions,
breadth snapshots, context events, sentiment observations, and context
assessments. Does NOT write to signal_events or daily_assessments tables.

Design spec section 13, 16.3.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime

from lei_signal.market_context.types import (
    MarketContextEvent,
    MarketContextSnapshot,
    MarketId,
    SentimentObservation,
)


def _serialize_reasons(reasons: tuple[str, ...]) -> str:
    return json.dumps(list(reasons), ensure_ascii=False)


def _deserialize_reasons(json_str: str) -> tuple[str, ...]:
    if not json_str:
        return ()
    return tuple(json.loads(json_str))


def write_market_context(
    connection: sqlite3.Connection,
    snapshot: MarketContextSnapshot,
    events: Sequence[MarketContextEvent],
    *,
    run_id: str,
) -> dict:
    """Write a market context snapshot and its events to the database.

    Uses INSERT OR REPLACE for snapshots (latest wins per market_id + as_of)
    and INSERT OR IGNORE for events (idempotent by event identity).

    Args:
        connection: SQLite connection with migrations applied.
        snapshot: The complete market context snapshot.
        events: Associated market context events.
        run_id: Analysis run identifier.

    Returns:
        Dict with counts of inserted records.
    """
    inserted = 0

    # 1. Write breadth snapshot (from MarketContextSnapshot fields)
    connection.execute(
        """INSERT OR REPLACE INTO market_breadth_snapshots (
            market_id, as_of, available_at, universe_version,
            constituent_count, eligible_20, eligible_50, eligible_200,
            missing_20, missing_50, missing_200,
            coverage_20, coverage_50, coverage_200,
            breadth_20, breadth_50, breadth_200,
            percentile_20, percentile_50, percentile_200,
            source_kind, provenance, data_status, run_id
        ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snapshot.market_id.value, str(snapshot.as_of), str(snapshot.available_at),
            snapshot.universe_version,
            snapshot.constituent_count,
            snapshot.coverage_20, snapshot.coverage_50, snapshot.coverage_200,
            snapshot.breadth_20, snapshot.breadth_50, snapshot.breadth_200,
            snapshot.percentile_20, snapshot.percentile_50, snapshot.percentile_200,
            snapshot.source_kind.value, snapshot.provenance, snapshot.data_status.value,
            run_id,
        ),
    )
    inserted += 1

    # 2. Write events
    for event in events:
        evidence_json = json.dumps(event.evidence, ensure_ascii=False)
        connection.execute(
            """INSERT OR IGNORE INTO market_context_events (
                market_id, as_of, available_at, event_type, event_version,
                threshold_origin, evidence_json, provenance, source_kind,
                data_status, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.market_id.value, str(event.as_of), str(event.available_at),
                event.event_type, event.event_version,
                event.threshold_origin, evidence_json,
                event.provenance, event.source_kind.value,
                event.data_status.value, run_id,
            ),
        )
        inserted += 1

    # 3. Write context assessment (summary + reasons + conflicts)
    connection.execute(
        """INSERT OR REPLACE INTO market_context_assessments (
            market_id, as_of, available_at,
            long_regime, heat_state, breadth_direction,
            summary, reasons_json, conflicts_json,
            drawdown_from_ath, naaim_label, aaii_label,
            source_kind, provenance, data_status, run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snapshot.market_id.value, str(snapshot.as_of), str(snapshot.available_at),
            snapshot.long_regime.value, snapshot.heat_state.value,
            snapshot.breadth_direction.value,
            snapshot.summary.value,
            _serialize_reasons(snapshot.reasons),
            _serialize_reasons(snapshot.conflicts),
            snapshot.drawdown_from_ath,
            snapshot.naaim_label.value, snapshot.aaii_label.value,
            snapshot.source_kind.value, snapshot.provenance,
            snapshot.data_status.value, run_id,
        ),
    )
    inserted += 1

    return {"inserted": inserted}


def write_sentiment_observations(
    connection: sqlite3.Connection,
    observations: Sequence[SentimentObservation],
) -> int:
    """Write sentiment observations. Uses INSERT OR IGNORE for idempotency."""
    count = 0
    for obs in observations:
        connection.execute(
            """INSERT OR IGNORE INTO sentiment_observations (
                series_id, survey_week, available_at,
                source, license_status, publication_delay_days,
                current_eligible, exposure_index,
                bullish, neutral, bearish, bull_bear,
                percentile, label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                obs.series_id, str(obs.survey_week),
                obs.available_at.isoformat(),
                obs.source, obs.license_status,
                obs.publication_delay_days,
                int(obs.current_eligible),
                obs.exposure_index,
                obs.bullish, obs.neutral, obs.bearish, obs.bull_bear,
                obs.percentile, obs.label.value,
            ),
        )
        count += 1
    return count


def read_market_context_at(
    connection: sqlite3.Connection,
    market_id: MarketId,
    decision_at: datetime,
) -> dict | None:
    """Read the latest market context assessment visible at decision_at.

    Returns the row as a dict, or None if no assessment is available.
    """
    row = connection.execute(
        """SELECT * FROM market_context_assessments
           WHERE market_id = ? AND available_at <= ?
           ORDER BY available_at DESC
           LIMIT 1""",
        (market_id.value, decision_at.isoformat()),
    ).fetchone()

    if row is None:
        return None

    return dict(row)
