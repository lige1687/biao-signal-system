"""One synthetic account, one serial whole-order batch. No persistent engine."""
from pathlib import Path
from dataclasses import dataclass, asdict
from copy import deepcopy
from decimal import Decimal as D
import hashlib, json, sys

RAW = Path(__file__).resolve().parent.parent
PATHS = {
    'spec': RAW / 'weekly-portfolio-dated-execution-2026-10-08/source-baseline/shared-account-spec.md',
    'planner2': RAW / 'weekly-portfolio-order-planning-2026-10-08/order_planning_v2.py',
    'planner1_arithmetic': RAW / 'weekly-portfolio-order-planning-2026-10-08/order_planning.py',
    'datedledger': RAW / 'weekly-portfolio-dated-execution-2026-10-08/dated_ledger.py'}
EXPECTED = {
    'spec': '695ce8a18e34d3520c53f793b1f347a05e146fea345474b5d72224ba93c30a5a',
    'planner2': 'a9ab958fa737fc53e7a08905da9ffd82b40687354f2b8be2d508db121a13b958',
    'planner1_arithmetic': '645cac7faa6fc25bd95e0c25b63621d4e233b501a6d0b946895ff685b584a75a',
    'datedledger': '20f6547deea6d19c6416daa6048ee18a7111ff6bf4c7b21bbae90a7b379e62d3'}
assert {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in PATHS.items()} == EXPECTED
sys.path.insert(0, str(PATHS['planner2'].parent))
sys.path.insert(0, str(PATHS['datedledger'].parent))
import order_planning_v2 as planner
from dated_ledger import Ledger, instant, number


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def verify_plan(p):
    content = {'decision_hash': p.decision_hash, 'cash': asdict(p.current_cash),
               'actions': asdict(p.action_context),
               'funding_receipt': asdict(p.funding_receipt) if p.funding_receipt else None,
               'frozen_at': p.frozen_at, 'opening_at': p.opening_at,
               'complete_plan': {'status': p.status, 'reason': p.reason, 'ordering': p.ordering,
                                 'budgets': p.budgets, 'unallocated': p.unallocated,
                                 'orders': [{k: v for k, v in asdict(o).items()
                                             if k not in ('order_id', 'decision_hash', 'plan_hash')}
                                            for o in p.orders]}}
    if digest(content) != p.plan_hash:
        raise ValueError('complete plan hash differs')
    for i, o in enumerate(p.orders):
        if (o.plan_hash != p.plan_hash or o.decision_hash != p.decision_hash
                or o.order_id != digest((p.plan_hash, i, o.symbol, o.side))):
            raise ValueError('order identity differs from complete plan')


@dataclass(frozen=True)
class OpeningEvidence:
    calendar_name: str
    calendar_hash: str
    at: str
    symbol: str
    price: D
    buy: bool | None
    sell: bool | None


@dataclass(frozen=True)
class AttemptReceipt:
    account_name: str
    order_id: str
    event_id: str
    status: str
    reason: str
    before_json: str
    after_json: str
    ledger_apply_count: int
    ledger_state_unchanged: bool
    quantity: D
    price: D
    opening_at: str

    @property
    def before(self): return json.loads(self.before_json)

    @property
    def after(self): return json.loads(self.after_json)


class Batch:
    """Transient expected state and attempted IDs only; no reservation or recovery."""
    def __init__(self, account, decision, plan):
        self.account = account; self.decision = decision; self.plan = plan
        self.expected = account.ledger.snapshot(); self.receipts = {}; self.stopped = False

    @property
    def complete(self):
        return self.stopped or all(o.order_id in self.receipts for o in self.plan.orders)


class SyntheticAccount:
    def __init__(self, name, calendar, *, initial_at, cash, lots=(), units=1000,
                 prior_complete=None, marks=None):
        if not name: raise ValueError('named synthetic account required')
        self.name = name; self.initial_at = instant(initial_at)
        self._calendar = deepcopy(calendar); self.calendar_hash = digest(calendar)
        self.ledger = Ledger(calendar, cash=cash, lots=lots, units=units,
                             prior_complete=prior_complete, marks=marks)
        self._cash_sources = {}; self._decisions = {}; self._sale_results = {}
        self._attempted_keys = set()
        self._original_decision_hash = None
        self._active = None; self.calendar_events = []

    def opening(self, symbol, at):
        binding = self._calendar.get('opens', {}).get(at, {}).get(symbol)
        if binding is None: raise ValueError('missing opening in account calendar')
        return OpeningEvidence(self._calendar['name'], self.calendar_hash, at, symbol,
                               number(binding['price']), binding.get('buy'), binding.get('sell'))

    def cash_snapshot(self, *, at, includes_sale_receipt=None):
        s = self.ledger.snapshot()
        expected_at = instant(s['last_at']) if s['last_at'] else self.initial_at
        if instant(at) != expected_at:
            raise ValueError('cash snapshot must use actual current ledger clock')
        if includes_sale_receipt is not None:
            r = self._sale_results.get(includes_sale_receipt)
            if r is None or instant(at) < r.proceeds_available_at:
                raise ValueError('sale not yet available in this account')
            if any(x['sale_id'] == includes_sale_receipt for x in s['restricted']):
                raise ValueError('sale remains restricted; explicit release event required')
        snap = planner.CashSnapshot('cash-from-' + self.name,
                                    self.name + ':' + digest(s), s['cash'], at, at,
                                    includes_sale_receipt is not None, includes_sale_receipt)
        self._cash_sources[snap.source_id] = (snap, s)
        return snap

    def decision(self, *, name, decision_at, reference_known_at, references, costs):
        if self._original_decision_hash is not None:
            raise ValueError('original decision already bound; rename or reset unsupported')
        if self.ledger.snapshot()['last_at'] is not None:
            raise ValueError('initial decision constructor only; no automatic policy recomputation')
        if instant(reference_known_at) != self.initial_at:
            raise ValueError('initial known-time binding required')
        snap = self.cash_snapshot(at=reference_known_at)
        s = self.ledger.snapshot()
        assets = tuple(planner.Asset(symbol, price, reference_known_at,
                                    self.ledger.shares(symbol), self.ledger.sellable(symbol, decision_at))
                       for symbol, price in sorted(references.items()))
        d = planner.Decision(name, decision_at, reference_known_at, reference_known_at,
                             s['cash'], sum((r['amount'] for r in s['restricted']), D(0)),
                             sum((r['amount'] for r in s['receivables'].values()), D(0)), assets, costs)
        self._decisions[d.input_hash] = d
        return d, snap

    def begin(self, decision, plan):
        if self._active is not None and not self._active.complete:
            raise ValueError('another unfinished batch unsupported')
        verify_plan(plan)
        if self._original_decision_hash is not None and decision.input_hash != self._original_decision_hash:
            raise ValueError('single original decision binding differs')
        if any((plan.decision_hash, o.side, o.symbol) in self._attempted_keys
               for o in plan.orders):
            raise ValueError('re-attempt through fresh batch or new plan ID unsupported')
        if plan.status not in ('ready', 'await_sale'):
            raise ValueError('unsupported plan: ' + plan.reason)
        if (self._decisions.get(decision.input_hash) != decision
                or plan.decision_hash != decision.input_hash):
            raise ValueError('decision does not originate from this account')
        cash_source = self._cash_sources.get(plan.current_cash.source_id)
        if cash_source is None or cash_source[0] != plan.current_cash or cash_source[1] != self.ledger.snapshot():
            raise ValueError('stale or foreign current cash source')
        if plan.funding_receipt is not None and self._sale_results.get(plan.funding_receipt.receipt_id) != plan.funding_receipt:
            raise ValueError('funding receipt does not originate from this account')
        if plan.funding_receipt is not None:
            r = plan.funding_receipt
            snap = plan.current_cash
            state = self.ledger.snapshot()
            if snap.includes_sale_proceeds is not True or snap.included_receipt_id != r.receipt_id:
                raise ValueError('released funding receipt must be explicitly included in current cash')
            if state['last_at'] is None or instant(state['last_at']) < r.proceeds_available_at:
                raise ValueError('funding not released on this ledger clock')
            if any(x['sale_id'] == r.receipt_id for x in state['restricted']):
                raise ValueError('funding remains restricted on this ledger')
        self._original_decision_hash = decision.input_hash
        self._active = Batch(self, decision, plan)
        return self._active

    def apply_calendar_event(self, event):
        if self._active is not None and not self._active.complete:
            raise ValueError('calendar update during unfinished frozen batch unsupported')
        if event.get('kind') not in ('advance', 'pay', 'dividend', 'split', 'close'):
            raise ValueError('only explicit release/payment/action/valuation events; no fabricated deposit')
        before = self.ledger.snapshot(); result = self.ledger.apply(event)
        self.calendar_events.append({'event': deepcopy(event), 'before': before,
                                     'after': self.ledger.snapshot(), 'money': result})
        return result

    def sale_result(self, receipt):
        if receipt.status != 'filled' or receipt.account_name != self.name:
            raise ValueError('accepted sale from this account required')
        batch = self._active
        if batch is None or batch.receipts.get(receipt.order_id) != receipt:
            raise ValueError('sale receipt identity absent from batch')
        order = next(o for o in batch.plan.orders if o.order_id == receipt.order_id)
        if order.side != 'sell': raise ValueError('receipt not a sale')
        binding = self._calendar['opens'][receipt.opening_at][order.symbol]
        r = planner.SaleResult(order.order_id, 'filled', receipt.quantity, receipt.price,
                               receipt.opening_at, binding['proceeds_available_at'], receipt.event_id)
        self._sale_results[r.receipt_id] = r
        return r


def attempt_open(decision, plan, order, opening_evidence, ledger, batch_context):
    batch = batch_context
    if not isinstance(batch, Batch): raise ValueError('account-created batch context required')
    account = batch.account
    before = account.ledger.snapshot(); clock = opening_evidence.at
    money_before = account.ledger.receipt(clock); apply_count = 0
    eid = 'frozen-order:' + order.order_id
    if order.order_id in batch.receipts:
        old = batch.receipts[order.order_id]
        return AttemptReceipt(account.name, order.order_id, eid, 'replay_ignored', old.status,
                              json.dumps(money_before, sort_keys=True), json.dumps(money_before, sort_keys=True),
                              0, True, order.quantity, opening_evidence.price, clock)
    status = 'refused'; reason = ''
    canonical = next((o for o in batch.plan.orders if o.order_id == order.order_id), None)
    if canonical is not None:
        account._attempted_keys.add((batch.plan.decision_hash, canonical.side,
                                     canonical.symbol))
    try:
        if ledger is not account.ledger or account._active is not batch:
            raise ValueError('foreign ledger or batch context')
        if batch.stopped or before != batch.expected:
            batch.stopped = True
            raise ValueError('outside ledger change; batch stopped')
        if (decision != batch.decision or plan != batch.plan
                or plan.decision_hash != decision.input_hash):
            raise ValueError('wrong decision, plan, or cost identity')
        verify_plan(plan)
        if (order not in plan.orders or order.plan_hash != plan.plan_hash
                or opening_evidence.symbol != order.symbol or instant(clock) != order.opening_at):
            raise ValueError('wrong order or opening identity; no resize')
        next_order = next((o for o in plan.orders if o.order_id not in batch.receipts), None)
        if next_order is None or next_order.order_id != order.order_id:
            raise ValueError('frozen serial order sequence differs')
        if (digest(account.ledger._calendar) != account.calendar_hash
                or opening_evidence != account.opening(order.symbol, clock)):
            raise ValueError('calendar evidence identity differs')
        ctx = plan.action_context
        if ctx.covered_from > decision.decision_at or ctx.covered_through < order.opening_at:
            raise ValueError('unknown action coverage')
        actual_actions = [instant(a[k]) for a in account._calendar.get('actions', {}).values()
                          for k in ('split_at', 'dividend_at') if k in a]
        if any(decision.decision_at < t <= order.opening_at for t in ctx.events + tuple(actual_actions)):
            raise ValueError('company action crossing unsupported')
        if order.side == 'buy':
            check = planner.validate_opening_order(plan, order, opening_at=clock,
                                                   price=opening_evidence.price, eligible=opening_evidence.buy)
            if check != 'matches_frozen_buy': raise ValueError(check)
        elif order.side == 'sell':
            if plan.status != 'await_sale' or opening_evidence.sell is not True:
                raise ValueError('sell opening not qualified')
        else: raise ValueError('unknown side')
        event = {'kind': order.side, 'id': eid, 'at': clock, 'symbol': order.symbol,
                 'qty': order.quantity, 'price': opening_evidence.price,
                 'commission_rate': decision.costs.commission,
                 'minimum_commission': decision.costs.minimum,
                 'slippage_rate': decision.costs.slippage}
        apply_count = 1
        account.ledger.apply(event)
        status = 'filled'; batch.expected = account.ledger.snapshot()
    except (ValueError, KeyError, TypeError) as error:
        reason = str(error)
    after = account.ledger.snapshot(); money_after = account.ledger.receipt(clock)
    receipt = AttemptReceipt(account.name, order.order_id, eid, status, reason,
                             json.dumps(money_before, sort_keys=True), json.dumps(money_after, sort_keys=True),
                             apply_count, before == after, order.quantity, opening_evidence.price, clock)
    batch.receipts[order.order_id] = receipt
    return receipt
