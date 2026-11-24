"""Causal and missing-price checks for the separate index research width."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research.ma_cluster_information import (
    DEFINITION_REF, prepare_ma_cluster_observations,
)


def _fixture(count=310):
    days, current = [], date(2020, 1, 1)
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    bars = []
    for i, d in enumerate(days):
        close = 100 + i * .11 + math.sin(i / 7)
        bars.append({"asset": "index", "date": d, "status": "quoted", "open": close,
                     "high": close + 1, "low": close - 1, "close": close,
                     "action_known": True})
    payload = {"calendar": days, "bars": bars, "data_mode": "synthetic"}
    contract = {"universe": {"assets": ["index"]},
                "feature": {"kind": "ma_cluster_information", "lookback": 120,
                            "warmup": 252, "missing_policy": "segmented",
                            "definition_ref": DEFINITION_REF},
                "question": {"sampling": "periodic", "frequency": "weekly",
                             "period": [days[0], days[-1]]},
                "target": {"kind": "forward_return", "start_offset": 1,
                           "end_offset": 21, "entry_field": "close", "unit": "percentage_point"}}
    return payload, contract


def test_width_is_six_seeded_lines_and_keeps_raw_ratio():
    payload, contract = _fixture()
    got = prepare_ma_cluster_observations(payload, contract, compute_labels=False)
    row = next(r for r in got["observations"] if r["date"] == "2021-01-01")
    # Independent causal reference: only closes through this observation.
    closes = [b["close"] for b in payload["bars"] if b["date"] <= row["date"]]
    lines = []
    for n in (20, 60, 120):
        lines.append(sum(closes[-n:]) / n)
        ema = sum(closes[:n]) / n
        for value in closes[n:]:
            ema = (2 / (n + 1)) * value + (1 - 2 / (n + 1)) * ema
        lines.append(ema)
    expected = max(lines) / min(lines) - 1
    assert row["features"]["width"] == pytest.approx(expected)
    assert row["features"]["added"] == pytest.approx(100 * expected)
    assert row["y"] is None and row["label_end"] is None


def test_future_changes_do_not_rewrite_prior_features_and_real_gap_restarts_252():
    payload, contract = _fixture()
    first = prepare_ma_cluster_observations(payload, contract, compute_labels=False)
    changed = deepcopy(payload)
    for bar in changed["bars"]:
        if bar["date"] >= payload["calendar"][275]:
            bar["open"] = bar["high"] = bar["low"] = bar["close"] = 10000.
    second = prepare_ma_cluster_observations(changed, contract, compute_labels=False)
    before = lambda result: [(r["date"], r["features"], r["eligible"])
                             for r in result["observations"] if r["date"] < payload["calendar"][275]]
    assert before(first) == before(second)
    gap = deepcopy(payload)
    bar = gap["bars"][260]
    bar.update(status="vendor_missing", open=None, high=None, low=None, close=None)
    reset = prepare_ma_cluster_observations(gap, contract, compute_labels=False)
    after_gap = [r for r in reset["observations"] if r["date"] > payload["calendar"][260]]
    assert after_gap and all(not r["ready_252"] and not r["eligible"] for r in after_gap)


def test_old_card_cannot_be_used_for_index_comparison():
    payload, contract = _fixture()
    contract["feature"]["definition_ref"] = "trend.ma_cluster_width@1.0.0"
    with pytest.raises(ValueError, match="research definition"):
        prepare_ma_cluster_observations(payload, contract, compute_labels=False)
