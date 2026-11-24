import math

import pytest

from lei_signal.research.account_path_diagnostics import compare_nav_paths


def rows(values, start="2026-01-01"):
    from datetime import date, timedelta

    first = date.fromisoformat(start)
    return [{"date": (first + timedelta(days=i)).isoformat(), "nav": value} for i, value in enumerate(values)]


def compare(base, cand):
    return compare_nav_paths(rows(base), rows(cand), cashflow_adjusted=True, calendar="calendar_day")


def test_flat_recovery_resets_peak_then_drawdown_starts_again():
    result = compare([100, 90, 100, 95], [100, 100, 100, 100])
    episodes = result["baseline_drawdowns"]["episodes"]
    assert episodes == [
        {"anchor_date": "2026-01-01", "first_below_date": "2026-01-02", "end_date": "2026-01-03", "recovered": True, "elapsed_calendar_days": 2, "observations_below": 1, "depth_pct": pytest.approx(-10)},
        {"anchor_date": "2026-01-03", "first_below_date": "2026-01-04", "end_date": "2026-01-04", "recovered": False, "elapsed_calendar_days": 1, "observations_below": 1, "depth_pct": pytest.approx(-5)},
    ]
    assert result["baseline_drawdowns"]["ongoing"] == episodes[-1]


def test_earlier_longest_completed_is_distinct_from_short_ongoing():
    result = compare([100, 80, 100, 100, 99], [100, 100, 100, 100, 100])
    summary = result["baseline_drawdowns"]
    assert summary["longest_completed"]["elapsed_calendar_days"] == 2
    assert summary["longest_completed"]["recovered"] is True
    assert summary["ongoing"]["observations_below"] == 1
    assert summary["ongoing"]["first_below_date"] == "2026-01-05"


def test_relative_peak_pullback_can_happen_above_starting_relative_wealth():
    result = compare([100, 100, 100], [100, 120, 110])
    assert result["relative_underperformance"]["episodes"] == []
    episode = result["relative_peak_pullbacks"]["episodes"][0]
    assert episode["anchor_date"] == "2026-01-02"
    assert episode["first_below_date"] == "2026-01-03"
    assert episode["depth_pct"] == pytest.approx(-100 / 12)
    assert result["end_relative_wealth_change_pct"] == pytest.approx(10)


def test_initial_navs_are_normalized_even_when_not_one():
    result = compare([250, 275], [40, 44])
    assert result["relative_underperformance"]["episodes"] == []
    assert result["relative_peak_pullbacks"]["episodes"] == []
    assert result["end_relative_wealth_change_pct"] == pytest.approx(0)


def test_flat_paths_have_no_zero_depth_episodes():
    result = compare([2, 2, 2], [9, 9, 9])
    for key in ("baseline_drawdowns", "candidate_drawdowns", "relative_underperformance", "relative_peak_pullbacks"):
        assert result[key]["episodes"] == []
        assert result[key]["max_depth_pct"] == 0


def test_observed_dates_allows_gaps_but_reports_calendar_elapsed_time():
    b = [{"date": "2026-01-01", "nav": 1}, {"date": "2026-01-04", "nav": 0.9}]
    c = [{"date": "2026-01-01", "nav": 3}, {"date": "2026-01-04", "nav": 3}]
    result = compare_nav_paths(b, c, cashflow_adjusted=True, calendar="observed_dates")
    assert result["sample_count"] == 2
    assert result["baseline_drawdowns"]["ongoing"]["elapsed_calendar_days"] == 3


def test_relative_underperformance_recovers_then_falls_again_across_date_gaps():
    dates = ["2026-01-01", "2026-01-03", "2026-01-08", "2026-01-10", "2026-01-15"]
    baseline = [{"date": day, "nav": 1} for day in dates]
    candidate = [{"date": day, "nav": nav} for day, nav in zip(dates, [10, 8, 10, 9, 8])]
    episodes = compare_nav_paths(
        baseline, candidate, cashflow_adjusted=True, calendar="observed_dates"
    )["relative_underperformance"]["episodes"]
    assert [(e["anchor_date"], e["first_below_date"], e["end_date"], e["recovered"])
            for e in episodes] == [
        ("2026-01-01", "2026-01-03", "2026-01-08", True),
        ("2026-01-08", "2026-01-10", "2026-01-15", False),
    ]
    assert [(e["elapsed_calendar_days"], e["observations_below"], e["depth_pct"])
            for e in episodes] == [(7, 1, pytest.approx(-20)), (7, 2, pytest.approx(-20))]


@pytest.mark.parametrize("kwargs", [
    {"cashflow_adjusted": False, "calendar": "calendar_day"},
    {"cashflow_adjusted": True, "calendar": "weekdays"},
])
def test_rejects_invalid_declaration(kwargs):
    with pytest.raises(ValueError):
        compare_nav_paths(rows([1, 2]), rows([1, 2]), **kwargs)


@pytest.mark.parametrize("bad", [
    [],
    [{"date": "2026-01-01", "nav": 1}],
    [{"date": "2026-01-02", "nav": 1}, {"date": "2026-01-01", "nav": 2}],
    [{"date": "2026-01-01", "nav": 1}, {"date": "2026-01-01", "nav": 2}],
    [{"date": "2026-01-01", "nav": True}, {"date": "2026-01-02", "nav": 2}],
    [{"date": "2026-01-01", "nav": 0}, {"date": "2026-01-02", "nav": 2}],
    [{"date": "2026-01-01", "nav": -1}, {"date": "2026-01-02", "nav": 2}],
    [{"date": "2026-01-01", "nav": math.nan}, {"date": "2026-01-02", "nav": 2}],
    [{"date": "2026-01-01", "nav": math.inf}, {"date": "2026-01-02", "nav": 2}],
    [{"date": "2026-01-01", "nav": 10**1000}, {"date": "2026-01-02", "nav": 2}],
    [{"date": "2026-1-1", "nav": 1}, {"date": "2026-01-02", "nav": 2}],
])
def test_rejects_invalid_rows(bad):
    with pytest.raises(ValueError):
        compare_nav_paths(bad, rows([1] * max(2, len(bad))), cashflow_adjusted=True, calendar="observed_dates")


def test_rejects_date_misalignment_and_missing_calendar_day():
    with pytest.raises(ValueError):
        compare_nav_paths(rows([1, 2]), rows([1, 2], "2026-02-01"), cashflow_adjusted=True, calendar="observed_dates")
    gapped = [{"date": "2026-01-01", "nav": 1}, {"date": "2026-01-03", "nav": 2}]
    with pytest.raises(ValueError):
        compare_nav_paths(gapped, gapped, cashflow_adjusted=True, calendar="calendar_day")


@pytest.mark.parametrize("baseline, candidate", [
    ([1e-308, 1e308], [1, 1]),  # normalized baseline overflows
    ([1e308, 1e-308], [1, 1]),  # normalized baseline underflows to zero
    ([1e-308, 1e308], [1e308, 1e-308]),  # relative wealth over/underflows
])
def test_rejects_nonfinite_or_zero_derived_paths(baseline, candidate):
    with pytest.raises(ValueError):
        compare_nav_paths(
            rows(baseline), rows(candidate), cashflow_adjusted=True, calendar="calendar_day"
        )


def test_rejects_overflowing_end_relative_wealth_change_percentage():
    with pytest.raises(ValueError, match="percentage must be finite"):
        compare_nav_paths(
            rows([1, 1]), rows([1, 1e308]), cashflow_adjusted=True, calendar="calendar_day"
        )
