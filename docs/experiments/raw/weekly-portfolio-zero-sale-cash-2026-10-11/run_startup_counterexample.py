"""One approved artificial all-cash startup path, using the frozen P1 choice."""
import hashlib
import json
import os
import sys
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONTRACT = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/zero-sale-startup-counterexample-contract-20261011.json"
PARENT = CONTRACT.with_name("zero-sale-implementation-contract-20261011.json")
POLICY = HERE / "policy_zero_sale.py"
ORDERS = ROOT / "docs/experiments/raw/weekly-portfolio-order-planning-2026-10-08"
LEDGER = ROOT / "docs/experiments/raw/weekly-portfolio-dated-execution-2026-10-08"
FIXED = {
    PARENT: "e2fe55aa0941f38bc7eaa57c9603cb643f1fbb256ad6ec49199551e7b854c034",
    POLICY: "dc7ab5d846120b850590e0c51bc02bfc9afdae1ee41badf9a61462a447914db6",
    ORDERS / "order_planning.py": "645cac7faa6fc25bd95e0c25b63621d4e233b501a6d0b946895ff685b584a75a",
    ORDERS / "order_planning_v2.py": "a9ab958fa737fc53e7a08905da9ffd82b40687354f2b8be2d508db121a13b958",
    LEDGER / "dated_ledger.py": "20f6547deea6d19c6416daa6048ee18a7111ff6bf4c7b21bbae90a7b379e62d3",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for path, expected in FIXED.items():
    if sha(path) != expected:
        raise RuntimeError("frozen input changed: " + str(path))
sys.path[:0] = [str(ORDERS), str(LEDGER), str(HERE)]
import order_planning_v2 as planner
import dated_ledger as dated
import policy_zero_sale as zero_sale

WEEKS = ("2026-01-05", "2026-01-12", "2026-01-19")
NEXT = ("2026-01-12", "2026-01-19", "2026-01-26")
CLOSES = ("2026-01-02", "2026-01-09", "2026-01-16")


def clock(day, hms):
    return day + "T" + hms + "+08:00"


def check(ok, why):
    if not ok:
        raise AssertionError(why)


def make_ledger():
    clocks = {}
    closes = {}
    for day in WEEKS:
        clocks[clock(day, "00:00:00")] = [0]
        clocks[clock(day, "09:30:00")] = [3]
    for day in CLOSES:
        at = clock(day, "15:00:00")
        clocks[at] = [4]
        closes[at] = {"A": "100", "B": "1"}
    calendar = {"name": "artificial-three-week-startup", "timezone": "Asia/Shanghai",
                "clocks": clocks, "closes": closes, "opens": {}, "actions": {}}
    # Frozen specification states initial balance 0 and initial unit price 1.
    return dated.Ledger(calendar, cash=0, lots=(), units=0,
        prior_complete={"at": clock(CLOSES[0], "15:00:00"), "nav": "1"},
        marks={"A": "100", "B": "1"})


def decide(ledger, session, day, following, index):
    decision_at = clock(day, "08:00:00")
    opening_at = clock(day, "09:30:00")
    snapshot = ledger.snapshot()
    check(snapshot["cash"] == D(250 * (index + 1)), "weekly cash differs before decision")
    assets = tuple(planner.Asset(symbol, price, decision_at,
                                ledger.shares(symbol), ledger.sellable(symbol, opening_at))
                   for symbol, price in (("A", D(100)), ("B", D(1))))
    costs = planner.Costs(D(".001"), D(5), D(".001"), "fixed-artificial-fees")
    decision = planner.Decision("zero-start-week-" + str(index + 1),
        decision_at, decision_at, decision_at, snapshot["cash"], D(0), D(0), assets, costs)
    cash = planner.CashSnapshot("ledger-free-cash", "zero-start-week-" + str(index + 1),
                               snapshot["cash"], decision_at, decision_at, False, None)
    action_context = planner.ActionContext("explicit-empty-actions", "zero-start",
        decision_at, clock(CLOSES[0], "15:00:00"), clock("2026-01-26", "15:00:00"), ())
    result = session.decide(planner, day, decision, cash, action_context,
        frozen_at=clock(day, "09:00:00"), opening_at=opening_at,
        next_scheduled_week=following)
    check(result.old_plan.reason == "triggered_no_sellable_whole_lot_pending_user",
          "old planner did not take the zero-sale trigger")
    check(result.status == "defer_cash_to_next_scheduled_week" and not result.orders,
          "policy did not retain cash")
    check(result.deferred_cash == snapshot["cash"], "deferred cash differs from ledger")
    check(ledger.shares("A") == 0 and ledger.shares("B") == 0,
          "startup unexpectedly bought holdings")
    return {"week": index + 1, "scheduled_day": day,
            "old_plan_status": result.old_plan.status,
            "old_plan_reason": result.old_plan.reason,
            "policy_status": result.status, "order_count": len(result.orders),
            "deferred_cash": str(result.deferred_cash),
            "account": ledger.receipt(opening_at)}


def main():
    contract = json.loads(CONTRACT.read_text())
    plan = contract["output_plan"]
    target = Path(plan["output"])
    check(target.is_dir() and target.stat().st_dev == plan["external_device"],
          "fixed external output or device unavailable")
    stat = os.statvfs(target)
    check(stat.f_bavail * stat.f_frsize > plan["external_reserve_bytes"],
          "external reserve insufficient")
    check(sha(POLICY) == contract["fixed_implementation_sha256"],
          "implemented policy differs from controller freeze")
    ledger = make_ledger()
    session = zero_sale.ScheduledPolicy(WEEKS)
    weeks = []
    for index, (day, following) in enumerate(zip(WEEKS, NEXT)):
        zero_sale.deposit_week_once(ledger, day, 250)
        before = ledger.snapshot()
        try:
            zero_sale.deposit_week_once(ledger, day, 250)
        except ValueError as error:
            check(str(error) == "weekly deposit already applied", "unexpected repeat-deposit error")
        else:
            raise AssertionError("second weekly deposit accepted")
        check(ledger.snapshot() == before, "repeat deposit changed account")
        weeks.append(decide(ledger, session, day, following, index))
        if index < 2:
            ledger.apply({"id": "close:" + CLOSES[index + 1], "kind": "close",
                          "at": clock(CLOSES[index + 1], "15:00:00")})
    state = ledger.snapshot()
    check(state["cash"] == D(750) and state["inflows"] == D(750)
          and state["fees"] == 0 and state["units"] == D(750)
          and not state["lots"] and not state["restricted"] and not state["receivables"],
          "three-week terminal account differs")
    result = {"schema_version": 1, "kind": "single_artificial_startup_counterexample",
        "pid": os.getpid(), "contract_sha256": sha(CONTRACT),
        "fixed_source_sha256": {str(p): h for p, h in FIXED.items()},
        "runner_sha256": sha(Path(__file__)), "external_device": target.stat().st_dev,
        "weeks": weeks, "final": ledger.receipt(clock(WEEKS[-1], "09:30:00")),
        "accepted_ledger_events": sum(a["accepted"] for a in ledger.audit),
        "rejected_ledger_events": sum(not a["accepted"] for a in ledger.audit),
        "conclusion": "zero-start P1 leaves cash 250, 500, 750 and never opens a holding under these fixed rules"}
    destination = target / "startup-counterexample-replay.json"
    with destination.open("x") as file:
        json.dump(result, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    print(json.dumps({"weeks": len(weeks), "final_cash": str(state["cash"]),
                      "shares": {"A": str(ledger.shares("A")), "B": str(ledger.shares("B"))},
                      "result": str(destination), "bytes": destination.stat().st_size,
                      "sha256": sha(destination)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
