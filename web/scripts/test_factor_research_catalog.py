"""Behavioral checks for the read-only research display adapter."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_factor_research", HERE / "build_factor_research.py"
)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class FactorResearchCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.summary = {
            "overall": {
                "rank_ic_valid_dates": 40,
                "rank_ic_mean": 0.1,
                "high_minus_low_mean": 0.02,
            },
            "fixed_nonoverlap_anchor": {
                "rank_ic_valid_dates": 4,
                "rank_ic_mean": -0.1,
                "high_minus_low_mean": -0.02,
            },
            "by_period": {
                "2025": {
                    "rank_ic_valid_dates": 40,
                    "rank_ic_mean": 0.1,
                    "high_minus_low_mean": 0.02,
                }
            },
            "predeclared_screen": {"positive_clue_screen_passed": False},
        }

    def _write(self, relative, data):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
        return {"path": relative, "sha256": builder.sha(p)}

    def _binding(self, id_, reference):
        prefix = f"docs/experiments/raw/{id_}"
        sources = {
            "protocol": self._write(
                f"{prefix}/protocol.json",
                {
                    "definitions": [reference],
                    "symbols": ["TEST"],
                    "window": ["2025-01-01", "2025-12-31"],
                },
            ),
            "summary": self._write(f"{prefix}/summary.json", self.summary),
            "independent": self._write(f"{prefix}/independent.json", self.summary),
            "run": self._write(
                f"{prefix}/run.json",
                {"status": "completed", "completed_at": "2026-01-01T00:00:00+00:00"},
            ),
        }
        return {
            "id": id_,
            "adapter": "rank_summary_v1",
            "reference": reference,
            "title": id_,
            "kind": "predictive_study",
            "review_status": "draft",
            "review_summary": "pending",
            "summary": "screen failed",
            "reviewed_at": "2026-01-02",
            "sources": sources,
            "limitations": [],
            "next_steps": [],
        }

    def test_same_structured_schema_accepts_second_registered_experiment(self):
        experiments, errors = builder.load_experiments(
            self.root,
            [
                self._binding("first", "factor.first@1.0.0"),
                self._binding("second", "factor.second@1.0.0"),
            ],
        )
        self.assertEqual(errors, [])
        first, second = experiments
        self.assertEqual([first["id"], second["id"]], ["first", "second"])
        self.assertEqual(second["references"], ["factor.second@1.0.0"])
        self.assertEqual(second["metrics"][1]["unit"], "fraction")
        self.assertEqual(second["result"], "no_help")

    def test_removing_experiment_removes_historical_claim(self):
        registry = builder.definitions.load_registry()
        card = builder.definitions.resolve(registry, "mixed.momentum.raw@1.0.0")
        item = builder.item_from_card(
            builder.ROOT,
            "mixed.momentum.raw@1.0.0",
            card,
            builder.factor_access.load_access_catalog(root=builder.ROOT),
            {"path": "docs/research/definitions.v1.json", "sha256": "x"},
        )
        self.assertNotEqual(item["research"]["stage"], "historical")
        builder.attach_experiments([item], [])
        self.assertEqual(item["experiment_ids"], [])
        self.assertNotIn("筛选未通过", item["research"]["summary"])

    def test_one_drifted_experiment_is_blocked_without_losing_other(self):
        good = self._binding("good", "factor.good@1.0.0")
        bad = self._binding("bad", "factor.bad@1.0.0")
        (self.root / bad["sources"]["summary"]["path"]).write_text("{}")
        experiments, errors = builder.load_experiments(self.root, [good, bad])
        self.assertEqual(experiments[0]["run_status"], "completed")
        self.assertEqual(experiments[1]["run_status"], "unknown")
        self.assertEqual(experiments[1]["result"], "insufficient")
        self.assertEqual(experiments[1]["metrics"], [])
        self.assertEqual(experiments[1]["result_tables"], [])
        self.assertEqual(len(errors), 1)
        self.assertIn("fingerprint drift", errors[0])

    def test_pinned_source_drift_rejected(self):
        binding = self._binding("drift", "factor.test@1.0.0")
        (self.root / binding["sources"]["summary"]["path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "fingerprint drift"):
            builder.make_momentum(self.root, binding)

    def test_project_source_drift_has_empty_local_fallback(self):
        spec = self._write("docs/experiments/project.md", {"status": "design"})
        project = {
            "id": "project",
            "title": "test project",
            "stage": "in_progress",
            "summary": "design",
            "review_status": "pending",
            "references": [],
            "evidence_date": "2026-01-01",
            "sources": [spec],
            "limitations": [],
            "next_steps": [],
        }
        (self.root / spec["path"]).write_text("changed")
        with self.assertRaisesRegex(ValueError, "fingerprint drift") as error:
            builder.make_project(self.root, project)
        blocked = builder.blocked_project(project, str(error.exception))
        self.assertEqual(blocked["stage"], "insufficient")
        self.assertEqual(blocked["sources"], [])
        self.assertIsNone(blocked["evidence_date"])

    def test_nonfinite_result_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            builder.metric("bad", float("nan"), "ratio", "example")

    def test_registered_families_get_specific_plain_language_purpose(self):
        registry = builder.definitions.load_registry()
        references = [
            "mixed.momentum.raw@1.0.0",
            "mixed.rv20@1.0.0",
            "trend.distance50@1.0.0",
            "breadth.csi300.delta200_20@1.0.0",
            "risk.product_account_weight@1.0.0",
            "mixed.pullback_ma_distance@2.0.0",
        ]
        descriptions = [
            builder.purpose_for(builder.definitions.resolve(registry, ref)) for ref in references
        ]
        self.assertIn("扣除最近一个月", descriptions[0])
        self.assertIn("波动", descriptions[1])
        self.assertIn("50日均线", descriptions[2])
        self.assertIn("沪深300", descriptions[3])
        self.assertIn("完整账户", descriptions[4])
        self.assertIn("哪条线最近", descriptions[5])

    def test_bad_material_blocks_one_item_without_erasing_definition(self):
        registry = builder.definitions.load_registry()
        card = builder.definitions.resolve(registry, "mixed.momentum.raw@1.0.0")
        with patch.object(
            builder.factor_access,
            "read_materials",
            side_effect=builder.factor_access.AccessError("source drift"),
        ):
            item = builder.item_from_card(
                builder.ROOT,
                "mixed.momentum.raw@1.0.0",
                card,
                {"definitions": {"mixed.momentum.raw@1.0.0": card}},
                {"path": "docs/research/definitions.v1.json", "sha256": "x"},
            )
        self.assertEqual(item["research"]["stage"], "insufficient")
        self.assertEqual(item["calculation"]["status"], "verified")
        self.assertIn("source drift", item["limitations"])

    def _workflow_binding(self, id_="question-a"):
        reference = "research.trend.ma_cluster_width@1.0.0"
        prefix = f"docs/experiments/raw/{id_}"
        report_path = f"docs/experiments/{id_}.md"
        contract = {"question": {"question_id": id_, "factor_refs": [reference],
            "period": ["2023-01-01", "2026-06-30"],
            "target": {"kind": "mae", "horizon": 20, "start_offset": 1, "end_offset": 21}},
            "feature": {"definition_ref": reference}, "target": {"kind": "mae", "start_offset": 1, "end_offset": 21},
            "universe": {"assets": ["sh000300", "sz399006"]},
            "publication": {"report_path": report_path, "conclusion": "insufficient"}}
        performance = [{"model": m, "metric": metric, "value": value,
            "unit": "percentage_point_squared" if metric == "MSE" else "percentage_point",
            "rows": 81, "dates": 43, "assets": 2}
            for m in ["B0", "B1", "B2"] for metric, value in [("MSE", 9), ("RMSE", 3)]]
        increments = [{"new_model": "B2", "old_model": m, "relative_percent": -3.77,
            "absolute_error_improvement": -0.3, "lo": -0.8, "hi": 0.1,
            "metric": "MSE", "unit": "percentage_point_squared"} for m in ["B1", "B0"]]
        result = {"performance": performance, "increments": increments,
            "period_comparisons": [{"fold": "0", "old_model": "B1", "new_model": "B2",
                "year": "2025", "old_value": 8, "new_value": 9,
                "absolute_error_improvement": -1, "rows": 47, "dates": 24,
                "unit": "percentage_point_squared"}]}
        sources = {"contract": self._write(f"{prefix}/contract.json", contract),
            "run_contract": self._write(f"{prefix}/run-contract.json", contract),
            "summary": self._write(f"{prefix}/result.json", result),
            "block60": self._write(f"{prefix}/block60.json", result)}
        sources["receipt"] = self._write(f"{prefix}/receipt.json", {
            "run_id": "run-a", "callback_executed": True,
            "contract_sha256": sources["contract"]["sha256"],
            "outputs": {"result.json": sources["summary"]["sha256"]}})
        for role in ["report", "family_report", "controller", "numeric_check", "protocol", "feature_audit"]:
            sources[role] = self._write(report_path if role == "report" else f"{prefix}/{role}.json", {"fixture": role})
        self._write("docs/experiments/registry.json", {"entries": {report_path: {"verdict": "mixed"}}})
        return {"id": id_, "adapter": "workflow_prediction_v1", "reference": reference,
            "run_id": "run-a", "target_kind": "mae", "title": "风险信息", "kind": "predictive_study",
            "summary": "证据不足", "result": "insufficient", "review_status": "reviewed",
            "review_summary": "有限复核", "reviewed_at": "2026-09-30", "sources": sources,
            "limitations": ["不是ETF账户结果"], "next_steps": [], "source_note": "审计更正保留"}

    def test_workflow_reads_exact_question_and_error_units_without_account_claim(self):
        experiment = builder.make_workflow_prediction(self.root, self._workflow_binding())
        self.assertEqual(experiment["id"], "question-a")
        self.assertEqual(experiment["references"], ["research.trend.ma_cluster_width@1.0.0"])
        self.assertEqual(experiment["target_horizon"], "20个交易日；下一交易日收盘起，至第21个交易日收盘")
        self.assertEqual(experiment["run_at"], None)
        self.assertEqual(experiment["result"], "insufficient")
        self.assertEqual(experiment["metrics"][0]["unit"], "percent")
        self.assertIn("不是投资收益", experiment["metrics"][0]["meaning"])
        self.assertEqual(experiment["source_note"], "审计更正保留")

    def test_workflow_rejects_wrong_question_old_version_and_receipt_relationship(self):
        for field, value in [("id", "wrong"), ("reference", "trend.ma_cluster_width@1.0.0"), ("run_id", "other-run")]:
            with self.subTest(field=field):
                binding = self._workflow_binding()
                binding[field] = value
                with self.assertRaises(ValueError):
                    builder.make_workflow_prediction(self.root, binding)
        binding = self._workflow_binding()
        receipt = json.loads((self.root / binding["sources"]["receipt"]["path"]).read_text())
        receipt["outputs"]["result.json"] = "0" * 64
        binding["sources"]["receipt"] = self._write(binding["sources"]["receipt"]["path"], receipt)
        with self.assertRaisesRegex(ValueError, "receipt"):
            builder.make_workflow_prediction(self.root, binding)

    def test_blocked_workflow_stays_attached_without_borrowing_completed_claim(self):
        bad = self._workflow_binding()
        bad["sources"]["controller"]["sha256"] = "0" * 64
        experiments, errors = builder.load_experiments(self.root, [bad, self._binding("other", "other@1.0.0")])
        self.assertEqual(len(errors), 1)
        item = {"reference": bad["reference"], "experiment_ids": [], "research": {"stage": "unbound", "result": "unknown"}}
        builder.attach_experiments([item], experiments)
        self.assertEqual(item["experiment_ids"], [bad["id"]])
        self.assertEqual(item["research"]["stage"], "unbound")
        self.assertEqual(experiments[1]["run_status"], "completed")

    def test_scope_rejects_unknown_duplicate_and_excluded_references(self):
        cards = {"a@1.0.0": {"type": "feature"}, "b@1.0.0": {"type": "baseline"}}
        for references in [["missing@1.0.0"], ["a@1.0.0", "a@1.0.0"], ["b@1.0.0"]]:
            with self.subTest(references=references), self.assertRaises(ValueError):
                builder.select_references(cards, {"excluded_references": [], "included_references": references})

    def test_workflow_duplicate_ids_are_rejected(self):
        binding = self._workflow_binding()
        with self.assertRaisesRegex(ValueError, "duplicate experiment id"):
            builder.load_experiments(self.root, [binding, binding])

    def test_workflow_cannot_replace_uncertainty_with_other_predictions(self):
        binding = self._workflow_binding()
        changed = json.loads((self.root / binding["sources"]["block60"]["path"]).read_text())
        changed["performance"][0]["value"] = 1
        binding["sources"]["block60"] = self._write(binding["sources"]["block60"]["path"], changed)
        with self.assertRaisesRegex(ValueError, "same predictions"):
            builder.make_workflow_prediction(self.root, binding)


if __name__ == "__main__":
    unittest.main()
