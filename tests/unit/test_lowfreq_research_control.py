"""Synthetic contracts only; no market results or network access."""

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lei_signal.research import lowfreq_research_control as control


def bind(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
    return bind(path)


class ContractFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.selector = self.root / "selector.csv"
        self.rows = [
            {"scope": "gp", "code": "sh.600001", "decision_date": "2020-05-31", "eligibility_status": "qualified", "score": "0.2"},
            {"scope": "common_cfo", "code": "sh.600001", "decision_date": "2020-05-31", "eligibility_status": "unknown", "score": ""},
        ]
        self.write_selector()
        self.runner = self.root / "runner.py"
        self.runner.write_text("# frozen synthetic runner\n")
        self.source = self.root / "qualification.json"
        self.source_doc = {"status": "terminal", "records": [
            {"scope": "gp", "code": "sh.600001", "decision_date": "2020-05-31", "publication_date": "2020-04-01", "status": "qualified"},
            {"scope": "common_cfo", "code": "sh.600001", "decision_date": "2020-05-31", "publication_date": None, "status": "unknown"},
        ]}
        self.source_binding = save(self.source, self.source_doc)
        self.design = self.root / "design.json"
        self.design_binding = save(self.design, {"selector_sha256": bind(self.selector)["sha256"]})
        self.prior = self.root / "prior_manifest.json"
        self.prior_binding = save(self.prior, {"schema": "saved-prior/1"})
        self.brief = self.root / "brief.json"
        self.brief_doc = {"budget_control": {"core_max": 1, "core_used": 1, "followup_max": 3, "followup_used": 1}}
        self.brief_binding = save(self.brief, self.brief_doc)
        self.review = self.root / "review.json"
        self.review_doc = {"design_sha256": self.design_binding["sha256"],
                           "qualification_sha256": self.source_binding["sha256"],
                           "scientific_design_accepted": True, "effects_authorized": True,
                           "label_access_authorized": True,
                           "result_accepted": False}
        self.review_binding = save(self.review, self.review_doc)
        self.contract = {"schema": control.SCHEMA, "action": "preflight", "stage": "diagnostic",
                         "scopes": ["gp", "common_cfo"],
                         "bindings": {"design": self.design_binding, "runner": bind(self.runner),
                                      "source_qualification": self.source_binding,
                                      "prior_manifest": self.prior_binding, "brief": self.brief_binding,
                                      "controller_review": self.review_binding, "selector": bind(self.selector)},
                         "scientific_identity": {"question": "Does saved financial rank distinguish stocks?",
                                                 "definition": "same month and industry rank bands",
                                                 "formula": "top band minus bottom band",
                                                 "inputs": [self.prior_binding, self.source_binding],
                                                 "uses": ["selection gradient"]},
                         "history": {"reviewed_history_complete": True, "attempts": []}}

    def write_selector(self, extra=None):
        fields = ["scope", "code", "decision_date", "eligibility_status", "score"] + ([extra] if extra else [])
        with self.selector.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({**row, **({extra: "0.9"} if extra else {})})

    def refresh_source(self):
        self.source_binding = save(self.source, self.source_doc)
        self.contract["bindings"]["source_qualification"] = self.source_binding
        self.contract["scientific_identity"]["inputs"][1] = self.source_binding
        self.review_doc["qualification_sha256"] = self.source_binding["sha256"]
        self.contract["bindings"]["controller_review"] = save(self.review, self.review_doc)

    def add_attempt(self, status, *, identity=None):
        identity = identity or control._identity(self.contract["scientific_identity"])
        attempt = {"schema": "lowfreq-research-attempt/1", "identity_sha256": identity,
                   "stage": "diagnostic", "status": status}
        if status != "started":
            receipt = self.root / f"receipt-{status}.json"
            receipt_doc = {"status": status}
            if status == "completed":
                manifest = self.root / "old-manifest.json"
                attempt["manifest"] = save(manifest, {"status": "computed"})
                receipt_doc["manifest_sha256"] = attempt["manifest"]["sha256"]
            attempt["receipt"] = save(receipt, receipt_doc)
        path = self.root / f"attempt-{status}.json"
        self.contract["history"]["attempts"].append(save(path, attempt))

    def result(self, *, accepted=False):
        output = self.root / "diagnostic.json"
        output_binding = save(output, {"count": 2})
        manifest = self.root / "result-manifest.json"
        manifest_binding = save(manifest, {"schema": "lowfreq-controlled-result/1", "stage": "diagnostic",
                                           "identity_sha256": control._identity(self.contract["scientific_identity"]),
                                           "status": "computed_pending_review", "evidence_status": "inconclusive",
                                           "outputs": {"diagnostic.json": output_binding}, "exit_code": 0})
        self.contract["action"] = "acceptance"
        self.contract["result_manifest"] = manifest_binding
        if accepted:
            self.review_doc.update(result_accepted=True, result_manifest_sha256=manifest_binding["sha256"])
            self.contract["bindings"]["controller_review"] = save(self.review, self.review_doc)
        return output


class LowfreqControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fx = ContractFixture(self.tmp.name)

    def test_valid_seen_diagnostic_and_same_code_two_scopes(self):
        answer = control.check(self.fx.contract)
        self.assertEqual(answer["status"], "eligible_for_separate_execution")
        self.assertEqual(answer["source_counts"], {"qualified": 1, "unknown": 1})

    def test_diagnostic_does_not_bypass_outcome_authorization(self):
        self.fx.review_doc["label_access_authorized"] = False
        self.fx.contract["bindings"]["controller_review"] = save(self.fx.review, self.fx.review_doc)
        with self.assertRaisesRegex(control.ControlError, "outcome access not authorized"):
            control.check(self.fx.contract)

    def test_qualification_never_returns_permission_for_outcomes(self):
        self.fx.contract["stage"] = "qualification"
        self.fx.review_doc.update(label_access_authorized=False, scientific_design_accepted=False)
        self.fx.contract["bindings"]["controller_review"] = save(self.fx.review, self.fx.review_doc)
        self.assertEqual(control.check(self.fx.contract)["status"], "source_work_only")

    def test_late_publication_or_unqualified_effect_is_blocked(self):
        self.fx.source_doc["records"][0]["publication_date"] = "2020-06-01"
        self.fx.refresh_source()
        with self.assertRaisesRegex(control.ControlError, "not public"):
            control.check(self.fx.contract)
        self.fx.source_doc["records"][0].update(publication_date=None, status="unknown")
        self.fx.rows[0].update(eligibility_status="unknown", score="")
        self.fx.write_selector()
        self.fx.contract["bindings"]["selector"] = bind(self.fx.selector)
        self.fx.contract["bindings"]["design"] = save(self.fx.design, {"selector_sha256": bind(self.fx.selector)["sha256"]})
        self.fx.review_doc["design_sha256"] = self.fx.contract["bindings"]["design"]["sha256"]
        self.fx.refresh_source()
        self.fx.contract["stage"] = "effect"
        with self.assertRaisesRegex(control.ControlError, "lacks authority or qualified"):
            control.check(self.fx.contract)

    def test_unknown_score_not_zero_filled(self):
        self.fx.rows[1]["score"] = "0"
        self.fx.write_selector()
        self.fx.contract["bindings"]["selector"] = bind(self.fx.selector)
        self.fx.contract["bindings"]["design"] = save(self.fx.design, {"selector_sha256": bind(self.fx.selector)["sha256"]})
        self.fx.review_doc["design_sha256"] = self.fx.contract["bindings"]["design"]["sha256"]
        self.fx.contract["bindings"]["controller_review"] = save(self.fx.review, self.fx.review_doc)
        with self.assertRaisesRegex(control.ControlError, "filled with score"):
            control.check(self.fx.contract)

    def test_future_outcome_or_weight_column_cannot_enter_selector(self):
        for forbidden in ("future_return", "weight_B", "exit_date"):
            self.fx.write_selector(forbidden)
            self.fx.contract["bindings"]["selector"] = bind(self.fx.selector)
            self.fx.contract["bindings"]["design"] = save(self.fx.design, {"selector_sha256": bind(self.fx.selector)["sha256"]})
            self.fx.review_doc["design_sha256"] = self.fx.contract["bindings"]["design"]["sha256"]
            self.fx.contract["bindings"]["controller_review"] = save(self.fx.review, self.fx.review_doc)
            with self.assertRaisesRegex(control.ControlError, "result/weight/future"):
                control.check(self.fx.contract)

    def test_immutable_hash_drift_rejected(self):
        self.fx.runner.write_text("# changed\n")
        with self.assertRaisesRegex(control.ControlError, "absent or changed"):
            control.check(self.fx.contract)

    def test_unsettled_attempt_rejected(self):
        self.fx.add_attempt("started")
        with self.assertRaisesRegex(control.ControlError, "unsettled"):
            control.check(self.fx.contract)

    def test_completed_attempt_without_receipt_rejected(self):
        self.fx.add_attempt("completed")
        attempt_binding = self.fx.contract["history"]["attempts"][0]
        attempt = json.loads(Path(attempt_binding["path"]).read_text())
        attempt.pop("receipt")
        self.fx.contract["history"]["attempts"][0] = save(Path(attempt_binding["path"]), attempt)
        with self.assertRaises(control.ControlError):
            control.check(self.fx.contract)

    def test_completed_same_identity_reuses_even_if_input_path_copied(self):
        self.fx.add_attempt("completed")
        copied = self.fx.root / "copy-of-prior.json"
        copied.write_bytes(self.fx.prior.read_bytes())
        self.fx.contract["scientific_identity"]["inputs"][0] = bind(copied)
        self.assertEqual(control.check(self.fx.contract)["status"], "reuse")

    def test_renaming_output_or_agent_does_not_reset_spent_budget(self):
        self.fx.brief_doc["budget_control"]["followup_used"] = 3
        self.fx.contract["bindings"]["brief"] = save(self.fx.brief, self.fx.brief_doc)
        self.fx.contract["agent"] = "new-name"
        self.fx.contract["output"] = "another-directory"
        with self.assertRaisesRegex(control.ControlError, "budget exhausted"):
            control.check(self.fx.contract)

    def test_exit_zero_without_result_review_remains_pending(self):
        self.fx.result()
        self.assertEqual(control.check(self.fx.contract)["status"], "pending_review")
        self.fx.review_doc.update(result_accepted=True, result_manifest_sha256=self.fx.contract["result_manifest"]["sha256"])
        self.fx.contract["bindings"]["controller_review"] = save(self.fx.review, self.fx.review_doc)
        self.assertEqual(control.check(self.fx.contract)["status"], "accepted")

    def test_result_output_hash_drift_blocks_acceptance(self):
        output = self.fx.result(accepted=True)
        output.write_text('{"count": 999}')
        with self.assertRaisesRegex(control.ControlError, "absent or changed"):
            control.check(self.fx.contract)

    def test_nan_budget_rejected(self):
        self.fx.brief_doc["budget_control"]["followup_used"] = float("nan")
        self.fx.brief.write_text(json.dumps(self.fx.brief_doc), encoding="utf-8")
        self.fx.contract["bindings"]["brief"] = bind(self.fx.brief)
        with self.assertRaisesRegex(control.ControlError, "nonnegative integer"):
            control.check(self.fx.contract)


if __name__ == "__main__":
    unittest.main()
