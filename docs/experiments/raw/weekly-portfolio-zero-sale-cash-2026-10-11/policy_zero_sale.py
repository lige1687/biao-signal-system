"""Bounded synthetic P1 choice: zero eligible whole-lot sale defers cash."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PolicyDecision:
    status: str
    reason: str
    orders: tuple
    deferred_cash: Decimal
    old_plan: object
    next_scheduled_week: str | None


def decide_p1(planner, decision, cash, actions, *, frozen_at, opening_at,
              next_scheduled_week):
    """Keep the accepted planner's arithmetic; replace only its zero-sale policy."""
    old = planner.plan_p1(
        decision, current_cash=cash, action_context=actions,
        frozen_at=frozen_at, opening_at=opening_at,
    )
    if old.status == "unsupported" and old.reason == "triggered_no_sellable_whole_lot_pending_user":
        return PolicyDecision(
            "defer_cash_to_next_scheduled_week",
            "adjustment_triggered_but_aggregate_eligible_sale_rounds_to_zero",
            (), cash.amount, old, next_scheduled_week,
        )
    if old.status == "ready":
        return PolicyDecision("normal_p0_when_no_adjustment_trigger", old.reason,
                              old.orders, Decimal(0), old, None)
    if old.status == "await_sale":
        return PolicyDecision("await_actual_sale_then_later_buy", old.reason,
                              old.orders, Decimal(0), old, None)
    return PolicyDecision("unsupported", old.reason, (), cash.amount, old, None)


def after_sale(planner, decision, policy, result, cash, *, frozen_at, opening_at):
    if policy.status != "await_actual_sale_then_later_buy":
        raise ValueError("an actual frozen sale plan is required")
    continuation = planner.later_buys(
        decision, policy.old_plan, result, current_cash=cash,
        frozen_at=frozen_at, opening_at=opening_at,
    )
    if continuation.status != "ready":
        return PolicyDecision("failed_sale_cash_retained", continuation.reason, (),
                              cash.amount, continuation, None)
    return PolicyDecision("later_buys_from_actual_sale_receipt", continuation.reason,
                          continuation.orders, Decimal(0), continuation, None)


def deposit_week_once(ledger, day, amount):
    """Only the canonical weekly event ID can issue this synthetic cash inflow."""
    eid = "deposit:" + day
    before = ledger.snapshot()
    if eid in before["ids"]:
        raise ValueError("weekly deposit already applied")
    return ledger.apply({"id": eid, "kind": "deposit", "at": day + "T00:00:00+08:00",
                         "amount": str(amount)})


class ScheduledPolicy:
    """One decision per explicitly supplied synthetic scheduled week."""

    def __init__(self, scheduled_days):
        self.scheduled_days = frozenset(scheduled_days)
        self.decided_days = set()
        self.deferred_until = None

    def decide(self, planner, day, decision, cash, actions, *, frozen_at,
               opening_at, next_scheduled_week):
        if day not in self.scheduled_days or day in self.decided_days:
            raise ValueError("unscheduled or repeated weekly decision")
        if self.deferred_until is not None and day < self.deferred_until:
            raise ValueError("cash deferred until next scheduled week")
        result = decide_p1(planner, decision, cash, actions,
                           frozen_at=frozen_at, opening_at=opening_at,
                           next_scheduled_week=next_scheduled_week)
        self.decided_days.add(day)
        self.deferred_until = result.next_scheduled_week
        return result
