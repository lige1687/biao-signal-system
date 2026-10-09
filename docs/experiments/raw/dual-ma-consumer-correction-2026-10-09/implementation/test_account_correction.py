"""Pure synthetic checks only; never runs a market account."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import account_correction as c


class CorrectionChecks(unittest.TestCase):
    def test_exact_four_s_two_d_and_unknown_preserved(self):
        sample = {
            "510300.SS": [{"date": "2025-05-29", "S20": "True", "E20": "True", "D20": "True", "S60": "", "D60": ""}],
            "159915.SZ": [{"date": "2023-01-09", "S60": "True", "E60": "True", "D60": "True"},
                          {"date": "2023-04-14", "S120": "True", "E120": "False", "D120": "False"}],
            "588000.SS": [{"date": "2024-04-30", "S60": "True", "E60": "False", "D60": "False"}],
        }
        for symbol, rows in sample.items():
            for row in rows:
                for policy in c.POLICIES[symbol]:
                    row.setdefault(policy, "False")
        before = copy.deepcopy(sample)
        after = {symbol: c.corrected_states(symbol, rows) for symbol, rows in sample.items()}
        changed = []
        for symbol in sample:
            for old, new in zip(before[symbol], after[symbol]):
                for field in old:
                    if field == "date":
                        continue
                    old_value = c.parse_state(old[field])
                    new_value = c.parse_state(new[field]) if isinstance(new[field], str) else new[field]
                    if old_value is not new_value:
                        changed.append((symbol, old["date"], field, old_value, new_value))
        self.assertEqual([x[2] for x in changed].count("D20"), 1)
        self.assertEqual([x[2] for x in changed].count("D60"), 1)
        self.assertEqual(len(changed), 6)
        self.assertEqual(after["510300.SS"][0]["S60"], "")
        self.assertEqual(after["159915.SZ"][1]["D120"], False)
        self.assertEqual(after["588000.SS"][0]["D60"], False)
        # This is the production path after corrected_states: saved rows ->
        # by_day -> assemble_policy_bars -> strict bool state.
        for symbol, rows in after.items():
            by_day = {row["date"]: row for row in rows}
            for policy in c.POLICIES[symbol]:
                bars = [{"date": row["date"], "open": "1", "close": "1"} for row in rows]
                assembled = c.assemble_policy_bars(bars, by_day, policy)
                self.assertTrue(all(type(bar["state"]) in (bool, type(None)) for bar in assembled))
        self.assertIs(c.assemble_policy_bars([{"date": "2025-05-29"}], {"2025-05-29": after["510300.SS"][0]}, "S20")[0]["state"], False)

    def test_wrong_saved_cell_and_missing_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "strict state mismatch"):
            c.corrected_states("510300.SS", [{"date": "2025-05-29", "S20": "False", "E20": "True", "D20": "False"}])
        with self.assertRaisesRegex(ValueError, "missing correction"):
            c.corrected_states("510300.SS", [])
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            c.parse_state("unknown")
        for value in (0, 1):
            with self.assertRaisesRegex(ValueError, "unrecognized"):
                c.parse_state(value)
        self.assertIs(c.parse_state(False), False)
        self.assertIs(c.parse_state(True), True)

    def test_only_twelve_replaced_and_other_120_identical(self):
        keys = sorted(c.allowed_keys())
        old = [{"symbol": s, "policy_id": p, "fee_scenario_id": f, "v": i} for i, (s, p, f) in enumerate(keys)]
        old += [{"symbol": "other", "policy_id": f"P{i}", "fee_scenario_id": "base", "v": i} for i in range(120)]
        replacements = {k: dict(old[i], v="new") for i, k in enumerate(keys)}
        result = c.replace_accounts(old, replacements)
        self.assertEqual(len(result), 132)
        self.assertEqual(result[12:], old[12:])
        with self.assertRaisesRegex(ValueError, "exact twelve"):
            c.replace_accounts(old, dict(list(replacements.items())[:-1]))

    def test_unreleased_and_wrong_route_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = root / "contract.json"
            plan = root / "plan.json"
            release = root / "release.json"
            contract.write_text(json.dumps({"affected_keys": [list(k) for k in sorted(c.allowed_keys())]}))
            plan.write_text(json.dumps({"task_id": "test"}))
            release.write_text(json.dumps({"authorized": False, "contract_sha256": c.sha(contract), "route_plan_sha256": c.sha(plan)}))
            with self.assertRaisesRegex(ValueError, "fixed parent task paths"):
                c.validate_gate(root, contract, release, plan)
            wrong = {"external_mount": "/tmp", "run_directory": "/tmp/other/task/run", "run_id": "run",
                     "output": "/tmp/other/task/run/result", "external_device": 0}
            with self.assertRaisesRegex(ValueError, "external route"):
                c.secure_output_dir(wrong)

    def test_claim_and_external_writes_are_exclusive_and_no_follow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c.claim_once(root, "fixed.started.json", {"attempt": 1})
            with self.assertRaises(FileExistsError):
                c.claim_once(root, "fixed.started.json", {"attempt": 2})
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                receipt = c.write_json(fd, "result.json", {"ok": True}, root.stat().st_dev)
                actual = (root / "result.json").read_bytes()
                self.assertEqual(receipt, {"bytes": len(actual), "sha256": hashlib.sha256(actual).hexdigest()})
                with self.assertRaises(FileExistsError):
                    c.write_json(fd, "result.json", {"ok": False}, root.stat().st_dev)
                (root / "link.json").symlink_to(root / "result.json")
                with self.assertRaises((FileExistsError, OSError)):
                    c.write_json(fd, "link.json", {"ok": False}, root.stat().st_dev)
                self.assertEqual(json.loads((root / "result.json").read_text()), {"ok": True})
                with self.assertRaisesRegex(ValueError, "device"):
                    c.write_json(fd, "wrong-device.json", {}, root.stat().st_dev + 1)
            finally:
                os.close(fd)


if __name__ == "__main__":
    unittest.main()
