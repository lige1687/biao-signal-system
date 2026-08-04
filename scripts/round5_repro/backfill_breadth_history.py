"""One-shot backfill: walk every session in the index bars and persist
a breadth snapshot for each, so the percentile / forward-stats endpoints
have history to work with on day 1.

Run once after `ingest_real_markets.py`:

    LEI_CACHE_ROOT=... python scripts/round5_repro/backfill_breadth_history.py

⚠️  This backfill only produces non-empty breadth values for sessions
that have matching component bars on disk. The current `ingest_real_markets`
caps at 250 bars per symbol, so the backfill writes a long tail of
"no data" rows whose `breadth_20` is NULL — those don't help the
percentile / forward-stats story. The honest path is: let the system
write one real snapshot per trading day in production. After ~252
trading days the forward-stats endpoint lights up on its own.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

from lei_signal.api import config
from lei_signal.api.market_context_service import (
    _DEFAULT_GLOBAL_MARKETS,
    MarketContextService,
)
from lei_signal.market_context.storage import write_market_context
from lei_signal.market_context.types import MarketContextSnapshot, MarketId
from lei_signal.storage.sqlite_store import connect


def _persist_snapshots(
    connection: sqlite3.Connection,
    snapshots: tuple[MarketContextSnapshot, ...],
    run_id: str,
) -> int:
    n = 0
    for snap in snapshots:
        write_market_context(connection, snap, snap.extreme_events, run_id=run_id)
        n += 1
    return n


def backfill(
    *,
    as_of_max: date,
    market_ids: tuple[MarketId, ...] = _DEFAULT_GLOBAL_MARKETS,
    sleep_seconds: float = 0.0,
) -> int:
    root = Path(config.cache_root())
    fixture_root = root / "fixtures" / "market_context"
    if not (fixture_root / "indices" / "CN_ALL_A.parquet").exists():
        print(
            f"missing {fixture_root}/indices/CN_ALL_A.parquet — "
            "run ingest_real_markets first",
            file=sys.stderr,
        )
        return 1

    db_path = Path(config.sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch()
    connection = connect(db_path)

    svc = MarketContextService()
    total = 0
    for market_id in market_ids:
        index_path = fixture_root / "indices" / f"{market_id.value}.parquet"
        if not index_path.exists():
            print(f"  {market_id.value}: no index file, skipping", file=sys.stderr)
            continue
        import pandas as pd
        bars = pd.read_parquet(index_path)
        if "date" in bars.columns:
            bars["date"] = pd.to_datetime(bars["date"])
            bars = bars.set_index("date").sort_index()
        session_dates = [
            d.date() for d in bars.index
            if isinstance(d, pd.Timestamp) and d.date() <= as_of_max
        ]
        print(f"  {market_id.value}: {len(session_dates)} sessions to backfill", file=sys.stderr)

        # Wipe prior revisions for this market so re-runs are idempotent.
        connection.execute(
            "DELETE FROM market_breadth_snapshot_revisions WHERE market_id = ?",
            (market_id.value,),
        )
        connection.execute(
            "DELETE FROM market_context_assessment_revisions WHERE market_id = ?",
            (market_id.value,),
        )
        connection.execute(
            "DELETE FROM market_breadth_snapshots WHERE market_id = ?",
            (market_id.value,),
        )
        connection.execute(
            "DELETE FROM market_context_assessments WHERE market_id = ?",
            (market_id.value,),
        )
        connection.commit()

        for i, as_of in enumerate(session_dates):
            try:
                dto = svc._build_for_market(market_id, as_of)
            except Exception as exc:
                print(f"  {as_of}: error {exc}", file=sys.stderr)
                continue
            # Recompute percentiles over the full breadth history up to `as_of`
            # so the very first backfill pass leaves percentiles populated.
            from lei_signal.api.market_context_service import _read_breadth_history
            for snap_dict in dto.snapshots:
                mid = MarketId(snap_dict["market_id"])
                for window in (20, 50, 200):
                    hist = _read_breadth_history(connection, mid, up_to=as_of)
                    if not hist.empty:
                        col = f"breadth_{window}"
                        if col not in hist.columns:
                            continue
                        series = hist[col].dropna()
                        from lei_signal.market_context.breadth import rolling_percentile_at
                        pct = rolling_percentile_at(
                            series, as_of=as_of, lookback=1260, min_periods=60,
                        )
                        if pct is not None:
                            snap_dict[f"percentile_{window}"] = pct
                            pct_col = col.replace("breadth", "percentile")
                            connection.execute(
                                f"UPDATE market_breadth_snapshot_revisions "
                                f"SET {pct_col} = ? "
                                f"WHERE market_id = ? AND as_of = ? AND revision_no = ("
                                f"SELECT MAX(revision_no) FROM market_breadth_snapshot_revisions "
                                f"WHERE market_id = ? AND as_of = ?)",
                                (pct, mid.value, str(as_of), mid.value, str(as_of)),
                            )
            total += 1
            if i % 50 == 0:
                connection.commit()
                if sleep_seconds:
                    time.sleep(sleep_seconds)
        connection.commit()
    connection.close()
    print(f"done — {total} backfill snapshots persisted to {db_path}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of", type=str, default=None,
        help="Latest date (default: today)",
    )
    args = parser.parse_args(argv)
    as_of_max = date.fromisoformat(args.as_of) if args.as_of else date.today()
    return backfill(as_of_max=as_of_max)


if __name__ == "__main__":
    sys.exit(main())
