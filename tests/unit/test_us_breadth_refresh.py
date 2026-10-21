from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json

import pandas as pd
import pytest

from lei_signal.market_context.us_breadth_refresh import build_candidate, closed_date, parse_chart, install_candidate


def fixture():
    dates = pd.bdate_range("2025-01-01", periods=240)
    names = [f"STOCK{i}" for i in range(120)]
    prices = pd.DataFrame({s: range(1, 241) for s in names}, index=dates)
    old = [{"date": dates[230].strftime("%Y-%m-%d"), "breadth_20": 12.3,
            "breadth_50": 45.6, "breadth_200": 78.9}]
    return old, prices, dates, names


def test_append_preserves_history_and_has_each_closed_session():
    old, prices, dates, names = fixture()
    rows, audit = build_candidate(old, prices, dates, names)
    assert rows[:len(old)] == old
    assert len(audit) == 9
    assert rows[-1] == {"date": dates[-1].strftime("%Y-%m-%d"),
                        "breadth_20": 100, "breadth_50": 100, "breadth_200": 100}
    assert audit[-1]["eligible"] == {"20": 120, "50": 120, "200": 120}


def test_missing_stock_session_is_not_forward_filled():
    old, prices, dates, names = fixture()
    prices.loc[dates[225], names[:8]] = float("nan")
    with pytest.raises(ValueError, match="insufficient coverage"):
        build_candidate(old, prices, dates, names)


def test_missing_whole_market_session_is_not_compressed_out_of_ma():
    old, prices, dates, names = fixture()
    with pytest.raises(ValueError, match="insufficient coverage"):
        build_candidate(old, prices.drop(index=dates[225]), dates, names)


def test_no_new_sessions_and_duplicate_dates_are_rejected():
    old, prices, dates, names = fixture()
    with pytest.raises(ValueError, match="no completed"):
        build_candidate(old, prices, dates[:231], names)
    with pytest.raises(ValueError, match="duplicate"):
        build_candidate(old, pd.concat([prices, prices.tail(1)]), dates, names)


def test_adjusted_close_and_closed_date_only():
    payload = {"chart": {"error": None, "result": [{
        "timestamp": [int(datetime(2026, 10, d, 13, 30, tzinfo=ZoneInfo("UTC")).timestamp()) for d in (20, 21)],
        "indicators": {"adjclose": [{"adjclose": [50, 51]}], "quote": [{"close": [100, 102]}]},
    }]}}
    parsed = parse_chart(payload, "2026-10-20")
    assert parsed.to_dict() == {pd.Timestamp("2026-10-20"): 50}
    assert closed_date(datetime(2026, 10, 21, 12, tzinfo=ZoneInfo("America/New_York"))) == "2026-10-20"
    assert closed_date(datetime(2026, 10, 21, 17, tzinfo=ZoneInfo("America/New_York"))) == "2026-10-21"


def test_no_adjusted_price_does_not_fall_back_to_raw_close():
    payload = {"chart": {"error": None, "result": [{"timestamp": [1], "indicators": {"quote": [{"close": [123]}]}}]}}
    with pytest.raises(KeyError):
        parse_chart(payload, "2026-10-20")


def test_install_checks_source_and_retains_exact_backup(tmp_path):
    target = tmp_path / "live.json"
    original = b'[{"date":"2026-09-04","breadth_20":42}]'
    candidate = original[:-1] + b',{"date":"2026-09-08","breadth_20":45}]'
    target.write_bytes(original)
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    (prepared / "sp500_ma_breadth_history.json").write_bytes(candidate)
    (prepared / "receipt.json").write_text(json.dumps({
        "qualified": True, "previous_file": str(target),
        "previous_sha256": hashlib.sha256(original).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
    }))
    result = install_candidate(prepared, target)
    assert result["installed"] and target.read_bytes() == candidate
    assert list(tmp_path.glob("*.bak"))[0].read_bytes() == original
    with pytest.raises(ValueError, match="live source changed"):
        install_candidate(prepared, target)
