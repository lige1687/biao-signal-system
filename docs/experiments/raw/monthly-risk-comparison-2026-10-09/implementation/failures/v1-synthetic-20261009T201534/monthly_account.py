"""Pure monthly account arithmetic; no archived imports, IO, signals or runner.

Historical calls belong exclusively to the released one-time driver. All
monetary arithmetic uses Decimal; statistics retain the frozen sample ddof=1.
"""

from __future__ import annotations

import calendar
import math
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR

D = Decimal
LOT = D(100)
LOOKBACK = 63


def number(value):
    if value is None or value == "" or isinstance(value, bool):
        raise ValueError("missing or nonnumeric value")
    result = D(str(value))
    if not result.is_finite():
        raise ValueError("nonfinite value")
    return result


def flag(value):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError("unknown boolean identity")


def dates(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("inverted period")
    return [(first + timedelta(days=i)).isoformat() for i in range((last-first).days+1)]


def by_date(rows):
    result = {row["date"]: row for row in rows}
    if len(result) != len(rows) or list(result) != sorted(result):
        raise ValueError("duplicate or unordered dates")
    for day in result:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("noncanonical date")
    return result


def sample_stdev(values):
    if len(values) < 2:
        raise ValueError("insufficient returns")
    vals = [float(number(v)) for v in values]
    mean = math.fsum(vals) / len(vals)
    return math.sqrt(math.fsum((v-mean)**2 for v in vals)/(len(vals)-1))


def previous_month(month):
    first = date.fromisoformat(month + "-01")
    return (first-timedelta(days=1)).strftime("%Y-%m")


def monthly_targets(accounts, trading_days, start="2026-01-01", end="2026-06-30"):
    """Six prior-month decisions, using ONLY saved base-fee A and B0 wealth.

    The last 63 official trading dates are required to be complete/common;
    missing rows are errors, never silently replaced by older observations.
    A chronological prefix through the cutoff yields the identical decision.
    """
    if set(accounts) != {"A_ALL", "A_SMA", "B0"}:
        raise ValueError("expected exact three base-fee accounts")
    maps = {key: by_date(rows) for key, rows in accounts.items()}
    official = sorted(set(trading_days))
    months = sorted({day[:7] for day in dates(start, end)})
    targets = {key: [] for key in ("A_ALL", "A_SMA")}
    for month in months:
        prior_month = previous_month(month)
        eligible = [day for day in official if day[:7] <= prior_month]
        month_dates = [day for day in eligible if day[:7] == prior_month]
        if not month_dates or len(eligible) < LOOKBACK:
            raise ValueError(f"fewer than 63 or missing prior month: {month}")
        cutoff = month_dates[-1]
        window = eligible[-LOOKBACK:]
        returns, denominators = {}, {}
        for name, source in maps.items():
            returns[name], denominators[name] = [], []
            for day in window:
                prior = (date.fromisoformat(day)-timedelta(days=1)).isoformat()
                if day not in source or prior not in source:
                    raise ValueError(f"missing common date/prior natural day: {name} {day}")
                if not flag(source[day]["is_trading_day"]):
                    raise ValueError(f"trading identity mismatch: {name} {day}")
                wealth, before = number(source[day]["wealth"]), number(source[prior]["wealth"])
                if min(wealth, before) <= 0:
                    raise ValueError("nonpositive complete wealth")
                returns[name].append(wealth/before-1)
                denominators[name].append({"date": day, "prior_natural_date": prior,
                                           "wealth": str(wealth), "prior_wealth": str(before),
                                           "return": str(returns[name][-1])})
        sigma_b0 = sample_stdev(returns["B0"])
        if sigma_b0 == 0:
            raise ValueError(f"zero B0 volatility at {cutoff}")
        for name in targets:
            sigma_a = sample_stdev(returns[name])
            weight = min(1.0, sigma_a/sigma_b0)
            targets[name].append({"month": month, "active_from": month+"-01",
                                  "cutoff": cutoff, "available_at": cutoff+" close",
                                  "window_dates": window, "observations": LOOKBACK,
                                  "sigma_a": sigma_a, "sigma_b0": sigma_b0,
                                  "weight": str(weight), "source_fee": "base",
                                  "returns_a": denominators[name],
                                  "returns_b0": denominators["B0"]})
    return targets


def floor_lot(value):
    return (number(value)/LOT).to_integral_value(rounding=ROUND_FLOOR)*LOT


def adjustment(cash, receivable, units, opening_price, weight, fee):
    """Target before fees, then cap the one BUY by cash including fees."""
    cash, receivable, units, opening_price, weight, fee = map(
        number, (cash, receivable, units, opening_price, weight, fee))
    if min(cash, receivable, units, fee) < 0 or opening_price <= 0 or not 0 <= weight <= 1:
        raise ValueError("invalid adjustment input")
    if units % LOT:
        raise ValueError("non-lot holdings need sourced action handling")
    wealth = cash+receivable+units*opening_price
    target = floor_lot(weight*wealth/opening_price)
    wanted = target-units
    affordable = floor_lot(cash/(opening_price*(1+fee)))
    delta = min(wanted, affordable) if wanted > 0 else max(wanted, -units)
    notional, charge = abs(delta)*opening_price, abs(delta)*opening_price*fee
    new_cash = cash-delta*opening_price-charge
    if new_cash < 0 or units+delta < 0 or delta % LOT:
        raise ValueError("cash, sell or lot bound failed")
    return {"opening_wealth": str(wealth), "target_units": str(target),
            "requested_delta": str(wanted), "cash_affordable_buy_units": str(affordable),
            "units_delta": str(delta), "notional": str(notional), "fee": str(charge),
            "cash_before": str(cash), "cash_after": str(new_cash),
            "receivable_before": str(receivable), "units_before": str(units),
            "units_after": str(units+delta), "price": str(opening_price),
            "fee_rate": str(fee), "weight": str(weight)}


def validate_targets(targets, start, end):
    months = sorted({day[:7] for day in dates(start, end)})
    if [t["month"] for t in targets] != months:
        raise ValueError("exactly one chronological target per month required")
    for target in targets:
        cutoff, month = target["cutoff"], target["month"]
        if cutoff[:7] != previous_month(month) or cutoff >= month+"-01":
            raise ValueError("future/same-month target cutoff")
        if not 0 <= number(target["weight"]) <= 1:
            raise ValueError("weight outside [0,1]")


def simulate_monthly(*, cash, fee, targets, quotes, trading_days, restrictions,
                     actions, start="2026-01-01", end="2026-06-30"):
    """Natural-day ledger with at most one executable adjustment per month.

    Preopen: supersede expired target, recognize ex-date receivable, execute.
    After close: mark, record entitlements, transfer paid receivables to cash.
    Missing opens/explicit old-core restrictions wait; executable zero-lot
    adjustments clear. No fill or reinvestment follows that in the same month.
    """
    cash, fee = number(cash), number(fee)
    if cash <= 0 or fee < 0:
        raise ValueError("invalid initial cash/fee")
    validate_targets(targets, start, end)
    quote_map = by_date(quotes)
    natural = dates(start, end)
    trading = set(trading_days)
    if not trading.issubset(natural) or not set(quote_map).issubset(trading):
        raise ValueError("quotes/calendar outside period or nontrading quote")
    if not set(restrictions).issubset(trading):
        raise ValueError("restriction outside trading dates")
    if any(v not in (None, "halt", "blocked") for v in restrictions.values()):
        raise ValueError("unknown restriction must not be silently ignored")
    for event in actions:
        if event["type"] != "dividend" or event.get("unit_basis") != "old":
            raise ValueError("unhandled corporate action; exact source adapter required")
        if not start <= event["record_date"] < event["ex_date"] <= event["pay_date"] <= end:
            raise ValueError("cross-boundary or invalid dividend order")
        if number(event["cash_per_unit"]) < 0:
            raise ValueError("negative dividend")
    if len({e["event_id"] for e in actions}) != len(actions):
        raise ValueError("duplicate event id")
    initial_cash = cash
    units = receivable = fees = D(0)
    bought = sold = paid_total = booked = unit_delta = D(0)
    mark, pending = None, None
    target_map = {t["month"]: t for t in targets}
    rights, recognized, paid = {}, set(), set()
    daily, fills, orders, rejections, action_ledger = [], [], [], [], []
    current_month = None
    for day in natural:
        month = day[:7]
        if month != current_month:
            if pending is not None:
                pending.update(status="superseded", superseded_at=day, replacement_month=month)
            target = target_map[month]
            pending = {"order_id": month, "month": month, "decision_at": target["cutoff"]+" close",
                       "available_from": month+"-01", "weight": target["weight"], "status": "pending"}
            orders.append(pending)
            current_month = month
        for event in actions:
            key = event["event_id"]
            if event["ex_date"] == day:
                if key not in rights or key in recognized:
                    raise ValueError("unrecorded/duplicate dividend right")
                amount = rights[key]
                receivable += amount
                booked += amount
                recognized.add(key)
                action_ledger.append({"date": day, "phase": "before_open", "type": "ex_receivable",
                                      "event_id": key, "amount": str(amount)})
        quote = quote_map.get(day)
        op = number(quote["open"]) if quote and quote.get("open") not in (None, "") else None
        close = number(quote["close"]) if quote and quote.get("close") not in (None, "") else None
        if any(v is not None and v <= 0 for v in (op, close)):
            raise ValueError("nonpositive nominal quote")
        tradable = flag(quote["tradable"]) if quote and "tradable" in quote else True
        if pending is not None and day in trading:
            blocked = op is None or not tradable or restrictions.get(day) in ("halt", "blocked")
            if blocked:
                rejections.append({"date": day, "order_id": pending["order_id"],
                                   "reason": "missing_open" if op is None else "explicit_restriction",
                                   "decision_at": pending["decision_at"]})
            else:
                trade = adjustment(cash, receivable, units, op, pending["weight"], fee)
                delta, charge = number(trade["units_delta"]), number(trade["fee"])
                cash, units = number(trade["cash_after"]), number(trade["units_after"])
                fees += charge
                unit_delta += delta
                if delta > 0:
                    bought += number(trade["notional"])
                elif delta < 0:
                    sold += number(trade["notional"])
                pending.update(executed_at=day+" open", adjustment=trade,
                               status="filled" if delta else "no_executable_lot_or_target_met")
                if delta:
                    fills.append({"date": day, "phase": "open", "order_id": pending["order_id"],
                                  "decision_at": pending["decision_at"], **trade})
                pending = None
        stale = close is None
        if close is not None:
            mark = close
        if mark is None:
            if units:
                raise ValueError("no valuation mark for holdings")
            mark = D(0)
        for event in actions:
            key = event["event_id"]
            if event["record_date"] == day:
                if key in rights:
                    raise ValueError("duplicate record right")
                rights[key] = units*number(event["cash_per_unit"])
                action_ledger.append({"date": day, "phase": "after_close", "type": "record_right",
                                      "event_id": key, "units": str(units), "amount": str(rights[key])})
            if event["pay_date"] == day:
                if key not in recognized or key in paid:
                    raise ValueError("payment without unique recognized claim")
                amount = rights[key]
                cash += amount
                receivable -= amount
                paid_total += amount
                paid.add(key)
                action_ledger.append({"date": day, "phase": "after_close", "type": "payment_day_end",
                                      "event_id": key, "amount": str(amount)})
        wealth = cash+receivable+units*mark
        bridge = {"cash_residual_cny": cash-(initial_cash+sold-bought-fees+paid_total),
                  "receivable_residual_cny": receivable-(booked-paid_total),
                  "unit_residual": units-unit_delta,
                  "wealth_residual_cny": wealth-(cash+receivable+units*mark),
                  "buy_notional_cny": bought, "sell_notional_cny": sold,
                  "paid_dividends_cny": paid_total, "recognized_dividends_cny": booked,
                  "fees_cny": fees}
        if min(cash, receivable, units) < 0 or wealth <= 0:
            raise ValueError("negative balances/nonpositive wealth")
        if any(bridge[k] != 0 for k in ("cash_residual_cny", "receivable_residual_cny",
                                        "unit_residual", "wealth_residual_cny")):
            raise ValueError("daily bridge failed")
        daily.append({"date": day, "cash": str(cash), "receivable": str(receivable),
                      "units": str(units), "raw_close": str(close) if close is not None else None,
                      "mark": str(mark), "wealth": str(wealth), "is_trading_day": day in trading,
                      "stale_mark": stale, "mark_basis": "stale_prior_mark" if stale else "nominal_close",
                      "invested_pct": str(100*units*mark/wealth),
                      "reconciliation": {k: str(v) for k, v in bridge.items()}})
    if recognized != paid or set(rights) != recognized:
        raise ValueError("unsettled/unrecognized corporate action")
    if pending is not None:
        pending.update(status="pending_at_period_end")
    return {"initial_cash": str(initial_cash), "fee_rate": str(fee), "fees": str(fees),
            "daily": daily, "orders": orders, "fills": fills,
            "rejections": rejections, "action_ledger": action_ledger,
            "terminal_liquidation": False}


def daily_returns(rows, initial_wealth, start, end):
    if [r["date"] for r in rows] != dates(start, end):
        raise ValueError("complete natural-day ledger required")
    before = number(initial_wealth)
    result = []
    for row in rows:
        wealth = number(row["wealth"])
        if min(wealth, before) <= 0:
            raise ValueError("nonpositive wealth")
        result.append(wealth/before-1)
        before = wealth
    return result


def metrics(rows, initial_wealth, trading_days, start, end):
    changes = daily_returns(rows, initial_wealth, start, end)
    trading = set(trading_days)
    if {r["date"] for r in rows if flag(r["is_trading_day"])} != trading:
        raise ValueError("metric calendar identity mismatch")
    selected = [r for row, r in zip(rows, changes) if row["date"] in trading]
    peak, drop = number(initial_wealth), D(0)
    peak_day = date.fromisoformat(start)-timedelta(days=1)
    active_peak, longest = None, 0
    for row in rows:
        day, wealth = date.fromisoformat(row["date"]), number(row["wealth"])
        if wealth >= peak:
            if active_peak is not None:
                longest = max(longest, (day-active_peak).days)
                active_peak = None
            peak, peak_day = wealth, day
        else:
            drop = min(drop, wealth/peak-1)
            if active_peak is None:
                active_peak = peak_day
    if active_peak is not None:
        longest = max(longest, (date.fromisoformat(end)-active_peak).days)
    final = number(rows[-1]["wealth"])
    return {"trading_day_volatility": sample_stdev(selected), "trading_observations": len(selected),
            "natural_observations": len(rows), "initial_wealth": str(initial_wealth),
            "end_wealth": str(final), "net_change": str(final-number(initial_wealth)),
            "net_change_ratio": str(final/number(initial_wealth)-1), "max_drawdown": str(drop),
            "worst_day": str(min(changes)), "longest_underwater_calendar_days": longest,
            "unrecovered_at_end": active_peak is not None,
            "average_invested_pct_natural_days": str(sum(number(r["invested_pct"]) for r in rows)/len(rows))}


def opportunity_description(new_daily, initial_wealth, b0_daily, b0_prior_wealth, start, end):
    """Saved B0 return on the same day's new-account starting wealth.

    A diagnostic amount on B0 rising/falling days, NOT an additional account,
    executable buy policy, or additive decomposition of terminal wealth gap.
    All signed gaps are retained; a negative upside gap means new did better.
    """
    new_returns = daily_returns(new_daily, initial_wealth, start, end)
    b0_returns = daily_returns(b0_daily, b0_prior_wealth, start, end)
    before = number(initial_wealth)
    rows, upside, downside = [], D(0), D(0)
    for row, r_new, r_b0 in zip(new_daily, new_returns, b0_returns):
        gap = before*(r_b0-r_new)
        if r_b0 > 0:
            upside += gap
        elif r_b0 < 0:
            downside -= gap
        rows.append({"date": row["date"], "starting_new_wealth": str(before),
                     "saved_b0_return": str(r_b0), "new_return": str(r_new),
                     "same_day_b0_minus_new_cny": str(gap)})
        before = number(row["wealth"])
    return {"description": "原B0上涨日，同一日初新账户资金按B0当日变化计算减去新账户实际变化的金额；含费用/分红影响。负值保留。每日起点不同，不等于期末资产差，也不能作为独特收益相加。",
            "b0_up_days_gap_cny": str(upside), "b0_down_days_avoided_cny": str(downside),
            "daily": rows, "additional_simulated_paths": 0}
