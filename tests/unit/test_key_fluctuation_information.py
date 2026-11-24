"""Synthetic, prefix-only checks for the K01 research adapter."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import math

import pytest

from lei_signal.research import key_fluctuation_information as key


def _fixture():
    calendar = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(310)]
    bars = []
    for i, day in enumerate(calendar):
        close = 100 + .15 * i + 3 * math.sin(i / 6)
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "action_known": True, "open": close, "high": close + 1,
                     "low": close - 1, "close": close})
    payload = {"data_mode": "synthetic", "calendar": calendar, "bars": bars}
    contract = {"feature": {"kind": "key_fluctuation_information",
                            "definition_ref": key.DEFINITION_REF, "lookback": 60,
                            "warmup": 252, "missing_policy": "segmented"},
                "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                           "entry_field": "close", "path_field": "close",
                           "price_measure": "economic_price"},
                "question": {"sampling": "daily", "period": [calendar[0], calendar[-1]]},
                "universe": {"assets": ["synthetic-A"]}}
    return payload, contract


def test_no_label_path_is_prefix_only(monkeypatch):
    payload, contract = _fixture()
    from lei_signal.research import workflow_inputs
    monkeypatch.setattr(workflow_inputs, "_label", lambda *args, **kwargs: pytest.fail("future label accessed"))
    prepared = key.prepare_key_observations(payload, contract)
    rows = prepared["observations"]
    assert rows[250]["ready_252"] is False
    assert rows[251]["ready_252"] is True
    assert all(r["y"] is None and r["target_label_reason"] == "not_computed" for r in rows)
    assert any(r["critical_down20"] is True for r in rows)
    assert any(r["critical_down20"] is False for r in rows)
    for row in rows[251:]:
        i = payload["calendar"].index(row["date"])
        closes = [b["close"] for b in payload["bars"][:i + 1]]
        ema = closes[0]
        for close in closes[1:]:
            ema = (2 * close + 19 * ema) / 21
        assert row["critical_down20"] is ((closes[-1] < ema) and (closes[-1] < closes[-21]))


def test_missing_row_resets_warmup_and_future_mutation_does_not_change_past():
    payload, contract = _fixture()
    original = key.prepare_key_observations(payload, contract)["observations"]
    changed = deepcopy(payload)
    changed["bars"][275]["close"] += 20
    changed["bars"][275]["open"] += 20
    changed["bars"][275]["high"] += 20
    changed["bars"][275]["low"] += 20
    after = key.prepare_key_observations(changed, contract)["observations"]
    assert original[:275] == after[:275]
    missing = deepcopy(payload)
    missing["bars"][270] = {"asset": "synthetic-A", "date": payload["calendar"][270],
                            "status": "vendor_missing", "action_known": False}
    rows = key.prepare_key_observations(missing, contract)["observations"]
    assert rows[270]["ready_252"] is False
    assert rows[-1]["ready_252"] is False


def test_real_label_path_needs_separate_permission():
    payload, contract = _fixture()
    payload["data_mode"] = "historical_reconstruction"
    payload["price_series"] = "economic_price"
    contract["universe"]["assets"] = list(key.ASSETS)
    with pytest.raises(ValueError, match="authorization"):
        key.prepare_key_observations(payload, contract, compute_labels=True)


def test_matching_uses_only_known_fields_and_same_phase():
    base = {"ready_252": True, "sma60_up": True, "asset": "synthetic-A",
            "r1": -1.0, "ret3": -2.0, "ret20": -3.0, "vol20": 12.0}
    rows = [dict(base, id="f", date="2025-02-01", critical_down20=True),
            dict(base, id="a", date="2025-02-02", critical_down20=False),
            dict(base, id="b", date="2024-12-31", critical_down20=False),
            dict(base, id="c", date="2025-02-03", critical_down20=False, ret20=1.0)]
    pairs, support = key.match_known_features(rows, [r["date"] for r in rows[::-1]])
    assert [p["control_id"] for p in pairs] == ["a"]
    assert support[0]["matched"] is True


def test_synthetic_path_uses_next_close_and_full_contained_window():
    payload, contract = _fixture()
    rows = key.prepare_key_observations(payload, contract)["observations"]
    focal = rows[270]
    control = rows[271]
    result = key.describe_paths(payload, rows, [{"event_id": focal["id"], "control_id": control["id"]}])
    values = [r["close"] for r in payload["bars"][271:292]]
    assert result["paths"][focal["id"]]["mae"] == pytest.approx(100 * max(0, 1-min(values)/values[0]))
    assert result["paths"][focal["id"]]["return"] == pytest.approx(100*(values[-1]/values[0]-1))
    assert rows[270]["y"] is None  # effect helper never mutates qualification rows


def test_draft_gate_blocks_real_future_labels():
    import json
    from pathlib import Path
    from lei_signal.research.workflow import WorkflowBlocked, preflight
    root = Path(__file__).resolve().parents[2]
    draft = json.loads((root / "docs/experiments/raw/key-fluctuation-information-2026-10-01/workflow-draft.json").read_text())
    with pytest.raises(WorkflowBlocked, match="no real-label/effect authorization"):
        preflight(draft, root, require_frozen=False)


def test_pair_summary_weights_assets_equally_and_keeps_counterexample():
    diffs = {"510300.SS": [("2025-01-02", {"mae": 4.0}),
                            ("2025-01-03", {"mae": 2.0})],
             "510500.SS": [("2025-01-02", {"mae": -1.0})]}
    result = key.summarize_paired_effects({"by_asset_differences": diffs},
                                          block_lengths=(2,), draws=20, seed=1)
    assert result["overall_equal_asset"]["mae"] == pytest.approx(1.0)
    assert result["by_phase_equal_asset"]["eval_2025"]["mae"] == pytest.approx(1.0)
    assert result["asset_counterexamples"]["510500.SS"] is True
    assert len(result["uncertainty_sensitivity"]["2"]["mae"]) == 2
