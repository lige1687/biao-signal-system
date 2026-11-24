"""Checks the saved price/volume display without fitting models or touching source data."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import unittest
from pathlib import Path

MAIN = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "docs/research/definitions.v1.json").is_file()
)
HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_factor_research", Path(__file__).with_name("build_factor_research.py")
)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
BINDINGS = HERE / "src/pages/factor-research/display-bindings.json"


class SavedFamilyDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings = json.loads(BINDINGS.read_text())

    def _family(self, family):
        return next(x for x in self.bindings["experiments"] if x.get("family") == family)

    def test_saved_sources_give_18_exact_rows_and_both_comparisons(self):
        total = 0
        for family, expected_count, expected_rows in (("price", 6, {6072}), ("volume", 12, {6013, 6053})):
            binding = self._family(family)
            displayed = builder.make_price_volume_family(MAIN, binding)
            rows = displayed["result_tables"][0]["rows"]
            self.assertEqual(len(rows), expected_count)
            self.assertEqual(set(displayed["references"]), {x["reference"] for x in rows})
            self.assertEqual({x["rows"] for x in rows}, expected_rows)
            self.assertEqual(displayed["run_status"], "completed")
            self.assertEqual(displayed["result"], "no_help")
            for row in rows:
                self.assertTrue(math.isclose(row["vs_existing"], row["existing"] - row["added"], abs_tol=1e-10))
                self.assertTrue(math.isclose(row["vs_simple"], row["simple"] - row["added"], abs_tol=1e-10))
                self.assertLess(row["vs_simple"], 0)
                self.assertLessEqual(row["low"], row["high"])
            total += len(rows)
        self.assertEqual(total, 18)

    def test_hash_drift_blocks_only_affected_family_without_publishing_numbers(self):
        original = self._family("price")
        bad = copy.deepcopy(original)
        bad["sources"]["comparison"]["sha256"] = "0" * 64
        experiments, errors = builder.load_experiments(MAIN, [bad, self._family("volume")])
        self.assertEqual(len(errors), 1)
        self.assertEqual(experiments[0]["run_status"], "unknown")
        self.assertEqual(experiments[0]["result_tables"], [])
        self.assertEqual(experiments[1]["run_status"], "completed")

    def test_agent_button_flag_requires_verified_effect_evidence(self):
        catalog = builder.build(MAIN, BINDINGS)
        by_ref = {item["reference"]: item for item in catalog["items"]}
        for family in ("price", "volume"):
            for candidate in self._family(family)["candidates"].values():
                self.assertTrue(by_ref[candidate["reference"]]["agent_evidence_available"])
        self.assertFalse(by_ref["research.trend.ma_cluster_width@1.0.0"]["agent_evidence_available"])
        self.assertFalse(by_ref["mixed.momentum.raw@1.0.0"]["agent_evidence_available"])

    def test_new_price_volume_guides_categories_and_definition_diagnostics(self):
        catalog = builder.build(MAIN, BINDINGS)
        guides = json.loads((HERE / "src/pages/factor-research/reading-guidance.json").read_text())["guides"]
        guided = {reference for guide in guides for reference in guide["references"]}
        families = {family: self._family(family)["candidates"] for family in ("price", "volume")}
        by_ref = {item["reference"]: item for item in catalog["items"]}
        for family, candidates in families.items():
            for candidate in candidates.values():
                ref = candidate["reference"]
                self.assertIn(ref, guided)
                self.assertEqual(by_ref[ref]["category"], "价格" if family == "price" else "量能")
        self.assertEqual(len(families["price"]), 6)
        self.assertEqual(len(families["volume"]), 12)
        self.assertTrue(catalog["definition_errors"])
        self.assertFalse(set(catalog["definition_errors"]) & set(catalog["unintegrated_references"]))


if __name__ == "__main__":
    unittest.main()
