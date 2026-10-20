"""Task 2 unit tests — point-in-time universe membership.

Design spec sections 5, 16.1.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.market_context.types import ContextSourceKind, MarketId
from lei_signal.market_context.universe import (
    ContextDataUnavailableError,
    LocalUniverseProvider,
    UniverseConflictError,
    UniverseMembershipProvider,
    load_universe_snapshot,
)

# ── Fixture helpers ───────────────────────────────────────────────────


def _make_membership_csv(path: Path, rows: list[dict]) -> Path:
    """Write a universe membership CSV with required columns."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path


def _dt(d: str) -> date:
    return date.fromisoformat(d)


# ── Tests ─────────────────────────────────────────────────────────────


class TestUniverseMembershipProvider:
    """Tests that any provider implementation must satisfy."""

    def test_protocol_is_importable(self) -> None:
        """UniverseMembershipProvider must be a usable protocol."""
        # Protocol should exist as a type
        assert UniverseMembershipProvider is not None


class TestLocalUniverseProvider:
    def test_exact_point_in_time_membership(self) -> None:
        """Membership changes on rebalance effective date."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Member AAA: effective 2024-01-01 to 2024-06-30
            # Member BBB: effective 2024-07-01 onward
            csv_path = root / "CSI_300.parquet"  # same format works for CSV
            df = pd.DataFrame({
                "universe_id": ["CSI_300", "CSI_300"],
                "symbol": ["AAA.SH", "BBB.SH"],
                "effective_from": ["2024-01-01", "2024-07-01"],
                "effective_until": ["2024-06-30", "9999-12-31"],
                "source": ["test", "test"],
                "source_version": ["v1", "v1"],
                "source_kind": ["formal", "formal"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)

            # Before rebalance
            snap_before = provider.snapshot(MarketId.CSI_300, _dt("2024-06-28"))
            assert snap_before.symbols == ("AAA.SH",)
            assert snap_before.source_kind == ContextSourceKind.FORMAL

            # On rebalance effective date
            snap_on = provider.snapshot(MarketId.CSI_300, _dt("2024-07-01"))
            assert snap_on.symbols == ("BBB.SH",)

            # After rebalance
            snap_after = provider.snapshot(MarketId.CSI_300, _dt("2024-07-15"))
            assert snap_after.symbols == ("BBB.SH",)

    def test_future_row_invisible_before_effective(self) -> None:
        """A row with effective_from in the future must not appear."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300", "CSI_300"],
                "symbol": ["AAA.SH", "BBB.SH"],
                "effective_from": ["2024-01-01", "2025-01-01"],
                "effective_until": ["9999-12-31", "9999-12-31"],
                "source": ["test", "test"],
                "source_version": ["v1", "v1"],
                "source_kind": ["formal", "formal"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            assert "BBB.SH" not in snap.symbols
            assert "AAA.SH" in snap.symbols

    def test_missing_universe_file_raises(self) -> None:
        """Missing file must raise ContextDataUnavailableError, not return empty."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = LocalUniverseProvider(root)
            with pytest.raises(ContextDataUnavailableError):
                provider.snapshot(MarketId.CSI_300, _dt("2024-01-01"))

    def test_overlapping_contradictory_rows_raise_conflict(self) -> None:
        """Overlapping intervals for different symbols is fine;
        overlapping for the SAME symbol must raise."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300", "CSI_300"],
                "symbol": ["AAA.SH", "AAA.SH"],
                "effective_from": ["2024-01-01", "2024-03-01"],
                "effective_until": ["2024-06-30", "9999-12-31"],
                "source": ["test", "test"],
                "source_version": ["v1", "v1"],
                "source_kind": ["formal", "formal"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            with pytest.raises(UniverseConflictError):
                provider.snapshot(MarketId.CSI_300, _dt("2024-04-01"))

    def test_adjacent_intervals_are_permitted(self) -> None:
        """Adjacent intervals (end of one = start of next) are valid."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300", "CSI_300"],
                "symbol": ["AAA.SH", "AAA.SH"],
                "effective_from": ["2024-01-01", "2024-07-01"],
                "effective_until": ["2024-06-30", "9999-12-31"],
                "source": ["test", "test"],
                "source_version": ["v1", "v1"],
                "source_kind": ["formal", "formal"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap_before = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            snap_after = provider.snapshot(MarketId.CSI_300, _dt("2024-07-15"))
            assert snap_before.symbols == ("AAA.SH",)
            assert snap_after.symbols == ("AAA.SH",)

    def test_current_constituent_backfill_is_research_proxy(self) -> None:
        """Current-constituent backfill must return RESEARCH_PROXY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300"],
                "symbol": ["AAA.SH"],
                "effective_from": ["2020-01-01"],
                "effective_until": ["9999-12-31"],
                "source": ["current_snapshot"],
                "source_version": ["2024-backfill"],
                "source_kind": ["research_proxy"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            assert snap.source_kind == ContextSourceKind.RESEARCH_PROXY

    def test_symbols_are_sorted_and_stable(self) -> None:
        """Symbols must be returned in stable sorted order."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300"] * 3,
                "symbol": ["CCC.SH", "AAA.SH", "BBB.SH"],
                "effective_from": ["2024-01-01"] * 3,
                "effective_until": ["9999-12-31"] * 3,
                "source": ["test"] * 3,
                "source_version": ["v1"] * 3,
                "source_kind": ["formal"] * 3,
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            assert snap.symbols == ("AAA.SH", "BBB.SH", "CCC.SH")

    def test_universe_version_is_deterministic_hash(self) -> None:
        """Same membership rows → same universe_version hash."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300"] * 2,
                "symbol": ["AAA.SH", "BBB.SH"],
                "effective_from": ["2024-01-01"] * 2,
                "effective_until": ["9999-12-31"] * 2,
                "source": ["test"] * 2,
                "source_version": ["v1"] * 2,
                "source_kind": ["formal"] * 2,
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap1 = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            snap2 = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            assert snap1.universe_version == snap2.universe_version
            assert len(snap1.universe_version) > 0

    def test_csv_fallback(self) -> None:
        """Provider falls back to CSV when Parquet not found."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.csv"
            df = pd.DataFrame({
                "universe_id": ["CSI_300"],
                "symbol": ["AAA.SH"],
                "effective_from": ["2024-01-01"],
                "effective_until": ["9999-12-31"],
                "source": ["test"],
                "source_version": ["v1"],
                "source_kind": ["formal"],
            })
            df.to_csv(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap = provider.snapshot(MarketId.CSI_300, _dt("2024-06-15"))
            assert snap.symbols == ("AAA.SH",)

    def test_append_future_row_does_not_change_past_snapshot(self) -> None:
        """Adding a future membership row must not change earlier as_of snapshot."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300"],
                "symbol": ["AAA.SH"],
                "effective_from": ["2024-01-01"],
                "effective_until": ["9999-12-31"],
                "source": ["test"],
                "source_version": ["v1"],
                "source_kind": ["formal"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap_before = provider.snapshot(MarketId.CSI_300, _dt("2024-03-01"))
            syms_before = snap_before.symbols

            # Now write a file with an additional future row
            df2 = pd.DataFrame({
                "universe_id": ["CSI_300", "CSI_300"],
                "symbol": ["AAA.SH", "BBB.SH"],
                "effective_from": ["2024-01-01", "2025-01-01"],
                "effective_until": ["9999-12-31", "9999-12-31"],
                "source": ["test", "test"],
                "source_version": ["v1", "v1"],
                "source_kind": ["formal", "formal"],
            })
            df2.to_parquet(csv_path, index=False)

            # Re-create provider (simulates a later run)
            provider2 = LocalUniverseProvider(root)
            snap_after = provider2.snapshot(MarketId.CSI_300, _dt("2024-03-01"))
            assert snap_after.symbols == syms_before
            # Version may differ because the file changed, but symbols must be identical
            # (the future row doesn't affect the past as_of)
            assert "BBB.SH" not in snap_after.symbols


class TestLoadUniverseSnapshot:
    def test_convenience_function(self) -> None:
        """load_universe_snapshot delegates correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "CSI_300.parquet"
            df = pd.DataFrame({
                "universe_id": ["CSI_300"],
                "symbol": ["AAA.SH"],
                "effective_from": ["2024-01-01"],
                "effective_until": ["9999-12-31"],
                "source": ["test"],
                "source_version": ["v1"],
                "source_kind": ["formal"],
            })
            df.to_parquet(csv_path, index=False)

            provider = LocalUniverseProvider(root)
            snap = load_universe_snapshot(provider, MarketId.CSI_300, _dt("2024-06-15"))
            assert snap.market_id == MarketId.CSI_300
            assert snap.symbols == ("AAA.SH",)
            assert snap.source_kind == ContextSourceKind.FORMAL
