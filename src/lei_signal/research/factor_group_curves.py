"""Deterministic daily quote-proxy account for frozen monthly research targets.

Daily high/low/volume are ex-post restrictions on an opening quote simulation;
they are not information known at the open. Adjusted fractional quote units are
used throughout. No dividend cash, borrow, intramonth retry, or terminal sale.
"""

from __future__ import annotations

from math import isfinite


def _positive(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if isfinite(number) and number > 0 else None


def _quote(row, key):
    return _positive(row.get(key)) if isinstance(row, dict) else None


def _valid(row):
    return isinstance(row, dict) and row.get("source_valid") is True


def _fill_reason(row, side):
    if not _valid(row):
        return "source_invalid"
    if str(row.get("tradestatus")) != "1":
        return "not_trading"
    if _positive(row.get("volume")) is None:
        return "no_volume"
    if _quote(row, "open") is None:
        return "no_open"
    if side == "buy" and str(row.get("isST")) != "0":
        return "st_buy_blocked"
    high, low, previous = (_quote(row, key) for key in ("high", "low", "preclose"))
    if any(value is None for value in (high, low, previous)):
        return "limit_quote_unknown"
    if high < low:
        return "invalid_range"
    if abs(high - low) <= 1e-10 * max(high, low) and (
        (side == "buy" and low > previous) or (side == "sell" and high < previous)
    ):
        return "one_price_adverse_buy" if side == "buy" else "one_price_adverse_sell"
    return None


def _finite_nonnegative(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite nonnegative number") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return number


def simulate(
    calendar,
    market,
    targets,
    cost_bps=25,
    initial_cash=100000,
    start_date="2014-12-31",
    end_date="2025-12-31",
):
    """Run one cash account from frozen month-end weights.

    ``calendar`` includes the preceding decision date when needed. ``targets``
    must explicitly contain every actionable month end; missing means error,
    whereas ``qualified=False, weights={}`` means a cash decision. Results are
    plain dicts with ``daily``, ``orders``, ``trades``, ``month_end_holdings``.
    """
    dates = list(calendar)
    if not dates or any(not isinstance(date, str) for date in dates) or dates != sorted(set(dates)):
        raise ValueError("calendar must be sorted unique date strings")
    if start_date > end_date:
        raise ValueError("start_date after end_date")
    if not isinstance(market, dict) or not isinstance(targets, dict):
        raise ValueError("market and targets must be mappings")
    cash = _finite_nonnegative(initial_cash, "initial_cash")
    if cash <= 0:
        raise ValueError("initial_cash must be positive")
    fee_rate = _finite_nonnegative(cost_bps, "cost_bps") / 10000
    actionable_month_ends = {
        before for before, after in zip(dates, dates[1:]) if before[:7] != after[:7]
    }
    for decision, item in targets.items():
        if decision not in actionable_month_ends or not isinstance(item, dict) or type(item.get("qualified")) is not bool:
            raise ValueError(f"invalid target decision: {decision}")
        weights = item.get("weights")
        if not isinstance(weights, dict):
            raise ValueError(f"invalid weights: {decision}")
        if not item["qualified"] and weights:
            raise ValueError(f"unqualified target must be cash: {decision}")
        if item["qualified"] and not weights:
            raise ValueError(f"qualified target must name holdings: {decision}")
        total = 0.0
        for code, weight in weights.items():
            if not isinstance(code, str) or not code:
                raise ValueError("invalid target code")
            total += _finite_nonnegative(weight, f"weight {code}")
        if total > 1 + 1e-10:
            raise ValueError(f"weights exceed one: {decision}")
    for code, rows in market.items():
        if not isinstance(code, str) or not isinstance(rows, dict):
            raise ValueError("market must map code to date rows")

    # A decision is actionable only on the first trading date of the next month.
    decisions = {}
    for before, after in zip(dates, dates[1:]):
        if before[:7] != after[:7] and start_date <= after <= end_date:
            if before not in targets:
                raise ValueError(f"missing month-end target: {before}")
            decisions[after] = before

    holdings = {}  # code -> units, last known mark, mark date, permanently broken
    daily, orders, trades, month_end_holdings = [], [], [], []
    fees_total = 0.0
    tolerance = 1e-8

    def row(code, date):
        return market.get(code, {}).get(date)

    def order_record(date, decision, code, side, qty, gross, fee, reason):
        record = {
            "date": date, "decision_date": decision, "code": code, "side": side,
            "qty": qty, "gross": gross, "fee": fee,
            "status": "filled" if reason is None else "blocked", "reason": reason,
        }
        orders.append(record)
        return record

    for date in dates:
        if not start_date <= date <= end_date:
            continue
        for code, position in holdings.items():
            if not position["broken"] and isinstance(row(code, date), dict) and row(code, date).get("basis_break") is True:
                position["broken"] = True
        opening_marks = {}
        for code, position in holdings.items():
            quote = row(code, date)
            opening_marks[code] = (
                _quote(quote, "open") if not position["broken"] and _valid(quote)
                and str(quote.get("tradestatus")) == "1" and _positive(quote.get("volume"))
                else None
            ) or position["mark"]
        nav_before = cash + sum(p["units"] * opening_marks[c] for c, p in holdings.items())
        if not isfinite(nav_before) or nav_before < -tolerance:
            raise ArithmeticError("invalid opening net asset value")
        gross_today = 0.0
        blocked_sell_gross_today = 0.0
        decision = decisions.get(date)
        if decision is not None:
            weights = targets[decision]["weights"]
            desired = {code: nav_before * weight for code, weight in weights.items()}
            sells = []
            buys = []
            for code in sorted(set(holdings) | set(weights)):
                position = holdings.get(code)
                quote = row(code, date)
                open_price = _quote(quote, "open")
                current = position["units"] * opening_marks[code] if position else 0.0
                wanted = desired.get(code, 0.0)
                delta = wanted - current
                if delta < -tolerance:
                    sells.append((code, -delta, open_price))
                elif delta > tolerance:
                    buys.append((code, delta, open_price))
            for code, desired_gross, price in sells:
                position = holdings[code]
                reason = "basis_break" if position["broken"] else _fill_reason(row(code, date), "sell")
                if reason is None:
                    # The intent is expressed in current open value, with no short sale.
                    gross = min(desired_gross, position["units"] * price)
                    qty = gross / price
                    fee = gross * fee_rate
                    position["units"] -= qty
                    position["mark"] = price
                    position["mark_date"] = date
                    cash += gross - fee
                    fees_total += fee
                    gross_today += gross
                    order = order_record(date, decision, code, "sell", qty, gross, fee, None)
                    trades.append({**order, "cash_after": cash, "units_after": max(0.0, position["units"])})
                    if position["units"] <= tolerance:
                        del holdings[code]
                else:
                    blocked_sell_gross_today += desired_gross
                    order_record(date, decision, code, "sell", desired_gross / price if price else None, desired_gross, 0.0, reason)
            # Scale all intended buys once, before their individual fill checks.
            buy_total = sum(gross for _, gross, _ in buys)
            scale = min(1.0, cash / ((1 + fee_rate) * buy_total)) if buy_total else 1.0
            for code, requested, price in buys:
                gross = requested * scale
                if gross <= tolerance:
                    order_record(date, decision, code, "buy", 0.0, 0.0, 0.0, "insufficient_cash")
                    continue
                existing = holdings.get(code)
                reason = "basis_break" if existing and existing["broken"] else _fill_reason(row(code, date), "buy")
                if reason is not None:
                    order_record(date, decision, code, "buy", gross / price if price else None, gross, 0.0, reason)
                    continue
                qty = gross / price
                fee = gross * fee_rate
                cash -= gross + fee
                if cash < -tolerance:
                    raise ArithmeticError("buy exceeded cash")
                cash = max(0.0, cash)
                fees_total += fee
                gross_today += gross
                if existing:
                    existing["units"] += qty
                    existing["mark"] = price
                    existing["mark_date"] = date
                else:
                    holdings[code] = {"units": qty, "mark": price, "mark_date": date, "broken": False}
                order = order_record(date, decision, code, "buy", qty, gross, fee, None)
                trades.append({**order, "cash_after": cash, "units_after": holdings[code]["units"]})

        market_value = unknown_value = 0.0
        stale_count = broken_count = 0
        for code, position in holdings.items():
            quote = row(code, date)
            closing = None if position["broken"] else (
                _quote(quote, "close") if _valid(quote) and str(quote.get("tradestatus")) == "1"
                and _positive(quote.get("volume")) else None
            )
            if closing is not None:
                position["mark"] = closing
                position["mark_date"] = date
                position["stale_today"] = False
            else:
                position["stale_today"] = True
                stale_count += 1
                unknown_value += position["units"] * position["mark"]
            broken_count += position["broken"]
            market_value += position["units"] * position["mark"]
        nav = cash + market_value
        if not all(isfinite(x) for x in (cash, market_value, unknown_value, nav, fees_total)) or nav < -tolerance:
            raise ArithmeticError("invalid daily account value")
        if nav <= tolerance:
            raise ArithmeticError("net asset value is zero")
        deviation = None
        if decision is not None:
            expected = targets[decision]["weights"]
            actual = {code: p["units"] * p["mark"] / nav for code, p in holdings.items()}
            deviation = sum(abs(actual.get(c, 0.0) - expected.get(c, 0.0)) for c in set(actual) | set(expected))
        daily.append({
            "date": date, "nav_quote_proxy": nav, "cash": cash, "market_value": market_value,
            "unknown_value": unknown_value, "unknown_fraction": unknown_value / nav,
            "stress_zero_unknown_nav": nav - unknown_value,
            "fees_cumulative": fees_total, "gross_traded_today": gross_today,
            "nav_before_trade": nav_before, "held_count": len(holdings),
            "stale_count": stale_count, "basis_broken_count": broken_count,
            "blocked_sell_gross_today": blocked_sell_gross_today,
            "close_target_deviation": deviation, "cash_fraction": cash / nav,
        })
        next_index = dates.index(date) + 1
        if next_index == len(dates) or dates[next_index][:7] != date[:7]:
            for code, p in sorted(holdings.items()):
                month_end_holdings.append({
                    "date": date, "code": code, "units": p["units"], "mark": p["mark"],
                    "mark_date": p["mark_date"], "stale": p["stale_today"],
                    "broken": p["broken"], "lastknownweight": p["units"] * p["mark"] / nav,
                })
    return {"daily": daily, "orders": orders, "trades": trades, "month_end_holdings": month_end_holdings}
