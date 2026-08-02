"""Task 5 unit tests — NAAIM and AAII point-in-time sentiment."""

from __future__ import annotations

import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.market_context.sentiment import (
    SentimentLabel,
    classify_sentiment_percentile,
    latest_available_sentiment,
    load_aaii_observations,
    load_naaim_observations,
)

# ── NAAIM tests ───────────────────────────────────────────────────────


class TestNAAIM:
    def test_loads_valid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "naaim.csv"
            df = pd.DataFrame({
                "survey_week": ["2024-01-01", "2024-01-08"],
                "available_at": ["2024-01-03T07:00:00", "2024-01-10T07:00:00"],
                "exposure_index": [75.5, 80.2],
                "source": ["official", "official"],
                "license_status": ["licensed", "licensed"],
                "publication_delay_days": [2, 2],
            })
            df.to_csv(path, index=False)

            obs = load_naaim_observations(path)
            assert len(obs) == 2
            assert obs[0].series_id == "NAAIM"
            assert obs[0].exposure_index == 75.5
            assert obs[0].available_at.hour == 7

    def test_missing_available_at_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "naaim.csv"
            df = pd.DataFrame({
                "survey_week": ["2024-01-01"],
                "exposure_index": [75.5],
                "source": ["official"],
                "license_status": ["licensed"],
                "publication_delay_days": [2],
            })
            df.to_csv(path, index=False)

            with pytest.raises(ValueError, match="available_at"):
                load_naaim_observations(path)

    def test_not_visible_before_release(self) -> None:
        """An observation with available_at=Thursday 07:00 is invisible Wednesday."""
        obs_list = [
            type("SentimentObservation", (), {
                "series_id": "NAAIM",
                "survey_week": date(2024, 6, 10),
                "available_at": datetime(2024, 6, 13, 7, 0, tzinfo=UTC),
                "source": "official",
                "license_status": "licensed",
                "publication_delay_days": 3,
                "current_eligible": True,
                "exposure_index": 80.0,
                "percentile": 50.0,
                "label": SentimentLabel.NEUTRAL,
                "bullish": None,
                "neutral_val": None,
                "bearish": None,
                "bull_bear": None,
            })(),
        ]

        # Wednesday before release
        wed = datetime(2024, 6, 12, 16, 0, tzinfo=UTC)
        result = latest_available_sentiment(obs_list, wed, max_age_days=14)
        assert result is None

        # Thursday after release
        thu = datetime(2024, 6, 13, 16, 0, tzinfo=UTC)
        result = latest_available_sentiment(obs_list, thu, max_age_days=14)
        assert result is not None
        assert result.exposure_index == 80.0


# ── AAII tests ────────────────────────────────────────────────────────


class TestAAII:
    def test_loads_valid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aaii.csv"
            df = pd.DataFrame({
                "survey_week": ["2024-01-04"],
                "available_at": ["2024-01-10T08:00:00"],
                "bullish": [35.5],
                "neutral": [30.0],
                "bearish": [34.5],
                "source": ["official"],
                "license_status": ["licensed"],
            })
            df.to_csv(path, index=False)

            obs = load_aaii_observations(path)
            assert len(obs) == 1
            assert obs[0].series_id == "AAII"
            assert obs[0].bull_bear == pytest.approx(1.0)  # 35.5 - 34.5
            assert obs[0].bullish == 35.5

    def test_missing_available_at_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aaii.csv"
            df = pd.DataFrame({
                "survey_week": ["2024-01-04"],
                "bullish": [35.5],
                "neutral": [30.0],
                "bearish": [34.5],
                "source": ["official"],
                "license_status": ["licensed"],
            })
            df.to_csv(path, index=False)

            with pytest.raises(ValueError, match="available_at"):
                load_aaii_observations(path)


# ── Sentiment percentile tests ─────────────────────────────────────────


class TestSentimentPercentile:
    def test_extreme_low(self) -> None:
        label = classify_sentiment_percentile(5.0, list(range(100)), min_periods=52)
        assert label == SentimentLabel.EXTREME_LOW

    def test_low(self) -> None:
        label = classify_sentiment_percentile(20.0, list(range(100)), min_periods=52)
        assert label == SentimentLabel.LOW

    def test_neutral(self) -> None:
        label = classify_sentiment_percentile(50.0, list(range(100)), min_periods=52)
        assert label == SentimentLabel.NEUTRAL

    def test_high(self) -> None:
        label = classify_sentiment_percentile(80.0, list(range(100)), min_periods=52)
        assert label == SentimentLabel.HIGH

    def test_extreme_high(self) -> None:
        label = classify_sentiment_percentile(95.0, list(range(100)), min_periods=52)
        assert label == SentimentLabel.EXTREME_HIGH

    def test_insufficient_history_returns_unknown(self) -> None:
        label = classify_sentiment_percentile(50.0, list(range(30)), min_periods=52)
        assert label == SentimentLabel.UNKNOWN
