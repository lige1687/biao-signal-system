"""Task 3 unit tests — local market bars data source."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.market_context.data_sources import LocalMarketBarsProvider


def _make_bar_file(path: Path, dates: list[str], closes: list[float]) -> None:
    """Create a minimal OHLCV parquet file."""
    df = pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [1000000] * len(closes),
    })
    df.to_parquet(path, index=False)


class TestLocalMarketBarsProvider:
    def test_loads_valid_bars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            comp_root = Path(tmp) / "components"
            comp_root.mkdir()
            idx_root = Path(tmp) / "indices"
            idx_root.mkdir()

            # Create a component file
            _make_bar_file(
                comp_root / "AAA.SH.parquet",
                ["2024-01-01", "2024-01-02", "2024-01-03"],
                [10.0, 11.0, 12.0],
            )

            provider = LocalMarketBarsProvider(comp_root, idx_root)
            result = provider.load_components(
                {"AAA.SH"}, date(2024, 1, 3)
            )

            assert "AAA.SH" in result.bars_by_symbol
            assert len(result.missing_symbols) == 0
            # Should be cropped at as_of
            frame = result.bars_by_symbol["AAA.SH"]
            assert len(frame) == 3  # all three dates are <= 2024-01-03

    def test_crops_at_as_of(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            comp_root = Path(tmp) / "components"
            comp_root.mkdir()
            idx_root = Path(tmp) / "indices"
            idx_root.mkdir()

            _make_bar_file(
                comp_root / "AAA.SH.parquet",
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
                [10.0, 11.0, 12.0, 13.0, 14.0],
            )

            provider = LocalMarketBarsProvider(comp_root, idx_root)
            result = provider.load_components({"AAA.SH"}, date(2024, 1, 3))

            frame = result.bars_by_symbol["AAA.SH"]
            assert len(frame) == 3
            assert frame.iloc[-1]["close"] == 12.0

    def test_reports_missing_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            comp_root = Path(tmp) / "components"
            comp_root.mkdir()
            idx_root = Path(tmp) / "indices"
            idx_root.mkdir()

            _make_bar_file(
                comp_root / "AAA.SH.parquet",
                ["2024-01-01", "2024-01-02"],
                [10.0, 11.0],
            )

            provider = LocalMarketBarsProvider(comp_root, idx_root)
            result = provider.load_components(
                {"AAA.SH", "MISSING.SH"}, date(2024, 1, 2)
            )

            assert "AAA.SH" in result.bars_by_symbol
            assert "MISSING.SH" in result.missing_symbols
            assert "MISSING.SH" not in result.bars_by_symbol

    def test_ignores_non_parquet_csv_files(self) -> None:
        """CSV fallback should work for .csv files."""
        with tempfile.TemporaryDirectory() as tmp:
            comp_root = Path(tmp) / "components"
            comp_root.mkdir()
            idx_root = Path(tmp) / "indices"
            idx_root.mkdir()

            df = pd.DataFrame({
                "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "open": [10.0, 11.0],
                "high": [10.1, 11.1],
                "low": [9.9, 10.9],
                "close": [10.0, 11.0],
                "volume": [1000000, 1000000],
            })
            df.to_csv(comp_root / "AAA.SH.csv", index=False)

            provider = LocalMarketBarsProvider(comp_root, idx_root)
            result = provider.load_components({"AAA.SH"}, date(2024, 1, 2))
            assert "AAA.SH" in result.bars_by_symbol

    def test_load_index_returns_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            comp_root = Path(tmp) / "components"
            comp_root.mkdir()
            idx_root = Path(tmp) / "indices"
            idx_root.mkdir()

            _make_bar_file(
                idx_root / "CSI_300.parquet",
                ["2024-01-01", "2024-01-02", "2024-01-03"],
                [3500.0, 3520.0, 3480.0],
            )

            provider = LocalMarketBarsProvider(comp_root, idx_root)
            frame = provider.load_index("CSI_300", date(2024, 1, 3))
            assert len(frame) == 3
            assert "close" in frame.columns
