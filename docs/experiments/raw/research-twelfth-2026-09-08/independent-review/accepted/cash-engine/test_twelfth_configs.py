"""Contract tests for the twelfth-batch explicit configurations."""
import sys
sys.dont_write_bytecode = True

import unittest

from engine import simulate


TWELFTH = {
    "A20E", "A20J", "A60E", "A60J", "A120E", "A120J",
    "C1", "C2", "C3", "D", "REF_BREAKOUT", "REF_ROAD",
}


def bar(open=1.0, close=None):
    close = open if close is None else close
    return {
        "open": open,
        "close": close,
        "high": max(open, close) + 0.02,
        "low": min(open, close) - 0.02,
        "volume": 1000,
    }


def fixture():
    prices = {
        "X": {
            "2023-12-29": bar(),
            **{f"2024-01-{day:02d}": bar() for day in [1, 2, 3, 4, 5, 8, 9, 10]},
        }
    }
    observations = {"X": {day: {} for day in prices["X"]}}
    return prices, observations


def candidate(candidate_id="first", signal_date="2024-01-01", **changes):
    row = {
        "candidate_id": candidate_id,
        "symbol": "X",
        "signal_date": signal_date,
        "signal_ref": 1.0,
        "stop": 0.9,
        "target": 1.6,
        "variant": "A_repaired_daily",
        "signal_accepted": True,
    }
    row.update(changes)
    return row


def run(config_id, candidates=None, weekly_per_symbol=2500):
    prices, observations = fixture()
    return simulate(
        prices,
        [],
        [candidate()] if candidates is None else candidates,
        observations,
        start="2024-01-01",
        end="2024-01-10",
        weekly_per_symbol=weekly_per_symbol,
        fee=0.001,
        config_id=config_id,
        limits={"X": 1.0},
        explicit_config_set=TWELFTH,
        exit_rule=lambda position, observation, close: None,
    )


class TwelfthConfigContract(unittest.TestCase):
    def test_new_config_is_rejected_without_explicit_set(self):
        prices, observations = fixture()
        with self.assertRaisesRegex(ValueError, "Unknown configuration"):
            simulate(
                prices, [], [candidate()], observations,
                start="2024-01-01", end="2024-01-10", fee=0.001,
                config_id="A20E", limits={"X": 1.0},
                exit_rule=lambda position, observation, close: None,
            )

    def test_all_explicit_configs_use_previous_equity_one_percent_budget(self):
        for config_id in sorted(TWELFTH):
            with self.subTest(config_id=config_id):
                result = run(config_id)
                self.assertEqual(len(result["trades"]), 1)
                trade = result["trades"][0]
                self.assertEqual(trade["shares"], 200)
                self.assertEqual(trade["previous_product_equity"], 2500)
                self.assertEqual(trade["risk_budget"], 25)

    def test_non_breakout_variant_is_not_subject_to_p7_b_lock(self):
        result = run("A20E")
        self.assertEqual(result["trades"][0]["candidate_id"], "first")

    def test_later_candidate_cannot_move_open_position_stop(self):
        result = run("C1", [
            candidate("first", stop=0.9),
            candidate("later", signal_date="2024-01-02", stop=0.5, target=3.0),
        ])
        self.assertEqual(len(result["roundtrips"]), 1)
        self.assertEqual(result["roundtrips"][0]["initial_stop"], 0.9)
        self.assertEqual(result["roundtrips"][0]["stop"], 0.9)
        later = next(order for order in result["orders"] if order.get("candidate_id") == "later")
        self.assertEqual(later["reason"], "position_exists")


if __name__ == "__main__":
    unittest.main(verbosity=2)
