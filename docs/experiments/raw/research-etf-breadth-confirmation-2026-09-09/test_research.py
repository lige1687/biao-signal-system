import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from research_engine import (  # noqa: E402
    BuyConfirmationState,
    breadth_from_close_panel,
    month_end_signal_dates,
    target_action,
    price_trend_targets,
)
from run_backtest import continuous_close, execute_target  # noqa: E402
from decimal import Decimal as D


def test_b50_b200_share_denominator_and_missing_is_not_weak():
    dates = pd.bdate_range("2020-01-01", periods=205)
    panel = pd.DataFrame(
        {
            "a": range(1, 206),
            "b": range(205, 0, -1),
            "c": [10.0] * 199 + [None] * 6,
        },
        index=dates,
        dtype=float,
    )
    out = breadth_from_close_panel(panel, {d: ("a", "b", "c") for d in dates}, 0.5)
    last = out.iloc[-1]
    assert last.eligible == 2
    assert last.missing == 1
    assert last.b50 == 50.0
    assert last.b200 == 50.0


def test_confirmation_waits_then_executes_once():
    s = BuyConfirmationState(current_target=0.0)
    assert s.on_raw_target("2020-01-03", 1.0, confirmed=False) is None
    assert s.on_confirmation("2020-01-06", confirmed=False) is None
    order = s.on_confirmation("2020-01-07", confirmed=True)
    assert order["target"] == 1.0
    assert order["signal_date"] == "2020-01-07"
    s.on_fill(1.0)
    assert s.on_confirmation("2020-01-08", confirmed=True) is None


def test_confirmation_cancel_cross_tier_reduction_and_reentry():
    s = BuyConfirmationState(current_target=0.0)
    s.on_raw_target("2020-01-03", 1.0, confirmed=False)
    s.on_raw_target("2020-01-10", 0.5, confirmed=False)
    assert s.pending_target == 0.5
    reduction = s.on_raw_target("2020-01-17", 0.0, confirmed=False)
    assert reduction["target"] == 0.0
    assert s.pending_target is None
    s.on_fill(0.0)
    s.on_raw_target("2020-01-24", 1.0, confirmed=False)
    order = s.on_confirmation("2020-01-27", confirmed=True)
    assert order["target"] == 1.0


def test_price_trend_and_month_end_have_fixed_timing():
    dates = pd.bdate_range("2020-01-01", periods=205)
    close = pd.Series(range(1, 206), index=dates, dtype=float)
    targets = price_trend_targets(close, 200)
    assert targets.dropna().iloc[-1] == 1.0
    month_ends = month_end_signal_dates(close.index)
    assert month_ends[0] == pd.Timestamp("2020-01-31")
    assert month_ends[-1] == dates[-1]


def test_confirmation_is_not_requested_inside_five_point_band():
    assert target_action(0.47, 0.50, band=0.05) == "none"
    assert target_action(0.45, 0.50, band=0.05) == "buy"
    assert target_action(0.55, 0.50, band=0.05) == "sell"


def test_integer_lot_and_fee_never_spend_more_than_cash():
    cash, units, trade, reason, _ = execute_target(D("1000000"), D("0"), D("0"), D("3.333"), D("1"), D("0.001"), False)
    assert reason is None
    assert trade[1] % 100 == 0
    assert cash >= 0
    assert cash == D("1000000") - trade[2] - trade[3]


def test_cash_dividend_does_not_create_a_false_price_break():
    bars = pd.DataFrame({"close": [10.0, 9.0]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"]))
    actions = [{"symbol": "sh510300", "type": "cash_dividend", "effective_date": "2020-01-02", "cash": "1"}]
    out = continuous_close(bars, actions, "sh510300")
    assert out.iloc[1] == out.iloc[0]
