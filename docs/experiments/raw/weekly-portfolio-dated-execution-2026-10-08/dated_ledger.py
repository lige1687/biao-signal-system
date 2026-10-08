"""Synthetic dated execution only. apply is the sole supported mutation API.
All calendar rules are explicit fixture evidence, never inferred exchange rules.
"""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal as D


def instant(value):
    t = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(t, datetime) or t.utcoffset() is None:
        raise ValueError('timezone-bound instant required')
    return t


def number(value):
    n = D(str(value))
    if not n.is_finite():
        raise ValueError('finite amount required')
    return n


def fee(notional, commission_rate, minimum_commission, slippage_rate):
    c, m, s = map(number, (commission_rate, minimum_commission, slippage_rate))
    if min(c, m, s) < 0:
        raise ValueError('negative fee input')
    return max(notional * c, m) + notional * s


def require_prior_information(observed_at, decision_at, execution_at):
    if not instant(observed_at) <= instant(decision_at) < instant(execution_at):
        raise ValueError('information or execution time invalid')


PHASE = {'deposit': 0, 'dividend': 1, 'split': 1, 'pay': 2,
         'buy': 3, 'sell': 3, 'close': 4}


class Ledger:
    def __init__(self, calendar, *, cash=0, lots=(), units=0,
                 prior_complete=None, marks=None):
        if not calendar.get('name') or not calendar.get('clocks') or not calendar.get('timezone'):
            raise ValueError('named explicit calendar required')
        self._calendar = deepcopy(calendar)
        self._zone = ZoneInfo(calendar['timezone'])
        self._state = {'cash': number(cash), 'lots': deepcopy(list(lots)),
                       'restricted': [], 'receivables': {}, 'units': number(units),
                       'inflows': D(0), 'fees': D(0), 'actions': set(),
                       'ids': set(), 'last_at': None, 'last_phase': -1,
                       'prior_complete': deepcopy(prior_complete),
                       'marks': deepcopy(marks or {})}
        if min(self._state['cash'], self._state['units']) < 0:
            raise ValueError('negative opening balance')
        for lot in self._state['lots']:
            lot['qty'] = number(lot['qty']); instant(lot['release_at'])
            if lot['qty'] <= 0 or not lot.get('symbol'):
                raise ValueError('invalid opening lot')
        self.audit = []

    def snapshot(self):
        return deepcopy(self._state)

    def shares(self, symbol):
        return sum((l['qty'] for l in self._state['lots'] if l['symbol'] == symbol), D(0))

    def sellable(self, symbol, at):
        t = instant(at)
        return sum((l['qty'] for l in self._state['lots']
                    if l['symbol'] == symbol and instant(l['release_at']) <= t), D(0))

    @staticmethod
    def _equity(state, prices):
        holdings = {}
        for lot in state['lots']:
            holdings[lot['symbol']] = holdings.get(lot['symbol'], D(0)) + lot['qty']
        value = state['cash'] + sum((r['amount'] for r in state['restricted']), D(0))
        value += sum((r['amount'] for r in state['receivables'].values()), D(0))
        for symbol, qty in holdings.items():
            if qty:
                if symbol not in prices or prices[symbol] is None or number(prices[symbol]) <= 0:
                    raise ValueError('missing or invalid mark')
                value += qty * number(prices[symbol])
        return value

    def equity(self, prices):
        return self._equity(self._state, prices)

    def receipt(self, at):
        s = self._state
        symbols = sorted({l['symbol'] for l in s['lots']})
        try:
            value = str(self._equity(s, s['marks']))
        except ValueError:
            value = None
        return {'at': str(at), 'free_cash': str(s['cash']),
                'restricted_cash': str(sum((r['amount'] for r in s['restricted']), D(0))),
                'receivable': str(sum((r['amount'] for r in s['receivables'].values()), D(0))),
                'shares': {x: str(self.shares(x)) for x in symbols},
                'sellable': {x: str(self.sellable(x, at)) for x in symbols},
                'equity': value, 'units': str(s['units']), 'fees': str(s['fees'])}

    def apply(self, event):
        """Commit a validated event atomically; rejection audit is separate from money state."""
        before = self.snapshot()
        try:
            e = deepcopy(event); at = instant(e['at']); kind = e['kind']; eid = e['id']
            if not isinstance(eid, str) or not eid or eid in before['ids']:
                raise ValueError('missing or duplicate event id')
            phase = e.get('phase') if kind == 'advance' else PHASE.get(kind)
            if phase not in (0, 1, 2, 3, 4):
                raise ValueError('unknown event or phase')
            if phase not in self._calendar['clocks'].get(e['at'], []):
                raise ValueError('unbound calendar clock or phase')
            last = before['last_at']
            if last and (at < instant(last) or
                         (at.astimezone(self._zone).date() == instant(last).astimezone(self._zone).date()
                          and phase < before['last_phase'])):
                raise ValueError('backward time or same-day phase order')
            work = deepcopy(before)
            self._require_due_actions(work, e, at)
            # Proceeds cannot be unlocked at their selling opening, even if the
            # explicitly supplied payment clock is equal to that opening.
            remaining = []
            for r in work['restricted']:
                if at >= instant(r['available_at']) and at > instant(r['sold_at']):
                    work['cash'] += r['amount']
                else:
                    remaining.append(r)
            work['restricted'] = remaining
            self._execute(work, e, at)
            work['ids'].add(eid); work['last_at'] = e['at']; work['last_phase'] = phase
            self._state = work
            self.audit.append({'event': e, 'accepted': True, 'state': self.receipt(e['at'])})
            return self.receipt(e['at'])
        except (ValueError, KeyError, TypeError, ArithmeticError) as error:
            self.audit.append({'event': deepcopy(event), 'accepted': False,
                               'reason': str(error), 'money_state_unchanged': self._state == before})
            raise ValueError(str(error)) from error

    def _require_due_actions(self, state, event, at):
        # Every bound effective split/dividend is required, not optional.
        # Concurrent actions need an explicit unique integer sequence; the
        # execution engine does not guess which action goes first.
        groups = {}
        for aid, action in self._calendar.get('actions', {}).items():
            for kind in ('split', 'dividend'):
                clock = action.get(kind + '_at')
                if clock is not None and instant(clock) <= at:
                    groups.setdefault(instant(clock), []).append((aid, kind, action))
        for clock in sorted(groups):
            actions = groups[clock]
            if len(actions) > 1:
                sequences = [a.get('sequence') for _, _, a in actions]
                if (any(type(n) is not int for n in sequences) or
                        len(set(sequences)) != len(sequences)):
                    raise ValueError('ambiguous concurrent required action order')
                actions.sort(key=lambda row: row[2]['sequence'])
            for aid, kind, _ in actions:
                if aid in state['actions']:
                    continue
                if (event['kind'] == kind and event.get('action_id') == aid
                        and clock == at):
                    # Later actions at this clock may follow this one, but no
                    # downstream event can bypass either of them.
                    return
                raise ValueError('required due action missing: ' + aid)

    def _execute(self, s, e, at):
        k = e['kind']
        if k == 'advance':
            return
        if k == 'deposit':
            local = at.astimezone(self._zone)
            if local.hour or local.minute or local.second or local.microsecond:
                raise ValueError('deposit requires midnight')
            amount = number(e['amount']); prior = s['prior_complete']
            if prior is None or instant(prior['at']).astimezone(self._zone).date() >= local.date():
                raise ValueError('saved prior complete-day NAV required')
            required = [instant(clock) for clock in self._calendar.get('closes', {})
                        if instant(clock).astimezone(self._zone).date() < local.date()]
            if required and instant(prior['at']) != max(required):
                raise ValueError('latest required complete-day close missing')
            nav = number(prior['nav'])
            if amount <= 0 or nav <= 0:
                raise ValueError('positive deposit and NAV required')
            s['cash'] += amount; s['units'] += amount / nav; s['inflows'] += amount
        elif k in ('buy', 'sell'):
            symbol = e['symbol']
            binding = self._calendar.get('opens', {}).get(e['at'], {}).get(symbol)
            if not binding or binding.get(k) is not True:
                raise ValueError('missing opening, halt, or product permission')
            require_prior_information(binding['observed_at'], binding['decision_at'], e['at'])
            qty, price = number(e['qty']), number(binding['price'])
            if 'price' in e and number(e['price']) != price:
                raise ValueError('price differs from qualified opening')
            if qty <= 0 or price <= 0:
                raise ValueError('positive quantity and opening required')
            charge = fee(qty * price, e.get('commission_rate', '.001'),
                         e.get('minimum_commission', 0), e.get('slippage_rate', 0))
            holding = sum((l['qty'] for l in s['lots'] if l['symbol'] == symbol), D(0))
            if k == 'buy':
                release = binding['release_at']
                if (release not in self._calendar['clocks'] or instant(release) <= at or
                        instant(release).astimezone(self._zone).date() <= at.astimezone(self._zone).date()
                        or qty % 100):
                    raise ValueError('explicit later-local-date release and buy lot required')
                if qty * price + charge > s['cash']:
                    raise ValueError('insufficient free cash including fees')
                s['cash'] -= qty * price + charge
                s['lots'].append({'symbol': symbol, 'qty': qty, 'release_at': release,
                                  'purchase_id': e['id']})
            else:
                available = binding['proceeds_available_at']
                if instant(available) < at:
                    raise ValueError('proceeds availability precedes sale')
                eligible = [l for l in s['lots'] if l['symbol'] == symbol
                            and instant(l['release_at']) <= at]
                if qty > sum((l['qty'] for l in eligible), D(0)) or (qty % 100 and qty != holding):
                    raise ValueError('unreleased, oversale, or invalid remainder')
                net = qty * price - charge
                if net < 0 and -net > s['cash']:
                    raise ValueError('available cash cannot cover sale fee excess')
                left = qty
                for lot in eligible:
                    take = min(left, lot['qty']); lot['qty'] -= take; left -= take
                if net >= 0:
                    s['restricted'].append({'amount': net, 'available_at': available,
                                            'sold_at': e['at'], 'sale_id': e['id']})
                else:
                    s['cash'] += net
            s['fees'] += charge
            s['marks'][symbol] = price
        elif k in ('dividend', 'split', 'pay'):
            aid = e['action_id']; action = self._calendar.get('actions', {}).get(aid)
            if not action or action.get(k + '_at') != e['at']:
                raise ValueError('unbound action clock')
            if k == 'pay':
                r = s['receivables'].get(aid)
                if r is None or r['paid'] or at < instant(r['pay_at']):
                    raise ValueError('not due or duplicate payment')
                s['cash'] += r['amount']; r['amount'] = D(0); r['paid'] = True
            else:
                if aid in s['actions']:
                    raise ValueError('duplicate action')
                if k == 'dividend':
                    qty, per = number(action['eligible_shares']), number(action['per_share'])
                    if min(qty, per) < 0 or instant(action['pay_at']) < at:
                        raise ValueError('invalid dividend entitlement or payment clock')
                    s['receivables'][aid] = {'amount': qty * per, 'pay_at': action['pay_at'], 'paid': False}
                    # Explicit effective mark avoids stale nominal price plus receivable.
                    mark = number(action['effective_mark'])
                    if mark <= 0:
                        raise ValueError('qualified positive effective mark required')
                    s['marks'][action['symbol']] = mark
                else:
                    mult = number(action['multiplier'])
                    if mult <= 0:
                        raise ValueError('invalid split multiplier')
                    for lot in s['lots']:
                        if lot['symbol'] == action['symbol']:
                            lot['qty'] *= mult
                    if action['symbol'] in s['marks']:
                        s['marks'][action['symbol']] = number(s['marks'][action['symbol']]) / mult
                s['actions'].add(aid)
        elif k == 'close':
            prices = self._calendar.get('closes', {}).get(e['at'])
            if prices is None:
                raise ValueError('unbound complete-day valuation')
            equity = self._equity(s, prices)
            if s['units'] <= 0:
                raise ValueError('positive accounting units required for complete NAV')
            s['marks'] = deepcopy(prices)
            s['prior_complete'] = {'at': e['at'], 'nav': equity / s['units']}
