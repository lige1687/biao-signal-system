"""Isolated, deterministic account clock for the bounded two-ETF research scenario.

All events are model events. A stored daily opening is a conditional fill input,
not evidence that an order could actually have traded in the market.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
import json

from order_planning_v2 import (ActionContext, Asset, CashSnapshot, Costs,
                               Decision, SaleResult, later_buys, plan_p0,
                               validate_opening_order)
from policy_startup_approved import decide_p1

SYMBOLS = ("sh510300", "sz159915")
COSTS = Costs(D(".001"), D("5"), D(".001"), "fixed-artificial-research-cost")
TICK = D(".001")
POST_WINDOW_LOCK = "9999-12-31"  # State marker only: never a model session or price date.


def dec(value):
    x = D(str(value))
    if not x.is_finite():
        raise ValueError("finite number required")
    return x


def clock(day, time):
    return datetime.fromisoformat(f"{day}T{time}+08:00")


def fee(qty, price):
    notional = dec(qty) * dec(price)
    return max(notional * COSTS.commission, COSTS.minimum) + notional * COSTS.slippage


def tick(value):
    return dec(value).quantize(TICK, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Dividend:
    event_id: str
    symbol: str
    announcement_date: str
    record_date: str
    ex_date: str
    pay_date: str
    per_share: D

    def __post_init__(self):
        object.__setattr__(self, "per_share", dec(self.per_share))
        if (self.symbol not in SYMBOLS or self.per_share <= 0 or
                not self.announcement_date <= self.record_date < self.ex_date <= self.pay_date):
            raise ValueError("invalid dated cash action")


class Account:
    """Dated money and share state; no broker state or historical authority."""

    def __init__(self, initial_marks, previous_close_day):
        if set(initial_marks) != set(SYMBOLS):
            raise ValueError("both initial known marks required")
        self.cash = D(0)
        self.lots = []
        self.restricted = []
        self.receivables = {}
        self.entitlements = {}
        self.units = D(0)
        self.inflows = D(0)
        self.fees = D(0)
        self.marks = {s: dec(p) for s, p in initial_marks.items()}
        self.mark_age = {s: 0 for s in SYMBOLS}
        self.previous_close_day = previous_close_day
        self.previous_nav = D(1)
        self.deposit_ids = set()
        self.action_phases = set()
        self.order_ids = set()
        self.events = []
        self.rejections = []
        self.cancellations = []
        self.daily = []
        if any(p <= 0 for p in self.marks.values()):
            raise ValueError("positive initial marks required")

    def shares(self, symbol):
        return sum((lot["qty"] for lot in self.lots if lot["symbol"] == symbol), D(0))

    def unlocked(self, symbol, day):
        return sum((lot["qty"] for lot in self.lots
                    if lot["symbol"] == symbol and lot["unlock_day"] <= day), D(0))

    def equity(self):
        return (self.cash + sum((r["amount"] for r in self.restricted), D(0))
                + sum(self.receivables.values(), D(0))
                + sum((self.shares(s) * self.marks[s] for s in SYMBOLS), D(0)))

    def receipt(self, day):
        return {"day": day, "free_cash": str(self.cash),
                "restricted_cash": str(sum((r["amount"] for r in self.restricted), D(0))),
                "receivable": str(sum(self.receivables.values(), D(0))),
                "shares": {s: str(self.shares(s)) for s in SYMBOLS},
                "locked_shares": {s: str(self.shares(s)-self.unlocked(s, day)) for s in SYMBOLS},
                "marks": {s: str(self.marks[s]) for s in SYMBOLS},
                "mark_age": dict(self.mark_age), "equity": str(self.equity()),
                "units": str(self.units), "fees": str(self.fees),
                "inflows": str(self.inflows)}

    def deposit(self, day, amount=D(250)):
        if date.fromisoformat(day).weekday() != 0 or day in self.deposit_ids:
            raise ValueError("weekly Monday deposit already used or unscheduled")
        if self.previous_close_day >= day or self.previous_nav <= 0:
            raise ValueError("prior complete NAV unavailable")
        amount = dec(amount)
        if amount <= 0:
            raise ValueError("positive deposit required")
        self.units += amount / self.previous_nav
        self.cash += amount
        self.inflows += amount
        self.deposit_ids.add(day)
        self.events.append({"kind": "deposit", "day": day, "amount": str(amount),
                            "nav_used": str(self.previous_nav)})

    def release_sale_cash(self, day):
        due = [r for r in self.restricted if r["available_day"] <= day]
        self.cash += sum((r["amount"] for r in due), D(0))
        self.restricted = [r for r in self.restricted if r["available_day"] > day]
        for r in due:
            self.events.append({"kind": "release_sale_cash", "day": day,
                                "sale_id": r["sale_id"], "amount": str(r["amount"])})

    def record(self, action):
        key = (action.event_id, "record")
        if key in self.action_phases:
            raise ValueError("duplicate dividend record")
        self.entitlements[action.event_id] = self.shares(action.symbol)
        self.action_phases.add(key)
        self.events.append({"kind": "record", "day": action.record_date,
                            "action": action.event_id,
                            "eligible_shares": str(self.entitlements[action.event_id])})

    def ex(self, action):
        key = (action.event_id, "ex")
        if key in self.action_phases or (action.event_id, "record") not in self.action_phases:
            raise ValueError("ex requires unique prior record")
        old_mark = self.marks[action.symbol]
        new_mark = old_mark - action.per_share
        if new_mark <= 0:
            raise ValueError("nonpositive ex-dividend reference")
        amount = self.entitlements[action.event_id] * action.per_share
        self.receivables[action.event_id] = amount
        self.marks[action.symbol] = new_mark
        self.action_phases.add(key)
        self.events.append({"kind": "ex", "day": action.ex_date,
                            "action": action.event_id, "receivable": str(amount),
                            "reference_before": str(old_mark), "reference_after": str(new_mark)})

    def pay(self, action, day):
        key = (action.event_id, "pay")
        if key in self.action_phases or (action.event_id, "ex") not in self.action_phases:
            raise ValueError("payment requires unique prior ex")
        if day <= action.pay_date or action.event_id not in self.receivables:
            raise ValueError("payment must follow announced date on a later model day")
        amount = self.receivables.pop(action.event_id)
        self.cash += amount
        self.action_phases.add(key)
        self.events.append({"kind": "pay", "day": day,
                            "action": action.event_id, "amount": str(amount)})

    def buy(self, order, day, opening, unlock_day):
        if order.order_id in self.order_ids or order.side != "buy":
            raise ValueError("duplicate or wrong-side buy")
        q, p = dec(order.quantity), dec(opening)
        if q <= 0 or q % 100 or unlock_day <= day or p <= 0 or p > order.cap:
            raise ValueError("invalid frozen whole-lot buy")
        charge = fee(q, p)
        total = q * p + charge
        if total > self.cash or total > order.budget:
            raise ValueError("buy exceeds actual free cash or frozen budget")
        self.cash -= total
        self.fees += charge
        self.lots.append({"symbol": order.symbol, "qty": q,
                          "unlock_day": unlock_day, "purchase_id": order.order_id})
        self.order_ids.add(order.order_id)
        self.events.append({"kind": "buy", "day": day, "symbol": order.symbol,
                            "qty": str(q), "price": str(p), "fee": str(charge),
                            "order_id": order.order_id})

    def sell(self, order, day, opening, proceeds_day):
        if order.order_id in self.order_ids or order.side != "sell":
            raise ValueError("duplicate or wrong-side sale")
        q, p = dec(order.quantity), dec(opening)
        if (q <= 0 or q % 100 or p <= 0 or q > self.unlocked(order.symbol, day)
                or proceeds_day <= day):
            raise ValueError("sale quantity or release invalid")
        charge = fee(q, p)
        net = q * p - charge
        if net < 0:
            raise ValueError("sale fee exceeds proceeds")
        left = q
        for lot in self.lots:
            if lot["symbol"] == order.symbol and lot["unlock_day"] <= day and left:
                taken = min(left, lot["qty"])
                lot["qty"] -= taken
                left -= taken
        if left:
            raise AssertionError("unlocked sale accounting mismatch")
        self.lots = [lot for lot in self.lots if lot["qty"] > 0]
        self.restricted.append({"amount": net, "available_day": proceeds_day,
                                "sale_id": order.order_id})
        self.fees += charge
        self.order_ids.add(order.order_id)
        self.events.append({"kind": "sell", "day": day, "symbol": order.symbol,
                            "qty": str(q), "price": str(p), "fee": str(charge),
                            "net_restricted": str(net), "order_id": order.order_id})
        return net

    def close(self, day, bars, known_missing=()):
        for symbol in SYMBOLS:
            bar = bars.get(symbol)
            if bar is None:
                if (symbol, day) not in known_missing:
                    raise ValueError("unexplained missing close: " + symbol + " " + day)
                self.mark_age[symbol] += 1
            else:
                value = dec(bar["close"])
                if value <= 0:
                    raise ValueError("nonpositive close")
                self.marks[symbol] = value
                self.mark_age[symbol] = 0
        if self.units <= 0:
            raise ValueError("cannot close before first account unit issued")
        self.previous_nav = self.equity() / self.units
        self.previous_close_day = day
        self.daily.append({"day": day, "unit_nav": str(self.previous_nav),
                           "account": self.receipt(day)})

    def dump_money(self):
        """JSON round trip for a clean boundary without outstanding plans."""
        data = {"cash": str(self.cash), "lots": [{**lot, "qty": str(lot["qty"])}
                 for lot in self.lots], "restricted": [{**r, "amount": str(r["amount"])}
                 for r in self.restricted],
                "receivables": {k: str(v) for k, v in self.receivables.items()},
                "entitlements": {k: str(v) for k, v in self.entitlements.items()},
                "units": str(self.units), "inflows": str(self.inflows),
                "fees": str(self.fees), "marks": {k: str(v) for k, v in self.marks.items()},
                "mark_age": self.mark_age,
                "previous_close_day": self.previous_close_day,
                "previous_nav": str(self.previous_nav),
                "deposit_ids": sorted(self.deposit_ids),
                "action_phases": sorted([list(x) for x in self.action_phases]),
                "order_ids": sorted(self.order_ids)}
        return json.dumps(data, sort_keys=True)

    @classmethod
    def load_money(cls, text):
        data = json.loads(text)
        account = cls(data["marks"], data["previous_close_day"])
        account.cash = dec(data["cash"])
        account.lots = [{**lot, "qty": dec(lot["qty"])} for lot in data["lots"]]
        account.restricted = [{**r, "amount": dec(r["amount"])} for r in data["restricted"]]
        account.receivables = {k: dec(v) for k, v in data["receivables"].items()}
        account.entitlements = {k: dec(v) for k, v in data["entitlements"].items()}
        for key in ("units", "inflows", "fees", "previous_nav"):
            setattr(account, key, dec(data[key]))
        account.mark_age = data["mark_age"]
        account.deposit_ids = set(data["deposit_ids"])
        account.action_phases = {tuple(x) for x in data["action_phases"]}
        account.order_ids = set(data["order_ids"])
        if account.cash < 0 or account.equity() < 0:
            raise ValueError("invalid restored money")
        return account


class PortfolioEngine:
    def __init__(self, policy, bars, model_days, actions, initial_marks,
                 previous_close_day, *, known_missing=(), blocked=()):
        if policy not in ("P0", "P1"):
            raise ValueError("P0/P1 only")
        self.policy = policy
        self.bars = bars
        self.model_days = tuple(sorted(set(model_days)))
        self.actions = tuple(actions)
        self.known_missing = frozenset(known_missing)
        self.blocked = frozenset(blocked)
        self.account = Account(initial_marks, previous_close_day)
        self.pending = None
        self.decided = set()
        self.plans = []

    def next_model(self, day):
        return next((d for d in self.model_days if d > day), None)

    def candidate_this_week(self, day):
        end = day + timedelta(days=7)
        return next((d for d in self.model_days
                     if date.fromisoformat(d) >= end - timedelta(days=7)
                     and date.fromisoformat(d) < end), None)

    def _decision(self, day, candidate):
        if day in self.decided:
            raise ValueError("duplicate weekly decision")
        self.decided.add(day)
        if candidate is None:
            self.plans.append({"day": day, "status": "no_candidate_this_week"})
            return
        known_at = clock(self.account.previous_close_day, "16:00:00")
        decision_at = clock(day, "00:01:00")
        assets = tuple(Asset(s, self.account.marks[s], known_at,
                             self.account.shares(s), self.account.unlocked(s, candidate))
                       for s in SYMBOLS)
        decision = Decision(self.policy + ":" + day, decision_at, known_at,
                            decision_at, self.account.cash,
                            sum((r["amount"] for r in self.account.restricted), D(0)),
                            sum(self.account.receivables.values(), D(0)), assets, COSTS)
        cash = CashSnapshot("account-free-cash", day, self.account.cash,
                            decision_at, decision_at, False, None)
        sunday = (date.fromisoformat(day) + timedelta(days=6)).isoformat()
        known_events = tuple(clock(a.ex_date, "08:00:00") for a in self.actions
                             if a.announcement_date < day and day <= a.ex_date <= sunday)
        context = ActionContext("known-actions", day, decision_at, decision_at,
                                clock(sunday, "23:59:00"), known_events)
        opening = clock(candidate, "09:30:00")
        frozen = clock(candidate, "08:05:00")
        if self.policy == "P0":
            plan = plan_p0(decision, current_cash=cash, action_context=context,
                           frozen_at=frozen, opening_at=opening)
            status, orders = plan.status, plan.orders
        else:
            choice = decide_p1(__import__("order_planning_v2"), decision, cash, context,
                               frozen_at=frozen, opening_at=opening,
                               next_scheduled_week=(date.fromisoformat(day)+timedelta(days=7)).isoformat())
            plan, status, orders = choice.old_plan, choice.status, choice.orders
        self.plans.append({"day": day, "candidate": candidate, "status": status,
                           "reason": plan.reason, "orders": len(orders)})
        if orders and status in ("ready", "buy_when_no_sale_required",
                                 "normal_p0_when_no_adjustment_trigger",
                                 "await_actual_sale_then_later_buy"):
            self.pending = {"kind": "initial", "day": candidate, "week": day,
                            "decision": decision, "plan": plan, "orders": orders,
                            "context": context}

    def _band(self, symbol, day):
        fraction = D(".20") if symbol == "sz159915" and day >= "2020-08-24" else D(".10")
        reference = self.account.marks[symbol]
        return tick(reference * (1-fraction)), tick(reference * (1+fraction))

    def _opening(self, symbol, day):
        if (symbol, day) in self.blocked:
            return None, "blocked_open"
        bar = self.bars.get(day, {}).get(symbol)
        if bar is None:
            return None, "missing_open"
        opening = dec(bar["open"])
        low, high = self._band(symbol, day)
        if opening <= 0 or opening < low or opening > high or opening != tick(opening):
            return None, "open_outside_prior_legal_band_or_tick"
        return opening, "qualified_model_open"

    def _attempt(self, day):
        pending = self.pending
        if pending is None or pending["day"] != day:
            return
        plan = pending["plan"]
        for order in pending["orders"]:
            opening, reason = self._opening(order.symbol, day)
            if opening is None:
                self.account.rejections.append({"day": day, "symbol": order.symbol,
                                                "side": order.side, "reason": reason})
                if order.side == "sell":
                    break
                continue
            low, high = self._band(order.symbol, day)
            if order.side == "buy" and opening == high:
                self.account.rejections.append({"day": day, "symbol": order.symbol,
                                                "side": "buy", "reason": "at_upper_limit"})
                continue
            if order.side == "sell" and opening == low:
                self.account.rejections.append({"day": day, "symbol": order.symbol,
                                                "side": "sell", "reason": "at_lower_limit"})
                break
            if order.side == "buy":
                result = validate_opening_order(plan, order, opening_at=clock(day, "09:30:00"),
                                                price=opening, eligible=True)
                if result != "matches_frozen_buy":
                    self.account.rejections.append({"day": day, "symbol": order.symbol,
                                                    "side": "buy", "reason": result})
                    continue
                unlock = self.next_model(day) or POST_WINDOW_LOCK
                self.account.buy(order, day, opening, unlock)
            else:
                if opening < low:
                    self.account.rejections.append({"day": day, "symbol": order.symbol,
                                                    "side": "sell", "reason": "below_frozen_sell_limit"})
                    break
                release = self.next_model(day) or POST_WINDOW_LOCK
                self.account.sell(order, day, opening, release)
                if date.fromisoformat(release) >= date.fromisoformat(pending["week"])+timedelta(days=7):
                    self.account.cancellations.append({"day": release, "reason": "later_buy_new_week_expiry"})
                    break
                receipt = SaleResult(order.order_id, "filled", order.quantity, opening,
                                     clock(day, "09:30:00"), clock(release, "08:00:00"),
                                     order.order_id + ":filled")
                self.pending = {"kind": "later", "day": release,
                                "week": pending["week"], "decision": pending["decision"],
                                "plan": plan, "sale_receipt": receipt, "orders": ()}
                return
        self.pending = None

    def _freeze_later(self, day):
        pending = self.pending
        if pending is None or pending["kind"] != "later" or pending["day"] != day:
            return
        receipt = pending["sale_receipt"]
        snapshot = CashSnapshot("actual-sale-released-cash", receipt.receipt_id,
                                self.account.cash, clock(day, "08:00:00"),
                                clock(day, "08:00:00"), True, receipt.receipt_id)
        result = later_buys(pending["decision"], pending["plan"], receipt,
                            current_cash=snapshot, frozen_at=clock(day, "08:05:00"),
                            opening_at=clock(day, "09:30:00"))
        if result.status != "ready":
            self.account.cancellations.append({"day": day, "reason": result.reason})
            self.pending = None
            return
        pending["plan"] = result
        pending["orders"] = result.orders
        pending["kind"] = "later_ready"

    def run(self, start, end):
        current = date.fromisoformat(start)
        last = date.fromisoformat(end)
        if current > last:
            raise ValueError("ordered window required")
        model = set(self.model_days)
        while current <= last:
            day = current.isoformat()
            if current.weekday() == 0:
                if self.pending:
                    self.account.cancellations.append({"day": day, "reason": "weekly_expiry",
                                                       "pending_kind": self.pending["kind"]})
                    self.pending = None
                self.account.deposit(day)
                candidate = next((d for d in self.model_days
                                  if day <= d < (current+timedelta(days=7)).isoformat()), None)
                self._decision(day, candidate)
            if day in model:
                for action in self.actions:
                    if action.ex_date == day:
                        self.account.ex(action)
                        if self.pending:
                            self.account.cancellations.append({"day": day,
                                                               "reason": "ex_crossed_unexecuted_plan",
                                                               "action": action.event_id})
                            self.pending = None
                self.account.release_sale_cash(day)
                for action in self.actions:
                    if (action.pay_date < day and (action.event_id, "ex") in self.account.action_phases
                            and (action.event_id, "pay") not in self.account.action_phases):
                        self.account.pay(action, day)
                self._freeze_later(day)
                self._attempt(day)
                self.account.close(day, self.bars.get(day, {}), self.known_missing)
                for action in self.actions:
                    if action.record_date == day:
                        self.account.record(action)
            current += timedelta(days=1)
        return {"policy": self.policy, "start": start, "end": end,
                "terminal": self.account.receipt(end), "deposits": len(self.account.deposit_ids),
                "plans": self.plans, "events": self.account.events,
                "rejections": self.account.rejections,
                "cancellations": self.account.cancellations,
                "daily": self.account.daily,
                "pending": None if self.pending is None else {"kind": self.pending["kind"],
                                                               "day": self.pending["day"]}}
