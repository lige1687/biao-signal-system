"""Market breadth calculation — Round 4.

Computes Breadth20/50/200 for a given universe on a given as_of date,
with independent denominators, coverage tracking, stale-session handling,
and point-in-time constraints.

Design spec sections 6, 6.1, 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.market_context.types import (
    BreadthSnapshot,
    ContextDataStatus,
    MarketId,
    UniverseSnapshot,
)


@dataclass(frozen=True)
class BreadthConfig:
    """Configuration for breadth calculation.

    ma_windows: cycle periods for breadth calculation (N-day MA).
    minimum_coverage: below this ratio, the horizon is DATA_INCOMPLETE.
    stale_sessions: max market sessions a missing symbol can be carried forward.
      0 disables carry-forward (always exclude immediately).
    percentile_lookback: trailing window for rolling percentile.
    percentile_min_periods: minimum observations for a valid percentile.
    """

    ma_windows: tuple[int, ...] = (20, 50, 200)
    minimum_coverage: float = 0.90
    stale_sessions: int = 5
    percentile_lookback: int = 1260
    percentile_min_periods: int = 252


def _rolling_mean(series: pd.Series, window: int) -> pd.Series:
    """Compute rolling MA using actual observed bars only (no forward fill of NaN)."""
    return series.rolling(window=window, min_periods=window).mean()


def _session_axis(history: pd.DataFrame, as_of: date) -> pd.DatetimeIndex | None:
    """Sorted session axis of `history`, with `as_of` guaranteed present."""
    if history.empty or not isinstance(history.index, pd.DatetimeIndex):
        return None
    ts = pd.Timestamp(as_of)
    axis = history.index.sort_values()
    if ts not in axis:
        axis = axis.append(pd.DatetimeIndex([ts])).sort_values()
    return axis


def value_sessions_back(
    history: pd.DataFrame,
    column: str,
    *,
    as_of: date,
    sessions_back: int,
) -> float | None:
    """Value of `column` exactly `sessions_back` real sessions before `as_of`.

    The session axis is `history`'s own index, so business-day arithmetic and
    calendar gaps can never shift the reference point. Returns None when the
    axis is too short — an approximate reference is worse than no reading.
    """
    axis = _session_axis(history, as_of)
    if axis is None or column not in history.columns:
        return None
    pos = int(axis.get_loc(pd.Timestamp(as_of)))
    ref_pos = pos - sessions_back
    if ref_pos < 0:
        return None
    ref_ts = axis[ref_pos]
    if ref_ts not in history.index:
        return None
    raw = history.at[ref_ts, column]
    if raw is None or pd.isna(raw):
        return None
    return float(raw)


def breadth_delta(
    history: pd.DataFrame,
    column: str,
    *,
    as_of: date,
    sessions_back: int,
    current: float | None = None,
) -> float | None:
    """Change in `column` over exactly `sessions_back` sessions ending at `as_of`.

    `current` supplies the as_of reading for a snapshot not yet written into
    `history`; without it, `as_of` must itself be a row in `history`.
    """
    if current is None:
        if history.empty or not isinstance(history.index, pd.DatetimeIndex):
            return None
        ts = pd.Timestamp(as_of)
        if ts not in history.index or column not in history.columns:
            return None
        raw = history.at[ts, column]
        if raw is None or pd.isna(raw):
            return None
        current = float(raw)

    reference = value_sessions_back(
        history, column, as_of=as_of, sessions_back=sessions_back
    )
    if reference is None:
        return None
    return current - reference


def rolling_percentile_at(
    values: pd.Series,
    *,
    as_of: date,
    lookback: int,
    min_periods: int,
) -> float | None:
    """Point-in-time percentile rank of the `as_of` reading within its history.

    Only observations dated at or before `as_of` are visible, so appending
    later sessions can never change a percentile already published.
    """
    if values.empty or not isinstance(values.index, pd.DatetimeIndex):
        return None
    visible = values[values.index <= pd.Timestamp(as_of)].dropna()
    if len(visible) < min_periods:
        return None
    window = visible.iloc[-lookback:]
    current = float(window.iloc[-1])
    return float((window <= current).sum()) / len(window) * 100.0


def compute_breadth_snapshot(
    *,
    universe: UniverseSnapshot,
    bars_by_symbol: dict[str, pd.DataFrame],
    sessions: pd.DatetimeIndex,
    as_of: date,
    config: BreadthConfig | None = None,
) -> BreadthSnapshot:
    """Compute a single breadth snapshot for the given universe on as_of.

    Args:
        universe: Point-in-time universe membership snapshot.
        bars_by_symbol: OHLCV DataFrames keyed by symbol, each with 'close' column
                        and DatetimeIndex. Must be pre-cropped at as_of.
        sessions: Full market session DatetimeIndex for stale-session tracking.
        as_of: The decision date.
        config: Breadth calculation parameters. None uses defaults.

    Returns:
        BreadthSnapshot with all three breadth values, eligibility counts,
        coverage ratios, and provenance metadata.
    """
    if config is None:
        config = BreadthConfig()
    constituent_count = len(universe.symbols)
    windows = config.ma_windows

    # Find as_of position in sessions
    as_of_ts = pd.Timestamp(as_of)
    try:
        as_of_pos = sessions.get_loc(as_of_ts)
    except KeyError:
        # as_of might not be exactly in sessions; find the closest <= as_of
        as_of_pos = sessions[sessions <= as_of_ts].size - 1
        if as_of_pos < 0:
            # No session data before as_of
            return _empty_snapshot(universe, as_of, config, constituent_count)

    # For each symbol, determine if close > MA(N) for each N
    eligible: dict[int, int] = {}
    above: dict[int, int] = {}
    missing: dict[int, int] = {}

    for w in windows:
        eligible[w] = 0
        above[w] = 0
        missing[w] = 0

    for sym in universe.symbols:
        if sym not in bars_by_symbol:
            # Symbol not in bars — check if it can be carried forward (stale)
            for w in windows:
                missing[w] += 1
            continue

        frame = bars_by_symbol[sym]
        close = frame["close"]

        # Check if the symbol has recent data or is stale
        if config.stale_sessions > 0 and len(close) > 0:
            last_bar_idx = close.index[-1]
            last_bar_pos = sessions.get_loc(last_bar_idx) if last_bar_idx in sessions else -1
            if last_bar_pos >= 0:
                sessions_gap = as_of_pos - last_bar_pos
                if sessions_gap > config.stale_sessions:
                    # Too stale — exclude from all windows
                    for w in windows:
                        missing[w] += 1
                    continue
                # else: within stale window — use last known state
        elif len(close) == 0:
            for w in windows:
                missing[w] += 1
            continue

        # For each window, check eligibility and MA comparison
        for w in windows:
            if len(close) >= w:
                # Compute MA using last w bars (actual bars only)
                ma = _rolling_mean(close, w)
                last_ma = ma.iloc[-1]
                last_close = close.iloc[-1]

                if pd.notna(last_ma):
                    eligible[w] += 1
                    if last_close > last_ma:
                        above[w] += 1
                    # close <= MA → not above
                else:
                    missing[w] += 1
            else:
                # Not enough bars for this window
                missing[w] += 1

    # Build result
    coverage: dict[int, float] = {}
    breadth: dict[int, float | None] = {}

    for w in windows:
        if constituent_count > 0:
            coverage[w] = eligible[w] / constituent_count
        else:
            coverage[w] = 0.0

        # Always compute breadth if we have eligible symbols (even if below coverage threshold)
        # The coverage check controls data_status, not whether we compute the value
        if eligible[w] > 0:
            breadth[w] = (above[w] / eligible[w]) * 100.0
        else:
            breadth[w] = None

    # Determine overall data status
    any_incomplete = any(
        coverage[w] < config.minimum_coverage for w in windows
    )
    data_status = ContextDataStatus.INCOMPLETE if any_incomplete else ContextDataStatus.COMPLETE

    return BreadthSnapshot(
        market_id=universe.market_id,
        as_of=as_of,
        available_at=as_of,  # same-day availability for breadth
        universe_version=universe.universe_version,
        constituent_count=constituent_count,
        eligible_20=eligible.get(20, 0),
        eligible_50=eligible.get(50, 0),
        eligible_200=eligible.get(200, 0),
        missing_20=missing.get(20, 0),
        missing_50=missing.get(50, 0),
        missing_200=missing.get(200, 0),
        coverage_20=coverage.get(20, 0.0),
        coverage_50=coverage.get(50, 0.0),
        coverage_200=coverage.get(200, 0.0),
        breadth_20=breadth.get(20),
        breadth_50=breadth.get(50),
        breadth_200=breadth.get(200),
        source_kind=universe.source_kind,
        provenance=universe.source,
        data_status=data_status,
    )


def _empty_snapshot(
    universe: UniverseSnapshot,
    as_of: date,
    config: BreadthConfig,
    constituent_count: int,
) -> BreadthSnapshot:
    """Return a snapshot with zero eligibility when no session data is available."""
    return BreadthSnapshot(
        market_id=universe.market_id,
        as_of=as_of,
        available_at=as_of,
        universe_version=universe.universe_version,
        constituent_count=constituent_count,
        eligible_20=0, eligible_50=0, eligible_200=0,
        missing_20=constituent_count, missing_50=constituent_count, missing_200=constituent_count,
        coverage_20=0.0, coverage_50=0.0, coverage_200=0.0,
        breadth_20=None, breadth_50=None, breadth_200=None,
        source_kind=universe.source_kind,
        provenance=universe.source,
        data_status=ContextDataStatus.UNAVAILABLE,
    )


def build_breadth_history(
    *,
    universe_provider,
    bars_provider,
    market_id: MarketId,
    sessions: pd.DatetimeIndex,
    start: date,
    end: date,
    config: BreadthConfig | None = None,
) -> pd.DataFrame:
    """Build a breadth history DataFrame from start to end.

    Returns a DataFrame with columns for each breadth value, coverage,
    eligibility, universe_version, etc., indexed by date.
    """
    if config is None:
        config = BreadthConfig()
    records: list[dict] = []

    for as_of in pd.date_range(start, end, freq="B"):
        as_of_date = as_of.date()
        if as_of_date not in sessions:
            continue

        try:
            universe_snap = universe_provider.snapshot(market_id, as_of_date)
        except Exception:
            continue

        bars_result = bars_provider.load_components(
            set(universe_snap.symbols), as_of_date
        )

        snap = compute_breadth_snapshot(
            universe=universe_snap,
            bars_by_symbol=bars_result.bars_by_symbol,
            sessions=sessions,
            as_of=as_of_date,
            config=config,
        )

        records.append({
            "date": as_of_date,
            "breadth_20": snap.breadth_20,
            "breadth_50": snap.breadth_50,
            "breadth_200": snap.breadth_200,
            "coverage_20": snap.coverage_20,
            "coverage_50": snap.coverage_50,
            "coverage_200": snap.coverage_200,
            "eligible_20": snap.eligible_20,
            "eligible_50": snap.eligible_50,
            "eligible_200": snap.eligible_200,
            "constituent_count": snap.constituent_count,
            "universe_version": snap.universe_version,
        })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    return df
