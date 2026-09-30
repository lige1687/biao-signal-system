"""V01 inclusive volume, background, and as-of qualification checks."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math
import json
from pathlib import Path

import pytest

from lei_signal.research.volume_information import DEFINITION_REF, prepare_volume_observations, qualify_volume_panel


def _fixture(count=300):
    calendar, d = [], date(2020, 1, 1)
    while len(calendar) < count:
        if d.weekday() < 5:
            calendar.append(d.isoformat())
        d += timedelta(days=1)
    bars = []
    for i, day in enumerate(calendar):
        close = 100 + .1 * i + math.sin(i / 7)
        bars.append({"asset": "ETF", "date": day, "status": "quoted", "open": close,
                     "high": close + 1, "low": close - 1, "close": close,
                     "volume": 250 if i == 260 else 10, "volume_source_known": True,
                     "action_known": True})
    payload = {"data_mode": "synthetic", "calendar": calendar, "bars": bars}
    contract = {"feature": {"kind": "volume_anomaly_information", "definition_ref": DEFINITION_REF,
                            "lookback": 20, "warmup": 252, "missing_policy": "segmented"},
                "universe": {"assets": ["ETF"]},
                "question": {"sampling": "daily", "period": [calendar[0], calendar[-1]]},
                "target": {"kind": "downside_event", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "threshold": 5, "price_measure": "economic_price"}}
    return payload, contract


def _at(prepared, day):
    return next(r for r in prepared["observations"] if r["date"] == day)


def test_inclusive_volume_and_four_level_price_background():
    payload, contract = _fixture()
    prepared = prepare_volume_observations(payload, contract, compute_labels=False)
    event = _at(prepared, payload["calendar"][260])
    # Current-day 250 is part of the 20-day denominator: 250/(19*10+250)*20.
    assert event["features"]["volume_ratio20"] == pytest.approx(250 / ((19 * 10 + 250) / 20))
    assert event["features"]["added"] == 1
    assert event["features"]["r1"] == pytest.approx(100 * (payload["bars"][260]["close"] / payload["bars"][259]["close"] - 1))
    assert event["features"]["r1_group"] in (0, 1, 2, 3)
    assert event["y"] is None and event["label_end"] is None


def test_future_prices_do_not_change_previous_features_and_split_crossing_is_unknown():
    payload, contract = _fixture()
    first = prepare_volume_observations(payload, contract, compute_labels=False)
    changed = deepcopy(payload)
    for bar in changed["bars"][275:]:
        bar.update(open=1000, high=1001, low=999, close=1000, volume=1000)
    later = prepare_volume_observations(changed, contract, compute_labels=False)
    for d in payload["calendar"][252:275]:
        assert _at(first, d)["features"] == _at(later, d)["features"]
    split = deepcopy(payload)
    split["bars"][260]["volume_break"] = True
    got = prepare_volume_observations(split, contract, compute_labels=False)
    assert all(_at(got, split["calendar"][i])["volume_group"] == "unknown" for i in range(260, 279))
    assert _at(got, split["calendar"][279])["volume_group"] == "ordinary"


def test_volume_gap_is_unknown_not_false_and_price_gap_restarts_252():
    payload, contract = _fixture()
    gap = deepcopy(payload)
    gap["bars"][260]["volume_source_known"] = False
    got = prepare_volume_observations(gap, contract, compute_labels=False)
    row = _at(got, payload["calendar"][260])
    assert row["ready_252"] and row["volume_group"] == "unknown" and row["features"]["added"] is None
    price = deepcopy(payload)
    price["bars"][260].update(status="vendor_missing", open=None, high=None, low=None, close=None, volume=None)
    got_price = prepare_volume_observations(price, contract, compute_labels=False)
    assert not _at(got_price, payload["calendar"][261])["ready_252"]


def test_wrong_definition_is_rejected():
    payload, contract = _fixture()
    contract["feature"]["definition_ref"] = "trend.ma_cluster_width@1.0.0"
    with pytest.raises(ValueError, match="exact research card"):
        prepare_volume_observations(payload, contract, compute_labels=False)


def test_saved_source_qualifier_recomputes_price_volume_and_split_marker():
    root = Path(__file__).resolve().parents[2]
    base = root / "docs/experiments/raw/volume-information-2026-09-30/execution"
    payload = json.loads((base / "panel.json").read_text())
    manifest = json.loads((base / "source-manifest.json").read_text())
    contract = {"data": {"sha256": manifest["panel_sha256"],
                         "qualification": {"adapter": "volume_etf_economic/1.0",
                                           "manifest_path": str((base / "source-manifest.json").relative_to(root))}},
                "universe": {"assets": manifest["assets"]},
                "feature": {"kind": "volume_anomaly_information", "definition_ref": DEFINITION_REF,
                            "lookback": 20, "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "downside_event", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "threshold": 5, "price_measure": "economic_price"},
                "question": {"sampling": "daily"}}
    quality = qualify_volume_panel(payload, contract, root)
    assert quality["quality"]["request_satisfied"]
    assert quality["quality"]["economic_ohlc_max_absolute_difference"] < 1e-12
    wrong_volume = deepcopy(payload)
    wrong_volume["bars"][0]["volume"] *= 2
    with pytest.raises(ValueError, match="panel volume differs"):
        qualify_volume_panel(wrong_volume, contract, root)
    wrong_break = deepcopy(payload)
    wrong_break["bars"][0]["volume_break"] = True
    with pytest.raises(ValueError, match="break marker differs"):
        qualify_volume_panel(wrong_break, contract, root)
    wrong_close = deepcopy(payload)
    wrong_close["bars"][0]["close"] *= 1.001
    with pytest.raises(ValueError, match="economic close differs|economic close differs|economic close|economic close differs from nominal"):
        qualify_volume_panel(wrong_close, contract, root)
