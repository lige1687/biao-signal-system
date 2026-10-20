import math
import unittest

from lei_signal.research.annual_profitability import operating_profitability_after_da


class AnnualProfitabilityTests(unittest.TestCase):
    def test_negative_operating_profit_is_not_clipped(self):
        self.assertEqual(operating_profitability_after_da(
            -12, 3, 100, financials_qualified=True), -0.15)

    def test_zero_operating_profit_is_valid(self):
        self.assertEqual(operating_profitability_after_da(
            8, 8, 100, financials_qualified=True), 0.0)

    def test_nonpositive_equity_is_rejected(self):
        for equity in (0, -1):
            with self.subTest(equity=equity):
                self.assertIsNone(operating_profitability_after_da(
                    10, 1, equity, financials_qualified=True))

    def test_negative_interest_is_not_treated_as_revenue(self):
        self.assertIsNone(operating_profitability_after_da(
            10, -2, 100, financials_qualified=True))

    def test_missing_nonfinite_boolean_and_unqualified_inputs_rejected(self):
        for values in (
            (None, 1, 100), (1, math.nan, 100), (1, 1, math.inf),
            (True, 1, 100), (1, False, 100), (1, 1, True),
        ):
            with self.subTest(values=values):
                self.assertIsNone(operating_profitability_after_da(
                    *values, financials_qualified=True))
        for flag in (False, 1, "true", None):
            with self.subTest(flag=flag):
                self.assertIsNone(operating_profitability_after_da(
                    10, 1, 100, financials_qualified=flag))

    def test_common_scale_does_not_change_ratio(self):
        base = operating_profitability_after_da(120, 20, 500, financials_qualified=True)
        scaled = operating_profitability_after_da(1200, 200, 5000, financials_qualified=True)
        self.assertEqual(base, scaled)

    def test_interest_is_subtracted_once(self):
        self.assertEqual(operating_profitability_after_da(
            100, 10, 100, financials_qualified=True), 0.9)

    def test_finite_inputs_with_overflowing_result_are_rejected(self):
        for values in ((-1e308, 1e308, 1), (1, 0, 5e-324)):
            with self.subTest(values=values):
                self.assertIsNone(operating_profitability_after_da(
                    *values, financials_qualified=True))


if __name__ == "__main__":
    unittest.main()
