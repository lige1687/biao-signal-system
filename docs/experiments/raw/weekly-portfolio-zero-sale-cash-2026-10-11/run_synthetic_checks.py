"""One bounded artificial-account replay; no market or network input."""
import hashlib
import json
import os
import sys
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD_ORDERS = ROOT / "docs/experiments/raw/weekly-portfolio-order-planning-2026-10-08"
OLD_LEDGER = ROOT / "docs/experiments/raw/weekly-portfolio-dated-execution-2026-10-08"
EXPECTED = {
    OLD_ORDERS / "order_planning.py": "645cac7faa6fc25bd95e0c25b63621d4e233b501a6d0b946895ff685b584a75a",
    OLD_ORDERS / "order_planning_v2.py": "a9ab958fa737fc53e7a08905da9ffd82b40687354f2b8be2d508db121a13b958",
    OLD_LEDGER / "dated_ledger.py": "20f6547deea6d19c6416daa6048ee18a7111ff6bf4c7b21bbae90a7b379e62d3",
    ROOT / "docs/experiments/raw/weekly-portfolio-dated-execution-2026-10-08/source-baseline/shared-account-spec.md": "695ce8a18e34d3520c53f793b1f347a05e146fea345474b5d72224ba93c30a5a",
    Path("/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术交易体系.md"): "df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20",
    Path("/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术实现.md"): "85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for path, expected in EXPECTED.items():
    if digest(path) != expected:
        raise RuntimeError("frozen source changed: " + str(path))
sys.path[:0] = [str(OLD_ORDERS), str(OLD_LEDGER), str(HERE)]
import order_planning_v2 as planning
import dated_ledger as dated
import policy_zero_sale as policy

T = lambda day, clock: f"2026-01-{day}T{clock}+08:00"
DAY5, DAY12 = "2026-01-05", "2026-01-12"
COSTS = planning.Costs(D(".001"), D("5"), D(".001"), "artificial-fees")


def check(ok, message):
    if not ok:
        raise AssertionError(message)


def opening(price, *, buy=False, sell=False, observed=None, decision=None,
            release=None, proceeds=None):
    return {"price": str(price), "buy": buy, "sell": sell,
            "observed_at": observed or T("02", "15:00:00"),
            "decision_at": decision or T("05", "08:00:00"),
            "release_at": release or T("13", "09:30:00"),
            "proceeds_available_at": proceeds or T("06", "09:30:00")}


def ledger_a(*, a_qty=100, b_qty=10000, b_price=".7", a_release=None,
             sale_allowed=False, second_week=False):
    clocks = {T("05", "00:00:00"): [0], T("05", "09:30:00"): [3],
              T("06", "09:30:00"): [3], T("06", "10:00:00"): [3],
              T("09", "15:00:00"): [4],
              T("12", "00:00:00"): [0], T("12", "09:30:00"): [3],
              T("13", "09:30:00"): [3]}
    calendar = {"name": "finite-artificial-two-week-calendar", "timezone": "Asia/Shanghai",
                "clocks": clocks,
                "closes": {T("02", "15:00:00"): {"A": "100", "B": str(b_price)},
                           T("09", "15:00:00"): {"A": "100", "B": "1"}},
                "opens": {
                    T("05", "09:30:00"): {"A": opening("100", sell=sale_allowed)},
                    T("06", "10:00:00"): {"B": opening("1", buy=True,
                          observed=T("05", "15:00:00"), decision=T("06", "09:30:00"),
                          release=T("07", "09:30:00"))},
                    T("12", "09:30:00"): {"B": opening("1", buy=True,
                          observed=T("09", "15:00:00"), decision=T("12", "08:00:00"),
                          release=T("13", "09:30:00"))}}}
    clocks[T("07", "09:30:00")] = [3]
    lots = [{"symbol": "A", "qty": str(a_qty),
             "release_at": a_release or T("02", "09:30:00"), "purchase_id": "opening-A"},
            {"symbol": "B", "qty": str(b_qty),
             "release_at": T("02", "09:30:00"), "purchase_id": "opening-B"}]
    return dated.Ledger(calendar, cash=0, lots=lots,
                        units=D(a_qty)*100 + D(b_qty)*D(b_price),
                        prior_complete={"at": T("02", "15:00:00"), "nav": "1"},
                        marks={"A": "100", "B": str(b_price)})


def decision(ledger, *, day, a_price, b_price, opening_at, name):
    clock = T(day, "08:00:00")
    s = ledger.snapshot()
    a = planning.Asset("A", D(a_price), clock, ledger.shares("A"),
                       ledger.sellable("A", opening_at))
    b = planning.Asset("B", D(b_price), clock, ledger.shares("B"),
                       ledger.sellable("B", opening_at))
    d = planning.Decision(name, clock, clock, clock, s["cash"],
        sum((r["amount"] for r in s["restricted"]), D(0)),
        sum((r["amount"] for r in s["receivables"].values()), D(0)),
        (a, b), COSTS)
    cash = planning.CashSnapshot("ledger-free-cash", name, s["cash"],
                               clock, clock, False, None)
    actions = planning.ActionContext("explicit-empty-actions", name, clock,
        T("02", "15:00:00"), T("13", "15:00:00"), ())
    return d, cash, actions


def decide(session, ledger, day, prices, name, next_day):
    opening_at = T(day[-2:], "09:30:00")
    d, cash, actions = decision(ledger, day=day[-2:], a_price=prices[0],
                               b_price=prices[1], opening_at=opening_at, name=name)
    result = session.decide(planning, day, d, cash, actions,
        frozen_at=T(day[-2:], "09:00:00"), opening_at=opening_at,
        next_scheduled_week=next_day)
    return d, cash, actions, result


def buy_event(order, event_id):
    return {"id": event_id, "kind": "buy", "at": order.opening_at.isoformat(),
            "symbol": order.symbol, "qty": str(order.quantity), "price": str(order.reference),
            "commission_rate": ".001", "minimum_commission": "5", "slippage_rate": ".001"}


def replay_zero_then_next():
    l = ledger_a()
    session = policy.ScheduledPolicy((DAY5, DAY12))
    policy.deposit_week_once(l, DAY5, 250)
    d, cash, acts, first = decide(session, l, DAY5, ("100", ".7"), "zero-lot", DAY12)
    check(first.status == "defer_cash_to_next_scheduled_week" and not first.orders,
          "zero-sale policy did not stop same-week buys")
    check(l.snapshot()["cash"] == D(250) and l.shares("A") == 100 and l.shares("B") == 10000,
          "week-one cash or holdings moved")
    before = l.snapshot()
    try:
        session.decide(planning, DAY5, d, cash, acts,
            frozen_at=T("05", "09:00:00"), opening_at=T("05", "09:30:00"),
            next_scheduled_week=DAY12)
    except ValueError:
        pass
    else:
        raise AssertionError("same-week P0 fallback accepted")
    check(l.snapshot() == before, "duplicate decision changed ledger")
    l.apply({"id": "close:2026-01-09", "kind": "close", "at": T("09", "15:00:00")})
    policy.deposit_week_once(l, DAY12, 250)
    before_duplicate = l.snapshot()
    try:
        policy.deposit_week_once(l, DAY12, 250)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate weekly deposit accepted")
    check(l.snapshot() == before_duplicate and l.snapshot()["inflows"] == D(500),
          "weekly deposit doubled or mutated on rejection")
    _, _, _, second = decide(session, l, DAY12, ("100", "1"), "next-week", "2026-01-19")
    check(second.status == "normal_p0_when_no_adjustment_trigger", "next-week P0 branch absent")
    check(len(second.orders) == 1 and second.orders[0].symbol == "B"
          and second.orders[0].quantity == D(200), "next-week fixed order differs")
    order = second.orders[0]
    check(planning.validate_opening_order(second.old_plan, order,
          opening_at=order.opening_at, price=D(1), eligible=True) == "matches_frozen_buy",
          "fixed opening order rejected")
    l.apply(buy_event(order, "buy:B:2026-01-12"))
    check(l.snapshot()["cash"] == D("294.8") and l.shares("B") == D(10200),
          "next-week cash or position differs")
    return {"scenario": "zero_lot_then_next_scheduled_week", "pass": True,
            "week1_status": first.status, "week1_receipt": first.deferred_cash.to_eng_string(),
            "week2_status": second.status, "final": l.receipt(T("12", "09:30:00")),
            "accepted_events": sum(a["accepted"] for a in l.audit),
            "rejected_events": sum(not a["accepted"] for a in l.audit)}


def replay_unreleased():
    l = ledger_a(a_release=T("06", "09:30:00"))
    policy.deposit_week_once(l, DAY5, 250)
    session = policy.ScheduledPolicy((DAY5,))
    _, _, _, result = decide(session, l, DAY5, ("100", ".7"), "unreleased", DAY12)
    check(result.status == "defer_cash_to_next_scheduled_week" and not result.orders,
          "unreleased zero-sale branch absent")
    check(l.sellable("A", T("05", "09:30:00")) == 0 and l.snapshot()["cash"] == 250,
          "unreleased quantity or retained cash differs")
    return {"scenario": "unreleased_overweight_lot", "pass": True,
            "final": l.receipt(T("05", "09:30:00"))}


def replay_sale(*, allowed):
    l = ledger_a(a_qty=300, b_qty=9000, b_price="1", sale_allowed=allowed)
    policy.deposit_week_once(l, DAY5, 250)
    session = policy.ScheduledPolicy((DAY5,))
    d, _, _, first = decide(session, l, DAY5, ("100", "1"),
                             "sale-filled" if allowed else "sale-rejected", DAY12)
    check(first.status == "await_actual_sale_then_later_buy" and len(first.orders) == 1,
          "exact-100 sale did not use original P1")
    order = first.orders[0]
    check(order.symbol == "A" and order.side == "sell" and order.quantity == 100,
          "exact-100 sale quantity differs")
    event = {"id": "sell:A:2026-01-05", "kind": "sell", "at": T("05", "09:30:00"),
             "symbol": "A", "qty": "100", "price": "100", "commission_rate": ".001",
             "minimum_commission": "5", "slippage_rate": ".001"}
    before = l.snapshot()
    try:
        l.apply(event)
    except ValueError as error:
        if allowed:
            raise
        check("permission" in str(error) and l.snapshot() == before,
              "sale rejection did not preserve account state")
        status = "rejected"
    else:
        check(allowed, "disallowed sale filled")
        status = "filled"
    result = planning.SaleResult(order.order_id, status, D(100) if allowed else D(0),
        D(100) if allowed else D(0), T("05", "09:30:00"), T("06", "09:30:00"),
        "synthetic-sale-receipt")
    check(l.snapshot()["cash"] == 250, "proceeds spent at sale opening")
    if allowed:
        check(sum(r["amount"] for r in l.snapshot()["restricted"]) == D(9980),
              "sale proceeds not restricted")
    later_cash = planning.CashSnapshot("ledger-free-excluding-sale", "sale-followup",
        D(250), T("05", "10:00:00"), T("05", "00:00:00"), False, None)
    next_plan = policy.after_sale(planning, d, first, result, later_cash,
        frozen_at=T("06", "09:45:00"), opening_at=T("06", "10:00:00"))
    if not allowed:
        check(next_plan.status == "failed_sale_cash_retained" and not next_plan.orders,
              "failed sale chased a buy")
        check(l.snapshot()["cash"] == 250 and l.shares("A") == 300,
              "failed sale moved cash or holdings")
        return {"scenario": "failed_sale_retains_cash", "pass": True,
                "rejection": l.audit[-1]["reason"],
                "money_state_unchanged": l.audit[-1]["money_state_unchanged"],
                "final": l.receipt(T("05", "09:30:00"))}
    check(next_plan.status == "later_buys_from_actual_sale_receipt"
          and len(next_plan.orders) == 1, "actual sale receipt not bound to later buy")
    next_order = next_plan.orders[0]
    check(next_order.symbol == "B" and next_order.quantity == D(10200),
          "later buy quantity differs")
    l.apply(buy_event(next_order, "buy:B:2026-01-06"))
    check(l.shares("A") == 200 and l.shares("B") == 19200
          and l.snapshot()["cash"] == D("9.6") and not l.snapshot()["restricted"],
          "actual sale proceeds reused or later account state differs")
    return {"scenario": "exact_100_sale_then_later_buy", "pass": True,
            "sale_restricted": "9980", "later_buy_quantity": str(next_order.quantity),
            "final": l.receipt(T("06", "10:00:00"))}


def main():
    plan = json.loads((ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/zero-sale-implementation-contract-20261011.json").read_text())["output_plan"]
    run = Path(plan["run_directory"])
    out = Path(plan["output"])
    check(run.is_dir() and out.is_dir() and os.stat(run).st_dev == plan["external_device"]
          and os.stat(out).st_dev == plan["external_device"], "frozen external result unavailable")
    check(os.statvfs(run).f_bavail * os.statvfs(run).f_frsize > plan["external_reserve_bytes"],
          "external reserve insufficient")
    result = {"schema": 1, "purpose": "artificial policy and dated-ledger replay only",
              "source_sha256": {str(p): h for p, h in EXPECTED.items()},
              "code_sha256": {p.name: digest(p) for p in (HERE / "policy_zero_sale.py", Path(__file__))},
              "pid": os.getpid(), "external_device": os.stat(out).st_dev,
              "scenarios": [replay_zero_then_next(), replay_unreleased(),
                            replay_sale(allowed=True), replay_sale(allowed=False)]}
    check(len(result["scenarios"]) <= 8 and all(s["pass"] for s in result["scenarios"]),
          "scenario batch failed")
    destination = out / "synthetic-ledger-replay.json"
    with destination.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        handle.write("\n")
    print(json.dumps({"passed": len(result["scenarios"]), "failed": 0,
                      "result": str(destination), "sha256": digest(destination),
                      "bytes": destination.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
