import unittest
from dataclasses import FrozenInstanceError,replace,asdict
from decimal import Decimal as D
from order_planning import *

KNOWN='2026-01-01T15:00:00+08:00'
DECISION='2026-01-01T16:00:00+08:00'
FREEZE='2026-01-02T08:00:00+08:00'
OPEN='2026-01-02T09:30:00+08:00'
PAY='2026-01-06T10:00:00+08:00'
NEXTFREEZE='2026-01-07T08:00:00+08:00'
NEXT='2026-01-07T09:30:00+08:00'
FLOOR=Costs('.001',5,'.001','synthetic-floor5')
ZERO=Costs(0,0,0,'synthetic-zero')
RECEIPTS={}

def decision(name='invented-v0.2',free=250,restricted=0,receivable=0,held=(0,0),prices=(1,1),sellable=None,c=ZERO,future=0):
    sellable=held if sellable is None else sellable
    assets=tuple(Asset(s,prices[i],KNOWN,held[i],sellable[i]) for i,s in enumerate(('A','B')))
    return Decision(name,DECISION,KNOWN,KNOWN,free,restricted,receivable,assets,c,future)


def p0(d):return plan_p0(d,frozen_at=FREEZE,opening_at=OPEN)


class PureChecks(unittest.TestCase):
    def keep(self,**x):RECEIPTS[self.id().split('.')[-1]]=x

    def test_floor_fee_exact_boundary(self):
        self.assertEqual(affordable_quantity(205,2,FLOOR),0)
        self.assertEqual(affordable_quantity('205.2',2,FLOOR),100)
        self.assertEqual(cost(100,2,FLOOR),D('205.2'));self.assertEqual(cost(0,2,FLOOR),0)
        self.keep(cost100=cost(100,2,FLOOR),q205=0,q205_2=100,zero_fee=cost(0,2,FLOOR))

    def test_fixed_quantity_cap_no_resize(self):
        d=decision(free='410.5',prices=(2,2),c=FLOOR);p=p0(d);o=p.orders[0]
        self.assertEqual(o.budget,D('205.25'));self.assertEqual(o.quantity,100);self.assertEqual(o.cap,D('2.000'))
        status=validate_opening_order(p,o,opening_at=OPEN,price='2.001',eligible=True)
        self.assertEqual(status,'reject_no_resize');self.assertEqual(cost(100,'2.001',FLOOR),D('205.3001'))
        self.assertEqual(validate_opening_order(p,o,opening_at=OPEN,price=2,eligible=True,proposed_quantity=50),'reject_no_resize')
        self.keep(decision=asdict(d),plan=asdict(p),next_tick_cost=cost(100,'2.001',FLOOR),status=status)

    def test_variable_commission_and_cap_next_tick(self):
        c=Costs('.01',1,'.005','synthetic-variable')
        q=affordable_quantity(500,2,c);limit=price_cap(500,q,c)
        self.assertEqual(q,200);self.assertEqual(cost(q,2,c),406);self.assertEqual(limit,D('2.463'))
        self.assertEqual(cost(q,limit,c),D('499.989'));self.assertEqual(cost(q,limit+D('.001'),c),D('500.192'))
        self.keep(q=q,limit=limit,limit_cost=cost(q,limit,c),next_tick_cost=cost(q,limit+D('.001'),c))

    def test_p0_gaps_shared_cash_no_reallocation(self):
        d=decision(free=300,receivable=100,held=(100,200),prices=(2,2));p=p0(d)
        self.assertEqual(values(d)[0],1000);self.assertEqual(p.ordering,(('A',D(300)),('B',D(100))))
        self.assertEqual(p.budgets,(('A',D(300)),('B',D(0))))
        self.assertEqual(len(p.orders),1);self.assertEqual(p.orders[0].quantity,100)
        # Budget300, actual cost200 leaves100, but B's frozen budget stays0.
        self.assertEqual(cost(p.orders[0].quantity,2,d.costs),200)
        self.assertEqual(p.budgets[1][1],0);self.keep(decision=asdict(d),plan=asdict(p),unused_first=100)

    def test_equal_gaps_code_tie_250(self):
        d=decision();p=p0(d)
        self.assertEqual(p.budgets,(('A',D(125)),('B',D(125))))
        self.assertEqual(tuple(o.quantity for o in p.orders),(100,100))
        self.assertEqual(d.free-sum(cost(o.quantity,o.reference,d.costs) for o in p.orders),50)
        self.keep(decision=asdict(d),plan=asdict(p),remaining_after_reference_cost=50)

    def test_p1_sell_actual_later_buy_original_snapshot(self):
        d=decision(free=200,held=(350,100),prices=(2,1),sellable=(100,100),c=FLOOR)
        p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN);self.assertEqual(p.status,'await_sale')
        o=p.orders[0];self.assertEqual(o.quantity,100)
        r=SaleResult(o.order_id,'filled',100,'1.8',OPEN,PAY,'synthetic-sale1')
        q=later_buys(d,p,r,frozen_at=NEXTFREEZE,opening_at=NEXT)
        self.assertEqual(q.ordering,p.ordering);self.assertEqual(q.budgets,(('B',D('374.82')),('A',D(0))))
        self.assertEqual(q.orders[0].reference,1);self.assertEqual(q.orders[0].quantity,300)
        self.assertEqual(cost(300,1,FLOOR),D('305.3'))
        self.keep(decision=asdict(d),sale_plan=asdict(p),sale_receipt=asdict(r),later_plan=asdict(q),net=D('174.82'),later_cash=D('374.82'),buy_cost=D('305.3'))

    def test_p1_same_open_and_late_cash_rejected(self):
        d=decision(free=200,held=(350,100),prices=(2,1),sellable=(100,100),c=FLOOR)
        p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN);o=p.orders[0]
        r=SaleResult(o.order_id,'filled',100,'1.8',OPEN,OPEN,'synthetic-same-open')
        with self.assertRaises(ValueError):later_buys(d,p,r,frozen_at=FREEZE,opening_at=OPEN)
        r=replace(r,proceeds_available_at=PAY)
        with self.assertRaises(ValueError):later_buys(d,p,r,frozen_at=OPEN,opening_at=NEXT)
        self.keep(same_open_rejected=True,not_yet_available_rejected=True)

    def test_future_money_restricted_and_receivable_unspendable(self):
        d=decision(free=0,restricted=250,receivable=250,future=250);p=p0(d)
        self.assertEqual(values(d)[0],500);self.assertEqual(p.orders,());self.assertEqual(sum(b for _,b in p.budgets),0)
        with self.assertRaises(ValueError):replace(d,cash_available_at=at(PAY),free=250)
        self.keep(decision=asdict(d),plan=asdict(p),future_information_rejected=True)

    def test_p1_trigger_no_executable_whole_lot_unsupported(self):
        d=decision(free=0,held=(60,40),prices=(2,2),sellable=(60,40))
        p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN)
        self.assertEqual(p.status,'unsupported');self.assertEqual(p.reason,'triggered_no_sellable_whole_lot_pending_user')
        self.assertEqual(p.orders,());self.keep(decision=asdict(d),plan=asdict(p))

    def test_p1_not_triggered_uses_p0(self):
        d=decision(free=0,held=(100,100));p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN)
        self.assertEqual(p,p0(d));self.keep(plan=asdict(p))

    def test_exact_five_points_trigger_and_sellable_cap(self):
        d=decision(free=0,held=(1100,900));p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN)
        self.assertEqual(p.status,'await_sale');self.assertEqual(p.orders[0].quantity,100)
        d=decision(free=200,held=(700,100),sellable=(199,100));p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN)
        self.assertEqual(p.orders[0].quantity,100);self.keep(plan=asdict(p))

    def test_immutable_snapshot_hash_and_future_price(self):
        d=decision();p=p0(d)
        with self.assertRaises(FrozenInstanceError):d.free=D(1000)
        with self.assertRaises(FrozenInstanceError):d.assets[0].reference=D(3)
        with self.assertRaises(FrozenInstanceError):p.orders[0].quantity=D(200)
        self.assertEqual(d.input_hash,decision().input_hash)
        self.assertNotEqual(d.input_hash,decision(free=300).input_hash)
        with self.assertRaises(ValueError):replace(d,assets=(replace(d.assets[0],known_at=at(OPEN)),d.assets[1]))
        self.keep(input_hash=d.input_hash,immutability=True,future_price_rejected=True)

    def test_bad_costs_numbers_and_order_identity(self):
        for x in ('NaN','Infinity','-1'):
            with self.assertRaises(ValueError):Costs(x,0,0,'bad')
        d=decision();p=p0(d);o=p.orders[0]
        with self.assertRaises(ValueError):validate_opening_order(p,replace(o,budget=D(1000)),opening_at=OPEN,price=1,eligible=True)
        self.assertEqual(validate_opening_order(p,o,opening_at=OPEN,price=1,eligible=None),'reject_product_not_eligible')
        self.assertEqual(validate_opening_order(p,o,opening_at=OPEN,price=0,eligible=True),'reject_missing_opening_price')
        with self.assertRaises(ValueError):validate_opening_order(p,o,opening_at=NEXT,price=1,eligible=True)
        self.keep(changed_order_rejected=True,unknown_permission_rejected=True,wrong_open_rejected=True)

    def test_action_crossing_no_assumed_adjustment(self):
        d=decision();p=plan_p0(d,frozen_at=FREEZE,opening_at=OPEN,actions=[FREEZE])
        self.assertEqual(p.status,'unsupported');self.assertEqual(p.reason,'unsupported_company_action_crossing')
        with self.assertRaises(ValueError):plan_p0(d,frozen_at=OPEN,opening_at=OPEN)
        self.keep(plan=asdict(p),same_open_freeze_rejected=True)

    def test_failed_partial_or_wrong_sale_no_chase(self):
        d=decision(free=200,held=(350,100),prices=(2,1),sellable=(100,100),c=FLOOR)
        p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN);o=p.orders[0]
        r=SaleResult(o.order_id,'failed',0,0,OPEN,PAY,'synthetic-failed')
        q=later_buys(d,p,r,frozen_at=NEXTFREEZE,opening_at=NEXT);self.assertEqual(q.orders,());self.assertEqual(q.status,'unsupported')
        with self.assertRaises(ValueError):later_buys(d,p,replace(r,status='filled',quantity=D(50),price=D('1.8')),frozen_at=NEXTFREEZE,opening_at=NEXT)
        with self.assertRaises(ValueError):later_buys(d,p,replace(r,order_id='other'),frozen_at=NEXTFREEZE,opening_at=NEXT)
        self.keep(failed_sale_plan=asdict(q),partial_filled_quantity_rejected=True,other_id_rejected=True)


if __name__=='__main__':unittest.main()
