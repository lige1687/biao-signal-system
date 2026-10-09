"""C's independent arithmetic over saved artifacts; no account execution.

Uses only the standard library. Does not import B's code or any old strategy.
Do not run until B has published its authorized four-path result location.
"""
import argparse
import calendar
import csv
import datetime as dt
import hashlib
import json
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path
import statistics

PATHS = ["A_ALL-base", "A_ALL-stress", "A_SMA-base", "A_SMA-stress"]
START, END = "2026-01-01", "2026-06-30"


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def natural_dates():
    first, last = dt.date.fromisoformat(START), dt.date.fromisoformat(END)
    return [str(first + dt.timedelta(days=i)) for i in range((last-first).days+1)]


def csvmap(path):
    rows = list(csv.DictReader(Path(path).open(newline="")))
    assert len({r["date"] for r in rows}) == len(rows), "duplicate source date"
    return {r["date"]: r for r in rows}


def flag(x):
    assert x in (True, False, "True", "False"), f"unknown flag {x!r}"
    return x is True or x == "True"


class Audit:
    def __init__(self):
        self.count = 0
        self.failures = []
        self.maximum_numeric_error = D(0)

    def check(self, condition, where, observed=None, expected=None):
        self.count += 1
        if not condition:
            self.failures.append({"where": where, "observed": observed,
                                  "expected": expected})

    def near(self, observed, expected, where, tolerance="0.0000000000000001"):
        error = abs(D(str(observed))-D(str(expected)))
        self.maximum_numeric_error = max(self.maximum_numeric_error, error)
        self.check(error <= D(tolerance), where, str(observed), str(expected))


def independent_metrics(rows, initial, trading):
    prev, high = initial, initial
    high_date = dt.date.fromisoformat(START)-dt.timedelta(days=1)
    falling_from = None
    longest, draw = 0, D(0)
    changes, selected, exposures = [], [], []
    for r in rows:
        value, date = D(r["wealth"]), dt.date.fromisoformat(r["date"])
        change = value/prev-1
        changes.append(change)
        if r["date"] in trading:
            selected.append(float(change))
        if value >= high:
            if falling_from is not None:
                longest = max(longest, (date-falling_from).days)
            falling_from = None
            high, high_date = value, date
        else:
            draw = min(draw, value/high-1)
            falling_from = high_date if falling_from is None else falling_from
        exposures.append(100*D(r["units"])*D(r["mark"])/value)
        prev = value
    if falling_from is not None:
        longest = max(longest, (dt.date.fromisoformat(END)-falling_from).days)
    return {"trading_day_volatility": statistics.stdev(selected),
            "trading_observations": len(selected), "natural_observations": len(rows),
            "initial_wealth": str(initial), "end_wealth": str(prev),
            "net_change": str(prev-initial), "net_change_ratio": str(prev/initial-1),
            "max_drawdown": str(draw), "worst_day": str(min(changes)),
            "longest_underwater_calendar_days": longest,
            "unrecovered_at_end": falling_from is not None,
            "average_invested_pct_natural_days": str(sum(exposures)/len(exposures))}


def audit(binding, location):
    a = Audit()
    a.check(location["actual_path_attempts"] == 4, "four actual consumed paths")
    sources = binding["files"]
    for item in binding["source_closure"]:
        p = Path(item["path"])
        a.check(p.stat().st_size == item["bytes"] and digest(p) == item["sha256"],
                "source identity:"+item["id"])
    pointers = location["pointers"]
    identities = []
    for key, item in pointers.items():
        p = Path(item["path"])
        identities.append({"key": key, "path": str(p), "bytes": p.stat().st_size,
                           "sha256": digest(p), "device": p.stat().st_dev})
        a.check(p.stat().st_size == item["bytes"] and digest(p) == item["sha256"]
                and p.stat().st_dev == item["device"], "result identity:"+key)
    calendar_days = read(sources["calendar"]["path"])["days"]
    trading_all = sorted(d for d, x in calendar_days.items() if flag(x["is_trading_day"]))
    trading = {d for d in trading_all if START <= d <= END}
    natural = natural_dates()
    quotes = csvmap(sources["quotes"]["path"])
    references = {r["date"]: r for r in read(sources["execution_reference"]["path"])}
    old = {k: csvmap(sources[k]["path"]) for k in PATHS+["B0-base", "B0-stress"]}
    actions = [x for x in read(sources["mapped_actions"]["path"])
               if START <= x["record_date"] <= END]
    targets = read(pointers["monthly-targets"]["path"])
    expected_targets = {}
    for reference in ("A_ALL", "A_SMA"):
        a.check(len(targets[reference]) == 6, reference+":six monthly targets")
        expected_targets[reference] = []
        for month, t in enumerate(targets[reference], 1):
            active = f"2026-{month:02d}"
            prior = dt.date(2026, month, 1)-dt.timedelta(days=1)
            cutoff = str(prior)
            dates = [d for d in trading_all if d <= cutoff][-63:]
            deviations = {}
            for account in (reference+"-base", "B0-base"):
                deviations[account] = statistics.stdev([
                    float(D(old[account][d]["wealth"])/D(old[account][str(
                        dt.date.fromisoformat(d)-dt.timedelta(days=1))]["wealth"])-1)
                    for d in dates])
            sb, sa = deviations["B0-base"], deviations[reference+"-base"]
            a.check(sb > 0, active+":B0 nonzero standard deviation")
            weight = min(1., sa/sb)
            a.check(t["month"] == active and t["cutoff"] == cutoff
                    and t["window_dates"] == dates and t["observations"] == 63
                    and t["last_trading_observation"] == dates[-1]
                    and t["source_fee"] == "base"
                    and t["available_at"] == cutoff+" end_of_day", reference+":"+active+":cutoff")
            a.near(t["sigma_a"], sa, reference+":"+active+":A standard deviation")
            a.near(t["sigma_b0"], sb, reference+":"+active+":B0 standard deviation")
            a.near(t["weight"], weight, reference+":"+active+":weight")
            expected_targets[reference].append({"month": active, "weight": weight,
                                                "cutoff": cutoff, "sigma_a": sa, "sigma_b0": sb})
    results = {}
    for key in PATHS:
        data = read(pointers[key]["path"])
        account = data["account"]
        ref, fee_name = key.split("-")
        fee = D(".001" if fee_name == "base" else ".002")
        initial = D(binding["initial_states"][key]["wealth"])
        a.near(account["initial_cash"], initial, key+":initial cash")
        a.near(account["fee_rate"], fee, key+":fixed fee rate")
        a.check(account["terminal_liquidation"] is False, key+":no terminal liquidation")
        rows, fills, orders = account["daily"], account["fills"], account["orders"]
        a.check([r["date"] for r in rows] == natural, key+":complete natural days")
        by_day = {r["date"]: r for r in rows}
        a.check({r["date"] for r in rows if flag(r["is_trading_day"])} == trading,
                key+":exact trading calendar")
        a.check(len(orders) == 6 and len({o["month"] for o in orders}) == 6,
                key+":unique monthly adjustments")
        for order, target in zip(orders, targets[ref]):
            month = target["month"]
            candidates = [d for d in sorted(trading) if d[:7] == month
                          and references[d]["restriction"] is None
                          and quotes[d].get("open") not in (None, "")]
            when = order.get("executed_at", "").split(" ")[0]
            a.check(when == candidates[0], key+":"+month+":first executable open", when, candidates[0])
            a.check(order["decision_at"] == target["cutoff"]+" end_of_day"
                    and order["weight"] == target["weight"], key+":"+month+":decision/source")
            yesterday = str(dt.date.fromisoformat(when)-dt.timedelta(days=1))
            before = by_day.get(yesterday, {"cash": str(initial), "receivable": "0", "units": "0"})
            cash, receivable, units = (D(before[x]) for x in ("cash", "receivable", "units"))
            for event in actions:
                if event["ex_date"] == when:
                    receivable += D(by_day[event["record_date"]]["units"])*D(event["cash_per_unit"])
            price = D(quotes[when]["open"])
            value = cash+receivable+units*price
            desired = (D(target["weight"])*value/price/100).to_integral_value(rounding=ROUND_FLOOR)*100
            affordable = (cash/(price*(1+fee))/100).to_integral_value(rounding=ROUND_FLOOR)*100
            delta = min(desired-units, affordable) if desired >= units else desired-units
            adj = order["adjustment"]
            a.near(adj["opening_wealth"], value, key+":"+month+":opening complete wealth")
            a.near(adj["target_units"], desired, key+":"+month+":target units")
            a.near(adj["units_delta"], delta, key+":"+month+":actual cash-capped delta")
            a.check(sum(f["order_id"] == month for f in fills) == int(delta != 0),
                    key+":"+month+":single fill or executable zero")
            for f in (f for f in fills if f["order_id"] == month):
                a.near(f["units_delta"], delta, key+":"+month+":fill equals cash-capped order")
                a.check(f["date"] == when and f["phase"] == "open",
                        key+":"+month+":actual fill at approved open")
        fill_map = {d: [f for f in fills if f["date"] == d] for d in natural}
        buy = sell = total_fee = paid = booked = unit_change = D(0)
        for row in rows:
            day = row["date"]
            for f in fill_map[day]:
                delta, price = D(f["units_delta"]), D(f["price"])
                notional, charge = abs(delta)*price, abs(delta)*price*fee
                a.near(f["notional"], notional, key+":"+day+":notional")
                a.near(f["fee"], charge, key+":"+day+":fee")
                a.check(day in trading and references[day]["restriction"] is None
                        and D(references[day]["lower_limit"]) < price < D(references[day]["upper_limit"])
                        and price == D(quotes[day]["open"]), key+":"+day+":opening restriction")
                total_fee += charge
                unit_change += delta
                if delta > 0:
                    buy += notional
                else:
                    sell += notional
            for event in actions:
                amount = D(by_day[event["record_date"]]["units"])*D(event["cash_per_unit"])
                if event["ex_date"] == day:
                    booked += amount
                if event["pay_date"] == day:
                    paid += amount
            c, receivable, q, mark, value = (D(row[x]) for x in ("cash", "receivable", "units", "mark", "wealth"))
            a.near(c, initial+sell-buy-total_fee+paid, key+":"+day+":cash")
            a.near(receivable, booked-paid, key+":"+day+":receivable")
            a.near(q, unit_change, key+":"+day+":units")
            a.near(value, c+receivable+q*mark, key+":"+day+":wealth")
            a.check(min(c, receivable, q) >= 0 and value > 0, key+":"+day+":nonnegative balances")
            if day in trading:
                a.near(mark, quotes[day]["close"], key+":"+day+":close mark")
            else:
                yesterday = str(dt.date.fromisoformat(day)-dt.timedelta(days=1))
                previous_mark = by_day[yesterday]["mark"] if yesterday in by_day else quotes["2025-12-31"]["close"]
                a.near(mark, previous_mark, key+":"+day+":nontrading carried mark")
                a.check(not fill_map[day], key+":"+day+":no nontrading fills")
        for event in actions:
            ledger = [x for x in account["action_ledger"] if x["event_id"] == event["event_id"]]
            amount = D(by_day[event["record_date"]]["units"])*D(event["cash_per_unit"])
            a.check([(x["date"], x["phase"], x["type"]) for x in ledger] == [
                (event["record_date"], "after_close", "record_right"),
                (event["ex_date"], "before_open", "ex_receivable"),
                (event["pay_date"], "after_close", "payment_day_end")], key+":dividend order")
            for x in ledger:
                a.near(x["amount"], amount, key+":dividend amount")
        own = independent_metrics(rows, initial, trading)
        saved_rows = [old[key][d] for d in natural]
        saved = independent_metrics(saved_rows, initial, trading)
        for label, expected, observed in [("new", own, data["metrics"]), ("saved_A", saved, data["saved_A_metrics"])]:
            for field, value in expected.items():
                if isinstance(value, bool):
                    a.check(observed[field] is value, key+":"+label+":"+field)
                else:
                    a.near(observed[field], value, key+":"+label+":"+field)
        old_fills = read(sources[key+"-ledger"]["path"])["fills"]
        period_fills = [f for f in old_fills if START <= f["date"] <= END]
        old_fee = sum((D(f["fee"]) for f in period_fills), D(0))
        a.near(data["metrics"]["fees_2026h1"], total_fee, key+":new total fee")
        a.near(data["saved_A_metrics"]["fees_2026h1"], old_fee, key+":old fill fee total")
        a.check(data["metrics"]["trade_count"] == len(fills)
                and data["saved_A_metrics"]["trade_count"] == len(period_fills), key+":trade counts")
        ratio = own["trading_day_volatility"]/saved["trading_day_volatility"]
        gap = D(own["end_wealth"])-D(saved["end_wealth"])
        a.near(data["volatility_ratio"], ratio, key+":volatility ratio")
        a.near(data["end_wealth_minus_saved_A"], gap, key+":ending amount gap")
        profit = sell-buy+D(rows[-1]["units"])*D(rows[-1]["mark"])+booked-total_fee
        a.near(profit, D(rows[-1]["wealth"])-initial, key+":profit contributions")
        a.near(account["profit_bridge"]["sum_contributions"], profit, key+":saved contribution total")
        up = down = D(0)
        before = initial
        bbefore = D(old["B0-"+fee_name]["2025-12-31"]["wealth"])
        diagnostic = data["opportunity_description"]
        a.check([x["date"] for x in diagnostic["daily"]] == natural,
                key+":complete dated opportunity description")
        for row, observed in zip(rows, diagnostic["daily"]):
            bv = D(old["B0-"+fee_name][row["date"]]["wealth"])
            br = bv/bbefore-1
            dv = before*br-(D(row["wealth"])-before)
            a.near(observed["same_day_b0_minus_new_cny"], dv, key+":"+row["date"]+":saved B0 diagnostic")
            if br > 0:
                up += dv
            elif br < 0:
                down -= dv
            before, bbefore = D(row["wealth"]), bv
        a.near(diagnostic["b0_up_days_gap_cny"], up, key+":up day diagnostic")
        a.near(diagnostic["b0_down_days_avoided_cny"], down, key+":down day diagnostic")
        results[key] = {"new": own, "saved_A": saved, "new_fees": str(total_fee),
                        "saved_A_fees": str(old_fee), "new_trades": len(fills),
                        "saved_A_trades": len(period_fills), "volatility_ratio": ratio,
                        "end_wealth_minus_saved_A": str(gap), "matched": .90 <= ratio <= 1.10,
                        "profit_contributions": str(profit), "up_day_diagnostic": str(up),
                        "down_day_diagnostic": str(down)}
    return {"schema": "C-independent-saved-result-audit/1", "checked_at": dt.datetime.now().astimezone().isoformat(),
            "decision": "accepted" if not a.failures else "changes_required",
            "checks": a.count, "failures": a.failures, "maximum_numeric_error": str(a.maximum_numeric_error),
            "result_identities": identities, "independent_monthly_targets": expected_targets,
            "paths": results, "both_fees_matched": {ref: all(results[ref+"-"+fee]["matched"] for fee in ("base", "stress")) for ref in ("A_ALL", "A_SMA")},
            "new_account_executions_by_C": 0, "original_A_or_B0_replays": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = audit(read(args.binding), read(args.location))
    with Path(args.out).open("x") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"decision": result["decision"], "checks": result["checks"],
                      "failures": len(result["failures"])}))
