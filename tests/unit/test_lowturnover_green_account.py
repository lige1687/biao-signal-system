"""Synthetic account checks; no provider data or market-effect calculation."""

from __future__ import annotations

from copy import deepcopy

import pytest

from lei_signal.research.lowturnover_green_account import simulate

DAYS = [
    "2024-12-30",
    "2024-12-31",
    "2025-01-01",
    "2025-01-02",
    "2025-01-31",
    "2025-02-01",
    "2025-02-02",
    "2025-02-28",
]


def _case(n=40, months=("2024-12", "2025-01")):
    market = {}
    for i in range(n):
        code = f"C{i:02d}"
        market[code] = {
            day: {
                "date": day,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "preclose": 100.0,
                "volume": 1000,
                "tradestatus": "1",
                "isST": "0",
                "source_valid": True,
            }
            for day in DAYS
        }
    features = [
        {
            "code": f"C{i:02d}",
            "month": month,
            "decision_date": "2024-12-31" if month == "2024-12" else "2025-01-31",
            "eligible": True,
            "green": True,
            "momentum": float(n - i),
            "hot": float(i),
            "vol60": float(i + 1) / 100,
        }
        for month in months
        for i in range(n)
    ]
    return market, features


def _run(market, features, **kw):
    return simulate(DAYS, market, features, first_month="2024-12", last_month="2025-01", **kw)


def _at(result, day):
    return next(row for row in result["daily"] if row["date"] == day)


def test_continuous_cash_months_no_candidates_and_no_liquidation():
    market, features = _case()
    empty = _run(market, [])
    assert [m["month"] for m in empty["monthly"]] == ["2025-01", "2025-02"]
    assert all(m["return_quote_proxy"] == 0 for m in empty["monthly"])
    assert empty["summary"]["transaction_count"] == 0
    base = _run(market, features)
    assert base["summary"]["open_positions"] == 10
    assert base["summary"]["final_nav_quote_proxy"] == pytest.approx(100000 / 1.0025)
    assert len([t for t in base["transactions"] if t["status"] == "filled"]) == 10
    assert base["summary"]["fill_basis"] == "restricted_quote_proxy_not_executable_lower_bound"
    assert all(len(row["slots"]) == 10 for row in base["daily"])
    assert all(
        sum(s["cash"] + s["market_value"] for s in row["slots"])
        == pytest.approx(row["nav_quote_proxy"])
        for row in base["daily"]
    )


def test_t_close_only_and_t_plus_one_sale_t_plus_two_replacement():
    market, features = _case()
    jan = [f for f in features if f["month"] == "2025-01"]
    for f in jan:
        if f["code"] == "C00":
            f["momentum"] = 29.0  # rank 12, outside buffer 10
        elif f["code"] == "C10":
            f["momentum"] = 41.0
    result = _run(market, features, buffer_rank=10)
    assert {s["code"] for s in _at(result, "2025-01-01")["slots"]} == {
        f"C{i:02d}" for i in range(10)
    }
    assert "C00" in {s["code"] for s in _at(result, "2025-01-31")["slots"]}
    feb1 = [
        t for t in result["transactions"] if t["date"] == "2025-02-01" and t["status"] == "filled"
    ]
    feb2 = [
        t for t in result["transactions"] if t["date"] == "2025-02-02" and t["status"] == "filled"
    ]
    assert [(t["side"], t["code"]) for t in feb1] == [("sell", "C00")]
    assert [(t["side"], t["code"]) for t in feb2] == [("buy", "C10")]
    assert len({s["code"] for s in _at(result, "2025-02-28")["slots"]}) == 10
    assert result["summary"]["transaction_count"] == 12
    assert result["summary"]["fees_paid"] > 0


def test_failed_sale_keeps_units_then_delayed_sale_does_not_chase_buy():
    market, features = _case()
    for f in features:
        if f["month"] == "2025-01" and f["code"] == "C00":
            f["green"] = False
            f["eligible"] = False
    market["C00"]["2025-02-01"].update(open=90, high=90, low=90, preclose=100, close=90)
    result = _run(market, features)
    feb1 = _at(result, "2025-02-01")
    assert "C00" in {s["code"] for s in feb1["slots"]}
    assert any(
        t["date"] == "2025-02-01" and t["code"] == "C00" and t["reason"] == "one_price_adverse_sell"
        for t in result["transactions"]
    )
    assert any(
        t["date"] == "2025-02-02"
        and t["code"] == "C00"
        and t["side"] == "sell"
        and t["status"] == "filled"
        for t in result["transactions"]
    )
    assert not any(t["date"] >= "2025-02-02" and t["side"] == "buy" for t in result["transactions"])
    assert sum(s["code"] is None for s in _at(result, "2025-02-28")["slots"]) == 1


def test_failed_buy_no_retry_no_reselection_and_unknown_mark_is_explicit():
    market, features = _case()
    market["C00"]["2025-01-01"].update(open=110, high=110, low=110, preclose=100)
    result = _run(market, features)
    assert any(
        t["code"] == "C00" and t["reason"] == "one_price_adverse_buy"
        for t in result["transactions"]
    )
    assert not any(
        t["date"].startswith("2025-01")
        and t["side"] == "buy"
        and t["code"] == "C00"
        and t["status"] == "filled"
        for t in result["transactions"]
    )
    assert sum(s["code"] is None for s in _at(result, "2025-01-31")["slots"]) == 1
    # Once a held quote becomes invalid, the proxy keeps the old mark and says so.
    market, features = _case()
    market["C00"]["2025-01-31"]["source_valid"] = False
    result = _run(market, features)
    day = _at(result, "2025-01-31")
    assert day["stale_slots"] == 1 and day["unknown_exposure"] > 0
    assert day["stress_zero_stale_nav"] == pytest.approx(
        day["nav_quote_proxy"] - day["stale_market_value"]
    )
    assert "C00" in result["decisions"][1]["unknown_held"]
    assert not any(t["side"] == "sell" and t["code"] == "C00" for t in result["transactions"])


def test_buffer_retain_and_cancel_pending_sale_after_return_to_rank():
    market, features = _case()
    for f in features:
        if f["month"] == "2025-01" and f["code"] == "C00":
            f["momentum"] = 29.0  # outside top10 but within top20 buffer
    retained = _run(market, features, buffer_rank=20)
    assert "C00" in retained["decisions"][1]["retained"]
    assert not any(t["side"] == "sell" for t in retained["transactions"])


def test_exposure_and_cost_accounting_fields():
    market, features = _case()
    result = _run(market, features)
    day = _at(result, "2025-01-31")
    assert day["cash"] == pytest.approx(0, abs=1e-8)
    assert day["weighted_momentum_exposure"] is not None
    assert day["weighted_vol60_exposure"] is not None
    assert day["max_single_stock_weight"] == pytest.approx(0.1)
    assert day["stock_hhi"] == pytest.approx(0.1)
    assert result["summary"]["traded_notional_over_2initial"] == pytest.approx(
        result["summary"]["final_nav_quote_proxy"] / 200000
    )
    assert result["summary"]["turnover_oneway"] == pytest.approx(
        sum(r["filled_gross_today"] / r["nav_before_trade_proxy"] / 2 for r in result["daily"])
    )
    assert all(
        t["nav_before_trade_proxy"] == _at(result, t["date"])["nav_before_trade_proxy"]
        for t in result["transactions"]
        if t["status"] == "filled"
    )


def test_failed_empty_slot_buy_does_not_change_frozen_replacement():
    market, features = _case()
    market["C00"]["2025-01-01"].update(open=110, high=110, low=110, preclose=100)
    market["C00"]["2025-02-01"].update(open=110, high=110, low=110, preclose=100)
    for feature in features:
        if feature["month"] == "2025-01" and feature["code"] == "C01":
            feature.update(eligible=False, green=False)
    result = _run(market, features)
    jan = result["decisions"][1]
    assert [(o["slot"], o["code"]) for o in jan["planned_buys"]] == [(1, "C00")]
    assert jan["planned_replacements"] == [
        {"slot": 2, "sell_code": "C01", "replacement_code": "C10"}
    ]
    assert any(
        t["date"] == "2025-02-01" and t["code"] == "C00" and t["status"] == "blocked"
        for t in result["transactions"]
    )
    assert any(
        t["date"] == "2025-02-02"
        and t["code"] == "C10"
        and t["side"] == "buy"
        and t["status"] == "filled"
        for t in result["transactions"]
    )
    assert not any(t["date"] == "2025-02-02" and t["code"] == "C00" for t in result["transactions"])


def test_basis_break_permanently_freezes_existing_holding():
    market, features = _case()
    market["C00"]["2025-01-02"].update(basis_break=True, source_valid=False, close=200)
    market["C00"]["2025-01-31"].update(close=220)
    market["C00"]["2025-02-01"].update(close=230, open=230)
    for feature in features:
        if feature["month"] == "2025-01" and feature["code"] == "C00":
            feature.update(eligible=False, green=False)
    result = _run(market, features)
    before = next(s for s in _at(result, "2025-01-01")["slots"] if s["code"] == "C00")
    after = next(s for s in _at(result, "2025-02-28")["slots"] if s["code"] == "C00")
    assert after["basis_broken"] and after["stale"]
    assert after["mark"] == before["mark"] == 100
    assert after["market_value"] == pytest.approx(before["market_value"])
    assert "C00" in result["decisions"][1]["unknown_held"]
    assert not any(t["code"] == "C00" and t["side"] == "sell" for t in result["transactions"])
    assert result["summary"]["basis_broken_exposure_days"] > 0


def test_valid_source_halt_carries_last_trading_mark_through_terminal_month():
    market, features = _case()
    for day in DAYS[4:]:
        market["C00"][day].update(
            source_valid=True,
            tradestatus="0",
            volume=0,
            close=999,
        )
    for feature in features:
        if feature["month"] == "2025-01" and feature["code"] == "C00":
            feature.update(eligible=False, green=False)
    result = _run(market, features)
    for day in DAYS[4:]:
        row = _at(result, day)
        held = next(slot for slot in row["slots"] if slot["code"] == "C00")
        assert held["mark"] == 100
        assert held["mark_date"] == "2025-01-02"
        assert held["stale"]
        assert row["unknown_exposure"] > 0
        assert row["stress_zero_stale_nav"] == pytest.approx(
            row["nav_quote_proxy"] - row["stale_market_value"]
        )
    assert any(t["code"] == "C00" and t["reason"] == "not_trading" for t in result["transactions"])
    assert result["summary"]["pending_sells_end"] == 1
    assert result["summary"]["stress_zero_stale_final"] < result["summary"]["final_nav_quote_proxy"]


def test_future_month_features_cannot_change_prior_daily_funds_or_orders():
    market, features = _case()
    base = _run(market, features)
    altered = deepcopy(features)
    for feature in altered:
        if feature["month"] == "2025-01":
            feature.update(eligible=False, green=False, momentum=-999, hot=999, vol60=999)
    changed = _run(market, altered)
    assert [r for r in changed["daily"] if r["date"] < "2025-01-31"] == [
        r for r in base["daily"] if r["date"] < "2025-01-31"
    ]
    # T-close features legitimately update today's descriptive exposures; they
    # cannot change any opening trade or capital value already realized.
    for key in ("nav_quote_proxy", "cash", "market_value", "fees_cumulative", "slots"):
        assert _at(changed, "2025-01-31")[key] == _at(base, "2025-01-31")[key]
    assert [r for r in changed["transactions"] if r["date"] <= "2025-01-31"] == [
        r for r in base["transactions"] if r["date"] <= "2025-01-31"
    ]
    assert changed["decisions"][0] == base["decisions"][0]


def test_st_blocks_new_buy_but_does_not_block_held_stock_sale():
    market, features = _case()
    market["C00"]["2025-01-01"]["isST"] = "1"
    blocked_buy = _run(market, features)
    assert any(
        t["date"] == "2025-01-01"
        and t["code"] == "C00"
        and t["side"] == "buy"
        and t["reason"] == "st_restricted"
        for t in blocked_buy["transactions"]
    )
    assert not any(slot["code"] == "C00" for slot in _at(blocked_buy, "2025-01-02")["slots"])

    market, features = _case()
    for feature in features:
        if feature["month"] == "2025-01" and feature["code"] == "C00":
            feature.update(eligible=False, green=False)
    market["C00"]["2025-02-01"]["isST"] = "1"
    sold = _run(market, features)
    assert any(
        t["date"] == "2025-02-01"
        and t["code"] == "C00"
        and t["side"] == "sell"
        and t["status"] == "filled"
        for t in sold["transactions"]
    )
    assert not any(slot["code"] == "C00" for slot in _at(sold, "2025-02-01")["slots"])


def test_known_st_exit_even_while_green_and_feature_eligible():
    market, features = _case()
    market["C00"]["2025-01-31"]["isST"] = "1"
    market["C00"]["2025-02-01"]["isST"] = "1"
    result = _run(market, features)
    january = result["decisions"][1]
    assert "C00" not in january["ranked"]
    assert "C00" in january["known_not_candidate"]
    assert "C00" in january["sell_planned"]
    assert "C00" not in january["unknown_held"]
    assert any(
        t["date"] == "2025-02-01"
        and t["code"] == "C00"
        and t["side"] == "sell"
        and t["status"] == "filled"
        for t in result["transactions"]
    )


def test_current_month_missing_scores_do_not_reuse_previous_month_values():
    market, features = _case()
    for feature in features:
        if feature["month"] == "2025-01" and feature["code"] == "C00":
            feature.update(momentum=None, vol60=None, green=None, eligible=False)
    result = _run(market, features)
    old = _at(result, "2025-01-02")
    current = _at(result, "2025-01-31")
    assert old["score_date"] == "2024-12-31"
    assert old["weighted_momentum_exposure"] is not None
    assert old["holding_momentum_exposure"] is not None
    assert current["score_date"] == "2025-01-31"
    assert "C00" in result["decisions"][1]["unknown_held"]
    assert current["unknown_feature_weight"] == pytest.approx(0.1)
    assert current["weighted_momentum_exposure"] is None
    assert current["weighted_vol60_exposure"] is None
    assert current["holding_momentum_exposure"] is None
    assert current["holding_vol60_exposure"] is None
    held = next(slot for slot in current["slots"] if slot["code"] == "C00")
    assert held["score_date"] is None
    assert next(slot for slot in current["slots"] if slot["code"] == "C01")["score_date"] == (
        "2025-01-31"
    )


def test_holding_only_exposure_separates_idle_cash():
    market, features = _case()
    market["C00"]["2025-01-01"].update(open=110, high=110, low=110, preclose=100)
    result = _run(market, features)
    row = _at(result, "2025-01-02")
    assert row["cash"] > 0
    assert row["unknown_feature_weight"] == 0
    assert row["holding_momentum_exposure"] == pytest.approx(
        row["weighted_momentum_exposure"] / row["invested_fraction"]
    )
    assert row["holding_vol60_exposure"] == pytest.approx(
        row["weighted_vol60_exposure"] / row["invested_fraction"]
    )
