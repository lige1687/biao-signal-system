"""Small arithmetic checks only; no historical sources or output directory."""

from decimal import Decimal

from comparator import calibrate_2025, period_fees, risk_metrics, simulate_hold


def row(day, wealth, trading=True):
    return {"date": day, "wealth": str(wealth), "is_trading_day": str(trading)}


def run():
    # Including January 2's prior natural day changes this estimate.
    a = [row("2024-12-31", 100), row("2025-01-01", 100, False), row("2025-01-02", 101), row("2025-01-03", "99.99")]
    b = [row("2024-12-31", 100), row("2025-01-01", 100, False), row("2025-01-02", 102), row("2025-01-03", "99.96")]
    trading_2025 = {"2024-12-31", "2025-01-02", "2025-01-03"}
    fit = calibrate_2025(a, b, trading_2025)
    assert abs(fit["weight"] - 0.5) < 1e-12
    assert fit["trading_observations"] == 2 and fit["first"] == "2025-01-02"
    shifted = [a[0], row("2025-01-01", "100.5", False)] + a[2:]
    shifted_fit = calibrate_2025(shifted, b, trading_2025)
    assert shifted_fit["prior_natural_vs_prior_trading_difference_dates"]["A"] == ["2025-01-02"]
    try:
        calibrate_2025([a[0]] + a[2:], b, trading_2025)
    except ValueError as exc:
        assert "missing date" in str(exc)
    else:
        raise AssertionError("omitted first denominator passed")

    quotes = [{"date": "2026-01-02", "open": "10", "close": "10"},
              {"date": "2026-01-03", "open": "10", "close": "11"},
              {"date": "2026-01-05", "open": "12", "close": "12"}]
    action = [{"type": "dividend", "event_id": "synthetic-right", "record_date": "2026-01-03",
               "ex_date": "2026-01-04", "pay_date": "2026-01-05",
               "cash_per_unit": "0.1", "unit_basis": "old"}]
    result = simulate_hold(cash=Decimal(10000), fee=Decimal("0.001"), weight=Decimal("0.5"),
                           quotes=quotes, trading_days={"2026-01-02", "2026-01-03", "2026-01-05"},
                           restrictions={"2026-01-02": "blocked"}, actions=action,
                           start="2026-01-01", end="2026-01-06")
    assert len(result["fills"]) == 1 and result["fills"][0]["date"] == "2026-01-03"
    assert result["fills"][0]["units"] == "400"
    assert Decimal(result["fills"][0]["notional"]) + Decimal(result["fills"][0]["fee"]) <= 5000
    assert result["rejections"] == [{"date": "2026-01-02", "reason": "explicit_restriction"}]
    by_day = {row["date"]: row for row in result["daily"]}
    assert by_day["2026-01-04"]["receivable"] == "40.0"  # ex date books a claim, no cash yet
    assert by_day["2026-01-04"]["cash"] == by_day["2026-01-03"]["cash"]
    assert Decimal(by_day["2026-01-05"]["cash"]) - Decimal(by_day["2026-01-04"]["cash"]) == 40
    assert Decimal(by_day["2026-01-06"]["cash"]) + Decimal(by_day["2026-01-06"]["receivable"]) + Decimal(by_day["2026-01-06"]["units"]) * Decimal(by_day["2026-01-06"]["mark"]) == Decimal(by_day["2026-01-06"]["wealth"])
    assert by_day["2026-01-06"]["units"] == "400"  # no liquidation or dividend reinvestment
    metrics = risk_metrics(result["daily"], Decimal(10000),
                           {"2026-01-02", "2026-01-03", "2026-01-05"})
    assert metrics["trading_observations"] == 3 and metrics["trading_day_volatility"] > 0
    assert metrics["prior_natural_vs_prior_trading_difference_dates"] == ["2026-01-05"]

    # An executable open with less than a full lot clears the one-time order.
    no_lot = simulate_hold(cash=Decimal(1000), fee=Decimal("0.002"), weight=Decimal("0.05"),
                           quotes=[{"date": "2026-01-02", "open": "10", "close": "10"},
                                   {"date": "2026-01-03", "open": "0.1", "close": "0.1"}],
                           trading_days={"2026-01-02", "2026-01-03"}, restrictions={}, actions=[],
                           start="2026-01-01", end="2026-01-03")
    assert no_lot["fills"] == [] and no_lot["daily"][-1]["cash"] == "1000"
    assert period_fees({"reconciliation": {"fees_cny": "123"}},
                       {"reconciliation": '{"fees_cny":"125.5"}'}) == Decimal("2.5")
    all_cash = simulate_hold(cash=Decimal(1000), fee=Decimal("0.001"), weight=Decimal(0),
                             quotes=quotes[:2], trading_days={"2026-01-02", "2026-01-03"},
                             restrictions={}, actions=[], start="2026-01-01", end="2026-01-03")
    assert all_cash["fills"] == [] and all_cash["daily"][-1]["wealth"] == "1000"
    try:
        calibrate_2025([row("2024-12-31", 100), row("2025-01-01", 100, False), row("2025-01-02", 101), row("2025-01-03", 102)],
                       [row("2024-12-31", 100), row("2025-01-01", 100, False), row("2025-01-02", 100), row("2025-01-03", 100)],
                       trading_2025)
    except ValueError as exc:
        assert "zero B0" in str(exc)
    else:
        raise AssertionError("zero B0 volatility passed")
    print("synthetic checks passed: first denominator, weight, blocked/open buy, lot and fee, dividend phases, no rebuy, zero cases, daily bridge")


if __name__ == "__main__":
    run()
