"""Classify a daily bar using the snapshot that actually supplied it."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BarState = Literal["closed", "intraday", "unknown"]

_MARKET_CLOSE = {
    "Asia/Shanghai": time(15),
    "Asia/Hong_Kong": time(16),
    "America/New_York": time(16),
}


@dataclass(frozen=True, slots=True)
class BarStatus:
    status: BarState
    reason: str


def assess_bar_status(
    *,
    last_date: date | datetime | None,
    fetched_at: datetime | None,
    timezone: str | None,
    cache_fallback_used: bool = False,
) -> BarStatus:
    """Assess a daily bar from its exchange date and actual fetch timestamp.

    A pre-close snapshot remains intraday even if inspected on a later day.
    The current clock cannot establish whether cached prices ever settled.
    """
    if last_date is None:
        return BarStatus("unknown", "missing_bar_date")
    if cache_fallback_used:
        # AnalysisEntry.fetched_at marks the analysis run, not the original
        # source snapshot when Parquet fallback supplied the bars.
        return BarStatus("unknown", "cache_source_time_unknown")
    if not isinstance(last_date, date):
        return BarStatus("unknown", "invalid_bar_date")
    if fetched_at is None:
        return BarStatus("unknown", "missing_fetch_time")
    if (
        not isinstance(fetched_at, datetime)
        or fetched_at.tzinfo is None
        or fetched_at.utcoffset() is None
    ):
        return BarStatus("unknown", "invalid_fetch_time")
    if timezone not in _MARKET_CLOSE:
        return BarStatus("unknown", "unsupported_timezone")
    try:
        market_tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return BarStatus("unknown", "unsupported_timezone")

    bar_day = last_date.date() if isinstance(last_date, datetime) else last_date
    local_fetch = fetched_at.astimezone(market_tz)
    if local_fetch.date() < bar_day:
        return BarStatus("unknown", "fetch_before_bar_date")
    if local_fetch.date() > bar_day:
        return BarStatus("closed", "later_market_day_snapshot")
    if local_fetch.time() >= _MARKET_CLOSE[timezone]:
        return BarStatus("closed", "post_close_snapshot")
    return BarStatus("intraday", "pre_close_snapshot")
