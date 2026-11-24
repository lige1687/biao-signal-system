import numpy as np
import pytest

from lei_signal.research.green_momentum import (
    _valid_daily,
    arm_month,
    costs,
    drift_turnover,
    factor_table,
    future_outcome,
    qualified_features,
    residual_scores,
    select_arms,
)


def test_ch3_values_are_already_decimal_and_skip_t():
    factors = factor_table(
        [("mnthdt", "rf_mon", "mktrf", "SMB", "VMG"), (20200131, 0.002, 0.1, -0.04, 0.03)]
    )
    assert factors["2020-01"] == (0.002, 0.1, -0.04, 0.03)
    rng = np.random.default_rng(4)
    f = np.column_stack((np.full(36, 0.002), rng.normal(0, 0.03, (36, 3))))
    y = 0.01 + f[:, 1:] @ np.array([0.7, -0.3, 0.4]) + rng.normal(0, 0.005, 36)
    returns = y + f[:, 0]
    first = residual_scores(returns, f)
    changed = returns.copy()
    changed[-1] += 0.4
    second = residual_scores(changed, f)
    # The T return is outside the score window, but inside the fitted 36 months.
    assert first["ordinary"] == pytest.approx(second["ordinary"])
    assert first["arithmetic_control"] == pytest.approx(second["arithmetic_control"])
    assert first["residual"] != second["residual"]
    assert first["residual"] != pytest.approx(0)


def test_alpha_is_retained_in_residual_score():
    rng = np.random.default_rng(7)
    x = rng.normal(0, 0.03, (36, 3))
    noise = rng.normal(0, 0.002, 36)
    f = np.column_stack((np.full(36, 0.001), x))
    ret = 0.02 + x @ np.array([0.2, -0.4, 0.8]) + noise + 0.001
    result = residual_scores(ret, f)
    fit = np.linalg.lstsq(np.column_stack((np.ones(36), x)), ret - 0.001, rcond=None)[0]
    q = (ret - 0.001) - x @ fit[1:]
    assert result["residual"] == pytest.approx(sum(q[-12:-1]) / np.std(q[-12:-1], ddof=1))
    assert abs(sum(q[-12:-1]) - sum((q - fit[0])[-12:-1])) > 0.1


def test_full_rank_and_positive_sd_required():
    with pytest.raises(ValueError, match="full rank"):
        residual_scores([0.01] * 36, [(0.001, 0.02, 0.0, 0.0)] * 36)
    rng = np.random.default_rng(34)
    factors = np.column_stack((np.full(36, .001), rng.normal(0, .03, (36, 3))))
    exact = .01 + factors[:, 1:] @ np.array([.2, -.3, .4]) + .001
    with pytest.raises(ValueError, match="standard deviation"):
        residual_scores(exact, factors)


def test_observed_suspension_may_have_blank_pct_but_not_changed_price():
    previous = {"close": "100"}
    halted = {
        "close": "100",
        "preclose": "100",
        "pctChg": "",
        "volume": "",
        "adjustflag": "2",
        "tradestatus": "0",
    }
    assert _valid_daily(halted, previous)
    assert not _valid_daily({**halted, "close": "101"}, previous)
    assert not _valid_daily({**halted, "volume": "1"}, previous)
    assert not _valid_daily({**halted, "tradestatus": "1"}, previous)


def test_ties_and_selection_do_not_consult_future():
    rows = []
    for i in range(30):
        rows.append(
            {
                "code": f"c{i:02}",
                "eligible": True,
                "ordinary": 1.0,
                "arithmetic_control": float(i),
                "scaled_control": float(i),
                "residual": float(i),
                "high52": float(i),
            }
        )
    arms, reason = select_arms(list(reversed(rows)))
    assert not reason
    assert arms["ordinary"] == [f"c{i:02}" for i in range(9)]
    assert len(arms["all_green"]) == 30
    assert select_arms(rows[:29])[1] == "common_eligible_below_minimum"


def _quote(day, close, preclose, traded="1", volume="100"):
    return {
        "date": day,
        "close": str(close),
        "preclose": str(preclose),
        "open": str(close),
        "high": str(close),
        "low": str(close),
        "pctChg": str(100 * (close / preclose - 1)),
        "adjustflag": "2",
        "tradestatus": traded,
        "volume": volume,
    }


def test_future_missing_stays_unknown_and_bounds_hold():
    days = ["2020-01-31", "2020-02-03", "2020-03-02"]
    quotes = {
        d: r
        for d, r in zip(
            days,
            [_quote(days[0], 100, 100), _quote(days[1], 100, 100), _quote(days[2], 110, 100)],
            strict=True,
        )
    }
    good = future_outcome(quotes, days, *days)
    assert good["return"] == pytest.approx(0.1)
    missing = dict(quotes)
    missing.pop(days[1])
    bad = future_outcome(missing, days, *days)
    assert bad["return"] is None
    result = arm_month(["a", "b"], {"a": good, "b": bad})
    assert result["unknown_weight"] == 0.5
    assert result["complete_return"] is None
    assert result["known_weighted_contribution"] == pytest.approx(0.05)
    assert result["strict_lower_bound"] == pytest.approx(-0.45)
    assert result["strict_upper_bound"] is None
    assert result["scenario_plus100"] == pytest.approx(0.55)


def test_exit_close_after_exit_open_never_enters_outcome_or_qualification():
    days = ["2020-01-31", "2020-02-03", "2020-03-02"]
    quotes = {d: _quote(d, 100, 100) for d in days}
    quotes[days[-1]] = {
        **_quote(days[-1], 10000, 100),
        "open": "110",
        "high": "1",
        "low": "1",
        "pctChg": "999999",
    }
    observed = future_outcome(quotes, days, *days)
    assert observed["return"] == pytest.approx(0.1)
    assert observed["opportunity"] == pytest.approx(0.1)
    assert observed["adverse"] == pytest.approx(0)


def test_drift_turnover_gross_and_costs():
    initial = drift_turnover(None, None, ["a", "b"])
    assert initial["half_l1"] == initial["traded_gross"] == 1
    prior = {"a": {"return": 1.0}, "b": {"return": 0.0}}
    changed = drift_turnover(["a", "b"], prior, ["a", "c"])
    assert changed["half_l1"] == pytest.approx(0.5)
    assert changed["traded_gross"] == pytest.approx(1.0)
    assert costs(changed["traded_gross"])["cost_25bps"] == pytest.approx(0.0025)
    assert (
        drift_turnover(["a", "b"], {"a": {"return": None}, "b": prior["b"]}, ["a"])["half_l1"]
        is None
    )


def test_green_feature_uses_only_past_and_requires_all_months():
    from lei_signal.research.fip import month_add

    months = [month_add("2013-01", i) for i in range(38)]
    days = [f"{m}-{d:02d}" for m in months for d in range(1, 21)]
    rows = []
    for i, day in enumerate(days):
        close, preclose = 100 + i, 99 + i
        rows.append(
            {
                "date": day,
                "close": str(close),
                "preclose": str(preclose),
                "pctChg": str(100 * (close / preclose - 1)),
                "adjustflag": "2",
                "tradestatus": "1",
                "isST": "0",
                "volume": "100",
            }
        )
    rng = np.random.default_rng(13)
    factors = {month_add("2013-02", i): (0.001, *rng.normal(0, 0.02, 3)) for i in range(36)}
    before = qualified_features(rows[:740], days, factors, "a", "2016-01", "2016-01")[0]
    after = qualified_features(rows, days, factors, "a", "2016-01", "2016-01")[0]
    assert before["eligible"] and after["eligible"]
    assert before["ordinary"] == pytest.approx(after["ordinary"])
    assert before["high52"] == pytest.approx(after["high52"])
    missing = qualified_features(
        [r for r in rows if r["date"] != "2014-02-02"], days, factors, "a", "2016-01", "2016-01"
    )[0]
    assert "month_calendar_gap" in missing["reasons"]
    revised = [dict(r) for r in rows]
    revised[400]["adjustflag"] = "3"
    flagged = qualified_features(revised, days, factors, "a", "2016-01", "2016-01")[0]
    assert "invalid_month_price_identity" in flagged["reasons"]


def test_prior_holdings_turnover_uses_realized_return_even_if_now_ineligible():
    # A prior holding that vanishes from the next eligibility pool still has
    # its realized endpoint and must be sold at the next rebalance.
    previous_codes = ["old", "still"]
    previous_outcomes = {"old": {"return": 0.5}, "still": {"return": 0.0}}
    new_codes = ["still", "new"]
    turnover = drift_turnover(previous_codes, previous_outcomes, new_codes)
    assert turnover["traded_gross"] == pytest.approx(1.2)


def _runner_helpers():
    import importlib.util
    from pathlib import Path

    path = (Path(__file__).resolve().parents[2] / "docs/experiments/raw"
            / "green-momentum-selection-2026-10-20/run_study.py")
    spec = importlib.util.spec_from_file_location("green_momentum_runner_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_primary_performance_uses_only_same_complete_pair_months():
    runner = _runner_helpers()
    months = ["2020-01", "2020-02", "2020-03"]
    arms = {
        "2020-01": {"residual": {"complete_return": .1, "mean_adverse": -.2},
                    "scaled_control": {"complete_return": .02, "mean_adverse": -.1}},
        "2020-02": {"residual": {"complete_return": .8, "mean_adverse": -.1},
                    "scaled_control": {"complete_return": None, "mean_adverse": -.3}},
        "2020-03": {"residual": {"complete_return": -.1, "mean_adverse": -.3},
                    "scaled_control": {"complete_return": -.02, "mean_adverse": -.2}},
    }
    result = runner.primary_paired_performance(months, arms)
    assert result["complete_pair_months"] == 2
    assert result["residual"]["mean_monthly_return"] == pytest.approx(0)
    assert result["residual"]["loss_month_share"] == pytest.approx(.5)
    assert result["residual"]["worst_month"] == pytest.approx(-.1)
    assert result["residual"]["mean_stock_adverse_excursion"] == pytest.approx(-.25)
    assert result["scaled_control"]["monthly_return_sd"] == pytest.approx(
        np.std([.02, -.02], ddof=1))


def test_break_even_numerator_and_turnover_use_same_net_observable_months():
    runner = _runner_helpers()
    lookup = {
        ("2020-01", "residual"): {"complete_return": .12, "traded_gross": 1.,
                                  "net_return_25bps": .1175},
        ("2020-01", "scaled_control"): {"complete_return": .10, "traded_gross": .5,
                                        "net_return_25bps": .09875},
        ("2020-02", "residual"): {"complete_return": -.9, "traded_gross": None,
                                  "net_return_25bps": None},
        ("2020-02", "scaled_control"): {"complete_return": .1, "traded_gross": .5,
                                        "net_return_25bps": .09875},
    }
    result = runner.primary_cost_budget(["2020-01", "2020-02"], lookup)
    assert result["same_net_observable_pair_months"] == 1
    assert result["gross_mean_increment_same_pairs"] == pytest.approx(.02)
    assert result["mean_extra_traded_gross_same_pairs"] == pytest.approx(.5)
    assert result["break_even_extra_cost_bps_if_positive"] == pytest.approx(400)
