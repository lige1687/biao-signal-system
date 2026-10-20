"""Only synthetic prices and dates; no market files or research results."""

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.month_end_rebalancing import (
    build_events,
    calendar_drift,
    circular_block_mean_interval,
    expanding_predictions,
    total_return,
)


def panel_fixture() -> pd.DataFrame:
    dates = pd.bdate_range("2024-12-02", "2026-10-05")
    t = np.arange(len(dates), dtype=float)
    panel = pd.DataFrame(index=dates)
    panel["SPY_close"] = 100 * np.exp(0.0005 * t + 0.01 * np.sin(t / 20))
    panel["IEF_close"] = 100 * np.exp(0.0001 * t + 0.005 * np.cos(t / 14))
    panel["SPY_open"] = panel.SPY_close * 1.001
    panel["IEF_open"] = panel.IEF_close * 0.999
    panel["SPY_dividend"] = 0.0
    panel["IEF_dividend"] = 0.0
    return panel


def test_total_return_ex_dividend_and_reject_bad_inputs():
    days = pd.bdate_range("2026-01-01", periods=3)
    close = pd.Series([100.0, 98.0, 99.0], index=days)
    dividend = pd.Series([0.0, 2.0, 0.0], index=days)
    result = total_return(close, dividend)
    assert result.tolist() == pytest.approx([1.0, 1.0, 99 / 98])
    with pytest.raises(ValueError):
        total_return(close.mask(close.index == days[1]), dividend)
    with pytest.raises(ValueError):
        total_return(close, dividend.mask(dividend.index == days[1]))
    with pytest.raises(ValueError):
        total_return(close.mask(close.index == days[1], 0), dividend)


def test_drift_numeric_scale_and_direction():
    assert calendar_drift(1.1, 1.0) == pytest.approx(0.02264150943396226)
    assert calendar_drift(1.1, 1.0) == pytest.approx(calendar_drift(11, 10))
    for gs, gb in [(1.1, 1.0), (0.9, 1.0), (1.1, 1.1)]:
        drift = calendar_drift(gs, gb)
        relative = np.log(gs / gb)
        assert np.sign(drift) == np.sign(relative)


def test_month_events_time_dividends_placebo_and_future_stability():
    panel = panel_fixture()
    events = build_events(panel, "2025-03-01", "2026-09-30")
    assert events.month.iloc[0] == "2025-03"
    assert events.month.iloc[-1] == "2026-09"
    assert len(events) == 19
    assert (events.label_end.dt.to_period("M").astype(str) == events.month).all()
    assert ((events.label_end - events.signal_date).dt.days > 0).all()
    assert (events.placebo_signal_date < events.signal_date).all()
    assert (events.placebo_label_end < events.signal_date).all()

    # An ex-date dividend is received over close-to-close holding, but not
    # when entering at that same day's opening.
    first = events.iloc[0]
    entry = first.label_start
    panel.loc[entry, "SPY_dividend"] = 2.0
    changed = build_events(panel, "2025-03-01", "2026-09-30")
    assert changed.y.iloc[0] > first.y
    assert changed.y_open.iloc[0] == pytest.approx(first.y_open)

    # Price changes after an event cannot change its signal or earlier fitted
    # predictions. (This fixture has fewer than 60 training months.)
    future = panel.copy()
    future.loc[future.index >= "2026-09-01", "SPY_close"] *= 2
    before = build_events(panel, "2025-03-01", "2026-09-30")
    after = build_events(future, "2025-03-01", "2026-09-30")
    pd.testing.assert_frame_equal(before.iloc[:-1].reset_index(drop=True),
                                  after.iloc[:-1].reset_index(drop=True))


def test_truncated_month_and_missing_one_asset_are_not_silent():
    panel = panel_fixture()
    truncated = panel.loc[:"2026-09-30"]
    events = build_events(truncated, "2026-09-01", "2026-09-30")
    assert events.empty
    bad = panel.copy()
    bad.loc["2025-03-14", "IEF_close"] = np.nan
    with pytest.raises(ValueError, match="missing"):
        build_events(bad, "2025-03-01", "2025-03-31")


def test_expanding_uses_only_matured_labels_and_no_future_leakage():
    dates = pd.date_range("2015-01-10", periods=75, freq="MS")
    signals = dates + pd.Timedelta(days=8)
    events = pd.DataFrame({
        "signal_date": signals,
        "label_end": signals + pd.Timedelta(days=20),
        "stock_log": np.arange(75) / 100,
        "relative_log": np.sin(np.arange(75) / 5) / 10,
        "drift": np.sin(np.arange(75) / 5) / 50,
        "y": np.arange(75) / 200,
    })
    result = expanding_predictions(events, min_train=60)
    assert result.signal_date.iloc[0] == signals[60]
    assert result.train_n.iloc[0] == 60
    assert set(["pred_mean", "pred_stock_log", "pred_relative_log", "pred_drift"]).issubset(result)
    changed = events.copy()
    changed.loc[changed.index >= 70, "y"] = -999
    old = result.loc[result.signal_date <= signals[70]].reset_index(drop=True)
    new = expanding_predictions(changed, min_train=60)
    new = new.loc[new.signal_date <= signals[70]].reset_index(drop=True)
    pd.testing.assert_frame_equal(old.drop(columns="y"), new.drop(columns="y"))
    # A label maturing after the current signal must be excluded.
    overlapping = events.copy()
    overlapping.loc[0, "label_end"] = signals[60] + pd.Timedelta(days=1)
    assert expanding_predictions(overlapping, min_train=60).signal_date.iloc[0] == signals[61]


def test_circular_interval_is_reproducible_and_descriptive():
    x = np.tile([0.0, 1.0, -0.5], 20)
    a = circular_block_mean_interval(x, reps=100)
    assert a == circular_block_mean_interval(x, reps=100)
    assert a[0] <= x.mean() <= a[1]
