from datetime import date, timedelta

import pytest

from lei_signal.strategy_portfolios.engine import backtest, build_feature_panel, select_targets


def market_days(n=410):
    days = []
    day = date(2024, 1, 1)
    while len(days) < n:
        if day.weekday() < 5:
            days.append(day.isoformat())
        day += timedelta(days=1)
    return days


def bars_for(symbols=("A", "B"), n=410, changes=None):
    changes = changes or {}
    days = market_days(n)
    rows = []
    for i, day in enumerate(days):
        for j, symbol in enumerate(symbols):
            close = changes.get((day, symbol, "close"), 100 + i * (0.2 + j * 0.08))
            opening = changes.get((day, symbol, "open"), close)
            rows.append({"date": day, "symbol": symbol, "open": opening,
                         "close": close, "volume": changes.get((day, symbol, "volume"), 1000),
                         "valid": changes.get((day, symbol, "valid"), True),
                         "tradable": changes.get((day, symbol, "tradable"), True)})
    return rows, days


def first_eligible_month_end(rows, days):
    panel = build_feature_panel(rows, days)
    return next(day for day in days if day != days[-1] and day[:7] != days[days.index(day)+1][:7]
                and any(row["eligible"] for row in panel if row["date"] == day))


def test_point_in_time_and_missing_close_breaks_history():
    rows, days = bars_for()
    day = first_eligible_month_end(rows, days)
    original = [r for r in build_feature_panel(rows, days) if r["date"] == day]
    future = next(d for d in days if d > day)
    for row in rows:
        if row["date"] == future:
            row["close"] *= 100
    assert [r for r in build_feature_panel(rows, days) if r["date"] == day] == original
    missing = next(r for r in rows if r["date"] == day and r["symbol"] == "A")
    missing["valid"] = False
    panel = build_feature_panel(rows, days)
    assert not next(r for r in panel if r["date"] == day and r["symbol"] == "A")["eligible"]
    assert not next(r for r in panel if r["date"] == future and r["symbol"] == "A")["eligible"]


def test_unknown_tradability_with_positive_volume_is_quote_eligible():
    rows, days = bars_for(symbols=("US",), n=430)
    for row in rows:
        row["tradable"] = None
        row["eligible_buy"] = None
    day = first_eligible_month_end(rows, days)
    signal = next(row for row in build_feature_panel(rows, days) if row["date"] == day)
    assert signal["eligible"] is True


def test_tied_percentiles_and_scheme_difference():
    data = [dict(date="2025-01-31", symbol=s, momentum=m, recent_return=r,
                 volatility=v, close=100, eligible=True)
            for s, m, r, v in [("B", .3, .2, .1), ("A", .3, .2, .1),
                               ("C", .1, -.2, .2), ("D", .2, .1, .3)]]
    mv = select_targets(data, "mv", slots=2)
    rv = select_targets(data, "rv", slots=2)
    assert [r["symbol"] for r in mv] == ["A", "B"]
    assert mv[0]["factor_ranks"]["m"] == mv[1]["factor_ranks"]["m"]
    assert [r["symbol"] for r in rv] != [r["symbol"] for r in mv]
    assert len(select_targets(data, "equal", slots=2)) == 4
    assert all(r["target_weight"] == .25 for r in select_targets(data, "equal", slots=2))


def test_month_end_next_open_and_gap_cash_constraint():
    rows, days = bars_for(symbols=("A",), n=430)
    decision_day = first_eligible_month_end(rows, days)
    next_day = days[days.index(decision_day)+1]
    result = backtest(rows, "m", decision_day, next_day, cost_bps=100, slots=1,
                      initial_cash=1000, trend_exit=False)
    assert result["decisions"][0]["date"] == decision_day
    assert result["trades"][0]["date"] == next_day
    assert result["trades"][0]["decision_date"] == decision_day
    assert result["daily"][-1]["cash"] >= -1e-8
    # Frozen units are reduced when the next open gaps up.
    for row in rows:
        if row["date"] == next_day:
            row["open"] *= 2
    gap = backtest(rows, "m", decision_day, next_day, cost_bps=100, slots=1,
                   initial_cash=1000, trend_exit=False)
    trade = gap["trades"][0]
    assert trade["quantity"] < trade["requested_quantity"]
    assert trade["unfilled_reason"] == "gap_cash_shortfall"
    assert gap["daily"][-1]["cash"] >= -1e-8


def test_failed_sell_keeps_position_and_stale_value():
    rows, days = bars_for(symbols=("A",), n=440)
    first = first_eligible_month_end(rows, days)
    first_next = days[days.index(first)+1]
    exit_day = days[days.index(first)+4]
    exit_next = days[days.index(exit_day)+1]
    for row in rows:
        if row["date"] == exit_day:
            row["close"] = 1  # below 120-day average
        if row["date"] == exit_next:
            row["open_tradable"] = False
            row["valid"] = False
    result = backtest(rows, "m", first, exit_next, 0, slots=1)
    assert result["trades"][0]["date"] == first_next
    failed = [t for t in result["trades"] if t["date"] == exit_next]
    assert failed and failed[0]["quantity"] == 0
    assert result["daily"][-1]["holdings_count"] == 1
    assert result["daily"][-1]["unknown_weight"] > 0
    assert result["daily"][-1]["cash"] == pytest.approx(result["daily"][-2]["cash"])
    retry_day = days[days.index(exit_next)+1]
    retried = backtest(rows, "m", first, retry_day, 0, slots=1)
    assert any(t["date"] == retry_day and t["reason"] == "trend_exit" and t["quantity"] > 0
               for t in retried["trades"])
    assert retried["daily"][-1]["holdings_count"] == 0
    later = days[days.index(retry_day)+5]
    still_out = backtest(rows, "m", first, later, 0, slots=1)
    assert not any(t["side"] == "buy" and t["date"] > retry_day
                   for t in still_out["trades"])


def test_concentration_cap_and_no_reentry_before_month_end():
    rows, days = bars_for(symbols=("A",), n=440)
    first = first_eligible_month_end(rows, days)
    # One slot invests 100%; the daily 10% cap plans a cut to 5%.
    later = days[days.index(first)+3]
    result = backtest(rows, "m", first, later, 0, slots=1, trend_exit=False)
    cap = [t for t in result["trades"] if t["reason"] == "concentration_cap"]
    assert cap and cap[0]["side"] == "sell"
    assert not any(t["side"] == "buy" and t["date"] > days[days.index(first)+1]
                   for t in result["trades"])


def test_reject_negative_fees():
    with pytest.raises(ValueError, match="fees"):
        backtest([], "mv", "2025-01-01", "2025-12-31", -1)


def test_buy_eligibility_at_decision_and_open_without_eod_lookahead():
    rows, days = bars_for(symbols=("A",), n=430)
    decision_day = first_eligible_month_end(rows, days)
    next_day = days[days.index(decision_day)+1]
    decision_bar = next(r for r in rows if r["date"] == decision_day)
    decision_bar["eligible_buy"] = False
    assert not next(r for r in build_feature_panel(rows, days)
                    if r["date"] == decision_day)["eligible"]
    decision_bar["eligible_buy"] = None  # unknown permits quote-level research
    opening_bar = next(r for r in rows if r["date"] == next_day)
    opening_bar["open_buy_allowed"] = False
    blocked = backtest(rows, "m", decision_day, next_day, 0, slots=1)
    assert blocked["trades"][0]["unfilled_reason"] == "not_buy_eligible_at_open"
    opening_bar["open_buy_allowed"] = None
    opening_bar["open_tradable"] = None
    opening_bar["valid"] = False
    opening_bar["close"] = None
    opening_bar["volume"] = 0
    quoted = backtest(rows, "m", decision_day, next_day, 0, slots=1)
    assert quoted["trades"][0]["quantity"] > 0
    assert quoted["daily"][-1]["unknown_weight"] > 0


def test_explicit_open_status_blocks_and_sell_ignores_buy_status():
    rows, days = bars_for(symbols=("A",), n=440)
    first = first_eligible_month_end(rows, days)
    buy_day = days[days.index(first)+1]
    first_open = next(r for r in rows if r["date"] == buy_day)
    first_open["open_tradable"] = False
    blocked = backtest(rows, "m", first, buy_day, 0, slots=1)
    assert blocked["trades"][0]["quantity"] == 0
    first_open["open_tradable"] = True
    exit_day = days[days.index(first)+3]
    sell_day = days[days.index(exit_day)+1]
    for row in rows:
        if row["date"] == exit_day:
            row["close"] = 1
        if row["date"] == sell_day:
            row["open_buy_allowed"] = False
            row["eligible_buy"] = False
            row["valid"] = False
            row["volume"] = 0
            row["open_tradable"] = True
    sold = backtest(rows, "m", first, sell_day, 0, slots=1)
    assert any(t["date"] == sell_day and t["side"] == "sell" and t["quantity"] > 0
               for t in sold["trades"])


def test_precomputed_panel_reuse_and_truncated_terminal_date(monkeypatch):
    rows, days = bars_for(symbols=("A",), n=430)
    first = first_eligible_month_end(rows, days)
    next_day = days[days.index(first)+1]
    panel = build_feature_panel(rows, days)
    expected = backtest(rows, "m", first, next_day, 0, slots=1, calendar=days)
    def no_recompute(*args, **kwargs):
        raise AssertionError("recomputed features")
    monkeypatch.setattr("lei_signal.strategy_portfolios.engine.build_feature_panel", no_recompute)
    reused = backtest(rows, "m", first, next_day, 0, slots=1,
                      calendar=days, feature_panel=panel)
    assert reused == expected
    truncated_rows = [row for row in rows if row["date"] <= first]
    truncated_days = [day for day in days if day <= first]
    no_next_open = backtest(truncated_rows, "m", first, first, 0, slots=1,
                            calendar=truncated_days, feature_panel=panel)
    assert no_next_open["decisions"] == []
