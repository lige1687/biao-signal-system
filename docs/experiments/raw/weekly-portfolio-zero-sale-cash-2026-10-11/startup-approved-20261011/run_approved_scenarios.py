"""One bounded artificial batch using the approved isolated startup policy."""

import hashlib
import json
import os
import plistlib
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD_POLICY = HERE.parent
ORDERS = ROOT / "docs/experiments/raw/weekly-portfolio-order-planning-2026-10-08"
LEDGER = ROOT / "docs/experiments/raw/weekly-portfolio-dated-execution-2026-10-08"
CONTRACT = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/startup-approved-implementation-contract-20261011.json"
FIXED = {
    CONTRACT: "42999d333e3defcbbdfd5104ea94d43771dc7605ebbd64a4fb3e0874abbf8993",
    OLD_POLICY / "policy_zero_sale.py": "dc7ab5d846120b850590e0c51bc02bfc9afdae1ee41badf9a61462a447914db6",
    OLD_POLICY / "run_startup_counterexample.py": "bf0bf5835b7492863d7ed0d8e70d8699d9a4aa4104dadf6b755906171e96748d",
    ORDERS / "order_planning.py": "645cac7faa6fc25bd95e0c25b63621d4e233b501a6d0b946895ff685b584a75a",
    ORDERS / "order_planning_v2.py": "a9ab958fa737fc53e7a08905da9ffd82b40687354f2b8be2d508db121a13b958",
    LEDGER / "dated_ledger.py": "20f6547deea6d19c6416daa6048ee18a7111ff6bf4c7b21bbae90a7b379e62d3",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for path, expected in FIXED.items():
    if sha(path) != expected:
        raise RuntimeError("frozen input changed: " + str(path))
sys.path[:0] = [str(ORDERS), str(LEDGER), str(OLD_POLICY), str(HERE)]
import order_planning_v2 as planner
import dated_ledger as dated
import policy_zero_sale as old_policy
import policy_startup_approved as policy

WEEKS = ("2026-01-05", "2026-01-12", "2026-01-19")
CLOSES = ("2026-01-02", "2026-01-09", "2026-01-16")
RELEASES = ("2026-01-06", "2026-01-13", "2026-01-20")
COSTS = planner.Costs(D(".001"), D(5), D(".001"), "fixed-artificial-fees")


def clock(day, hms):
    return day + "T" + hms + "+08:00"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def preflight():
    plan = json.loads(CONTRACT.read_text())["output_plan"]
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    check(info.get("VolumeUUID") == plan["external_uuid"], "external UUID differs")
    check(info.get("Internal") == 0 and info.get("WritableVolume") == 1,
          "external writable identity differs")
    check(mount.stat().st_dev == plan["external_device"], "external device differs")
    internal = os.statvfs(ROOT)
    external = os.statvfs(mount)
    check(internal.f_bavail * internal.f_frsize >
          plan["internal_reserve_bytes"] + plan["internal_metadata_bytes"],
          "internal reserve insufficient")
    check(external.f_bavail * external.f_frsize >
          plan["external_reserve_bytes"] + plan["estimated_bytes"],
          "external reserve insufficient")
    target = Path(plan["output"])
    check(target.parent == Path(plan["run_directory"]), "fixed result directory differs")
    check(not target.exists(), "fixed result directory already exists")
    return target, plan


def opening(symbol, day, close_day, release_day, price):
    return {"price": str(price), "buy": True, "sell": True,
            "observed_at": clock(close_day, "15:00:00"),
            "decision_at": clock(day, "08:00:00"),
            "release_at": clock(release_day, "09:30:00"),
            "proceeds_available_at": clock(release_day, "09:30:00")}


def make_ledger(name, *, weeks, prices, lots=(), units=0):
    clocks = {}
    opens = {}
    closes = {}
    for i, day in enumerate(weeks):
        close_day = CLOSES[i]
        release_day = RELEASES[i]
        clocks[clock(day, "00:00:00")] = [0]
        clocks[clock(day, "09:30:00")] = [3]
        clocks[clock(release_day, "09:30:00")] = [3]
        opens[clock(day, "09:30:00")] = {
            symbol: opening(symbol, day, close_day, release_day, price)
            for symbol, price in prices.items()
        }
        clocks[clock(close_day, "15:00:00")] = [4]
        closes[clock(close_day, "15:00:00")] = {s: str(p) for s, p in prices.items()}
    calendar = {"name": name, "timezone": "Asia/Shanghai", "clocks": clocks,
                "closes": closes, "opens": opens, "actions": {}}
    return dated.Ledger(calendar, cash=0, lots=lots, units=units,
                        prior_complete={"at": clock(CLOSES[0], "15:00:00"), "nav": "1"},
                        marks={s: str(p) for s, p in prices.items()})


def inputs(ledger, day, prices, name):
    at = clock(day, "08:00:00")
    opening_at = clock(day, "09:30:00")
    state = ledger.snapshot()
    assets = tuple(planner.Asset(symbol, D(str(price)), at, ledger.shares(symbol),
                                 ledger.sellable(symbol, opening_at))
                   for symbol, price in sorted(prices.items()))
    decision = planner.Decision(name, at, at, at, state["cash"],
                                sum((r["amount"] for r in state["restricted"]), D(0)),
                                sum((r["amount"] for r in state["receivables"].values()), D(0)),
                                assets, COSTS)
    cash = planner.CashSnapshot("ledger-free-cash", name, state["cash"], at, at, False, None)
    actions = planner.ActionContext("explicit-empty-actions", name, at,
                                    clock(CLOSES[0], "15:00:00"),
                                    clock("2026-01-26", "15:00:00"), ())
    return decision, cash, actions


def reject_repeat_deposit(ledger, day):
    before = ledger.snapshot()
    try:
        policy.deposit_week_once(ledger, day, 250)
    except ValueError as error:
        check(str(error) == "weekly deposit already applied", "wrong duplicate deposit rejection")
    else:
        raise AssertionError("duplicate weekly deposit accepted")
    check(ledger.snapshot() == before, "rejected deposit changed money state")


def decision_once(ledger, session, day, next_day, prices, name):
    d, cash, actions = inputs(ledger, day, prices, name)
    kwargs = {"frozen_at": clock(day, "09:00:00"),
              "opening_at": clock(day, "09:30:00"), "next_scheduled_week": next_day}
    old = old_policy.decide_p1(planner, d, cash, actions, **kwargs)
    result = session.decide(planner, day, d, cash, actions, **kwargs)
    before = ledger.snapshot()
    try:
        session.decide(planner, day, d, cash, actions, **kwargs)
    except ValueError as error:
        check(str(error) == "unscheduled or repeated weekly decision", "wrong repeat decision rejection")
    else:
        raise AssertionError("duplicate weekly decision accepted")
    check(ledger.snapshot() == before, "rejected decision changed account")
    return result, old


def execute_buys(ledger, result, day):
    check(result.old_plan.status == "ready", "original P0 buy plan missing")
    placed = []
    for order in result.orders:
        check(order.side == "buy" and order.quantity > 0 and order.quantity % 100 == 0,
              "buy quantity differs from legal whole lots")
        opening_at = clock(day, "09:30:00")
        check(planner.validate_opening_order(result.old_plan, order,
              opening_at=opening_at, price=order.reference, eligible=True) == "matches_frozen_buy",
              "frozen buy did not qualify")
        ledger.apply({"id": "buy:" + day + ":" + order.symbol, "kind": "buy",
                      "at": opening_at, "symbol": order.symbol,
                      "qty": str(order.quantity), "price": str(order.reference),
                      "commission_rate": str(COSTS.commission),
                      "minimum_commission": str(COSTS.minimum),
                      "slippage_rate": str(COSTS.slippage)})
        placed.append({"symbol": order.symbol, "quantity": str(order.quantity),
                       "reference": str(order.reference), "budget": str(order.budget),
                       "cap": str(order.cap)})
    return placed


def startup_three_weeks():
    prices = {"A": "1", "B": "1"}
    ledger = make_ledger("artificial-zero-start-approved", weeks=WEEKS, prices=prices)
    session = policy.ScheduledPolicy(WEEKS)
    weeks = []
    for i, day in enumerate(WEEKS):
        policy.deposit_week_once(ledger, day, 250)
        reject_repeat_deposit(ledger, day)
        result, old = decision_once(ledger, session, day,
                                    WEEKS[i + 1] if i < 2 else "2026-01-26",
                                    prices, "zero-start-week-" + str(i + 1))
        check(old.status == "defer_cash_to_next_scheduled_week", "historical startup branch changed")
        check(result.status == "buy_when_no_sale_required", "approved startup buy missing")
        orders = execute_buys(ledger, result, day)
        check(len(orders) == 2, "expected two original P0 buys per week")
        weeks.append({"week": i + 1, "day": day, "old_status": old.status,
                      "new_status": result.status, "orders": orders,
                      "account": ledger.receipt(clock(day, "09:30:00"))})
        if i < 2:
            ledger.apply({"id": "close:" + CLOSES[i + 1], "kind": "close",
                          "at": clock(CLOSES[i + 1], "15:00:00")})
    state = ledger.snapshot()
    check(state["cash"] == D("119.4") and state["inflows"] == D(750)
          and state["fees"] == D("30.6") and ledger.shares("A") == 300
          and ledger.shares("B") == 300, "three-week startup money or holdings differ")
    return {"scenario": "zero_start_three_scheduled_weeks", "weeks": weeks,
            "final": ledger.receipt(clock(WEEKS[-1], "09:30:00")),
            "accepted_ledger_events": sum(row["accepted"] for row in ledger.audit),
            "rejected_ledger_events": sum(not row["accepted"] for row in ledger.audit)}


def positive_underweight():
    day = WEEKS[0]
    prices = {"A": "1", "B": "1"}
    lots = [{"symbol": symbol, "qty": "100", "release_at": clock(CLOSES[0], "09:30:00"),
             "purchase_id": "opening-" + symbol} for symbol in prices]
    ledger = make_ledger("artificial-both-underweight", weeks=(day,), prices=prices,
                         lots=lots, units=200)
    session = policy.ScheduledPolicy((day,))
    policy.deposit_week_once(ledger, day, 250)
    reject_repeat_deposit(ledger, day)
    result, old = decision_once(ledger, session, day, WEEKS[1], prices,
                                "both-positive-underweight")
    check(all(a.held > 0 for a in inputs(ledger, day, prices, "check")[0].assets),
          "both initial holdings must be positive")
    check(old.status == "defer_cash_to_next_scheduled_week"
          and result.status == "buy_when_no_sale_required", "underweight branch differs")
    orders = execute_buys(ledger, result, day)
    check(len(orders) == 2 and ledger.shares("A") == 200 and ledger.shares("B") == 200
          and ledger.snapshot()["cash"] == D("39.8"), "underweight account differs")
    return {"scenario": "both_positive_holdings_underweight", "old_status": old.status,
            "new_status": result.status, "orders": orders,
            "final": ledger.receipt(clock(day, "09:30:00")),
            "rejected_ledger_events": sum(not row["accepted"] for row in ledger.audit)}


def genuine_excess_below_whole_lot():
    day = WEEKS[0]
    prices = {"A": "100", "B": ".7"}
    lots = [{"symbol": "A", "qty": "100", "release_at": clock(CLOSES[0], "09:30:00"),
             "purchase_id": "opening-A"},
            {"symbol": "B", "qty": "10000", "release_at": clock(CLOSES[0], "09:30:00"),
             "purchase_id": "opening-B"}]
    ledger = make_ledger("artificial-true-excess-small-sale", weeks=(day,),
                         prices=prices, lots=lots, units=17000)
    session = policy.ScheduledPolicy((day,))
    policy.deposit_week_once(ledger, day, 250)
    reject_repeat_deposit(ledger, day)
    before = ledger.snapshot()
    result, old = decision_once(ledger, session, day, WEEKS[1], prices,
                                "true-overweight-below-lot")
    check(old.status == "defer_cash_to_next_scheduled_week"
          and result.status == "defer_cash_to_next_scheduled_week"
          and result.reason == "required_excess_but_no_eligible_whole_lot_sale"
          and not result.orders, "true excess must defer without orders")
    check(ledger.snapshot() == before and ledger.snapshot()["cash"] == 250,
          "true excess deferred account changed")
    return {"scenario": "true_excess_sale_below_100", "old_status": old.status,
            "new_status": result.status, "required_excess_A_value": "1375",
            "required_A_sale_shares_before_rounding": "13.75", "orders": [],
            "next_scheduled_week": result.next_scheduled_week,
            "final": ledger.receipt(clock(day, "09:30:00")),
            "rejected_ledger_events": sum(not row["accepted"] for row in ledger.audit)}


def main():
    target, plan = preflight()
    scenarios = [startup_three_weeks(), positive_underweight(),
                 genuine_excess_below_whole_lot()]
    check(len(scenarios) == 3, "bounded scenario count differs")
    result = {"schema_version": 1, "kind": "approved_startup_artificial_batch",
              "contract_sha256": sha(CONTRACT),
              "source_sha256": {str(path): expected for path, expected in FIXED.items()},
              "policy_sha256": sha(HERE / "policy_startup_approved.py"),
              "runner_sha256": sha(Path(__file__)),
              "new_scenarios": 3, "prior_scenarios_reused_without_rerun": 5,
              "cumulative_scenarios": 8, "scenarios": scenarios,
              "boundary": "artificial engineering only; no market or actual trading result"}
    target.mkdir(parents=True, exist_ok=False)
    check(target.stat().st_dev == plan["external_device"], "result created on wrong device")
    destination = target / "approved-startup-replay.json"
    with destination.open("x") as file:
        json.dump(result, file, ensure_ascii=False, indent=2, default=str, sort_keys=True)
        file.write("\n")
    print(json.dumps({"result": str(destination), "sha256": sha(destination),
                      "bytes": destination.stat().st_size,
                      "policy_sha256": result["policy_sha256"],
                      "runner_sha256": result["runner_sha256"],
                      "final_startup": scenarios[0]["final"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
