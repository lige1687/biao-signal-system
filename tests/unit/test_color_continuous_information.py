"""Small exact sequence checks for outcome-free continuous color features."""
from __future__ import annotations

from copy import deepcopy

import pytest

from lei_signal.research import color_continuous_information as continuous


def _row(i, color, *, ready=True, above=True, asset="A"):
    return {"id": f"{asset}|d{i:03d}", "asset": asset, "date": f"d{i:03d}",
            "ready_252": ready, "color20": color if ready else None,
            "color60": color if ready else None,
            "distance_to_ema20": 2. if above else 0.,
            "ret20": 1., "ret60": 2., "vol20": 3., "bull_group": True}


def test_exact_20_colors_19_pairs_and_strict_ema(monkeypatch):
    # Ten green then ten gray: one switch among the 19 adjacent pairs.
    source = [_row(i, "green" if i < 10 else "gray", above=i < 8)
              for i in range(20)]
    monkeypatch.setattr(continuous, "history_rows", lambda payload: source)
    rows = continuous.continuous_rows({})
    assert all(r["green_share20"] is None for r in rows[:19])
    assert rows[19]["green_share20"] == .5
    assert rows[19]["switch_frequency20"] == pytest.approx(1 / 19)
    assert rows[19]["ema_above_share20"] == .4  # equality is false
    assert rows[19]["color20_gray"] == 1
    assert rows[19]["distance_to_ema20"] == 0.


def test_gap_breaks_window_and_prefix_does_not_change(monkeypatch):
    source = [_row(i, "green" if i % 2 else "black") for i in range(45)]
    source[21] = _row(21, None, ready=False)
    monkeypatch.setattr(continuous, "history_rows", lambda payload: source)
    full = continuous.continuous_rows({})
    monkeypatch.setattr(continuous, "history_rows", lambda payload: source[:36])
    prefix = continuous.continuous_rows({})
    assert full[:36] == prefix
    assert full[20]["switch_frequency20"] == 1.
    assert full[21]["green_share20"] is None
    assert all(r["green_share20"] is None for r in full[22:41])
    assert full[41]["green_share20"] is not None


def test_same_day_average_ties_missing_and_constant():
    rows = [_row(1, "green", asset=a) for a in "ABCD"]
    for row, value in zip(rows, (1., 2., 2., 4.)):
        row["x"] = value
    out = continuous.same_day_ranks(rows, "x")
    assert [r["x_rank"] for r in out] == [0., .5, .5, 1.]
    assert "x_rank" not in rows[0]  # pure copies
    constant = [{**r, "x": 5.} for r in rows]
    assert [r["x_rank"] for r in continuous.same_day_ranks(constant, "x")] == [.5] * 4
    missing = deepcopy(rows)
    missing[0]["x"] = None
    missing[1]["ready_252"] = False
    ranked = continuous.same_day_ranks(missing, "x")
    assert [r["x_rank"] for r in ranked] == [None, None, 0., 1.]
    one = continuous.same_day_ranks(rows[:1], "x")
    assert one[0]["x_rank"] is None
    with pytest.raises(ValueError):
        continuous.same_day_ranks(rows, "color20")


def test_registered_ema_slope_control_at_first_ready_and_equality():
    bars = [{"asset": "A", "date": f"d{i:03d}", "status": "quoted",
             "action_known": True, "open": 100., "high": 101., "low": 99.,
             "close": 100., "volume": 100.} for i in range(275)]
    payload = {"assets": ["A"], "calendar": [b["date"] for b in bars], "bars": bars}
    rows = continuous.continuous_rows(payload)
    assert rows[251]["ema20_up_share20"] == 0.
    assert rows[251]["ema_above_share20"] is None  # needs 20 qualified rows
    assert rows[270]["ema_above_share20"] == 0.  # exact equality is not above
    assert rows[270]["ema20_up_share20"] == 0.
