import json
import unittest
from pathlib import Path

from lei_signal.research.question_contract import validate_question, validate_result


def valid_question():
    return {
        "question_id": "ma-road-001",
        "hypothesis_family": "dual-ma-road",
        "factor_refs": ["etf.ma@1.0.0"],
        "layer": "factor_information",
        "comparison": "time_series",
        "sampling": "daily",
        "target": {
            "kind": "forward_return",
            "horizon": 21,
            "start_offset": 1,
            "end_offset": 22,
            "price_basis": "close_to_close",
        },
        "baseline": "shorter moving average state only",
        "added_information": "longer moving average confirmation",
        "method": {"name": "fixed-horizon group difference", "reason": "same-event baseline"},
        "primary_metric": {
            "name": "mean_return_difference",
            "direction": "higher",
            "attention_threshold": None,
            "threshold_reason": "not set for this descriptive question",
        },
        "auxiliary_metrics": ["up_rate", "median_return"],
        "universe": ["510300.SS", "510050.SS"],
        "period": ["2022-01-01", "2026-06-30"],
        "validation": {
            "stage": "exploration",
            "split_policy": "chronological date split",
            "label_boundary_policy": "drop labels crossing split boundary",
        },
        "dependence": {"note": "overlapping windows and shared ETF market dates"},
        "sources": {"frozen_daily_state.csv": "sha256-placeholder"},
        "trial_history": {"known_previous": "family history incomplete"},
    }


def valid_result(question=None):
    question = question or valid_question()
    return {
        "question_id": question["question_id"],
        "evidence": {"A": "completed", "B": "insufficient", "C": "not_applicable"},
        "conclusion": "证据不足",
        "primary": {
            "difference": None,
            "interval": None,
            "missing_reason": "not computed",
            "interval_missing_reason": "not computed",
        },
        "sample": {"rows": 10, "dates": 10, "assets": 1, "coverage": 1.0},
        "sources": ["summary.json"],
    }


class QuestionContractTests(unittest.TestCase):
    def test_valid_question(self):
        self.assertIsNone(validate_question(valid_question()))

    def test_all_frozen_questions_validate_without_flattening_objects(self):
        contract_path = Path("docs/archive/handoffs-plans/dual-ma-information-2026-09-28/questions.json")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(len(contract["questions"]), 7)
        for question in contract["questions"]:
            with self.subTest(question_id=question["question_id"]):
                self.assertIsInstance(question["universe"], list)
                self.assertIsInstance(question["period"], list)
                self.assertIsInstance(question["dependence"], dict)
                self.assertIsInstance(question["sources"], dict)
                self.assertIsInstance(question["trial_history"], dict)
                self.assertIsNone(validate_question(question))

    def test_joint_requires_nonempty_structure(self):
        question = valid_question()
        question["comparison"] = "joint"
        with self.assertRaises(ValueError):
            validate_question(question)
        question["joint_structure"] = "date blocks with all ETFs kept together"
        self.assertIsNone(validate_question(question))

    def test_other_sampling_requires_sample_unit(self):
        question = valid_question()
        question["sampling"] = "other"
        with self.assertRaises(ValueError):
            validate_question(question)
        question["sample_unit"] = "one frozen event start"
        self.assertIsNone(validate_question(question))

    def test_event_sampling_requires_definition(self):
        question = valid_question()
        question["sampling"] = "event"
        with self.assertRaises(ValueError):
            validate_question(question)
        question["event_definition"] = "first Q20 true transition"
        self.assertIsNone(validate_question(question))

    def test_cross_section_rank_method_must_match_design_and_reason(self):
        question = valid_question()
        question["method"] = {"name": "rank_ic", "reason": "rank association"}
        with self.assertRaises(ValueError):
            validate_question(question)
        question["comparison"] = "joint"
        with self.assertRaises(ValueError):
            validate_question(question)
        question["joint_structure"] = "rank across ETFs within each date, then summarize across dates"
        question["method"]["reason"] = "ranks formed by date across ETFs"
        self.assertIsNone(validate_question(question))

    def test_forward_target_horizon_and_start_are_consistent(self):
        question = valid_question()
        question["target"]["start_offset"] = 0
        with self.assertRaises(ValueError):
            validate_question(question)
        question = valid_question()
        question["target"]["horizon"] = 20
        with self.assertRaises(ValueError):
            validate_question(question)

    def test_decision_policy_can_mark_target_not_applicable_with_reason(self):
        question = valid_question()
        question["layer"] = "decision_policy"
        question["target"] = {
            "kind": "not_applicable",
            "horizon": None,
            "start_offset": None,
            "end_offset": None,
            "price_basis": None,
            "reason": "account policy outcome, not a forward factor label",
        }
        self.assertIsNone(validate_question(question))

    def test_question_rejects_bad_enums_and_empty_required_values(self):
        question = valid_question()
        question["comparison"] = "pearson"
        with self.assertRaises(ValueError):
            validate_question(question)
        question = valid_question()
        question["baseline"] = " "
        with self.assertRaises(ValueError):
            validate_question(question)

    def test_valid_result_preserves_extra_fields(self):
        result = valid_result()
        result["review_note"] = "caller-owned field"
        self.assertIsNone(validate_result(valid_question(), result))

    def test_result_requires_exact_question_id_and_known_labels(self):
        question = valid_question()
        result = valid_result(question)
        result["question_id"] = "another-question"
        with self.assertRaises(ValueError):
            validate_result(question, result)
        result = valid_result(question)
        result["conclusion"] = "looks promising"
        with self.assertRaises(ValueError):
            validate_result(question, result)

    def test_support_requires_completed_baseline_comparison(self):
        question = valid_question()
        result = valid_result(question)
        result["conclusion"] = "增量获得支持"
        result["evidence"]["B"] = "not_computed"
        with self.assertRaises(ValueError):
            validate_result(question, result)
        result["evidence"]["B"] = "completed"
        self.assertIsNone(validate_result(question, result))

    def test_exploration_cannot_claim_completed_c_evidence(self):
        question = valid_question()
        result = valid_result(question)
        result["evidence"]["C"] = "completed"
        with self.assertRaises(ValueError):
            validate_result(question, result)

    def test_null_numeric_result_needs_missing_reason(self):
        result = valid_result()
        result["primary"]["missing_reason"] = None
        with self.assertRaises(ValueError):
            validate_result(valid_question(), result)

    def test_interval_can_be_missing_independently_of_difference(self):
        result = valid_result()
        result["primary"].update(
            difference=0.2,
            interval=None,
            missing_reason=None,
            interval_missing_reason="too few effective time blocks",
        )
        self.assertIsNone(validate_result(valid_question(), result))
        result["primary"]["interval_missing_reason"] = None
        with self.assertRaises(ValueError):
            validate_result(valid_question(), result)


if __name__ == "__main__":
    unittest.main()
