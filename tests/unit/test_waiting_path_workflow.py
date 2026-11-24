"""Controlled descriptive entry: synthetic only, no market effects or network."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import shutil
from unittest.mock import Mock

import pytest

from lei_signal.research import workflow as w
from lei_signal.research.question_contract import validate_workflow_contract

ROOT = Path(__file__).resolve().parents[2]
REF = "research.trend.ema20_sma20_waiting_path@1.0.0"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def case(tmp_path):
    root = tmp_path / "repo"
    catalog = w.read_json(ROOT / w.CATALOG)
    paths = list(w.CODE_PATHS) + [w.CATALOG, catalog["strategy_sources"], catalog["definition_registry"], catalog["report_registry"]]
    paths += [v["path"] for v in catalog["standards"].values()]
    paths += [f"src/lei_signal/research/{name}.py" for name in ("ema_sma_waiting_path", "top_structure_information", "volume_information")]
    for name in paths:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    dump(root / catalog["report_registry"], {"version": 1, "categories": ["方法论与验证"], "entries": {}})
    prices = [100] * 252 + [110] * 20 + [90] * 10 + [100] * 40
    dates = [(date(2022, 1, 1) + timedelta(days=i)).isoformat() for i in range(len(prices))]
    # Fixed later calendar phases are navigation, not fitted/evaluated periods.
    dates += ["2025-01-01", "2025-12-31", "2026-01-01", "2026-06-30"]
    prices += [100] * 4
    payload = {"data_mode": "synthetic", "calendar": dates, "bars": [
        {"asset": "X", "date": d, "status": "quoted", "action_known": True,
         "open": p, "high": p, "low": p, "close": p, "exact_nominal_close": str(p)}
        for d, p in zip(dates, prices)]}
    data = dump(root / "docs/experiments/raw/test/panel.json", payload)
    c = w.read_json(ROOT / "docs/experiments/raw/research-workflow-engineering-2026-09-29/demos-final/continuous/run/contract.json")
    for key in ("bindings", "freeze", "rehearsal", "calendar"):
        c.pop(key, None)
    c["schema_version"] = "research-workflow/1.1"
    c["data"] = {"mode": "synthetic", "path": str(data.relative_to(root)), "sha256": w.file_hash(data)}
    c["question"].update(factor_refs=[REF], universe=["X"], period=[dates[0], dates[-1]],
        hypothesis_family="synthetic-waiting", target={"kind": "forward_return", "horizon": 20,
        "start_offset": 1, "end_offset": 21, "price_basis": "close_to_close"},
        method={"name": "waiting_path_description", "reason": "Fixed descriptive engineering test"},
        primary_metric={"name": "paired_terminal_return_difference", "direction": "higher",
                        "attention_threshold": None, "threshold_reason": "No significance claim"})
    c["universe"].update(assets=["X"], allow_partial=False)
    c["feature"] = {"kind": "ema_sma_waiting_path", "lookback": 20, "warmup": 252,
        "missing_policy": "segmented", "bar_frequency": "daily_quote", "definition_ref": REF,
        "ema_seed": "first_close", "ema_alpha": "2/21", "sma_lag": 20, "terminal_offset": 21}
    c["target"] = {"kind": "forward_return", "start_offset": 1, "end_offset": 21,
                   "entry_field": "close", "unit": "percentage_point"}
    c["split"] = {"label_policy": "purge", "evaluation_label_policy": "contained", "folds": [
        {"train_end": "2024-12-31", "eval_start": "2025-01-01", "eval_end": "2025-12-31"},
        {"train_end": "2025-12-31", "eval_start": "2026-01-01", "eval_end": "2026-06-30"}]}
    c["evaluator"] = {"kind": "waiting_path_description", "version": "1.0.0",
                      "baseline_features": ["early_reference"], "added_features": ["first_s_confirmation"]}
    c["weights"] = {"policy": "equal_asset", "comparison": "fixed_common"}
    c["budget"] = {"scientific_variants": 1, "execution_seconds": 120, "max_rows": 1000, "real_runs": 0}
    c["history"] = {"family": "synthetic-waiting", "ledger_path": str(w.family_ledger(root, "synthetic-waiting").relative_to(root))}
    c["sources"] = []
    c["permissions"] = {"real_labels": False, "effect_authorized": False, "real_fits": 0, "paid_requests": 0, "production": False}
    c["publication"].update(report_path="docs/experiments/waiting-synthetic-2026-10-02.md", conclusion="insufficient", category="方法论与验证")
    for key, reason in zip(c["controller_review"], ("Synthetic universe only", "Fixed narrow research proxy", "No training or predictions", "Price description only")):
        c["controller_review"][key]["reason"] = reason
    artifact = dump(root / "docs/experiments/raw/test/qualification.json", {
        "data_sha256": c["data"]["sha256"], "outcome_values_used_for_design": False,
        "counts": {"assets": 1, "observations": len(dates), "dates": len(dates), "episodes": None}})
    c["research_design"] = {"claim_mapping": {
        "original_statement": "EMA may lead SMA", "source_section": "section 2.2",
        "proxy_definition": "Fixed E new-start and first S within H", "preserved_conditions": ["continuous E"],
        "omitted_conditions": ["complete module A"], "decision_use": "Describe waiting prices",
        "observation_time": "after completed close", "intended_action_time": "next close reference",
        "application_scope": "synthetic", "tested_scope": "one artificial asset", "unresolved_uses": ["trading"]},
        "sample_fit": {"qualification_artifact": str(artifact.relative_to(root)), "qualification_sha256": w.file_hash(artifact),
            "outcome_values_used_for_design": False, "unit": "scheduled asset date", "assets": 1,
            "observations": len(dates), "dates": len(dates), "episodes": None, "paired_support": "unknown until outcomes",
            "dependence": "overlapping fixed windows", "model_feature_count": 0,
            "rationale": "Description needs no train fitting", "decision": "describe_only"}}
    return root, c, payload


@pytest.mark.parametrize("field,value", [("warmup", 251), ("lookback", 60), ("ema_seed", "first_window_sma"),
    ("ema_alpha", "0.1"), ("sma_lag", 19), ("terminal_offset", 20), ("missing_policy", "real_quote")])
def test_strict_definition_gate(tmp_path, field, value):
    root, c, _ = case(tmp_path)
    c["feature"][field] = value
    spy = Mock()
    with pytest.raises(ValueError):
        w.preflight(c, root, require_frozen=False)
    spy.assert_not_called()


def test_description_gate_preserves_no_training_and_no_future_export(tmp_path):
    root, c, _ = case(tmp_path)
    validate_workflow_contract(c)
    proof = w.preflight(c, root, require_frozen=False)
    assert proof["full_prefix_invariance"]["future_outcomes"] == 0
    assert all(r["label"] is None and r["y"] is None and r["label_end"] is None for r in proof["observations"])
    frozen = w.freeze_workflow(dump(root / "draft.json", c), root / "freeze", root)
    redacted = w.read_json(root / "freeze/preflight.json")
    assert all(r["label"] is None for r in redacted["observations"])
    assert w.read_json(frozen)["rehearsal"]["fits"] == 0
    assert {"confirmed", "ema_failed"} <= set(w.read_json(frozen)["rehearsal"]["status_counts"])


def test_description_kind_rejects_predictive_claim_or_model_features(tmp_path):
    _, c, _ = case(tmp_path)
    for mutation in (lambda x: x["evaluator"].update(kind="prediction_ridge", **{"lambda": 1}),
                     lambda x: x["research_design"]["sample_fit"].update(model_feature_count=2),
                     lambda x: x["research_design"]["sample_fit"].update(decision="estimate")):
        bad = deepcopy(c)
        mutation(bad)
        with pytest.raises(ValueError):
            validate_workflow_contract(bad)


@pytest.mark.parametrize("key", ["performance", "increments", "event_ledger", "coverage", "uncertainty", "definition_ref"])
def test_publication_recomputes_every_descriptive_artifact(tmp_path, monkeypatch, key):
    root, c, _ = case(tmp_path)
    frozen = w.freeze_contract(c, root)
    path = dump(root / "frozen.json", frozen)
    out = root / "run"
    assert w.execute_workflow(path, out, root=root)["execution"] == "completed"
    result = w.read_json(out / "result.json")
    assert result["execution"]["fits"] == 0 and result["predictions"] == []
    result[key] = [] if isinstance(result[key], list) else {}
    dump(out / "result.json", result)
    # Bypass the artifact hash deliberately to test the independent numeric gate.
    monkeypatch.setattr(w, "verify_receipt", lambda *_: (frozen, w.read_json(out / "preflight.json"), w.read_json(out / "receipt.json")))
    with pytest.raises(w.WorkflowBlocked, match="publication numeric/unit/ledger mismatch"):
        w.check_publication(out, root)


def test_budget_zero_blocks_real_before_effects_or_ledger(tmp_path):
    root, c, _ = case(tmp_path)
    c["data"]["mode"] = "historical_reconstruction"
    c["permissions"].update(real_labels=True, effect_authorized=True)
    with pytest.raises(w.WorkflowBlocked, match="real-run budget"):
        w._reserve(c, {}, root / "real", root)
    assert not w.family_ledger(root, c["history"]["family"]).exists()


def test_synthetic_publication_uses_controlled_entry_and_registers(tmp_path):
    root, c, _ = case(tmp_path)
    frozen = dump(root / "frozen.json", w.freeze_contract(c, root))
    assert w.execute_workflow(frozen, root / "run", root=root, register_report=True)["execution"] == "completed"
    registry = w.read_json(root / "docs/experiments/registry.json")
    assert c["publication"]["report_path"] in registry["entries"]


def test_adapter_fingerprint_changes_features_and_future_prices_cache(tmp_path):
    root, c, _ = case(tmp_path)
    bindings = w.actual_bindings(c, root)
    changed = deepcopy(bindings)
    changed["files"]["src/lei_signal/research/ema_sma_waiting_path.py"] = "a" * 64
    before, after = w.cache_keys(c, bindings), w.cache_keys(c, changed)
    assert before["features"] != after["features"]
    assert before["labels"] != after["labels"]
    assert before["prediction"] != after["prediction"]


def test_real_permission_rejection_has_no_side_effect(tmp_path):
    root, c, _ = case(tmp_path)
    c["data"]["mode"] = "historical_reconstruction"
    c["budget"]["real_runs"] = 1
    c["permissions"].update(real_labels=True, effect_authorized=False)
    with pytest.raises(w.WorkflowBlocked, match="explicit permission"):
        w._reserve(c, {}, root / "real", root)
    assert not w.family_ledger(root, c["history"]["family"]).exists()


def test_waiting_gate_does_not_mutate_bound_panel_for_generic_prefix_probe(tmp_path, monkeypatch):
    from lei_signal.research import input_preflight
    root, c, payload = case(tmp_path)
    original = input_preflight.inspect_workflow_input
    calls = []
    def bound_input(data, contract):
        assert data == payload, "qualification must retain exact bound source panel"
        calls.append(len(data["bars"]))
        return original(data, contract)
    monkeypatch.setattr(input_preflight, "inspect_workflow_input", bound_input)
    proof = w.preflight(c, root, require_frozen=False)
    assert calls == [len(payload["bars"])]
    assert proof["prefix_checks"] == []
    assert proof["full_prefix_invariance"]["ok"]
