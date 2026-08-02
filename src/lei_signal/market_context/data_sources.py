"""Local market bars data provider — Round 4.

Reads component OHLCV bars and index bars from local files.
Files are expected as Parquet (primary) or CSV (fallback).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class BarsResult:
    """Immutable result from loading component bars."""

    bars_by_symbol: dict[str, pd.DataFrame] = field(default_factory=dict)
    missing_symbols: set[str] = field(default_factory=set)
    source_version: str = ""


class LocalMarketBarsProvider:
    """Reads component and index bar files from local directories.

    File naming:
      Components:  <component_root>/<symbol>.parquet or .csv
      Indices:     <index_root>/<market_id>.parquet or .csv

    Each file must contain columns: date, open, high, low, close, volume.
    """

    def __init__(self, component_root: str | Path, index_root: str | Path) -> None:
        self._comp_root = Path(component_root)
        self._idx_root = Path(index_root)

    def _find_file(self, root: Path, name: str) -> Path | None:
        """Find parquet or CSV file. Returns None if neither exists."""
        parquet = root / f"{name}.parquet"
        csv = root / f"{name}.csv"
        if parquet.exists():
            return parquet
        if csv.exists():
            return csv
        return None

    def _load_frame(self, path: Path) -> pd.DataFrame:
        """Load OHLCV frame and normalize."""
        if path.suffix == ".parquet":
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path)

        # Ensure date column is datetime
        if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"])

        return df

    def load_components(
        self,
        symbols: set[str],
        as_of: date,
    ) -> BarsResult:
        """Load bars for the given symbols, cropped at as_of.

        Only loads files for symbols present in the supplied set.
        Reports missing symbols explicitly.
        """
        bars_by_symbol: dict[str, pd.DataFrame] = {}
        missing: set[str] = set()

        as_of_ts = pd.Timestamp(as_of)

        for sym in sorted(symbols):
            path = self._find_file(self._comp_root, sym)
            if path is None:
                missing.add(sym)
                continue

            df = self._load_frame(path)
            df = df.set_index("date") if "date" in df.columns else df

            # Crop at as_of (inclusive — include bars on or before as_of)
            if isinstance(df.index, pd.DatetimeIndex):
                df = df[df.index <= as_of_ts].copy()

            if len(df) == 0:
                missing.add(sym)
                continue

            bars_by_symbol[sym] = df

        return BarsResult(
            bars_by_symbol=bars_by_symbol,
            missing_symbols=missing,
            source_version="local.v1",
        )

    def load_index(self, market_id: str, as_of: date) -> pd.DataFrame:
        """Load index bars for a market, cropped at as_of.

        Returns empty DataFrame if file not found.
        """
        path = self._find_file(self._idx_root, market_id)
        if path is None:
            return pd.DataFrame()

        df = self._load_frame(path)
        df = df.set_index("date") if "date" in df.columns else df

        as_of_ts = pd.Timestamp(as_of)
        if isinstance(df.index, pd.DatetimeIndex):
            df = df[df.index <= as_of_ts].copy()

        return df
