"""Read-only attachment checks, never a backtest or financial certification."""

import copy
import hashlib
import json

import pytest

from lei_signal.research.component_diagnosis import review_diagnosis


def _value(direction="positive"):
    return {
        "context": {
            key: key + "-v1"
            for key in (
                "object_id",
                "period",
                "opportunity_set_id",
                "signal_version",
                "benchmark_id",
                "capital_rules",
                "cost_rules",
                "execution_rules",
                "exit_rules",
                "other_rules",
            )
        },
        "result": {"evaluated": True, "metrics": {"synthetic_only": 0.01}},
        "judgment": {
            "direction": direction,
            "criterion": "original contract declaration",
            "contract_id": "contract-one",
        },
    }


def _ref(root, name, value):
    path = root / (name + ".json")
    path.write_text(json.dumps({"saved": value}), encoding="utf-8")
    return {
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "pointer": "/saved",
        "value": copy.deepcopy(value),
    }


def _request(root, conflict=True):
    return {
        "schema": "component-diagnosis/1",
        "signal": _ref(root, "signal", _value()),
        "account": _ref(root, "account", _value("negative" if conflict else "positive")),
        "suspected_component": "exit",
    }


def _comparison(root, request, component="exit"):
    variant = copy.deepcopy(request["account"]["value"])
    variant["context"]["exit_rules" if component == "exit" else "capital_rules"] = "alternative-v1"
    variant["result"]["metrics"]["synthetic_only"] = 0.02
    return {
        "component": component,
        "baseline": copy.deepcopy(request["account"]),
        "variant": _ref(root, "variant", variant),
    }


def test_no_conflict_needs_no_component_or_backtests(tmp_path):
    request = _request(tmp_path, conflict=False)
    request.pop("suspected_component")
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "not_needed"
    assert result["conflict_detected"] is False
    assert result["planned_comparisons"] == []
    assert not result["run_authorized"] and not result["causality_verified"]
    assert not result["returns_verified"]


def test_conflict_only_plans_one_manual_comparison_and_writes_nothing(tmp_path):
    request = _request(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "planned_for_manual_review"
    assert result["conflict_detected"] is True
    assert result["max_comparisons"] == 1
    assert len(result["planned_comparisons"]) == 1
    assert result["planned_comparisons"][0]["component"] == "exit"
    assert "opportunity_set_id" in result["planned_comparisons"][0]["frozen_fields"]
    assert not result["run_authorized"] and not result["executed"]
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize(
    "result_value",
    [
        None,
        {},
        {"evaluated": False},
        {"evaluated": True},
        {"evaluated": True, "metrics": {"return": "unknown"}},
        {"evaluated": True, "metrics": {"return": None}},
        {"evaluated": True, "metrics": {"status": "not_evaluated"}},
    ],
)
def test_missing_measurements_are_blocked_not_conflicts(tmp_path, result_value):
    request = _request(tmp_path)
    value = request["account"]["value"]
    value["result"] = result_value
    request["account"] = _ref(tmp_path, "account", value)
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "blocked"
    assert result["conflict_detected"] is None
    assert result["planned_comparisons"] == []


@pytest.mark.parametrize("tamper", ["sha", "value", "pointer", "source"])
def test_source_binding_prevents_forged_or_drifted_judgment(tmp_path, tamper):
    request = _request(tmp_path)
    if tamper == "sha":
        request["account"]["sha256"] = "0" * 64
    elif tamper == "value":
        request["account"]["value"]["judgment"]["direction"] = "positive"
    elif tamper == "pointer":
        request["account"]["pointer"] = "/missing"
    else:
        (tmp_path / "account.json").write_text("{}")
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "blocked"
    assert result["conflict_detected"] is None


@pytest.mark.parametrize(
    "field",
    [
        "opportunity_set_id",
        "period",
        "object_id",
        "signal_version",
        "benchmark_id",
        "cost_rules",
        "other_rules",
    ],
)
def test_different_context_is_not_a_conflict(tmp_path, field):
    request = _request(tmp_path)
    value = request["account"]["value"]
    value["context"][field] = "unrelated"
    request["account"] = _ref(tmp_path, "account", value)
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


def test_prior_comparison_is_reused_before_planning(tmp_path):
    request = _request(tmp_path)
    request["comparison"] = _comparison(tmp_path, request)
    request.pop("suspected_component")
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "reused_for_manual_review"
    assert len(result["reused_comparisons"]) == 1
    assert result["planned_comparisons"] == []
    assert not result["returns_verified"] and not result["causality_verified"]


@pytest.mark.parametrize(
    "field", ["capital_rules", "execution_rules", "cost_rules", "other_rules", "opportunity_set_id"]
)
def test_exit_comparison_freezes_all_other_conditions(tmp_path, field):
    request = _request(tmp_path)
    comparison = _comparison(tmp_path, request)
    value = comparison["variant"]["value"]
    value["context"][field] = "also changed"
    comparison["variant"] = _ref(tmp_path, "variant", value)
    request["comparison"] = comparison
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


def test_capital_execution_can_change_only_selected_component(tmp_path):
    request = _request(tmp_path)
    request["suspected_component"] = "capital_execution"
    request["comparison"] = _comparison(tmp_path, request, "capital_execution")
    assert review_diagnosis(tmp_path, request)["status"] == "reused_for_manual_review"


@pytest.mark.parametrize(
    "change", ["unrelated_baseline", "contract", "criterion", "no_change", "multiple"]
)
def test_reuse_rejects_unrelated_or_multiple_comparisons(tmp_path, change):
    request = _request(tmp_path)
    comparison = _comparison(tmp_path, request)
    value = comparison["variant"]["value"]
    if change == "unrelated_baseline":
        comparison["baseline"] = _ref(tmp_path, "unrelated", comparison["baseline"]["value"])
    elif change in {"contract", "criterion"}:
        value["judgment"]["contract_id" if change == "contract" else "criterion"] = "different"
        comparison["variant"] = _ref(tmp_path, "variant", value)
    elif change == "no_change":
        comparison["variant"] = _ref(tmp_path, "variant", request["account"]["value"])
    request["comparison"] = [comparison, comparison] if change == "multiple" else comparison
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


@pytest.mark.parametrize("component", [["exit", "capital_execution"], "all", None])
def test_one_suspected_component_is_required_for_plan(tmp_path, component):
    request = _request(tmp_path)
    request["suspected_component"] = component
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


def test_outside_root_and_symlink_escape_blocked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    request = _request(root)
    outer = _ref(tmp_path, "outside", request["account"]["value"])
    outer["path"] = str(tmp_path / "outside.json")
    request["account"] = outer
    assert review_diagnosis(root, request)["status"] == "blocked"
    (root / "escape.json").symlink_to(tmp_path / "outside.json")
    request["account"]["path"] = "escape.json"
    assert review_diagnosis(root, request)["status"] == "blocked"


def test_original_contract_identity_must_match(tmp_path):
    request = _request(tmp_path)
    value = request["account"]["value"]
    value["judgment"]["contract_id"] = "other contract"
    request["account"] = _ref(tmp_path, "account", value)
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


def test_plan_freezes_extra_declared_conditions(tmp_path):
    request = _request(tmp_path)
    for layer in ("signal", "account"):
        value = request[layer]["value"]
        value["context"]["dividend_basis"] = "net-reinvested-v1"
        request[layer] = _ref(tmp_path, layer, value)
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "planned_for_manual_review"
    assert "dividend_basis" in result["planned_comparisons"][0]["frozen_fields"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_nonfinite_and_boolean_metrics_do_not_count_as_measurements(tmp_path, value):
    request = _request(tmp_path)
    selected = request["account"]["value"]
    selected["result"]["metrics"] = {"metric": value}
    request["account"] = _ref(tmp_path, "account", selected)
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


def test_missing_context_field_and_unbound_judgment_are_blocked(tmp_path):
    request = _request(tmp_path)
    value = request["account"]["value"]
    value["context"].pop("capital_rules")
    request["account"] = _ref(tmp_path, "account", value)
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"
    request = _request(tmp_path)
    request["account"] = {"direction": "negative"}
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


def test_duplicate_json_source_keys_are_rejected(tmp_path):
    request = _request(tmp_path)
    path = tmp_path / "account.json"
    path.write_text('{"saved": {}, "saved": ' + json.dumps(request["account"]["value"]) + "}")
    request["account"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


@pytest.mark.parametrize("status", ["unknown", "not_evaluated", "pending", "failed", "incomplete"])
def test_contradictory_saved_result_status_is_blocked(tmp_path, status):
    request = _request(tmp_path)
    value = request["account"]["value"]
    value["result"]["status"] = status
    request["account"] = _ref(tmp_path, "account", value)
    assert review_diagnosis(tmp_path, request)["status"] == "blocked"


@pytest.mark.parametrize(
    ("signal_direction", "account_direction", "expected_conflict"),
    [
        ("positive", "neutral", True),
        ("neutral", "positive", True),
        ("positive", "negative", True),
        ("negative", "positive", True),
        ("negative", "neutral", False),
        ("neutral", "negative", False),
        ("positive", "positive", False),
        ("negative", "negative", False),
        ("neutral", "neutral", False),
    ],
)
def test_declared_positive_improvement_vs_no_improvement_triggers_diagnosis(
    tmp_path, signal_direction, account_direction, expected_conflict
):
    request = _request(tmp_path)
    request["signal"] = _ref(tmp_path, "signal", _value(signal_direction))
    request["account"] = _ref(tmp_path, "account", _value(account_direction))
    result = review_diagnosis(tmp_path, request)
    assert result["conflict_detected"] is expected_conflict
    assert result["status"] == ("planned_for_manual_review" if expected_conflict else "not_needed")
    assert len(result["planned_comparisons"]) == int(expected_conflict)
    assert not result["run_authorized"] and not result["executed"]


@pytest.mark.parametrize("layer", ["signal", "account"])
def test_unknown_direction_still_blocks_conditional_diagnosis(tmp_path, layer):
    request = _request(tmp_path)
    request[layer] = _ref(tmp_path, layer, _value("unknown"))
    result = review_diagnosis(tmp_path, request)
    assert result["status"] == "blocked"
    assert result["conflict_detected"] is None
    assert result["planned_comparisons"] == []
