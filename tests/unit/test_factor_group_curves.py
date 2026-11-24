"""Small synthetic paths test the account mechanics, never historical returns."""

import pytest

from lei_signal.research.factor_group_curves import simulate


DATES = ["2020-01-31", "2020-02-03", "2020-02-28", "2020-03-02", "2020-03-31"]


def quote(price=10, **changes):
    row = dict(source_valid=True, basis_break=False, open=price, close=price,
               high=price + 1, low=price - 1, preclose=price, volume=100,
               tradestatus=1, isST=0)
    row.update(changes)
    return row


def run(market=None, targets=None, dates=DATES, **kwargs):
    market = market or {"A": {d: quote() for d in dates}, "B": {d: quote() for d in dates}}
    targets = targets or {"2020-01-31": {"qualified": True, "weights": {"A": 1}},
                          "2020-02-28": {"qualified": True, "weights": {"A": 1}}}
    return simulate(dates, market, targets, initial_cash=100, cost_bps=0,
                    start_date=dates[0], end_date=dates[-1], **kwargs)


def day(result, date):
    return next(x for x in result["daily"] if x["date"] == date)


def test_future_target_change_cannot_change_past_and_no_future_label_interface():
    first = run()
    other = run(targets={"2020-01-31": {"qualified": True, "weights": {"A": 1}},
                         "2020-02-28": {"qualified": True, "weights": {"B": 1},
                                         "future_return_label": 999}})
    assert [x for x in first["daily"] if x["date"] <= "2020-02-28"] == [
        x for x in other["daily"] if x["date"] <= "2020-02-28"]
    assert len([t for t in other["trades"] if t["date"] == "2020-03-02"]) == 2


def test_failed_buy_keeps_its_cash_and_does_not_fund_other_name():
    market = {c: {d: quote() for d in DATES} for c in ("A", "B")}
    market["A"]["2020-02-03"]["open"] = None
    result = run(market=market, targets={"2020-01-31": {"qualified": True,
                   "weights": {"A": .5, "B": .5}},
                   "2020-02-28": {"qualified": True, "weights": {"B": .5}}})
    assert next(o for o in result["orders"] if o["code"] == "A")["reason"] == "no_open"
    assert day(result, "2020-02-03")["cash"] == pytest.approx(50)
    assert day(result, "2020-02-03")["market_value"] == pytest.approx(50)


def test_halted_exit_is_pending_then_reopen_loss_is_visible():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-03-02"] = quote(tradestatus=0, source_valid=False)
    market["A"]["2020-03-31"] = quote(6, preclose=10)
    targets = {"2020-01-31": {"qualified": True, "weights": {"A": 1}},
               "2020-02-28": {"qualified": False, "weights": {}}}
    result = run(market=market, targets=targets)
    halted = day(result, "2020-03-02")
    assert halted["cash"] == 0 and halted["blocked_sell_gross_today"] == pytest.approx(100)
    assert halted["unknown_value"] == pytest.approx(100)
    assert day(result, "2020-03-31")["nav_quote_proxy"] == pytest.approx(60)
    assert day(result, "2020-03-31")["blocked_sell_gross_today"] == 0
    assert len(result["trades"]) == 1


def test_basis_break_is_permanent_for_held_units():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-02-28"] = quote(10, basis_break=True)
    market["A"]["2020-03-02"] = quote(2)
    market["A"]["2020-03-31"] = quote(3)
    result = run(market=market)
    assert day(result, "2020-03-31")["nav_quote_proxy"] == pytest.approx(100)
    assert day(result, "2020-03-31")["basis_broken_count"] == 1
    assert next(h for h in result["month_end_holdings"] if h["date"] == "2020-03-31")["broken"]


def test_same_constant_target_does_not_churn_and_fee_only_on_fills():
    result = run()
    assert len(result["trades"]) == 1
    assert day(result, "2020-03-31")["gross_traded_today"] == 0
    charged = simulate(DATES, {"A": {d: quote() for d in DATES}},
                       {"2020-01-31": {"qualified": True, "weights": {"A": 1}},
                        "2020-02-28": {"qualified": True, "weights": {"A": 1}}},
                       initial_cash=100, cost_bps=25,
                       start_date=DATES[0], end_date=DATES[-1])
    assert len(charged["trades"]) == 1
    last = charged["daily"][-1]
    assert last["nav_quote_proxy"] + last["fees_cumulative"] == pytest.approx(100)


def test_fee_cash_scaling_never_borrows():
    result = simulate(DATES, {"A": {d: quote() for d in DATES}},
                      {"2020-01-31": {"qualified": True, "weights": {"A": 1}},
                       "2020-02-28": {"qualified": True, "weights": {"A": 1}}},
                      initial_cash=100, cost_bps=100,
                      start_date=DATES[0], end_date=DATES[-1])
    assert day(result, "2020-02-03")["cash"] == pytest.approx(0)
    assert result["trades"][0]["gross"] == pytest.approx(100 / 1.01)
    assert all(x["cash"] >= 0 for x in result["daily"])


def test_cash_decision_blocks_but_does_not_erase_old_position():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-03-02"] = quote(tradestatus=0)
    result = run(market=market, targets={
        "2020-01-31": {"qualified": True, "weights": {"A": 1}},
        "2020-02-28": {"qualified": False, "weights": {}}})
    assert day(result, "2020-03-02")["held_count"] == 1
    assert [o for o in result["orders"] if o["date"] == "2020-03-02"][0]["status"] == "blocked"


def test_missing_close_on_new_buy_uses_open_as_stale_mark():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-02-03"] = quote(close=None)
    result = run(market=market)
    opened = day(result, "2020-02-03")
    assert opened["stale_count"] == 1
    assert opened["unknown_value"] == pytest.approx(100)
    assert opened["stress_zero_unknown_nav"] == pytest.approx(0)


def test_missing_close_after_add_to_existing_uses_trade_open_without_phantom_loss():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-03-02"] = quote(12, close=None, preclose=10)
    targets = {"2020-01-31": {"qualified": True, "weights": {"A": .5}},
               "2020-02-28": {"qualified": True, "weights": {"A": 1}}}
    result = run(market=market, targets=targets)
    added = day(result, "2020-03-02")
    assert added["nav_before_trade"] == pytest.approx(110)
    assert added["cash"] == pytest.approx(0)
    assert added["nav_quote_proxy"] == pytest.approx(110)
    assert added["unknown_value"] == pytest.approx(110)
    assert added["close_target_deviation"] == pytest.approx(0)


def test_missing_close_after_partial_sale_marks_remainder_at_trade_open():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-03-02"] = quote(12, close=None, preclose=10)
    targets = {"2020-01-31": {"qualified": True, "weights": {"A": 1}},
               "2020-02-28": {"qualified": True, "weights": {"A": .5}}}
    result = run(market=market, targets=targets)
    reduced = day(result, "2020-03-02")
    assert reduced["nav_before_trade"] == pytest.approx(120)
    assert reduced["cash"] == pytest.approx(60)
    assert reduced["unknown_value"] == pytest.approx(60)
    assert reduced["nav_quote_proxy"] == pytest.approx(120)


def test_terminal_date_does_not_force_liquidation():
    result = run()
    assert day(result, "2020-03-31")["held_count"] == 1
    assert all(t["date"] != "2020-03-31" for t in result["trades"])


def test_one_price_adverse_and_st_buy_rule():
    market = {"A": {d: quote() for d in DATES}}
    market["A"]["2020-02-03"] = quote(11, high=11, low=11, preclose=10)
    result = run(market=market)
    assert result["orders"][0]["reason"] == "one_price_adverse_buy"
    market["A"]["2020-02-03"] = quote(isST=1)
    result = run(market=market)
    assert result["orders"][0]["reason"] == "st_buy_blocked"


def test_st_sale_allowed_but_one_price_down_sale_blocked():
    market = {"A": {d: quote() for d in DATES}}
    targets = {"2020-01-31": {"qualified": True, "weights": {"A": 1}},
               "2020-02-28": {"qualified": False, "weights": {}}}
    market["A"]["2020-03-02"] = quote(isST=1)
    sold = run(market=market, targets=targets)
    assert sold["orders"][-1]["status"] == "filled"
    market["A"]["2020-03-02"] = quote(9, high=9, low=9, preclose=10, isST=1)
    blocked = run(market=market, targets=targets)
    assert blocked["orders"][-1]["reason"] == "one_price_adverse_sell"


@pytest.mark.parametrize("calendar,targets", [
    (["2020-02-03", "2020-01-31"], {}),
    (["2020-01-31", "2020-01-31"], {}),
    (DATES, {"2020-01-31": {"qualified": True, "weights": {"A": 1.1}}}),
    (DATES, {"2020-01-31": {"qualified": False, "weights": {"A": 1}}}),
    (DATES, {}),
    (DATES, {"2020-01-31": {"qualified": True, "weights": {}}}),
    (DATES, {"2020-02-03": {"qualified": True, "weights": {"A": 1}}}),
    (DATES, {"2020-03-31": {"qualified": True, "weights": {"A": 1}}}),
])
def test_invalid_calendar_weights_or_missing_decision_raise(calendar, targets):
    with pytest.raises(ValueError):
        simulate(calendar, {}, targets, initial_cash=100, start_date="2020-01-31", end_date="2020-03-31")
