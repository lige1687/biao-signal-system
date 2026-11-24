from datetime import date, timedelta

import pytest

from lei_signal.strategy_portfolios.ledger import advance, expected_close, initialize, summary

CONFIG = {
    "initial_cash": 100000,
    "schemes": {"mv": "", "rv": ""},
    "slots": 20,
    "cost_bps": {"CN": 25, "US": 10},
    "concentration_cap": 0.10,
}


def data(until="2026-10-20", scale=1):
    rows = []
    day = date(2024, 9, 1)
    i = 0
    while day.isoformat() <= until:
        if day.weekday() < 5:
            i += 1
            rows.append(
                {
                    "symbol": "ABC",
                    "date": day.isoformat(),
                    "open": (100 + i) * scale,
                    "close": (101 + i) * scale,
                    "volume": 10000,
                    "valid": True,
                    "tradable": None,
                    "eligible_buy": None,
                    "open_tradable": None,
                    "open_buy_allowed": None,
                }
            )
        day += timedelta(days=1)
    return {"bars": rows, "universe": [{"symbol": "ABC", "name": "Test"}]}


def seeded():
    state = initialize(CONFIG, "2026-10-20T17:00:00+08:00")
    return advance(state, "CN", data(), "2026-10-20T18:00:00+08:00")


def test_seed_has_frozen_order_but_no_returns_and_idempotent():
    state = seeded()
    account = state["markets"]["CN"]["accounts"]["mv"]
    assert account["orders"][0]["execute_date"] == "2026-10-21"
    assert not account["series"]
    again = advance(state, "CN", data(), "2026-10-20T19:00:00+08:00")
    assert again["markets"]["CN"]["accounts"] == state["markets"]["CN"]["accounts"]


def test_unit_scale_change_does_not_double_value_and_no_duplicate_fill():
    state = seeded()
    unscaled = advance(state, "CN", data("2026-10-21"), "2026-10-21T16:00:00+08:00")
    scaled = advance(state, "CN", data("2026-10-21", 0.5), "2026-10-21T16:00:00+08:00")
    a = unscaled["markets"]["CN"]["accounts"]["mv"]
    b = scaled["markets"]["CN"]["accounts"]["mv"]
    assert a["series"][0]["equity"] == pytest.approx(b["series"][0]["equity"])
    assert a["orders"][0]["filled_quantity"] > 0
    assert a["cash"] >= 0
    replay = advance(scaled, "CN", data("2026-10-21", 0.5), "2026-10-21T17:00:00+08:00")
    assert replay["markets"]["CN"]["accounts"] == scaled["markets"]["CN"]["accounts"]


def test_late_order_or_missing_session_never_backfills():
    state = seeded()
    for account in state["markets"]["CN"]["accounts"].values():
        account["orders"][0]["created_at"] = "2026-10-21T10:00:00+08:00"
    result = advance(state, "CN", data("2026-10-21"), "2026-10-21T16:00:00+08:00")
    assert result["markets"]["CN"]["accounts"]["mv"]["orders"][0]["filled_quantity"] == 0
    skipped = advance(seeded(), "CN", data("2026-10-22"), "2026-10-22T16:00:00+08:00")
    assert skipped["markets"]["CN"]["accounts"]["mv"]["orders"][0]["status"] == "未成交"


def test_revision_blocks_symbol_and_stale_data_does_not_advance():
    state = seeded()
    fresh = data("2026-10-21")
    fresh["bars"][-3]["close"] *= 1.05
    result = advance(state, "CN", fresh, "2026-10-21T16:00:00+08:00")
    assert "ABC" in result["markets"]["CN"]["errors"]
    assert result["markets"]["CN"]["accounts"]["mv"]["orders"][0]["filled_quantity"] == 0
    stale = advance(state, "CN", data(), "2026-10-21T16:00:00+08:00")
    assert stale["markets"]["CN"]["last_date"] == "2026-10-20"
    assert stale["markets"]["CN"]["status"] == "等待最新资料"


def test_failed_sell_does_not_release_cash():
    state = advance(seeded(), "CN", data("2026-10-21"), "2026-10-21T16:00:00+08:00")
    account = state["markets"]["CN"]["accounts"]["mv"]
    held = account["holdings"]["ABC"]["shares"]
    account["orders"].append(
        {
            "id": "sell-test",
            "date": "2026-10-21",
            "symbol": "ABC",
            "side": "sell",
            "quantity": held,
            "status": "等待",
            "reason": "test",
            "created_at": "2026-10-21T16:00:00+08:00",
            "execute_date": "2026-10-22",
        }
    )
    old_cash = account["cash"]
    fresh = data("2026-10-22")
    fresh["bars"][-1]["open_tradable"] = False
    result = advance(state, "CN", fresh, "2026-10-22T16:00:00+08:00")
    assert result["markets"]["CN"]["accounts"]["mv"]["cash"] == old_cash
    assert result["markets"]["CN"]["accounts"]["mv"]["holdings"]["ABC"]["shares"] == held


def test_us_before_close_freeze_allows_first_same_date_valuation():
    state = initialize(CONFIG, "2026-10-20T07:00:00-04:00")
    state = advance(state, "US", data("2026-10-19"), "2026-10-20T07:00:00-04:00")
    result = advance(state, "US", data("2026-10-20"), "2026-10-20T17:00:00-04:00")
    assert len(result["markets"]["US"]["accounts"]["mv"]["series"]) == 1
    assert summary([], 100000) is None
    assert expected_close("US", "2026-11-27T10:00:00-05:00") == "2026-11-25"


def test_midday_seed_still_initializes_at_next_close():
    state = initialize(CONFIG, "2026-10-20T11:00:00+08:00")
    state = advance(state, "CN", data("2026-10-19"), "2026-10-20T11:00:00+08:00")
    assert not state["markets"]["CN"]["accounts"]["mv"]["orders"]
    state = advance(state, "CN", data("2026-10-20"), "2026-10-20T16:00:00+08:00")
    order = state["markets"]["CN"]["accounts"]["mv"]["orders"][0]
    assert order["execute_date"] == "2026-10-21"
    assert order["reason"] == "首次配置"
