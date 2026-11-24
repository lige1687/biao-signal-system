"""Small synthetic source-shape checks; no saved market effects are run."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pytest

from lei_signal.research.fip import SOURCE_FIELDS, month_add
from lei_signal.research.high52_revalidation import ADJUSTMENT_FIELDS
from lei_signal.research.momentum_increment_inputs import (
    ETF_SYMBOLS,
    cn_symbol_inputs,
    etf_monthly_inputs,
    exchange_trading_days,
)


def days(n: int, start: date = date(2023, 1, 2)) -> list[str]:
    result = []
    current = start
    while len(result) < n:
        if current.weekday() < 5:
            result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def payload(fields, rows):
    return {"fields": list(fields), "data": rows, "error_code": "0", "error_msg": "success"}


def old_label_dates(calendar, decision):
    month = decision[:7]
    holding = month_add(month, 1)
    following = month_add(month, 2)
    return {
        "holding_month": holding,
        "entry_date": next(day for day in calendar if day[:7] == holding),
        "exit_date": next(day for day in calendar if day[:7] == following),
    }


def cn_fixture():
    calendar = days(320)
    code = "sz.000001"
    decision = max(day for day in calendar if day[:7] == calendar[253][:7])
    daily = [
        [
            day,
            code,
            "10.0000",
            "10.0000",
            "10.0000",
            "10.0000",
            "10.0000",
            "100",
            "1000",
            "3",
            "1",
            "0.000000",
            "0",
        ]
        for day in calendar
    ]
    actions = payload(ADJUSTMENT_FIELDS, [[code, "2020-01-01", "1.000000", "1.000000", "1.000000"]])
    monthly = [
        {
            "code": code,
            "month": decision[:7],
            "decision_date": decision,
            "green": True,
            "return": None,
            **old_label_dates(calendar, decision),
        }
    ]
    return calendar, code, decision, daily, actions, monthly


def test_cn_reuses_fore_adjustment_and_old_green_without_future_eligibility():
    calendar = days(320)
    code = "sz.000001"
    source_rows = [
        [
            day,
            code,
            "10.0000",
            "10.0000",
            "10.0000",
            "10.0000",
            "10.0000",
            "100",
            "1000",
            "3",
            "1",
            "0.000000",
            "0",
        ]
        for day in calendar
    ]
    actions = payload(ADJUSTMENT_FIELDS, [[code, "2020-01-01", "2.000000", "1.000000", "1.000000"]])
    decision = max(day for day in calendar if day[:7] == calendar[253][:7])
    monthly = [
        {
            "code": code,
            "month": decision[:7],
            "decision_date": decision,
            "green": True,
            "return": 0.10,
            "adverse": -0.04,
            "opportunity": 0.20,
            **old_label_dates(calendar, decision),
        }
    ]
    first = cn_symbol_inputs(code, calendar, payload(SOURCE_FIELDS, source_rows), actions, monthly)
    record = first["records"][0]
    assert first["price_basis"] == "raw_ohlc_times_effective_foreAdjustFactor"
    assert first["prices"][decision] == "20.0000000000"
    assert record["green"] is True
    assert record["formation_eligible"] is True
    assert record["scores"]["mom20"] == pytest.approx(0.0)
    assert record["future_labels"]["return"] == pytest.approx(0.10)
    assert record["label_basis"].startswith("saved_next_month_first_open")
    altered = deepcopy(monthly)
    altered[0]["return"] = None
    after = cn_symbol_inputs(code, calendar, payload(SOURCE_FIELDS, source_rows), actions, altered)
    assert after["records"][0]["scores"] == record["scores"]
    assert after["records"][0]["green"] == record["green"]
    assert after["records"][0]["formation_eligible"] == record["formation_eligible"]
    assert after["records"][0]["future_labels"]["return"] is None


def test_cn_missing_calendar_row_and_source_break_invalidate_window():
    calendar = days(320)
    code = "sz.000001"
    decision = max(day for day in calendar if day[:7] == calendar[253][:7])
    decision_index = calendar.index(decision)
    rows = [
        [
            day,
            code,
            "10.0000",
            "10.0000",
            "10.0000",
            "10.0000",
            "10.0000",
            "100",
            "1000",
            "3",
            "1",
            "0.000000",
            "0",
        ]
        for day in calendar
        if day != calendar[decision_index - 10]
    ]
    actions = payload(ADJUSTMENT_FIELDS, [[code, "2020-01-01", "1.000000", "1.000000", "1.000000"]])
    monthly = [
        {
            "code": code,
            "month": decision[:7],
            "decision_date": decision,
            "green": False,
            "return": None,
            **old_label_dates(calendar, decision),
        }
    ]
    result = cn_symbol_inputs(code, calendar, payload(SOURCE_FIELDS, rows), actions, monthly)
    assert calendar[decision_index - 10] not in result["prices"]
    assert calendar[decision_index - 9] in result["source_break_dates"]
    assert calendar[decision_index - 9] not in result["prices"]
    assert result["records"][0]["scores"]["mom20"] is None
    assert result["records"][0]["score_reasons"]["mom20"] == "missing_price"
    assert result["records"][0]["green"] is False
    assert result["records"][0]["formation_eligible"] is True
    assert result["records"][0]["future_labels"]["return"] is None


def test_cn_old_label_month_and_entry_exit_dates_fail_closed():
    calendar, code, _, daily, actions, monthly = cn_fixture()
    for field, value in (
        ("holding_month", "2025-01"),
        ("entry_date", monthly[0]["exit_date"]),
        ("exit_date", monthly[0]["entry_date"]),
        ("entry_date", None),
    ):
        bad = deepcopy(monthly)
        bad[0][field] = value
        with pytest.raises(ValueError, match="future label dates"):
            cn_symbol_inputs(code, calendar, payload(SOURCE_FIELDS, daily), actions, bad)
    exit_month = monthly[0]["exit_date"][:7]
    incomplete = [day for day in calendar if day[:7] < exit_month]
    with pytest.raises(ValueError, match="lacks future label month"):
        cn_symbol_inputs(code, incomplete, payload(SOURCE_FIELDS, daily), actions, monthly)


@pytest.mark.parametrize("field_index,value", [(7, "0"), (12, "1")])
def test_cn_formation_quote_status_and_st_are_exposed_without_changing_green(field_index, value):
    calendar, code, decision, daily, actions, monthly = cn_fixture()
    source = next(row for row in daily if row[0] == decision)
    source[field_index] = value
    result = cn_symbol_inputs(code, calendar, payload(SOURCE_FIELDS, daily), actions, monthly)
    record = result["records"][0]
    assert record["green"] is True
    assert record["formation_eligible"] is False
    assert "formation_not_traded_or_st" in record["formation_reasons"]
    assert record["future_labels"]["return"] is None


def test_cn_formation_source_break_is_not_a_tradable_close():
    calendar, code, decision, daily, actions, monthly = cn_fixture()
    source = next(row for row in daily if row[0] == decision)
    source[11] = "5.000000"  # Reported raw percentage conflicts with flat raw close.
    result = cn_symbol_inputs(code, calendar, payload(SOURCE_FIELDS, daily), actions, monthly)
    record = result["records"][0]
    assert decision in result["source_break_dates"]
    assert record["formation_eligible"] is False
    assert "formation_source_break" in record["formation_reasons"]
    assert "formation_positive_close_missing" in record["formation_reasons"]


def test_etf_full_calendar_six_names_future_unknown_never_changes_qualification():
    calendar = days(350)
    decision = calendar[280]
    month = decision[:7]
    decision = max(day for day in calendar if day[:7] == month)
    index = calendar.index(decision)
    target = calendar[index + 21]
    warm, formal = {}, {}
    for code in ETF_SYMBOLS:
        rows = [{"date": day, "economic_index": 1 + i / 1000} for i, day in enumerate(calendar)]
        warm[code], formal[code] = rows[:252], rows[252:]
    baseline = etf_monthly_inputs(calendar, warm, formal, month, month)[0]
    assert len(baseline["rows"]) == 6
    assert baseline["target_date"] == target
    assert baseline["factor_qualified"]["mom20"] is True
    assert baseline["mix_qualified"] is True
    assert baseline["green_subset_status"] == "not_evaluated_no_qualified_historical_green_flags"
    assert baseline["label_basis"] == (
        "formation_close_to_fixed_plus21_exchange_sessions_economic_index"
    )
    assert all("green" not in row for row in baseline["rows"])
    changed = deepcopy(formal)
    changed[ETF_SYMBOLS[0]] = [
        row for row in changed[ETF_SYMBOLS[0]] if row["date"] != calendar[index + 10]
    ]
    after = etf_monthly_inputs(calendar, warm, changed, month, month)[0]
    assert after["factor_qualified"] == baseline["factor_qualified"]
    assert after["mix_qualified"] == baseline["mix_qualified"]
    assert after["rows"][0]["scores"] == baseline["rows"][0]["scores"]
    assert after["rows"][0]["future_return"] is None
    assert after["rows"][0]["future_reason"] == "future_calendar_price_gap"
    assert after["rows"][1]["future_return"] is not None


def test_etf_prewarm_and_formal_gaps_are_never_compressed():
    calendar = days(350)
    decision = calendar[280]
    month = decision[:7]
    decision = max(day for day in calendar if day[:7] == month)
    i = calendar.index(decision)
    warm, formal = {}, {}
    for code in ETF_SYMBOLS:
        rows = [{"date": day, "economic_index": 1 + j / 1000} for j, day in enumerate(calendar)]
        warm[code], formal[code] = rows[:252], rows[252:]
    warm["159915.SZ"] = [row for row in warm["159915.SZ"] if row["date"] != calendar[i - 240]]
    formal["512100.SS"] = [row for row in formal["512100.SS"] if row["date"] != calendar[i - 10]]
    result = etf_monthly_inputs(calendar, warm, formal, month, month)[0]
    by_code = {row["code"]: row for row in result["rows"]}
    assert by_code["159915.SZ"]["score_reasons"]["mom252"] == "missing_price"
    assert by_code["512100.SS"]["score_reasons"]["mom20"] == "missing_price"
    assert result["factor_qualified"]["mom252"] is False
    assert result["factor_qualified"]["mom20"] is False
    assert result["mix_qualified"] is False
    assert len(result["rows"]) == 6


def test_saved_exchange_calendar_shape_requires_qualified_flags():
    sample = {
        "authority": "exchange_official",
        "market": "CN",
        "months_failed": [],
        "days": {
            "2023-01-02": {"is_trading_day": True},
            "2023-01-03": {"is_trading_day": False},
            "2023-01-04": {"is_trading_day": True},
        },
    }
    assert exchange_trading_days(sample) == ["2023-01-02", "2023-01-04"]
    broken = deepcopy(sample)
    broken["months_failed"] = ["2023-01"]
    with pytest.raises(ValueError):
        exchange_trading_days(broken)
    broken = deepcopy(sample)
    broken["days"]["2023-01-02"]["is_trading_day"] = 1
    with pytest.raises(ValueError):
        exchange_trading_days(broken)


def test_etf_unmatured_last_month_keeps_formation_qualification():
    calendar = days(350)
    month = calendar[-1][:7]
    warm, formal = {}, {}
    for code in ETF_SYMBOLS:
        rows = [{"date": day, "economic_index": 1 + i / 1000} for i, day in enumerate(calendar)]
        warm[code], formal[code] = rows[:252], rows[252:]
    result = etf_monthly_inputs(calendar, warm, formal, month, month)[0]
    assert result["target_date"] is None
    assert result["factor_qualified"]["mom20"] is True
    assert result["mix_qualified"] is True
    assert all(row["future_return"] is None for row in result["rows"])
    assert all(row["future_reason"] == "target_outside_calendar" for row in result["rows"])


def test_etf_rejects_missing_formation_calendar_month():
    calendar = ["2023-01-31", "2023-03-31"]
    empty = {code: [] for code in ETF_SYMBOLS}
    with pytest.raises(ValueError, match="formation month missing"):
        etf_monthly_inputs(calendar, empty, empty, "2023-01", "2023-03")
