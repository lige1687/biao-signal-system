"""Synthetic checks for the isolated historical selection evaluator."""

import csv
import hashlib
import json
import math
from datetime import date, timedelta

import pytest

from lei_signal.research import lowfreq_discovery as study


def test_prefix_only_scale_and_halt():
    rows = []
    start = date(2013, 1, 1)
    for i in range(275):
        rows.append({"date": (start + timedelta(days=i)).isoformat(), "close": 10 + i / 100,
                     "amount": 1000 + i, "traded": True, "is_st": False})
    features = study._features(rows)
    first = features[rows[252]["date"]]
    assert first["momentum"] == pytest.approx(rows[231]["close"] / rows[0]["close"] - 1)
    assert first["valid_count"] == 253
    assert features[rows[251]["date"]]["momentum"] is None
    doubled = [dict(r, close=2 * r["close"]) for r in rows]
    other = study._features(doubled)
    assert other[rows[252]["date"]]["momentum"] == pytest.approx(first["momentum"])
    assert other[rows[252]["date"]]["vol60"] == pytest.approx(first["vol60"])
    # Appending a future quote cannot change an earlier observation.
    assert study._features(rows + [dict(rows[-1], date="2014-12-01", close=999)])[rows[252]["date"]] == first
    payload = {"error_code": "0", "fields": ["date", "code", "close", "amount", "tradestatus", "isST"],
               "data": [["2020-01-01", "sh.600001", "10", "100", "1", "0"],
                        ["2020-01-02", "sh.600001", "10", "100", "0", "0"],
                        ["2020-01-03", "sh.600001", "11", "100", "1", "0"]]}
    payload["data"][1][3] = "0"
    quotes, valid, errors = study._quotes(payload, "sh.600001", {"frequency": "d", "adjustflag": "2", "code": "sh.600001", "start_date": "2013-01-01", "end_date": "2026-01-15"})
    assert errors == []
    assert len(valid) == 2 and [r["date"] for r in valid] == ["2020-01-01", "2020-01-03"]
    assert study._outcome(quotes, "2020-01-02", "2020-01-03")[0] == pytest.approx(.1)
    assert study._outcome(quotes, "2020-01-02", "2020-01-03")[1] == "observed_mark_halted_entry_or_exit"
    assert study._outcome(quotes, "2020-01-02", "2020-01-03")[2] == pytest.approx(.1)


def test_calendar_timing_cross_month_and_year():
    calendar = ["2014-12-30", "2014-12-31", "2015-01-02", "2015-01-30",
                "2015-02-02", "2015-02-27", "2015-03-02"]
    with pytest.raises(ValueError):
        study._decision_and_execution_dates(calendar, "2015-01", "2015-03")
    assert study._decision_and_execution_dates(calendar, "2015-01", "2015-02") == [
        ("2015-01", "2014-12-31", "2015-01-02", "2015-02-02"),
        ("2015-02", "2015-01-30", "2015-02-02", "2015-03-02")]


def test_fixed_sample_rank_ties_and_nine_cells():
    names = [f"sh.60{i:04d}" for i in range(11)]
    cohort = {"fields": ["code", "type", "ipoDate", "outDate"],
              "data": [[c, "1", "2010-01-01", ""] for c in names] +
                      [["sh.600999", "1", "2015-01-01", ""]]}
    chosen, count, _ = study._cohort(cohort, "2014-12-31", 7)
    assert count == 11 and len(chosen) == 7
    assert chosen == sorted(names, key=lambda c: (hashlib.sha256(("lowfreq-20141231-v1|" + c).encode()).hexdigest(), c))[:7]
    panel = [{"code": c, "eligibility_reason": "eligible", "momentum": 1,
              "short": 1, "vol60": i, "amount20": 10 - i} for i, c in enumerate(names)]
    weights, eligible = study._selections(panel)
    assert list(weights["momentum_top20"]) == sorted(names)[:3]  # ceil(11/5)
    assert [len(weights[f"momentum_q{i}"]) for i in range(1, 6)] == [3, 2, 2, 2, 2]
    cells = study._conditional_groups(eligible)
    assert len(cells) == 9 and sum(c["n"] for c in cells) == 11
    assert sum(c["n"] / len(eligible) for c in cells) == pytest.approx(1)
    assert all(len(c["top"]) == math.ceil(c["n"] / 5) for c in cells)
    cells27 = study._conditional_groups(eligible, include_short=True)
    assert len(cells27) == 27 and sum(c["n"] for c in cells27) == 11
    assert len(study._selections([])[0]["pool_equal"]) == 0


def test_unknown_weights_and_no_renormalization():
    result = study._weighted_outcome({"A": .4, "B": .6}, {"A": (.1, "observed", .1),
            "B": (None, "missing", None)})
    assert result["observed_contribution"] == pytest.approx(.04)
    assert result["unknown_weight"] == pytest.approx(.6)
    assert result["scenario_minus100"] == pytest.approx(-.56)
    assert result["scenario_zero"] == pytest.approx(.04)
    assert result["known_only_return"] is None
    assert study._weighted_outcome({}, {})["scenario_zero"] is None
    relative = study._relative_unknown({"A": .5, "B": .5}, {"B": .5, "C": .5},
                    {"A": (None, "missing", None), "B": (.2, "observed", .2),
                     "C": (None, "missing", None)})
    assert relative["observed_delta"] == 0
    assert relative["adverse_unknown_minus100_or_zero"] == pytest.approx(-.5)
    assert relative["favorable_unknown_minus100_or_zero"] == pytest.approx(.5)
    assert study._turnover({"A": .5, "C": .5}, {"A": .5, "B": .5}) == pytest.approx(.5)


def test_full_contract_synthetic_no_market_data(tmp_path, monkeypatch):
    design = {"research_id": study.DESIGN_ID, "version": "design-v3", "frozen_before_performance": True,
              "universe": {"asof": "2014-12-31", "sample_size": 3},
              "uncertainty": {"circular_month_block_lengths": [6, 12], "draws": 5, "seed": 3}}
    def saved(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    design_spec = saved("design.json", design)
    monkeypatch.setattr(study, "DESIGN_SHA256", design_spec["sha256"])
    monkeypatch.setattr(study, "_check_output_parent", lambda spec, out: __import__("pathlib").Path(out))
    codes = ["sh.600001", "sh.600002", "sh.600003"]
    cohort = saved("cohort.json", {"fields": ["code", "type", "ipoDate", "outDate"],
                                    "data": [[c, "1", "2010-01-01", ""] for c in codes]})
    # Dense historical prefix; then exact first and last market days of each month.
    days = []
    current = date(2013, 1, 1)
    while current <= date(2026, 1, 31):
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    calendar = saved("calendar.json", {"fields": ["calendar_date", "is_trading_day"],
                                        "data": [[d, "1"] for d in days]})
    sources = []
    for idx, code in enumerate(codes):
        data = [[d, code, str(10 + idx * 3 + i / 1000), str(10000 + i), "1", "0"]
                for i, d in enumerate(days)]
        if idx == 0:
            # A halted global month-end is not a valid quote for selection.
            halt = days.index("2014-12-31")
            data[halt][4] = "0"
            data[halt][3] = "0"
        item = saved(f"{idx}.json", {"error_code": "0", "fields": ["date", "code", "close", "amount", "tradestatus", "isST"],
                                      "data": data})
        sources.append({"code": code, **item, "status": "ok", "request": {"frequency": "d", "adjustflag": "2", "code": code,
                                                               "start_date": "2013-01-01", "end_date": "2026-01-15"}})
    contract = saved("contract.json", {"schema": "lowfreq-evaluator-contract/1", "design": design_spec,
                                       "cohort": cohort, "calendar": calendar, "sources": sources,
                                       "output_parent": str(tmp_path)})
    destination = tmp_path / "new-result"
    result = study.run_study(contract["path"], destination)
    assert result["quality"]["monthly_full_rows"] == 3 * 132
    assert result["quality"]["sample_reached_600"] is False
    with (destination / "monthly.csv").open() as f:
        months = list(csv.DictReader(f))
    assert len(months) == 132
    assert (months[0]["month"], months[0]["decision_date"], months[0]["entry_date"], months[0]["exit_date"]) == (
        "2015-01", "2014-12-31", "2015-01-01", "2015-02-02")
    assert months[-1]["month"] == "2025-12"
    assert months[-1]["entry_date"] == "2025-12-01" and months[-1]["exit_date"] == "2026-01-01"
    with (destination / "per_stock_month.csv").open() as f:
        panel = list(csv.DictReader(f))
    assert next(r for r in panel if r["month"] == "2015-01" and r["code"] == codes[0])["eligibility_reason"] == "no_actual_month_end_quote"
    with (destination / "increment.csv").open() as f:
        increments = list(csv.DictReader(f))
    assert len(increments) == 132 * (9 + 27) * 2
    assert len([r for r in increments if r["month"] == "2015-01" and r["control"] == "vol_amount_short_27" and r["scenario"] == "scenario_zero"]) == 27
    with pytest.raises(FileExistsError):
        study.run_study(contract["path"], destination)


def test_common_calendar_windows_and_data_errors():
    calendar = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(80)]
    code = "sh.600001"
    data = [[d, code, str(10 + i / 100), "100", "1", "0"] for i, d in enumerate(calendar)]
    data[20][3] = "0"
    data[20][4] = "0"  # A genuine halt keeps the provider's book price and zero amount.
    doc = {"error_code": "0", "fields": ["date", "code", "close", "amount", "tradestatus", "isST"], "data": data}
    request = {"frequency": "d", "adjustflag": "2", "code": code,
               "start_date": "2013-01-01", "end_date": "2026-01-15"}
    quote, valid, errors = study._quotes(doc, code, request, calendar, {"ipo": "2010-01-01", "out": None})
    assert not errors and len(valid) == 79
    features = study._features(valid, calendar, quote)
    last = features[calendar[-1]]
    assert last["amount20"] == 100
    assert last["vol60"] is not None
    assert last["valid_count"] == 79
    missing = {"error_code": "0", "fields": doc["fields"], "data": [r for r in data if r[0] != calendar[30]]}
    quote2, valid2, errors2 = study._quotes(missing, code, request, calendar, {"ipo": "2010-01-01", "out": None})
    assert (calendar[30], "expected_listed_day_missing_from_source") in errors2
    assert study._features(valid2, calendar, quote2)[calendar[-1]]["vol60"] is None
    bad_st = {"error_code": "0", "fields": doc["fields"], "data": [list(r) for r in data]}
    bad_st["data"][-1][-1] = "unknown"
    _, _, errors3 = study._quotes(bad_st, code, request, calendar, {"ipo": "2010-01-01", "out": None})
    assert (calendar[-1], "invalid_status_or_isST") in errors3


def test_empty_month_is_not_cash_or_zero():
    empty = study._weighted_outcome({}, {})
    assert empty["empty_selection"] and empty["scenario_minus100"] is None
    assert study._mean([None, None]) is None
    assert study._blocks([None] * 12, [6], 2, 1) == {}


def test_local_large_result_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="separate mounted device"):
        study._check_output_parent({"output_parent": str(tmp_path)}, tmp_path / "new")


def test_fault_only_blocks_relevant_dependency_window():
    calendar = [f"2025-01-{d:02d}" for d in range(1, 32)]
    code = "sh.600001"
    quotes = {code: {calendar[-1]: {"traded": True}}}
    features = {code: {calendar[-1]: {"momentum_252_start_date": "2024-01-01"}}}
    errors = {code: [("2013-07-01", "expected_listed_day_missing_from_source"),
                     ("2025-01-20", "expected_listed_day_missing_from_source")]}
    matched = study._relevant_errors(calendar[-1], calendar, [code], quotes, features,
                                     errors, {code: {"ipo": "2010-01-01", "out": None}})
    assert [r["date"] for r in matched] == ["2025-01-20"]
    assert matched[0]["dependency_start"] == "2024-01-01"


def test_v3_halt_amount_normalization_and_strict_endpoints():
    code = "sh.600001"
    request = {"frequency": "d", "adjustflag": "2", "code": code,
               "start_date": "2013-01-01", "end_date": "2026-01-15"}
    rows = [["2020-01-01", code, "10", "", "0", "0"],
            ["2020-01-02", code, "11", "100", "1", "0"]]
    doc = {"error_code": "0", "fields": ["date", "code", "close", "amount", "tradestatus", "isST"], "data": rows}
    quotes, _, errors = study._quotes(doc, code, request)
    assert errors == [] and quotes["2020-01-01"]["amount"] == 0
    assert quotes["2020-01-01"]["normalized_halt_amount"]
    assert study._outcome(quotes, "2020-01-01", "2020-01-02")[:2] == (
        pytest.approx(.1), "observed_mark_halted_entry_or_exit")
    marked = study._weighted_outcome({code: 1}, {code: study._outcome(quotes, "2020-01-01", "2020-01-02")},
                                     {code: (True, False)})
    assert marked["unknown_weight"] == 0 and marked["entry_halt_weight"] == 1
    assert marked["either_halt_weight"] == 1 and marked["exit_halt_weight"] == 0
    for bad_amount, status in (("bogus", "0"), ("1", "0"), ("", "1")):
        bad = {**doc, "data": [["2020-01-01", code, "10", bad_amount, status, "0"], rows[1]]}
        _, _, bad_errors = study._quotes(bad, code, request)
        assert bad_errors
    invalid_end = {**quotes, "2020-01-02": {**quotes["2020-01-02"], "close": 0}}
    assert study._outcome(invalid_end, "2020-01-01", "2020-01-02")[0] is None
    invalid_status = {**quotes, "2020-01-01": {**quotes["2020-01-01"], "status_valid": False}}
    assert study._outcome(invalid_status, "2020-01-01", "2020-01-02")[0] is None
    invalid_amount = {**quotes, "2020-01-01": {**quotes["2020-01-01"], "amount": 1}}
    assert study._outcome(invalid_amount, "2020-01-01", "2020-01-02")[0] is None


def test_v3_conditional_same_stock_relative_unknown():
    cells = [{"n": 2, "top": {"A": 1}, "all": {"A": .5, "B": .5}}]
    top, all_members = study._combined_cell_weights(cells, 2)
    assert top == {"A": 1} and all_members == {"A": .5, "B": .5}
    outcomes = {"A": (None, "missing", None), "B": (None, "missing", None)}
    relative = study._relative_unknown(top, all_members, outcomes)
    assert relative["adverse_unknown_minus100_or_zero"] == pytest.approx(-.5)
    assert relative["favorable_unknown_minus100_or_zero"] == pytest.approx(.5)
    assert study._weighted_outcome(top, outcomes)["scenario_minus100"] - study._weighted_outcome(all_members, outcomes)["scenario_minus100"] == 0


def test_v3_exited_source_fault_does_not_block_later_month():
    calendar = [f"2025-01-{d:02d}" for d in range(1, 32)]
    code = "sh.600001"
    quotes = {code: {calendar[-1]: {"traded": True}}}
    features = {code: {calendar[-1]: {"momentum_252_start_date": "2024-01-01"}}}
    errors = {code: [("2025-01-20", "expected_listed_day_missing_from_source")]}
    exited = {code: {"ipo": "2010-01-01", "out": "2025-01-15"}}
    assert study._relevant_errors(calendar[-1], calendar, [code], quotes, features, errors, exited) == []
    live = {code: {"ipo": "2010-01-01", "out": None}}
    assert len(study._relevant_errors(calendar[-1], calendar, [code], quotes, features, errors, live)) == 1


def test_v3_blocked_month_denominator_and_conditional_intervals():
    def method(value):
        return {"scenario_zero": value, "scenario_minus100": value,
                "unknown_weight": 0, "empty_selection": value is None,
                "entry_halt_weight": 0, "exit_halt_weight": 0, "either_halt_weight": 0,
                "target_replacement_turnover": None}
    relative = {"observed_delta": .2, "adverse_unknown_minus100_or_zero": .2,
                "favorable_unknown_minus100_or_zero": .2}
    months = []
    conditional = []
    for month, value in (("2015-01", .2), ("2015-02", None)):
        methods = {m: method(value if m == "momentum_top20" else (0 if value is not None else None))
                   for m in study.METHODS}
        months.append({"month": month, "methods": methods, "pool_count": 1 if value is not None else 0,
                       "relative_adversarial": {"momentum_top20_minus_pool_equal": relative if value is not None else None,
                                                "momentum_top20_minus_short_top20": relative if value is not None else None}})
        bundle = {"cells": [], "combined": {"top": method(value), "all": method(0 if value is not None else None),
                                               "relative_adversarial": relative if value is not None else None}}
        conditional.append({"month": month, "cells_by_kind": {"vol_amount_9": bundle,
                                                                 "vol_amount_short_27": bundle}})
    stock = [{"month": "2015-01", "code": "A", "future_return": .2,
              "weight_momentum_top20": 1, "weight_pool_equal": 0}]
    design = {"uncertainty": {"circular_month_block_lengths": [6, 12], "draws": 5, "seed": 3}}
    performance, _, _ = study._aggregate(months, [], stock, conditional, design)
    assert performance["methods"]["momentum_top20"]["defined_months"]["scenario_zero"] == 1
    assert performance["methods"]["momentum_top20"]["mean_pct"]["scenario_zero"] == pytest.approx(20)
    assert performance["methods"]["momentum_top20"]["scenarios"]["scenario_zero"] is None
    assert performance["per_stock_excess_contribution_reconciliation"]["contribution_sum_pct"] == pytest.approx(20)
    for kind in ("vol_amount_9", "vol_amount_short_27"):
        entry = performance["conditional_comparisons"][kind]
        assert entry["scenario_zero"]["defined_months"] == 1
        assert entry["scenario_zero"]["monthly_values"] == [.2, None]
        assert set(entry["scenario_zero"]["block_intervals"]) == {"6", "12"}
        assert entry["unknown_relative_adversarial"]["adverse"]["monthly_values"] == [.2, None]
