"""Research-only point-in-time affine price conversion. No signals/accounts/network."""
from dataclasses import dataclass
from decimal import Decimal, getcontext
from bisect import bisect_left
getcontext().prec = 40
D = Decimal
FIELDS = ('open', 'high', 'low', 'close')
MODES = ('cash_additive_v1', 'cash_proportional_v1')

class QualificationError(ValueError):
    pass

def number(value):
    x = D(str(value))
    if not x.is_finite():
        raise QualificationError('nonfinite number')
    return x

@dataclass(frozen=True)
class Transform:
    a: Decimal = D(1)
    b: Decimal = D(0)
    volume_multiplier: Decimal = D(1)
    event_ids: tuple = ()

    def forward(self, value):
        return self.a * number(value) + self.b

    def inverse_to_original_date(self, value):
        # This is the old source-date nominal price, never a current trade price.
        return (number(value) - self.b) / self.a

class PriceBasis:
    def __init__(self, bars_by_symbol, actions):
        self.bars = bars_by_symbol
        self.actions = tuple(dict(a) for a in actions)
        self.dates = {}
        for symbol, bars in self.bars.items():
            dates = [b['date'] for b in bars]
            if dates != sorted(set(dates)):
                raise QualificationError('duplicate or unordered quote dates')
            self.dates[symbol] = dates

    def mapping(self, symbol, historical_date, as_of, mode, phase='close'):
        if mode not in MODES or phase not in ('open', 'close'):
            raise QualificationError('unknown convention or knowledge phase')
        if historical_date > as_of:
            raise QualificationError('future historical observation')
        # Filter on BOTH announcement and effectivity; no terminal adjustment basis.
        selected = [a for a in self.actions if a['symbol'] == symbol
                    and historical_date < a['effective_date'] <= as_of
                    and (a['announcement_date'] < as_of if phase == 'open'
                         else a['announcement_date'] <= as_of)]
        selected.sort(key=lambda a: (a['effective_date'], a['event_id']))
        identities, economic_keys = set(), set()
        seen_by_date = {}
        for action in selected:
            key = (symbol, action['type'], action['effective_date'])
            if action['event_id'] in identities or key in economic_keys:
                raise QualificationError('duplicate or conflicting economic event')
            identities.add(action['event_id']); economic_keys.add(key)
            if action['currency'] != 'CNY':
                raise QualificationError('unverified currency conversion')
            if action['effective_date'] in seen_by_date:
                raise QualificationError('same-day mixed action order unspecified')
            seen_by_date[action['effective_date']] = action['type']
        a, b, volume = D(1), D(0), D(1)
        for action in selected:
            if action['type'] == 'split':
                r = number(action['ratio'])
                if r <= 0:
                    raise QualificationError('nonpositive split ratio')
                a, b, volume = a/r, b/r, volume*r
            elif action['type'] == 'cash_dividend':
                d = number(action['cash'])
                if d <= 0:
                    raise QualificationError('nonpositive dividend')
                if mode == 'cash_additive_v1':
                    b -= d
                else:
                    idx = bisect_left(self.dates.get(symbol, []), action['effective_date']) - 1
                    if idx < 0:
                        raise QualificationError('missing previous nominal quote')
                    c = number(self.bars[symbol][idx]['close'])
                    if c <= d:
                        raise QualificationError('reference close <= dividend')
                    f = (c-d)/c
                    a, b = a*f, b*f
            else:
                raise QualificationError('unimplemented corporate action')
        return Transform(a, b, volume, tuple(x['event_id'] for x in selected))

    def bar(self, symbol, original, as_of, mode, phase='close'):
        t = self.mapping(symbol, original['date'], as_of, mode, phase)
        values = {f: t.forward(original[f]) for f in FIELDS}
        if any(v <= 0 for v in values.values()):
            raise QualificationError('nonpositive converted OHLC')
        if not values['low'] <= min(values['open'], values['close']) <= max(values['open'], values['close']) <= values['high']:
            raise QualificationError('invalid OHLC ordering')
        volume = number(original['volume']) * t.volume_multiplier
        if volume < 0:
            raise QualificationError('negative volume')
        return dict(date=original['date'], **values, volume=volume,
                    volume_unit='original source unit, split-adjusted; unit not independently established',
                    basis_as_of=as_of, events=t.event_ids)

    def rebase_level(self, level, as_of, mode, phase='close'):
        if level['confirmed_at'] > as_of or (phase == 'open' and level['confirmed_at'] == as_of):
            raise QualificationError('structure not yet confirmed at requested decision phase')
        if not level['source_date'] <= level['confirmed_at'] <= level['basis_as_of'] <= as_of:
            raise QualificationError('inconsistent level provenance dates')
        t = self.mapping(level['symbol'], level['basis_as_of'], as_of, mode, phase)
        value = t.forward(level['value'])
        if value <= 0:
            raise QualificationError('nonpositive rebased level')
        return dict(level, value=value, basis_as_of=as_of, rebase_event_ids=t.event_ids)
