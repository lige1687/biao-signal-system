"""Boundary tests for saved hourly-confirmation price-path comparisons."""

from copy import deepcopy

import pytest

from lei_signal.research.hourly_confirmation_increment import evaluate_asset


def payload(prices=(100, 90, 110, 120, 130), *, status="confirmed", terminal="2024-01-03",
            confirmation="2024-01-03", first="2024-01-01"):
    days = [f"2024-01-{n:02d}" for n in range(1, len(prices) + 1)]
    return {
        "asset": {"code": "example", "name": "example", "group": "stock"},
        "daily": [{"date": day, "qualified": True, "adjusted_close": price,
                   "adjusted_low": price}
                  for day, price in zip(days, prices, strict=True)],
        "waits": [{"identity_key": "bottom-1", "first_seen": first, "status": status,
                   "terminal_date": terminal, "confirmation_date": confirmation,
                   "confirmation_time": "10:30" if status == "confirmed" else None,
                   "confirmation_adjusted_close": 110 if status == "confirmed" else None,
                   "wait_observed_hours": 7, "anchor_adjusted_low": 70}],
    }


def one(data, horizon=2):
    return evaluate_asset(data, horizons=(horizon,))["event_rows"][0]


def test_exact_horizon_and_close_only_risk_excludes_pre_entry_decline():
    row = one(payload())
    assert row["horizon_date"] == "2024-01-03"
    assert row["baseline_return_pct"] == pytest.approx(10)
    assert row["candidate_entry_date"] == "2024-01-03"
    assert row["candidate_entry_time"] == "10:30"
    assert row["candidate_entry_close"] == 110
    assert row["candidate_return_pct"] == 0
    assert row["baseline_risk_pct"] == pytest.approx(10)
    assert row["candidate_risk_pct"] == 0
    assert row["participation_price_change_pct"] == pytest.approx(10)
    assert row["confirmation_wait_hours"] == 7
    assert row["delta_pp"] == pytest.approx(-10)


def test_initial_unknown_is_never_zero_or_paired():
    row = one(payload(status="initial_unknown", terminal="2024-01-01", confirmation=None))
    assert row["reason"] == "initial_hour_unknown"
    assert row["baseline_return_pct"] == pytest.approx(10)
    assert row["candidate_return_pct"] is None
    assert row["delta_pp"] is None


@pytest.mark.parametrize("status,terminal,confirmation", [
    ("confirmed", "2024-01-04", "2024-01-04"),
    ("broken_before_confirm", "2024-01-02", None),
    ("censored", "2024-01-05", None),
])
def test_no_participation_can_miss_subsequent_rise(status, terminal, confirmation):
    row = one(payload(status=status, terminal=terminal, confirmation=confirmation))
    assert row["qualification"] == "paired"
    assert row["candidate_return_pct"] == 0
    assert row["missed_upside_pp"] == pytest.approx(10)
    assert row["avoided_downside_pp"] == 0
    assert row["delta_pp"] == pytest.approx(-10)


@pytest.mark.parametrize("status", ["data_gap", "same_day_ambiguous"])
def test_hour_failure_inside_horizon_unknown_after_horizon_irrelevant(status):
    inside = one(payload(status=status, terminal="2024-01-02", confirmation=None))
    assert inside["qualification"] == "unknown"
    assert inside["candidate_return_pct"] is None
    after = one(payload(status=status, terminal="2024-01-04", confirmation=None))
    assert after["qualification"] == "paired"
    assert after["candidate_return_pct"] == 0


def test_missing_price_gap_cross_period_and_immaturity_preserve_counts():
    missing = payload()
    missing["daily"][1]["adjusted_close"] = None
    assert one(missing)["reason"] == "missing_price"
    gap = payload()
    gap["daily"][1]["qualified"] = False
    assert one(gap)["reason"] == "daily_gap"
    short = payload(prices=(100, 101))
    assert one(short)["reason"] == "immature_horizon"
    crossing = payload(prices=(100, 101, 102), first="2024-01-01")
    crossing["daily"] = [
        {"date": "2023-12-29", "qualified": True, "adjusted_close": 100},
        {"date": "2023-12-30", "qualified": True, "adjusted_close": 101},
        {"date": "2024-01-02", "qualified": True, "adjusted_close": 102},
    ]
    crossing["waits"][0]["first_seen"] = "2023-12-29"
    result = evaluate_asset(crossing, horizons=(2,))
    assert result["event_rows"][0]["reason"] == "crosses_period"
    assert result["qualification_counts"]["2:2021-2023"]["unknown"] == 1
    absent = payload(first="2024-02-01")
    assert one(absent)["reason"] == "missing_start"


def test_nonparticipant_avoided_downside_and_contribution_identity():
    down = one(payload(prices=(100, 90, 80), status="broken_before_confirm",
                       terminal="2024-01-02", confirmation=None))
    assert down["baseline_return_pct"] == pytest.approx(-20)
    assert down["avoided_downside_pp"] == pytest.approx(20)
    for row in (down, one(payload())):
        assert row["delta_pp"] == pytest.approx(
            -row["missed_upside_pp"] + row["avoided_downside_pp"] + row["timing_delta_pp"]
        )


def test_future_append_and_future_terminal_update_cannot_change_mature_row():
    initial = payload(status="censored", terminal="2024-01-03", confirmation=None)
    before = one(initial)
    later = deepcopy(initial)
    later["daily"].append({"date": "2024-01-06", "qualified": True, "adjusted_close": 200})
    later["waits"][0].update(status="confirmed", terminal_date="2024-01-06",
                              confirmation_date="2024-01-06", confirmation_time="10:30",
                              confirmation_adjusted_close=200, wait_observed_hours=20)
    assert one(later) == before


def test_already_uses_start_close_and_two_horizons_have_separate_counts():
    data = payload(status="already", terminal="2024-01-01", confirmation="2024-01-01")
    result = evaluate_asset(data, horizons=(2, 3))
    assert all(row["candidate_return_pct"] == row["baseline_return_pct"]
               for row in result["event_rows"])
    assert all(row["candidate_entry_time"] == "15:00" for row in result["event_rows"])
    assert result["qualification_counts"]["2:2024-2025"]["participating"] == 1
    assert result["qualification_counts"]["3:2024-2025"]["participating"] == 1


def test_reference5_can_cancel_after_earlier_hourly_confirmation():
    data = payload(prices=(100, 110, 95, 100, 105, 120, 130),
                   terminal="2024-01-02", confirmation="2024-01-02")
    data["waits"][0]["confirmation_adjusted_close"] = 110
    data["waits"][0]["anchor_adjusted_low"] = 90
    data["daily"][2]["adjusted_low"] = 89
    row = one(data, horizon=6)
    assert row["candidate_participated"] is True
    assert row["candidate_return_pct"] == pytest.approx(100 * (130 / 110 - 1))
    assert row["reference5_participated"] is False
    assert row["reference5_return_pct"] == 0
    assert row["reference5_loss_pct"] == 0
    assert row["hourly_minus_reference5_pp"] == pytest.approx(row["candidate_return_pct"])


def test_reference5_observes_only_day5_to_terminal_and_requires_anchor_and_lows():
    data = payload(prices=(100, 80, 90, 95, 99, 110, 120),
                   status="already", terminal="2024-01-01", confirmation="2024-01-01")
    row = one(data, horizon=6)
    assert row["reference5_participated"] is True
    assert row["reference5_return_pct"] == pytest.approx(100 * (120 / 110 - 1))
    assert row["reference5_loss_pct"] == 0
    no_anchor = deepcopy(data)
    no_anchor["waits"][0].pop("anchor_adjusted_low")
    assert one(no_anchor, horizon=6)["reason"] == "missing_anchor"
    no_low = deepcopy(data)
    no_low["daily"][3].pop("adjusted_low")
    assert one(no_low, horizon=6)["reason"] == "missing_first_week_low"


def test_saved_hourly_close_not_later_daily_close_sets_return_and_risk():
    data = payload(prices=(100, 110, 120), terminal="2024-01-02",
                   confirmation="2024-01-02")
    data["waits"][0]["confirmation_adjusted_close"] = 105
    row = one(data)
    assert row["baseline_return_pct"] == pytest.approx(20)
    assert row["candidate_return_pct"] == pytest.approx(100 * (120 / 105 - 1))
    assert row["candidate_return_pct"] != pytest.approx(100 * (120 / 110 - 1))
    assert row["participation_price_change_pct"] == pytest.approx(5)
    assert row["candidate_risk_pct"] == 0
    data["daily"][1]["adjusted_close"] = 100
    assert one(data)["candidate_risk_pct"] == pytest.approx(100 * (1 - 100 / 105))


def test_missing_hourly_confirmation_price_and_confirmation_before_t0():
    data = payload(prices=(100, 110, 120), terminal="2024-01-02",
                   confirmation="2024-01-02")
    data["waits"][0]["confirmation_adjusted_close"] = None
    assert one(data)["reason"] == "missing_confirmation_price"
    data["waits"][0]["confirmation_date"] = "2024-01-01"
    with pytest.raises(ValueError, match="must follow"):
        one(data)
