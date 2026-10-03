"""Independent arithmetic and timing boundaries for signed-volume direction."""
from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import volume_direction_information as direction
from lei_signal.research import workflow_inputs as shared


def fixture(n=530):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = []
    for j, asset in enumerate(("synthetic-A", "synthetic-B")):
        for i, day in enumerate(days):
            price = 100 + j + 0.07*i + 3*math.sin(i/6+j/2) + 1.3*math.sin(i/13)
            bars.append(dict(asset=asset, date=day, status="quoted", open=price,
                high=price+1, low=price-1, close=price, action_known=True,
                volume=100+i%7, volume_source_known=True, volume_break=False))
    contract = {
        "feature": {"kind": direction.KIND, "definition_ref": direction.REFS["direction_excess20"],
            "candidate": "direction_excess20", "comparison_mode": "main", "lookback": 20,
            "warmup": 252, "missing_policy": "segmented", "anchor_asset": "synthetic-A"},
        "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
            "entry_field": "close", "path_field": "close", "unit": "percentage_point",
            "price_measure": "economic_price"},
        "question": {"sampling": "daily", "period": [days[0], days[-1]]},
        "universe": {"assets": ["synthetic-A", "synthetic-B"]},
        "split": {"folds": direction.FOLDS}, "data": {"sha256": "synthetic"},
        "permissions": {"real_labels": False, "effect_authorized": False}}
    return {"data_mode": "synthetic", "calendar": days, "bars": bars}, contract


def own(rows, n):
    return rows[n:]


def test_manual_weighting_identity_scale_and_equal_volume():
    closes = [100.0]
    signs = [1, -1, 0, 1] * 5
    for s in signs:
        closes.append(closes[-1] + s)
    volumes = [2.0 if s > 0 else 1.0 for s in signs]
    result = direction.candidate_values(closes, volumes)
    manual_count = sum(signs)/20
    manual_weighted = sum(s*v for s, v in zip(signs, volumes))/sum(volumes)
    assert result["direction20"] == pytest.approx(manual_count)
    assert result["direction_excess20"] == pytest.approx(manual_weighted-manual_count)
    assert direction.candidate_values(closes, [v*1000 for v in volumes])["direction_excess20"] == pytest.approx(result["direction_excess20"])
    assert direction.candidate_values(closes, [3.0]*20)["direction_excess20"] == pytest.approx(0)
    for flat in ([100.0]*21, [100.0+i for i in range(21)]):
        assert direction.candidate_values(flat, volumes)["direction_excess20"] == pytest.approx(0)


def test_invalid_window_rejected_without_epsilon_or_coercion():
    closes = [float(100+i) for i in range(21)]
    volumes = [2.0]*20
    for bad in (float("nan"), float("inf"), True, 0, -1):
        v = volumes.copy(); v[-1] = bad
        assert all(x is None for x in direction.candidate_values(closes, v).values())
        c = closes.copy(); c[-1] = bad
        assert all(x is None for x in direction.candidate_values(c, volumes).values())
    assert all(x is None for x in direction.candidate_values(closes[:-1], volumes).values())
    assert all(x is None for x in direction.candidate_values(closes, volumes[:-1]).values())


def test_prefix_no_future_label_and_joint_price_warmup(monkeypatch):
    payload, contract = fixture()
    monkeypatch.setattr(shared, "_label", lambda *a, **k: pytest.fail("future label read"))
    rows = direction.prepare_volume_direction_observations(payload, contract)["observations"]
    sample = own(rows, 530)
    assert not sample[250]["ready_252"] and sample[251]["ready_252"]
    assert sample[251]["features"]["direction20"] is not None
    assert all(not r["eligible"] for r in rows[:530])
    short = deepcopy(payload); short["bars"] = [r for r in short["bars"] if r["date"] <= payload["calendar"][300]]
    assert direction.prepare_volume_direction_observations(short, contract)["observations"] == rows[:301]+rows[530:831]
    gap = deepcopy(payload)
    bar = next(r for r in gap["bars"] if r["asset"] == "synthetic-A" and r["date"] == payload["calendar"][275])
    bar.update(status="vendor_missing", open=None, high=None, low=None, close=None, volume=None)
    changed = own(direction.prepare_volume_direction_observations(gap, contract)["observations"], 530)
    assert not changed[526]["ready_252"] and changed[527]["ready_252"]


@pytest.mark.parametrize("change", ["break", "missing", "invalid", "unknown"])
def test_volume_reset_preserves_price_clock_and_pairs(change):
    payload, contract = fixture()
    rows = own(direction.prepare_volume_direction_observations(payload, contract)["observations"], 530)
    altered = deepcopy(payload)
    bar = next(r for r in altered["bars"] if r["asset"] == "synthetic-B" and r["date"] == payload["calendar"][300])
    if change == "break": bar["volume_break"] = True
    if change == "missing": bar["volume"] = None
    if change == "invalid": bar["volume"] = float("nan")
    if change == "unknown": bar["volume_source_known"] = False
    changed = own(direction.prepare_volume_direction_observations(altered, contract)["observations"], 530)
    assert changed[300]["continuous_real_ohlc"] == rows[300]["continuous_real_ohlc"]
    assert changed[300]["feature_reason"] == "volume_window_incomplete"
    ready_day = 319 if change == "break" else 320
    assert changed[ready_day-1]["continuous_volume_pairs"] == 19
    assert not changed[ready_day-1]["eligible"] and changed[ready_day]["eligible"]
    # Same price features recover; the new pair window starts after the reset.
    assert changed[ready_day]["features"]["return20"] == rows[ready_day]["features"]["return20"]
    first_pair_day = ready_day-19
    expected = direction.candidate_values(
        [r["close"] for r in altered["bars"] if r["asset"] == "synthetic-B"][first_pair_day-1:ready_day+1],
        [r["volume"] for r in altered["bars"] if r["asset"] == "synthetic-B"][first_pair_day:ready_day+1])
    assert changed[ready_day]["features"]["direction_excess20"] == pytest.approx(expected["direction_excess20"])


def test_label_maturity_authorization_and_exact_target():
    payload, contract = fixture()
    payload["decision_at"] = payload["calendar"][300] + "T16:00:00"
    rows = own(direction.prepare_volume_direction_observations(payload, contract, compute_labels=True)["observations"], 301)
    assert rows[278]["label_end"] == payload["calendar"][299]
    assert rows[280]["y"] is None
    for key, value in (("path_field", "low"), ("end_offset", 20), ("price_measure", "provider_index_price")):
        wrong = deepcopy(contract); wrong["target"][key] = value
        with pytest.raises(ValueError):
            direction.prepare_volume_direction_observations(payload, wrong)
    payload["data_mode"] = "historical_reconstruction"
    with pytest.raises(ValueError, match="authorization"):
        direction.prepare_volume_direction_observations(payload, contract, compute_labels=True)


def test_qualification_counts_calendar_maturity_without_outcomes(monkeypatch):
    payload, contract = fixture()
    contract["split"]["folds"] = [{"train_end": payload["calendar"][350],
        "eval_start": payload["calendar"][375], "eval_end": payload["calendar"][420]}]
    called = []
    def source_only(*args):
        called.append(True)
        return {"quality": {"request_satisfied": True}, "warnings": []}
    monkeypatch.setattr(direction, "qualify_top_panel", source_only)
    monkeypatch.setattr(shared, "_label", lambda *a, **k: pytest.fail("future label read"))
    result = direction.build_qualification(payload, contract, None)
    fold = result["scientific_support"]["folds"][0]
    assert called and result["outcome_values_used_for_design"] is False
    assert fold["train"] == 100  # t=251..350, and every label matures before day375.
    assert fold["evaluation"] == 25  # 375..399 can mature by day420.
    assert result["scientific_support"]["model_feature_count"] == 20
