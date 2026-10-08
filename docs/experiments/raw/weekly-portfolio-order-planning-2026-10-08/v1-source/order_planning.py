"""Pure immutable synthetic v0.2 order arithmetic; no ledger or market IO."""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib,json


def num(v):
    x=D(str(v))
    if not x.is_finite() or x<0: raise ValueError('finite nonnegative input required')
    return x


def at(v):
    t=datetime.fromisoformat(v) if isinstance(v,str) else v
    if not isinstance(t,datetime) or t.utcoffset() is None: raise ValueError('aware time required')
    return t


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


@dataclass(frozen=True)
class Costs:
    commission: D
    minimum: D
    slippage: D
    name: str
    def __post_init__(self):
        for n in ('commission','minimum','slippage'): object.__setattr__(self,n,num(getattr(self,n)))
        if not self.name: raise ValueError('named cost scenario required')


def cost(q,p,c):
    q,p=num(q),num(p)
    if q==0: return D(0)
    with localcontext() as ctx:
        ctx.prec=80
        n=q*p
        return n+max(n*c.commission,c.minimum)+n*c.slippage


def affordable_quantity(budget,price,c):
    b,p=num(budget),num(price)
    if p<=0: raise ValueError('positive reference required')
    # Both arms of max(commission, floor) must fit. Fraction avoids rounded
    # division accidentally crossing the exact 100-share boundary.
    variable=F(b)/(F(p)*(1+F(c.commission)+F(c.slippage)))
    floor=(F(b)-F(c.minimum))/(F(p)*(1+F(c.slippage)))
    bound=max(F(0),min(variable,floor))
    return D((bound.numerator//(bound.denominator*100))*100)


def price_cap(budget,quantity,c):
    b,q=num(budget),num(quantity)
    if q<=0 or q%100: raise ValueError('positive whole-lot quantity required')
    variable=F(b)/(F(q)*(1+F(c.commission)+F(c.slippage)))
    floor=(F(b)-F(c.minimum))/(F(q)*(1+F(c.slippage)))
    bound=min(variable,floor)
    if bound<=0: raise ValueError('no positive affordable cap')
    ticks=bound.numerator*1000//bound.denominator
    if ticks<=0: raise ValueError('no positive price tick affordable')
    return D(ticks)/1000


@dataclass(frozen=True)
class Asset:
    symbol:str
    reference:D
    known_at:datetime
    held:D
    sellable:D
    target:D=D('.5')
    def __post_init__(self):
        for n in ('reference','held','sellable','target'):object.__setattr__(self,n,num(getattr(self,n)))
        object.__setattr__(self,'known_at',at(self.known_at))
        if not self.symbol or self.reference<=0 or self.sellable>self.held or self.target!=D('.5'):
            raise ValueError('v0.2 two-product half targets, positive price, valid holdings required')


@dataclass(frozen=True)
class Decision:
    name:str
    decision_at:datetime
    holdings_known_at:datetime
    cash_available_at:datetime
    free:D
    restricted:D
    receivable:D
    assets:tuple
    costs:Costs
    future_inflow:D=D(0)
    input_hash:str=field(init=False)
    def __post_init__(self):
        for n in ('decision_at','holdings_known_at','cash_available_at'):object.__setattr__(self,n,at(getattr(self,n)))
        for n in ('free','restricted','receivable','future_inflow'):object.__setattr__(self,n,num(getattr(self,n)))
        object.__setattr__(self,'assets',tuple(self.assets))
        if (not self.name or not isinstance(self.costs,Costs) or len(self.assets)!=2 or
                any(not isinstance(a,Asset) for a in self.assets) or
                len({a.symbol for a in self.assets})!=2):raise ValueError('named distinct two-product snapshot required')
        if (max(self.holdings_known_at,self.cash_available_at)>self.decision_at or
                any(a.known_at>self.decision_at for a in self.assets)):
            raise ValueError('decision uses future information or future free cash')
        object.__setattr__(self,'input_hash',fingerprint({'name':self.name,'decision_at':self.decision_at,'holdings_known_at':self.holdings_known_at,'cash_available_at':self.cash_available_at,'free':self.free,'restricted':self.restricted,'receivable':self.receivable,'assets':[asdict(a) for a in self.assets],'costs':asdict(self.costs),'future_inflow':self.future_inflow}))


def values(d):
    with localcontext() as ctx:
        ctx.prec=80
        total=d.free+d.restricted+d.receivable+sum((a.held*a.reference for a in d.assets),D(0))
        gaps=tuple((a.symbol,max(D(0),total*a.target-a.held*a.reference)) for a in d.assets)
    return total,tuple(sorted(gaps,key=lambda r:(-r[1],r[0])))


@dataclass(frozen=True)
class Order:
    order_id:str
    input_hash:str
    symbol:str
    side:str
    quantity:D
    reference:D
    budget:D
    cap:D|None
    frozen_at:datetime
    opening_at:datetime


@dataclass(frozen=True)
class Plan:
    input_hash:str
    status:str
    reason:str
    ordering:tuple
    budgets:tuple
    orders:tuple
    unallocated:D


def timeline(d,frozen_at,opening_at,actions):
    frozen_at,opening_at=at(frozen_at),at(opening_at)
    if not d.decision_at<=frozen_at<opening_at:raise ValueError('freeze must follow decision and precede opening')
    if any(d.decision_at<at(t)<=opening_at for t in actions):
        return 'unsupported_company_action_crossing'
    return ''


def _buys(d,cash,frozen_at,opening_at,actions=()):
    reason=timeline(d,frozen_at,opening_at,actions)
    _,gaps=values(d)
    if reason:return Plan(d.input_hash,'unsupported',reason,gaps,(),(),num(cash))
    remaining=num(cash); budgets=[]; orders=[]
    assets={a.symbol:a for a in d.assets}
    for symbol,gap in gaps:
        budget=min(gap,remaining);remaining-=budget;budgets.append((symbol,budget))
        a=assets[symbol];q=affordable_quantity(budget,a.reference,d.costs)
        if q:
            cap=price_cap(budget,q,d.costs)
            oid=fingerprint((d.input_hash,'buy',symbol,str(at(opening_at))))
            orders.append(Order(oid,d.input_hash,symbol,'buy',q,a.reference,budget,cap,at(frozen_at),at(opening_at)))
    return Plan(d.input_hash,'ready','frozen budgets; residual not reallocated',gaps,tuple(budgets),tuple(orders),remaining)


def plan_p0(d,*,frozen_at,opening_at,actions=()):
    return _buys(d,d.free,frozen_at,opening_at,actions)


def plan_p1(d,*,frozen_at,opening_at,actions=()):
    reason=timeline(d,frozen_at,opening_at,actions);total,gaps=values(d)
    if reason:return Plan(d.input_hash,'unsupported',reason,gaps,(),(),d.free)
    if total==0:return plan_p0(d,frozen_at=frozen_at,opening_at=opening_at,actions=actions)
    triggered=any(abs(F(a.held*a.reference)/F(total)-F(a.target))>=F(D('.05')) for a in d.assets)
    if not triggered:return plan_p0(d,frozen_at=frozen_at,opening_at=opening_at,actions=actions)
    sales=[]
    for a in sorted(d.assets,key=lambda a:a.symbol):
        excess=max(D(0),a.held*a.reference-total*a.target)
        bound=min(F(excess)/F(a.reference),F(a.sellable))
        q=D(bound.numerator//(bound.denominator*100)*100)
        if q:
            oid=fingerprint((d.input_hash,'sell',a.symbol,str(at(opening_at))))
            sales.append(Order(oid,d.input_hash,a.symbol,'sell',q,a.reference,D(0),None,at(frozen_at),at(opening_at)))
    if not sales:return Plan(d.input_hash,'unsupported','triggered_no_sellable_whole_lot_pending_user',gaps,(),(),d.free)
    if len(sales)!=1:return Plan(d.input_hash,'unsupported','multiple_sales_execution_not_defined',gaps,(),(),d.free)
    return Plan(d.input_hash,'await_sale','actual later proceeds required',gaps,(),tuple(sales),d.free)


@dataclass(frozen=True)
class SaleResult:
    order_id:str
    status:str
    quantity:D
    price:D
    sold_at:datetime
    proceeds_available_at:datetime
    receipt_id:str
    def __post_init__(self):
        for n in ('quantity','price'):object.__setattr__(self,n,num(getattr(self,n)))
        for n in ('sold_at','proceeds_available_at'):object.__setattr__(self,n,at(getattr(self,n)))
        if not self.receipt_id or self.proceeds_available_at<self.sold_at:raise ValueError('bound receipt and payment time required')


def later_buys(d,sale_plan,result,*,frozen_at,opening_at,actions=()):
    # Pure arithmetic only; SaleResult is explicitly supplied synthetic evidence.
    if sale_plan.input_hash!=d.input_hash or sale_plan.status!='await_sale' or len(sale_plan.orders)!=1:
        raise ValueError('matching original single-sale plan required')
    sale=sale_plan.orders[0]
    if result.order_id!=sale.order_id or result.sold_at!=sale.opening_at:
        raise ValueError('sale receipt does not match frozen order identity or opening')
    if result.status!='filled':
        return Plan(d.input_hash,'unsupported','failed_or_partial_sale_no_chase',sale_plan.ordering,(),(),d.free)
    if result.quantity!=sale.quantity or result.price<=0:raise ValueError('full fixed sale quantity and valid actual price required')
    frozen_at,opening_at=at(frozen_at),at(opening_at)
    if result.proceeds_available_at>frozen_at or opening_at<=result.sold_at or frozen_at<result.sold_at:
        raise ValueError('actual proceeds not available before freezing later opening')
    net=result.quantity*result.price-(cost(result.quantity,result.price,d.costs)-result.quantity*result.price)
    actual_cash=d.free+net
    if actual_cash<0:raise ValueError('sale fee deficit exceeds original free cash')
    return _buys(d,actual_cash,frozen_at,opening_at,actions)


def validate_opening_order(plan,order,*,opening_at,price,eligible,proposed_quantity=None):
    if order not in plan.orders or order.input_hash!=plan.input_hash:raise ValueError('order not in frozen plan')
    if at(opening_at)!=order.opening_at or not order.frozen_at<at(opening_at):raise ValueError('opening differs from frozen order')
    if eligible is not True: return 'reject_product_not_eligible'
    if proposed_quantity is not None and num(proposed_quantity)!=order.quantity:return 'reject_no_resize'
    p=num(price)
    if p<=0:return 'reject_missing_opening_price'
    if order.side!='buy':return 'unsupported_sell_execution_qualification'
    if p>order.cap:return 'reject_no_resize'
    return 'matches_frozen_buy'
