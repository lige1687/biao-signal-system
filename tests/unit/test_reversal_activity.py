from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path

import pytest

from lei_signal.research.reversal_activity import amount60, form_month, open_market_row, simulate_open


def _runner():
    path = Path(__file__).resolve().parents[2] / "docs/experiments/raw/reversal-activity-increment-2026-10-23/run.py"
    spec = importlib.util.spec_from_file_location("activity_runner_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_formation_ignores_future_results_and_uses_exact_past_60_days():
    days = [f"2014-12-{i:02d}" for i in range(1, 31)] + [f"2015-01-{i:02d}" for i in range(1, 32)]
    end = days[-1]
    raw = {f"C{i:02d}": {d: {"amount": i, "tradestatus": "1"} for d in days} for i in range(90)}
    raw["C00"][days[-60]].update(amount=0, tradestatus="0")
    raw["C00"][days[0]]["amount"] = -1  # outside the sixty-day window
    raw["C01"][days[-1]]["amount"] = -1
    rows = [{"code": f"C{i:02d}", "hot": i, "vol60": 90-i,
             "momentum": i/10, "return": None} for i in range(90)]
    a = form_month(rows, raw, days, end)
    b = form_month([{**r, "return": 999} for r in rows], raw, days, end)
    assert a == b
    assert a["eligible_n"] == 89
    assert a["rejected"] == [{"code": "C01", "reason": f"amount_invalid:{end}"}]
    assert [s["n"] for s in a["strata"]] == [30, 30, 29]
    assert [s["qualified"] for s in a["strata"]] == [True, True, False]
    for stratum in a["strata"][:2]:
        weights = stratum["weights"]
        assert len(weights["G5"]) == len(weights["lowvol"])
        assert set(weights["G5"]) <= set(stratum["codes"])
        assert set(weights["lowvol"]) <= set(stratum["codes"])
        assert set(weights["rev_volbalanced"]) <= set(stratum["codes"])
        assert sum(weights["rev_volbalanced"].values()) == pytest.approx(1)
        assert sum(weights["pool"].values()) == pytest.approx(1)
    assert amount60(raw, days, "C00", end)[1] is None
    raw["C00"][days[0]]["amount"] = 1e20
    assert form_month(rows, raw, days, end) == a


def test_lowest_hot_is_g5_and_balanced_selection_is_same_direction():
    days = [f"2014-12-{i:02d}" for i in range(1, 31)] + [f"2015-01-{i:02d}" for i in range(1, 31)]
    values = [-0.2, -0.1, 0, 0.1, 0.2]
    rows = [{"code": f"C{i:02d}", "hot": values[i % 5],
             "vol60": float(i), "momentum": float(i)} for i in range(90)]
    raw = {r["code"]: {d: {"amount": 100, "tradestatus": "1"} for d in days} for r in rows}
    result = form_month(rows, raw, days, days[-1])
    for stratum in result["strata"]:
        f = {r["code"]: r for r in result["features"]}
        assert max(f[c]["hot"] for c in stratum["groups"]["G5"]) <= min(
            f[c]["hot"] for c in stratum["groups"]["G1"])
        balanced_mean = sum(w*f[c]["hot"] for c,w in stratum["weights"]["rev_volbalanced"].items())
        pool_mean = sum(f[c]["hot"] for c in stratum["codes"])/stratum["n"]
        assert balanced_mean <= pool_mean


def _quote(open_price=10, close=10, close_break=False, **future):
    return {"open_valid": True, "open_basis_break": False, "open": open_price,
            "tradestatus_open": "1", "isST_open": "0", "close_valid": True,
            "close_basis_break": close_break, "close": close, **future}


def test_future_bar_fields_cannot_change_open_order_or_opening_mark():
    dates = ["2025-01-31", "2025-02-03", "2025-02-04", "2025-02-28", "2025-03-03"]
    targets = {dates[0]: {"qualified": True, "weights": {"A": 1.0}},
               dates[3]: {"qualified": True, "weights": {"A": 1.0}}}
    market = {"A": {d: _quote() for d in dates}}
    base = simulate_open(dates, market, targets, cost_bps=25)
    polluted = deepcopy(market)
    polluted["A"][dates[1]].update(high=1e9, low=-1e9, volume=0,
                                      source_valid=False, close=999, close_valid=False)
    changed = simulate_open(dates, polluted, targets, cost_bps=25)
    assert changed["orders"][0] == base["orders"][0]
    assert changed["daily"][0]["nav_before_trade"] == base["daily"][0]["nav_before_trade"]
    assert changed["daily"][1]["nav_before_trade"] == base["daily"][1]["nav_before_trade"]
    assert changed["daily"][0]["cash"] >= 0


def test_close_break_keeps_buy_then_locks_next_month_and_carries_unknown():
    dates = ["2025-01-31", "2025-02-03", "2025-02-28", "2025-03-03"]
    targets = {dates[0]: {"qualified": True, "weights": {"A": 1}},
               dates[2]: {"qualified": True, "weights": {"B": 1}}}
    market = {"A": {dates[1]: _quote(close_break=True), dates[2]: _quote(close=20),
                    dates[3]: _quote(close=30)},
              "B": {dates[3]: _quote()}}
    out = simulate_open(dates, market, targets, cost_bps=25)
    assert out["orders"][0]["status"] == "filled"
    assert out["daily"][1]["basis_broken_count"] == 1
    assert out["daily"][1]["unknown_value"] > 0
    assert out["daily"][1]["stress_zero_unknown_nav"] == pytest.approx(out["daily"][1]["cash"])
    sell = next(r for r in out["orders"] if r["side"] == "sell")
    assert sell["status"] == "blocked" and sell["reason"] == "prior_basis_break"
    assert out["daily"][-1]["held_count"] == 1
    assert any(r["code"] == "B" and r["reason"] == "insufficient_cash" for r in out["orders"])
    assert out["daily"][-1]["cash"] >= 0
    assert out["daily"][-1]["fees_cumulative"] == pytest.approx(sum(t["fee"] for t in out["trades"]))


def test_market_adapter_open_is_independent_of_close_audit():
    days = ["2025-01-31", "2025-02-03"]
    adapted = {"raw_by_day": {
        days[0]: {"close": "10", "adjustflag": "3"},
        days[1]: {"open": "10", "preclose": "10", "close": "999",
                  "tradestatus": "1", "isST": "0", "adjustflag": "3"}},
        "factor_by_day": {days[0]: ("1", 1), days[1]: ("1", 1)},
        "rows": [], "break_dates": [days[1]]}
    identity = lambda *a, **kw: {"intervals_overlap": True}
    row = open_market_row(adapted, days, days[1], identity)
    assert row["open_valid"] is True and row["open"] == 10
    assert row["close_basis_break"] is True
    adapted["raw_by_day"][days[1]]["preclose"] = "11"
    identity = lambda *a, **kw: {"intervals_overlap": False}
    assert open_market_row(adapted, days, days[1], identity)["open_basis_break"] is True


def test_suspended_zero_and_missing_open_do_not_permanently_lock_reopening():
    days = ["2025-01-31", "2025-02-03", "2025-02-04", "2025-02-28", "2025-03-03"]
    raw = {days[0]: {"close": "10", "adjustflag": "3"},
           days[1]: {"open": "", "preclose": "10", "close": "10",
                     "tradestatus": "0", "isST": "0", "adjustflag": "3"},
           days[2]: {"open": "0", "preclose": "10", "close": "10",
                     "tradestatus": "1", "isST": "0", "adjustflag": "3"},
           days[3]: {"open": "10", "preclose": "10", "close": "10",
                     "tradestatus": "1", "isST": "0", "adjustflag": "3"},
           days[4]: {"open": "10", "preclose": "10", "close": "10",
                     "tradestatus": "1", "isST": "0", "adjustflag": "3"}}
    adapted = {"raw_by_day": raw,
               "factor_by_day": {d: ("1", 1) for d in days},
               "rows": [{"date": d, "close": "10", "tradestatus": raw[d].get("tradestatus", "1")}
                        for d in days[1:]],
               "break_dates": [days[2]],
               "failures": {days[2]: ["nonpositive numeric source field"]}}
    identity = lambda *a, **kw: {"intervals_overlap": True}
    market = {"A": {d: open_market_row(adapted, days, d, identity) for d in days}}
    assert market["A"][days[1]]["open_reason"] == "no_trade"
    assert not market["A"][days[1]]["open_basis_break"]
    assert market["A"][days[2]]["open_reason"] == "no_open_quote"
    assert not market["A"][days[2]]["open_basis_break"]
    assert not market["A"][days[2]]["close_basis_break"]
    targets = {days[0]: {"qualified": True, "weights": {"A": 1}},
               days[3]: {"qualified": True, "weights": {"A": 1}}}
    base = simulate_open(days, market, targets, cost_bps=0)
    assert base["orders"][0]["reason"] == "no_trade"
    assert base["orders"][-1]["status"] == "filled"
    polluted = deepcopy(market)
    polluted["A"][days[1]].update(close=1000, high=1000, low=-1000, volume=100000,
                                     source_valid=False)
    changed = simulate_open(days, polluted, targets, cost_bps=0)
    assert changed["orders"] == base["orders"]


def test_missing_raw_is_stale_and_next_observed_day_uses_identity():
    days = ["2025-01-31", "2025-02-03", "2025-02-04", "2025-02-05"]
    raw = {days[0]: {"close": "10", "adjustflag": "3"},
           days[1]: {"open": "10", "preclose": "10", "close": "10",
                     "tradestatus": "1", "isST": "0", "adjustflag": "3"},
           days[3]: {"open": "10", "preclose": "10", "close": "10",
                     "tradestatus": "1", "isST": "0", "adjustflag": "3"}}
    adapted = {"raw_by_day": raw, "factor_by_day": {d: ("1", 1) for d in raw},
               "rows": [{"date": days[1], "close": "10", "tradestatus": "1"},
                        {"date": days[3], "close": "10", "tradestatus": "1"}],
               "break_dates": [days[3]],
               "failures": {days[3]: ["calendar_gap_before_row"]}}
    identity = lambda *a, **kw: {"intervals_overlap": True}
    market = {"A": {d: open_market_row(adapted, days, d, identity) for d in days}}
    assert market["A"][days[2]]["open_reason"] == "raw_day_missing"
    assert not market["A"][days[2]]["close_basis_break"]
    assert market["A"][days[3]]["open_valid"]
    assert not market["A"][days[3]]["close_basis_break"]
    assert market["A"][days[3]]["close_unknown_reason"] == "source_uncertain"
    target = {days[0]: {"qualified": True, "weights": {"A": 1}}}
    out = simulate_open(days, market, target, cost_bps=0)
    assert out["daily"][2]["unknown_value"] > 0
    assert out["daily"][2]["basis_broken_count"] == 0
    assert out["daily"][3]["unknown_value"] > 0


@pytest.mark.parametrize("current,failures,days,expect_open", [
    ({"open": "", "preclose": "10", "close": "", "tradestatus": "1",
      "isST": "0", "adjustflag": "3"},
     ["blank numeric source field"], ["2025-01-31", "2025-02-03"], False),
    ({"open": "", "preclose": "10", "close": "10", "tradestatus": "1",
      "isST": "0", "adjustflag": "3"},
     ["calendar_gap_before_row", "blank numeric source field"],
     ["2025-01-31", "2025-02-02", "2025-02-03"], False),
    ({"open": "10", "preclose": "10", "close": "", "tradestatus": "1",
      "isST": "0", "adjustflag": "3"},
     ["blank numeric source field"], ["2025-01-31", "2025-02-03"], True),
])
def test_missing_numeric_and_gap_are_unknown_not_permanent_break(current, failures, days, expect_open):
    first, last = days[0], days[-1]
    adapted = {"raw_by_day": {first: {"close": "10", "adjustflag": "3"}, last: current},
               "factor_by_day": {first: ("1", 1), last: ("1", 1)},
               "rows": [], "break_dates": [last], "failures": {last: failures}}
    identity = lambda *a, **kw: {"intervals_overlap": True}
    row = open_market_row(adapted, days, last, identity)
    assert row["open_valid"] is expect_open
    assert row["open_basis_break"] is False
    assert row["close_basis_break"] is False
    assert row["close_valid"] is False
    assert row["close_unknown_reason"] == "source_uncertain"
    target = {first: {"qualified": True, "weights": {"A": 1}}}
    out = simulate_open([first, last], {"A": {last: row}}, target, cost_bps=0)
    assert out["orders"][0]["status"] == ("filled" if expect_open else "blocked")
    assert out["daily"][-1]["basis_broken_count"] == 0
    if expect_open:
        assert out["daily"][-1]["unknown_value"] > 0


def test_unverified_prior_close_and_mixed_real_break_remain_separate():
    days = ["2025-01-31", "2025-02-03"]
    raw = {days[0]: {"close": "", "adjustflag": "3"},
           days[1]: {"open": "10", "preclose": "10", "close": "10",
                     "tradestatus": "1", "isST": "0", "adjustflag": "3"}}
    adapted = {"raw_by_day": raw, "factor_by_day": {d: ("1", 1) for d in days},
               "rows": [], "break_dates": [days[1]],
               "failures": {days[1]: ["blank numeric source field"]}}
    identity = lambda *a, **kw: {"intervals_overlap": True}
    row = open_market_row(adapted, days, days[1], identity)
    assert row["open_reason"] == "continuity_unverified"
    assert not row["open_basis_break"] and not row["close_basis_break"]
    adapted["raw_by_day"][days[0]]["close"] = "10"
    adapted["failures"][days[1]] = ["blank numeric source field", "adjusted_preclose_break"]
    assert open_market_row(adapted, days, days[1], identity)["close_basis_break"] is True


def test_opening_mark_survives_unknown_close_without_rebalance():
    days = ["2025-01-31", "2025-02-03", "2025-02-04"]
    target = {days[0]: {"qualified": True, "weights": {"A": 1}}}
    market = {"A": {days[1]: _quote(open_price=10, close=10),
                    days[2]: _quote(open_price=5, close=999, close_valid=False)}}
    out = simulate_open(days, market, target, cost_bps=0)
    assert out["daily"][-1]["nav_before_trade"] == pytest.approx(50000)
    assert out["daily"][-1]["unknown_value"] == pytest.approx(50000)
    assert out["month_end_holdings"][-1]["mark"] == pytest.approx(5)
    assert out["month_end_holdings"][-1]["mark_date"] == days[2]


def test_runner_universe_and_low_minus_high_direction():
    runner = _runner()
    cohort = {"fields": ["code", "status"],
              "data": [[f"C{i:03d}", "1"] for i in range(900)]}
    excluded = [f"C{i:03d}" for i in range(600)]
    salt = "high52-independent-cohort-20261020"
    selected = sorted([f"C{i:03d}" for i in range(600,900)],
                      key=lambda c: (hashlib.sha256(f"{salt}|{c}".encode()).hexdigest(), c))
    acquisition = {"cohort": {"path": "synthetic", "sha256": "abc"},
                   "selection_rule": "sha256(salt+|+code) ascending over historical cohort minus old600, first300; no replacement",
                   "salt": salt, "excluded_old_codes": excluded, "codes": selected}
    manifest = {"cohort_sha256": "abc", "asset_sources": {c: {} for c in selected}}
    rows = [{"code": selected[0]}, {"code": selected[1]}]
    coverage = runner.validate_universe(cohort, manifest, rows, "abc", acquisition)
    assert coverage["source_codes"] == 300 and coverage["opportunity_codes"] == 2
    assert len(coverage["source_without_opportunity"]) == 298
    with pytest.raises(ValueError, match="absent from fixed source"):
        runner.validate_universe(cohort, manifest, rows+[{'code': 'OUT'}], "abc", acquisition)
    bad = deepcopy(manifest)
    bad["asset_sources"].pop(selected[0])
    bad["asset_sources"][excluded[0]] = {}
    with pytest.raises(ValueError, match="hash-selected 300"):
        runner.validate_universe(cohort, bad, rows, "abc", acquisition)
    gaps = {1: {"2025-01": 0.04}, 3: {"2025-01": 0.01}}
    assert runner.cross_stratum_differences(gaps, 1, 3, ["2025-01"])["2025-01"] == pytest.approx(0.03)
    assert runner.CROSS_EXPRESSION == "(low_activity_G5-pool)-(high_activity_G5-pool)"
