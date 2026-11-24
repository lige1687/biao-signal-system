"""Offline checks of the actual existing commodity source, with no Yahoo calls."""
from copy import deepcopy
from datetime import datetime

import pytest

from lei_signal.fundamentals import sources


@pytest.fixture
def dated_prices():
    return {
        "HG=F": [("2026-09-29", 3.8), ("2026-09-30", 4.0)],
        "GC=F": [("2026-09-28", 1990.0), ("2026-09-29", 2000.0)],
        "CL=F": [("2026-09-29", 70.0), ("2026-09-30", 72.0)],
    }


def calculate(monkeypatch, prices):
    calls = []
    def closes(tickers, period):
        calls.append((tickers, period))
        return deepcopy(prices)
    monkeypatch.setattr(sources, "_yf_closes", closes)
    monkeypatch.setattr(sources, "_yf_last", lambda *a, **k: pytest.fail("Undated helper used"))
    result = sources.fetch_commodity_ratios()
    assert calls == [(["HG=F", "GC=F", "CL=F"], "3mo")]
    return result


def test_latest_common_day_prevents_stale_gold_mix(monkeypatch, dated_prices):
    result = calculate(monkeypatch, dated_prices)
    assert result["copper_gold"] == pytest.approx(0.0019)
    assert result["copper_gold"] != 4.0 / 2000.0
    assert result["crude_gold"] == 70.0 / 2000.0
    assert (result["copper"], result["gold"], result["crude"]) == (3.8, 2000.0, 70.0)
    meta = result["meta"]
    assert meta["quote_date"] == "2026-09-29"
    assert meta["latest_dates"] == {"HG=F": "2026-09-30", "GC=F": "2026-09-29", "CL=F": "2026-09-30"}
    assert meta["tickers"] == {"copper": "HG=F", "gold": "GC=F", "crude": "CL=F"}
    assert datetime.fromisoformat(meta["retrieved_at_utc"]).utcoffset().total_seconds() == 0
    assert all(meta[key] == "unknown" for key in ["publication_time", "quote_units", "roll_contract_identity", "data_usage_license"])


def test_precision_is_not_pre_rounded(monkeypatch, dated_prices):
    dated_prices["HG=F"][0] = ("2026-09-29", 3.8001)
    assert calculate(monkeypatch, dated_prices)["copper_gold"] == 3.8001 / 2000.0


def test_common_day_uses_all_three_and_handles_unsorted_rows(monkeypatch, dated_prices):
    dated_prices["CL=F"] = [("2026-09-28", 60.0), ("2026-09-27", 59.0)]
    dated_prices["HG=F"] = [("2026-09-30", 4.0), ("2026-09-28", 3.7)]
    result = calculate(monkeypatch, dated_prices)
    assert result["meta"]["quote_date"] == "2026-09-28"
    assert result["gold"] == 1990.0
    assert result["copper_gold"] == 3.7 / 1990.0


@pytest.mark.parametrize("ticker", ["HG=F", "GC=F", "CL=F"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_inputs_fail_closed(monkeypatch, dated_prices, ticker, value):
    dated_prices[ticker][0] = (dated_prices[ticker][0][0], value)
    assert calculate(monkeypatch, dated_prices) is None


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_nonpositive_gold_fails_closed(monkeypatch, dated_prices, value):
    dated_prices["GC=F"][1] = ("2026-09-29", value)
    assert calculate(monkeypatch, dated_prices) is None


def test_finite_negative_crude_is_allowed(monkeypatch, dated_prices):
    dated_prices["CL=F"][0] = ("2026-09-29", -37.0)
    result = calculate(monkeypatch, dated_prices)
    assert result["crude"] == -37.0
    assert result["crude_gold"] == -37.0 / 2000.0


@pytest.mark.parametrize("value", [3.8, 99.0])
def test_duplicate_date_even_identical_is_rejected(monkeypatch, dated_prices, value):
    dated_prices["HG=F"].append(("2026-09-29", value))
    assert calculate(monkeypatch, dated_prices) is None


def test_no_common_date_is_unavailable(monkeypatch, dated_prices):
    dated_prices["CL=F"] = [("2026-09-27", 70.0)]
    assert calculate(monkeypatch, dated_prices) is None


@pytest.mark.parametrize("rows", [[], None])
def test_missing_series_is_unavailable(monkeypatch, dated_prices, rows):
    dated_prices["CL=F"] = rows
    assert calculate(monkeypatch, dated_prices) is None


def test_malformed_date_is_unavailable(monkeypatch, dated_prices):
    dated_prices["HG=F"][0] = ("2026-9-29", 3.8)
    assert calculate(monkeypatch, dated_prices) is None


def test_source_failure_is_unavailable(monkeypatch):
    def failed(*args, **kwargs):
        raise sources.FundamentalsSourceError("offline fixture failure")
    monkeypatch.setattr(sources, "_yf_closes", failed)
    assert sources.fetch_commodity_ratios() is None


@pytest.mark.parametrize("value", [True, False, "2000", "bad", None])
def test_bool_and_nonnumeric_prices_are_rejected(monkeypatch, dated_prices, value):
    dated_prices["GC=F"][1] = ("2026-09-29", value)
    assert calculate(monkeypatch, dated_prices) is None


def test_future_quote_date_is_rejected_against_frozen_utc_read_day(monkeypatch, dated_prices):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1, 8, 0, tzinfo=tz)
    monkeypatch.setattr(sources, "datetime", FrozenDatetime)
    dated_prices["HG=F"].append(("2026-10-02", 4.1))
    assert calculate(monkeypatch, dated_prices) is None


def test_utc_read_day_itself_is_allowed(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1, 8, 0, tzinfo=tz)
    monkeypatch.setattr(sources, "datetime", FrozenDatetime)
    prices = {"HG=F": [("2026-10-01", 4.0)], "GC=F": [("2026-10-01", 2000.0)], "CL=F": [("2026-10-01", 70.0)]}
    result = calculate(monkeypatch, prices)
    assert result["meta"]["quote_date"] == "2026-10-01"
    assert result["meta"]["retrieved_at_utc"] == "2026-10-01T08:00:00+00:00"
