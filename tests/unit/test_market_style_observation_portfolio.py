"""Pure portfolio review keeps dates, account state, and capital meanings separate."""

import json

import pytest

from lei_signal.market_style_observation.portfolio_review import summarize_portfolio


def _row(day, equity, daily_return):
    return {"date": day, "equity": equity, "nav": equity / 100000,
            "drawdown": min(0, equity / 100000 - 1), "return": daily_return}


def _payload():
    left = [_row("2026-01-01", 100000, 0), _row("2026-01-02", 90000, -.1),
            _row("2026-01-31", 99000, .1), _row("2026-02-01", 89100, -.1)]
    right = [_row("2026-01-01", 100000, 0), _row("2026-01-02", 95000, -.05),
             _row("2026-01-31", 95000, 0), _row("2026-02-01", 85500, -.1)]
    def account(scheme, series, targets):
        return {"scheme": scheme, "name": scheme, "history": {
            "series": series, "summary": {"cumulative_return": series[-1]["equity"] / 100000 - 1,
                                         "max_drawdown": -.2, "cost": 100}},
            "forward": {"series": [], "targets": targets, "holdings": []}}
    return {"generated_at": "2026-10-20T00:00:00Z", "started_at": "2026-10-20T00:00:00Z",
            "markets": [{"id": "US", "source_date": "2026-10-19", "accounts": [
                account("mv", left, [{"symbol": "A", "target_weight": .5}, {"symbol": "B", "target_weight": .5}]),
                account("rv", right, [{"symbol": "A", "target_weight": .25}, {"symbol": "C", "target_weight": .75}]),
            ], "comparison": {"return_correlation": .8, "holding_overlap": .1,
                              "combined_history": {"summary": {"cumulative_return": -.1, "max_drawdown": -.3,
                                                               "cost": 200}, "series": left}}}]}


def test_first_month_includes_first_day_and_initialization_is_not_an_observation():
    result = summarize_portfolio(_payload(), "us")
    hist = result["history"]
    assert hist["common_curve_days"] == 4
    assert hist["initialization_dates_excluded"] == ["2026-01-01"]
    assert hist["common_valid_return_days"] == 3
    assert hist["both_down_days"] == 2
    assert hist["either_down_days"] == 2
    assert hist["monthly"]["common_months"] == 2
    assert hist["monthly"]["both_down_months"] == 2
    assert hist["monthly"]["series"][0]["mv_return"] == pytest.approx(-.01)
    assert hist["monthly"]["series"][0]["rv_return"] == pytest.approx(-.05)
    assert hist["monthly"]["series"][1]["mv_return"] == pytest.approx(-.1)
    assert hist["return_correlation_recomputed"] is not None
    assert hist["return_correlation_difference"] == pytest.approx(hist["return_correlation_recomputed"] - .8)
    json.dumps(result, allow_nan=False)


def test_targets_are_not_invested_holdings_and_weights_have_bounds():
    payload = _payload()
    result = summarize_portfolio(payload, "US")
    assert result["history"]["targets"]["count_overlap"] == .1
    assert result["history"]["targets"]["weight_overlap"] is None
    assert result["forward"]["targets"]["common_count"] == 1
    assert result["forward"]["targets"]["union_count"] == 3
    assert result["forward"]["targets"]["weight_overlap"] == .25
    assert result["forward"]["holdings"]["status"] == "empty"
    assert result["forward"]["holdings"]["weight_overlap"] is None
    assert result["forward"]["both_down_loss_50_50_initial_capital"] is None
    accounts = payload["markets"][0]["accounts"]
    accounts[0]["forward"]["holdings"] = [{"symbol": "A", "weight": .4}, {"symbol": "B", "weight": .6}]
    accounts[1]["forward"]["holdings"] = [{"symbol": "A", "weight": .2}, {"symbol": "C", "weight": .8}]
    assert summarize_portfolio(payload, "US")["forward"]["holdings"]["weight_overlap"] == pytest.approx(.2)
    accounts[1]["forward"]["holdings"][0]["weight"] = .5
    assert summarize_portfolio(payload, "US")["forward"]["holdings"]["weight_overlap"] is None


def test_missing_and_duplicate_daily_dates_do_not_become_zero_returns():
    payload = _payload()
    accounts = payload["markets"][0]["accounts"]
    accounts[0]["history"]["series"].append(_row("2026-01-02", 12345, -.9))
    accounts[1]["history"]["series"][2]["return"] = None
    result = summarize_portfolio(payload, "US")["history"]
    assert result["duplicate_dates_excluded"]["mv"] == 1
    assert result["common_curve_days"] == 3
    assert result["common_valid_return_days"] == 1
    assert result["both_down_days"] == 1
    assert result["monthly"]["common_months"] == 2  # Month endpoints remain usable despite a missing daily return.


def test_zero_is_valid_flat_day_and_no_data_is_explicit():
    payload = _payload()
    accounts = payload["markets"][0]["accounts"]
    accounts[1]["history"]["series"][1]["return"] = 0
    result = summarize_portfolio(payload, "US")["history"]
    assert result["common_valid_return_days"] == 3
    assert result["both_down_days"] == 1
    assert summarize_portfolio({}, "US")["available"] is False


def test_forward_joint_loss_uses_equal_initial_capital_and_actual_recorded_returns():
    payload = _payload()
    accounts = payload["markets"][0]["accounts"]
    accounts[0]["forward"]["series"] = [_row("2026-10-21", 90000, -.1)]
    accounts[1]["forward"]["series"] = [_row("2026-10-21", 95000, -.05)]
    result = summarize_portfolio(payload, "US")["forward"]
    assert result["common_valid_return_days"] == 1
    assert result["both_down_days"] == 1
    assert result["both_down_loss_50_50_initial_capital"] == pytest.approx(7500)
