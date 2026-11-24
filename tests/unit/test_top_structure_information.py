"""T01: narrow strict top, causal timing and source gates."""
import copy
import json
from pathlib import Path

import pytest

from lei_signal.research.top_structure_information import (
    DEFINITION_REF, prepare_top_observations, qualify_top_panel,
)

ROOT = Path(__file__).resolve().parents[2]


def _case():
    from datetime import date, timedelta
    days = [(date(2022, 1, 3) + timedelta(days=i)).isoformat() for i in range(270)]
    bars = []
    for i, day in enumerate(days):
        close = 100 + i / 10
        high, low = close + 1, close - 1
        if i in (252, 253, 254):
            high = 130 - (i - 252)
            low = 126 - (i - 252)
            close = 128 - (i - 252)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": close, "high": high, "low": low, "close": close,
                     "action_known": True})
    contract = {"feature": {"kind": "simple_top3_information", "definition_ref": DEFINITION_REF,
                            "lookback": 60, "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "path_field": "close"},
                "question": {"sampling": "daily", "period": [days[251], days[-1]]},
                "universe": {"assets": ["synthetic-A"]}}
    return {"data_mode": "synthetic", "calendar": days, "bars": bars}, contract


def _at(result, day):
    return next(r for r in result["observations"] if r["date"] == day)


def test_strict_shape_equal_boundaries_containment_and_prefix():
    payload, contract = _case()
    days = payload["calendar"]
    base = prepare_top_observations(payload, contract, compute_labels=False)
    assert _at(base, days[254])["simple_top3"] is True
    assert _at(base, days[254])["y"] is None
    assert _at(base, days[254])["label_reason"] == "not_computed"
    for field, value in (("high", payload["bars"][253]["high"]),
                         ("low", payload["bars"][253]["low"]),
                         ("high", payload["bars"][252]["high"] + 1)):
        altered = copy.deepcopy(payload)
        altered["bars"][254][field] = value
        assert _at(prepare_top_observations(altered, contract, compute_labels=False), days[254])["simple_top3"] is False
    prefix = copy.deepcopy(payload)
    prefix["bars"] = prefix["bars"][:255]
    prefix["calendar"] = prefix["calendar"][:255]
    assert _at(prepare_top_observations(prefix, contract, compute_labels=False), days[254])["features"] == _at(base, days[254])["features"]


def test_missing_reset_and_no_future_labels():
    payload, contract = _case()
    missing = copy.deepcopy(payload)
    missing["bars"][253].update(status="vendor_missing", open=None, high=None, low=None, close=None)
    row = _at(prepare_top_observations(missing, contract, compute_labels=False), missing["calendar"][254])
    assert row["ready_252"] is False and row["simple_top3"] is None
    assert row["y"] is None and row["label_end"] is None


def test_source_tamper_rejected_by_full_economic_qualifier():
    folder = ROOT / "docs/experiments/raw/volume-information-2026-09-30/execution"
    payload = json.loads((folder / "panel.json").read_text())
    contract = {"data": {"sha256": "382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b",
                         "qualification": {"manifest_path": str((folder / "source-manifest.json").relative_to(ROOT))}},
                "universe": {"assets": list(("510300.SS", "510050.SS", "510500.SS", "588000.SS"))}}
    altered = copy.deepcopy(payload)
    altered["bars"][0]["high"] *= 1.01
    with pytest.raises(ValueError, match="economic high differs"):
        qualify_top_panel(altered, contract, ROOT)
