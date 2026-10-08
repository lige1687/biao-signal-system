"""Pure planning repair. Current cash and inherited action evidence mandatory."""
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal as D
import order_planning as _v1

Costs = _v1.Costs
Asset = _v1.Asset
Decision = _v1.Decision
SaleResult = _v1.SaleResult
cost = _v1.cost
affordable_quantity = _v1.affordable_quantity
price_cap = _v1.price_cap


@dataclass(frozen=True)
class CashSnapshot:
    name: str
    source_id: str
    amount: D
    known_at: datetime
    available_at: datetime
    includes_sale_proceeds: bool
    included_receipt_id: str | None

    def __post_init__(self):
        object.__setattr__(self, 'amount', _v1.num(self.amount))
        for n in ('known_at', 'available_at'):
            object.__setattr__(self, n, _v1.at(getattr(self, n)))
        if (not self.name or not self.source_id or type(self.includes_sale_proceeds) is not bool
                or self.includes_sale_proceeds != bool(self.included_receipt_id)):
            raise ValueError('named cash source and explicit sale inclusion receipt required')


@dataclass(frozen=True)
class ActionContext:
    name: str
    source_id: str
    known_at: datetime
    covered_from: datetime
    covered_through: datetime
    events: tuple

    def __post_init__(self):
        for n in ('known_at', 'covered_from', 'covered_through'):
            object.__setattr__(self, n, _v1.at(getattr(self, n)))
        object.__setattr__(self, 'events', tuple(sorted(_v1.at(t) for t in self.events)))
        if (not self.name or not self.source_id or self.covered_from > self.covered_through
                or any(not self.covered_from <= t <= self.covered_through for t in self.events)):
            raise ValueError('named covered interval and in-coverage action clocks required')


@dataclass(frozen=True)
class Order:
    order_id: str
    decision_hash: str
    plan_hash: str
    symbol: str
    side: str
    quantity: D
    reference: D
    budget: D
    cap: D | None
    frozen_at: datetime
    opening_at: datetime


@dataclass(frozen=True)
class Plan:
    decision_hash: str
    plan_hash: str
    status: str
    reason: str
    ordering: tuple
    budgets: tuple
    orders: tuple
    unallocated: D
    current_cash: CashSnapshot
    action_context: ActionContext
    funding_receipt: SaleResult | None
    frozen_at: datetime
    opening_at: datetime


def _evidence(d, cash, context, frozen_at, opening_at, initial=False):
    frozen_at, opening_at = _v1.at(frozen_at), _v1.at(opening_at)
    if not d.decision_at <= frozen_at < opening_at:
        raise ValueError('freeze must precede opening after decision')
    if not isinstance(cash, CashSnapshot) or not isinstance(context, ActionContext):
        raise ValueError('current cash and immutable action context required')
    if max(cash.known_at, cash.available_at) > frozen_at:
        raise ValueError('current cash evidence not yet known or available')
    if context.known_at > d.decision_at:
        raise ValueError('action evidence not known at original decision')
    if initial and (cash.amount != d.free or cash.includes_sale_proceeds
                    or max(cash.known_at, cash.available_at) > d.decision_at):
        raise ValueError('initial snapshot must bind original known free cash excluding sale')
    if context.covered_from > d.decision_at or context.covered_through < opening_at:
        return 'unsupported_action_coverage_unknown'
    if any(d.decision_at < t <= opening_at for t in context.events):
        return 'unsupported_company_action_crossing'
    return ''


def _build(d, base, cash, context, receipt, frozen_at, opening_at):
    frozen_at, opening_at = _v1.at(frozen_at), _v1.at(opening_at)
    content = {
        'decision_hash': d.input_hash, 'cash': asdict(cash), 'actions': asdict(context),
        'funding_receipt': asdict(receipt) if receipt else None,
        'frozen_at': frozen_at, 'opening_at': opening_at,
        'complete_plan': {
            'status': base.status, 'reason': base.reason, 'ordering': base.ordering,
            'budgets': base.budgets, 'unallocated': base.unallocated,
            'orders': [{k: v for k, v in asdict(o).items()
                        if k not in ('order_id', 'input_hash')} for o in base.orders]}}
    ph = _v1.fingerprint(content)
    orders = tuple(Order(_v1.fingerprint((ph, i, o.symbol, o.side)), d.input_hash, ph,
                         o.symbol, o.side, o.quantity, o.reference, o.budget, o.cap,
                         o.frozen_at, o.opening_at) for i, o in enumerate(base.orders))
    return Plan(d.input_hash, ph, base.status, base.reason, base.ordering, base.budgets,
                orders, base.unallocated, cash, context, receipt, frozen_at, opening_at)


def _unsupported(d, reason, cash, context, receipt, frozen_at, opening_at):
    _, gaps = _v1.values(d)
    base = _v1.Plan(d.input_hash, 'unsupported', reason, gaps, (), (), cash.amount)
    return _build(d, base, cash, context, receipt, frozen_at, opening_at)


def plan_p0(d, *, current_cash, action_context, frozen_at, opening_at):
    reason = _evidence(d, current_cash, action_context, frozen_at, opening_at, initial=True)
    if reason:
        return _unsupported(d, reason, current_cash, action_context, None, frozen_at, opening_at)
    base = _v1.plan_p0(d, frozen_at=frozen_at, opening_at=opening_at, actions=action_context.events)
    return _build(d, base, current_cash, action_context, None, frozen_at, opening_at)


def plan_p1(d, *, current_cash, action_context, frozen_at, opening_at):
    reason = _evidence(d, current_cash, action_context, frozen_at, opening_at, initial=True)
    if reason:
        return _unsupported(d, reason, current_cash, action_context, None, frozen_at, opening_at)
    base = _v1.plan_p1(d, frozen_at=frozen_at, opening_at=opening_at, actions=action_context.events)
    return _build(d, base, current_cash, action_context, None, frozen_at, opening_at)


def later_buys(d, sale_plan, result, *, current_cash, frozen_at, opening_at):
    # No action argument or empty default: immutable original coverage is inherited.
    if (not isinstance(sale_plan, Plan) or sale_plan.decision_hash != d.input_hash
            or sale_plan.status != 'await_sale' or len(sale_plan.orders) != 1
            or not isinstance(result, SaleResult)):
        raise ValueError('matching original single-sale plan and receipt required')
    context = sale_plan.action_context
    reason = _evidence(d, current_cash, context, frozen_at, opening_at)
    if reason:
        return _unsupported(d, reason, current_cash, context, result, frozen_at, opening_at)
    sale = sale_plan.orders[0]
    if result.order_id != sale.order_id or result.sold_at != sale.opening_at:
        raise ValueError('receipt identity or sale opening differs')
    if result.status != 'filled':
        return _unsupported(d, 'failed_or_partial_sale_no_chase', current_cash,
                            context, result, frozen_at, opening_at)
    if result.quantity != sale.quantity or result.price <= 0:
        raise ValueError('full fixed quantity and actual sale price required')
    frozen_at, opening_at = _v1.at(frozen_at), _v1.at(opening_at)
    if (result.proceeds_available_at > frozen_at or opening_at <= result.sold_at
            or frozen_at < result.sold_at):
        raise ValueError('actual sale proceeds unavailable before later frozen opening')
    if current_cash.includes_sale_proceeds:
        if (current_cash.included_receipt_id != result.receipt_id
                or current_cash.known_at < result.sold_at
                or current_cash.available_at < result.proceeds_available_at):
            raise ValueError('current cash sale-inclusion receipt or time mismatch')
        amount = current_cash.amount
    else:
        # Add exactly this sale net to explicitly supplied current cash, never old d.free.
        net = 2 * result.quantity * result.price - cost(result.quantity, result.price, d.costs)
        amount = current_cash.amount + net
        if amount < 0:
            raise ValueError('sale fees exceed current allocatable cash')
    base = _v1._buys(d, amount, frozen_at, opening_at, context.events)
    return _build(d, base, current_cash, context, result, frozen_at, opening_at)


def validate_opening_order(plan, order, *, opening_at, price, eligible, proposed_quantity=None):
    if (order not in plan.orders or order.plan_hash != plan.plan_hash
            or order.decision_hash != plan.decision_hash):
        raise ValueError('order differs from complete frozen plan identity')
    if _v1.at(opening_at) != order.opening_at or not order.frozen_at < _v1.at(opening_at):
        raise ValueError('opening differs from frozen order')
    if eligible is not True:
        return 'reject_product_not_eligible'
    if proposed_quantity is not None and _v1.num(proposed_quantity) != order.quantity:
        return 'reject_no_resize'
    p = _v1.num(price)
    if p <= 0:
        return 'reject_missing_opening_price'
    if order.side != 'buy':
        return 'unsupported_sell_execution_qualification'
    if p > order.cap:
        return 'reject_no_resize'
    return 'matches_frozen_buy'
