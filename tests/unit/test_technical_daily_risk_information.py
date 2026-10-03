"""Synthetic checks for the two research-only 21-close risk adapters."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import json
import math
from pathlib import Path

import pytest

from lei_signal.research import workflow, workflow_inputs
from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research.technical_daily_risk_information import prepare_risk_observations


ROOT = Path(__file__).resolve().parents[2]


def contract(kind):
    source = "slope" if kind == "slope_change_risk_information" else "age"
    path = ROOT / f"docs/experiments/raw/technical-daily-risk-2026-10-03/{source}/original-draft.json"
    c = json.loads(path.read_text(encoding="utf-8"))
    ref = ("research.risk.slope_change60_20@1.0.0" if source == "slope" else
           "research.risk.ema_only_wait_age20@1.0.0")
    c["feature"].update(kind=kind, definition_ref=ref)
    c["question"]["factor_refs"] = [ref]
    c["target"].update(kind="mae", path_field="close")
    c["question"]["target"].update(kind="mae", price_basis="close_to_close_path")
    c["evaluator"]["minimum_training_rows"] = 22
    return c


def panel(count=320):
    days = [(date(2023, 1, 2) + timedelta(days=i)).isoformat() for i in range(count)]
    bars = []
    for i, day in enumerate(days):
        price = 100 + 0.03 * i + 5 * math.sin(i / 3)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": price, "high": price + 1, "low": price - 1,
                     "close": price, "volume": 100.0, "action_known": True})
    return {"data_mode": "synthetic", "calendar": days, "bars": bars}


@pytest.mark.parametrize("kind", ["slope_change_risk_information", "ema_only_wait_age_risk_information"])
def test_registered_contract_and_rehearsal(kind):
    c = contract(kind)
    validate_workflow_contract(c)
    result = workflow.run_rehearsal(c)
    assert result["fits"] == 2
    assert result["coverage"]["eligible"] > 0
    assert result["performance"]


@pytest.mark.parametrize("kind", ["slope_change_risk_information", "ema_only_wait_age_risk_information"])
def test_features_are_past_only_and_label_uses_closes(kind, monkeypatch):
    c, p = contract(kind), panel()
    c["universe"]["assets"] = ["synthetic-A"]
    c["question"]["universe"] = ["synthetic-A"]
    c["question"]["period"] = [p["calendar"][0], p["calendar"][-1]]
    called = []
    original = workflow_inputs._label

    def label(*args, **kwargs):
        called.append(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(workflow_inputs, "_label", label)
    base = prepare_risk_observations(p, c)["observations"]
    assert len(called) == len(base)  # Only the new wrapper calls the label reader.
    assert base[250]["ready_252"] is False and base[251]["ready_252"] is True
    i = 270
    expected = max(0, 100 * (1 - min(b["close"] for b in p["bars"][i+1:i+22]) /
                              p["bars"][i+1]["close"]))
    assert base[i]["y"] == pytest.approx(expected)
    assert base[i]["label_end"] == p["calendar"][i+21]
    assert base[i]["definition_ref"] == c["feature"]["definition_ref"]
    assert base[-1]["target_label_reason"] == "immature_label"
    lows_only = deepcopy(p)
    lows_only["bars"][i+5]["low"] = 0.01
    assert prepare_risk_observations(lows_only, c)["observations"][i]["y"] == pytest.approx(expected)
    changed = deepcopy(p)
    changed["bars"][290].update(open=200., high=201., low=199., close=200.)
    altered = prepare_risk_observations(changed, c)["observations"]
    assert [r["features"] for r in base[:290]] == [r["features"] for r in altered[:290]]
    missing = deepcopy(p)
    missing["bars"][275] = {"asset": "synthetic-A", "date": p["calendar"][275],
                            "status": "vendor_missing", "action_known": True}
    gap = prepare_risk_observations(missing, c)["observations"]
    assert gap[275]["ready_252"] is False
    assert gap[-1]["ready_252"] is False
    assert gap[270]["target_label_reason"] == "path_vendor_missing"


@pytest.mark.parametrize("kind", ["slope_change_risk_information", "ema_only_wait_age_risk_information"])
def test_rejects_wrong_target_and_missing_real_permission(kind):
    c, p = contract(kind), panel()
    for mutation in (
        lambda x: x["target"].update(kind="forward_return"),
        lambda x: x["target"].update(path_field="low"),
        lambda x: x["target"].update(end_offset=20),
        lambda x: x["feature"].update(definition_ref="research.trend.other@1.0.0"),
    ):
        bad = deepcopy(c)
        mutation(bad)
        with pytest.raises(ValueError):
            prepare_risk_observations(p, bad)
        with pytest.raises(ValueError):
            validate_workflow_contract(bad)
    real = deepcopy(p)
    real["data_mode"] = "historical_reconstruction"
    real["price_series"] = "economic_price"
    for field, bad_value in (("real_labels", False), ("effect_authorized", False),
                             ("real_fits", 5), ("real_fits", True)):
        denied = deepcopy(c)
        denied["permissions"][field] = bad_value
        with pytest.raises(ValueError, match="authorization"):
            prepare_risk_observations(real, denied)
        with pytest.raises(workflow.WorkflowBlocked, match="four-fit ceiling"):
            workflow.preflight(denied, require_frozen=False)


def test_old_return_entry_still_rejects_mae():
    from lei_signal.research.ema_only_wait_age_information import prepare_sequence_observations
    from lei_signal.research.trend_slope_change_information import prepare_slope_observations
    p = panel()
    for kind, old in (("slope_change_risk_information", prepare_slope_observations),
                      ("ema_only_wait_age_risk_information", prepare_sequence_observations)):
        c = contract(kind)
        c["feature"]["kind"] = ("slope_change_information" if kind.startswith("slope") else
                                "ema_only_wait_age_information")
        c["feature"]["definition_ref"] = ("research.trend.slope_change60_20@1.0.0" if kind.startswith("slope") else
                                         "research.trend.ema_only_wait_age20@1.0.0")
        c["universe"]["assets"] = ["synthetic-A"]
        c["question"]["period"] = [p["calendar"][0], p["calendar"][-1]]
        with pytest.raises(ValueError):
            old(p, c, compute_labels=False)
