"""首次均线回撤确认事件的回测口径。"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lei_signal.domain.types import Direction, Provenance, Severity, SignalEvent
from lei_signal.research.first_ma_pullback_backtest import (
    PULLBACK_BACKTEST_HORIZONS,
    build_first_ma_pullback_backtest,
)
from lei_signal.rules.first_ma_pullback import SUB_RULE_CONFIRMED


def _frame(rows: int = 140) -> pd.DataFrame:
    index = pd.bdate_range("2025-01-02", periods=rows)
    close = [100.0 + position * 0.5 for position in range(rows)]
    frame = pd.DataFrame(
        {
            "open": [value - 0.2 for value in close],
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "atr14": 2.0,
            "signal_color": "green",
            "sma20": [value - 1.0 for value in close],
            "sma60": [value - 5.0 for value in close],
            "sma120": [value - 10.0 for value in close],
            "sma20_slope": 0.5,
            "sma60_slope": 0.3,
            "sma120_slope": 0.1,
        },
        index=index,
    )
    return frame


def _event(frame: pd.DataFrame, position: int, period: int = 20) -> SignalEvent:
    day: date = frame.index[position].date()
    return SignalEvent(
        event_id=f"event-{period}-{position}",
        symbol="TEST",
        timeframe="1d",
        event_date=day,
        available_date=day,
        rule_id="first_ma_pullback",
        rule_version="1.0.0",
        direction=Direction.BULLISH,
        severity=Severity.IMPORTANT,
        strength=75,
        reason_cn="test",
        provenance=Provenance.RESEARCH_PROXY,
        evidence={"sub_rule": SUB_RULE_CONFIRMED, "ma_period": period},
    )


def test_horizons_include_120_days() -> None:
    assert PULLBACK_BACKTEST_HORIZONS == (5, 10, 20, 60, 120)


def test_fixed_horizon_reports_mean_median_mfe_mae_and_incomplete() -> None:
    frame = _frame()
    report = build_first_ma_pullback_backtest(frame, [_event(frame, 10)])
    assert report is not None
    side = next(item for item in report.sides if item.ma_period == 20)
    by_key = {stat.key: stat for stat in side.stats}
    assert by_key["day_5"].sample_count == 1
    assert by_key["day_5"].mean_return == pytest.approx((107.5 / 105.0 - 1.0) * 100.0)
    assert by_key["day_5"].median_return == by_key["day_5"].mean_return
    assert by_key["day_5"].mean_mfe is not None
    assert by_key["day_5"].mean_mae is not None
    assert by_key["day_120"].sample_count == 1
    assert by_key["day_120"].incomplete_count == 0


def test_incomplete_horizon_is_not_mixed_into_returns() -> None:
    frame = _frame()
    report = build_first_ma_pullback_backtest(frame, [_event(frame, 100)])
    assert report is not None
    side = next(item for item in report.sides if item.ma_period == 20)
    by_key = {stat.key: stat for stat in side.stats}
    assert by_key["day_60"].sample_count == 0
    assert by_key["day_60"].incomplete_count == 1
    assert by_key["day_60"].mean_return is None


def test_rule_exit_uses_first_black_slope_break_or_price_failure() -> None:
    frame = _frame(80)
    entry = 10
    frame.loc[frame.index[15], "sma20_slope"] = 0.0
    report = build_first_ma_pullback_backtest(frame, [_event(frame, entry)])
    assert report is not None
    side = next(item for item in report.sides if item.ma_period == 20)
    stat = next(item for item in side.stats if item.key == "rule_exit")
    assert stat.sample_count == 1
    assert stat.mean_holding_days == pytest.approx(5.0)
    assert side.open_trades == 0


def test_no_confirmed_events_returns_none() -> None:
    assert build_first_ma_pullback_backtest(_frame(), []) is None
