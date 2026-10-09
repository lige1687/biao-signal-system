"""Isolated 510300 cash comparator. Preparation stage: synthetic checks only.

No archived runner is imported. Historical execution has no CLI until the
controller releases the source manifest, output plan, and two-path budget.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path


START, END = "2026-01-01", "2026-06-30"
LOT = Decimal(100)
FEES = {"base": Decimal("0.001"), "stress": Decimal("0.002")}
START_CASH = {"base": Decimal("110542.384400"), "stress": Decimal("110113.941800")}


def d(value):
    return None if value in (None, "") else Decimal(str(value))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(root: Path, bindings: dict) -> None:
    """Verify every frozen byte before consuming any historical source."""
    for item in bindings.values():
        path = root / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError(f"frozen source mismatch: {item['path']}")


def csv_rows(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def natural_dates(start: str, end: str) -> list[str]:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("inverted period")
    return [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def unique_by_date(rows: list[dict]) -> dict[str, dict]:
    result = {r["date"]: r for r in rows}
    if len(result) != len(rows) or list(result) != sorted(result):
        raise ValueError("duplicate or unordered dates")
    return result


def sample_stdev(values: list[Decimal]) -> float:
    if len(values) < 2:
        raise ValueError("insufficient return observations")
    numbers = [float(v) for v in values]
    mean = math.fsum(numbers) / len(numbers)
    return math.sqrt(math.fsum((v - mean) ** 2 for v in numbers) / (len(numbers) - 1))


def calibrate_2025(a_rows: list[dict], b0_rows: list[dict], trading_days: set[str]) -> dict:
    """Common official trading days; each return uses the prior natural day's wealth."""
    a, b = unique_by_date(a_rows), unique_by_date(b0_rows)
    selected = sorted(day for day in trading_days if "2025-01-01" <= day <= "2025-12-31")
    if len(selected) < 2:
        raise ValueError("missing 2025 trading calendar")
    returns = [[], []]
    denominator_differences = {"A": [], "B0": []}
    all_trading = sorted(trading_days)
    for day in selected:
        yesterday = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
        earlier = [d0 for d0 in all_trading if d0 < day]
        if not earlier:
            raise ValueError(f"missing prior trading date: {day}")
        prior_trading = earlier[-1]
        for label, source, target in (("A", a, returns[0]), ("B0", b, returns[1])):
            if day not in source or yesterday not in source or source[day]["is_trading_day"] != "True":
                raise ValueError(f"missing date or trading identity: {day}")
            wealth, prior = d(source[day]["wealth"]), d(source[yesterday]["wealth"])
            if wealth is None or prior is None or min(wealth, prior) <= 0:
                raise ValueError(f"invalid complete wealth: {day}")
            if prior_trading not in source:
                raise ValueError(f"missing prior trading wealth: {day}")
            if prior != d(source[prior_trading]["wealth"]):
                denominator_differences[label].append(day)
            target.append(wealth / prior - 1)
    sigma_a, sigma_b0 = map(sample_stdev, returns)
    if sigma_b0 == 0:
        raise ValueError("zero B0 volatility")
    weight = min(1.0, sigma_a / sigma_b0)
    if not 0 <= weight <= 1:
        raise ValueError("invalid fixed weight")
    return {"weight": weight, "sigma_a": sigma_a, "sigma_b0": sigma_b0,
            "trading_observations": len(selected), "first": selected[0], "last": selected[-1],
            "prior_natural_vs_prior_trading_difference_dates": denominator_differences}


def simulate_hold(*, cash: Decimal, fee: Decimal, weight: Decimal, quotes: list[dict],
                  trading_days: set[str], restrictions: dict[str, str], actions: list[dict],
                  start: str = START, end: str = END) -> dict:
    """One pending whole-lot buy, then hold. Dividend cash is available at day end."""
    if cash <= 0 or fee < 0 or not Decimal(0) <= weight <= Decimal(1):
        raise ValueError("invalid initial state, fee or weight")
    quote_map = unique_by_date(quotes)
    days = natural_dates(start, end)
    if any(day not in days for day in quote_map) or any(day not in days for day in trading_days):
        raise ValueError("quotes or trading dates outside period")
    if set(quote_map) - trading_days:
        raise ValueError("quote on nontrading day")
    for event in actions:
        if event["type"] != "dividend" or event.get("unit_basis") != "old":
            raise ValueError("unhandled corporate action")
        if not (start <= event["record_date"] < event["ex_date"] <= event["pay_date"] <= end):
            raise ValueError("dividend date order or period")
        if d(event["cash_per_unit"]) is None or d(event["cash_per_unit"]) < 0:
            raise ValueError("invalid dividend")
    if len({e["event_id"] for e in actions}) != len(actions):
        raise ValueError("duplicate action")
    initial_cash, budget = cash, cash * weight
    units = receivable = cumulative_fees = Decimal(0)
    prior_mark = None
    pending = weight > 0
    fills, rejections, ledger, daily = [], [], [], []
    rights, recognized, paid = {}, set(), set()
    for day in days:
        quote = quote_map.get(day)
        op = d(quote.get("open")) if quote else None
        close = d(quote.get("close")) if quote else None
        if (op is not None and op <= 0) or (close is not None and close <= 0):
            raise ValueError("nonpositive nominal quote")
        for event in actions:
            key = event["event_id"]
            if event["ex_date"] == day:
                if key not in rights or key in recognized:
                    raise ValueError("unrecorded or duplicate dividend right")
                receivable += rights[key]
                recognized.add(key)
                ledger.append({"date": day, "type": "ex_receivable", "event_id": key,
                               "amount": str(rights[key])})
        if pending and day in trading_days:
            blocked = op is None or quote.get("tradable") is False or restrictions.get(day) in ("halt", "blocked")
            if blocked:
                rejections.append({"date": day, "reason": "missing_open" if op is None else "explicit_restriction"})
            else:
                affordable = min(budget, cash) / (op * (1 + fee))
                buy_units = (affordable / LOT).to_integral_value(rounding=ROUND_FLOOR) * LOT
                if buy_units > 0:
                    cost, charge = buy_units * op, buy_units * op * fee
                    if cost + charge > budget or cost + charge > cash:
                        raise ValueError("buy exceeds original budget or cash")
                    cash -= cost + charge
                    units += buy_units
                    cumulative_fees += charge
                    fills.append({"date": day, "units": str(buy_units), "open": str(op),
                                  "notional": str(cost), "fee": str(charge)})
                pending = False  # B0 clears an executable order even when no full lot fits.
        stale = close is None
        if close is not None:
            prior_mark = close
        if prior_mark is None:
            if units:
                raise ValueError("no valuation mark for held units")
            mark = Decimal(0)
        else:
            mark = prior_mark
        for event in actions:
            key = event["event_id"]
            if event["record_date"] == day:
                if key in rights:
                    raise ValueError("duplicate record right")
                rights[key] = units * d(event["cash_per_unit"])
                ledger.append({"date": day, "type": "record_right", "event_id": key,
                               "units": str(units), "amount": str(rights[key])})
        for event in actions:
            key = event["event_id"]
            if event["pay_date"] == day:
                if key not in recognized or key in paid:
                    raise ValueError("payment without receivable")
                cash += rights[key]
                receivable -= rights[key]
                paid.add(key)
                ledger.append({"date": day, "type": "payment_day_end", "event_id": key,
                               "amount": str(rights[key])})
        wealth = cash + receivable + units * mark
        if min(cash, receivable, units, wealth) < 0:
            raise ValueError("negative account balance")
        bought = sum((d(fill["notional"]) for fill in fills), Decimal(0))
        paid_cash = sum((d(entry["amount"]) for entry in ledger
                         if entry["type"] == "payment_day_end"), Decimal(0))
        booked = sum((d(entry["amount"]) for entry in ledger
                      if entry["type"] == "ex_receivable"), Decimal(0))
        bought_units = sum((d(fill["units"]) for fill in fills), Decimal(0))
        residual = {"cash": cash - (initial_cash - bought - cumulative_fees + paid_cash),
                    "receivable": receivable - (booked - paid_cash),
                    "units": units - bought_units,
                    "wealth": wealth - (cash + receivable + units * mark)}
        if any(value != 0 for value in residual.values()):
            raise ValueError("daily cash, receivable, unit or wealth bridge failed")
        daily.append({"date": day, "cash": str(cash), "receivable": str(receivable),
                      "units": str(units), "mark": str(mark), "wealth": str(wealth),
                      "invested_pct": str(Decimal(100) * units * mark / wealth),
                      "is_trading_day": day in trading_days, "stale_mark": stale,
                      "reconciliation": {key: str(value) for key, value in residual.items()}})
    if recognized != paid or set(rights) != recognized:
        raise ValueError("unsettled dividend in fixed period")
    return {"daily": daily, "fills": fills, "rejections": rejections, "ledger": ledger,
            "initial_cash": str(initial_cash), "budget": str(budget), "weight": str(weight),
            "fee_rate": str(fee), "fees": str(cumulative_fees)}


def risk_metrics(daily: list[dict], initial_cash: Decimal, trading_days: set[str]) -> dict:
    """Trading-day volatility uses yesterday's natural-day wealth as denominator.

    Drawdown, worst day and recovery are observed across every natural day.
    Initial cash is the prior natural-day wealth for the period's first day.
    """
    if not daily:
        raise ValueError("empty account")
    wealth = [d(row["wealth"]) for row in daily]
    if any(v is None or v <= 0 for v in wealth):
        raise ValueError("invalid daily wealth")
    returns = [wealth[0] / initial_cash - 1] + [wealth[i] / wealth[i - 1] - 1 for i in range(1, len(wealth))]
    selected = [value for row, value in zip(daily, returns) if row["date"] in trading_days]
    prior_trading_wealth = initial_cash
    denominator_differences = []
    for i, row in enumerate(daily):
        if row["date"] in trading_days:
            prior_natural_wealth = initial_cash if i == 0 else wealth[i - 1]
            if prior_natural_wealth != prior_trading_wealth:
                denominator_differences.append(row["date"])
            prior_trading_wealth = wealth[i]
    invested = [d(row["invested_pct"]) if row.get("invested_pct") not in (None, "")
                else Decimal(100) * d(row["units"]) * d(row["mark"]) / d(row["wealth"])
                for row in daily]
    peak, max_drawdown, peak_day, active_peak, longest_days = initial_cash, Decimal(0), None, None, 0
    for row, value in zip(daily, wealth):
        if value >= peak:
            if active_peak is not None:
                longest_days = max(longest_days, (date.fromisoformat(row["date"]) - active_peak).days)
                active_peak = None
            peak, peak_day = value, row["date"]
        else:
            max_drawdown = min(max_drawdown, value / peak - 1)
            if active_peak is None:
                active_peak = date.fromisoformat(peak_day or (date.fromisoformat(row["date"]) - timedelta(days=1)).isoformat())
    if active_peak is not None:
        longest_days = max(longest_days, (date.fromisoformat(daily[-1]["date"]) - active_peak).days)
    return {"trading_day_volatility": sample_stdev(selected), "trading_observations": len(selected),
            "prior_natural_vs_prior_trading_difference_dates": denominator_differences,
            "average_invested_pct_natural_days": str(sum(invested) / len(invested)),
            "max_drawdown": str(max_drawdown),
            "worst_day": str(min(returns)), "longest_underwater_calendar_days": longest_days,
            "unrecovered_at_end": active_peak is not None, "end_wealth": str(wealth[-1]),
            "net_change": str(wealth[-1] - initial_cash),
            "net_change_ratio": str(wealth[-1] / initial_cash - 1)}


def period_fees(prior_row: dict, end_row: dict) -> Decimal:
    def cumulative(row):
        bridge = row["reconciliation"]
        if isinstance(bridge, str):
            bridge = json.loads(bridge)
        return d(bridge["fees_cny"])
    amount = cumulative(end_row) - cumulative(prior_row)
    if amount < 0:
        raise ValueError("negative period fee increment")
    return amount


def compute_historical_in_memory(root: Path, manifest: dict) -> dict:
    """Prepared two-path calculation. Controller must release before calling.

    This function has no filesystem writes or archived-code imports. A released
    driver must save complete outputs to its independently authorized plan.
    """
    if manifest.get("status") != "synthetic_only_pending_controller_release":
        raise ValueError("unexpected preparation manifest")
    bindings = manifest["bindings"]
    verify_sources(root, bindings)

    def path(key):
        return root / bindings[key]["path"]

    calendar = json.loads(path("original_calendar").read_text())
    trading = {day for day, info in calendar["days"].items() if info["is_trading_day"]}
    a = {(name, fee): csv_rows(path(f"original_a_{name.lower()}_{fee}_daily"))
         for name in ("ALL", "SMA") for fee in FEES}
    b0 = {fee: csv_rows(path(f"original_b0_{fee}_daily")) for fee in FEES}
    for fee in FEES:
        all_2025 = [r for r in a["ALL", fee] if "2025-01-01" <= r["date"] <= "2025-12-31"]
        sma_2025 = [r for r in a["SMA", fee] if "2025-01-01" <= r["date"] <= "2025-12-31"]
        if not all_2025 or all_2025 != sma_2025:
            raise ValueError(f"A_ALL and A_SMA differ in 2025: {fee}")
        state = unique_by_date(a["ALL", fee]).get("2025-12-31")
        if state is None or any(d(state[k]) != target for k, target in
                                (("cash", START_CASH[fee]), ("wealth", START_CASH[fee]),
                                 ("units", Decimal(0)), ("receivable", Decimal(0)))):
            raise ValueError(f"incorrect cash carry at 2025-12-31: {fee}")
    fit = calibrate_2025(a["ALL", "base"], b0["base"], trading)
    weight = Decimal(str(fit["weight"]))
    quotes = [r for r in csv_rows(path("original_nominal_quotes")) if START <= r["date"] <= END]
    reference = json.loads(path("original_510300_execution_reference").read_text())
    restrictions = {r["date"]: r["restriction"] for r in reference
                    if START <= r["date"] <= END and r["restriction"] is not None}
    quote_dates = {r["date"] for r in quotes}
    reference_dates = {r["date"] for r in reference if START <= r["date"] <= END}
    period_trading = {day for day in trading if START <= day <= END}
    if quote_dates != reference_dates or quote_dates != period_trading:
        raise ValueError("nominal quote, execution reference or official calendar date mismatch")
    all_actions = json.loads(path("original_510300_mapped_actions").read_text())
    crossing = [event for event in all_actions if event["type"] == "dividend"
                and (START <= event["record_date"] <= END or START <= event["ex_date"] <= END
                     or START <= event["pay_date"] <= END)
                and not (START <= event["record_date"] < event["ex_date"] <= event["pay_date"] <= END)]
    if crossing:
        raise ValueError("corporate action crosses period boundary")
    actions = [event for event in all_actions if event["type"] == "dividend"
               and START <= event["record_date"] < event["ex_date"] <= event["pay_date"] <= END]
    if any(event["type"] != "dividend" and START <= event.get("date", "") <= END for event in all_actions):
        raise ValueError("period split requires separate sourced allocation rule")
    outcomes = {}
    for fee_name, rate in FEES.items():
        simulation = simulate_hold(cash=START_CASH[fee_name], fee=rate, weight=weight,
                                   quotes=quotes, trading_days=period_trading,
                                   restrictions=restrictions, actions=actions)
        metrics = risk_metrics(simulation["daily"], START_CASH[fee_name], period_trading)
        comparisons = {}
        for name in ("ALL", "SMA"):
            saved = [r for r in a[name, fee_name] if START <= r["date"] <= END]
            if [r["date"] for r in saved] != natural_dates(START, END):
                raise ValueError(f"A daily period incomplete: {name} {fee_name}")
            a_metrics = risk_metrics(saved, START_CASH[fee_name], period_trading)
            prior_row = unique_by_date(a[name, fee_name])["2025-12-31"]
            a_metrics["fees_2026h1"] = str(period_fees(prior_row, saved[-1]))
            a_sigma = a_metrics["trading_day_volatility"]
            ratio = metrics["trading_day_volatility"] / a_sigma if a_sigma else None
            comparisons[name] = {"saved_A_metrics": a_metrics, "volatility_ratio": ratio,
                                 "within_0_90_to_1_10": ratio is not None and 0.90 <= ratio <= 1.10,
                                 "end_wealth_difference": str(d(metrics["end_wealth"]) - d(a_metrics["end_wealth"]))}
        metrics["fees_2026h1"] = simulation["fees"]
        outcomes[fee_name] = {"account": simulation, "metrics": metrics, "against_A": comparisons}
    return {"calibration": fit, "outcomes": outcomes,
            "scope": "one ETF, observed 2026H1; no retuning or trading authorization"}


if __name__ == "__main__":
    raise SystemExit("Preparation stage only: run synthetic_checks.py. Historical CLI awaits controller release.")
