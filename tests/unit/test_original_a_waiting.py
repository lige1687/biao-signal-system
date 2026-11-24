"""Synthetic-only checks for first identities and finite-history waiting descriptions."""

from datetime import date, timedelta
import random

import pandas as pd
import pytest

from lei_signal.features.indicators import seeded_ema
from lei_signal.research.original_a_waiting import (
    daily_bottom_events, describe_waits, hourly_arrangement,
)


def day(n, *, high=11, low=10, close=10.5, qualified=True):
    return {"date": (date(2025, 1, 1) + timedelta(days=n)).isoformat(),
            "qualified": qualified, "adjusted_open": close, "adjusted_high": high,
            "adjusted_low": low, "adjusted_close": close}


def bottom_sequence(flat_count):
    rows = [day(i) for i in range(flat_count)]
    rows += [day(flat_count, high=12, low=10.5, close=11),
             day(flat_count + 1, high=13, low=10.6, close=12)]
    return rows


def test_first_identity_warmup_and_future_cannot_rewrite_it():
    before = bottom_sequence(249)  # first confirmation at continuous day 251
    first = daily_bottom_events(before, asset="ETF")
    assert len(first) == 1 and first[0]["warm252"] is False
    assert first[0]["continuous_daily_n_at_first"] == 251
    after = before + [day(251, high=14, low=10.7, close=13)]
    extended = daily_bottom_events(after, asset="ETF")
    assert extended[0] == first[0]
    assert sum(item["identity_key"] == first[0]["identity_key"] for item in extended) == 1
    qualified = daily_bottom_events(bottom_sequence(250), asset="ETF")
    assert len(qualified) == 1 and qualified[0]["warm252"] is True
    assert qualified[0]["continuous_daily_n_at_first"] == 252


def test_containment_anchor_and_gap_reset():
    rows = [day(0), day(1, high=10.8, low=10.2),
            day(2, high=12, low=10.5, close=11),
            day(3, high=13, low=10.6, close=12)]
    events = daily_bottom_events(rows, asset="ETF")
    assert len(events) == 1
    event = events[0]
    assert event["anchor_adjusted_low"] == 10
    assert event["identity_tuple"][4:6] == [rows[0]["date"], rows[2]["date"]]
    assert event["confirmation_span_daily_bars"] == 2
    assert event["simple_three_raw_bars"] is False
    assert event["snapshot_at_first"]["M1"]["source_bars"] == 2
    assert event["snapshot_at_first"]["M1"]["first_date"] == rows[0]["date"]
    assert event["snapshot_at_first"]["M1"]["completed_date"] == rows[1]["date"]
    assert event["snapshot_at_first"]["reference_price"] == 10
    assert event["snapshot_at_first"]["trigger_price"] == 12
    assert event["snapshot_at_first"]["final_price"] == 13
    gap = day(4, qualified=False)
    second = [day(5), day(6, high=12, low=10.5, close=11),
              day(7, high=13, low=10.6, close=12)]
    combined = daily_bottom_events(rows + [gap] + second, asset="ETF")
    assert len(combined) == 2 and combined[0] == event
    assert combined[1]["source_segment_first_date"] == second[0]["date"]
    assert combined[1]["continuous_daily_n_at_first"] == 3


def test_simple_three_raw_bars_keeps_first_snapshot():
    rows = [day(0), day(1, high=12, low=10.5, close=11),
            day(2, high=13, low=10.6, close=12)]
    first = daily_bottom_events(rows, asset="ETF")[0]
    assert first["simple_three_raw_bars"] is True
    assert [first["snapshot_at_first"][name]["source_bars"] for name in ("M1", "M2", "Mk")] == [1, 1, 1]
    later = daily_bottom_events(rows + [day(3, high=14, low=10.7, close=13)], asset="ETF")
    assert later[0] == first


HOURS = ("10:30", "11:30", "14:00", "15:00")


def hour_rows(prices, *, bad_day=None):
    return [{"date": (date(2025, 1, 1) + timedelta(days=i // 4)).isoformat(),
             "time": HOURS[i % 4], "adjusted_close": float(price),
             "hour_qualified": i // 4 != bad_day}
            for i, price in enumerate(prices)]


def test_seeded_ema_matches_production_and_strict_both_series():
    prices = [100 + 0.02 * i + 2 * ((i % 7) - 3) for i in range(132)]
    states = hourly_arrangement(hour_rows(prices))
    assert all(s["bull"] is None for s in states[:119])
    for n in (20, 60, 120):
        expected = seeded_ema(pd.Series(prices, dtype=float), n)
        for i in range(119, len(states)):
            assert states[i]["ema"][n] == pytest.approx(expected.iloc[i])
            assert states[i]["sma"][n] == pytest.approx(sum(prices[i - n + 1:i + 1]) / n)
    for state in states[119:]:
        ema, sma = state["ema"], state["sma"]
        assert state["bull"] is ((ema[20] > ema[60] > ema[120]) and
                                 (sma[20] > sma[60] > sma[120]))
    assert hourly_arrangement(hour_rows([100] * 120))[-1]["bull"] is False  # equality is not strict


def test_bad_hour_invalidates_day_and_resets_finite_history():
    prices = list(range(1, 129))
    states = hourly_arrangement(hour_rows(prices, bad_day=30))
    assert states[119]["continuous_hour_n"] == 120
    assert all(states[i]["bull"] is None for i in range(120, 124))
    assert states[124]["continuous_hour_n"] == 1 and states[124]["bull"] is None


def test_ema_up_alone_does_not_pass_strict_double_order():
    rng = random.Random(0)
    prices = [100.0]
    for _ in range(250):
        prices.append(prices[-1] + rng.uniform(-4, 4))
    states = hourly_arrangement(hour_rows(prices))
    s = states[138]
    assert s["ema"][20] > s["ema"][60] > s["ema"][120]
    assert not (s["sma"][20] > s["sma"][60] > s["sma"][120])
    assert s["bull"] is False


def event(start, anchor=10, close=100):
    return {"identity_key": "first", "first_seen": start, "warm252": True,
            "anchor_adjusted_low": anchor, "adjusted_close_at_first": close}


def state(day_value, time_value, bull, close=101, n=120, qualified=True):
    return {"date": day_value, "time": time_value, "bull": bull,
            "hour_qualified": qualified, "adjusted_close": close,
            "continuous_hour_n": n}


def wait_case(day2_low=10, day2_bulls=(False, True), *, day2_qualified=True,
              hour_qualified=True, include_day2=True):
    d1, d2 = day(0)["date"], day(1)["date"]
    daily = [day(0, low=9, high=101, close=100)]
    if include_day2:
        daily.append(day(1, low=day2_low, high=105, close=102,
                         qualified=day2_qualified))
    hours = [state(d1, "15:00", False, close=100)]
    if include_day2:
        hours += [state(d2, HOURS[i], bull, close=102 + i, n=121 + i,
                        qualified=hour_qualified)
                  for i, bull in enumerate(day2_bulls)]
    return describe_waits([event(d1)], hours, daily)[0]


def test_wait_confirmed_counts_observed_bars_only_and_price_change():
    result = wait_case()
    assert result["status"] == "confirmed" and result["wait_observed_hours"] == 2
    assert result["initial_hour_n"] == 120 and result["confirmation_hour_n"] == 122
    assert result["confirmation_time"] == "11:30" and result["price_change_pct"] == pytest.approx(3)
    assert result["terminal_date"] == day(1)["date"] and result["terminal_time"] == "11:30"
    assert result["not_full_A"] is True


def test_wait_counts_only_present_hour_rows_across_lunch_and_days():
    d1, d2, d3 = (day(i)["date"] for i in range(3))
    daily = [day(0, low=9, high=101, close=100),
             day(1, low=10, high=103, close=101),
             day(2, low=10, high=105, close=102)]
    hours = [state(d1, "15:00", False, close=100),
             state(d2, "11:30", False, n=121),
             state(d2, "14:00", False, n=122),
             state(d3, "14:00", True, close=104, n=123)]
    result = describe_waits([event(d1)], hours, daily)[0]
    assert result["status"] == "confirmed"
    assert result["wait_observed_hours"] == 3
    assert result["confirmation_hour_n"] == 123


def test_wait_unknown_and_already_are_distinct():
    d1 = day(0)["date"]
    daily = [day(0, low=9, high=101, close=100)]
    unknown = describe_waits([event(d1)], [state(d1, "15:00", None, n=119)], daily)[0]
    already = describe_waits([event(d1)], [state(d1, "15:00", True, close=100)], daily)[0]
    assert unknown["status"] == "initial_unknown" and unknown["price_change_pct"] is None
    assert unknown["initial_hour_n"] == 119
    assert unknown["terminal_date"] == d1 and unknown["terminal_time"] == "15:00"
    assert already["status"] == "already" and already["price_change_pct"] == 0
    assert already["terminal_date"] == d1 and already["terminal_time"] == "15:00"


def test_same_day_breach_and_bull_is_ambiguous_even_with_hour_order():
    result = wait_case(day2_low=9, day2_bulls=(False, True))
    assert result["status"] == "same_day_ambiguous"
    assert result["daily_broken"] is True and result["price_change_pct"] is None
    assert result["terminal_date"] == day(1)["date"] and result["terminal_time"] is None


def test_gap_dominates_daily_breach_and_equality_is_not_breach():
    gap = wait_case(day2_low=9, day2_bulls=(True,), hour_qualified=False)
    equal = wait_case(day2_low=10, day2_bulls=(True,))
    broken = wait_case(day2_low=9, day2_bulls=(False, False))
    assert gap["status"] == "data_gap" and gap["daily_broken"] is True
    assert gap["terminal_date"] == day(1)["date"] and gap["terminal_time"] is None
    assert equal["status"] == "confirmed" and equal["daily_broken"] is False
    assert broken["status"] == "broken_before_confirm" and broken["price_change_pct"] is None
    assert broken["terminal_date"] == day(1)["date"] and broken["terminal_time"] is None


def test_censor_and_overlapping_events_are_preserved():
    d1 = day(0)["date"]
    result = wait_case(day2_low=10, day2_bulls=(False, False))
    assert result["status"] == "censored" and result["price_change_pct"] is None
    assert result["terminal_date"] == day(1)["date"] and result["terminal_time"] == "15:00"
    rows = describe_waits([event(d1), {**event(d1), "identity_key": "overlap"}],
                          [state(d1, "15:00", False)], [day(0)])
    assert len(rows) == 2 and all(r["status"] == "censored" for r in rows)
