"""Unit tests for account/exit_path invariants in atr_opportunity_study.

Uses only stdlib unittest + pandas/numpy.
"""

import importlib.util
import math
from pathlib import Path
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parent


def _load_module():
    path = ROOT.parent / "atr_opportunity_study.py"
    spec = importlib.util.spec_from_file_location("atr_opportunity_study", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # no-op main because __name__ guard in module
    return mod


class TestAtrAccount(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def _sell_rate(self, fee: str, ep: float) -> float:
        if fee == "legacy":
            return max(0.0005, 0.005 / ep)
        if fee == "amount_5bp":
            return 0.0005
        return 0.001

    def _bars(self, closes, opens, trend_exit=False):
        return pd.DataFrame({
            "close": list(map(float, closes)),
            "open": list(map(float, opens)),
            "trend_exit": [bool(trend_exit)] * len(closes),
        })

    def _fee_rates(self):
        return ("legacy", "amount_5bp", "amount_10bp")

    def test_1_initial_cash_is_non_negative_after_entry_fee(self):
        ep = 100.0
        stop = 90.0
        for fee in self._fee_rates():
            for sizing in ("same_budget", "same_planned_risk"):
                with self.subTest(fee=fee, sizing=sizing):
                    out = self.mod.account(ep=ep, stop=stop, price=ep, minimum_close=ep, closed=False,
                                           fee=fee, sizing=sizing)
                    self.assertGreaterEqual(out["cash_after_entry"], -1e-12)

    def test_2_flat_price_closed_only_loses_entry_and_exit_fees(self):
        ep = 100.0
        stop = 90.0
        for fee in self._fee_rates():
            with self.subTest(fee=fee):
                out = self.mod.account(ep=ep, stop=stop, price=ep, minimum_close=ep, closed=True,
                                       fee=fee, sizing="same_budget")
                buy_rate = self._sell_rate(fee, ep)
                q = out["quantity_proxy"]
                sell_rate = self._sell_rate(fee, ep)
                expected = -(q * ep * (buy_rate + sell_rate))
                self.assertLess(out["budget_return"], 0.0)
                self.assertAlmostEqual(out["budget_return"], expected, delta=1e-12)
                self.assertAlmostEqual(out["fees_fraction"], q * ep * (buy_rate + sell_rate), delta=1e-12)

    def test_3_planned_one_percent_risk_is_bounded_no_leverage(self):
        ep = 100.0
        stop = ep * 0.99  # 1% risk
        for fee in self._fee_rates():
            with self.subTest(fee=fee):
                out = self.mod.account(ep=ep, stop=stop, price=ep * 0.99, minimum_close=ep * 0.99, closed=False,
                                       fee=fee, sizing="same_planned_risk")
                buy_rate = self._sell_rate(fee, ep)
                qmax = 1.0 / (ep * (1 + buy_rate))
                q_risk = min(qmax, 0.01 / (ep - stop))
                self.assertLessEqual(q_risk * ep, 1.0 + 1e-12)
                self.assertAlmostEqual(out["position_fraction"], q_risk * ep, delta=1e-12)
                self.assertLessEqual(out["planned_loss_fraction"], 0.010000001)
                self.assertGreaterEqual(out["cash_after_entry"], -1e-12)

    def test_3b_small_risk_does_not_leverage_infinitely(self):
        ep = 100.0
        stop = ep - 0.0001  # 极小风险
        out = self.mod.account(ep=ep, stop=stop, price=ep, minimum_close=ep, closed=False,
                               fee="legacy", sizing="same_planned_risk")
        self.assertLessEqual(out["position_fraction"], 1.0 + 1e-12)
        self.assertGreaterEqual(out["cash_after_entry"], -1e-12)

    def test_4_gap_can_make_drawdown_exceed_planned_risk(self):
        ep = 100.0
        stop = 90.0
        # minimum_close far below stop: risk on paper should exceed planned 1% risk
        out = self.mod.account(ep=ep, stop=stop, price=20.0, minimum_close=20.0, closed=True,
                               fee="legacy", sizing="same_planned_risk")
        self.assertAlmostEqual(out['planned_loss_fraction'], .01)
        self.assertLess(out['budget_return'], -.08)
        self.assertLess(out["minimum_budget_return"], -out["planned_loss_fraction"] - 1e-6)

    def test_5_no_exit_fee_when_not_closed(self):
        ep = 100.0
        stop = 90.0
        price = ep
        for fee in self._fee_rates():
            with self.subTest(fee=fee):
                out = self.mod.account(ep=ep, stop=stop, price=price, minimum_close=price, closed=False,
                                       fee=fee, sizing="same_budget")
                buy_rate = self._sell_rate(fee, ep)
                self.assertAlmostEqual(out["fees_fraction"], out["quantity_proxy"] * ep * buy_rate, delta=1e-12)

    def test_6_cn_limit_open_uses_next_open_after_trigger_close(self):
        ep = 100.0
        stop = 90.0
        bars = self._bars(
            closes=[100, 120, 80, 80, 80],
            opens=[100, 120, 60, 70, 88],  # 60<=9.5% down from 80 so blocked, then 88>85.5 on next day executes
        )
        out = self.mod.exit_path(bars, entry_pos=0, stop=stop, cn=True)
        self.assertTrue(out["closed"])
        self.assertEqual(out["exit_pos"], 4)
        self.assertEqual(out["reason"], "structure_stop_C")
        bars.loc[4, 'close'] = -1000  # unavailable future close must not affect open fill
        again = self.mod.exit_path(bars, entry_pos=0, stop=stop, cn=True)
        self.assertEqual(again, out)

    def test_7_exit_after_signal_uses_next_open_not_same_day_close(self):
        ep = 100.0
        stop = 90.0
        bars = self._bars(
            closes=[100, 100, 80, 100],
            opens=[100, 100, 95, 90],  # signal at index2 close 80, next index open 90 should execute
        )
        out = self.mod.exit_path(bars, entry_pos=1, stop=stop, cn=False)
        self.assertTrue(out["closed"])
        self.assertEqual(out["exit_pos"], 3)
        self.assertNotEqual(out["exit_pos"], 2)

    def test_8_missing_next_open_cannot_jump_to_other_day(self):
        bars = self._bars(
            closes=[100, 80, 80],
            opens=[100, 79, math.nan],
        )
        out = self.mod.exit_path(bars, entry_pos=0, stop=90.0, cn=True)
        self.assertFalse(out["closed"])
        self.assertIsNone(out["exit_pos"])
        self.assertEqual(out["reason"], "missing_next_open_no_execution")


if __name__ == "__main__":
    unittest.main()
