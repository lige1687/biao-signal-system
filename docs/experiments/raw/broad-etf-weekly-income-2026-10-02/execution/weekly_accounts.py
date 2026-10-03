"""Isolated weekly-income account policy. Real runs require a later controller grant.

Frozen market signals and first12 inputs are read-only. No network, signal generation,
or writes to the first12 archive. This module can also run synthetic fixtures.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
from legacy_primitives import D, effective_reference, execute_target, unavailable, week_key

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"
POLICY = "weekly-income-three-methods/1.0.0"
START, END = "2015-01-01", "2026-06-30"
SYMBOLS = ("sh510300", "sz159915")
METHODS = ("hold", "breadth_three_tier", "simple_60_close_breakout")
FEES = ("0.001", "0.002")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def verify_lock():
    lock = load(HERE / "input-lock.json")
    for relative, digest in lock["inputs"].items():
        path = ROOT / relative
        if not path.exists() or sha(path) != digest:
            raise RuntimeError(f"locked input changed or missing: {relative}")
    for relative, digest in lock["code"].items():
        path = HERE / relative
        if not path.exists() or sha(path) != digest:
            raise RuntimeError(f"locked code changed or missing: {relative}")
    return lock


def read_bars(symbol):
    with (OLD / "inputs/bars" / f"{symbol}-nominal.csv").open(newline="") as fh:
        return [{**r, **{k: D(r[k]) for k in ("open", "high", "low", "close", "volume")}}
                for r in csv.DictReader(fh)]


def calendar(start=START, end=END):
    current, finish = date.fromisoformat(start), date.fromisoformat(end)
    while current <= finish:
        yield current.isoformat()
        current += timedelta(days=1)


def income_days(start=START, end=END):
    return [day for day in calendar(start, end) if date.fromisoformat(day).weekday() == 0]


def xirr(incomes, final_day, final_asset):
    """Unique root for fixed negative deposits and one positive terminal asset."""
    flows = [(date.fromisoformat(day), -float(value)) for day, value in incomes]
    flows.append((date.fromisoformat(final_day), float(final_asset)))
    if not incomes or final_asset <= 0:
        return {"rate": None, "reason": "nonpositive_terminal_or_no_deposits"}
    base = flows[0][0]
    years = [(d - base).days / 365 for d, _ in flows]
    def npv(rate):
        return sum(amount * math.exp(-math.log1p(rate) * year) for (_, amount), year in zip(flows, years))
    lower, upper = -0.999999999, 1.0
    while npv(upper) > 0 and upper < 1e9:
        upper = 2 * upper + 1
    if npv(lower) <= 0 or npv(upper) >= 0:
        return {"rate": None, "reason": "root_not_bracketed", "bracket": [lower, upper]}
    iterations = 0
    for iterations in range(1, 201):
        middle = (lower + upper) / 2
        if npv(middle) > 0:
            lower = middle
        else:
            upper = middle
        if upper - lower < 1e-13:
            break
    rate = (lower + upper) / 2
    residual = npv(rate)
    return {"rate": rate, "bracket": [lower, upper], "residual": residual,
            "iterations": iterations, "converged": abs(residual) <= max(1e-7, float(final_asset) * 1e-11)}


def period_rows(daily, period):
    groups = defaultdict(list)
    for row in daily:
        groups[row["date"][:7 if period == "month" else 4]].append(row)
    rows, previous, previous_nav = [], D("0"), None
    for key, values in sorted(groups.items()):
        end = D(values[-1]["equity"])
        deposits = sum((D(v["external_income"]) for v in values), D("0"))
        last_nav = values[-1]["nav"]
        rows.append({"period": key, "start_equity": float(previous), "end_equity": float(end),
                     "external_income": float(deposits), "net_gain": float(end - previous - deposits),
                     "unit_return": (last_nav / previous_nav - 1) if previous_nav and last_nav is not None else
                     (last_nav - 1 if last_nav is not None else None)})
        previous, previous_nav = end, last_nav
    return rows


def drawdown(daily):
    peak = None; max_dd = 0.0; start = None; intervals = []
    valley_day = None; valley_nav = None; interval_dd = None
    for row in daily:
        nav = row["nav"]
        if nav is None: continue
        if peak is None:
            # The first deposit creates units at 1 before the day's fee and move.
            peak = 1.0
            peak_day = row["date"]
        if nav >= peak:
            if start is not None:
                intervals.append({"start_date": start, "valley_date": valley_day,
                                  "valley_nav": valley_nav, "max_drawdown": interval_dd,
                                  "recovery_date": row["date"],
                                  "recovery_days": (date.fromisoformat(row["date"]) - date.fromisoformat(start)).days})
                start = valley_day = valley_nav = interval_dd = None
            # Equal highs reset the waiting clock to the last attained peak.
            peak = nav; peak_day = row["date"]
        else:
            dd = nav / peak - 1
            if start is None:
                start = peak_day
                interval_dd = 0.0
            if dd < interval_dd:
                interval_dd = dd; valley_day = row["date"]; valley_nav = nav
            if dd < max_dd: max_dd = dd
    if start is not None:
        intervals.append({"start_date": start, "valley_date": valley_day,
                          "valley_nav": valley_nav, "max_drawdown": interval_dd,
                          "recovery_date": None, "recovery_days": None})
    return max_dd, intervals


def simulate(symbol, method, fee, bars, actions, settings, signals, start=START, end=END, weekly_income=D("250")):
    if method not in METHODS or symbol not in SYMBOLS:
        raise ValueError("fixed products and methods only")
    fee, weekly_income = D(str(fee)), D(str(weekly_income))
    bar_map = {b["date"]: b for b in bars}
    signal_by_day = defaultdict(list)
    for signal in signals:
        if signal["eligible_date"] <= end:
            signal_by_day[signal["eligible_date"]].append(signal)
    action_by_effective, action_by_pay, action_by_record = defaultdict(list), defaultdict(list), defaultdict(list)
    for action in actions:
        if action["symbol"] != symbol: continue
        action_by_effective[action["effective_date"]].append(action)
        if action.get("pay_date"): action_by_pay[action["pay_date"]].append(action)
        if action.get("record_date"): action_by_record[action["record_date"]].append(action)
    restrictions = [r for r in settings.get("dated_restrictions", []) if r["symbol"] == symbol]
    no_mark = {r["date"] for r in restrictions if not r["close_mark_allowed"]}
    cash = receivable = shares = account_units = cumulative_income = cumulative_fees = D("0")
    last_mark = next((b["close"] for b in reversed(bars) if b["date"] < start), None)
    reference = last_mark; mark_date = next((b["date"] for b in reversed(bars) if b["date"] < start), None)
    rights, dues = {}, {}
    pending = None; order_number = 0; active60 = False
    daily, trades, rejected, orders, incomes = [], [], [], [], []
    for day in calendar(start, end):
        prior_equity = cash + receivable + shares * last_mark if last_mark is not None else cash + receivable
        income = weekly_income if date.fromisoformat(day).weekday() == 0 else D("0")
        if income:
            if account_units == 0:
                if prior_equity != 0: raise RuntimeError("initial units with nonzero prior asset")
                account_units = income
            else:
                if prior_equity <= 0: raise RuntimeError("nonpositive pre-income unit price")
                account_units += income / (prior_equity / account_units)
            cash += income; cumulative_income += income; incomes.append((day, income))
        bar = bar_map.get(day)
        if action_by_effective[day] and shares and (bar is None or day in no_mark):
            raise RuntimeError(f"action without quote requires qualified ex-date mark: {day}")
        # Effective events precede payment, including when both occur today.
        for action in sorted(action_by_effective[day], key=lambda a: a["event_id"]):
            if action["type"] == "cash_dividend":
                amount = rights.get(action["event_id"], D("0")) * D(action["cash"])
                receivable += amount; dues[action["event_id"]] = amount
            elif action["type"] == "split":
                shares *= D(action["ratio"])
        for action in action_by_pay[day]:
            if action["type"] == "cash_dividend":
                amount = dues.pop(action["event_id"], D("0"))
                receivable -= amount; cash += amount
        def cancel(reason):
            nonlocal pending
            if pending:
                rejected.append({"date": day, "order_id": pending["id"], "reason": reason,
                                 "trigger_date": pending["trigger_date"]})
                pending = None
        def new_order(target, reason, trigger_date, trigger_type):
            nonlocal pending, order_number
            if pending: cancel("replaced_by_new_target")
            order_number += 1
            pending = {"id": order_number, "target": str(target), "reason": reason,
                       "trigger_date": trigger_date, "trigger_type": trigger_type,
                       "execution_week": week_key(day)}
            orders.append(dict(pending, created_date=day,
                               market_signal_date=trigger_date if trigger_type == "market_signal" else None,
                               funding_trigger_date=trigger_date if trigger_type == "funding_00" else None,
                               funding_trigger_time="00:00" if trigger_type == "funding_00" else None))
        if method == "breadth_three_tier" and pending and week_key(day) != tuple(pending["execution_week"]):
            cancel("stale_weekly_order_cancelled")
        incoming = signal_by_day[day]
        for signal in incoming:
            if signal["signal_date"] >= day:
                raise RuntimeError("market signal must precede execution day")
            if method == "breadth_three_tier":
                # A signal from an unfinished week is not executable in this window.
                if tuple(signal["source_week"]) == week_key(day):
                    raise RuntimeError("unfinished weekly signal")
                new_order(signal["target"], signal["reason"], signal["signal_date"], "market_signal")
            elif method == "simple_60_close_breakout":
                active60 = D(signal["target"]) == 1
                new_order(signal["target"], signal["reason"], signal["signal_date"], "market_signal")
        if income and method == "hold":
            if pending is None: new_order("1", "weekly_income_buy", day, "funding_00")
            else: pending["reason"] += "+weekly_income"
        if income and method == "simple_60_close_breakout" and active60:
            if pending is None: new_order("1", "weekly_income_buy_active60", day, "funding_00")
            elif D(pending["target"]) == 1: pending["reason"] += "+weekly_income"
        if pending:
            ref_open = effective_reference(reference, actions, symbol, day) if reference is not None else None
            block = unavailable(symbol, day, bar, ref_open, settings)
            if block:
                rejected.append({"date": day, "order_id": pending["id"], "reason": block, "retained": True})
            else:
                cash2, shares2, trade, reason, equity_open, actual = execute_target(
                    cash, receivable, shares, bar["open"], D(pending["target"]), fee,
                    apply_band=(method == "breadth_three_tier"))
                if reason:
                    rejected.append({"date": day, "order_id": pending["id"], "reason": reason, "retained": False,
                                     "actual_open_weight": float(actual)})
                    pending = None
                elif trade:
                    side, qty, notional, cost = trade
                    cash, shares = cash2, shares2; cumulative_fees += cost
                    trades.append({"date": day, "order_id": pending["id"], "trigger_date": pending["trigger_date"],
                                   "trigger_type": pending["trigger_type"],
                                   "market_signal_date": pending["trigger_date"] if pending["trigger_type"] == "market_signal" else None,
                                   "funding_trigger_date": pending["trigger_date"] if pending["trigger_type"] == "funding_00" else None,
                                   "funding_trigger_time": "00:00" if pending["trigger_type"] == "funding_00" else None,
                                   "side": side, "shares": float(qty),
                                   "price": float(bar["open"]), "notional": float(notional), "fee": float(cost),
                                   "reason": pending["reason"]})
                    pending = None
        if min(cash, receivable, shares) < 0: raise RuntimeError(f"negative position: {day}")
        if bar is not None and day not in no_mark:
            last_mark = bar["close"]; reference = bar["close"]; mark_date = day
        for action in action_by_record[day]:
            if action["type"] == "cash_dividend": rights[action["event_id"]] = shares
        equity = cash + receivable + (shares * last_mark if last_mark is not None else D("0"))
        nav = float(equity / account_units) if account_units else None
        factor = float(equity / (prior_equity + income)) if account_units and prior_equity + income else None
        row = {"date": day, "cash": float(cash), "receivable": float(receivable), "units": float(shares),
               "mark": float(last_mark) if last_mark is not None else None,
               "equity": float(equity), "external_income": float(income),
               "cumulative_income": float(cumulative_income), "account_units": float(account_units),
               "nav": nav, "daily_growth_factor": factor, "fees": float(cumulative_fees),
               "market_value": float(shares * last_mark) if last_mark is not None else 0.0,
               "invested_weight": float(shares * last_mark / equity) if equity and last_mark is not None else 0.0,
               "mark_age_days": (date.fromisoformat(day) - date.fromisoformat(mark_date)).days if mark_date else None,
               "active60": active60 if method == "simple_60_close_breakout" else None}
        if abs(D(str(row["equity"])) - (D(str(row["cash"])) + D(str(row["receivable"])) + D(str(row["market_value"])))) > D("0.000001"):
            raise RuntimeError(f"asset identity failed: {day}")
        daily.append(row)
    if pending: rejected.append({"date": end, "order_id": pending["id"], "reason": "pending_at_period_end"})
    for signal in signals:
        if signal["eligible_date"] > end:
            rejected.append({"date": end, "signal_date": signal["signal_date"],
                             "reason": "signal_after_period_end", "source_signal": signal,
                             "unfinished_source_week_candidate": method == "breadth_three_tier" and
                             tuple(signal["source_week"]) == week_key(end) and date.fromisoformat(end).weekday() < 4})
    monthly, yearly = period_rows(daily, "month"), period_rows(daily, "year")
    final = daily[-1]
    if abs(sum(r["net_gain"] for r in monthly) - (final["equity"] - final["cumulative_income"])) > 1e-5:
        raise RuntimeError("monthly reconciliation failed")
    if abs(sum(r["net_gain"] for r in yearly) - (final["equity"] - final["cumulative_income"])) > 1e-5:
        raise RuntimeError("yearly reconciliation failed")
    max_dd, intervals = drawdown(daily)
    after_funding = [r for r in daily if r["cumulative_income"] > 0]
    summary = {"symbol": symbol, "method": method, "fee_per_side": float(fee), "policy": POLICY,
               "initial_cash": 0, "weekly_income_count": len(incomes), "total_external_income": final["cumulative_income"],
               "final_equity": final["equity"], "net_gain": final["equity"] - final["cumulative_income"],
               "final_cash": final["cash"], "final_receivable": final["receivable"],
               "final_shares": final["units"], "terminal_market_value": final["market_value"],
               "final_nav": final["nav"], "unit_cumulative_return": final["nav"] - 1 if final["nav"] is not None else None,
               "max_unit_drawdown": max_dd, "drawdown_intervals": intervals,
               "xirr": xirr(incomes, end, D(str(final["equity"]))),
               "fees": final["fees"], "buys": sum(t["side"] == "buy" for t in trades),
               "sells": sum(t["side"] == "sell" for t in trades),
               "cash_only_days_since_first_income": sum(r["units"] == 0 for r in after_funding),
               "unfunded_days": len(daily) - len(after_funding),
               "average_invested_weight_since_first_income": sum(r["invested_weight"] for r in after_funding)/len(after_funding) if after_funding else None,
               "conditional_product_qualification": True}
    return {"daily": daily, "trades": trades, "orders": orders, "rejected": rejected,
            "summary": summary, "monthly": monthly, "yearly": yearly}


def real_run(grant_path):
    lock = verify_lock()
    if not grant_path or Path(grant_path).resolve() != (HERE / "real-run-authorization.json").resolve():
        raise RuntimeError("real market run is disabled until controller-specific authorization")
    grant = load(grant_path)
    if grant.get("approved") is not True or grant.get("contract_sha256") != lock["preparation_contract_sha256"]:
        raise RuntimeError("missing matching controller authorization")
    out = HERE / "core-01"
    if out.exists(): raise RuntimeError("preserve prior core-01 attempt")
    out.mkdir()
    save(out / "run-lock.json", {"input_lock_sha256": sha(HERE / "input-lock.json"),
                                 "grant_sha256": sha(grant_path), "status": "started"})
    config = load(OLD / "config.json")
    settings = load(OLD / "inputs/execution-parameters-source.json")
    settings["dated_restrictions"] = load(OLD / "inputs/dated-restrictions.json")
    actions = load(OLD / "inputs/actions.json")
    prepared = load(OLD / "prepared-signals.json")
    summaries = []
    for symbol in SYMBOLS:
        bars = read_bars(symbol)
        for method in METHODS:
            signals = prepared["weekly_breadth"] if method == "breadth_three_tier" else prepared["breakout"][symbol] if method == "simple_60_close_breakout" else []
            for fee in FEES:
                name = f"{symbol}-{method}-fee{fee}"
                result = simulate(symbol, method, fee, bars, actions, settings, signals)
                folder = out / name; folder.mkdir()
                for item in ("daily", "trades", "orders", "rejected", "summary", "monthly", "yearly"):
                    save(folder / f"{item}.json", result[item])
                summaries.append(result["summary"])
    save(out / "summary.json", summaries)
    verify_lock()
    save(out / "completion.json", {"accounts": len(summaries), "status": "completed"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--run-real", action="store_true")
    parser.add_argument("--authorization")
    args = parser.parse_args()
    if args.run_real:
        real_run(args.authorization)
    elif args.prepare_only:
        print(json.dumps({"status": "prepared_only", "policy": POLICY,
                          "locked_inputs": len(verify_lock()["inputs"])}))
    else:
        parser.error("choose --prepare-only; --run-real requires a later controller grant")
