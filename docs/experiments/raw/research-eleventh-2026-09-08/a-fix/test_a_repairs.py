from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from unittest.mock import patch

import pandas as pd
import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "research-package"
sys.path.insert(0, str(PACKAGE / "src"))

from lei_signal.rules import first_ma_pullback as a
from lei_signal.rules.strict_structure import SIDE_BOTTOM, StrictStructure


def _frame(days: int = 26) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-01", periods=days)
    frame = pd.DataFrame(
        {
            "open": 10.0,
            "high": 10.5,
            "low": 9.0,
            "close": 10.0,
            "volume": 1_000.0,
            "signal_color": "green",
        },
        index=index,
    )
    for period, sma, ema, lag in (
        (20, 9.2, 8.9, 8.5),
        (60, 8.0, 8.0, 7.5),
        (120, 7.0, 7.0, 6.5),
    ):
        frame[f"sma{period}"] = sma
        frame[f"ema{period}"] = [ema + i * 0.001 for i in range(days)]
        frame[f"close_lag{period}"] = lag
    return frame


def _run(
    frame: pd.DataFrame,
    *,
    structures: list[StrictStructure] | None = None,
    weekly: list[bool] | None = None,
    clock: list[int] | None = None,
):
    weekly_values = weekly or [True] * len(frame)
    clock_values = clock or [a.TYPE2_STEADY_UP] * len(frame)
    with (
        patch.object(
            a,
            "average_true_range",
            lambda data, period: pd.Series(
                [float("nan")] * min(20, len(data))
                + [1.0] * max(0, len(data) - 20),
                index=data.index,
            ),
        ),
        patch.object(
            a,
            "weekly_env_series",
            lambda data: pd.Series(weekly_values, index=data.index),
        ),
        patch.object(
            a,
            "clock_series",
            lambda data: pd.Series(clock_values, index=data.index),
        ),
        patch.object(a, "detect_strict_structures", lambda data: structures or []),
    ):
        return a.detect_first_ma_pullback_events(frame, "SYNTHETIC")


def _bottom(confirmed: date, invalidated: date | None) -> StrictStructure:
    return StrictStructure(
        side=SIDE_BOTTOM,
        confirmed_date=confirmed,
        reference_price=8.0,
        trigger_price=10.3,
        final_price=10.8,
        reference_date=confirmed,
        contained_bars_merged=0,
        structure_id="bottom-1",
        invalidated_date=invalidated,
        invalidated_reason="new_low_breaks_bottom" if invalidated else None,
    )


def test_cached_bottom_invalidated_that_day_cannot_confirm() -> None:
    frame = _frame()
    touch_day = frame.index[20].date()
    confirm_day = frame.index[22].date()
    invalidated_day = frame.index[23].date()
    clock = [a.TYPE2_STEADY_UP] * len(frame)
    clock[22] = 3
    events = _run(
        frame,
        structures=[_bottom(confirm_day, invalidated_day)],
        clock=clock,
    )
    confirmed = [
        event
        for event in events
        if event.evidence["sub_rule"] == a.SUB_RULE_CONFIRMED
        and event.evidence["touch_date"] == touch_day.isoformat()
    ]
    assert confirmed == []


def test_future_invalidation_does_not_hide_bottom_before_that_day() -> None:
    frame = _frame(24)
    confirm_day = frame.index[22].date()
    future_day = date(2024, 12, 31)
    events = _run(frame, structures=[_bottom(confirm_day, future_day)])
    confirmed = [
        event for event in events
        if event.evidence["sub_rule"] == a.SUB_RULE_CONFIRMED
    ]
    assert confirmed
    assert {event.evidence["a3_source"] for event in confirmed} == {a.A3_STRUCTURE}
    assert {event.evidence["a3_structure_id"] for event in confirmed} == {"bottom-1"}


def test_invalid_bottom_falls_back_to_real_ema20_reclaim_reason() -> None:
    frame = _frame()
    frame.loc[frame.index[22], "close"] = 8.8
    frame.loc[frame.index[23], "close"] = 10.0
    confirm_day = frame.index[21].date()
    invalidated_day = frame.index[23].date()
    events = _run(frame, structures=[_bottom(confirm_day, invalidated_day)])
    on_day = [
        event for event in events
        if event.evidence["sub_rule"] == a.SUB_RULE_CONFIRMED
        and event.available_date == invalidated_day
    ]
    assert on_day
    assert {event.evidence["a3_source"] for event in on_day} == {a.A3_RECLAIM}
    assert {event.evidence["a3_structure_id"] for event in on_day} == {None}


def test_weekly_false_touch_is_ignored_and_recovery_starts_first_touch() -> None:
    frame = _frame(23)
    weekly = [True] * len(frame)
    weekly[20] = False
    frame.loc[frame.index[20], "low"] = 9.0
    frame.loc[frame.index[21], "low"] = 9.0
    events = _run(frame, weekly=weekly)
    touches20 = [
        event for event in events
        if event.evidence["sub_rule"] == a.SUB_RULE_TOUCHED
        and event.evidence["ma_period"] == 20
    ]
    assert [event.available_date for event in touches20] == [frame.index[21].date()]
    assert touches20[0].evidence["is_first_touch"] is True
    assert touches20[0].evidence["weekly_bull_env"] is True


@pytest.mark.parametrize("missing", ["volume", "signal_color"])
def test_missing_required_input_is_explicitly_rejected(missing: str) -> None:
    frame = _frame().drop(columns=missing)
    with pytest.raises(ValueError, match=rf"缺少必需字段.*{missing}"):
        a.detect_first_ma_pullback_events(frame, "SYNTHETIC")


def test_complete_required_input_still_executes() -> None:
    assert isinstance(_run(_frame()), list)
