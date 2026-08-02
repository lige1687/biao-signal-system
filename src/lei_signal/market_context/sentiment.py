"""NAAIM and AAII sentiment data loaders and classifiers — Round 4.

Design spec sections 10, 10.1, 10.2, 10.3, 16.1.

Loads CSV/Parquet files with release-time alignment.
No web scraping. Sentiment observations are only visible at their
real `available_at` timestamp. Missing data and stale observations
are reported explicitly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

from lei_signal.market_context.types import SentimentLabel, SentimentObservation


# ── Required columns ──────────────────────────────────────────────────

_NAAIM_REQUIRED = {
    "survey_week", "available_at", "exposure_index",
    "source", "license_status", "publication_delay_days",
}

_AAII_REQUIRED = {
    "survey_week", "available_at",
    "bullish", "neutral", "bearish",
    "source", "license_status",
}


# ── NAAIM loader ──────────────────────────────────────────────────────


def load_naaim_observations(path: str | Path) -> tuple[SentimentObservation, ...]:
    """Load NAAIM Exposure Index observations from CSV/Parquet.

    Required columns: survey_week, available_at, exposure_index,
    source, license_status, publication_delay_days.

    Raises ValueError if required columns are missing or if available_at
    is absent.
    """
    path = Path(path)
    df = _load_file(path)

    # Validate columns
    missing = _NAAIM_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required NAAIM columns: {missing}")

    observations: list[SentimentObservation] = []

    for _, row in df.iterrows():
        available_at = _parse_available_at(row["available_at"], "NAAIM")
        survey_week = _parse_date(row["survey_week"])

        observations.append(SentimentObservation(
            series_id="NAAIM",
            survey_week=survey_week,
            available_at=available_at,
            source=str(row["source"]),
            license_status=str(row["license_status"]),
            publication_delay_days=int(row.get("publication_delay_days", 0)),
            current_eligible=_is_current_eligible(
                str(row["license_status"]),
                available_at,
                max_delay_days=14,
            ),
            exposure_index=float(row["exposure_index"]),
            percentile=None,
            label=SentimentLabel.UNKNOWN,
        ))

    # Compute percentiles across all observations
    _compute_percentiles(observations)

    return tuple(observations)


# ── AAII loader ───────────────────────────────────────────────────────


def load_aaii_observations(path: str | Path) -> tuple[SentimentObservation, ...]:
    """Load AAII Investor Sentiment observations from CSV/Parquet.

    Required columns: survey_week, available_at, bullish, neutral, bearish,
    source, license_status.

    Raises ValueError if required columns are missing or if available_at
    is absent.
    """
    path = Path(path)
    df = _load_file(path)

    missing = _AAII_REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing required AAII columns: {missing}")

    observations: list[SentimentObservation] = []

    for _, row in df.iterrows():
        available_at = _parse_available_at(row["available_at"], "AAII")
        survey_week = _parse_date(row["survey_week"])
        bullish = float(row["bullish"])
        neutral_val = float(row["neutral"])
        bearish = float(row["bearish"])

        observations.append(SentimentObservation(
            series_id="AAII",
            survey_week=survey_week,
            available_at=available_at,
            source=str(row["source"]),
            license_status=str(row["license_status"]),
            publication_delay_days=None,
            current_eligible=_is_current_eligible(
                str(row["license_status"]),
                available_at,
                max_delay_days=10,
            ),
            bullish=bullish,
            neutral=neutral_val,
            bearish=bearish,
            bull_bear=bullish - bearish,
            percentile=None,
            label=SentimentLabel.UNKNOWN,
        ))

    # Compute percentiles
    _compute_percentiles(observations)

    return tuple(observations)


# ── Availability helpers ──────────────────────────────────────────────


def latest_available_sentiment(
    observations: Sequence[SentimentObservation],
    decision_at: datetime,
    max_age_days: int,
) -> SentimentObservation | None:
    """Return the most recent sentiment observation visible at decision_at.

    An observation is visible if available_at <= decision_at and
    decision_at - available_at <= max_age_days.

    Args:
        observations: All loaded sentiment observations.
        decision_at: The decision timestamp (timezone-aware).
        max_age_days: Maximum allowed age in calendar days.

    Returns:
        The latest visible observation, or None if none qualify.
    """
    # Ensure decision_at is timezone-aware
    if decision_at.tzinfo is None:
        decision_at = decision_at.replace(tzinfo=timezone.utc)

    visible: list[SentimentObservation] = []
    for obs in observations:
        if obs.available_at.tzinfo is None:
            obs_avail = obs.available_at.replace(tzinfo=timezone.utc)
        else:
            obs_avail = obs.available_at

        if obs_avail <= decision_at:
            age = decision_at - obs_avail
            if age.days <= max_age_days:
                visible.append(obs)

    if not visible:
        return None

    # Return the most recent by available_at
    return max(visible, key=lambda o: o.available_at)


def classify_sentiment_percentile(
    value: float,
    history: Sequence[float],
    *,
    min_periods: int = 52,
) -> SentimentLabel:
    """Classify sentiment percentile into a labeled band.

    Rules:
      percentile <= 10% → extreme_low
      percentile <= 25% → low
      percentile >= 90% → extreme_high
      percentile >= 75% → high
      otherwise → neutral
      fewer than min_periods → unknown
    """
    if len(history) < min_periods:
        return SentimentLabel.UNKNOWN

    # Compute percentile rank of value in history
    rank = sum(1 for h in history if h <= value)
    percentile = rank / len(history) * 100.0

    if percentile <= 10.0:
        return SentimentLabel.EXTREME_LOW
    if percentile <= 25.0:
        return SentimentLabel.LOW
    if percentile >= 90.0:
        return SentimentLabel.EXTREME_HIGH
    if percentile >= 75.0:
        return SentimentLabel.HIGH
    return SentimentLabel.NEUTRAL


# ── Internal helpers ──────────────────────────────────────────────────


def _load_file(path: Path) -> pd.DataFrame:
    """Load CSV or Parquet."""
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _parse_date(val) -> date:
    """Parse a date value."""
    ts = pd.Timestamp(val)
    return ts.date()


def _parse_available_at(val: str, series: str) -> datetime:
    """Parse available_at. Must be present and timezone-aware or UTC."""
    if pd.isna(val) or str(val).strip() == "":
        raise ValueError(
            f"Missing available_at for {series} observation. "
            f"available_at is required and must not be empty or default to survey_week."
        )
    ts = pd.Timestamp(val)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC").to_pydatetime()
    return ts.to_pydatetime()


def _is_current_eligible(
    license_status: str,
    available_at: datetime,
    max_delay_days: int,
) -> bool:
    """Determine if an observation is eligible for current summary.

    Public delayed data (with multi-month delay) is not current-eligible.
    Licensed data within max_delay_days of now is current-eligible.
    """
    status = license_status.lower()
    if "public_delayed" in status:
        return False

    now = datetime.now(timezone.utc)
    age = now - available_at
    return age.days <= max_delay_days


def _compute_percentiles(observations: list[SentimentObservation]) -> None:
    """Compute rolling percentiles for a list of observations.

    For each observation (sorted by available_at), compute its percentile
    rank against all prior observations. Uses exposure_index for NAAIM
    and bull_bear for AAII.
    """
    sorted_obs = sorted(observations, key=lambda o: o.available_at)

    for i, obs in enumerate(sorted_obs):
        if obs.series_id == "NAAIM" and obs.exposure_index is not None:
            values = [o.exposure_index for o in sorted_obs[:i] if o.exposure_index is not None]
            value = obs.exposure_index
        elif obs.series_id == "AAII" and obs.bull_bear is not None:
            values = [o.bull_bear for o in sorted_obs[:i] if o.bull_bear is not None]
            value = obs.bull_bear
        else:
            continue

        if len(values) < 52:
            obs = SentimentObservation(
                series_id=obs.series_id,
                survey_week=obs.survey_week,
                available_at=obs.available_at,
                source=obs.source,
                license_status=obs.license_status,
                publication_delay_days=obs.publication_delay_days,
                current_eligible=obs.current_eligible,
                exposure_index=obs.exposure_index,
                bullish=obs.bullish,
                neutral=obs.neutral,
                bearish=obs.bearish,
                bull_bear=obs.bull_bear,
                percentile=None,
                label=SentimentLabel.UNKNOWN,
            )
            observations[i] = obs
            continue

        rank = sum(1 for v in values if v <= value)
        percentile = rank / len(values) * 100.0

        label = _percentile_label(percentile, len(values))

        obs_new = SentimentObservation(
            series_id=obs.series_id,
            survey_week=obs.survey_week,
            available_at=obs.available_at,
            source=obs.source,
            license_status=obs.license_status,
            publication_delay_days=obs.publication_delay_days,
            current_eligible=obs.current_eligible,
            exposure_index=obs.exposure_index,
            bullish=obs.bullish,
            neutral=obs.neutral,
            bearish=obs.bearish,
            bull_bear=obs.bull_bear,
            percentile=percentile,
            label=label,
        )
        observations[i] = obs_new


def _percentile_label(percentile: float, history_len: int) -> SentimentLabel:
    """Map percentile to label."""
    if history_len < 52:
        return SentimentLabel.UNKNOWN
    if percentile <= 10.0:
        return SentimentLabel.EXTREME_LOW
    if percentile <= 25.0:
        return SentimentLabel.LOW
    if percentile >= 90.0:
        return SentimentLabel.EXTREME_HIGH
    if percentile >= 75.0:
        return SentimentLabel.HIGH
    return SentimentLabel.NEUTRAL
