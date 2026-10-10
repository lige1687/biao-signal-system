"""Source preflight now; paired historical account path requires later controller contract."""

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path
from math import sqrt
import plistlib
import statistics
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONTRACT = ROOT / "docs/experiments/raw/original-eight-continuation-2026-10-10/complete-account-engineering-contract-20261011.json"
CONTRACT_SHA = "606ea6eddab51050751383de8ee3093f4fd02f066e0a8d9bfe9be060be9c0fab"
AMENDMENT = CONTRACT.with_name("complete-account-engineering-amendment-20261011.json")
AMENDMENT_SHA = "019c7ee0434c707ab006f83120ecbf4d00d43fbf48e2e03ceea0fa9cd66e97c7"
SOURCE = ROOT / "docs/experiments/raw/research-eighth-2026-09-08/product-qualification"
sys.path[:0] = [str(HERE), str(ROOT / "docs/experiments/raw/weekly-portfolio-order-planning-2026-10-08"),
                str(ROOT / "docs/experiments/raw/weekly-portfolio-zero-sale-cash-2026-10-11/startup-approved-20261011"),
                str(ROOT / "docs/experiments/raw/weekly-portfolio-zero-sale-cash-2026-10-11")]
from engine import Dividend, PortfolioEngine, SYMBOLS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound_contract():
    if sha(CONTRACT) != CONTRACT_SHA:
        raise ValueError("engineering contract drift")
    if sha(AMENDMENT) != AMENDMENT_SHA:
        raise ValueError("engineering amendment drift")
    contract = json.loads(CONTRACT.read_text())
    for name, binding in contract["source_fingerprints"].items():
        path = ROOT / name
        if not path.is_file() or path.stat().st_size != binding["bytes"] or sha(path) != binding["sha256"]:
            raise ValueError("protected source drift: " + name)
    for path, expected in ((Path("/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术交易体系.md"),
                            contract["strategy_sha256"]["technical"]),
                           (Path("/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术实现.md"),
                            contract["strategy_sha256"]["implementation"])):
        if sha(path) != expected:
            raise ValueError("protected strategy source drift: " + str(path))
    return contract


def load_bars():
    bars = {}
    dates = {}
    summaries = {}
    for symbol in SYMBOLS:
        path = SOURCE / f"{symbol}-nominal.csv"
        seen = set()
        first, last = None, None
        with path.open(newline="") as file:
            for row in csv.DictReader(file):
                day = row["session_date"]
                if day in seen:
                    raise ValueError("duplicate quote date: " + symbol + " " + day)
                seen.add(day)
                first = first or day
                last = day
                if day < "2015-01-01" or day > "2026-06-30":
                    continue
                if row["symbol"] != symbol or D(row["open"]) <= 0 or D(row["close"]) <= 0:
                    raise ValueError("invalid nominal quote: " + symbol + " " + day)
                bars.setdefault(day, {})[symbol] = {"open": row["open"], "close": row["close"]}
        dates[symbol] = {d for d in seen if "2015-01-01" <= d <= "2026-06-30"}
        summaries[symbol] = {"file": str(path), "sha256": sha(path), "rows_all": len(seen),
                             "dates_in_window": len(dates[symbol]), "first": first, "last": last}
    return bars, sorted(set.union(*dates.values())), dates, summaries


def load_actions():
    raw = json.loads((SOURCE / "actions.json").read_text())
    actions = []
    for row in raw:
        if row["symbol"] in SYMBOLS and row.get("within_research_window"):
            if row["type"] != "cash_dividend":
                raise ValueError("unsupported holder conversion/split in two ETFs")
            actions.append(Dividend(row["event_id"], row["symbol"],
                                    row["announcement_date"], row["record_date"],
                                    row["effective_date"], row["pay_date"], D(row["cash"])))
    if len({a.event_id for a in actions}) != len(actions):
        raise ValueError("duplicate action identity")
    return actions


def preflight():
    contract = bound_contract()
    bars, model_days, dates, summaries = load_bars()
    actions = load_actions()
    expected_model_days = 2790
    if len(model_days) != expected_model_days:
        raise ValueError(f"model date union {len(model_days)} != {expected_model_days}")
    mondays = []
    day = date(2015, 1, 5)
    end = date(2026, 6, 29)
    while day <= end:
        mondays.append(day.isoformat())
        day += timedelta(days=7)
    if len(mondays) != contract["method"]["deposits"]["expected_weekly_events"]:
        raise ValueError("Monday deposit count differs")
    missing = sorted((symbol, day) for day in model_days for symbol in SYMBOLS
                     if day not in dates[symbol])
    known = {("sz159915", "2021-02-08")}
    if set(missing) != known:
        raise ValueError("unexplained cross-product quote absence: " + repr(missing[:8]))
    if len(actions) != 12:
        raise ValueError("two-product in-window cash action count differs")
    if any(a.record_date not in model_days or a.ex_date not in model_days for a in actions):
        raise ValueError("action record/ex date absent from model dates")
    restricted = json.loads((SOURCE / "dated-restrictions.json").read_text())
    blocked = {(row["symbol"], row["date"]) for row in restricted
               if row["symbol"] in SYMBOLS and not row["open_buy_allowed"]}
    if blocked != {("sz159915", "2021-02-08"), ("sz159915", "2021-02-09")}:
        raise ValueError("known 09:30 blocked dates differ")
    findings = {"schema_version": 1, "status": "source_structure_checked_no_policy_path",
                "contract_sha256": CONTRACT_SHA,
                "source_count_sha256_bound": len(contract["source_fingerprints"]),
                "nominal": summaries, "model_date_union": len(model_days),
                "first_model_day": model_days[0], "last_model_day": model_days[-1],
                "first_deposit": mondays[0], "last_deposit": mondays[-1],
                "scheduled_deposits": len(mondays),
                "actions": Counter(a.symbol for a in actions),
                "known_missing_quote": [list(x) for x in missing],
                "blocked_open": [list(x) for x in sorted(blocked)],
                "strict_historical_qualification_ready": False,
                "historical_policy_path_executed": False,
                "limits": "Hash/date/action structure only; no opening eligibility, calendar qualification, account return or strategy performance computed."}
    return findings, bars, model_days, actions, known, blocked


def gated_core(core_contract, expected_sha):
    """Future controller entry; cannot run without a later exact signed-off contract."""
    path = Path(core_contract)
    if not expected_sha or len(expected_sha) != 64 or sha(path) != expected_sha:
        raise ValueError("exact controller-approved core contract hash required")
    core = json.loads(path.read_text())
    if (core.get("engineering_contract_sha256") != CONTRACT_SHA or
            core.get("engineering_amendment_sha256") != AMENDMENT_SHA or
            core.get("engine_sha256") != sha(HERE / "engine.py") or
            core.get("runner_sha256") != sha(Path(__file__)) or
            core.get("input_preflight_sha256") != sha(HERE / "input-preflight.json") or
            core.get("core_execution_authorized") is not True):
        raise ValueError("later core execution contract not authorized")
    plan = core.get("output_plan", {})
    mount = Path(plan.get("external_mount", ""))
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    if (info.get("VolumeUUID") != plan.get("external_uuid") or info.get("Internal") != 0
            or info.get("WritableVolume") != 1 or mount.stat().st_dev != plan.get("external_device")):
        raise ValueError("future fixed external device mismatch")
    external = os.statvfs(mount)
    if external.f_bavail * external.f_frsize <= plan.get("external_reserve_bytes", 0) + plan.get("estimated_bytes", 0):
        raise ValueError("future external capacity insufficient")
    target = Path(plan["output"])
    if target.exists() or target.parent != Path(plan["run_directory"]):
        raise ValueError("future unique output binding unavailable")
    _, bars, model_days, actions, known, blocked = preflight()
    marks = {}
    previous_close_day = None
    for symbol in SYMBOLS:
        with (SOURCE / f"{symbol}-nominal.csv").open(newline="") as file:
            for row in csv.DictReader(file):
                if row["session_date"] < "2015-01-01":
                    marks[symbol] = row["close"]
                    previous_close_day = row["session_date"]
                else:
                    break
    if len(marks) != 2 or previous_close_day is None:
        raise ValueError("native prewindow reference missing")
    results = {}
    for policy in ("P0", "P1"):
        account = PortfolioEngine(policy, bars, model_days, actions, marks,
                                  previous_close_day, known_missing=known,
                                  blocked=blocked)
        path_result = account.run("2015-01-01", "2026-06-30")
        results[policy] = {"account": path_result, "metrics": summarize_metrics(path_result)}
    p0, p1 = results["P0"]["metrics"], results["P1"]["metrics"]
    results["paired"] = {"terminal_equity_difference_CNY": p1["terminal_equity"]-p0["terminal_equity"],
                         "unit_nav_drawdown_ratio": ratio(p1["max_drawdown"],p0["max_drawdown"]),
                         "annual_volatility_ratio": ratio(p1["annual_volatility"],p0["annual_volatility"])}
    target.mkdir(parents=True, exist_ok=False)
    if target.stat().st_dev != plan["external_device"]:
        raise ValueError("future result device changed")
    output = target / "paired-core-account.json"
    with output.open("x") as file:
        json.dump({"schema_version": 1, "core_contract_sha256": expected_sha,
                   "engineering_contract_sha256": CONTRACT_SHA,
                   "engineering_amendment_sha256": AMENDMENT_SHA,
                   "status": "conditional_daily_price_research_not_actual_trading",
                   "results": results}, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    print(json.dumps({"result": str(output), "sha256": sha(output),
                      "bytes": output.stat().st_size}, ensure_ascii=False))


def ratio(a, b):
    return None if b == 0 else a/b


def summarize_metrics(result):
    daily = result["daily"]
    if not daily:
        raise ValueError("empty account daily marks")
    values = [float(x["unit_nav"]) for x in daily]
    changes = [values[i]/values[i-1]-1 for i in range(1,len(values))]
    volatility = statistics.pstdev(changes)*sqrt(252) if changes else 0.0
    peak, deepest, peak_day, longest = 1.0, 0.0, daily[0]["day"], 0
    for row, nav in zip(daily, values):
        if nav >= peak:
            peak, peak_day = nav, row["day"]
        else:
            deepest = max(deepest, 1-nav/peak)
            longest = max(longest, (date.fromisoformat(row["day"])-date.fromisoformat(peak_day)).days)
    events = result["events"]
    deposits = [(x["day"], float(x["amount"])) for x in events if x["kind"] == "deposit"]
    terminal = float(result["terminal"]["equity"])
    end = date.fromisoformat(result["end"])
    if terminal == 0:
        annualized = -1.0
    else:
        def grown(rate):
            return sum(amount*(1+rate)**((end-date.fromisoformat(day)).days/365.25)
                       for day, amount in deposits)
        low, high = -0.999999, 1.0
        while grown(high) < terminal and high < 1e6:
            high = high*2+1
        if grown(high) < terminal:
            raise ValueError("annualized cashflow root unbounded")
        for _ in range(90):
            mid=(low+high)/2
            if grown(mid) < terminal: low=mid
            else: high=mid
        annualized=(low+high)/2
    operation_days = sorted({x["day"] for x in events if x["kind"] in ("buy", "sell")})
    operation_week = {}
    for x in events:
        if x["kind"] in ("buy", "sell"):
            d = date.fromisoformat(x["day"])
            monday = (d-timedelta(days=d.weekday())).isoformat()
            operation_week.setdefault(monday, set()).add(x["day"])
    extra_dates = sum(max(0,len(days)-1) for days in operation_week.values())
    years = {}
    prior_equity = 0.0
    for year in sorted({x["day"][:4] for x in daily}):
        rows = [x for x in daily if x["day"].startswith(year)]
        ending = float(rows[-1]["account"]["equity"])
        added = sum(amount for day, amount in deposits if day.startswith(year))
        years[year] = {"starting_equity": prior_equity, "contributions": added,
                       "ending_equity": ending, "profit_after_contributions": ending-prior_equity-added}
        prior_equity = ending
    return {"contributions": sum(amount for _,amount in deposits),
            "terminal_equity": terminal, "profit_vs_contributions": terminal-sum(amount for _,amount in deposits),
            "terminal_free_cash": result["terminal"]["free_cash"],
            "terminal_restricted_cash": result["terminal"]["restricted_cash"],
            "terminal_receivable": result["terminal"]["receivable"],
            "terminal_holdings": result["terminal"]["shares"],
            "terminal_locked_shares": result["terminal"]["locked_shares"],
            "unit_nav_total_return": values[-1]-1,
            "time_weighted_return": values[-1]-1,
            "cashflow_weighted_annualized_return": annualized,
            "max_drawdown": deepest, "longest_unrecovered_calendar_days": longest,
            "annual_volatility": volatility, "fees": float(result["terminal"]["fees"]),
            "buy_orders": sum(x["kind"]=="buy" for x in events),
            "sell_orders": sum(x["kind"]=="sell" for x in events),
            "rejected_orders": len(result["rejections"]),
            "cancelled_phases": len(result["cancellations"]),
            "operation_dates": len(operation_days),
            "extra_operation_dates_between_weekly_decisions": extra_dates,
            "turnover_CNY": sum(float(x["qty"])*float(x["price"]) for x in events
                                if x["kind"] in ("buy", "sell")),
            "dividend_entitlements": sum(x["kind"]=="record" for x in events),
            "dividend_payments": sum(x["kind"]=="pay" for x in events),
            "years": years}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--core-contract")
    parser.add_argument("--expected-core-sha")
    args = parser.parse_args()
    if args.preflight and not args.core_contract:
        findings, *_ = preflight()
        output = HERE / "input-preflight.json"
        with output.open("x") as file:
            json.dump(findings, file, ensure_ascii=False, indent=2, default=list, sort_keys=True)
            file.write("\n")
        print(json.dumps({"status": findings["status"], "input_preflight": str(output),
                          "sha256": sha(output)}, ensure_ascii=False))
    elif args.core_contract and not args.preflight:
        gated_core(args.core_contract, args.expected_core_sha)
    else:
        parser.error("choose preflight now or later approved core contract")


if __name__ == "__main__":
    main()
