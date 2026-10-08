"""Small synthetic accounting kernel; no market IO, signals, or production interface."""
from dataclasses import dataclass, field
from decimal import Decimal as D


def fee(notional, commission_rate, minimum_commission, slippage_rate):
    return max(notional * commission_rate, minimum_commission) + notional * slippage_rate


@dataclass
class Ledger:
    cash: D = D(0)
    shares: dict = field(default_factory=dict)
    settled: dict = field(default_factory=dict)
    receivables: dict = field(default_factory=dict)
    units: D = D(0)
    inflows: D = D(0)
    fees: D = D(0)
    applied_actions: set = field(default_factory=set)

    def equity(self, prices):
        if any(s not in prices or prices[s] is None or prices[s] <= 0
               for s, n in self.shares.items() if n):
            raise ValueError('missing or invalid mark')
        return self.cash + sum(self.receivables.values(), D(0)) + sum(
            (n * prices[s] for s, n in self.shares.items() if n), D(0))

    def deposit(self, amount, *, prior_complete_unit_value):
        if amount <= 0:
            raise ValueError('positive deposit required')
        # Caller supplies the frozen complete prior-close NAV, never a mixture
        # of yesterday's nominal price and today's corporate-action receivable.
        nav = prior_complete_unit_value
        if nav <= 0:
            raise ValueError('nonpositive unit value')
        self.units += amount / nav
        self.cash += amount
        self.inflows += amount

    def buy(self, symbol, qty, price, commission_rate=D('.001'),
            minimum_commission=D(0), slippage_rate=D(0), *, allowed=True):
        if not allowed or qty <= 0 or qty % D(100) or price <= 0:
            raise ValueError('buy not allowed or non-lot quantity')
        if min(commission_rate, minimum_commission, slippage_rate) < 0:
            raise ValueError('negative fee input')
        cost = qty * price
        charge = fee(cost, commission_rate, minimum_commission, slippage_rate)
        if cost + charge > self.cash:
            raise ValueError('insufficient shared cash')
        self.cash -= cost + charge
        self.shares[symbol] = self.shares.get(symbol, D(0)) + qty
        self.fees += charge

    def settle(self):
        self.settled = dict(self.shares)

    def sell(self, symbol, qty, price, commission_rate=D('.001'),
             minimum_commission=D(0), slippage_rate=D(0), *, allowed=True):
        holding = self.shares.get(symbol, D(0))
        if (not allowed or qty <= 0 or price <= 0 or qty > self.settled.get(symbol, D(0))
                or qty > holding or (qty % D(100) and qty != holding)):
            raise ValueError('sale not allowed, unsettled or invalid remainder')
        if min(commission_rate, minimum_commission, slippage_rate) < 0:
            raise ValueError('negative fee input')
        notional = qty * price
        charge = fee(notional, commission_rate, minimum_commission, slippage_rate)
        if self.cash + notional < charge:
            raise ValueError('sale cannot cover charge')
        self.cash += notional - charge
        self.shares[symbol] -= qty
        self.settled[symbol] -= qty
        self.fees += charge

    def recognize_dividend(self, action_id, eligible_shares, per_share):
        if action_id in self.applied_actions or min(eligible_shares, per_share) < 0:
            raise ValueError('duplicate or invalid dividend')
        self.receivables[action_id] = eligible_shares * per_share
        self.applied_actions.add(action_id)

    def pay_dividend(self, action_id):
        # Keep a zero-valued action record to reject later duplicate recognition.
        value = self.receivables[action_id]
        if value <= 0:
            raise ValueError('not payable twice')
        self.cash += value
        self.receivables[action_id] = D(0)

    def split(self, action_id, symbol, multiplier):
        if action_id in self.applied_actions or multiplier <= 0:
            raise ValueError('invalid share multiplier')
        self.shares[symbol] *= multiplier
        self.settled[symbol] = self.settled.get(symbol, D(0)) * multiplier
        self.applied_actions.add(action_id)


def require_prior_information(observed_at, decision_at, execution_at):
    if not observed_at <= decision_at < execution_at:
        raise ValueError('information or execution time invalid')


def require_later_open(sale_session, purchase_session):
    """Session ordinals come from a qualified exchange calendar, not daily bars."""
    if purchase_session <= sale_session:
        raise ValueError('sale proceeds require a later eligible opening session')
