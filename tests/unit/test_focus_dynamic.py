"""Synthetic, source-free checks for dynamic focus input mechanics."""
from collections import Counter

import pytest

from lei_signal.research.focus_dynamic import DailyAccumulator, daily_windows, eligible_code
from lei_signal.research.focus_recent import merge_rows
from lei_signal.research.high52_revalidation import ADJUSTMENT_FIELDS


def _adapted(days, *, missing=None, suspended=None, st=None, broken=None):
    missing, suspended, st, broken = set(missing or []), set(suspended or []), set(st or []), set(broken or [])
    raw = {day: {"tradestatus": "0" if day in suspended else "1",
                 "amount": "10", "isST": "1" if day in st else "0"}
           for day in days if day not in missing}
    prices = [{"date": day, "close": str(i + 1)} for i, day in enumerate(days)
              if day not in missing and day not in broken]
    return {"raw_by_day": raw, "rows": prices, "break_dates": list(broken)}


def test_dynamic_scope_excludes_beijing_bshares_and_nonordinary_codes():
    assert eligible_code("sh.688001", "1")
    assert eligible_code("sz.301001", "1")
    assert not eligible_code("bj.430001", "1")
    assert not eligible_code("sh.900901", "1")
    assert not eligible_code("sh.689009", "1")
    assert not eligible_code("sh.600000", "2")


def test_rank_tie_and_top_five_percent_after_eligibility():
    acc = DailyAccumulator(120)
    for i in range(100):
        acc.add("2025-01-02", f"sh.600{i:03d}", 100.0 if i < 10 else 10.0, i / 100)
    row = acc.finish(["2025-01-02"])[0]
    assert row["signal_valid"] and row["qualified_count"] == 100
    assert row["focus_count"] == 5
    assert row["focus_members"] == [f"sh.600{i:03d}" for i in range(5)]
    assert row["focus"] == pytest.approx(0.02)
    assert row["concentration"] == pytest.approx(500 / 1900)


def test_missing_suspension_st_and_ipo_boundaries_break_windows():
    days = [f"2025-01-{i:02d}" for i in range(1, 30)]
    assert len(daily_windows(_adapted(days), days, days[0], None, Counter())) == 9
    audit = Counter()
    rows = daily_windows(_adapted(days, missing={days[5]}), days, days[0], None, audit)
    assert len(rows) == 3 and rows[0][0] == days[26] and audit["missing_source_day"] == 1
    assert len(daily_windows(_adapted(days, suspended={days[5]}), days, days[0], None, Counter())) == 3
    assert len(daily_windows(_adapted(days, broken={days[5]}), days, days[0], None, Counter())) == 3
    assert len(daily_windows(_adapted(days, st={days[20]}), days, days[0], None, Counter())) == 8
    assert len(daily_windows(_adapted(days), days, days[6], None, Counter())) == 3
    assert len(daily_windows(_adapted(days), days, days[0], days[24], Counter())) == 4


def test_factor_conflict_fails_closed(monkeypatch):
    # Synthetic event sources with the same effective day and different factors.
    refs = [{"path": "one", "sha256": "a"}, {"path": "two", "sha256": "b"}]
    def fake_source(ref, _fields, _code):
        factor = "1" if ref["path"] == "one" else "2"
        return [["sh.600000", "2020-01-01", factor, factor, factor]]
    monkeypatch.setattr("lei_signal.research.focus_recent.source", fake_source)
    with pytest.raises(ValueError, match="conflicting factor events"):
        merge_rows("sh.600000", refs, ADJUSTMENT_FIELDS, "1900-01-01", "2025-12-31", Counter(), [])


def test_amount_window_excludes_twenty_day_return_start():
    days = [f"2025-01-{i:02d}" for i in range(1, 22)]
    adapted = _adapted(days)
    adapted["raw_by_day"][days[0]]["amount"] = ""
    assert len(daily_windows(adapted, days, days[0], None, Counter())) == 1
    adapted["raw_by_day"][days[1]]["amount"] = ""
    assert daily_windows(adapted, days, days[0], None, Counter()) == []
