"""Synthetic source boundary checks; no market or network access."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from lei_signal.strategy_portfolios import sources


def _chart(*, symbol="AAPL", dates=("2026-10-19", "2026-10-20"),
           currency="USD", timezone="America/New_York", volumes=(10, 20)):
    timestamps = [int(datetime.fromisoformat(d + "T12:00:00").replace(
        tzinfo=ZoneInfo(timezone)).timestamp()) for d in dates]
    return {"chart": {"error": None, "result": [{
        "meta": {"symbol": symbol, "currency": currency,
                 "exchangeTimezoneName": timezone},
        "timestamp": timestamps,
        "indicators": {"quote": [{"open": [100, 120], "high": [115, 125],
                                  "low": [95, 115], "close": [110, 120],
                                  "volume": list(volumes)}],
                       "adjclose": [{"adjclose": [99, 108]}]},
        "events": {"dividends": {"a": {"amount": 1.0}},
                   "splits": {"b": {"numerator": 2, "denominator": 1}}},
    }]}}


def test_yahoo_adjustment_actions_and_incomplete_session():
    payload = _chart()
    early = sources.parse_yahoo_history(payload, "AAPL", "2026-10-20T16:14:00-04:00")
    assert len(early["bars"]) == 1
    assert early["metadata"]["skipped"] == [{"date": "2026-10-20", "reason": "close_not_complete"}]
    late = sources.parse_yahoo_history(payload, "AAPL", "2026-10-20T16:15:00-04:00")
    assert len(late["bars"]) == 2
    assert late["bars"][0]["raw_open"] == 100
    assert late["bars"][0]["open"] == 90
    assert late["bars"][0]["high"] == pytest.approx(115 * .9)
    assert late["bars"][0]["close"] == 99
    assert late["events"]["dividends"]["a"]["amount"] == 1
    assert late["events"]["splits"]["b"]["numerator"] == 2
    assert late["bars"][0]["eligible_buy"] is None
    assert late["bars"][0]["open_tradable"] is None
    assert late["metadata"]["st_status"] == "unknown"


def test_yahoo_rejects_identity_future_and_malformed_prices():
    payload = _chart()
    with pytest.raises(ValueError, match="symbol or currency"):
        sources.parse_yahoo_history(payload, "MSFT", "2026-10-21T17:00:00-04:00")
    with pytest.raises(ValueError, match="future bar"):
        sources.parse_yahoo_history(payload, "AAPL", "2026-10-19T17:00:00-04:00")
    payload["chart"]["result"][0]["indicators"]["quote"][0]["close"][0] = None
    parsed = sources.parse_yahoo_history(payload, "AAPL", "2026-10-21T17:00:00-04:00")
    assert parsed["metadata"]["skipped"][0]["reason"] == "missing_or_invalid_price"
    assert len(parsed["bars"]) == 1


def test_yahoo_quarantines_incoherent_ohlc():
    payload = _chart()
    payload["chart"]["result"][0]["indicators"]["quote"][0]["low"][0] = 111
    parsed = sources.parse_yahoo_history(payload, "AAPL", "2026-10-21T17:00:00-04:00")
    assert parsed["metadata"]["skipped"][0]["date"] == "2026-10-19"
    assert len(parsed["bars"]) == 1


def test_yahoo_cn_close_and_zero_volume():
    payload = _chart(symbol="600000.SS", currency="CNY", timezone="Asia/Shanghai",
                     volumes=(10, 0))
    early = sources.parse_yahoo_history(payload, "600000.SS", "2026-10-20T15:14:00+08:00")
    assert len(early["bars"]) == 1
    parsed = sources.parse_yahoo_history(payload, "600000.SS", "2026-10-20T15:15:00+08:00")
    assert parsed["metadata"]["market"] == "CN"
    assert parsed["metadata"]["currency"] == "CNY"
    assert parsed["bars"][1]["valid"] is True
    assert parsed["bars"][1]["eligible_buy"] is False
    assert parsed["bars"][1]["open_buy_allowed"] is None
    with pytest.raises(ValueError, match="currency mismatch"):
        sources.parse_yahoo_history(_chart(symbol="600000.SS"), "600000.SS",
                                    "2026-10-20T15:15:00+08:00")


def test_yahoo_rejects_non_finite_prices():
    payload = _chart()
    payload["chart"]["result"][0]["indicators"]["quote"][0]["open"][0] = float("nan")
    parsed = sources.parse_yahoo_history(payload, "AAPL", "2026-10-21T17:00:00-04:00")
    assert parsed["metadata"]["skipped"][0]["reason"] == "missing_or_invalid_price"


def test_cn_symbol_conversion():
    assert sources.cn_to_yahoo_symbol("sh.600000") == "600000.SS"
    assert sources.cn_to_yahoo_symbol("sz.000001") == "000001.SZ"
    with pytest.raises(ValueError):
        sources.cn_to_yahoo_symbol("600000")


def test_confirmed_close_cutoffs():
    assert sources.completed_market_date("CN", "2026-10-20T15:14:00+08:00") == "2026-10-19"
    assert sources.completed_market_date("CN", "2026-10-20T15:15:00+08:00") == "2026-10-20"
    assert sources.completed_market_date("US", "2026-10-20T16:14:00-04:00") == "2026-10-19"
    assert sources.completed_market_date("US", "2026-10-20T16:15:00-04:00") == "2026-10-20"
    assert sources.proposed_session_open("US", "2026-10-20") == "2026-10-20T09:30:00-04:00"
    assert sources.proposed_session_open("CN", "2026-10-20") == "2026-10-20T09:30:00+08:00"


def test_us_loader_retains_missing_symbols(tmp_path, monkeypatch):
    members = [{"code": "AAPL", "name": "Apple"}]
    members += [{"code": f"MISS{i:03}", "name": "Missing"} for i in range(503)]
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"selection": {"us": members}}))
    monkeypatch.setattr(sources, "_US_CONTRACT", contract)
    payload = _chart(dates=("2026-10-19", "2026-10-20"))
    raw = json.dumps(payload).encode()
    (tmp_path / "AAPL.json").write_bytes(raw)
    attempts = [{"code": "AAPL", "status": "ok", "file": "AAPL.json",
                 "sha256": hashlib.sha256(raw).hexdigest(),
                 "retrieved_at": "2026-10-21T17:00:00-04:00"}]
    attempts += [{"code": m["code"], "status": "failed"} for m in members[1:]]
    (tmp_path / "attempts.jsonl").write_text("\n".join(json.dumps(a) for a in attempts))
    result = sources.load_historical_us(tmp_path)
    assert len(result["universe"]) == 504
    assert result["metadata"]["priced_symbols"] == 1
    assert len(result["metadata"]["missing_symbols"]) == 503
    assert len(result["bars"]) == 2


def test_bound_json_rejects_mutated_source(tmp_path):
    p = tmp_path / "source.json"
    p.write_text('{"answer":1}')
    with pytest.raises(ValueError, match="hash changed"):
        sources._bound_json({"path": str(p), "sha256": "0" * 64})


def test_cn_loader_keeps_suspension_st_and_source_break(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"asset_sources": {
        f"sh.{i:06}": {"daily": {}, "adjustments": {}} for i in range(300)
    }}))
    calendar = tmp_path / "calendar.json"
    calendar.write_text(json.dumps({"fields": ["calendar_date", "is_trading_day"],
                                    "data": [["2026-01-05", "1"], ["2026-01-06", "1"]]}))
    monkeypatch.setattr(sources, "_bound_json", lambda _: {})

    def adapted(_daily, _actions, code, _calendar, factor_field):
        assert factor_field == "foreAdjustFactor"
        return {"rows": [{"date": "2026-01-05", "tradestatus": "1", "isST": "1",
                          "open": "10", "close": "11", "volume": "100"}],
                "raw_by_day": {"2026-01-05": {"volume": "100", "isST": "1",
                                               "tradestatus": "1"},
                               "2026-01-06": {"volume": "0", "isST": "0",
                                               "tradestatus": "0"}},
                "break_dates": ["2026-01-06"], "failures": {"2026-01-06": ["gap"]}}

    monkeypatch.setattr(sources, "adapt_back_adjusted", adapted)
    result = sources.load_historical_cn(manifest, calendar)
    rows = [row for row in result["bars"] if row["symbol"] == "sh.000000"]
    assert len(result["universe"]) == 300
    assert rows[0]["tradable"] and not rows[0]["eligible_buy"]
    assert rows[0]["open_tradable"] and not rows[0]["open_buy_allowed"]
    assert rows[1]["source_break"] and rows[1]["close"] is None
