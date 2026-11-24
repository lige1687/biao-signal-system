from datetime import date, timedelta

import pytest

from lei_signal.research.us_erp_sigma_observation import (
    attach_events,
    conditional_baseline,
    erp_events,
    price_rows,
    validate_series,
    years_before,
)


def test_calendar_warmup_and_strict_crossing():
    start = date(2017, 1, 2)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(1100)]
    values = [float(i % 2) for i in range(1100)]
    values[-2] = 0.5  # At the 1.5σ upper rail: no crossing yet.
    values[-1] = 3.0
    events = erp_events(list(zip(dates, values)))
    assert {e["sigma"] for e in events if e["date"] == dates[-1]} == {1.5, 2.0}
    assert years_before("2020-02-29") == "2017-02-28"
    assert not [e for e in events if e["date"] < "2020-01-02"]


def test_label_start_maturity_and_worst_loss_exclude_signal_and_entry():
    dates = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(330)]
    prices = [100.0 + i for i in range(330)]
    prices[199], prices[200], prices[201], prices[202] = 20, 100, 90, 110
    rows = price_rows(list(zip(dates, prices)))
    row = next(r for r in rows if r["date"] == dates[199])
    assert row["labels"]["21"]["entry_date"] == dates[200]
    assert row["labels"]["21"]["end_date"] == dates[221]
    assert row["labels"]["21"]["worst_loss_pct"] == pytest.approx(-10.0)
    assert "126" in row["labels"]
    final = rows[-1]
    assert "21" not in final["labels"]
    assert "63" not in final["labels"]
    assert "126" not in final["labels"]


def test_cooldown_per_sigma_and_direction_and_common_condition_support():
    dates = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(280)]
    prices = [(100 + i * 0.1) for i in range(280)]
    rows = price_rows(list(zip(dates, prices)))
    sample_days = [dates[200], dates[210], dates[265]]
    events = [{"date": d, "sigma": s, "kind": "upper", "id": f"{s}:{d}:upper"}
              for d in sample_days for s in (1.5, 2.0)]
    joined = attach_events(events, rows, dates)
    assert sum(e["cooldown_keep"] for e in joined) == 4  # first and >=63 sessions, each sigma
    assert sum(e["cooldown_keep"] for e in joined if e["sigma"] == 1.5) == 2
    eligible = [r for r in rows if "21" in r["labels"]]
    comparison = conditional_baseline([joined[0]], eligible, "upper", 21)
    assert comparison["n"] == 1
    assert comparison["baseline_state_support"][joined[0]["state"]] > 0


def test_reject_duplicate_dates_and_missing_values():
    with pytest.raises(ValueError):
        validate_series({"dates": ["2020-01-01", "2020-01-01"], "values": [1, 2]})
    with pytest.raises(ValueError):
        validate_series({"dates": ["2020-01-01"], "values": [None]})
