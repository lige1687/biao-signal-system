"""Exact >=3 reward/risk boundary tests for twelfth-batch configurations."""
import sys
sys.dont_write_bytecode = True

import unittest

from engine import simulate


def bar(open_price=4.591):
    return dict(open=open_price, close=open_price, high=open_price + .01, low=open_price - .01, volume=1000)


def candidate(signal_ref=4.591, target=4.675):
    return dict(
        candidate_id="boundary", symbol="X", signal_date="2024-01-01",
        signal_ref=signal_ref, stop=4.563, target=target,
        variant="A_repaired_daily", signal_accepted=True,
    )


def run(row, open_price=4.591):
    prices = {"X": {"2023-12-29": bar(), "2024-01-01": bar(), "2024-01-02": bar(open_price)}}
    return simulate(
        prices, [], [row], {"X": {}},
        start="2024-01-01", end="2024-01-02", weekly_per_symbol=5000,
        fee=.001, config_id="A20E", limits={"X": 1.},
        explicit_config_set={"A20E"}, exit_rule=lambda position, observation, close: None,
    )


class ExactBoundaryTests(unittest.TestCase):
    def test_signal_ratio_exactly_three_is_accepted(self):
        result = run(candidate())
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["orders"][0]["signal_rr_recomputed"], 3.0)

    def test_signal_ratio_truly_below_three_is_rejected(self):
        result = run(candidate(target=4.674999))
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["orders"][0]["reason"], "signal_rr_below3")

    def test_open_ratio_exactly_three_is_accepted(self):
        result = run(candidate(signal_ref=4.590))
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["orders"][0]["open_rr"], 3.0)

    def test_open_ratio_truly_below_three_is_rejected(self):
        result = run(candidate(signal_ref=4.590), open_price=4.591001)
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["orders"][0]["reason"], "open_rr_below3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
