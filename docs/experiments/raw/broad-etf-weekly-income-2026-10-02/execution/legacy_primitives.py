"""Copied first12 execution primitives; source/line ranges in input-lock.json.
No old raw imports or account simulator are used at runtime.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, ROUND_FLOOR
D = Decimal

def week_key(day: str):
    iso = date.fromisoformat(day).isocalendar()
    return iso.year, iso.week

def effective_reference(reference: D, actions, symbol, day):
    for action in sorted((a for a in actions if a["symbol"] == symbol and a["effective_date"] == day), key=lambda x: x["event_id"]):
        if action["type"] == "cash_dividend":
            reference -= D(action["cash"])
        elif action["type"] == "split":
            reference /= D(action["ratio"])
    return reference


def unavailable(symbol, day, bar, reference, settings):
    if day in settings["blocked_dates"].get(symbol, []):
        return "known_open_unavailable"
    if bar is None:
        return "missing_quote"
    if reference is None:
        return None
    limit = D(str(settings["limits"][symbol]))
    for effective, value in settings["limit_changes"].get(symbol, []):
        if effective <= day:
            limit = D(str(value))
    boundary = reference * limit - D("0.00051")
    return "at_open_limit_conservative" if abs(bar["open"] - reference) >= boundary else None


def floor_lot(units: D, lot=D("100")) -> D:
    return (units / lot).to_integral_value(rounding=ROUND_FLOOR) * lot


def execute_target(cash, receivable, units, price, target, fee, apply_band=False, lot=D("100")):
    equity_open = cash + receivable + units * price
    actual = units * price / equity_open if equity_open else D("0")
    if apply_band and abs(target - actual) < D("0.05"):
        return cash, units, None, "inside_5pp_band", equity_open, actual
    desired_value = equity_open * target
    if desired_value > units * price:
        wanted = floor_lot((desired_value - units * price) / price, lot)
        affordable = floor_lot(cash / (price * (D("1") + fee)), lot)
        qty = min(wanted, affordable)
        if qty <= 0:
            return cash, units, None, "buy_rounds_to_zero_or_cash_short", equity_open, actual
        notional = qty * price
        cost = notional * fee
        return cash - notional - cost, units + qty, ("buy", qty, notional, cost), None, equity_open, actual
    qty = units if target == 0 else min(units, floor_lot((units * price - desired_value) / price, lot))
    if qty <= 0:
        return cash, units, None, "sell_rounds_to_zero", equity_open, actual
    notional = qty * price
    cost = notional * fee
    return cash + notional - cost, units - qty, ("sell", qty, notional, cost), None, equity_open, actual
