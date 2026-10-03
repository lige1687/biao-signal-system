"""Focused controls for the standalone validator; standard-library only."""
from copy import deepcopy
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import unittest

import validator as v

ROOT = Path(__file__).parent


class ValidatorControls(unittest.TestCase):
    def setUp(self):
        self.example = json.loads((ROOT / "fixtures/pass.json").read_text())

    def test_reviewed_formula_and_dependency_contracts_pass(self):
        self.assertEqual(v.validate_document(self.example)["status"], "pass")

    def test_full_formula_and_semantic_fields_are_bound(self):
        paths = [
            ("contract", "definition", "formula"),
            ("contract", "definition", "parameters", "window"),
            ("contract", "definition", "unit"),
            ("contract", "definition", "endpoints"),
            ("contract", "universe", "missing"),
            ("contract", "time", "timezone"),
            ("semantics", "input", "operator"),
            ("semantics", "ddof"),
            ("semantics", "include_current"),
            ("dependency_contracts", "mixed.asset.total_return@1.0.0", "definition", "formula"),
        ]
        for path in paths:
            with self.subTest(field=path):
                changed = deepcopy(self.example["formula"])
                current = changed
                for key in path[:-1]:
                    current = current[key]
                value = current[path[-1]]
                current[path[-1]] = not value if isinstance(value, bool) else 99 if isinstance(value, int) else "unreviewed"
                self.assertEqual(v.validate_formula(changed)["status"], "blocked")
        self.assertEqual(v.validate_formula({})["status"], "blocked")

    def test_rv20_warmup_endpoint_ddof_and_missing_controls(self):
        prices = [100.0]
        returns = [0.01, -0.02, 0.04, -0.01] * 5
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        values = v.rv20_reference(prices)
        self.assertTrue(all(x is None for x in values[:20]))
        expected = statistics.stdev(returns) * math.sqrt(252)
        self.assertAlmostEqual(values[20], expected, places=12)
        self.assertNotAlmostEqual(values[20], statistics.pstdev(returns) * math.sqrt(252), places=5)
        self.assertNotAlmostEqual(values[20], statistics.stdev([math.log(1 + r) for r in returns]) * math.sqrt(252), places=5)
        with_gap = prices[:10] + [None] + prices[10:]
        gap_values = v.rv20_reference(with_gap)
        self.assertIsNone(gap_values[10])
        self.assertAlmostEqual(gap_values[-1], expected, places=12)
        endpoint = prices[:-1] + [prices[-1] * 1.4]
        expected_last_returns = returns[:-1] + [endpoint[-1] / endpoint[-2] - 1]
        self.assertAlmostEqual(v.rv20_reference(endpoint)[-1], statistics.stdev(expected_last_returns) * math.sqrt(252), places=12)
        for bad in (0, -1, float("inf"), True):
            with self.assertRaises(ValueError):
                v.rv20_reference([100, bad])

    def test_absolute_time_equivalence_and_no_fixed_market_hour(self):
        bar = self.example["time"]["bars"][0]
        outputs = [v.qualify_bar(bar, at) for at in (
            "2026-10-03T15:30:00+08:00", "2026-10-03T07:30:00Z",
            "2026-10-03T03:30:00-04:00")]
        self.assertTrue(all(x == outputs[0] for x in outputs))
        # A synthetic midnight session crosses UTC dates; no local-hour rule.
        midnight = dict(bar, session_completed_at="2026-10-03T00:00:00+08:00",
                        feature_available_at="2026-10-03T00:05:00+08:00",
                        required_input_available_at=["2026-10-02T16:00:00Z"])
        self.assertEqual(v.qualify_bar(midnight, "2026-10-02T16:05:00Z")["status"], "pass")

    def test_global_cutoff_and_latest_required_input(self):
        bar = self.example["time"]["bars"][0]
        bar["decision_at"] = "2026-10-03T16:00:00+08:00"
        result = v.qualify_bar(bar, "2026-10-03T10:00:00+08:00")
        self.assertEqual(result["reason"], "availability_after_cutoff")
        self.assertEqual(v.qualify_bar(bar, "2026-10-03T15:00:00+08:00")["status"], "pass")
        bar["required_input_available_at"] += ["2026-10-03T16:15:00+08:00"]
        self.assertEqual(v.qualify_bar(bar, "2026-10-03T17:00:00+08:00")["reason"], "feature_precedes_required_input")
        bar["feature_available_at"] = "2026-10-03T16:15:00+08:00"
        # Per-row cutoff still applies even if the global cutoff is later.
        self.assertEqual(v.qualify_bar(bar, "2026-10-03T17:00:00+08:00")["reason"], "availability_after_cutoff")

    def test_missing_timezone_and_incomplete_availability_never_pass(self):
        bar = self.example["time"]["bars"][0]
        self.assertEqual(v.qualify_bar(bar, "2026-10-03T15:30:00")["status"], "unknown")
        self.assertEqual(v.qualify_bar(bar, "9999-12-31T23:59:59-08:00")["status"], "unknown")
        ancient = dict(bar, session_completed_at="0001-01-01T00:00:00+08:00")
        self.assertEqual(v.qualify_bar(ancient, "2026-10-03T15:30:00Z")["status"], "unknown")
        changed = dict(bar, feature_available_at="2026-10-03T15:00:00")
        self.assertEqual(v.qualify_bar(changed, "2026-10-03T15:30:00Z")["status"], "unknown")
        changed = dict(bar, availability_complete=False)
        self.assertEqual(v.qualify_bar(changed, "2026-10-03T15:30:00Z")["status"], "unknown")
        self.assertEqual(v.validate_time({"decision_at": "2026-10-03T15:30:00Z", "bars": [changed]})["status"], "blocked")
        self.assertEqual(v.validate_document({})["status"], "blocked")

    def test_cli_pass_and_two_blocking_cases(self):
        for fixture, expected in (("pass.json", 0), ("block_formula.json", 2), ("block_time.json", 2)):
            with self.subTest(fixture=fixture):
                proc = subprocess.run([sys.executable, "-B", str(ROOT / "validator.py"), str(ROOT / "fixtures" / fixture)],
                                      capture_output=True, text=True, check=False)
                self.assertEqual(proc.returncode, expected, proc.stderr)
                self.assertEqual(json.loads(proc.stdout)["status"], "pass" if expected == 0 else "blocked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
