"""A3 must use a bottom that is still valid on the entry evaluation date.

Prices follow the independently reviewed five-bar example. Only the unrelated
clock, weekly environment and ATR inputs are controlled; strict structures and
the A3 state machine are the current production functions.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

import pandas as pd
import pytest

from lei_signal.domain.types import SignalEvent
from lei_signal.rules import first_ma_pullback as a3
from lei_signal.rules.strict_structure import detect_strict_structures


def _frame(
    *, expired: bool = True, alternative: bool = False, future: bool = False
) -> pd.DataFrame:
    rows = [
        (11, 9, 10.5),
        (12, 10, 11.5),
        (13, 11, 12),
        (12, 8 if expired else 10.5, 11),
        (13, 10 if expired else 11, 12.5),
    ]
    if future:
        rows.append((12, 8, 11))
    frame = pd.DataFrame(
        rows, columns=["high", "low", "close"],
        index=pd.bdate_range("2024-01-01", periods=len(rows)),
    )
    frame["open"] = frame["close"]
    frame["volume"] = 1000.0
    for period, value in ((20, 10.0), (60, 7.0), (120, 6.0)):
        frame[f"sma{period}"] = value
        frame[f"close_lag{period}"] = 5.0
    frame["ema20"] = (
        ([9, 12, 12, 11, 11.5] if alternative else [9, 9, 9, 9, 9.5])
        + ([9.5] if future else [])
    )
    frame["ema60"] = 7.0
    frame["ema120"] = 6.0
    frame["signal_color"] = "green"
    return frame


def _entries(frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> list[SignalEvent]:
    monkeypatch.setattr(a3, "clock_series", lambda f: pd.Series(2, index=f.index))
    monkeypatch.setattr(a3, "weekly_env_series", lambda f: pd.Series(True, index=f.index))
    monkeypatch.setattr(a3, "average_true_range", lambda f, _n: pd.Series(5.0, index=f.index))
    return [
        event for event in a3.detect_first_ma_pullback_events(frame, "TEST")
        if event.evidence.get("sub_rule") == a3.SUB_RULE_CONFIRMED
        and event.evidence.get("ma_period") == 20
    ]


def _assert_both_variants(events: list[SignalEvent]) -> None:
    assert len(events) == 2
    assert {e.evidence["entry_variant"] for e in events} == {
        a3.ENTRY_EARLY, a3.ENTRY_CONFIRMED,
    }
    assert {e.available_date for e in events} == {date(2024, 1, 5)}


def test_expired_cached_bottom_cannot_support_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame()
    bottom = next(
        s for s in detect_strict_structures(frame)
        if s.side == "bottom" and s.reference_price == 9.0
    )
    assert bottom.confirmed_date == date(2024, 1, 3)
    assert bottom.invalidated_date == date(2024, 1, 4)
    assert _entries(frame, monkeypatch) == []


def test_valid_cached_bottom_still_supports_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    events = _entries(_frame(expired=False), monkeypatch)
    _assert_both_variants(events)
    assert all(e.evidence["a3_source"] == a3.A3_STRUCTURE for e in events)
    assert all(e.evidence["a3_structure_id"] is not None for e in events)
    assert all(e.evidence["stop_price"] == 9.0 for e in events)


def test_ema_reclaim_remains_an_independent_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    events = _entries(_frame(alternative=True), monkeypatch)
    _assert_both_variants(events)
    assert all(e.evidence["a3_source"] == a3.A3_RECLAIM for e in events)
    assert all(e.evidence["a3_structure_id"] is None for e in events)
    assert all(e.evidence["stop_price"] == 8.0 for e in events)


def test_future_expiry_preserves_all_past_entry_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = _entries(_frame(expired=False), monkeypatch)
    _assert_both_variants(prefix)
    extended = _entries(_frame(expired=False, future=True), monkeypatch)
    assert [asdict(e) for e in extended] == [asdict(e) for e in prefix]
