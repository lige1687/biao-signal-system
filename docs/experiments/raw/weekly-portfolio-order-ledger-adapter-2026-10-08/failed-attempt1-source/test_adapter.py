import unittest
from dataclasses import asdict, replace
from decimal import Decimal as D
from order_ledger_adapter import attempt_open, SyntheticAccount
from synthetic_fixtures import *

RECEIPTS = {}


class AdapterChecks(unittest.TestCase):
    def keep(self, **data): RECEIPTS[self.id().split('.')[-1]] = data

    def invoke(self, a, d, p, batch, order):
        return attempt_open(d, p, order, a.opening(order.symbol, OPEN if order.opening_at == planner._v1.at(OPEN) else NEXT),
                            a.ledger, batch)

    def test_two_valid_buys_exact_fees(self):
        a, d, p = make(); batch = a.begin(d, p)
        receipts = [self.invoke(a, d, p, batch, o) for o in p.orders]
        self.assertEqual([r.status for r in receipts], ['filled', 'filled'])
        self.assertEqual(a.ledger.snapshot()['cash'], D('.10'))
        self.assertEqual(a.ledger.snapshot()['fees'], D('10.40'))
        self.assertEqual((a.ledger.shares('A'), a.ledger.shares('B')), (100, 100))
        self.assertEqual([r.ledger_apply_count for r in receipts], [1, 1])
        self.keep(plan=asdict(p), attempts=[asdict(r) for r in receipts])

    def test_first_over_cap_second_budget_unchanged(self):
        a, d, p = make(calendar(first_price='2.001')); batch = a.begin(d, p)
        first = self.invoke(a, d, p, batch, p.orders[0])
        self.assertEqual(first.status, 'refused'); self.assertEqual(first.ledger_apply_count, 0)
        self.assertTrue(first.ledger_state_unchanged); self.assertEqual(a.ledger.snapshot()['cash'], D('410.50'))
        second = self.invoke(a, d, p, batch, p.orders[1])
        self.assertEqual(second.status, 'filled'); self.assertEqual(second.quantity, 100)
        self.assertEqual(a.ledger.snapshot()['cash'], D('205.30'))
        self.keep(plan=asdict(p), attempts=[asdict(first), asdict(second)])

    def test_sell_then_explicit_release_then_later_buy(self):
        a, d, p = make(sell=True); batch = a.begin(d, p)
        sale = self.invoke(a, d, p, batch, p.orders[0]); self.assertEqual(sale.status, 'filled')
        self.assertEqual(a.ledger.snapshot()['cash'], 200)
        self.assertEqual(sale.after['restricted_cash'], '174.82')
        r = a.sale_result(sale)
        with self.assertRaises(ValueError): a.cash_snapshot(at=OPEN, includes_sale_receipt=r.receipt_id)
        before_release = a.ledger.snapshot()
        a.apply_calendar_event({'kind': 'advance', 'id': 'explicit-sale-release-Jan6', 'at': PAY, 'phase': 3})
        snap = a.cash_snapshot(at=PAY, includes_sale_receipt=r.receipt_id)
        self.assertEqual(snap.amount, D('374.82'))
        q = planner.later_buys(d, p, r, current_cash=snap, frozen_at=NEXTFREEZE, opening_at=NEXT)
        later_batch = a.begin(d, q)
        buy = self.invoke(a, d, q, later_batch, q.orders[0]); self.assertEqual(buy.status, 'filled')
        self.assertEqual(buy.quantity, 300); self.assertEqual(a.ledger.snapshot()['cash'], D('69.52'))
        self.assertEqual(a.ledger.snapshot()['fees'], D('10.48'))
        self.keep(sale_plan=asdict(p), sale=asdict(sale), restricted_before_release=before_release,
                  release=a.calendar_events, current_cash=asdict(snap), later_plan=asdict(q), buy=asdict(buy))

    def test_replay_success_and_reject_have_no_second_effect(self):
        a, d, p = make(); batch = a.begin(d, p); o = p.orders[0]
        first = self.invoke(a, d, p, batch, o); state = a.ledger.snapshot()
        replay = self.invoke(a, d, p, batch, o)
        self.assertEqual(replay.status, 'replay_ignored'); self.assertEqual(state, a.ledger.snapshot())
        self.assertEqual(replay.ledger_apply_count, 0); self.assertEqual(first.event_id, replay.event_id)
        b, x, q = make(calendar(first_price='2.001')); context = b.begin(x, q)
        reject = self.invoke(b, x, q, context, q.orders[0]); same = b.ledger.snapshot()
        second = self.invoke(b, x, q, context, q.orders[0])
        self.assertEqual(second.status, 'replay_ignored'); self.assertEqual(same, b.ledger.snapshot())
        self.keep(success=asdict(first), success_replay=asdict(replay), refusal=asdict(reject), refusal_replay=asdict(second))

    def test_wrong_cost_plan_calendar_and_external_ledger_refused(self):
        results = []
        for variant in ('cost', 'plan', 'calendar', 'ledger', 'quantity'):
            a, d, p = make(); batch = a.begin(d, p); o = p.orders[0]; evidence = a.opening(o.symbol, OPEN)
            actual_d, actual_p, actual_o, ledger = d, p, o, a.ledger
            if variant == 'cost': actual_d = replace(d, costs=planner.Costs(0, 0, 0, 'other'))
            if variant == 'plan': actual_p = replace(p, plan_hash='another')
            if variant == 'calendar': evidence = replace(evidence, calendar_hash='another')
            if variant == 'ledger': ledger = make()[0].ledger
            if variant == 'quantity': actual_o = replace(o, quantity=D(50))
            before = a.ledger.snapshot()
            r = attempt_open(actual_d, actual_p, actual_o, evidence, ledger, batch)
            self.assertEqual(r.status, 'refused'); self.assertEqual(r.ledger_apply_count, 0)
            self.assertEqual(a.ledger.snapshot(), before); results.append(asdict(r))
        self.keep(refusals=results)

    def test_outside_cash_or_sellable_change_stops_batch(self):
        results = []
        for sell in (False, True):
            a, d, p = make(sell=sell); batch = a.begin(d, p)
            # Explicit negative test mutation, never an adapter-supported outflow.
            if sell: a.ledger._state['lots'][0]['qty'] = D(50)
            else: a.ledger._state['cash'] = D(0)
            before = a.ledger.snapshot(); r = self.invoke(a, d, p, batch, p.orders[0])
            self.assertEqual(r.status, 'refused'); self.assertIn('outside ledger change', r.reason)
            self.assertEqual(before, a.ledger.snapshot()); self.assertTrue(batch.stopped)
            results.append(asdict(r))
        self.keep(outside_change_refusals=results)

    def test_calendar_due_action_ledger_refusal_atomic(self):
        c = calendar(sell=True)
        c['actions']['unposted-known-before-decision'] = {'symbol': 'A', 'split_at': '2026-01-01T14:00:00+08:00', 'multiplier': D(2)}
        a, d, p = make(c, sell=True); batch = a.begin(d, p); before = a.ledger.snapshot()
        r = self.invoke(a, d, p, batch, p.orders[0])
        self.assertEqual(r.status, 'refused'); self.assertEqual(r.ledger_apply_count, 1)
        self.assertIn('required due action missing', r.reason); self.assertEqual(before, a.ledger.snapshot())
        self.keep(atomic_ledger_refusal=asdict(r))

    def test_hidden_calendar_action_crossing_or_halt_refused(self):
        c = calendar(); c['actions']['crossing'] = {'symbol': 'A', 'split_at': FREEZE, 'multiplier': D(2)}
        a, d, p = make(c); batch = a.begin(d, p); r = self.invoke(a, d, p, batch, p.orders[0])
        self.assertEqual(r.status, 'refused'); self.assertEqual(r.ledger_apply_count, 0)
        self.assertIn('crossing', r.reason)
        c = calendar(); c['opens'][OPEN]['A']['buy'] = False
        b, x, q = make(c); context = b.begin(x, q); halt = self.invoke(b, x, q, context, q.orders[0])
        self.assertEqual(halt.status, 'refused'); self.assertTrue(halt.ledger_state_unchanged)
        self.keep(hidden_crossing=asdict(r), halt=asdict(halt))

    def test_unknown_coverage_pending_branch_and_parallel_batch_unsupported(self):
        a, d, p = make(); batch = a.begin(d, p)
        with self.assertRaises(ValueError): a.begin(d, p)
        unknown = planner.plan_p0(d, current_cash=p.current_cash,
                                  action_context=replace(p.action_context, covered_through=planner._v1.at(FREEZE)),
                                  frozen_at=FREEZE, opening_at=OPEN)
        b, x, original = make()
        # Reuse matching current-account decision for explicit unsupported plan.
        unknown_b = planner.plan_p0(x, current_cash=original.current_cash,
                                    action_context=replace(original.action_context, covered_through=planner._v1.at(FREEZE)),
                                    frozen_at=FREEZE, opening_at=OPEN)
        with self.assertRaises(ValueError): b.begin(x, unknown_b)
        c = calendar(sell=True); small = SyntheticAccount('small', c, initial_at=KNOWN, cash=0,
                lots=[{'symbol': 'A', 'qty': D(60), 'release_at': KNOWN}, {'symbol': 'B', 'qty': D(40), 'release_at': KNOWN}],
                marks={'A': D(2), 'B': D(2)})
        sd, snap = small.decision(name='small-pending', decision_at=DEC, reference_known_at=KNOWN,
                                 references={'A': 2, 'B': 2}, costs=COSTS)
        sp = planner.plan_p1(sd, current_cash=snap, action_context=p.action_context, frozen_at=FREEZE, opening_at=OPEN)
        self.assertEqual(sp.reason, 'triggered_no_sellable_whole_lot_pending_user')
        with self.assertRaises(ValueError): small.begin(sd, sp)
        self.keep(unknown=asdict(unknown), pending=asdict(sp), parallel_batch_refused=True)

    def test_release_payment_distinct_no_fabricated_deposit_or_foreign_cash(self):
        a, d, p = make()
        with self.assertRaises(ValueError): a.apply_calendar_event({'kind': 'deposit', 'id': 'fake', 'at': OPEN, 'amount': 1000})
        with self.assertRaises(ValueError): a.cash_snapshot(at=OPEN)
        other, _, _ = make(); snap = other.cash_snapshot(at=KNOWN)
        foreign = replace(snap, source_id='foreign-account-source')
        forged = planner.plan_p0(d, current_cash=foreign, action_context=p.action_context, frozen_at=FREEZE, opening_at=OPEN)
        with self.assertRaises(ValueError): a.begin(d, forged)
        self.keep(fabricated_deposit_refused=True, future_cash_clock_refused=True, foreign_cash_refused=True)

    def test_frozen_serial_order_no_reshuffling(self):
        a, d, p = make(); batch = a.begin(d, p); before = a.ledger.snapshot()
        r = self.invoke(a, d, p, batch, p.orders[1])
        self.assertEqual(r.status, 'refused'); self.assertIn('serial order', r.reason)
        self.assertEqual(before, a.ledger.snapshot()); self.keep(out_of_sequence=asdict(r))


if __name__ == '__main__': unittest.main()
