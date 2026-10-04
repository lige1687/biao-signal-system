"""Synthetic causal identity checks for color history; no market outcomes."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from lei_signal.research import color_history_information as color


def _fixture(n=580):
    days, d = [], date(2020, 1, 1)
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    bars = []
    for i, day in enumerate(days):
        close = 100 + i * .04 + 5 * __import__("math").sin(i / 7)
        bars.append({"asset": "A", "date": day, "status": "quoted",
                     "action_known": True, "open": close, "high": close + 1,
                     "low": close - 1, "close": close, "volume": 100.})
    return {"calendar": days, "bars": bars}


def test_prefix_invariance_and_every_calendar_day():
    payload = _fixture()
    full = color.history_rows(payload)
    cutoff = payload["calendar"][420]
    short = color.history_rows({**payload, "calendar": payload["calendar"][:421],
                                "bars": payload["bars"][:421]})
    assert full[:421] == short
    assert len(full) == len(payload["calendar"])
    assert all(row["color20"] is None for row in full[:251])
    assert full[251]["ready_252"]
    assert any(row["transition20"] is not None for row in full[252:])


def test_missing_quote_resets_warmup_and_histories():
    payload = _fixture()
    payload["bars"][300]["status"] = "vendor_missing"
    rows = color.history_rows(payload)
    assert rows[300]["feature_reason"] == "missing_or_invalid_quote"
    assert all(not row["ready_252"] for row in rows[301:552])
    assert rows[552]["ready_252"]
    assert rows[552]["prior_color20"] is None
    assert rows[552]["switches20"] is None


def test_gray_paths_entry_origin_age_and_equality(monkeypatch):
    # Stub only the already-qualified daily indicator values to isolate history
    # semantics, including an exact equality at a gray boundary.
    closes = [100.] * 251 + [90., 100., 100., 110., 100., 90.]
    segment = [{"asset": "A", "date": f"d{i:04d}", "close": close}
               for i, close in enumerate(closes)]
    sequence = ["black", "gray", "gray", "green", "gray", "black"]
    def fake_items(rows):
        base = [None] * 251
        for state in sequence:
            base.append({"features": {"ret20": 0., "ret60": 0., "vol20": 1.},
                         "color20": state, "color60": state})
        return base
    def fake_frame(rows):
        n = len(rows)
        return pd.DataFrame({"ema20": [100.] * n, "ema60": [100.] * n,
                             "sma20": [100.] * n, "sma60": [100.] * n,
                             "close_lag20": [100.] * n,
                             "close_lag60": [100.] * n})
    monkeypatch.setattr(color, "_segment_features", fake_items)
    monkeypatch.setattr(color, "compute_features", fake_frame)
    rows = color._known_segment("A", segment)[251:]
    assert [r["color_run_age"] for r in rows] == [1, 1, 2, 1, 1, 1]
    assert rows[1]["state20"] == "ema_equal__deduction_equal"
    assert rows[1]["gray_origin"] == rows[2]["gray_origin"] == "black"
    assert rows[2]["gray_age"] == 2
    assert rows[3]["gray_resolution_path"] == "black-gray-green"
    assert rows[4]["gray_origin"] == "green"
    assert rows[5]["gray_resolution_path"] == "green-gray-black"
    assert rows[1]["gray_resolution_path"] is None
    assert rows[1]["group_run_id"] == rows[5]["group_run_id"]


def test_unknown_gray_origin_stays_unknown_until_exit(monkeypatch):
    segment = [{"asset": "A", "date": f"d{i:04d}", "close": 100.}
               for i in range(254)]
    states = ["gray", "gray", "green"]
    monkeypatch.setattr(color, "_segment_features", lambda rows: [None] * 251 + [
        {"features": {"ret20": 0., "ret60": 0., "vol20": 1.},
         "color20": s, "color60": s} for s in states])
    monkeypatch.setattr(color, "compute_features", lambda rows: pd.DataFrame({
        key: [100.] * len(rows) for key in ("ema20", "ema60", "sma20", "sma60",
                                          "close_lag20", "close_lag60")}))
    rows = color._known_segment("A", segment)[251:]
    assert rows[0]["gray_origin"] is None and rows[1]["gray_age"] == 2
    assert rows[2]["gray_resolution_path"] == "unknown-gray-green"
