import importlib.util
import unittest
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).with_name("qualify_membership.py")
SPEC = importlib.util.spec_from_file_location("qualify_membership", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MembershipRulesTests(unittest.TestCase):
    def test_end_is_exclusive(self):
        rows = [{"ticker": "AAA", "start": date(2020, 1, 1), "end": date(2020, 2, 1)}]
        self.assertEqual(module.ticker_set(module.active_intervals(rows, date(2020, 1, 31))), {"AAA"})
        self.assertEqual(module.active_intervals(rows, date(2020, 2, 1)), [])

    def test_reentry_is_counted_and_overlapping_interval_is_not_reentry(self):
        rows = [
            {"ticker": "AAA", "start": date(2019, 1, 1), "end": date(2020, 1, 1), "interval_id": 0},
            {"ticker": "AAA", "start": date(2020, 1, 1), "end": date(2021, 1, 1), "interval_id": 1},
            {"ticker": "BBB", "start": date(2020, 2, 1), "end": date(2021, 1, 1), "interval_id": 2},
            {"ticker": "BBB", "start": date(2020, 3, 1), "end": date(2021, 2, 1), "interval_id": 3},
        ]
        self.assertEqual(module.annual_interval_reentry_counts(rows, 2020), (3, 1))

    def test_rename_chain_is_transitive_and_cycle_rejected(self):
        self.assertEqual(module.rename_chain("OLD", {"OLD": "MID", "MID": "NEW"}), "NEW")
        with self.assertRaises(ValueError):
            module.rename_chain("A", {"A": "B", "B": "A"})

    def test_snapshot_selection_never_looks_forward(self):
        snapshots = [(date(2020, 1, 1), {"OLD"}), (date(2020, 3, 1), {"FUTURE"})]
        d, members = module.latest_snapshot_before(snapshots, date(2020, 2, 1))
        self.assertEqual(d, date(2020, 1, 1))
        self.assertEqual(members, {"OLD"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
