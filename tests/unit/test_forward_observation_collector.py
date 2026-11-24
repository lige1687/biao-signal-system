from datetime import datetime

import pytest

from lei_signal.forward_observation.collector import SHANGHAI, parse_daily, parse_tencent
from lei_signal.forward_observation.runner import next_run


def quote(at="20261021100500", bid="4.1", ask="4.2"):
    fields = [""] * 88
    for i, v in {1: "沪深300ETF华泰柏瑞", 2: "510300", 3: "4.2", 9: bid,
                 10: "17", 19: ask, 20: "23", 30: at}.items():
        fields[i] = v
    return ('v_sh510300="' + "~".join(fields) + '";').encode("gbk")


def daily(date="2026-10-21", close=4.2):
    start = datetime.fromisoformat(f"{date}T09:30:00+08:00")
    end = datetime.fromisoformat(f"{date}T15:00:01+08:00")
    return {"chart": {"error": None, "result": [{
        "meta": {"symbol": "510300.SS", "currency": "CNY",
                 "exchangeTimezoneName": "Asia/Shanghai", "regularMarketTime": end.timestamp()},
        "timestamp": [start.timestamp()], "indicators": {"quote": [{"close": [close]}]},
        "events": {"dividends": {"a": {"date": start.timestamp(), "amount": 0.1}}},
    }]}}


def test_real_quote_preserves_timestamp_depth_and_hash():
    row = parse_tencent(quote(), "2026-10-21T10:05:05+08:00")
    assert row["market_open"] is True
    assert row["ask_size"] == 2300
    assert row["source_time"] == "2026-10-21T10:05:00+08:00"
    assert len(row["source_hash"]) == 64
    assert row["corporate_actions_checked_through"] is None


@pytest.mark.parametrize("stamp,received", [
    ("20261020100500", "2026-10-21T10:05:05+08:00"),
    ("20261021120000", "2026-10-21T12:00:05+08:00"),
    ("20261021161443", "2026-10-21T16:44:05+08:00"),
])
def test_old_lunch_after_close_never_market_open(stamp, received):
    assert not parse_tencent(quote(stamp), received)["market_open"]


def test_future_crossed_quote_not_valid():
    row = parse_tencent(quote(bid="4.3"), "2026-10-21T10:04:00+08:00")
    assert row["quality"] == "invalid"
    assert set(row["reasons"]) == {"source_time_in_future", "bid_ask_missing_or_crossed"}


def test_completed_close_and_unknown_dividend_payment():
    row = parse_daily(daily(), "2026-10-21T16:35:00+08:00")
    assert row["through"] == "2026-10-21"
    assert row["completed_close"] == {"source_time": "2026-10-21T15:00:00+08:00", "last": 4.2}
    assert row["actions"][0]["pay_date"] is None


def test_no_early_or_previous_day_close():
    assert parse_daily(daily(), "2026-10-21T15:05:00+08:00")["completed_close"] is None
    assert parse_daily(daily("2026-10-20"), "2026-10-21T16:35:00+08:00")["completed_close"] is None


def test_missing_close_and_future_vendor_time_rejected():
    with pytest.raises(ValueError, match="no valid"):
        parse_daily(daily(close=None), "2026-10-21T16:35:00+08:00")
    with pytest.raises(ValueError, match="future"):
        parse_daily(daily(), "2026-10-21T10:00:00+08:00")


@pytest.mark.parametrize("now,expected", [
    ("2026-10-21T09:00:00", "2026-10-21T09:30:00"),
    ("2026-10-21T10:00:00", "2026-10-21T10:05:00"),
    ("2026-10-21T11:29:00", "2026-10-21T13:00:00"),
    ("2026-10-21T14:59:00", "2026-10-21T16:35:00"),
    ("2026-10-23T16:35:00", "2026-10-26T09:30:00"),
])
def test_next_run_no_backfill_or_weekend(now, expected):
    assert next_run(datetime.fromisoformat(now).replace(tzinfo=SHANGHAI)) == (
        datetime.fromisoformat(expected).replace(tzinfo=SHANGHAI))
