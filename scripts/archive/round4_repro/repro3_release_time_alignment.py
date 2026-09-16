#!/usr/bin/env python3
"""Round 4 Repro 3: Release-Time Alignment for NAAIM/AAII.

Proves that:
1. An observation is invisible before its available_at timestamp.
2. The same observation becomes visible at and after available_at.
3. Missing available_at raises an error.

Usage:
  PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round4_repro/repro3_release_time_alignment.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from lei_signal.market_context.sentiment import (
    latest_available_sentiment,
    load_aaii_observations,
    load_naaim_observations,
)

print("=" * 60)
print("REPRO 3: Release-Time Alignment")
print("=" * 60)

# ── NAAIM: invisible before release, visible after ────────────────────

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "naaim.csv"
    df = pd.DataFrame({
        "survey_week": ["2024-06-10"],
        "available_at": ["2024-06-13T07:00:00"],
        "exposure_index": [80.0],
        "source": ["official"],
        "license_status": ["licensed"],
        "publication_delay_days": [3],
    })
    df.to_csv(path, index=False)

    obs = load_naaim_observations(path)
    print(f"\nNAAIM observation:")
    print(f"  Survey week: {obs[0].survey_week}")
    print(f"  Available at: {obs[0].available_at}")
    print(f"  Exposure: {obs[0].exposure_index}")
    print(f"  Current eligible: {obs[0].current_eligible}")

    # Wednesday before release
    wed = datetime(2024, 6, 12, 16, 0, tzinfo=timezone.utc)
    result_before = latest_available_sentiment(obs, wed, max_age_days=14)
    assert result_before is None, "BUG: NAAIM visible before release!"
    print(f"\n  At {wed}: invisible ✓")

    # Thursday after release
    thu = datetime(2024, 6, 13, 16, 0, tzinfo=timezone.utc)
    result_after = latest_available_sentiment(obs, thu, max_age_days=14)
    assert result_after is not None, "BUG: NAAIM invisible after release!"
    assert result_after.exposure_index == 80.0
    print(f"  At {thu}: visible (exposure={result_after.exposure_index}) ✓")

# ── AAII: invisible before release, visible after ─────────────────────

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "aaii.csv"
    df = pd.DataFrame({
        "survey_week": ["2024-06-06"],
        "available_at": ["2024-06-12T08:00:00"],
        "bullish": [35.0],
        "neutral": [30.0],
        "bearish": [35.0],
        "source": ["official"],
        "license_status": ["licensed"],
    })
    df.to_csv(path, index=False)

    obs = load_aaii_observations(path)
    print(f"\nAAII observation:")
    print(f"  Survey week: {obs[0].survey_week}")
    print(f"  Available at: {obs[0].available_at}")
    print(f"  Bull-Bear: {obs[0].bull_bear:.1f}")

    # Before release
    before = datetime(2024, 6, 11, 16, 0, tzinfo=timezone.utc)
    result_before = latest_available_sentiment(obs, before, max_age_days=10)
    assert result_before is None, "BUG: AAII visible before release!"
    print(f"\n  At {before}: invisible ✓")

    # After release
    after = datetime(2024, 6, 12, 16, 0, tzinfo=timezone.utc)
    result_after = latest_available_sentiment(obs, after, max_age_days=10)
    assert result_after is not None, "BUG: AAII invisible after release!"
    assert abs(result_after.bull_bear) < 0.01, f"Expected bull_bear≈0, got {result_after.bull_bear}"
    print(f"  At {after}: visible (bull_bear={result_after.bull_bear:.1f}) ✓")

# ── Missing available_at must raise ───────────────────────────────────

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "naaim_missing.csv"
    df = pd.DataFrame({
        "survey_week": ["2024-06-10"],
        "exposure_index": [80.0],
        "source": ["official"],
        "license_status": ["licensed"],
        "publication_delay_days": [3],
    })
    df.to_csv(path, index=False)

    try:
        load_naaim_observations(path)
        print("\n  ✗ BUG: missing available_at NOT detected!")
        sys.exit(1)
    except ValueError as e:
        print(f"\n  ✓ Missing available_at correctly raises ValueError: {e}")

print("\n" + "=" * 60)
print("REPRO 3: ALL CHECKS PASSED")
print("=" * 60)
print("\nRelease-time alignment is correct:")
print("  - NAAIM invisible before available_at, visible after")
print("  - AAII invisible before available_at, visible after")
print("  - Missing available_at raises ValueError")
