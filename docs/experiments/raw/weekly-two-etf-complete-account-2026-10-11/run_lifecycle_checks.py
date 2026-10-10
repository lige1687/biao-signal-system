"""One authorized artificial lifecycle batch; no nominal historical policy paths."""

import hashlib
import json
import os
import plistlib
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONTRACT = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/complete-account-engineering-contract-20261011.json"
CONTRACT_SHA = "606ea6eddab51050751383de8ee3093f4fd02f066e0a8d9bfe9be060be9c0fab"
AMENDMENT = CONTRACT.with_name("complete-account-engineering-amendment-20261011.json")
AMENDMENT_SHA = "019c7ee0434c707ab006f83120ecbf4d00d43fbf48e2e03ceea0fa9cd66e97c7"
sys.path[:0] = [str(HERE), str(ROOT / "docs/experiments/raw/weekly-portfolio-order-planning-2026-10-08"),
                str(ROOT / "docs/experiments/raw/weekly-portfolio-zero-sale-cash-2026-10-11/startup-approved-20261011"),
                str(ROOT / "docs/experiments/raw/weekly-portfolio-zero-sale-cash-2026-10-11")]
from engine import Account, Dividend, PortfolioEngine, SYMBOLS
from run_account import summarize_metrics

MON, TUE, FRI, MON2, MON3 = "2026-01-05", "2026-01-06", "2026-01-09", "2026-01-12", "2026-01-19"
PREV = "2026-01-02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(ok, why):
    if not ok:
        raise AssertionError(why)


def bars(days, a="1", b="1", opens=None):
    opens = opens or {}
    return {day: {"sh510300": {"open": opens.get(("sh510300", day), a), "close": a},
                  "sz159915": {"open": opens.get(("sz159915", day), b), "close": b}}
            for day in days}


def engine(policy, days, a="1", b="1", *, opens=None, actions=(), missing=(), blocked=()):
    return PortfolioEngine(policy, bars(days, a, b, opens), days, actions,
                           {"sh510300": a, "sz159915": b}, PREV,
                           known_missing=missing, blocked=blocked)


def seed(account, a_qty, b_qty, a_price="1", b_price="1"):
    account.lots = [
        {"symbol": s, "qty": D(str(q)), "unlock_day": PREV, "purchase_id": "seed:"+s}
        for s, q in (("sh510300", a_qty), ("sz159915", b_qty)) if q
    ]
    account.units = D(str(a_qty))*D(a_price) + D(str(b_qty))*D(b_price)
    account.previous_nav = D(1)


def summarize(result):
    return {"terminal": result["terminal"], "deposit_count": result["deposits"],
            "event_kinds": dict((k, sum(e["kind"] == k for e in result["events"]))
                                for k in sorted({e["kind"] for e in result["events"]})),
            "rejections": result["rejections"], "cancellations": result["cancellations"],
            "plans": result["plans"]}


def case1_unaffordable():
    e = engine("P1", (MON, MON2, MON3), a="10", b="10")
    r = e.run(MON, MON3)
    check(r["terminal"]["free_cash"] == "750" and r["terminal"]["inflows"] == "750",
          "unaffordable deposits must accumulate once")
    check(not any(x["kind"] == "buy" for x in r["events"]), "unaffordable buy occurred")
    return summarize(r)


def case2_zero_start_paired():
    out = {}
    for name in ("P0", "P1"):
        r = engine(name, (MON, MON2, MON3)).run(MON, MON3)
        check(r["terminal"]["free_cash"] == "119.400"
              and r["terminal"]["shares"] == {s: "300" for s in SYMBOLS}
              and r["terminal"]["fees"] == "30.600", "three-week startup money differs")
        check(r["terminal"]["locked_shares"] == {s: "100" for s in SYMBOLS},
              "terminal buys must stay locked without future model session")
        check(sum(x["kind"] == "buy" for x in r["events"]) == 6,
              "three-week two-symbol buys differ")
        metric = summarize_metrics(r)
        check(metric["operation_dates"] == 3 and
              metric["extra_operation_dates_between_weekly_decisions"] == 0,
              "two buys at one weekly opening must not count as extra operation dates")
        check(metric["contributions"] == 750 and metric["terminal_equity"] == 719.4
              and abs(metric["profit_vs_contributions"] + 30.6) < 1e-9,
              "contribution/profit reconciliation differs")
        out[name] = summarize(r)
    return out


def case3_required_but_no_whole_sale():
    e = engine("P1", (MON,), a="100", b=".7")
    seed(e.account, 100, 10000, "100", ".7")
    r = e.run(MON, MON)
    check(r["terminal"]["free_cash"] == "250"
          and r["terminal"]["shares"] == {"sh510300": "100", "sz159915": "10000"}
          and not any(x["kind"] in ("buy", "sell") for x in r["events"]),
          "genuine excess below legal whole sale must defer")
    return summarize(r)


def seller_fixture(*, blocked=(), actions=(), days=(MON, TUE), close_a="2"):
    e = engine("P1", days, a=close_a, b="1",
               opens={("sh510300", MON): "1.81"}, blocked=blocked, actions=actions)
    seed(e.account, 500, 100, close_a, "1")
    return e


def case4_actual_sale_later_buy():
    r = seller_fixture().run(MON, TUE)
    sales = [x for x in r["events"] if x["kind"] == "sell"]
    buys = [x for x in r["events"] if x["kind"] == "buy"]
    check(len(sales) == 1 and sales[0]["qty"] == "100"
          and sales[0]["net_restricted"] == "175.81900", "actual sale or restricted net differs")
    check(len(buys) == 1 and buys[0]["symbol"] == "sz159915"
          and buys[0]["qty"] == "400" and buys[0]["day"] == TUE,
          "released sale funded later buy differs")
    check(r["terminal"]["free_cash"] == "20.41900", "later buy cash differs")
    operation_days = {x["day"] for x in r["events"] if x["kind"] in ("buy", "sell")}
    check(operation_days == {MON, TUE},
          "sale then later buy must count extra operation day")
    return summarize(r)


def case5_sale_rejected_no_pursuit():
    e = seller_fixture()
    e.bars[MON]["sh510300"]["open"] = "1.8"  # Exact lower legal limit.
    r = e.run(MON, TUE)
    check(any(x["reason"] == "at_lower_limit" and x["side"] == "sell"
              for x in r["rejections"]), "lower-limit sale refusal missing")
    check(not any(x["kind"] in ("sell", "buy") for x in r["events"])
          and r["terminal"]["free_cash"] == "250", "failed sale pursued or money changed")
    return summarize(r)


def case6_record_ex_pay_monday_overlap():
    action = Dividend("cash-A", "sh510300", "2026-01-01", PREV,
                      MON, FRI, D(".1"))
    days = (PREV, MON, TUE, FRI, MON2)
    e = engine("P0", days, actions=(action,), blocked={(s, MON2) for s in SYMBOLS})
    seed(e.account, 100, 100)
    r = e.run(PREV, MON2)
    kinds = [x["kind"] for x in r["events"]]
    check(kinds.count("record") == kinds.count("ex") == kinds.count("pay") == 1,
          "cash action phases not unique")
    record = next(x for x in r["events"] if x["kind"] == "record")
    ex = next(x for x in r["events"] if x["kind"] == "ex")
    check(record["eligible_shares"] == "100" and ex["receivable"] == "10.0"
          and ex["reference_before"] == "1" and ex["reference_after"] == "0.9",
          "record entitlement or ex-price transformation differs")
    check(r["plans"][0]["status"] == "unsupported" and r["plans"][0]["orders"] == 0,
          "known same-day ex between decision 00:01 and freeze 08:05 must block order")
    i_dep = next(i for i, x in enumerate(r["events"])
                 if x["kind"] == "deposit" and x["day"] == MON2)
    i_pay = next(i for i, x in enumerate(r["events"])
                 if x["kind"] == "pay")
    check(i_dep < i_pay and r["terminal"]["receivable"] == "0"
          and r["terminal"]["free_cash"] == "510.0",
          "Monday deposit/pay order or cash conversion differs")
    return summarize(r)


def case7_cross_week_expiry():
    e = seller_fixture(days=(FRI, MON2))
    # Friday is the first opening candidate after the Monday decision.
    e.bars[FRI]["sh510300"]["open"] = "1.81"
    e.blocked = frozenset({(s, MON2) for s in SYMBOLS})
    r = e.run(MON, MON2)
    check(any(x["kind"] == "sell" and x["day"] == FRI for x in r["events"]),
          "Friday sale missing")
    check(any(x["reason"] == "later_buy_new_week_expiry" for x in r["cancellations"]),
          "old later-buy not expired at week boundary")
    check(not any(x["kind"] == "buy" for x in r["events"]), "expired buy executed")
    terminal_sale = seller_fixture(days=(FRI,))
    terminal_sale.bars[FRI]["sh510300"]["open"] = "1.81"
    last = terminal_sale.run(MON, FRI)
    check(last["terminal"]["restricted_cash"] == "175.81900"
          and last["terminal"]["shares"]["sh510300"] == "400"
          and not any(x["kind"] == "release_sale_cash" for x in last["events"]),
          "last-window sale must retain restricted proceeds without future model event")
    return {"cross_week": summarize(r), "terminal_sale": summarize(last)}


def case8_ex_cross_cancels_later_order():
    action = Dividend("cash-after-sale", "sh510300", MON, MON,
                      TUE, FRI, D(".1"))
    e = seller_fixture(actions=(action,))
    r = e.run(MON, TUE)
    check(any(x["reason"] == "ex_crossed_unexecuted_plan" for x in r["cancellations"]),
          "ex-effect did not cancel outstanding buy")
    check(any(x["kind"] == "sell" for x in r["events"])
          and not any(x["kind"] == "buy" for x in r["events"]),
          "completed sale lost or later buy incorrectly filled")
    check(r["terminal"]["receivable"] == "40.0",
          "record-day post-sale ownership not preserved")
    return summarize(r)


def case9_missing_and_blocked_stale_mark():
    e = engine("P0", (MON, MON2), blocked={("sz159915", MON2)},
               missing={("sz159915", MON), ("sh510300", MON2)},
               opens={("sh510300", MON): "1.1"})
    del e.bars[MON]["sz159915"]
    del e.bars[MON2]["sh510300"]
    r = e.run(MON, MON2)
    reasons = {x["reason"] for x in r["rejections"]}
    check(reasons == {"at_upper_limit", "missing_open", "blocked_open"},
          "upper-limit/missing/blocked opening reasons differ")
    check(r["terminal"]["mark_age"]["sh510300"] == 1
          and r["terminal"]["free_cash"] == "500"
          and not any(x["kind"] == "buy" for x in r["events"]),
          "known stale mark/cash changed or fake fill")
    return summarize(r)


def case10_duplicate_save_recover_nav():
    a = Account({s: "1" for s in SYMBOLS}, PREV)
    seed(a, 100, 100)
    a.deposit(MON)
    before = a.dump_money()
    try:
        a.deposit(MON)
    except ValueError:
        check(a.dump_money() == before, "duplicate deposit mutated money")
    else:
        raise AssertionError("duplicate deposit accepted")
    a.close(MON, {"sh510300": {"close": "2"}, "sz159915": {"close": "1"}})
    nav = a.previous_nav
    restored = Account.load_money(a.dump_money())
    check(restored.dump_money() == a.dump_money(), "save/recover money differs")
    restored.deposit(MON2)
    check(restored.equity() == D(800) and restored.equity()/restored.units == nav,
          "new contribution incorrectly counted as return")
    return {"prior_nav": str(nav), "units_after_second_deposit": str(restored.units),
            "equity_after_second_deposit": str(restored.equity()),
            "recovered_money_equal": True, "duplicate_deposit_rejected": True}


CASES = (case1_unaffordable, case2_zero_start_paired,
         case3_required_but_no_whole_sale, case4_actual_sale_later_buy,
         case5_sale_rejected_no_pursuit, case6_record_ex_pay_monday_overlap,
         case7_cross_week_expiry, case8_ex_cross_cancels_later_order,
         case9_missing_and_blocked_stale_mark, case10_duplicate_save_recover_nav)


def external_target():
    if sha(CONTRACT) != CONTRACT_SHA:
        raise ValueError("engineering contract drift")
    plan = json.loads(CONTRACT.read_text())["output_plan"]
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    check(info.get("VolumeUUID") == plan["external_uuid"] and info.get("Internal") == 0
          and info.get("WritableVolume") == 1 and mount.stat().st_dev == plan["external_device"],
          "fixed writable external identity differs")
    external = os.statvfs(mount); internal = os.statvfs(ROOT)
    check(external.f_bavail*external.f_frsize > plan["external_reserve_bytes"]+plan["estimated_bytes"],
          "external capacity below reservation")
    check(internal.f_bavail*internal.f_frsize > plan["internal_reserve_bytes"]+plan["internal_metadata_bytes"],
          "internal metadata reserve insufficient")
    target = Path(plan["output"])
    check(target.is_dir() and target.stat().st_dev == plan["external_device"]
          and target.parent == Path(plan["run_directory"])
          and (target / "artificial-lifecycle.json").is_file()
          and not (target / "artificial-lifecycle-amended.json").exists(),
          "amended result must be a new file beside immutable first batch")
    return target, plan


def main():
    target, plan = external_target()
    check(sha(AMENDMENT) == AMENDMENT_SHA, "frozen engineering amendment drift")
    results = []
    for case in CASES:
        results.append({"name": case.__name__, "status": "passed", "evidence": case()})
    check(len(results) == 10, "artificial case budget exceeded")
    result = {"schema_version": 1, "kind": "artificial_full_account_lifecycle_only",
              "contract_sha256": CONTRACT_SHA, "engine_sha256": sha(HERE / "engine.py"),
              "amendment_sha256": AMENDMENT_SHA,
              "runner_sha256": sha(Path(__file__)), "case_count": len(results),
              "cases": results, "historical_policy_paths": 0,
              "boundary": "No actual historical ETF return, execution qualification or trading claim"}
    output = target / "artificial-lifecycle-amended.json"
    with output.open("x") as file:
        json.dump(result, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    print(json.dumps({"result": str(output), "bytes": output.stat().st_size,
                      "sha256": sha(output), "case_count": len(results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
