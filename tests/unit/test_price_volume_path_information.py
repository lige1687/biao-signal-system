"""Independent fixed-formula and timing checks for price/volume path research."""

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import price_volume_path_information as path


def test_daily_range_and_location_use_prior_economic_close():
    row = {"open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0, "volume": 10.0}
    actual = path.day_values(row, 100.0)
    assert actual["range"] == pytest.approx(0.2)
    assert actual["close_location"] == pytest.approx(0.5)
    assert actual["wick_balance"] == pytest.approx((5.0 - 10.0) / 20.0)
    scaled = {k: v * 7 for k, v in row.items() if k != "volume"} | {"volume": 10.0}
    scaled_actual = path.day_values(scaled, 700.0)
    for field in ("range", "close_location", "wick_balance"):
        assert scaled_actual[field] == pytest.approx(actual[field])


def test_volume_weighting_is_zero_for_uniform_volume_and_scale_invariant():
    days = [{"range": 0.02 + i / 1000, "close_location": (-1) ** i / 2,
             "wick_balance": (-1) ** (i + 1) / 3, "volume": float(i + 1)} for i in range(20)]
    values = path.candidate_values(days, 20)
    assert values["range_mean"] == pytest.approx(sum(d["range"] for d in days) / 20)
    expected = sum(d["range"] * d["volume"] for d in days) / sum(d["volume"] for d in days) - values["range_mean"]
    assert values["volume_range_excess"] == pytest.approx(expected)
    scaled = deepcopy(days)
    for d in scaled:
        d["volume"] *= 1000
    assert path.candidate_values(scaled, 20)["volume_range_excess"] == pytest.approx(expected)
    for d in scaled:
        d["volume"] = 1.0
    assert path.candidate_values(scaled, 20)["volume_range_excess"] == pytest.approx(0)


def test_missing_quote_and_future_bar_do_not_fill_current_features():
    days = [(date(2022, 1, 3) + timedelta(days=i)).isoformat() for i in range(310)]
    bars = []
    for asset in ("synthetic-A", "synthetic-B"):
        for i, day in enumerate(days):
            close = 100 + i / 10 + math.sin(i / 7)
            bars.append({"asset": asset, "date": day, "status": "quoted", "open": close - 0.2,
                         "high": close + 0.5, "low": close - 0.7, "close": close,
                         "volume": float(100 + i % 11), "volume_break": False})
    payload = {"data_mode": "synthetic", "calendar": days, "bars": bars}
    contract = {"feature": {"kind": path.KIND, "candidate": "range_mean20",
               "definition_ref": path.REFS["range_mean20"], "lookback": 20,
               "warmup": 252, "missing_policy": "segmented", "anchor_asset": "synthetic-A"},
               "universe": {"assets": ["synthetic-A", "synthetic-B"]},
               "question": {"period": [days[0], days[-1]]},
               "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                          "entry_field": "close", "path_field": "close",
                          "unit": "percentage_point", "price_measure": "economic_price"}}
    original = path.prepare_observations(payload, contract)["observations"]
    truncated = {**payload, "bars": [b for b in bars if b["date"] <= days[280]]}
    prefix = path.prepare_observations(truncated, contract)["observations"]
    assert {r["id"]: r["features"] for r in prefix if r["date"] <= days[280]} == {
        r["id"]: r["features"] for r in original if r["date"] <= days[280]}
    gap = deepcopy(payload)
    gap["bars"] = [b for b in gap["bars"] if not (b["asset"] == "synthetic-B" and b["date"] == days[275])]
    changed = path.prepare_observations(gap, contract)["observations"]
    by_id = {r["id"]: r for r in changed}
    assert not by_id[f"synthetic-B|{days[275]}"]["eligible"]
    assert not by_id[f"synthetic-B|{days[309]}"]["eligible"]
