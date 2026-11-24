from collections import Counter
import json
import pytest

from lei_signal.research.focus_recent import observation, stock_windows
from lei_signal.research import focus_recent


def test_21_adjacent_sessions_and_zero_daily_amount():
    days = [f"2026-01-{i:02d}" for i in range(1, 22)]
    raw = {day: {"tradestatus": "1", "isST": "0", "amount": "1"} for day in days}
    raw[days[-1]]["amount"] = "0"
    adapted = {"research_price_basis": "raw_ohlc_times_effective_foreAdjustFactor",
               "rows": [{"date": day, "close": str(100 + i)} for i, day in enumerate(days)],
               "raw_by_day": raw, "break_dates": []}
    audit = Counter()
    result = stock_windows(adapted, days, "A", audit)
    assert result[days[-1]]["mean_amount"] == 19 / 20
    assert result[days[-1]]["current_amount"] == 0
    assert result[days[-1]]["momentum"] == 120 / 100 - 1
    broken = {**adapted, "break_dates": [days[-1]]}
    assert stock_windows(broken, days, "A", Counter()) == {}
    missing = {**adapted, "raw_by_day": {k: v for k, v in raw.items() if k != days[4]}}
    assert stock_windows(missing, days, "A", Counter()) == {}


def test_fixed_five_percent_tie_order_and_100_stock_gate():
    stock = {f"C{i:03d}": {"momentum": i / 100, "mean_amount": 100 if i >= 105 else 1,
                           "current_amount": 0} for i in range(110)}
    result = observation("2026-01-21", stock)
    assert result["qualified_count"] == 110
    assert result["focus_count"] == 6
    assert result["focus_members"] == [f"C{i:03d}" for i in range(105, 110)] + ["C000"]
    assert result["concentration"] == 501 / 605
    assert observation("2026-01-21", dict(list(stock.items())[:99]))["focus"] is None


@pytest.mark.parametrize("fault", ["duplicate", "missing", "different_cohort", "wrong_end", "wrong_manifest", None])
def test_gap_admission_rejects_incomplete_or_mixed_packets(tmp_path, monkeypatch, fault):
    result = {"status": "qualified_raw_available", "asOfRequested": "2026-11-02",
              "dailyRange": ["2026-10-26", "2026-11-02"],
              "factorRange": ["2026-10-24", "2026-11-02"], "manifestSha256": "original",
              "acquisitionLedger": {"path": "ledger", "sha256": "verified"}}
    ledger = {"fixedManifestSha256": "original", "responses": [
        {"code": "A", "kind": "daily"}, {"code": "A", "kind": "factor"}]}
    if fault == "duplicate": ledger["responses"].append(ledger["responses"][0])
    if fault == "missing": ledger["responses"].pop()
    if fault == "different_cohort": ledger["responses"][0]["code"] = "B"
    if fault == "wrong_end": result["asOfRequested"] = "2026-11-03"
    if fault == "wrong_manifest": ledger["fixedManifestSha256"] = "changed"
    monkeypatch.setattr(focus_recent, "checked", lambda *_: json.dumps(ledger).encode())
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    if fault:
        with pytest.raises(ValueError): focus_recent.gap_sources(path, {"A"}, "2026-11-02")
    else:
        grouped, meta = focus_recent.gap_sources(path, {"A"}, "2026-11-02")
        assert set(grouped["A"]) == {"daily", "factor"}
        assert meta["ledgerSha256"] == "verified"
