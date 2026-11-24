"""Daily bar settlement must follow the captured source snapshot."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from lei_signal.api.bar_status import assess_bar_status
from lei_signal.api.card_mapper import is_intraday_forming
from lei_signal.api.portfolio_workspace import _forming


def _result(bar_day: date, timezone: str):
    return SimpleNamespace(
        price_data=SimpleNamespace(
            report=SimpleNamespace(last_date=bar_day),
            info=SimpleNamespace(timezone=timezone),
        )
    )


def test_cn_preclose_snapshot_stays_intraday_after_close_and_overnight() -> None:
    local = ZoneInfo("Asia/Shanghai")
    fetched = datetime(2026, 10, 15, 14, 30, tzinfo=local)
    result = _result(date(2026, 10, 15), "Asia/Shanghai")
    status = assess_bar_status(
        last_date=date(2026, 10, 15), fetched_at=fetched, timezone="Asia/Shanghai"
    )
    assert (status.status, status.reason) == ("intraday", "pre_close_snapshot")
    assert is_intraday_forming(result, fetched_at=fetched)
    for inspected_at in (
        datetime(2026, 10, 15, 20, tzinfo=local),
        datetime(2026, 10, 16, 9, tzinfo=local),
    ):
        assert _forming(result, "510300.SS", SimpleNamespace(fetched_at=fetched), inspected_at)


def test_cn_postclose_snapshot_is_closed() -> None:
    fetched = datetime(2026, 10, 15, 15, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
    status = assess_bar_status(
        last_date=date(2026, 10, 15), fetched_at=fetched, timezone="Asia/Shanghai"
    )
    assert (status.status, status.reason) == ("closed", "post_close_snapshot")
    result = _result(date(2026, 10, 15), "Asia/Shanghai")
    assert not is_intraday_forming(result, fetched_at=fetched)
    assert not _forming(result, "510300.SS", SimpleNamespace(fetched_at=fetched), fetched)


@pytest.mark.parametrize(
    "month,day,utc_hour,expected",
    [
        (1, 15, 20, "intraday"),  # 15:00 EST
        (1, 15, 21, "closed"),  # 16:00 EST
        (7, 15, 19, "intraday"),  # 15:00 EDT
        (7, 15, 20, "closed"),  # 16:00 EDT
    ],
)
def test_us_session_uses_eastern_daylight_saving(month, day, utc_hour, expected) -> None:
    status = assess_bar_status(
        last_date=date(2026, month, day),
        fetched_at=datetime(2026, month, day, utc_hour, tzinfo=UTC),
        timezone="America/New_York",
    )
    assert status.status == expected


def test_hong_kong_close() -> None:
    tz = ZoneInfo("Asia/Hong_Kong")
    bar_day = date(2026, 10, 15)
    assert (
        assess_bar_status(
            last_date=bar_day,
            fetched_at=datetime(2026, 10, 15, 15, 59, tzinfo=tz),
            timezone="Asia/Hong_Kong",
        ).status
        == "intraday"
    )
    assert (
        assess_bar_status(
            last_date=bar_day,
            fetched_at=datetime(2026, 10, 15, 16, 1, tzinfo=tz),
            timezone="Asia/Hong_Kong",
        ).status
        == "closed"
    )


def test_historical_bar_fetched_later_is_closed() -> None:
    status = assess_bar_status(
        last_date=date(2024, 6, 28),
        fetched_at=datetime(2026, 10, 15, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        timezone="Asia/Shanghai",
    )
    assert (status.status, status.reason) == ("closed", "later_market_day_snapshot")


def test_cache_fallback_run_time_cannot_certify_old_snapshot() -> None:
    status = assess_bar_status(
        last_date=date(2026, 10, 15),
        fetched_at=datetime(2026, 10, 15, 20, tzinfo=ZoneInfo("Asia/Shanghai")),
        timezone="Asia/Shanghai",
        cache_fallback_used=True,
    )
    assert (status.status, status.reason) == ("unknown", "cache_source_time_unknown")


@pytest.mark.parametrize(
    "last_date,fetched_at,timezone,reason",
    [
        (None, datetime(2026, 10, 15, tzinfo=UTC), "Asia/Shanghai", "missing_bar_date"),
        (date(2026, 10, 15), None, "Asia/Shanghai", "missing_fetch_time"),
        (date(2026, 10, 15), datetime(2026, 10, 15), "Asia/Shanghai", "invalid_fetch_time"),
        (date(2026, 10, 15), datetime(2026, 10, 15, tzinfo=UTC), None, "unsupported_timezone"),
        (date(2026, 10, 15), datetime(2026, 10, 15, tzinfo=UTC), "UTC", "unsupported_timezone"),
        (
            date(2026, 10, 16),
            datetime(2026, 10, 15, tzinfo=UTC),
            "Asia/Shanghai",
            "fetch_before_bar_date",
        ),
    ],
)
def test_missing_or_inconsistent_provenance_is_unknown(
    last_date, fetched_at, timezone, reason
) -> None:
    status = assess_bar_status(last_date=last_date, fetched_at=fetched_at, timezone=timezone)
    assert (status.status, status.reason) == ("unknown", reason)
