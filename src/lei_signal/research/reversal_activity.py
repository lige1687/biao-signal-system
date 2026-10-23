"""Frozen monthly activity strata and opening-quote research accounts.

This is a retrospective quote proxy, not a live fill model. Opening logic may
read only *_open fields and a basis-break flag inherited from prior closes.
Closing qualification is deliberately applied after orders have been recorded.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from math import isfinite


FORMATION_MONTHS = tuple(f"{y:04d}-{m:02d}" for y in range(2014, 2026)
                         for m in range(1, 13) if "2014-12" <= f"{y:04d}-{m:02d}" <= "2025-11")
PORTFOLIOS = tuple([f"G{i}" for i in range(1, 6)] + ["lowvol", "pool", "rev_volbalanced"])
UNCERTAIN_CLOSE_REASONS = frozenset({
    "blank numeric source field", "nonpositive numeric source field",
    "invalid numeric source field", "calendar_gap_before_row",
})


def finite(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if isfinite(x) else None


def positive(value):
    x = finite(value)
    return x if x is not None and x > 0 else None


def _split(items, count):
    q, r = divmod(len(items), count)
    out, cursor = [], 0
    for i in range(count):
        n = q + (i < r)
        out.append(items[cursor:cursor+n])
        cursor += n
    return out


def amount60(raw_by_code, calendar, code, month_end):
    """Exactly 60 exchange dates ending at formation, including suspensions."""
    try:
        stop = calendar.index(month_end)
    except ValueError as exc:
        raise ValueError("month end absent from calendar") from exc
    days = calendar[max(0, stop-59):stop+1]
    if len(days) != 60:
        return None, "fewer_than_60_calendar_days"
    values = []
    rows = raw_by_code.get(code, {})
    for day in days:
        raw = rows.get(day)
        if raw is None or "amount" not in raw:
            return None, f"amount_missing:{day}"
        if str(raw.get("tradestatus")) not in ("0", "1"):
            return None, f"tradestatus_invalid:{day}"
        value = finite(raw["amount"])
        if value is None or value < 0:
            return None, f"amount_invalid:{day}"
        if str(raw["tradestatus"]) == "0" and value != 0:
            return None, f"suspended_amount_nonzero:{day}"
        values.append(value)
    average = sum(values) / 60
    if not isfinite(average):
        return None, "amount_mean_nonfinite"
    return average, None


def form_month(rows, raw_by_code, calendar, month_end, min_names=30):
    """Return decisions using an explicit whitelist of formation-time fields.

    A missing outcome never affects selection. One observation per code is
    required; invalid amount/feature observations are rejected with reasons.
    """
    if month_end not in calendar or month_end != max(d for d in calendar if d[:7] == month_end[:7]):
        raise ValueError("not an exchange month end")
    selected, rejected, seen = [], [], set()
    for original in rows:
        code = original.get("code")
        if not isinstance(code, str) or not code or code in seen:
            raise ValueError("duplicate or invalid formation code")
        seen.add(code)
        hot, vol, momentum = (finite(original.get(k)) for k in ("hot", "vol60", "momentum"))
        if hot is None or vol is None or vol < 0 or momentum is None:
            rejected.append({"code": code, "reason": "formation_feature_invalid"})
            continue
        amount, reason = amount60(raw_by_code, calendar, code, month_end)
        if reason:
            rejected.append({"code": code, "reason": reason})
            continue
        selected.append({"code": code, "hot": hot, "vol60": vol,
                         "momentum": momentum, "amount60": amount})
    selected.sort(key=lambda r: (r["amount60"], r["code"]))
    strata = []
    for index, names in enumerate(_split(selected, 3), 1):
        ordered = sorted(names, key=lambda r: (-r["hot"], r["code"]))
        groups = _split(ordered, 5)
        qualified = len(names) >= min_names
        allocations = {}
        if qualified:
            g5n = len(groups[4])
            allocations = {f"G{i}": {r["code"]: 1/len(group) for r in group}
                           for i, group in enumerate(groups, 1)}
            lowvol = sorted(names, key=lambda r: (r["vol60"], r["code"]))[:g5n]
            allocations["lowvol"] = {r["code"]: 1/g5n for r in lowvol}
            allocations["pool"] = {r["code"]: 1/len(names) for r in names}
            halves = _split(sorted(names, key=lambda r: (r["vol60"], r["code"])), 2)
            balanced = {}
            for half in halves:
                chosen = sorted(half, key=lambda r: (r["hot"], r["code"]))[:max(1, len(half)//5)]
                for item in chosen:
                    balanced[item["code"]] = len(half)/len(names)/len(chosen)
            allocations["rev_volbalanced"] = balanced
            if len(allocations) != 8 or abs(sum(balanced.values())-1) > 1e-10:
                raise ArithmeticError("incomplete portfolio allocations")
        strata.append({"stratum": index, "qualified": qualified, "n": len(names),
                       "amount_min": names[0]["amount60"] if names else None,
                       "amount_max": names[-1]["amount60"] if names else None,
                       "codes": [r["code"] for r in names],
                       "groups": {f"G{i}": [r["code"] for r in group]
                                  for i, group in enumerate(groups, 1)},
                       "weights": allocations})
    return {"month_end": month_end, "eligible_n": len(selected),
            "features": selected, "rejected": rejected, "strata": strata}


def open_market_row(adapted, calendar, day, price_identity, close_by_day=None,
                    calendar_index=None, break_dates=None, prior_source_day=None):
    """Extract opening fields separately from the adapter's close audit.

    The previous raw close is a prior-day observation. Current close, H/L,
    volume and source_valid are never consulted for opening qualification.
    """
    raw = adapted.get("raw_by_day", {}).get(day)
    factors = adapted.get("factor_by_day", {})
    index = calendar_index if calendar_index is not None else {d: i for i, d in enumerate(calendar)}
    breaks = break_dates if break_dates is not None else set(adapted.get("break_dates", []))
    out = {"open_valid": False, "open_basis_break": False,
           "close_valid": False, "close_basis_break": day in breaks}
    if day not in index or not isinstance(raw, dict):
        # No raw row is an unknown mark, not evidence of a broken price basis.
        out["close_basis_break"] = False
        out["open_reason"] = "raw_day_missing"
        return out
    factor_pair = factors.get(day)
    prior_day = (prior_source_day.get(day) if prior_source_day is not None else
                 next((d for d in reversed(calendar[:index[day]])
                       if isinstance(adapted.get("raw_by_day", {}).get(d), dict)), None))
    prior_raw = adapted.get("raw_by_day", {}).get(prior_day)
    prior_pair = factors.get(prior_day)
    out["tradestatus_open"] = raw.get("tradestatus")
    out["isST_open"] = raw.get("isST")
    try:
        if raw.get("adjustflag") != "3" or not factor_pair:
            raise ValueError("raw_or_factor_invalid")
        if not prior_pair or not prior_raw:
            raise ValueError("continuity_unverified")
        if prior_raw.get("adjustflag") != "3":
            raise ValueError("prior_raw_flag_invalid")
        if raw.get("tradestatus") not in ("0", "1"):
            raise ValueError("status_invalid")
        if raw["tradestatus"] == "0":
            raise ValueError("no_trade")
        if positive(raw.get("preclose")) is None:
            raise ValueError("continuity_unverified")
        if positive(prior_raw.get("close")) is None:
            raise ValueError("continuity_unverified")
        current_factor, event = factor_pair
        prior_factor, prior_event = prior_pair
        if positive(current_factor) is None or positive(prior_factor) is None:
            raise ValueError("continuity_unverified")
        identity = price_identity(prior_raw["close"], prior_factor, raw["preclose"], current_factor,
                                  same_effective_factor=prior_event == event)
        if not identity["intervals_overlap"]:
            raise ValueError("adjusted_preclose_break")
        if positive(raw.get("open")) is None:
            raise ValueError("no_open_quote")
        out["open"] = float(Decimal(raw["open"]) * Decimal(current_factor))
        out["open_valid"] = True
    except (ValueError, InvalidOperation, TypeError, KeyError) as exc:
        out["open_basis_break"] = str(exc) not in {
            "no_trade", "no_open_quote", "continuity_unverified"}
        out["open_reason"] = str(exc)
        out["close_basis_break"] |= out["open_basis_break"]
    failures = adapted.get("failures", {}).get(day, [])
    if not out["open_basis_break"] and failures and set(failures) <= UNCERTAIN_CLOSE_REASONS:
        # The full-bar auditor flags gaps and missing numerical fields, but
        # these alone do not prove a permanent basis discontinuity. Never use
        # the same-day close audit to turn an invalid open into a valid order.
        out["close_basis_break"] = False
        out["close_unknown_reason"] = "source_uncertain"
    if out.get("open_reason") in {"no_trade", "no_open_quote", "continuity_unverified"}:
        out["close_unknown_reason"] = out.get("close_unknown_reason") or out["open_reason"]
    # The close audit is attached only for the end-of-day pass.
    close_row = ((close_by_day or {}).get(day) if close_by_day is not None else
                 next((r for r in adapted.get("rows", []) if r.get("date") == day), None))
    if close_row and not out["close_basis_break"] and not out.get("close_unknown_reason"):
        out["close"] = positive(close_row.get("close"))
        out["close_valid"] = out["close"] is not None and close_row.get("tradestatus") == "1"
    return out


def simulate_open(calendar, market, targets, cost_bps=25, initial_cash=100000,
                  start_date="2015-01-01", end_date="2025-12-31"):
    """Run one account; close breaks cannot retroactively change opening orders."""
    dates = list(calendar)
    if dates != sorted(set(dates)) or not dates:
        raise ValueError("calendar must be sorted and unique")
    if not isfinite(float(initial_cash)) or initial_cash <= 0 or cost_bps not in (0, 25):
        raise ValueError("invalid cash or fee")
    decisions = {}
    for before, after in zip(dates, dates[1:]):
        if before[:7] != after[:7] and start_date <= after <= end_date:
            if before not in targets:
                raise ValueError(f"missing decision:{before}")
            item = targets[before]
            if type(item.get("qualified")) is not bool or not isinstance(item.get("weights"), dict):
                raise ValueError("invalid target")
            weights = item["weights"]
            if (not item["qualified"] and weights) or (item["qualified"] and not weights):
                raise ValueError("target qualification mismatch")
            if abs(sum(weights.values()) - (1 if item["qualified"] else 0)) > 1e-9:
                raise ValueError("target weights do not sum to one")
            decisions[after] = before
    cash = float(initial_cash)
    rate = cost_bps / 10000
    holdings, daily, orders, trades, month_end_holdings = {}, [], [], [], []
    fees = 0.0
    def quote(code, date):
        return market.get(code, {}).get(date, {})
    def reason(row, side):
        if row.get("open_basis_break") is True:
            return "open_basis_break"
        if row.get("open_valid") is not True or positive(row.get("open")) is None:
            return row.get("open_reason", "open_invalid")
        if str(row.get("tradestatus_open")) != "1":
            return "not_trading"
        if side == "buy" and str(row.get("isST_open")) != "0":
            return "st_buy_blocked"
        return None
    for i, date in enumerate(dates):
        if not start_date <= date <= end_date:
            continue
        opening_marks = {}
        for code, pos in holdings.items():
            r = quote(code, date)
            current_open = (positive(r.get("open")) if not pos["broken"]
                            and reason(r, "sell") is None else None)
            if current_open is not None:
                # Mark every held position before deciding whether to trade.
                # If the later close is unavailable, this opening mark remains
                # the last known value regardless of rebalance activity.
                pos["mark"], pos["mark_date"] = current_open, date
            opening_marks[code] = current_open or pos["mark"]
        nav_before = cash + sum(pos["units"]*opening_marks[code] for code, pos in holdings.items())
        gross_today = blocked_sell_today = 0.0
        decision = decisions.get(date)
        if decision:
            weights = targets[decision]["weights"]
            sells, buys = [], []
            for code in sorted(set(holdings) | set(weights)):
                old = holdings.get(code)
                current = old["units"]*opening_marks[code] if old else 0.0
                delta = nav_before*weights.get(code, 0.0)-current
                if delta < -1e-8:
                    sells.append((code, -delta))
                elif delta > 1e-8:
                    buys.append((code, delta))
            for code, intent in sells:
                pos, r = holdings[code], quote(code, date)
                why = "prior_basis_break" if pos["broken"] else reason(r, "sell")
                price = positive(r.get("open"))
                qty = None if price is None else min(intent/price, pos["units"])
                gross = intent if qty is None else qty*price
                fee = gross*rate if why is None else 0.0
                order = {"date": date, "decision_date": decision, "code": code, "side": "sell",
                         "qty": qty, "gross": gross, "fee": fee,
                         "status": "filled" if why is None else "blocked", "reason": why}
                orders.append(order)
                if why:
                    blocked_sell_today += intent
                    continue
                pos["units"] -= qty
                pos["mark"], pos["mark_date"] = price, date
                cash += gross-fee
                fees += fee
                gross_today += gross
                trades.append({**order, "cash_after": cash, "units_after": max(0, pos["units"])})
                if pos["units"] <= 1e-8:
                    del holdings[code]
            total = sum(g for _, g in buys)
            scale = min(1.0, cash/((1+rate)*total)) if total else 1.0
            for code, intent in buys:
                gross = intent*scale
                r = quote(code, date)
                pos = holdings.get(code)
                why = "prior_basis_break" if pos and pos["broken"] else reason(r, "buy")
                if gross <= 1e-8:
                    why = "insufficient_cash"
                price = positive(r.get("open"))
                qty = gross/price if price else None
                fee = gross*rate if why is None else 0.0
                order = {"date": date, "decision_date": decision, "code": code, "side": "buy",
                         "qty": qty, "gross": gross, "fee": fee,
                         "status": "filled" if why is None else "blocked", "reason": why}
                orders.append(order)
                if why:
                    continue
                cash -= gross+fee
                if cash < -1e-7:
                    raise ArithmeticError("buy exceeded cash")
                cash = max(0.0, cash)
                fees += fee
                gross_today += gross
                if pos:
                    pos["units"] += qty
                    pos["mark"], pos["mark_date"] = price, date
                else:
                    holdings[code] = {"units": qty, "mark": price,
                                      "mark_date": date, "broken": False}
                trades.append({**order, "cash_after": cash, "units_after": holdings[code]["units"]})
        market_value = unknown_value = 0.0
        stale = broken = 0
        for code, pos in holdings.items():
            r = quote(code, date)
            if r.get("close_basis_break") is True:
                pos["broken"] = True
            close = (positive(r.get("close")) if not pos["broken"] and r.get("close_valid") is True
                     and str(r.get("tradestatus_open")) == "1" else None)
            if close is None:
                stale += 1
                pos["stale_today"] = True
                unknown_value += pos["units"]*pos["mark"]
            else:
                pos["mark"], pos["mark_date"], pos["stale_today"] = close, date, False
            broken += pos["broken"]
            market_value += pos["units"]*pos["mark"]
        nav = cash+market_value
        if not all(isfinite(x) for x in (cash, nav, fees, unknown_value)) or nav <= 0:
            raise ArithmeticError("invalid account value")
        actual = {c: p["units"]*p["mark"]/nav for c,p in holdings.items()}
        wanted = targets[decision]["weights"] if decision else None
        daily.append({"date": date, "nav_quote_proxy": nav, "nav_before_trade": nav_before,
                      "cash": cash, "market_value": market_value, "cash_fraction": cash/nav,
                      "unknown_value": unknown_value, "unknown_fraction": unknown_value/nav,
                      "stress_zero_unknown_nav": nav-unknown_value,
                      "fees_cumulative": fees, "gross_traded_today": gross_today,
                      "held_count": len(holdings), "stale_count": stale,
                      "basis_broken_count": broken, "blocked_sell_gross_today": blocked_sell_today,
                      "close_target_deviation": sum(abs(actual.get(c,0)-wanted.get(c,0))
                                                    for c in set(actual)|set(wanted)) if wanted is not None else None})
        if i == len(dates)-1 or dates[i+1][:7] != date[:7]:
            for code, pos in sorted(holdings.items()):
                month_end_holdings.append({"date": date, "code": code, **pos,
                                           "lastknownweight": pos["units"]*pos["mark"]/nav})
    return {"daily": daily, "orders": orders, "trades": trades,
            "month_end_holdings": month_end_holdings}
