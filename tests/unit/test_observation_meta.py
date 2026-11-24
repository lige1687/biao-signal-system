from datetime import UTC, datetime, timedelta

from lei_signal.fundamentals.observation_meta import observation_item


BASE = dict(metric_id="x", label="X", market="us", universe="test", unit="%",
            source_name="test", source_url=None, source_access="test")


def test_future_date_is_rejected_not_marked_current():
    future = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    item = observation_item(**BASE, value=2.0, change=0.5, observation_date=future)
    assert item["quality_status"] == "missing"
    assert item["value"] is None and item["change"] is None
    assert "未来" in item["quality_reason"]


def test_missing_is_null_with_reason():
    item = observation_item(**BASE, quality_reason="无可信来源")
    assert item["value"] is None
    assert item["quality_status"] == "missing"
    assert item["quality_reason"] == "无可信来源"


def test_unknown_publication_stays_unverified():
    today = datetime.now(UTC).date().isoformat()
    item = observation_item(**BASE, value=2.0, observation_date=today)
    assert item["quality_status"] == "time_unverified"
    assert item["published_at"] is None
    assert item["publication_precision"] == "unknown"


def test_non_finite_value_and_change_are_removed():
    item = observation_item(**BASE, value=float("nan"), change=2.0)
    assert item["quality_status"] == "missing"
    assert item["value"] is None and item["change"] is None
    item = observation_item(**BASE, value=2.0, change=float("inf"))
    assert item["quality_status"] == "time_unverified"
    assert item["value"] == 2.0 and item["change"] is None
