"""All times and prices below are invented; no exchange T+1 claim."""
from decimal import Decimal as D
from dated_ledger import Ledger


def t(day, clock='09:30:00'):
    return f'2026-01-{day:02d}T{clock}+08:00'


O = t(2); SAT = t(3); SUN = t(4); HOLIDAY = t(5); NEXT = t(6); LAST = t(7)
MID = t(2, '00:00:00'); ACTION = t(2, '08:00:00'); PAY = t(2, '09:00:00')
LATE = t(6, '10:00:00'); CLOSE = t(2, '15:00:00'); PRIOR = t(1, '15:00:00')


def calendar(*, price='2', available=NEXT, release=NEXT):
    c = {'name': 'invented-Jan-2026-v1-weekend-and-Jan5-holiday',
         'timezone': 'Asia/Shanghai',
         'clocks': {MID:[0], ACTION:[1], PAY:[2], O:[3], CLOSE:[4],
                    SAT:[3], SUN:[3], HOLIDAY:[3], NEXT:[3], LATE:[3], LAST:[3],
                    t(6,'08:00:00'):[1], t(6,'09:00:00'):[2], t(6,'15:00:00'):[4],
                    t(7,'08:00:00'):[1], t(7,'09:00:00'):[2],
                    t(3,'00:00:00'):[0], t(3,'08:00:00'):[1], t(3,'09:00:00'):[2]},
         'opens': {}, 'actions': {},
         'closes': {CLOSE: {'A':D(price), 'B':D(price)},
                    t(6,'15:00:00'): {'A':D(price), 'B':D(price)}}}
    for at in (O, NEXT, LAST):
        c['opens'][at] = {s: {'buy':True, 'sell':True, 'price':D(price),
                              'release_at':release if at == O else t(8),
                              'proceeds_available_at':available if at == O else t(8),
                              'observed_at':t(1,'15:00:00'),
                              'decision_at':t(1,'16:00:00')} for s in ('A','B')}
    c['clocks'][t(8)] = [3]
    return c


def lot(qty=100, release=PRIOR, symbol='A'):
    return {'symbol':symbol, 'qty':D(qty), 'release_at':release, 'purchase_id':'opening-lot'}


def ledger(*, cash=0, lots=(), units=1000, c=None, marks=None, nav=1):
    return Ledger(c or calendar(), cash=cash, lots=lots, units=units,
                  prior_complete={'at':PRIOR, 'nav':D(nav)}, marks=marks or {'A':D(2),'B':D(2)})


def event(kind, eid, at=O, **fields):
    return dict(kind=kind, id=eid, at=at, **fields)


def trade(kind, eid, at=O, symbol='A', qty=100, **fields):
    return event(kind, eid, at, symbol=symbol, qty=qty, commission_rate=0, **fields)


def dividend(c, aid='d', *, recognize=ACTION, pay=PAY, qty=100, per='.1', mark='1.9'):
    c['actions'][aid] = {'symbol':'A', 'dividend_at':recognize, 'pay_at':pay,
                         'eligible_shares':D(qty), 'per_share':D(per), 'effective_mark':D(mark)}


def split(c, aid='s', at=ACTION, multiplier=2):
    c['actions'][aid] = {'symbol':'A','split_at':at,'multiplier':D(multiplier)}
