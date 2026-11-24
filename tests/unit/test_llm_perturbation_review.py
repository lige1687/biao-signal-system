"""Saved outputs only: perturbation comparisons are not leakage detection."""

import copy
import hashlib
import json

import pytest


def record():
    return {
        "data_mode": "synthetic",
        "answer_origin": "model",
        "context": dict(
            task_id="t",
            model_id="m",
            model_version="v",
            prompt_template_sha256="a" * 64,
            settings_sha256="b" * 64,
            as_of="2026-11-02",
            entity="index",
            period="daily",
            output_unit="points",
        ),
        "inputs": {"price": "100.00", "volume": "200"},
        "output": {"score": 1.0, "label": "hold", "raw_answer": "hold: 1"},
    }


def request(tmp_path, change=None):
    records = [record(), record(), record()]
    records[1]["inputs"]["price"] = "100.01"
    records[1]["output"]["score"] = 1.5
    records[2]["output"]["score"] = 1.25
    if change:
        change(records)
    refs = []
    for i, value in enumerate(records):
        data = json.dumps({"saved": value}).encode()
        path = tmp_path / f"{i}.json"
        path.write_bytes(data)
        refs.append(
            {"path": path.name, "sha256": hashlib.sha256(data).hexdigest(), "pointer": "/saved"}
        )
    return {
        "schema": "llm-perturbation-review/1",
        "pairs": [
            {
                "id": "pair1",
                "baseline": refs[0],
                "perturbed": refs[1],
                "unchanged_repeat": refs[2],
                "transformation": {
                    "fields": ["price"],
                    "max_absolute_change": "0.02",
                    "max_relative_change": "0.001",
                    "semantic_review": {
                        "status": "reviewed",
                        "reason": "Human reviewed same meaning.",
                    },
                },
            }
        ],
    }


def run(tmp_path, data):
    from lei_signal.research.llm_perturbation_review import review_perturbations

    return review_perturbations(tmp_path, data)


def test_reports_repeat_separately_without_causal_claims(tmp_path):
    result = run(tmp_path, request(tmp_path))
    assert result["status"] == "complete_for_manual_review"
    pair = result["pairs"][0]
    assert pair["perturbation"]["score_delta"] == 0.5
    assert pair["unchanged_repeat"]["score_delta"] == 0.25
    assert pair["perturbation"]["label_flip"] is False
    assert len(pair["bindings"]) == 3
    assert result["summary"]["requested_pairs"] == 1
    assert result["summary"]["comparable_pairs"] == 1
    assert not any(result["boundary"].values())


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r[0]["context"].pop("model_id"),
        lambda r: r[0]["output"].pop("raw_answer"),
        lambda r: r[0].pop("answer_origin"),
        lambda r: r[0].update(answer_origin="fallback"),
        lambda r: r[1]["context"].update(model_version="different"),
        lambda r: r[1]["context"].update(period="weekly"),
        lambda r: r[1]["context"].update(as_of="2026-11-03"),
        lambda r: r[1].update(data_mode="unknown"),
        lambda r: r[1]["inputs"].update(volume="201"),
        lambda r: r[1]["inputs"].update(price="101"),
        lambda r: r[2]["inputs"].update(price="100.01"),
        lambda r: r[1]["inputs"].pop("volume"),
        lambda r: r[1]["output"].update(score=True),
        lambda r: r[1]["output"].update(score=float("nan")),
        lambda r: r[1]["inputs"].update(price="NaN"),
        lambda r: r[1]["inputs"].update(price=100.01),
        lambda r: r[0]["inputs"].update(price="0"),
    ],
)
def test_unqualified_inputs_preserve_failed_pair(tmp_path, change):
    result = run(tmp_path, request(tmp_path, change))
    assert result["status"] == "blocked"
    assert len(result["pairs"]) == 1
    assert result["pairs"][0]["errors"]
    assert result["summary"]["comparable_pairs"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.pop("unchanged_repeat"),
        lambda p: p["transformation"].pop("semantic_review"),
        lambda p: p["transformation"]["semantic_review"].update(status="unknown"),
        lambda p: p["baseline"].update(sha256="0" * 64),
        lambda p: p["baseline"].pop("pointer"),
        lambda p: p["transformation"].update(max_absolute_change=True),
        lambda p: p["transformation"].update(fields=["price", "price"]),
        lambda p: p.update(id=True),
    ],
)
def test_missing_controls_and_source_drift_block(tmp_path, mutation):
    data = request(tmp_path)
    mutation(data["pairs"][0])
    result = run(tmp_path, data)
    assert result["status"] == "blocked"
    assert result["pairs"][0]["errors"]


def test_duplicate_ids_preserve_both_failures(tmp_path):
    data = request(tmp_path)
    data["pairs"].append(copy.deepcopy(data["pairs"][0]))
    result = run(tmp_path, data)
    assert result["summary"]["blocked_pairs"] == 2
    assert all(p["errors"] for p in result["pairs"])


def test_denominators_and_label_flip(tmp_path):
    data = request(tmp_path, lambda r: r[1]["output"].update(label="buy"))
    second = copy.deepcopy(data["pairs"][0])
    second.update(id="missing")
    second.pop("unchanged_repeat")
    data["pairs"].append(second)
    result = run(tmp_path, data)
    assert result["summary"]["requested_pairs"] == 2
    assert result["summary"]["by_data_mode"]["synthetic"]["perturbation_comparisons"] == 1
    assert result["summary"]["by_data_mode"]["synthetic"]["repeat_comparisons"] == 1
    assert result["summary"]["by_data_mode"]["synthetic"]["label_flip_count"] == 1
    assert result["summary"]["blocked_pairs"] == 1


def test_empty_and_oversize_requests(tmp_path):
    assert run(tmp_path, {})["status"] == "blocked"
    data = request(tmp_path)
    data["pairs"] *= 101
    assert run(tmp_path, data)["errors"]


def test_duplicate_source_triple_with_new_id_is_not_an_extra_observation(tmp_path):
    data = request(tmp_path)
    second = copy.deepcopy(data["pairs"][0])
    second["id"] = "renamed"
    data["pairs"].append(second)
    result = run(tmp_path, data)
    assert result["summary"]["comparable_pairs"] == 0
    assert result["summary"]["blocked_pairs"] == 2


def test_zero_baseline_has_no_invented_relative_effect(tmp_path):
    def zero(records):
        for value in records:
            value["inputs"]["price"] = "0"
        records[1]["inputs"]["price"] = "0.00"

    result = run(tmp_path, request(tmp_path, zero))
    assert result["status"] == "complete_for_manual_review"
    assert result["pairs"][0]["input_changes"][0]["relative_change"] == "0"


def test_real_saved_fallback_material_is_blocked(tmp_path):
    def old_material(records):
        for value in records:
            value["data_mode"] = "real"
            value["answer_origin"] = "fallback"
            value["context"].pop("model_id")
            value["output"].pop("raw_answer")

    result = run(tmp_path, request(tmp_path, old_material))
    assert result["status"] == "blocked"
    assert result["summary"]["comparable_pairs"] == 0


def test_reusing_baseline_reference_is_not_an_unchanged_input_repeat(tmp_path):
    data = request(tmp_path)
    data["pairs"][0]["unchanged_repeat"] = copy.deepcopy(data["pairs"][0]["baseline"])
    result = run(tmp_path, data)
    assert result["status"] == "blocked"
    assert result["pairs"][0]["errors"]


def test_completely_unchanged_inputs_are_not_a_perturbation(tmp_path):
    data = request(tmp_path, lambda records: records[1]["inputs"].update(price="100.00"))
    result = run(tmp_path, data)
    assert result["status"] == "blocked"
    assert result["summary"]["comparable_pairs"] == 0
    assert result["pairs"][0]["errors"]


def test_representation_only_change_is_a_valid_perturbation(tmp_path):
    data = request(tmp_path, lambda records: records[1]["inputs"].update(price="100.000"))
    result = run(tmp_path, data)
    assert result["status"] == "complete_for_manual_review"
    change = result["pairs"][0]["input_changes"][0]
    assert change["representation_changed"] is True
    assert float(change["absolute_change"]) == 0


def test_summary_separates_real_synthetic_and_unknown(tmp_path):
    pairs = []
    for mode in ("real", "synthetic", "unknown"):
        location = tmp_path / mode
        location.mkdir()

        def change(records, mode=mode):
            for value in records:
                value["data_mode"] = mode
            if mode == "real":
                records[1]["output"]["label"] = "buy"
                records[2]["output"]["label"] = "buy"

        data = request(location, change)
        pair = data["pairs"][0]
        pair["id"] = mode
        for role in ("baseline", "perturbed", "unchanged_repeat"):
            pair[role]["path"] = mode + "/" + pair[role]["path"]
        pairs.append(pair)
    result = run(tmp_path, {"schema": "llm-perturbation-review/1", "pairs": pairs})
    summary = result["summary"]
    assert summary["totals_scope"] == "request_processing_only"
    assert summary["requested_pairs"] == 3
    assert summary["comparable_pairs"] == 2
    assert "label_flip_count" not in summary
    assert "perturbation_comparisons" not in summary
    for mode in ("real", "synthetic", "unknown"):
        group = summary["by_data_mode"][mode]
        assert group["requested_pairs"] == 1
        assert group["comparable_pairs"] == (mode != "unknown")
        assert group["repeat_comparisons"] == (mode != "unknown")
        assert group["perturbation_comparisons"] == (mode != "unknown")
        assert group["label_flip_count"] == (mode == "real")
        assert group["repeat_label_flip_count"] == (mode == "real")
    assert summary["by_data_mode"]["unknown"]["blocked_pairs"] == 1
