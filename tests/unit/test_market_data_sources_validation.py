"""Round 5 A5: LocalMarketBarsProvider must run every loaded frame
through validate_bars and report missing vs invalid symbols separately.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from lei_signal.market_context.data_sources import LocalMarketBarsProvider


def _write_ohlcv(path: Path, prices: list[float], start: str = "2024-01-02") -> None:
    dates = pd.bdate_range(start, periods=len(prices))
    df = pd.DataFrame(
        {
            "date": dates,
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": [1_000_000] * len(prices),
        }
    )
    df.to_parquet(path)


def _write_illegal_ohlcv(path: Path) -> None:
    """OHLC where high < low — must fail validate_bars."""
    dates = pd.bdate_range("2024-01-02", periods=30)
    df = pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * 30,
            "high": [9.0] * 30,  # high < low!
            "low": [11.0] * 30,
            "close": [10.5] * 30,
            "volume": [1_000_000] * 30,
        }
    )
    df.to_parquet(path)


def _write_missing_columns(path: Path) -> None:
    dates = pd.bdate_range("2024-01-02", periods=30)
    df = pd.DataFrame({"date": dates, "close": [10.0] * 30})
    df.to_parquet(path)


class TestLocalMarketBarsProvider:
    def test_valid_file_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_ohlcv(root / "600000.SS.parquet", [10.0 + i for i in range(30)])
            provider = LocalMarketBarsProvider(root, root)
            result = provider.load_components({"600000.SS"}, date(2024, 2, 1))
            assert "600000.SS" in result.bars_by_symbol
            assert result.missing_symbols == set()
            assert result.invalid_symbols == set()

    def test_missing_file_reported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_ohlcv(root / "600000.SS.parquet", [10.0 + i for i in range(30)])
            provider = LocalMarketBarsProvider(root, root)
            result = provider.load_components({"600000.SS", "700000.SS"}, date(2024, 2, 1))
            assert "600000.SS" in result.bars_by_symbol
            assert "700000.SS" in result.missing_symbols
            assert "700000.SS" not in result.invalid_symbols

    def test_invalid_file_reported_as_invalid_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_illegal_ohlcv(root / "600000.SS.parquet")
            provider = LocalMarketBarsProvider(root, root)
            result = provider.load_components({"600000.SS"}, date(2024, 2, 1))
            assert "600000.SS" not in result.bars_by_symbol
            assert "600000.SS" in result.invalid_symbols
            assert "600000.SS" not in result.missing_symbols
            assert "600000.SS" in result.validation_reports
            assert result.validation_reports["600000.SS"].reason  # non-empty

    def test_missing_required_columns_reported_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_missing_columns(root / "600000.SS.parquet")
            provider = LocalMarketBarsProvider(root, root)
            result = provider.load_components({"600000.SS"}, date(2024, 2, 1))
            assert "600000.SS" in result.invalid_symbols
            assert "600000.SS" not in result.missing_symbols

    def test_index_load_crops_at_as_of(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_ohlcv(root / "CSI_300.parquet", [10.0 + i for i in range(30)])
            provider = LocalMarketBarsProvider(root, root)
            df = provider.load_index("CSI_300", date(2024, 1, 16))
            assert not df.empty
            assert df.index.max() <= pd.Timestamp("2024-01-16")
