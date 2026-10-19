"""Small independent examples for annual selection and fixed-unit valuation."""

import math

import pytest

from lei_signal.research.asset_growth_effect import (
    _blocks, _calendar_dates, _candidate_rows, _cell_effect, _drawdown,
    _entry_prices, _entry_quality, _execution_mode, _fourcells,
    _load_quotes, _marks, _net_after_fees,
    _monthly_records, _pair_summary, _period_change, _select, _topk,
)


def _row(code, growth, gp, momentum=0.0, industry="10"):
    return {"code": code, "growth": growth, "gp": gp,
            "momentum": momentum, "industry": industry}


def test_four_cells_strict_medians_and_conditional_same_count():
    rows = [_row("a", 3, 3), _row("b", 3, 1),
            _row("c", 1, 3), _row("d", 1, 1)]
    cells, gm, fm = _fourcells(rows)
    assert (gm, fm) == (2, 2)
    assert {k: [r["code"] for r in v] for k, v in cells.items()} == {
        "HH": ["a"], "HL": ["b"], "LH": ["c"], "LL": ["d"]}
    weights, sectors = _select(rows)
    assert sectors[0]["k"] == 3
    assert set(weights["C"]) == {"a", "c", "d"}
    assert weights["C"]["a"] == pytest.approx(1 / 3)
    for method in ("M", "G", "F", "A"):
        assert sum(weights[method].values()) == pytest.approx(1)
        assert sum(weight > 0 for weight in weights[method].values()) >= 3
    assert weights["P"]["b"] == pytest.approx(0.25)


def test_equal_median_is_tie_not_strict_exclusion():
    rows = [_row("a", 3, 3), _row("b", 2, 2), _row("c", 1, 1)]
    cells, _, _ = _fourcells(rows)
    assert [r["code"] for r in cells["TT"]] == ["b"]
    weights, sectors = _select(rows)
    assert sectors[0]["k"] == 3
    assert weights["C"] == weights["P"]


def test_fourcell_future_missing_remains_in_both_scenarios():
    rows = [_row("hh", 3, 3), _row("hl", 3, 1),
            _row("lh", 1, 3), _row("ll", 1, 1)]
    quotes = {"hh": {"exit": {"close": 1.2}}, "hl": {},
              "lh": {"exit": {"close": 1.1}}, "ll": {"exit": {"close": 0.9}}}
    entry = {r["code"]: 1 for r in rows}
    unchanged, interaction0 = _cell_effect(rows, quotes, entry, "exit", 0)
    lost, interaction1 = _cell_effect(rows, quotes, entry, "exit", -1)
    assert unchanged["HL"] == 0 and lost["HL"] == -1
    assert interaction0 == pytest.approx(0)
    assert interaction1 == pytest.approx(1)


def test_cutoff_tie_splits_mass_not_code_order():
    rows = [_row("z", 1, 1), _row("a", 2, 2), _row("m", 3, 3)]
    scores = {"z": 10, "a": 5, "m": 5}
    assert _topk(rows, scores, 2) == {"z": 1.0, "a": 0.5, "m": 0.5}


def test_sector_weights_and_fixed_units_drift_and_unknown_retention():
    rows = [_row("a", 3, 3), _row("b", 3, 1),
            _row("c", 1, 3), _row("d", 1, 1),
            _row("e", 2, 2, industry="20")]
    weights, sectors = _select(rows)
    assert [s["n"] for s in sectors] == [4, 1]
    assert weights["P"]["e"] == pytest.approx(0.2)
    assert weights["C"]["e"] == pytest.approx(0.2)
    portfolio = {"a": 0.5, "b": 0.5}
    quotes = {"a": {"t1": {"close": 2, "traded": True},
                    "t2": {"close": 4, "traded": True}},
              "b": {"t1": {"close": 1, "traded": True}}}
    unchanged, q0 = _marks(portfolio, {"a": 1, "b": 1}, quotes, ["t1", "t2"], 0)
    total_loss, q1 = _marks(portfolio, {"a": 1, "b": 1}, quotes, ["t1", "t2"], -1)
    assert unchanged == pytest.approx([1, 1.5, 2.5])
    assert total_loss == pytest.approx([1, 1.5, 2.0])
    assert q0[-1]["unknown_initial_weight"] == pytest.approx(0.5)
    assert q1[-1]["observed_initial_weight"] == pytest.approx(0.5)
    # Equal initial capital is not rebalanced after a doubles.
    assert unchanged[-1] != pytest.approx(3.0)


def test_unpriced_entry_keeps_original_weight_without_inventing_units():
    weights = {"priced": 0.4, "unpriced": 0.6}
    prices = {"priced": 10}
    quotes = {"priced": {"end": {"close": 20, "traded": True}},
              "unpriced": {"end": {"close": 100, "traded": True}}}
    unchanged, q0 = _marks(weights, prices, quotes, ["end"], 0)
    total_loss, q1 = _marks(weights, prices, quotes, ["end"], -1)
    assert unchanged[-1] == pytest.approx(1.4)
    assert total_loss[-1] == pytest.approx(0.8)
    assert _entry_quality(weights, prices)["unknown_initial_weight"] == pytest.approx(0.6)
    assert q0[-1]["unknown_initial_weight"] == pytest.approx(0.6)
    assert q1[-1]["observed_initial_weight"] == pytest.approx(0.4)
    assert _period_change(0.8, 0) is None


def test_traded_st_entry_forms_units_but_decision_st_remains_separate():
    rows = [_row("a", 1, 1), _row("b", 2, 2)]
    quotes = {"a": {"entry": {"close": 10, "traded": True, "is_st": True}},
              "b": {"entry": {"close": 20, "traded": False, "is_st": False}}}
    assert _entry_prices(rows, quotes, "entry") == {"a": 10}


def test_quote_parser_errors_are_all_preserved_and_rejected():
    sources = {code: {"request": {"code": code}} for code in ("a", "b")}
    def parser(source, code, request, calendar, membership):
        if code == "b":
            raise ValueError("bad raw row")
        return {}, [], [("2020-01-01", "gap"), ("2020-01-02", "bad amount")]
    quotes, quality = _load_quotes(["a", "b"], sources, [], {"a": {}, "b": {}},
                                   read_source=lambda item: ({}, None), parse=parser)
    assert quotes == {"a": {}}
    assert quality["status"] == "rejected"
    assert quality["error_count"] == 3
    assert [e["reason"] for e in quality["errors"]] == ["gap", "bad amount", "quote_parser_rejected"]
    assert quality["errors"][-1]["detail"] == "bad raw row"
    assert quality["fatal_count"] == 3


def test_only_expected_missing_quote_is_nonfatal_and_preserved():
    sources = {"a": {"request": {"code": "a"}}}
    def missing(source, code, request, calendar, membership):
        return {}, [], [("2025-05-27", "expected_listed_day_missing_from_source")]
    _, quality = _load_quotes(["a"], sources, [], {"a": {}},
                              read_source=lambda item: ({}, None), parse=missing)
    assert quality["error_count"] == 1
    assert quality["fatal_count"] == 0
    assert quality["status"] == "checked_with_nonfatal_missing"
    assert quality["nonfatal_missing"] == quality["errors"]
    def invalid(source, code, request, calendar, membership):
        return {}, [], [("2025-05-27", "invalid_price_or_amount")]
    _, bad = _load_quotes(["a"], sources, [], {"a": {}},
                          read_source=lambda item: ({}, None), parse=invalid)
    assert bad["status"] == "rejected" and bad["fatal_count"] == 1


def test_diagnostic_repair_requires_same_frozen_inputs_and_failed_receipt(tmp_path):
    failed_path = tmp_path / "failed.json"
    failed_path.write_text("{}")
    same = {name: {"sha256": name + "hash"} for name in ("design", "selector", "input_contract")}
    failed = {"schema": "asset-growth-effect-contract/1", **same,
              "control_contract": {"key": "failed_guard"}}
    receipt = {"status": "failed", "command": f"python -m runner --contract {failed_path}"}
    lookup = {"review": ({"effects_authorized": True}, None),
              "source": ({"status": "terminal"}, None),
              "failed_contract": (failed, failed_path),
              "failed_receipt": (receipt, tmp_path / "receipt.json"),
              "failed_guard": ({"stage": "effect", "action": "preflight",
                                "bindings": {"source_qualification": {"sha256": "sourcehash"}}}, None)}
    def bind(binding):
        return lookup[binding["key"]]
    guard = {"bindings": {"controller_review": {"key": "review"},
                          "source_qualification": {"key": "source", "sha256": "sourcehash"}}}
    spec = {**same, "repair_of": {"failed_contract": {"key": "failed_contract", "sha256": "oldsha"},
                                   "failed_receipt": {"key": "failed_receipt", "sha256": "receiptsha"}}}
    decision = {"status": "eligible_for_separate_execution", "stage": "diagnostic",
                "source_counts": {"qualified": 1}}
    result = _execution_mode(spec, guard, decision, bind=bind)
    assert result["stage"] == "diagnostic" and result["mode"] == "repair"
    changed = {**spec, "input_contract": {"sha256": "changed"}}
    with pytest.raises(ValueError, match="changed original input_contract"):
        _execution_mode(changed, guard, decision, bind=bind)
    with pytest.raises(ValueError, match="exact failed-contract"):
        _execution_mode(same, guard, decision, bind=bind)
    pending = {**lookup["source"][0], "status": "pending"}
    lookup["source"] = (pending, None)
    with pytest.raises(ValueError, match="terminal qualified source"):
        _execution_mode(spec, guard, decision, bind=bind)
    lookup["source"] = ({"status": "terminal"}, None)
    changed_source = {"bindings": {**guard["bindings"],
                                   "source_qualification": {"key": "source", "sha256": "changed"}}}
    with pytest.raises(ValueError, match="changed source qualification"):
        _execution_mode(spec, changed_source, decision, bind=bind)


def test_symmetric_fee_model_is_buy_division_and_sell_multiplication():
    assert _net_after_fees(1.25, 10) == pytest.approx(1.25 * 0.999 / 1.001 - 1)
    assert _net_after_fees(1, 30) == pytest.approx(0.997 / 1.003 - 1)


def test_twelve_months_only_and_condition_quality_split():
    month_ends = [f"m{i}" for i in range(1, 13)]
    paths = {m: [1] + [1 + i / 100 for i in range(1, 14)] for m in ("P", "M", "G", "F", "A", "C")}
    qualities = {m: [{"unknown_initial_weight": 0.0} for _ in range(13)] for m in paths}
    entries = {m: {"unknown_initial_weight": 0.0} for m in paths}
    qualities["C"][2]["unknown_initial_weight"] = 0.2
    result = _monthly_records(2020, "unchanged", month_ends, paths, qualities, entries)
    assert len(result) == 12
    assert result[-1]["date"] == "m12"
    assert result[0]["comparison_quality"] == "fully_observed"
    assert result[2]["comparison_quality"] == "scenario_involved"
    assert result[3]["comparison_quality"] == "scenario_involved"
    assert result[2]["P_label_has_imputed_quotes"] is False
    paths["P"][4] = 0
    result = _monthly_records(2020, "total_loss", month_ends, paths, qualities, entries)
    assert result[4]["P_period_change"] is None
    assert result[4]["market_group"] == "P_unknown"
    assert _drawdown(paths["P"]) == -1


def test_calendar_chronology_and_2025_unmatured():
    days = ["2024-06-28", "2024-07-01", "2024-07-31", "2024-08-30",
            "2024-09-30", "2024-10-31", "2024-11-29", "2024-12-31",
            "2025-01-31", "2025-02-28", "2025-03-31", "2025-04-30",
            "2025-05-30", "2025-06-30", "2025-07-01", "2025-07-31"]
    decision, entry, exit_day, marks = _calendar_dates(days, 2024)
    assert (decision, entry, exit_day) == ("2024-06-28", "2024-07-01", "2025-07-01")
    assert len(marks) == 12 and marks[0] == "2024-07-31" and marks[-1] == "2025-06-30"
    decision, entry, exit_day, marks = _calendar_dates(days, 2025)
    assert (decision, entry, exit_day, marks) == ("2025-06-30", "2025-07-01", None, [])
    with pytest.raises(ValueError, match="fixed annual dates"):
        _calendar_dates(days, 2023)


def test_candidate_pool_keeps_unknown_and_future_out_of_eligibility():
    calendar = ["2024-06-28", "2024-07-01", "2025-07-01"]
    selector = [{"decision_date": "2024-06-28", "code": "a", "industry": "10",
                 "eligibility_status": "qualified", "score": "1", "financial_score": "2", "momentum": "3"},
                {"decision_date": "2024-06-28", "code": "b", "industry": "10",
                 "eligibility_status": "unknown", "score": "", "financial_score": "", "momentum": ""}]
    quotes = {"a": {"2024-06-28": {"traded": True, "is_st": False, "status_valid": True}},
              "b": {"2024-06-28": {"traded": True, "is_st": False, "status_valid": True}}}
    # The calendar needs month-end marks only for mature years.
    more = [f"2024-{m:02d}-28" for m in range(8, 13)] + [f"2025-{m:02d}-28" for m in range(1, 7)]
    by_year, coverage = _candidate_rows(selector, sorted(set(calendar + more)), quotes,
                                         {"a": {}, "b": {}}, [2024])
    assert [r["code"] for r in by_year[2024][0]] == ["a"]
    assert coverage[0]["excluded_reasons"]["source_unknown"] == 1


def test_paired_arithmetic_blocks_and_leave_one_out():
    annual = []
    for year in range(2015, 2025):
        annual.append({"year": year, "scenario": "unchanged",
                       "returns": {"C": 0.1 + (year - 2015) / 100,
                                   "A": 0.1, "G": 0.1, "F": 0.1, "M": 0.1, "P": 0.1}})
    pairs = _pair_summary(annual)
    p = next(row for row in pairs if row["pair"] == "C-P")
    assert p["mean_difference"] == pytest.approx(0.045)
    assert p["first5"] == pytest.approx(0.02)
    assert p["last5"] == pytest.approx(0.07)
    assert p["leave_one_year_out"]["2024"] == pytest.approx(0.04)
    assert p["interval_2year_blocks"] == pytest.approx(_blocks([i / 100 for i in range(10)]))
    assert p["interval_2year_blocks"][0] <= 0.045 <= p["interval_2year_blocks"][1]
    assert _drawdown([1, 1.2, 0.9, 1.1]) == pytest.approx(-0.25)
