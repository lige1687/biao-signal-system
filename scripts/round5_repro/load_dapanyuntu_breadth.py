"""Load 大盘云图 A-share MA20 breadth history into the market-context store.

Fetches ~310 trading days of ready-computed MA20 站上率 from
sckd.dapanyuntu.com and writes one breadth-snapshot revision per session
for CN_ALL_A, with point-in-time percentiles.

Why this exists
---------------
Computing MA20 breadth ourselves needs a daily bar fetch per stock
(~5000 requests) and Tencent rate-limits after ~1500. 大盘云图 publishes
the aggregate directly, so one script run gives a full year of history
that the percentile / forward-stats endpoints can immediately use.

The readings are equal-weighted across 86 二级行业 rather than
count-weighted across individual stocks, so they land as
``source_kind=research_proxy``. Our own per-stock computation stays in
place as a cross-check.

Usage
-----
    LEI_CACHE_ROOT=... python scripts/round5_repro/load_dapanyuntu_breadth.py
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from lei_signal.api import config
from lei_signal.market_context.breadth import rolling_percentile_at
from lei_signal.market_context.dapanyuntu import (
    SOURCE,
    DapanyuntuUnavailableError,
    fetch_history,
    market_breadth_series,
)
from lei_signal.market_context.types import MarketId
from lei_signal.storage.sqlite_store import connect

MARKET_ID = MarketId.CN_ALL_A
UNIVERSE_VERSION = "dapanyuntu.industry_ma20.v1"

#: 86 二级行业 is the denominator the upstream aggregates over.
_TOTAL_INDUSTRIES = 86

#: Coverage floor: below this share of industries reporting we mark the
#: session incomplete rather than publishing a thin reading as complete.
_MIN_COVERAGE = 0.90

#: 大盘云图 only publishes MA20, so the 50/200 horizons stay NULL and the
#: classifier's per-horizon gating will report them as unavailable.
_PERCENTILE_MIN_PERIODS = 60
_PERCENTILE_LOOKBACK = 1260


def _clear_prior(connection: sqlite3.Connection) -> None:
    """Drop previous dapanyuntu-sourced rows so re-runs are idempotent."""
    for table in (
        "market_breadth_snapshot_revisions",
        "market_context_assessment_revisions",
    ):
        connection.execute(
            f"DELETE FROM {table} WHERE market_id = ?", (MARKET_ID.value,)
        )
    connection.execute(
        "DELETE FROM market_breadth_snapshots WHERE market_id = ?",
        (MARKET_ID.value,),
    )
    connection.execute(
        "DELETE FROM market_context_assessments WHERE market_id = ?",
        (MARKET_ID.value,),
    )
    connection.commit()


def _insert_session(
    connection: sqlite3.Connection,
    *,
    as_of: date,
    breadth: float,
    reporting: int,
    total: int,
    percentile: float | None,
    run_id: str,
) -> None:
    coverage = reporting / total if total else 0.0
    status = "complete" if coverage >= _MIN_COVERAGE else "incomplete"
    connection.execute(
        """INSERT OR REPLACE INTO market_breadth_snapshot_revisions (
            market_id, as_of, universe_version, revision_no,
            available_at, run_id, source_kind, provenance, data_status,
            constituent_count,
            eligible_20, eligible_50, eligible_200,
            missing_20, missing_50, missing_200,
            coverage_20, coverage_50, coverage_200,
            breadth_20, breadth_50, breadth_200,
            percentile_20, percentile_50, percentile_200
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            MARKET_ID.value, str(as_of), UNIVERSE_VERSION, 1,
            str(as_of), run_id, "research_proxy", SOURCE, status,
            total,
            reporting, 0, 0,
            total - reporting, total, total,
            coverage, 0.0, 0.0,
            breadth, None, None,
            percentile, None, None,
        ),
    )


def load(*, pages: int, dry_run: bool = False) -> int:
    print(f"  fetching {pages} pages from 大盘云图…", file=sys.stderr)
    try:
        fetched = fetch_history(pages=pages, pause_seconds=1.2)
    except DapanyuntuUnavailableError as exc:
        print(f"  upstream unavailable: {exc}", file=sys.stderr)
        return 1
    if not fetched:
        print("  no pages fetched", file=sys.stderr)
        return 1

    series = market_breadth_series(fetched)
    if not series:
        print("  no usable readings", file=sys.stderr)
        return 1

    sessions = sorted(series)
    print(
        f"  got {len(sessions)} sessions: {sessions[0]} -> {sessions[-1]}",
        file=sys.stderr,
    )

    # Point-in-time percentiles: for each session, rank its reading against
    # only the sessions at or before it. Never let a later session change
    # an earlier percentile.
    breadth_series = pd.Series(
        [series[d][0] for d in sessions],
        index=pd.to_datetime([str(d) for d in sessions]),
        dtype=float,
    )

    if dry_run:
        for d in sessions[-5:]:
            b, rep, tot = series[d]
            pct = rolling_percentile_at(
                breadth_series, as_of=d,
                lookback=_PERCENTILE_LOOKBACK,
                min_periods=_PERCENTILE_MIN_PERIODS,
            )
            label = f"P{pct:.0f}" if pct is not None else "P--"
            print(f"    {d}  {b:6.2f}%  {label}  ({rep}/{tot} 行业)", file=sys.stderr)
        print("  dry-run: nothing written", file=sys.stderr)
        return 0

    db_path = Path(config.sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch()
    connection = connect(db_path)
    try:
        _clear_prior(connection)
        run_id = f"dapanyuntu:{sessions[-1]}"
        written = 0
        for as_of in sessions:
            breadth, reporting, total = series[as_of]
            percentile = rolling_percentile_at(
                breadth_series, as_of=as_of,
                lookback=_PERCENTILE_LOOKBACK,
                min_periods=_PERCENTILE_MIN_PERIODS,
            )
            _insert_session(
                connection,
                as_of=as_of, breadth=breadth,
                reporting=reporting, total=total,
                percentile=percentile, run_id=run_id,
            )
            written += 1
        connection.commit()
    finally:
        connection.close()

    latest = sessions[-1]
    b, rep, tot = series[latest]
    pct = rolling_percentile_at(
        breadth_series, as_of=latest,
        lookback=_PERCENTILE_LOOKBACK, min_periods=_PERCENTILE_MIN_PERIODS,
    )
    label = f"P{pct:.0f}" if pct is not None else "P--"
    print(
        f"  wrote {written} sessions -> {db_path}\n"
        f"  latest {latest}: MA20 站上率 {b:.2f}%  {label}  ({rep}/{tot} 行业)",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=int, default=10,
        help="Pages to walk back (~31 sessions each; default 10 ≈ 310)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and report without writing to SQLite",
    )
    args = parser.parse_args(argv)
    return load(pages=args.pages, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
