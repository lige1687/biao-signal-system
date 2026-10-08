import unittest
from copy import deepcopy
from decimal import Decimal as D
from dated_ledger import fee, require_prior_information
from synthetic_fixtures import *

TRACES = {}


class Checks(unittest.TestCase):
    def keep(self, l):
        TRACES[self.id().split('.')[-1]] = deepcopy(l.audit)

    def reject(self, l, e):
        before = l.snapshot()
        with self.assertRaises(ValueError):
            l.apply(e)
        self.assertEqual(before, l.snapshot())
        self.assertTrue(l.audit[-1]['money_state_unchanged'])

    # Applicable original 16 assertions, migrated to the supported dated API.
    def test_01_shared_cash_cannot_be_spent_twice(self):
        l = ledger(cash=250)
        l.apply(event('buy','a',symbol='A',qty=100))
        self.reject(l,event('buy','b',symbol='B',qty=100))
        self.assertEqual(l.snapshot()['cash'],D('49.8')); self.keep(l)

    def test_02_exact_affordability_includes_fees(self):
        l=ledger(cash=200); self.reject(l,event('buy','a',symbol='A',qty=100))
        self.assertEqual(l.shares('A'),0); self.keep(l)

    def test_03_buy_lot_and_closed_market(self):
        l=ledger(cash=1000)
        self.reject(l,trade('buy','odd',qty=50)); self.reject(l,trade('buy','closed',HOLIDAY))
        self.keep(l)

    def test_04_new_purchase_not_sellable_same_day(self):
        l=ledger(cash=1000); l.apply(trade('buy','b'))
        self.reject(l,trade('sell','s'))
        l.apply(trade('sell','s2',NEXT)); self.assertEqual(l.shares('A'),0); self.keep(l)

    def test_05_marks_and_terminal_not_liquidated(self):
        l=ledger(cash=1000,c=calendar(price=5),marks={'A':D(5)})
        l.apply(event('buy','b',symbol='A',qty=100))
        self.assertEqual(l.equity({'A':D(5)}),D('999.5'))
        self.assertEqual(l.equity({'A':D(4)}),D('899.5'))
        self.assertEqual(l.shares('A'),100); self.keep(l)

    def test_06_unknown_mark_rejected(self):
        c=calendar(); c['closes'][CLOSE]={}
        l=ledger(lots=[lot()],c=c)
        self.reject(l,event('close','c',CLOSE))
        for prices in ({},{'A':None},{'A':0}):
            with self.assertRaises(ValueError): l.equity(prices)
        self.keep(l)

    def test_07_deposit_does_not_create_return(self):
        c=calendar(price=6); l=ledger(cash=500,lots=[lot()],c=c,marks={'A':D(6)})
        l.apply(event('close','c',CLOSE)); nav=l.snapshot()['prior_complete']['nav']
        l.apply(event('deposit','dep',t(3,'00:00:00'),amount=250))
        self.assertAlmostEqual(l.equity({'A':D(6)})/l.snapshot()['units'],nav,places=24)
        self.assertEqual(l.snapshot()['inflows'],250); self.keep(l)

    def test_08_dividend_receivable_cannot_be_spent(self):
        c=calendar(price='.05'); dividend(c,mark='1.9')
        l=ledger(lots=[lot()],c=c)
        l.apply(event('dividend','rec',ACTION,action_id='d'))
        self.assertEqual(l.equity({'A':D('1.9')}),200)
        # An unpaid receivable remains unpaid even after its clock until payment event.
        self.reject(l,trade('buy','b',symbol='B'))
        # Pay on another independent replay, before trade stage.
        q=ledger(lots=[lot()],c=c); q.apply(event('dividend','r',ACTION,action_id='d'))
        q.apply(event('pay','p',PAY,action_id='d'))
        self.assertEqual(q.snapshot()['cash'],10); self.assertEqual(q.equity({'A':D('1.9')}),200)
        self.reject(q,event('pay','p2',PAY,action_id='d')); self.keep(q)

    def test_09_entitlement_survives_sale(self):
        c=calendar(); dividend(c,recognize=t(6,'08:00:00'),pay=t(6,'09:00:00'))
        l=ledger(lots=[lot()],c=c); l.apply(trade('sell','s'))
        l.apply(event('dividend','r',t(6,'08:00:00'),action_id='d'))
        self.assertEqual(l.equity({}),210); self.keep(l)

    def test_10_split_preserves_value_and_sellable(self):
        c=calendar(price=5); split(c)
        l=ledger(cash=7,lots=[lot()],c=c,marks={'A':D(10)})
        before=l.equity({'A':D(10)}); l.apply(event('split','sp',ACTION,action_id='s'))
        self.assertEqual(l.equity({'A':D(5)}),before); self.assertEqual(l.sellable('A',O),200)
        self.keep(l)

    def test_11_commission_floor_and_slippage(self):
        self.assertEqual(fee(D(200),D('.001'),D(5),D('.001')),D('5.2'))

    def test_12_sale_then_purchase_actual_proceeds(self):
        l=ledger(lots=[lot()]); self.reject(l,trade('buy','b',symbol='B'))
        l.apply(trade('sell','s')); l.apply(trade('buy','b2',NEXT,symbol='B'))
        self.assertEqual(l.snapshot()['cash'],0); self.assertEqual(l.equity({'B':D(2)}),200)
        self.keep(l)

    def test_13_ex_dividend_deposit_prior_complete_nav(self):
        c=calendar(price=10); dividend(c,qty=100,per=1,mark=9)
        l=ledger(lots=[lot()],c=c,marks={'A':D(10)},nav=1)
        l.apply(event('deposit','dep',MID,amount=100))
        l.apply(event('dividend','d',ACTION,action_id='d'))
        self.assertEqual(l.equity({'A':D(9)}),1100)
        self.assertEqual(l.equity({'A':D(9)})/l.snapshot()['units'],1)
        # Historical wrong mixture: (1000 old marks +100 today's receivable)/1000=1.1
        wrong_units=D(1000)+D(100)/D('1.1')
        self.assertNotEqual(D(1100)/wrong_units,D(1)); self.keep(l)

    def test_14_duplicate_split_atomic(self):
        c=calendar(); split(c); l=ledger(lots=[lot()],c=c)
        l.apply(event('split','s',ACTION,action_id='s'))
        self.reject(l,event('split','new-id',ACTION,action_id='s')); self.keep(l)

    def test_15_sale_proceeds_same_open_forbidden(self):
        l=ledger(lots=[lot()]); l.apply(trade('sell','s'))
        self.reject(l,trade('buy','b',symbol='B'))
        self.assertEqual(l.snapshot()['cash'],0); self.assertEqual(l.equity({}),200); self.keep(l)

    def test_16_time_order_and_information(self):
        require_prior_information(PRIOR,t(1,'16:00:00'),O)
        with self.assertRaises(ValueError): require_prior_information(NEXT,PRIOR,O)
        c=calendar(); c['opens'][O]['A']['decision_at']=O
        l=ledger(cash=500,c=c); self.reject(l,trade('buy','b')); self.keep(l)

    # Seven contract groups with concrete money/time counterexamples.
    def test_group1_lots_repeat_open_weekend_holiday(self):
        l=ledger(cash=200,lots=[lot()]); l.apply(trade('buy','new'))
        l.apply(event('advance','repeat',O,phase=3)); self.assertEqual(l.sellable('A',O),100)
        self.reject(l,trade('sell','too-many',qty=200))
        for i,at in enumerate((SAT,SUN,HOLIDAY)):
            l.apply(event('advance',f'closed-{i}',at,phase=3)); self.assertEqual(l.sellable('A',at),100)
        l.apply(event('advance','release',NEXT,phase=3)); self.assertEqual(l.sellable('A',NEXT),200)
        self.keep(l)

    def test_group2_paid_after_open_target_qualification(self):
        c=calendar(available=LATE); c['opens'][NEXT]['B']['buy']=False
        l=ledger(lots=[lot()],c=c); l.apply(trade('sell','s'))
        self.reject(l,trade('buy','same',symbol='B'))
        self.reject(l,trade('buy','before-cash',NEXT))
        self.reject(l,trade('buy','forbidden',NEXT,symbol='B'))
        l.apply(event('advance','arrive',LATE,phase=3))
        self.assertEqual(l.snapshot()['cash'],200)
        self.reject(l,trade('buy','go-back',NEXT))
        self.reject(l,trade('buy','no-opening',LATE))
        l.apply(trade('buy','valid',LAST,symbol='B')); self.assertEqual(l.shares('B'),100)
        self.keep(l)

    def test_group3_mixed_free_restricted_and_sale_fee(self):
        l=ledger(cash=100,lots=[lot()]); l.apply(trade('sell','s'))
        self.assertEqual(l.snapshot()['cash'],100); self.assertEqual(l.equity({}),300)
        self.reject(l,event('buy','fee',symbol='B',qty=100))
        l.apply(event('advance','release',NEXT,phase=3))
        self.assertEqual(l.snapshot()['cash'],300); self.assertEqual(l.equity({}),300)
        self.keep(l)
        c=calendar(price='.01'); q=ledger(cash=4,lots=[lot()],c=c)
        q.apply(event('sell','cost',symbol='A',qty=100,minimum_commission=5,commission_rate=0))
        self.assertEqual(q.snapshot()['cash'],0); self.assertEqual(q.equity({}),0)
        self.assertTrue(all(r['amount']>=0 for r in q.snapshot()['restricted']))
        r=ledger(cash=3,lots=[lot()],c=c)
        self.reject(r,event('sell','fail',symbol='A',qty=100,minimum_commission=5,commission_rate=0))
        TRACES['group3_sale_fee_success']=q.audit; TRACES['group3_sale_fee_failure']=r.audit

    def test_group4_split_all_lots_entitlement_preserved(self):
        c=calendar(); dividend(c,pay=t(7,'09:00:00')); split(c,at=t(6,'08:00:00'))
        l=ledger(lots=[lot(),lot(release=LAST)],c=c)
        l.apply(event('dividend','d',ACTION,action_id='d'))
        l.apply(event('split','s',t(6,'08:00:00'),action_id='s'))
        self.assertEqual(l.shares('A'),400); self.assertEqual(l.sellable('A',NEXT),200)
        self.assertEqual([x['release_at'] for x in l.snapshot()['lots']],[PRIOR,LAST])
        self.assertEqual(l.snapshot()['receivables']['d']['amount'],10)
        self.reject(l,event('split','s2',t(6,'08:00:00'),action_id='s'))
        l.apply(trade('sell','sale',NEXT,qty=200))
        self.assertEqual(l.snapshot()['receivables']['d']['amount'],10)
        self.keep(l)

    def test_group5_payment_due_and_units_unchanged(self):
        c=calendar(); dividend(c,pay=t(6,'09:00:00'))
        l=ledger(lots=[lot()],c=c); l.apply(event('dividend','d',ACTION,action_id='d'))
        self.reject(l,event('pay','early',PAY,action_id='d'))
        value=l.equity({'A':D('1.9')}); units=l.snapshot()['units']
        l.apply(event('pay','due',t(6,'09:00:00'),action_id='d'))
        self.assertEqual(l.equity({'A':D('1.9')}),value); self.assertEqual(l.snapshot()['units'],units)
        self.keep(l)

    def test_group6_order_unique_ids_atomic_multiple_orders(self):
        c=calendar(); dividend(c); l=ledger(cash=1000,lots=[lot()],c=c)
        l.apply(trade('buy','b1')); l.apply(trade('buy','b2',symbol='B'))
        self.assertEqual(l.shares('B'),100)
        self.reject(l,trade('buy','b1'))
        self.reject(l,event('deposit','back',MID,amount=100))
        self.reject(l,event('dividend','wrong-phase',ACTION,action_id='d'))
        # Later timestamp still cannot return to an earlier same-day phase.
        c2=calendar(); c2['clocks'][t(2,'10:00:00')]=[1]; split(c2,at=t(2,'10:00:00'))
        q=ledger(cash=1000,c=c2); q.apply(trade('buy','b'))
        self.reject(q,event('split','phase',t(2,'10:00:00'),action_id='s'))
        self.reject(l,trade('sell','oversale',qty=200)); self.keep(l)
        TRACES['group6_later_phase_reversal']=q.audit

    def test_group7_bindings_and_no_undated_escape(self):
        l=ledger(cash=1000)
        self.assertFalse(hasattr(l,'settle')); self.assertFalse(hasattr(l,'buy'))
        self.reject(l,{'kind':'buy','id':'undated','symbol':'A','qty':100})
        self.reject(l,trade('buy','naive',at='2026-01-02T09:30:00'))
        c=calendar(); del c['opens'][O]['A']['release_at']
        q=ledger(cash=1000,c=c); self.reject(q,trade('buy','missing-release'))
        c=calendar(); del c['opens'][O]['A']['proceeds_available_at']
        r=ledger(lots=[lot()],c=c); self.reject(r,trade('sell','missing-payment'))
        self.keep(l); TRACES['group7_missing_release']=q.audit; TRACES['group7_missing_payment']=r.audit


if __name__ == '__main__': unittest.main()
