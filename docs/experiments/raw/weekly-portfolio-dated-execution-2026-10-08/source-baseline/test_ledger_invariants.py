import unittest
from copy import deepcopy
from decimal import Decimal as D
from datetime import datetime, timezone
from ledger_invariants import Ledger, fee, require_prior_information, require_later_open


class Invariants(unittest.TestCase):
    def test_shared_cash_cannot_be_spent_twice(self):
        l = Ledger(); l.deposit(D(250), prior_complete_unit_value=D(1))
        l.buy('A', D(100), D(2)); before = deepcopy(l)
        with self.assertRaises(ValueError): l.buy('B', D(100), D(2))
        self.assertEqual(l, before); self.assertEqual(l.cash, D('49.8'))

    def test_exact_affordability_includes_fees(self):
        l = Ledger(); l.deposit(D(200), prior_complete_unit_value=D(1))
        with self.assertRaises(ValueError): l.buy('A', D(100), D(2))
        self.assertEqual(l.cash, D(200)); self.assertEqual(l.shares, {})

    def test_buy_lot_and_closed_market_rejection(self):
        for qty, allowed in [(D(50), True), (D(100), False)]:
            l = Ledger(cash=D(1000)); old = deepcopy(l)
            with self.assertRaises(ValueError): l.buy('A', qty, D(2), allowed=allowed)
            self.assertEqual(l, old)

    def test_new_purchase_not_sellable_same_day(self):
        l = Ledger(cash=D(1000)); l.buy('A', D(100), D(2))
        with self.assertRaises(ValueError): l.sell('A', D(100), D(2))
        l.settle(); l.sell('A', D(100), D(2))
        self.assertEqual(l.shares['A'], 0)

    def test_held_positions_mark_every_day_and_terminal_not_liquidated(self):
        l = Ledger(); l.deposit(D(1000), prior_complete_unit_value=D(1)); l.buy('A', D(100), D(5))
        self.assertEqual(l.equity({'A': D(5)}), D('999.5'))
        self.assertEqual(l.equity({'A': D(4)}), D('899.5'))
        self.assertEqual(l.shares['A'], D(100)); self.assertEqual(l.fees, D('.5'))

    def test_missing_mark_cannot_be_zero_or_implicit_fill(self):
        l = Ledger(shares={'A': D(100)})
        with self.assertRaises(ValueError): l.equity({})
        with self.assertRaises(ValueError): l.equity({'A': None})

    def test_deposit_does_not_create_return(self):
        l = Ledger(); l.deposit(D(1000), prior_complete_unit_value=D(1)); l.buy('A', D(100), D(5), D(0))
        nav = l.equity({'A': D(6)}) / l.units
        l.deposit(D(250), prior_complete_unit_value=nav)
        self.assertAlmostEqual(l.equity({'A': D(6)}) / l.units, nav, places=24)
        self.assertEqual(l.inflows, D(1250))

    def test_dividend_receivable_cannot_be_spent(self):
        l = Ledger(shares={'A': D(100)})
        l.recognize_dividend('div1', D(100), D('.1'))
        self.assertEqual(l.equity({'A': D('4.9')}), D(500))
        with self.assertRaises(ValueError): l.buy('B', D(100), D('.05'), D(0))
        l.pay_dividend('div1'); self.assertEqual(l.cash, D(10))
        self.assertEqual(l.equity({'A': D('4.9')}), D(500))
        with self.assertRaises(ValueError): l.pay_dividend('div1')
        with self.assertRaises(ValueError): l.recognize_dividend('div1', D(100), D('.1'))

    def test_dividend_recorded_entitlement_survives_sale(self):
        l = Ledger(shares={'A': D(100)}, settled={'A': D(100)})
        eligibility = l.shares['A']
        l.sell('A', D(100), D(5), D(0))
        l.recognize_dividend('div2', eligibility, D('.1'))
        self.assertEqual(l.equity({}), D(510))

    def test_split_preserves_value_and_sellable_units(self):
        l = Ledger(cash=D(7), shares={'A': D(100)}, settled={'A': D(100)})
        before = l.equity({'A': D(10)})
        l.split('split1', 'A', D(2))
        self.assertEqual(l.equity({'A': D(5)}), before)
        self.assertEqual(l.settled['A'], D(200))

    def test_commission_floor_separate_from_slippage(self):
        self.assertEqual(fee(D(200), D('.001'), D(5), D('.001')), D('5.2'))

    def test_sale_then_purchase_uses_only_actual_proceeds(self):
        l = Ledger(shares={'A': D(100)}, settled={'A': D(100)})
        with self.assertRaises(ValueError): l.buy('B', D(100), D(1), D(0))
        l.sell('A', D(100), D(2), D(0))
        require_later_open(100, 101)
        l.buy('B', D(100), D(1), D(0))
        self.assertEqual(l.cash, D(100)); self.assertEqual(l.equity({'B': D(1)}), D(200))

    def test_ex_dividend_deposit_uses_complete_prior_unit_value(self):
        l = Ledger(shares={'A': D(100)}, units=D(1000))
        prior_nav = l.equity({'A': D(10)}) / l.units
        # Robust against an already-posted receivable: no mixing with old price.
        l.recognize_dividend('d', D(100), D(1))
        l.deposit(D(100), prior_complete_unit_value=prior_nav)
        self.assertEqual(l.equity({'A': D(9)}) / l.units, D(1))
        self.assertEqual(l.equity({'A': D(9)}), D(1100))

    def test_duplicate_split_rejected_without_state_change(self):
        l = Ledger(shares={'A': D(100)}, settled={'A': D(100)})
        l.split('split1', 'A', D(2)); prior = deepcopy(l)
        with self.assertRaises(ValueError): l.split('split1', 'A', D(2))
        self.assertEqual(l, prior)

    def test_sale_proceeds_cannot_fund_same_open(self):
        with self.assertRaises(ValueError): require_later_open(100, 100)
        with self.assertRaises(ValueError): require_later_open(100, 99)
        require_later_open(100, 101)

    def test_time_order_rejects_lookahead(self):
        a, b, c = [datetime(2026, 1, d, tzinfo=timezone.utc) for d in [2, 3, 5]]
        require_prior_information(a, b, c)
        with self.assertRaises(ValueError): require_prior_information(c, b, c)
        with self.assertRaises(ValueError): require_prior_information(a, b, b)


if __name__ == '__main__': unittest.main()
