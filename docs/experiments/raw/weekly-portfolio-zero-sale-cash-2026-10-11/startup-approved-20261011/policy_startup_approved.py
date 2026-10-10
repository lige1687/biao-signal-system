"""Bounded artificial P1 policy for an approved no-required-sale decision."""

from decimal import Decimal as D

from policy_zero_sale import PolicyDecision, deposit_week_once


def decide_p1(planner, decision, cash, actions, *, frozen_at, opening_at,
              next_scheduled_week):
    old = planner.plan_p1(
        decision, current_cash=cash, action_context=actions,
        frozen_at=frozen_at, opening_at=opening_at,
    )
    if old.status == "unsupported" and old.reason == "triggered_no_sellable_whole_lot_pending_user":
        total = (decision.free + decision.restricted + decision.receivable
                 + sum((a.held * a.reference for a in decision.assets), D(0)))
        required_excess = tuple(
            (a.symbol, max(D(0), a.held * a.reference - total * a.target))
            for a in decision.assets
        )
        if not any(excess > 0 for _, excess in required_excess):
            original_buy = planner.plan_p0(
                decision, current_cash=cash, action_context=actions,
                frozen_at=frozen_at, opening_at=opening_at,
            )
            if original_buy.status != "ready":
                return PolicyDecision("unsupported", original_buy.reason, (),
                                      cash.amount, original_buy, None)
            return PolicyDecision("buy_when_no_sale_required", original_buy.reason,
                                  original_buy.orders, D(0), original_buy, None)
        return PolicyDecision("defer_cash_to_next_scheduled_week",
                              "required_excess_but_no_eligible_whole_lot_sale",
                              (), cash.amount, old, next_scheduled_week)
    if old.status == "ready":
        return PolicyDecision("normal_p0_when_no_adjustment_trigger", old.reason,
                              old.orders, D(0), old, None)
    if old.status == "await_sale":
        return PolicyDecision("await_actual_sale_then_later_buy", old.reason,
                              old.orders, D(0), old, None)
    return PolicyDecision("unsupported", old.reason, (), cash.amount, old, None)


class ScheduledPolicy:
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
