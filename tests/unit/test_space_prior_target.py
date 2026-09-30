from datetime import date, timedelta
import math

import pandas as pd

from lei_signal.domain.types import Pivot
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.research.space_prior_target import (
    DEFINITION_REF, prepare_space_observations, upper_target_features,
)


def _p(index, price, *, confirmation=3):
    start = date(2024, 1, 1)
    return Pivot("high", index, start + timedelta(days=index), price,
                 index + confirmation, start + timedelta(days=index + confirmation))


def _value(pivots, day, close=100):
    return upper_target_features(pivots, as_of=day, close=close,
                                 atr20=10, previous_60_high=98)


def test_confirmation_and_missing_target_are_retained():
    p = _p(4, 120)
    assert _value((p,), date(2024, 1, 7))["distance_group"] == "no_target"
    result = _value((p,), date(2024, 1, 8))
    assert result["b1_distance_atr"] == 2
    assert abs(result["prior_60_high_distance_atr"] + 0.2) < 1e-12
    assert _value((p,), date(2024, 1, 8), close=121)["target_price"] is None


def test_latest_in_time_above_price_is_not_nearest_in_price():
    result = _value((_p(4, 101), _p(8, 130)), date(2024, 1, 13))
    assert result["target_price"] == 130
    assert result["b1_distance_atr"] == 3


def test_730_natural_day_boundary():
    old = Pivot("high", 1, date(2021, 12, 31), 110, 4, date(2022, 1, 3))
    as_of = date(2024, 1, 1)
    assert _value((old,), as_of)["target_price"] is None
    edge = Pivot("high", 2, as_of - timedelta(days=730), 110,
                 5, as_of - timedelta(days=727))
    assert _value((edge,), as_of)["target_price"] == 110


def test_prefix_pivots_match_full_history_at_same_observation():
    highs = [10, 11, 12, 20, 13, 12, 11, 10, 11, 12, 30, 13, 12, 11]
    dates = pd.date_range("2024-01-01", periods=len(highs))
    frame = pd.DataFrame({"high": highs, "low": [x - 2 for x in highs]}, index=dates)
    as_of = dates[8].date()
    prefix = confirmed_pivots(frame.iloc[:9], left=3, right=3)
    full = confirmed_pivots(frame, left=3, right=3)
    assert _value(prefix, as_of, close=10)["target_price"] == _value(full, as_of, close=10)["target_price"] == 20


def _daily_case(length=270):
    dates = pd.bdate_range("2024-01-01", periods=length).strftime("%Y-%m-%d").tolist()
    bars = []
    for i, d in enumerate(dates):
        close = 100 + 0.1 * i + 5 * math.sin(i / 15)
        bars.append({"asset": "sh000300", "date": d, "status": "quoted",
                     "open": close, "high": close * 1.01, "low": close * 0.99,
                     "close": close, "provider_price_known": True,
                     "price_series": "provider_index_price", "action_known": False})
    payload = {"calendar": dates, "bars": bars}
    contract = {"feature": {"kind": "space_prior_target", "definition_ref": DEFINITION_REF,
                            "lookback": 60, "warmup": 252, "missing_policy": "segmented"},
                "universe": {"assets": ["sh000300"]},
                "question": {"sampling": "daily", "period": [dates[0], dates[-1]]},
                "target": {"kind": "forward_return", "start_offset": 1,
                           "end_offset": 21, "entry_field": "close", "unit": "percentage_point",
                           "price_measure": "provider_index_price"}}
    return payload, contract


def test_daily_rehearsal_can_skip_future_labels_and_keep_all_observations():
    payload, contract = _daily_case()
    result = prepare_space_observations(payload, contract, compute_labels=False)
    assert result["coverage"]["observations"] == 270
    assert all(o["y"] is None and o["target_label_reason"] == "not_computed"
               for o in result["observations"])
    assert all({"prior_high60_atr", "ret20", "vol20", "distance60_atr", "added"}
               <= o["features"].keys() for o in result["observations"])


def test_252_quotes_do_not_replace_730_day_complete_history():
    payload, contract = _daily_case(540)
    rows = prepare_space_observations(payload, contract, compute_labels=False)["observations"]
    assert rows[300]["ready_252"] and not rows[300]["history_730"]
    assert rows[300]["feature_reason"] == "incomplete_730_day_history"
    assert rows[-1]["history_730"]


def test_first_in_window_pivot_requires_three_left_quotes():
    payload, contract = _daily_case(540)
    rows = prepare_space_observations(payload, contract, compute_labels=False)["observations"]
    assert rows[522]["ready_252"] and not rows[522]["history_730"]
    assert rows[524]["ready_252"] and not rows[524]["history_730"]
    assert rows[525]["history_730"]


def test_gap_invalidates_full_history_window_even_after_252_new_quotes():
    payload, contract = _daily_case(540)
    gap = payload["bars"][100]
    gap.update(status="vendor_missing", open=None, high=None, low=None, close=None)
    rows = prepare_space_observations(payload, contract, compute_labels=False)["observations"]
    assert rows[-1]["ready_252"] and not rows[-1]["history_730"]
    assert rows[-1]["feature_reason"] == "incomplete_730_day_history"


def test_future_close_availability_is_rejected():
    payload, contract = _daily_case()
    payload["bars"][0]["decision_at"] = "2024-01-01T14:00:00+08:00"
    try:
        prepare_space_observations(payload, contract, compute_labels=False)
    except ValueError as exc:
        assert "daily close unavailable" in str(exc)
    else:
        assert False, "pre-close decision must be rejected"
