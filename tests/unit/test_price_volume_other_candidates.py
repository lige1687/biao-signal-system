"""Arithmetic counterexamples for the predeclared price-only path candidates."""

import pytest

from lei_signal.research.price_volume_path_information import candidate_values, day_values


@pytest.mark.parametrize("lookback", [20, 60])
def test_closing_location_and_wick_balance_match_manual_average(lookback):
    days = []
    for i in range(lookback):
        row = {"open": 100.0, "high": 110.0, "low": 90.0,
               "close": 105.0 if i % 2 else 95.0, "volume": 100.0}
        days.append(day_values(row, 100.0))
    values = candidate_values(days, lookback)
    assert values["close_location_mean"] == pytest.approx(
        sum((2 * (105.0 if i % 2 else 95.0) - 200.0) / 20.0
            for i in range(lookback)) / lookback)
    assert values["wick_balance_mean"] == pytest.approx(
        sum(((110.0 - max(100.0, 105.0 if i % 2 else 95.0)) -
              (min(100.0, 105.0 if i % 2 else 95.0) - 90.0)) / 20.0
            for i in range(lookback)) / lookback)
    assert values["range_mean"] == pytest.approx(0.2)
    assert candidate_values(days[:-1], lookback)["close_location_mean"] is None


def test_flat_day_and_invalid_quote_are_distinct():
    flat = day_values({"open": 100.0, "high": 100.0, "low": 100.0,
                       "close": 100.0, "volume": 10.0}, 100.0)
    assert flat["close_location"] == 0
    assert flat["wick_balance"] == 0
    assert day_values({"open": 101.0, "high": 100.0, "low": 100.0,
                       "close": 100.0, "volume": 10.0}, 100.0) is None
