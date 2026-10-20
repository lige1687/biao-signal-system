"""Local market bars data provider — Round 4 + Round 5.

Reads component OHLCV bars and index bars from local files.
Files are expected as Parquet (primary) or CSV (fallback). Every loaded frame
goes through `validate_bars`, so missing/empty files and ill-formed rows are
distinguished instead of silently collapsed into "missing".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from lei_signal.data.validation import (
    DataUnavailableError,
    ValidationReport,
    validate_bars,
)

_ADJUSTED_DEFAULT = True


@dataclass(frozen=True, slots=True)
class BarsResult:
    """Immutable result from loading component bars.

    `invalid_symbols` separates files that loaded but failed OHLCV validation
    from `missing_symbols` (no file at all). The breadth calculator needs
    that distinction: an invalid file is a data-quality red flag, not the
    same thing as "we don't have this stock yet".
    """

    bars_by_symbol: dict[str, pd.DataFrame] = field(default_factory=dict)
    missing_symbols: set[str] = field(default_factory=set)
    invalid_symbols: set[str] = field(default_factory=set)
    validation_reports: dict[str, ValidationReport] = field(default_factory=dict)
    source_version: str = "local.v2"


class LocalMarketBarsProvider:
    """Reads component and index bar files from local directories.

    File naming:
      Components:  <component_root>/<symbol>.parquet or .csv
      Indices:     <index_root>/<market_id>.parquet or .csv

    Each file must contain columns: date, open, high, low, close, volume.
    Loaded frames are validated by `validate_bars`; frames that fail
    validation are reported under `invalid_symbols` and never returned
    for downstream breadth calculation.
    """

    def __init__(self, component_root: str | Path, index_root: str | Path,
                 *, adjusted: bool = _ADJUSTED_DEFAULT) -> None:
        self._comp_root = Path(component_root)
        self._idx_root = Path(index_root)
        self._adjusted = adjusted

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
        df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)

        # Ensure date column is datetime
        if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"])

        return df

    def _normalize_index(self, df: pd.DataFrame) -> pd.DataFrame:
        if "date" in df.columns:
            df = df.set_index("date")
        return df

    def _validate(
        self, df: pd.DataFrame, *, symbol: str, provider: str,
    ) -> tuple[pd.DataFrame | None, ValidationReport]:
        try:
            return validate_bars(
                df, symbol=symbol, provider=provider, adjusted=self._adjusted,
            )
        except DataUnavailableError as exc:
            return None, ValidationReport(
                symbol=symbol, provider=provider, rows=len(df), reason=str(exc),
            )

    def load_components(
        self,
        symbols: set[str],
        as_of: date,
    ) -> BarsResult:
        """Load bars for the given symbols, cropped at as_of."""
        bars_by_symbol: dict[str, pd.DataFrame] = {}
        missing: set[str] = set()
        invalid: set[str] = set()
        reports: dict[str, ValidationReport] = {}

        as_of_ts = pd.Timestamp(as_of)

        for sym in sorted(symbols):
            path = self._find_file(self._comp_root, sym)
            if path is None:
                missing.add(sym)
                continue

            raw = self._load_frame(path)
            raw = self._normalize_index(raw)

            if isinstance(raw.index, pd.DatetimeIndex):
                raw = raw[raw.index <= as_of_ts].copy()

            if len(raw) == 0:
                missing.add(sym)
                continue

            validated, report = self._validate(raw, symbol=sym, provider="local_components")
            reports[sym] = report
            if validated is None or len(validated) == 0:
                invalid.add(sym)
                continue

            bars_by_symbol[sym] = validated

        return BarsResult(
            bars_by_symbol=bars_by_symbol,
            missing_symbols=missing,
            invalid_symbols=invalid,
            validation_reports=reports,
        )

    def load_index(self, market_id: str, as_of: date) -> pd.DataFrame:
        """Load index bars for a market, cropped at as_of.

        Returns an empty DataFrame if the file is missing or fails validation
        — index data is optional (drawdown skipped silently) so the provider
        reports the failure via the validation report map but does not raise.
        """
        path = self._find_file(self._idx_root, market_id)
        if path is None:
            return pd.DataFrame()

        raw = self._load_frame(path)
        raw = self._normalize_index(raw)

        as_of_ts = pd.Timestamp(as_of)
        if isinstance(raw.index, pd.DatetimeIndex):
            raw = raw[raw.index <= as_of_ts].copy()

        validated, _ = self._validate(raw, symbol=market_id, provider="local_index")
        if validated is None:
            return pd.DataFrame()
        return validated
