import math

import pytest

from lei_signal.research.fip import (
    SOURCE_FIELDS, clock_slopes, fip_score, future_endpoint_return, group_stats,
    hac_mean, month_add, monthly_features, monthly_regression, qualify_source, rank_midpercent,
    tied_quantile_bins,
)


def test_fip_sign_zeros_and_permutation():
    assert fip_score([-.1, 0, -.2, .05], .2) == pytest.approx(.25)
    assert fip_score([.05, -.2, 0, -.1], .2) == pytest.approx(.25)
    assert fip_score([-.1, 0, -.2, .05], -.2) == pytest.approx(-.25)
    assert math.isnan(fip_score([], .1))
    assert math.isnan(fip_score([0, .1], 0))


def test_midrank_keeps_ties_together_and_order_independent():
    x = {"c": 2, "a": 1, "b": 1, "d": 4, "e": 5}
    ranks = rank_midpercent(x)
    assert ranks["a"] == ranks["b"] == .3
    assert tied_quantile_bins(x, 5)["a"] == tied_quantile_bins(x, 5)["b"]
    assert rank_midpercent(dict(reversed(list(x.items())))) == ranks


def test_calendar_formation_skips_decision_month_and_future_does_not_change_feature():
    # Twenty scheduled trading days per month keep this small and deterministic.
    months = [month_add("2013-12", i) for i in range(15)]
    dates = [f"{m}-{day:02d}" for m in months for day in range(1, 21)]
    rows = []
    for i, day in enumerate(dates):
        value = 100 + i
        rows.append({"date": day, "close_float": value, "preclose_float": value - 1,
                     "tradestatus": "1", "isST": "0", "daily_return": value/(value-1)-1,
                     "pct_return": value/(value-1)-1})
    first = monthly_features(rows[:260], dates, "x", "2014-12", "2014-12")[0]
    more = monthly_features(rows, dates, "x", "2014-12", "2014-12")[0]
    assert first["formation_start_date"] == "2013-12-20"
    assert first["formation_end_date"] == "2014-11-20"
    assert first["observed_traded_returns"] == 220
    assert first["fip_endpoint"] == more["fip_endpoint"]
    assert first["eligible"] == more["eligible"]
    assert first["decision_date"] == "2014-12-20"


def test_future_gap_does_not_change_prior_eligibility_and_formation_gap_does():
    months = [month_add("2013-12", i) for i in range(15)]
    dates = [f"{m}-{day:02d}" for m in months for day in range(1, 21)]
    rows = [{"date": day, "close_float": 100+i, "preclose_float": 99+i,
             "tradestatus": "1", "isST": "0", "daily_return": (100+i)/(99+i)-1,
             "pct_return": (100+i)/(99+i)-1} for i, day in enumerate(dates)]
    base = monthly_features(rows, dates, "x", "2014-12", "2014-12")[0]
    future_missing = monthly_features([row for row in rows if row["date"] != "2015-01-02"], dates, "x", "2014-12", "2014-12")[0]
    formation_missing = monthly_features([row for row in rows if row["date"] != "2014-06-02"], dates, "x", "2014-12", "2014-12")[0]
    assert base["eligible"] and future_missing["eligible"]
    assert "formation_calendar_row_missing" in formation_missing["reasons"]


def test_returned_adjustflag_quarantines_asset():
    row = ["2014-01-02", "sz.001914", "1", "1", "1", "1", "1", "1", "1", "3", "1", "0", "0"]
    payload = {"fields": list(SOURCE_FIELDS), "error_code": "0", "data": [row]}
    accepted, failures = qualify_source(payload, "sz.001914", {"2014-01-02"})
    assert accepted == []
    assert any(reason.startswith("returned_adjustflag") for reason in failures)


def test_clock_slopes_follow_production_sma_formula():
    prices = [100 * 1.001**i for i in range(120)]
    s20, s60 = clock_slopes(prices)
    assert s20 == pytest.approx(math.log((sum(prices[-20:]) / 20) / (sum(prices[-40:-20]) / 20)) / 20 * 252)
    assert s60 == pytest.approx(math.log((sum(prices[-60:]) / 60) / (sum(prices[:60]) / 60)) / 60 * 252)
    assert all(math.isnan(v) for v in clock_slopes(prices[:119]))


def test_hac_bartlett_hand_calculation():
    result = hac_mean([1, 2, 3], lag=1)
    # Mean 2; gamma0 = 2/3; gamma1 = 0; variance(mean) = 2/9.
    assert result["n"] == 3
    assert result["mean"] == 2
    assert result["se"] == pytest.approx(math.sqrt(2 / 9))
    assert result["ci_low"] == pytest.approx(2 - 1.96 * math.sqrt(2 / 9))


def test_hac_does_not_turn_missing_calendar_month_into_adjacent_month():
    assert hac_mean([1.0, None, 3.0], lag=1)["se"] == pytest.approx(math.sqrt(.5))
    assert hac_mean([1.0, 3.0], lag=1)["se"] == pytest.approx(.5)


def test_future_path_requires_all_scheduled_quotes_and_continuity():
    row = {"decision_date": "2015-01-02", "month": "2015-01"}
    dates = ["2015-01-02", "2015-02-02", "2015-07-31"]
    ends = {"2015-07": "2015-07-31"}
    quotes = {
        "2015-01-02": {"tradestatus": "1", "close_float": 100., "preclose_float": 99., "pct_return": 1/99},
        "2015-02-02": {"tradestatus": "0", "close_float": 100., "preclose_float": 100., "pct_return": math.nan},
        "2015-07-31": {"tradestatus": "1", "close_float": 110., "preclose_float": 100., "pct_return": .1},
    }
    value, reason = future_endpoint_return(row, quotes, ends, dates)
    assert value == pytest.approx(.1) and reason == ""
    missing = dict(quotes)
    missing.pop("2015-02-02")
    assert future_endpoint_return(row, missing, ends, dates)[1] == "future_calendar_row_missing"
    broken = {key: dict(value) for key, value in quotes.items()}
    broken["2015-07-31"]["preclose_float"] = 99.
    assert future_endpoint_return(row, broken, ends, dates)[1] == "future_adjacent_preclose_break"
    bad_pct = {key: dict(value) for key, value in quotes.items()}
    bad_pct["2015-07-31"]["pct_return"] = .09
    assert future_endpoint_return(row, bad_pct, ends, dates)[1] == "future_pct_return_disagreement"


def test_group_unknown_keeps_initial_weight():
    rows = [{"code": "a", "future_return": .2, "pret_endpoint": .1, "volatility_annualized": .2},
            {"code": "b", "future_return": math.nan, "pret_endpoint": .1, "volatility_annualized": .2}]
    result = group_stats(rows, {"a"})
    assert result["selected_n"] == 2 and result["known_n"] == 1
    assert result["known_weighted_contribution"] == pytest.approx(.1)
    assert result["unknown_weight"] == pytest.approx(.5)
    assert result["scenario_minus_100pct"] == pytest.approx(-.4)
    assert result["scenario_plus_100pct"] == pytest.approx(.6)


def test_regression_input_ranks_include_unknown_future_before_subset():
    rows = [{"code": str(i), "pret_endpoint": .1+i*.01, "volatility_annualized": .2+(i*i % 7)*.01,
             "clock_s20": .1+(i*3 % 8)*.01, "clock_s60": .1+(i*5 % 9)*.01,
             "fip_endpoint": -.5+i*.1, "future_return": math.nan if i == 2 else i*.02}
            for i in range(8)]
    result = monthly_regression(rows, min_n=7)
    assert result["past_rank_n"] == 8
    assert result["n"] == 7
