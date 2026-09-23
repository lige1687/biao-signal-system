#!/usr/bin/env python3
"""Project orchestrator mode contract, without a live dispatch."""

from pathlib import Path
import unittest

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


class DelegateModesTests(unittest.TestCase):
    def test_new_execution_uses_codex_and_gpt_6_family(self):
        body = SKILL.read_text(encoding="utf-8")
        self.assertIn("delegate_mode: codex", body)
        self.assertIn("execution_models: gpt-6-luna|gpt-6-sol|gpt-6-astra", body)
        self.assertNotIn("delegate_mode: codex|zcode", body)
        self.assertNotIn("Terra/medium", body)

    def test_keeps_historical_jobs_without_rebinding(self):
        body = SKILL.read_text(encoding="utf-8")
        self.assertIn("codex-delegate", body)
        self.assertIn("zcode-delegate", body)
        self.assertIn("does not select ZCode for new execution", body)
        self.assertIn("no silent rebinding", body)
        self.assertIn("partial writes", body)

    def test_model_effort_and_in_app_browser_are_project_policy(self):
        body = SKILL.read_text(encoding="utf-8")
        self.assertIn("6 Pro", body)
        self.assertIn("model", body)
        self.assertIn("reasoning_effort", body)
        self.assertIn("in-app browser", body)
        self.assertIn("network_allowed=false", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
