"""Small synthetic checks; no real monthly quote or return data are read."""

import hashlib
import random
import struct
import unittest

import risk_conditional_followup as risk


def synthetic_monthly(p_values, *, method_value=None):
    rows = []
    for month, p in zip(risk.months()[:len(p_values)], p_values):
        methods = {}
        for method in ("P", "M", "D", "F", "B"):
            value = p if method == "P" else (method_value(method, month) if method_value else 0.0)
            methods[method] = {scenario: value for scenario in risk.SCENARIOS}
        for scope in risk.SCOPES:
            rows.append({"scope": scope, "month": month, "methods": methods})
    return rows


class ConditionalRiskTests(unittest.TestCase):
    def test_strict_negative_p_and_original_denominator(self):
        rows = synthetic_monthly([-0.1, 0.0, 0.3, -0.2],
                                 method_value=lambda method, month: 0.1 if month.endswith("01") else 0.3)
        item = risk.make_series(rows, risk.months()[:4])[("gp", "unknown_zero", "B-P")]
        self.assertEqual(item["p_down_months"], 2)
        self.assertEqual(item["paired_down_months"], 2)
        self.assertAlmostEqual(item["original_difference"], 0.35)
        self.assertIsNone(item["values"][1])
        self.assertIsNone(item["values"][2])

    def test_resampled_denominator_and_repeated_positions(self):
        values = [1.0, None, 9.0, None]
        # Position 0 occurs twice. The denominator is three, not four or two.
        self.assertAlmostEqual(risk._sample_mean(values, [0, 0, 1, 2]), 11 / 3)
        self.assertIsNone(risk._sample_mean(values, [1, 3, 1, 3]))

    def test_circular_wrap_and_shared_original_index_hash(self):
        class Starts:
            def __init__(self): self.values = iter([4, 2])
            def randrange(self, n):
                self_assert = n == 5
                assert self_assert
                return next(self.values)
        self.assertEqual(risk.draw_positions(5, 3, Starts()), [4, 0, 1, 2, 3])
        # These are the original core's saved index digests, with no effect values.
        for block, expected in ((6, "b717407ab8165ec58a25c87210c2faa1741ec01867814ce5e9202f40f0ae7ec7"),
                                (12, "a08ac269b8961267b790b4b721128f3f34b97f19254ab567a0f225afd913f64d")):
            rng = random.Random(risk.SEED)
            digest = hashlib.sha256()
            for _ in range(risk.DRAWS):
                for position in risk.draw_positions(risk.N_MONTHS, block, rng):
                    digest.update(struct.pack(">H", position))
            self.assertEqual(digest.hexdigest(), expected)

    def test_all_up_draw_is_missing_not_zero(self):
        rows = synthetic_monthly([0.0, 0.1, 0.2])
        series = risk.make_series(rows, risk.months()[:3])
        result, _ = risk.calculate(series, n=3, draws=7, blocks=(2,), confidences=(0.95,))
        self.assertEqual(len(result), 30)
        self.assertTrue(all(r["draws_valid"] == 0 and r["lower"] is None and
                            r["upper"] is None and r["status"] == "no_down_month_draws" for r in result))

    def test_constant_difference_degenerate_intervals(self):
        rows = synthetic_monthly([-0.1] * 6, method_value=lambda method, month: 0.2)
        series = risk.make_series(rows, risk.months()[:6])
        result, _ = risk.calculate(series, n=6, draws=20, blocks=(2,), confidences=(0.95, 0.975))
        for row in result:
            if row["comparison"] == "B-M":
                self.assertEqual(row["original_difference"], 0)
                self.assertEqual(row["lower"], 0)
                self.assertEqual(row["upper"], 0)
                self.assertEqual(row["draws_valid"], 20)

    def test_positive_and_negative_paired_controls_on_same_down_dates(self):
        months = risk.months()[:4]
        rows = synthetic_monthly([-0.2, 0.1, -0.1, 0.0])
        for row in rows:
            for scenario in risk.SCENARIOS:
                row["methods"]["B"][scenario] = 0.2 if row["month"] in (months[0], months[2]) else -9.0
                row["methods"]["M"][scenario] = -0.2 if row["month"] in (months[0], months[2]) else 9.0
                row["methods"]["D"][scenario] = 0.4 if row["month"] in (months[0], months[2]) else -9.0
        series = risk.make_series(rows, months)
        self.assertAlmostEqual(series[("gp", "unknown_zero", "B-M")]["original_difference"], 0.4)
        self.assertAlmostEqual(series[("gp", "unknown_zero", "B-D")]["original_difference"], -0.2)

    def test_original_core_count_and_mean_are_independently_checked(self):
        rows = synthetic_monthly([-0.1, 0.2])
        series = risk.make_series(rows, risk.months()[:2])
        paired = [{"scope": scope, "scenario": scenario, "comparison": comparison, "period": "all",
                   "p_down_common_months": item["paired_down_months"],
                   "p_down_common_mean": item["original_difference"]}
                  for (scope, scenario, comparison), item in series.items()]
        uncertainty = [{"block_months": 6, "shared_index_sha256": "a"},
                       {"block_months": 12, "shared_index_sha256": "b"}]
        risk.verify_core(series, paired, uncertainty, {6: "a", 12: "b"})
        paired[0]["p_down_common_months"] += 1
        with self.assertRaises(ValueError):
            risk.verify_core(series, paired, uncertainty, {6: "a", 12: "b"})
        paired[0]["p_down_common_months"] -= 1
        with self.assertRaises(ValueError):
            risk.verify_core(series, paired, uncertainty, {6: "wrong", 12: "b"})


if __name__ == "__main__":
    unittest.main()
