import hashlib
import json
import sys
import types

import pytest

from lei_signal.research import lowfreq_input_guard as guard


FIELDS = list(guard.REQUIRED)


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _fixture(tmp_path, monkeypatch, rows=None):
    design = _write(tmp_path, "design.json", {"research_id": "lowfreq-expanded-discovery-2026-10-19",
        "version": "design-v3", "frozen_before_performance": True,
        "universe": {"asof": "2014-12-31", "sample_size": 1}})
    monkeypatch.setattr(guard, "DESIGN_SHA", design["sha256"])
    cohort = _write(tmp_path, "cohort.json", {"fields": ["code", "ipoDate", "outDate"],
        "data": [["sh.600010", "2000-01-01", "2020-01-01"]]})
    calendar = _write(tmp_path, "calendar.json", {"fields": ["calendar_date", "is_trading_day"],
        "data": [["2013-01-04", "1"], ["2013-01-07", "1"]]})
    base = ["2013-01-04", "sh.600010", "1", "2", "1", "1.5", "100", "150", "2", "1", "0"]
    source = _write(tmp_path, "source.json", {"fields": FIELDS, "error_code": "0", "data": rows if rows is not None else [base]})
    source.update({"code": "sh.600010", "status": "ok", "request": {"code": "sh.600010",
        "frequency": "d", "adjustflag": "2", "start_date": "2013-01-01", "end_date": "2026-01-15"}})
    contract = {"schema": "lowfreq-evaluator-contract/1", "design": design, "cohort": cohort,
                "calendar": calendar, "sources": [source]}
    return contract, source, base


def _refresh_source(source, payload):
    path = __import__("pathlib").Path(source["path"])
    path.write_text(json.dumps(payload), encoding="utf-8")
    source["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def test_clean_guard_calls_stub_and_preserves_bound_source(tmp_path, monkeypatch):
    contract, source, _ = _fixture(tmp_path, monkeypatch)
    before = source["sha256"]
    calls = []
    monkeypatch.setitem(sys.modules, "lei_signal.research.lowfreq_discovery",
                        types.SimpleNamespace(run_study=lambda c, o: calls.append((c, o)) or {"stub": True}))
    result = guard.guarded_run_study(contract, tmp_path / "new")
    assert result["status"] == "historical_only_conditional"
    assert result["result"] == {"stub": True}
    assert len(calls) == 1
    assert hashlib.sha256(__import__("pathlib").Path(source["path"]).read_bytes()).hexdigest() == before


@pytest.mark.parametrize("mutation,expected", [
    (lambda r: r.__setitem__(8, "3"), "returned_adjustflag"),
    (lambda r: r.__setitem__(9, "2"), "invalid_tradestatus"),
    (lambda r: r.__setitem__(10, "?"), "invalid_isST"),
    (lambda r: r.__setitem__(3, "nan"), "invalid_number"),
    (lambda r: r.__setitem__(3, "0.5"), "inconsistent_ohlc"),
    (lambda r: r.__setitem__(6, "-1"), "negative_activity"),
])
def test_bad_actual_row_blocks_before_executor(tmp_path, monkeypatch, mutation, expected):
    contract, source, row = _fixture(tmp_path, monkeypatch)
    mutation(row)
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": [row]})
    monkeypatch.setitem(sys.modules, "lei_signal.research.lowfreq_discovery",
                        types.SimpleNamespace(run_study=lambda *_: pytest.fail("executor called")))
    report = guard.guarded_run_study(contract, tmp_path / "new")
    assert report["status"] == "blocked"
    assert report["blockers"][expected]["count"] == 1


def test_empty_and_halt_cases(tmp_path, monkeypatch):
    contract, source, row = _fixture(tmp_path, monkeypatch)
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": []})
    assert "empty_table" in guard.inspect_contract(contract)["blockers"]
    row[9] = "0"
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": [row]})
    assert "halt_positive_amount" in guard.inspect_contract(contract)["blockers"]
    row[7] = ""
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": [row]})
    report = guard.inspect_contract(contract)
    assert "halt_positive_volume" in report["blockers"]
    row[6] = ""
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": [row]})
    report = guard.inspect_contract(contract)
    assert report["status"] == "historical_only_conditional"
    assert report["warnings"]["normalized_halt_amount"]["count"] == 1
    assert report["warnings"]["normalized_halt_volume"]["count"] == 1


def test_bad_dates_and_missing_field_are_blocked(tmp_path, monkeypatch):
    contract, source, row = _fixture(tmp_path, monkeypatch)
    next_row = row.copy()
    next_row[0] = "2013-01-07"
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": [next_row, row, row]})
    report = guard.inspect_contract(contract)
    assert report["blockers"]["quote_order"]["count"] == 2
    row[0] = "2013-01-05"
    _refresh_source(source, {"fields": FIELDS, "error_code": "0", "data": [row]})
    assert "outside_calendar" in guard.inspect_contract(contract)["blockers"]
    missing = FIELDS.copy()
    missing.remove("isST")
    _refresh_source(source, {"fields": missing, "error_code": "0", "data": [[v for i, v in enumerate(row) if i != 10]]})
    assert "table_schema" in guard.inspect_contract(contract)["blockers"]
    _refresh_source(source, {"fields": [1] + FIELDS[1:], "error_code": "0", "data": [row]})
    assert "table_schema" in guard.inspect_contract(contract)["blockers"]


@pytest.mark.parametrize("name,fields", [
    ("cohort", ["code", "ipoDate", 7]),
    ("calendar", ["calendar_date", 7]),
])
def test_malformed_bound_table_headers_report_blocker(tmp_path, monkeypatch, name, fields):
    contract, _, _ = _fixture(tmp_path, monkeypatch)
    path = __import__("pathlib").Path(contract[name]["path"])
    payload = json.loads(path.read_text())
    payload["fields"] = fields
    path.write_text(json.dumps(payload), encoding="utf-8")
    contract[name]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert "table_schema" in guard.inspect_contract(contract)["blockers"]


@pytest.mark.parametrize("claim", ["executable", "nominal_price_floor", "size_filtered", "point_in_time_proven"])
def test_claim_cannot_bypass(tmp_path, monkeypatch, claim):
    contract, _, _ = _fixture(tmp_path, monkeypatch)
    contract["metadata"] = {"point_in_time_proven": True, "execution_ready": True}
    monkeypatch.setitem(sys.modules, "lei_signal.research.lowfreq_discovery",
                        types.SimpleNamespace(run_study=lambda *_: pytest.fail("executor called")))
    assert "unsupported_claim" in guard.guarded_run_study(contract, tmp_path / "new", claim)["blockers"]


def test_available_versions_timezone_and_future_append():
    first = {"code": "x", "period": "2020Q1", "available_at": "2020-04-01T09:00:00+08:00", "value": 1}
    revised = {**first, "available_at": "2020-05-01T09:00:00+08:00", "value": 2}
    future = {**first, "available_at": "2020-06-01T09:00:00+08:00", "value": 3}
    other = {**first, "period": "2020Q2", "value": 9}
    decision = "2020-05-15T00:00:00+08:00"
    assert guard.select_available_records([first, revised, future, other], decision) == [revised, other]
    assert guard.select_available_records([first, revised, future, other, {**future, "value": 4}], decision) == [revised, other]
    with pytest.raises(ValueError, match="timezone"):
        guard.select_available_records([first], "2020-05-15T00:00:00")
    with pytest.raises(ValueError, match="timestamp"):
        guard.select_available_records([{**first, "available_at": None}], decision)


def test_historical_exit_and_failed_buy_keep_targets():
    assert guard.historically_listed({"ipoDate": "2000-01-01", "outDate": "2020-01-01"}, "2014-12-31")
    assert not guard.historically_listed({"ipoDate": "2000-01-01", "outDate": "2014-12-31"}, "2014-12-31")
    outcome = guard.frozen_selection_execution({"A": .4, "B": .4}, {"A": "halted", "B": "traded"})
    assert outcome["target_weights"] == {"A": .4, "B": .4}
    assert outcome["unfilled_target_weight"] == .4
    assert outcome["cash_target_weight"] == pytest.approx(.2)
    assert outcome["filled_weights"] is None
    unknown = guard.frozen_selection_execution({"A": .4, "B": .4}, {"A": "unknown", "B": "unfillable"})
    assert unknown["flags"] == {"A": "unknown", "B": "unfillable"}
    assert unknown["unfilled_target_weight"] == pytest.approx(.8)
    with pytest.raises(ValueError, match="unknown execution status"):
        guard.frozen_selection_execution({"A": .4}, {"A": "limit_up"})
    for invalid in (-.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="invalid long-only"):
            guard.frozen_selection_execution({"A": invalid}, {"A": "traded"})
    with pytest.raises(ValueError, match="exceeds 1"):
        guard.frozen_selection_execution({"A": .7, "B": .4}, {"A": "traded", "B": "traded"})
