"""Explicit invented prices, calendar and account: no real exchange rules."""
from decimal import Decimal as D
from order_ledger_adapter_v2 import SyntheticAccount, planner

KNOWN = '2026-01-01T15:00:00+08:00'
DEC = '2026-01-01T16:00:00+08:00'
FREEZE = '2026-01-02T08:00:00+08:00'
OPEN = '2026-01-02T09:30:00+08:00'
PAY = '2026-01-06T10:00:00+08:00'
NEXTFREEZE = '2026-01-07T08:00:00+08:00'
NEXT = '2026-01-07T09:30:00+08:00'
RELEASE = '2026-01-08T09:30:00+08:00'
COSTS = planner.Costs('.001', 5, '.001', 'invented-commission-floor5-and-slippage')


def calendar(first_price='2', sell=False):
    prices = {'A': D('1.8') if sell else D(first_price), 'B': D(2)}
    c = {'name': 'invented-one-account-calendar-Jan2026', 'timezone': 'Asia/Shanghai',
         'clocks': {OPEN: [3], PAY: [3], NEXT: [3], RELEASE: [3]},
         'opens': {}, 'actions': {}, 'closes': {}}
    for clock in (OPEN, NEXT):
        c['opens'][clock] = {s: {'price': prices[s] if clock == OPEN else D(1),
                                'buy': True, 'sell': True, 'release_at': RELEASE,
                                'proceeds_available_at': PAY if clock == OPEN else RELEASE,
                                'observed_at': KNOWN, 'decision_at': DEC} for s in ('A', 'B')}
    return c


def make(c=None, sell=False, cash=None):
    c = c or calendar(sell=sell)
    lots = ([{'symbol': 'A', 'qty': D(350), 'release_at': KNOWN},
             {'symbol': 'B', 'qty': D(100), 'release_at': KNOWN}] if sell else [])
    a = SyntheticAccount('single-invented-account', c, initial_at=KNOWN,
                         cash=(D(200) if sell else D('410.50')) if cash is None else D(cash),
                         lots=lots, units=1000, prior_complete={'at': KNOWN, 'nav': D(1)},
                         marks={'A': D(2), 'B': D(1 if sell else 2)})
    d, snap = a.decision(name='invented-original-weekly-decision', decision_at=DEC,
                         reference_known_at=KNOWN, references={'A': 2, 'B': 1 if sell else 2}, costs=COSTS)
    ctx = planner.ActionContext('invented-action-coverage', 'synthetic-empty-covered-source',
                                KNOWN, KNOWN, NEXT, ())
    p = (planner.plan_p1 if sell else planner.plan_p0)(d, current_cash=snap, action_context=ctx,
                                                    frozen_at=FREEZE, opening_at=OPEN)
    return a, d, p
