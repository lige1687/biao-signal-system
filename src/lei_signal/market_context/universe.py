"""Point-in-time index universe membership — Round 4.

Design spec sections 5, 16.1.

Provides the UniverseMembershipProvider protocol and a local-file
implementation that reads Parquet/CSV files with historical
effective_from/effective_until ranges. Enforces point-in-time visibility
and overlap validation.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

import pandas as pd

from lei_signal.market_context.types import ContextSourceKind, MarketId, UniverseSnapshot

# ── Sentinel for ongoing membership ───────────────────────────────────

# Pandas nanosecond resolution max: 2262-04-11.
# We accept "9999-12-31" as a human-readable sentinel but normalize
# to pd.Timestamp.max.date() internally.
_SENTINEL_STR = "9999-12-31"
_SENTINEL_DATE = pd.Timestamp.max.date()  # 2262-04-11

# ── Required columns ──────────────────────────────────────────────────

_REQUIRED_COLS = {
    "universe_id", "symbol", "effective_from",
    "effective_until", "source", "source_version", "source_kind",
}


# ── Errors ─────────────────────────────────────────────────────────────


class UniverseConflictError(ValueError):
    """Overlapping membership intervals for the same symbol."""


class ContextDataUnavailableError(FileNotFoundError):
    """Requested universe data file does not exist."""


# ── Protocol ───────────────────────────────────────────────────────────


class UniverseMembershipProvider(Protocol):
    """Protocol for any point-in-time universe membership provider.

    Implementations must return immutable UniverseSnapshot objects
    with exact effective-date semantics.
    """

    def snapshot(self, market_id: MarketId, as_of: date) -> UniverseSnapshot:
        ...


# ── Local implementation ──────────────────────────────────────────────


class LocalUniverseProvider:
    """Reads per-market universe files from a local root directory.

    File naming: <root>/<market_id>.parquet or <root>/<market_id>.csv

    Required columns:
      universe_id, symbol, effective_from, effective_until,
      source, source_version, source_kind

    effective_until is treated as exclusive upper bound.
    Sentinels like "9999-12-31" are normalized to pd.Timestamp.max.date().
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def _find_file(self, market_id: MarketId) -> Path:
        """Find parquet or CSV file for the market. Raise if neither exists."""
        parquet = self._root / f"{market_id.value}.parquet"
        csv = self._root / f"{market_id.value}.csv"
        if parquet.exists():
            return parquet
        if csv.exists():
            return csv
        raise ContextDataUnavailableError(
            f"Universe file not found for {market_id.value} at "
            f"{parquet} or {csv}"
        )

    @staticmethod
    def _parse_date_column(series: pd.Series) -> pd.Series:
        """Parse date column, handling sentinel values."""
        # Replace sentinel strings with pd.Timestamp.max
        mask = series.astype(str).str.strip() == _SENTINEL_STR
        parsed = pd.to_datetime(series, errors="coerce")
        parsed[mask] = pd.Timestamp.max
        return parsed.dt.date

    def _load(self, path: Path) -> pd.DataFrame:
        """Load and validate the membership file."""
        df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)

        # Validate required columns
        missing = _REQUIRED_COLS - set(df.columns)
        if missing:
            raise ValueError(
                f"Missing required columns in {path}: {missing}"
            )

        # Parse dates with sentinel handling
        df["effective_from"] = self._parse_date_column(df["effective_from"])
        df["effective_until"] = self._parse_date_column(df["effective_until"])

        return df

    def _active_rows(self, df: pd.DataFrame, as_of: date) -> pd.DataFrame:
        """Filter to rows active on as_of (effective_from <= as_of < effective_until)."""
        active = df[
            (df["effective_from"] <= as_of)
            & (df["effective_until"] > as_of)
        ].copy()
        return active

    def _validate_no_overlaps(self, active: pd.DataFrame) -> None:
        """For each symbol, verify no overlapping intervals."""
        for symbol, group in active.groupby("symbol"):
            intervals = sorted(
                zip(group["effective_from"], group["effective_until"], strict=False),
                key=lambda x: x[0],
            )
            for i in range(len(intervals) - 1):
                curr_end = intervals[i][1]
                next_start = intervals[i + 1][0]
                if next_start < curr_end:
                    raise UniverseConflictError(
                        f"Overlapping intervals for {symbol}: "
                        f"[{intervals[i][0]}, {curr_end}) and "
                        f"[{next_start}, {intervals[i+1][1]})"
                    )

    def _derive_source_info(self, active: pd.DataFrame) -> dict:
        """Derive source metadata from active rows."""
        source_kind_str = active["source_kind"].iloc[0] if len(active) > 0 else "formal"
        try:
            source_kind = ContextSourceKind(source_kind_str)
        except ValueError:
            source_kind = ContextSourceKind.FORMAL

        src_col = "source" in active.columns
        version_col = "source_version" in active.columns
        source = active["source"].iloc[0] if src_col and len(active) > 0 else ""
        source_version = (
            active["source_version"].iloc[0] if version_col and len(active) > 0 else ""
        )

        return {
            "source_kind": source_kind,
            "source": source,
            "source_version": source_version,
        }

    def _compute_version(self, active: pd.DataFrame) -> str:
        """Deterministic hash of active rows for audit trail."""
        if len(active) == 0:
            return "empty"
        # Sort by symbol for determinism
        sorted_rows = active.sort_values("symbol")
        payload = "|".join(
            f"{r.symbol}:{r.effective_from}:{r.effective_until}"
            for _, r in sorted_rows.iterrows()
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def snapshot(self, market_id: MarketId, as_of: date) -> UniverseSnapshot:
        """Return the universe membership snapshot for market_id on as_of."""
        path = self._find_file(market_id)
        df = self._load(path)

        # Filter to market_id
        market_df = df[df["universe_id"] == market_id.value]

        active = self._active_rows(market_df, as_of)
        self._validate_no_overlaps(active)

        info = self._derive_source_info(active)
        universe_version = self._compute_version(active)

        symbols = tuple(sorted(active["symbol"].tolist()))

        return UniverseSnapshot(
            market_id=market_id,
            as_of=as_of,
            symbols=symbols,
            source=info["source"],
            source_version=info["source_version"],
            source_kind=info["source_kind"],
            retrieved_at=datetime.now(UTC),
            universe_version=universe_version,
        )


# ── Convenience ────────────────────────────────────────────────────────


def load_universe_snapshot(
    provider: UniverseMembershipProvider,
    market_id: MarketId,
    as_of: date,
) -> UniverseSnapshot:
    """Convenience wrapper: load point-in-time universe via provider."""
    return provider.snapshot(market_id, as_of)
