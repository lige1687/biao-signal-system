import unittest
from dataclasses import replace, asdict, FrozenInstanceError
from decimal import Decimal as D
from order_planning_v2 import *

KNOWN = '2026-01-01T15:00:00+08:00'
DECISION = '2026-01-01T16:00:00+08:00'
FREEZE = '2026-01-02T08:00:00+08:00'
OPEN = '2026-01-02T09:30:00+08:00'
PAY = '2026-01-06T10:00:00+08:00'
NEXTFREEZE = '2026-01-07T08:00:00+08:00'
NEXT = '2026-01-07T09:30:00+08:00'
FLOOR = Costs('.001', 5, '.001', 'synthetic-floor5')
ZERO = Costs(0, 0, 0, 'synthetic-zero')
RECEIPTS = {}


def decision(free=200, held=(350, 100), prices=(2, 1), sellable=(100, 100), c=FLOOR):
    assets = tuple(Asset(s, prices[i], KNOWN, held[i], sellable[i])
                   for i, s in enumerate(('A', 'B')))
    return Decision('synthetic-v2-two-products', DECISION, KNOWN, KNOWN,
                    free, 0, 0, assets, c)


def actions(events=(), end=NEXT, source='synthetic-covered-actions'):
    return ActionContext('invented-covered-action-calendar', source, KNOWN, KNOWN, end, events)


def cash(amount, included=False, receipt=None, initial=False, source='synthetic-current-cash'):
    clock = KNOWN if initial else PAY
    return CashSnapshot('invented-allocatable-cash', source, amount, clock, clock, included, receipt)


def sale(d=None, context=None):
    d = d or decision()
    return plan_p1(d, current_cash=cash(d.free, initial=True),
                   action_context=context or actions(), frozen_at=FREEZE, opening_at=OPEN)


def result(p, price='1.8', receipt='synthetic-sale-high'):
    return SaleResult(p.orders[0].order_id, 'filled', 100, price, OPEN, PAY, receipt)


class Repairs(unittest.TestCase):
    def keep(self, **fields):
        RECEIPTS[self.id().split('.')[-1]] = fields

    def test_current_cash_outflow_not_old_free(self):
        d = decision(); p = sale(d); r = result(p)
        now = cash('174.82', True, r.receipt_id)
        q = later_buys(d, p, r, current_cash=now, frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(q.orders[0].budget, D('174.82'))
        self.assertEqual(q.orders[0].quantity, 100)
        self.assertEqual(cost(100, 1, d.costs), D('105.1'))
        self.assertLessEqual(cost(100, 1, d.costs), now.amount)
        self.keep(decision=asdict(d), sale=asdict(p), receipt=asdict(r), cash=asdict(now), plan=asdict(q))

    def test_cash_excluding_proceeds_add_once_and_included_never_twice(self):
        d = decision(); p = sale(d); r = result(p)
        a = later_buys(d, p, r, current_cash=cash(0), frozen_at=NEXTFREEZE, opening_at=NEXT)
        b = later_buys(d, p, r, current_cash=cash('174.82', True, r.receipt_id),
                       frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(a.budgets, b.budgets); self.assertEqual(a.orders[0].quantity, 100)
        self.assertNotEqual(a.plan_hash, b.plan_hash)
        legal = later_buys(d, p, r, current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(legal.orders[0].budget, D('374.82'))
        self.assertEqual(legal.orders[0].quantity, 300)
        self.assertEqual(cost(300, 1, d.costs), D('305.3'))
        self.keep(excluding=asdict(a), included=asdict(b), original_legal_path=asdict(legal))

    def test_missing_future_or_wrong_receipt_cash_refused(self):
        d = decision(); p = sale(d); r = result(p)
        with self.assertRaises(TypeError):
            later_buys(d, p, r, frozen_at=NEXTFREEZE, opening_at=NEXT)
        with self.assertRaises(ValueError):
            later_buys(d, p, r, current_cash=cash('174.82', True, 'wrong'),
                       frozen_at=NEXTFREEZE, opening_at=NEXT)
        with self.assertRaises(ValueError):
            later_buys(d, p, r, current_cash=replace(cash(0), available_at=r.proceeds_available_at.replace(day=8)),
                       frozen_at=NEXTFREEZE, opening_at=NEXT)
        with self.assertRaises(ValueError):
            CashSnapshot('n', 's', 0, PAY, PAY, True, None)
        self.keep(missing_cash_refused=True, future_cash_refused=True, wrong_inclusion_refused=True)

    def test_plan_identity_binds_cash_receipt_and_contents(self):
        d = decision(); p = sale(d); high = result(p); low = result(p, '.5', 'synthetic-sale-low')
        a = later_buys(d, p, high, current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT)
        b = later_buys(d, p, low, current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(a.decision_hash, b.decision_hash)
        self.assertNotEqual(a.plan_hash, b.plan_hash); self.assertNotEqual(a.orders[0].order_id, b.orders[0].order_id)
        self.assertEqual((a.orders[0].quantity, a.orders[0].cap), (D(300), D('1.231')))
        self.assertEqual((b.orders[0].quantity, b.orders[0].cap), (D(200), D('1.198')))
        other = later_buys(d, p, replace(high, receipt_id='same-money-other-receipt'), current_cash=cash(200),
                           frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertNotEqual(a.plan_hash, other.plan_hash)
        other = later_buys(d, p, high, current_cash=cash(200, source='another-cash-source'),
                           frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertNotEqual(a.plan_hash, other.plan_hash)
        with self.assertRaises(ValueError):
            validate_opening_order(a, b.orders[0], opening_at=NEXT, price=1, eligible=True)
        self.keep(high=asdict(a), low=asdict(b), different_source=asdict(other))

    def test_freeze_and_action_coverage_in_plan_identity(self):
        d = decision(); p = sale(d); r = result(p)
        a = later_buys(d, p, r, current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT)
        b = later_buys(d, p, r, current_cash=cash(200), frozen_at='2026-01-07T08:01:00+08:00', opening_at=NEXT)
        self.assertNotEqual(a.plan_hash, b.plan_hash)
        initial_a = sale(d, actions(source='source-A'))
        initial_b = sale(d, actions(source='source-B'))
        self.assertNotEqual(initial_a.plan_hash, initial_b.plan_hash)
        self.assertNotEqual(initial_a.orders[0].order_id, initial_b.orders[0].order_id)
        self.keep(first=asdict(a), later_freeze=asdict(b))

    def test_known_action_inherited_cannot_be_omitted(self):
        d = decision(); context = actions(('2026-01-06T08:00:00+08:00',)); p = sale(d, context)
        self.assertEqual(p.status, 'await_sale')
        q = later_buys(d, p, result(p), current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(q.status, 'unsupported'); self.assertEqual(q.reason, 'unsupported_company_action_crossing')
        self.assertEqual(q.action_context, p.action_context); self.assertEqual(q.orders, ())
        with self.assertRaises(TypeError):
            later_buys(d, p, result(p), current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT, actions=())
        with self.assertRaises(FrozenInstanceError):
            p.action_context.events = ()
        self.keep(initial=asdict(p), later=asdict(q), omission_override_refused=True)

    def test_missing_action_coverage_unknown_and_explicit_empty_valid(self):
        d = decision()
        with self.assertRaises(TypeError):
            plan_p1(d, current_cash=cash(200, initial=True), frozen_at=FREEZE, opening_at=OPEN)
        p = sale(d, actions(end=OPEN)); self.assertEqual(p.status, 'await_sale')
        q = later_buys(d, p, result(p), current_cash=cash(200), frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(q.reason, 'unsupported_action_coverage_unknown')
        good = sale(d, actions()); good_buy = later_buys(d, good, result(good), current_cash=cash(200),
                                                      frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(good_buy.status, 'ready')
        self.keep(short_coverage=asdict(q), fully_covered_empty=asdict(good_buy))

    def test_related_original_arithmetic_and_p0_snapshot(self):
        self.assertEqual(affordable_quantity(205, 2, FLOOR), 0)
        self.assertEqual(affordable_quantity('205.2', 2, FLOOR), 100)
        self.assertEqual(price_cap('205.25', 100, FLOOR), D('2.000'))
        c = Costs('.01', 1, '.005', 'synthetic-variable')
        self.assertEqual(price_cap(500, 200, c), D('2.463'))
        self.assertEqual(cost(200, '2.464', c), D('500.192'))
        d = decision(free=250, held=(0, 0), prices=(1, 1), sellable=(0, 0), c=ZERO)
        p = plan_p0(d, current_cash=cash(250, initial=True), action_context=actions(),
                    frozen_at=FREEZE, opening_at=OPEN)
        self.assertEqual(p.budgets, (('A', D(125)), ('B', D(125))))
        self.assertEqual(tuple(o.quantity for o in p.orders), (100, 100))
        self.assertEqual(validate_opening_order(p, p.orders[0], opening_at=OPEN, price='1.251', eligible=True),
                         'reject_no_resize')
        self.keep(p0=asdict(p), retained_exact_arithmetic=True)

    def test_related_same_open_unavailable_partial_and_pending_branch(self):
        d = decision(); p = sale(d); r = result(p)
        with self.assertRaises(ValueError):
            later_buys(d, p, r, current_cash=cash(200), frozen_at=FREEZE, opening_at=OPEN)
        q = later_buys(d, p, replace(r, status='partial', quantity=D(50)), current_cash=cash(200),
                       frozen_at=NEXTFREEZE, opening_at=NEXT)
        self.assertEqual(q.status, 'unsupported'); self.assertEqual(q.orders, ())
        small = decision(free=0, held=(60, 40), prices=(2, 2), sellable=(60, 40))
        wait = sale(small)
        self.assertEqual(wait.reason, 'triggered_no_sellable_whole_lot_pending_user')
        self.keep(partial=asdict(q), pending_user=asdict(wait), same_open_refused=True)


if __name__ == '__main__':
    unittest.main()
