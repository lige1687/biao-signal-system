"""Causal weekly aggregation, missingness and the fixed workflow wiring."""
from copy import deepcopy
from datetime import date, timedelta
import json
import math
from pathlib import Path

import pytest

from lei_signal.research import workflow, workflow_inputs
from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research import weekly_color_information as weekly

ROOT = Path(__file__).resolve().parents[2]


def contract(payload, target="forward_return"):
    path = ROOT / "docs/experiments/raw/technical-daily-risk-2026-10-03/slope/original-draft.json"
    c = json.loads(path.read_text())
    c["feature"].update(kind=weekly.KIND, lookback=20, definition_ref=weekly.DEFINITION_REF,
                        week_warmup=120, week_policy="previous_iso_week_only")
    c["question"]["factor_refs"] = [weekly.DEFINITION_REF]
    c["target"].update(kind=target, path_field="close")
    c["question"]["target"].update(kind=target,
        price_basis="close_to_close" if target == "forward_return" else "close_to_close_path")
    c["evaluator"].update(baseline_features=list(weekly.BASELINE_FEATURES),
                          added_features=list(weekly.ADDED_FEATURES), minimum_training_rows=32)
    c["research_design"]["sample_fit"]["model_feature_count"] = 15
    c["universe"]["assets"] = ["synthetic-A"]
    c["question"]["universe"] = ["synthetic-A"]
    c["question"]["period"] = [payload["calendar"][0], payload["calendar"][-1]]
    c["data"]["mode"] = "synthetic"
    return c


def panel(count=900):
    days, d = [], date(2020, 1, 6)  # Monday, complete first source week
    while len(days) < count:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    bars = []
    for i, day in enumerate(days):
        close = 120 + .045 * i + 17 * math.sin(i / 24) + 4 * math.sin(i / 5)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": close, "high": close + 1, "low": close - 1,
                     "close": close, "volume": 100, "action_known": True})
    return {"data_mode": "synthetic", "calendar": days, "bars": bars}


def test_previous_completed_week_and_prefix_are_strict():
    p = panel()
    c = contract(p)
    rows = weekly.prepare_observations(p, c)["observations"]
    # A Friday close cannot be consumed until next week's first observed day.
    friday = next(i for i in range(720, 800) if date.fromisoformat(rows[i]["date"]).weekday() == 4)
    assert rows[friday]["last_completed_week_date"] == p["calendar"][friday - 5]
    assert rows[friday + 1]["last_completed_week_date"] == p["calendar"][friday]
    changed = deepcopy(p)
    changed["bars"][friday]["close"] += 40
    later = weekly.prepare_observations(changed, c)["observations"]
    assert rows[:friday] == later[:friday]
    assert rows[friday]["week20_state"] == later[friday]["week20_state"]
    assert rows[friday]["features"]["week_ret20"] == later[friday]["features"]["week_ret20"]
    assert rows[friday + 1]["features"]["week_ret20"] != later[friday + 1]["features"]["week_ret20"]
    prefix = deepcopy(p)
    prefix["bars"] = prefix["bars"][:friday + 1]
    assert [(r["features"], r["week20_state"]) for r in rows[:friday + 1]] == [
        (r["features"], r["week20_state"]) for r in weekly.prepare_observations(prefix, c)["observations"]]


def test_seeded_ema_and_missing_week_reset_unknown():
    p = panel()
    c = contract(p)
    rows = weekly.prepare_observations(p, c)["observations"]
    # First eligible Monday consumes exactly 120 complete Friday closes.
    monday = next(i for i, row in enumerate(rows) if row["week_continuous"] == 120 and row["eligible"])
    closes = [bar["close"] for bar in p["bars"][:monday] if date.fromisoformat(bar["date"]).weekday() == 4]
    assert len(closes) == 120
    ema = sum(closes[:20]) / 20
    for close in closes[20:]:
        ema = close * 2 / 21 + ema * 19 / 21
    expected = weekly._color(closes[-1], ema, closes[-21])
    assert rows[monday]["week20_state"] == expected
    assert rows[monday]["features"]["week_ret20"] == pytest.approx(100 * (closes[-1] / closes[-21] - 1))
    missing = deepcopy(p)
    missing["bars"][monday + 1] = {"asset": "synthetic-A", "date": p["calendar"][monday + 1],
                                    "status": "action_unknown", "action_known": False}
    gap = weekly.prepare_observations(missing, c)["observations"]
    next_monday = monday + 5
    assert gap[next_monday]["week20_state"] is None
    assert gap[next_monday]["features"]["week20_green"] is None
    assert gap[next_monday]["feature_reason"] is not None
    assert gap[next_monday]["week_continuous"] == 0
    assert len(gap) == 900


@pytest.mark.parametrize("target", ["forward_return", "mae"])
def test_close_labels_and_rehearsal(target):
    p = panel()
    c = contract(p, target)
    validate_workflow_contract(c)
    rows = workflow_inputs.prepare_observations(p, c)["observations"]
    i = next(i for i, r in enumerate(rows) if r["eligible"])
    closes = [bar["close"] for bar in p["bars"]]
    expected = (100 * (closes[i + 21] / closes[i + 1] - 1) if target == "forward_return"
                else max(0, 100 * (1 - min(closes[i + 1:i + 22]) / closes[i + 1])))
    assert rows[i]["y"] == pytest.approx(expected)
    assert rows[i]["label_end"] == p["calendar"][i + 21]
    assert rows[-1]["target_label_reason"] == "immature_label"
    assert workflow.run_rehearsal(c)["fits"] == 2


def test_real_permission_and_policy_rejected():
    p = panel()
    c = contract(p)
    bad = deepcopy(c)
    bad["feature"]["week_policy"] = "current_friday"
    with pytest.raises(ValueError):
        validate_workflow_contract(bad)
    real = deepcopy(p)
    real["data_mode"] = "historical_reconstruction"
    c["permissions"] = {"real_labels": True, "effect_authorized": False, "real_fits": 4}
    with pytest.raises(ValueError, match="authorization"):
        weekly.prepare_observations(real, c, compute_labels=True)


def test_unqualified_days_never_read_future_label(monkeypatch):
    p = panel()
    c = contract(p)
    seen = []
    original = weekly.shared._label

    def traced(rows, index, target):
        seen.append(index)
        return original(rows, index, target)

    monkeypatch.setattr(weekly.shared, "_label", traced)
    rows = weekly.prepare_observations(p, c, compute_labels=True)["observations"]
    assert seen == [i for i, row in enumerate(rows) if row["feature_reason"] is None]
    assert all(row["y"] is None and row["label_end"] is None
               for row in rows if row["feature_reason"] is not None)


def test_truncated_first_week_is_not_seeded():
    p = panel()
    p["calendar"] = p["calendar"][1:]
    p["bars"] = p["bars"][1:]
    c = contract(p)
    rows = weekly.prepare_observations(p, c)["observations"]
    assert rows[0]["week_continuous"] == 0
    assert next(r for r in rows if r["week_continuous"] == 1)["last_completed_week_date"] == p["calendar"][8]
