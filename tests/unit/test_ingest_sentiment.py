"""Tests for scripts/round5_repro/ingest_sentiment.py (offline ingest)."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "round5_repro"))

from ingest_sentiment import (  # noqa: E402
    AAII_COLUMNS,
    NAAIM_COLUMNS,
    append_observation,
    build_aaii_row,
    build_naaim_row,
    dedupe_and_sort,
    default_release_datetime,
    from_aaii_csv,
    from_naaim_xlsx,
    thursday_on_or_after,
)


def test_thursday_on_or_after() -> None:
    # 2026-08-10 is a Monday → Thursday 2026-08-13
    assert thursday_on_or_after(date(2026, 8, 10)) == date(2026, 8, 13)
    # already Thursday → unchanged
    assert thursday_on_or_after(date(2026, 8, 13)) == date(2026, 8, 13)
    # Friday → next Thursday
    assert thursday_on_or_after(date(2026, 8, 14)) == date(2026, 8, 20)


def test_default_release_datetime() -> None:
    naaim = default_release_datetime("naaim", date(2026, 8, 10))
    assert naaim.hour == 7
    assert naaim.date() == date(2026, 8, 13)

    aaii = default_release_datetime("aaii", date(2026, 8, 10))
    assert aaii.hour == 8

    with pytest.raises(ValueError):
        default_release_datetime("foo", date(2026, 8, 10))


def test_build_rows() -> None:
    naaim = build_naaim_row(date(2026, 8, 10), 72.5)
    assert naaim["exposure_index"] == 72.5
    assert naaim["available_at"].startswith("2026-08-13T07:00")

    naaim2 = build_naaim_row(date(2026, 8, 10), 70.0, available_at="2026-08-13T12:00:00")
    assert naaim2["available_at"].startswith("2026-08-13T12:00")

    aaii = build_aaii_row(date(2026, 8, 10), 35.0, 28.0, 37.0)
    assert aaii["bullish"] == 35.0
    assert aaii["available_at"].startswith("2026-08-13T08:00")


def test_dedupe_and_sort() -> None:
    df = pd.DataFrame([
        {"survey_week": "2026-08-10", "available_at": "2026-08-13T07:00:00",
         "exposure_index": 70.0, "source": "x", "license_status": "licensed",
         "publication_delay_days": 3},
        {"survey_week": "2026-08-03", "available_at": "2026-08-06T07:00:00",
         "exposure_index": 60.0, "source": "x", "license_status": "licensed",
         "publication_delay_days": 3},
        {"survey_week": "2026-08-10", "available_at": "2026-08-13T07:00:00",
         "exposure_index": 71.0, "source": "x", "license_status": "licensed",
         "publication_delay_days": 3},
    ])
    out = dedupe_and_sort(df, NAAIM_COLUMNS)
    assert len(out) == 2
    # sorted ascending by available_at; dedupe keeps the last (71.0)
    assert out.iloc[0]["survey_week"] == "2026-08-03"
    assert out.iloc[1]["exposure_index"] == 71.0


def test_append_observation_writes_and_dedupes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        append_observation(root, "naaim", build_naaim_row(date(2026, 8, 3), 60.0),
                           NAAIM_COLUMNS, "naaim.csv")
        append_observation(root, "naaim", build_naaim_row(date(2026, 8, 3), 61.0),
                           NAAIM_COLUMNS, "naaim.csv")
        append_observation(root, "naaim", build_naaim_row(date(2026, 8, 10), 70.0),
                           NAAIM_COLUMNS, "naaim.csv")

        df = pd.read_csv(root / "naaim.csv")
        assert len(df) == 2
        assert df.iloc[0]["exposure_index"] == 61.0  # deduped keep-last, sorted


def test_from_aaii_csv() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "aaii_export.csv"
        pd.DataFrame({
            "Date": ["2026-08-06", "2026-08-13"],
            "Bullish": [35.0, 40.0],
            "Neutral": [30.0, 28.0],
            "Bearish": [35.0, 32.0],
        }).to_csv(src, index=False)
        out = from_aaii_csv(src)
        assert list(out.columns) == AAII_COLUMNS
        assert len(out) == 2
        assert out.iloc[-1]["bullish"] == 40.0


def test_from_naaim_xlsx() -> None:
    pytest.importorskip("openpyxl")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "naaim.xlsx"
        pd.DataFrame({
            "Date": ["2026-08-05", "2026-08-12"],
            "Average": [70.0, 72.5],
        }).to_excel(src, index=False)
        out = from_naaim_xlsx(src)
        assert list(out.columns) == NAAIM_COLUMNS
        assert len(out) == 2
        assert out.iloc[-1]["exposure_index"] == 72.5
