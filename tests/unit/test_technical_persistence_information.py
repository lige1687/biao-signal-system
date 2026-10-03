"""Exact synthetic checks; no historical outcomes or fitting."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import json
import math
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.features.indicators import compute_features
from lei_signal.research import workflow, workflow_inputs
from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research import technical_persistence_information as technical

ROOT = Path(__file__).resolve().parents[2]


def contract(kind, target_kind=None):
    path = ROOT / "docs/experiments/raw/technical-daily-risk-2026-10-03/slope/original-draft.json"
    c = json.loads(path.read_text(encoding="utf-8"))
    target_kind = target_kind or ("forward_return" if kind == technical.PERSISTENCE else "mae")
    c["feature"].update(kind=kind, lookback=20, definition_ref=technical.REFS[kind])
    c["question"]["factor_refs"] = [technical.REFS[kind]]
    c["target"].update(kind=target_kind, path_field="close")
    c["question"]["target"].update(kind=target_kind, price_basis=(
        "close_to_close" if target_kind == "forward_return" else "close_to_close_path"))
    c["evaluator"].update(
        baseline_features=list(technical.BASELINE_PERSISTENCE if kind == technical.PERSISTENCE
                               else technical.BASELINE_TRANSITION),
        added_features=[technical.ADDED[kind]], minimum_training_rows=22,
    )
    c["research_design"]["sample_fit"]["model_feature_count"] = len(c["evaluator"]["baseline_features"]) + 1
    return c


def panel(count=320, *, jump=False):
    days = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    bars = []
    for i, day in enumerate(days):
        close = 100 + .2 * i + (0 if jump else 4 * math.sin(i / 7))
        if jump and i == 254:
            close -= 20
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted", "open": close,
                     "high": close + 1, "low": close - 1, "close": close,
                     "volume": 10000, "action_known": True})
    return {"data_mode": "synthetic", "calendar": days, "bars": bars}


def local_contract(kind, payload, target_kind=None):
    c = contract(kind, target_kind)
    c["universe"]["assets"] = ["synthetic-A"]
    c["question"]["universe"] = ["synthetic-A"]
    c["question"]["period"] = [payload["calendar"][0], payload["calendar"][-1]]
    return c


@pytest.mark.parametrize("kind", [technical.PERSISTENCE, technical.TRANSITION])
def test_strict_formula_gap_prefix_and_unfinished_close(kind):
    payload = panel(jump=True)
    c = local_contract(kind, payload)
    rows = technical.prepare_observations(payload, c)["observations"]
    assert len(rows) == len(payload["calendar"])
    assert not rows[250]["ready_252"] and rows[251]["ready_252"]
    frame = compute_features(pd.DataFrame(payload["bars"]))
    for i in (251, 255, 280):
        ema = frame["ema20"].tolist()
        expected = sum(ema[j] > ema[j - 1] for j in range(i - 19, i + 1)) / 20
        if kind == technical.PERSISTENCE:
            assert rows[i]["features"]["ema20_up_share20"] == expected
            assert rows[i]["features"]["ema20_up"] == int(ema[i] > ema[i - 1])
        assert rows[i]["y"] is None
    changed = deepcopy(payload)
    changed["bars"][290]["close"] += .5
    assert rows[:290] == technical.prepare_observations(changed, c)["observations"][:290]
    missing = deepcopy(payload)
    missing["bars"][275] = {"asset": "synthetic-A", "date": payload["calendar"][275],
                            "status": "vendor_missing", "action_known": False}
    gap = technical.prepare_observations(missing, c)["observations"]
    assert not gap[275]["ready_252"] and not gap[-1]["ready_252"]
    cutoff = deepcopy(payload)
    cutoff["decision_at"] = payload["calendar"][270] + "T14:59:00+08:00"
    assert technical.prepare_observations(cutoff, c)["observations"][-1]["date"] == payload["calendar"][269]


def test_equality_and_exact_adjacent_event():
    constant = panel(jump=True)
    for row in constant["bars"]:
        row.update(open=100., high=100., low=100., close=100.)
    c = local_contract(technical.PERSISTENCE, constant)
    rows = technical.prepare_observations(constant, c)["observations"]
    assert rows[251]["features"]["ema20_up_share20"] == 0
    assert rows[251]["features"]["ema20_up"] == 0
    assert rows[251]["color20"] == "gray"
    payload = panel(jump=True)
    c = local_contract(technical.TRANSITION, payload)
    rows = technical.prepare_observations(payload, c)["observations"]
    assert rows[254]["color20"] == "black"
    assert rows[255]["color20"] == "green" and rows[255]["bull_group"]
    assert rows[255]["features"]["adjacent_black20"] == 1 and rows[255]["eligible"]
    assert not rows[254]["eligible"]
    assert rows[256]["features"]["adjacent_black20"] == 0
    assert rows[256]["eligible"]


@pytest.mark.parametrize("kind,target", [(technical.PERSISTENCE, "forward_return"),
                                           (technical.PERSISTENCE, "mae"),
                                           (technical.TRANSITION, "mae")])
def test_close_path_labels_and_registered_synthetic_rehearsal(kind, target):
    c = contract(kind, target)
    validate_workflow_contract(c)
    rehearsal = workflow.run_rehearsal(c)
    assert rehearsal["fits"] == 2 and rehearsal["performance"]
    payload = panel(jump=True)
    local = local_contract(kind, payload, target)
    rows = workflow_inputs.prepare_observations(payload, local)["observations"]
    i = 255
    closes = [bar["close"] for bar in payload["bars"]]
    expected = (100 * (closes[i + 21] / closes[i + 1] - 1) if target == "forward_return"
                else max(0, 100 * (1 - min(closes[i + 1:i + 22]) / closes[i + 1])))
    assert rows[i]["y"] == pytest.approx(expected)
    assert rows[i]["label_end"] == payload["calendar"][i + 21]
    assert rows[-1]["target_label_reason"] == "immature_label"
    changed = deepcopy(payload)
    changed["bars"][i + 3]["low"] = .01
    assert workflow_inputs.prepare_observations(changed, local)["observations"][i]["y"] == pytest.approx(expected)


def test_wrong_definition_target_and_real_permission_rejected():
    p = panel()
    for kind in (technical.PERSISTENCE, technical.TRANSITION):
        c = local_contract(kind, p)
        for change in (lambda x: x["target"].update(end_offset=20),
                       lambda x: x["feature"].update(definition_ref="wrong")):
            bad = deepcopy(c)
            change(bad)
            with pytest.raises(ValueError):
                technical.prepare_observations(p, bad)
        real = deepcopy(p)
        real.update(data_mode="historical_reconstruction", price_series="economic_price")
        c["permissions"]["real_labels"] = False
        with pytest.raises(ValueError, match="authorization"):
            technical.prepare_observations(real, c, compute_labels=True)


def test_outside_condition_never_reads_future_label(monkeypatch):
    payload = panel(jump=True)
    c = local_contract(technical.TRANSITION, payload)
    seen = []
    original = technical.shared._label

    def traced(rows, index, target):
        seen.append(index)
        return original(rows, index, target)

    monkeypatch.setattr(technical.shared, "_label", traced)
    result = technical.prepare_observations(payload, c, compute_labels=True)["observations"]
    assert seen == [i for i, row in enumerate(result) if row["feature_reason"] is None]
    assert all(row["y"] is None and row["label_end"] is None
               for row in result if row["feature_reason"] is not None)


def test_target_maturity_never_changes_past_condition():
    payload = panel(jump=True)
    for kind in (technical.PERSISTENCE, technical.TRANSITION):
        c = local_contract(kind, payload)
        full = technical.prepare_observations(payload, c, compute_labels=True)["observations"]
        short = deepcopy(payload)
        short["bars"] = short["bars"][:271]
        prefix = technical.prepare_observations(short, c, compute_labels=True)["observations"]
        assert [(r["features"], r["tested_condition"]) for r in prefix] == [
            (r["features"], r["tested_condition"]) for r in full[:271]]
