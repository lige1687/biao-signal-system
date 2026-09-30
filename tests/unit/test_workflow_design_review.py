import json
import tempfile
import unittest
from pathlib import Path

from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research.workflow import WorkflowBlocked, _verify_research_design_qualification, file_hash


FIXTURE = Path("docs/experiments/raw/research-workflow-engineering-2026-09-29/demos-final/continuous/run/contract.json")


def valid_contract():
    contract = json.loads(FIXTURE.read_text(encoding="utf-8"))
    contract["schema_version"] = "research-workflow/1.1"
    contract["research_design"] = {
        "claim_mapping": {
            "original_statement": "The source says the state may help identify stronger trends.",
            "source_section": "section 4.2",
            "proxy_definition": "The frozen daily feature represents the stated state.",
            "preserved_conditions": ["same decision timing"],
            "omitted_conditions": [],
            "decision_use": "Context for discretionary review",
            "observation_time": "after daily close",
            "intended_action_time": "next trading session",
            "application_scope": "fixed synthetic example only",
            "tested_scope": "two generated assets and one period",
            "unresolved_uses": [],
        },
        "sample_fit": {
            "qualification_artifact": "qualification.json",
            "qualification_sha256": "a" * 64,
            "outcome_values_used_for_design": False,
            "unit": "asset-date observation",
            "assets": 2,
            "observations": 100,
            "dates": 50,
            "episodes": None,
            "paired_support": "same asset-date rows",
            "dependence": "overlapping dates and shared market movement",
            "model_feature_count": 2,
            "rationale": "The qualified sample can support a limited estimate.",
            "decision": "estimate",
        },
    }
    for key, reason in zip(
        contract["controller_review"],
        ["Universe has two generated assets.", "Proxy is synthetic.", "Method is a mechanical demo.", "Conclusion is limited to the demo."],
    ):
        contract["controller_review"][key]["reason"] = reason
    return contract


class WorkflowDesignReviewTests(unittest.TestCase):
    def test_valid_1_1(self):
        self.assertIsNone(validate_workflow_contract(valid_contract()))

    def test_1_1_requires_design(self):
        contract = valid_contract()
        del contract["research_design"]
        with self.assertRaisesRegex(ValueError, "research_design"):
            validate_workflow_contract(contract)

    def test_1_1_controller_reasons_must_be_distinct_after_whitespace_normalization(self):
        contract = valid_contract()
        contract["controller_review"]["proxy_fidelity"]["reason"] = "  Universe   has two generated assets. "
        with self.assertRaisesRegex(ValueError, "distinct reasons"):
            validate_workflow_contract(contract)

    def test_rejects_future_outcomes_used_for_design(self):
        contract = valid_contract()
        contract["research_design"]["sample_fit"]["outcome_values_used_for_design"] = True
        with self.assertRaisesRegex(ValueError, "must be false"):
            validate_workflow_contract(contract)

    def test_model_feature_count_must_match_evaluator(self):
        contract = valid_contract()
        contract["research_design"]["sample_fit"]["model_feature_count"] = 3
        with self.assertRaisesRegex(ValueError, "distinct baseline and added feature count"):
            validate_workflow_contract(contract)

    def test_nonestimate_decision_keeps_qualification_without_statistical_run(self):
        for decision in ("describe_only", "qualification_only"):
            contract = valid_contract()
            contract["research_design"]["sample_fit"]["decision"] = decision
            with self.subTest(decision=decision), self.assertRaisesRegex(ValueError, "without a statistical run"):
                validate_workflow_contract(contract)

    def test_counts_and_lists_have_required_types(self):
        for field, value in (("assets", True), ("observations", -1), ("dates", 1.5), ("episodes", False)):
            contract = valid_contract()
            contract["research_design"]["sample_fit"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_workflow_contract(contract)
        for field, value in (("preserved_conditions", "one"), ("omitted_conditions", None), ("unresolved_uses", {})):
            contract = valid_contract()
            contract["research_design"]["claim_mapping"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_workflow_contract(contract)

    def test_legacy_1_0_contract_keeps_previous_shape(self):
        contract = json.loads(FIXTURE.read_text(encoding="utf-8"))
        contract.pop("research_design", None)
        self.assertIsNone(validate_workflow_contract(contract))

    def test_preflight_binding_accepts_hashed_counts_for_scheduled_rows(self):
        contract = valid_contract()
        rows = [
            {"asset": "A", "date": "2022-01-03", "eligible": False},
            {"asset": "A", "date": "2022-01-04", "eligible": True},
            {"asset": "B", "date": "2022-01-04", "eligible": False},
        ]
        contract["research_design"]["sample_fit"].update(assets=2, observations=3, dates=2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            artifact = {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
                        "counts": {"assets": 2, "observations": 3, "dates": 2, "episodes": None},
                        "scientific_support": {"qualified_train": 3, "qualified_eval": 1}}
            path.write_text(json.dumps(artifact), encoding="utf-8")
            contract["research_design"]["sample_fit"]["qualification_sha256"] = file_hash(path)
            _verify_research_design_qualification(contract, rows, tmp)

    def test_preflight_binding_rejects_bad_hash_count_and_data_source(self):
        contract = valid_contract()
        rows = [{"asset": "A", "date": "2022-01-03"}, {"asset": "B", "date": "2022-01-04"}]
        contract["research_design"]["sample_fit"].update(assets=2, observations=2, dates=2)
        for mutation, expected in (
            (lambda a: a.update(counts={"assets": 1, "observations": 2, "dates": 2, "episodes": None}), "counts.assets"),
            (lambda a: a.update(data_sha256="wrong"), "data_sha256"),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "qualification.json"
                artifact = {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
                            "counts": {"assets": 2, "observations": 2, "dates": 2, "episodes": None}}
                mutation(artifact)
                path.write_text(json.dumps(artifact), encoding="utf-8")
                contract["research_design"]["sample_fit"]["qualification_sha256"] = file_hash(path)
                with self.subTest(expected=expected), self.assertRaisesRegex(WorkflowBlocked, expected):
                    _verify_research_design_qualification(contract, rows, tmp)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            path.write_text("{}", encoding="utf-8")
            contract["research_design"]["sample_fit"]["qualification_sha256"] = "a" * 64
            with self.assertRaisesRegex(WorkflowBlocked, "hash"):
                _verify_research_design_qualification(contract, rows, tmp)

    def test_legacy_1_0_does_not_read_qualification_file(self):
        contract = {"schema_version": "research-workflow/1.0"}
        _verify_research_design_qualification(contract, [], "/path/that/does/not/exist")

    def test_episode_count_requires_and_counts_observed_episode_ids(self):
        contract = valid_contract()
        contract["research_design"]["sample_fit"].update(assets=1, observations=2, dates=2, episodes=1)
        rows = [{"asset": "A", "date": "2022-01-03", "episode_id": "event-1"},
                {"asset": "A", "date": "2022-01-04", "episode_id": "event-1"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            artifact = {"data_sha256": contract["data"]["sha256"], "outcome_values_used_for_design": False,
                        "counts": {"assets": 1, "observations": 2, "dates": 2, "episodes": 1}}
            path.write_text(json.dumps(artifact), encoding="utf-8")
            contract["research_design"]["sample_fit"]["qualification_sha256"] = file_hash(path)
            _verify_research_design_qualification(contract, rows, tmp)
            without_episode_field = [{key: value for key, value in row.items() if key != "episode_id"} for row in rows]
            with self.assertRaisesRegex(WorkflowBlocked, "no episode_id"):
                _verify_research_design_qualification(contract, without_episode_field, tmp)


if __name__ == "__main__":
    unittest.main()
