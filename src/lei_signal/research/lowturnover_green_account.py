"""Continuous, virtual-share research account for monthly green-stock rankings.

All signals are read at month-end close. Adjusted quote units make this a price
proxy: no real shares, dividend cash, delisting proceeds, or fill confirmation.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from lei_signal.research.fip import month_add

SCHEMES = {"momentum", "cool", "lowvol"}


def _number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _truth(value):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    return None


def _source(row):
    return isinstance(row, dict) and _truth(row.get("source_valid")) is True


def _mark(row):
    value = (
        _number(row.get("close"))
        if _source(row)
        and str(row.get("tradestatus")) == "1"
        and (_number(row.get("volume")) or 0) > 0
        else None
    )
    return value if value is not None and value > 0 else None


def _fill_reason(row, side, conservative_fill):
    if not _source(row):
        return "source_invalid_or_missing"
    if str(row.get("tradestatus")) != "1":
        return "not_trading"
    if side == "buy" and str(row.get("isST")) != "0":
        return "st_restricted"
    volume, op = _number(row.get("volume")), _number(row.get("open"))
    if volume is None or volume <= 0:
        return "nonpositive_volume"
    if op is None or op <= 0:
        return "invalid_open"
    if conservative_fill:
        high, low, pre = (_number(row.get(key)) for key in ("high", "low", "preclose"))
        if high is None or low is None or pre is None or pre <= 0 or high < low:
            return "limit_quote_unknown"
        if math.isclose(high, low, rel_tol=0, abs_tol=1e-10):
            if side == "buy" and op > pre:
                return "one_price_adverse_buy"
            if side == "sell" and op < pre:
                return "one_price_adverse_sell"
    return ""


def _ranked_pool(rows, market, day, scheme):
    """Frozen common top 30% momentum pool; rank each scheme within it."""
    good = []
    for row in rows:
        code = row["code"]
        quote = market.get(code, {}).get(day)
        if (
            row.get("decision_date") == day
            and _truth(row.get("eligible")) is True
            and _truth(row.get("green")) is True
            and _source(quote)
            and str(quote.get("isST")) == "0"
            and all(_number(row.get(k)) is not None for k in ("momentum", "hot", "vol60"))
        ):
            good.append(row)
    if len({row["code"] for row in good}) != len(good):
        raise ValueError("duplicate eligible code on decision day")
    n_pool = math.ceil(len(good) * 0.30)
    common = sorted(good, key=lambda r: (-float(r["momentum"]), r["code"]))[:n_pool]
    if scheme == "momentum":
        ranked = sorted(common, key=lambda r: (-float(r["momentum"]), r["code"]))
    elif scheme == "cool":
        ranked = sorted(common, key=lambda r: (float(r["hot"]), r["code"]))
    else:
        ranked = sorted(common, key=lambda r: (float(r["vol60"]), r["code"]))
    return [row["code"] for row in ranked], len(good)


def simulate(
    calendar,
    market,
    features,
    scheme="momentum",
    buffer_rank=20,
    cost_bps=25,
    initial_cash=100000,
    slots=10,
    first_month="2014-12",
    last_month="2025-11",
    conservative_fill=True,
):
    """Run one fixed scheme/buffer/cost arm without consulting future outcomes.

    A failed T+1 sale remains pending; later sale proceeds wait for next month.
    A filled T+1 sale may buy a frozen T-ranked replacement at T+2 only.
    Buy orders try once. Daily NAV uses last valid research close when stale,
    with the unknown exposure shown beside the quote-proxy value.
    """
    dates = list(calendar)
    if dates != sorted(set(dates)) or not dates:
        raise ValueError("calendar must be nonempty, sorted and unique")
    if scheme not in SCHEMES or buffer_rank not in (10, 20) or slots != 10:
        raise ValueError("unsupported frozen arm")
    fee = _number(cost_bps)
    capital = _number(initial_cash)
    if fee is None or fee < 0 or capital is None or capital <= 0:
        raise ValueError("invalid fee or initial cash")
    fee /= 10000
    if first_month > last_month:
        raise ValueError("invalid month range")
    month_ends = {day[:7]: day for day in dates}
    positions = {day: i for i, day in enumerate(dates)}
    selected_months = []
    month = first_month
    while month <= last_month:
        if month not in month_ends:
            raise ValueError(f"decision month absent from calendar: {month}")
        selected_months.append(month)
        month = month_add(month, 1)
    first_decision = month_ends[first_month]
    if month_add(last_month, 1) not in month_ends:
        raise ValueError("investment end month absent from calendar")
    last_day = month_ends[month_add(last_month, 1)]
    dates = [day for day in dates if day <= last_day]
    by_month = defaultdict(list)
    for row in features:
        if row.get("month") in selected_months:
            by_month[row["month"]].append(row)
    for m, rows in by_month.items():
        if len({row["code"] for row in rows}) != len(rows):
            raise ValueError(f"duplicate feature code: {m}")
    accounts = [
        {
            "slot": i + 1,
            "cash": capital / slots,
            "code": None,
            "units": 0.0,
            "last_mark": None,
            "mark_date": None,
            "entry_date": None,
            "pending_sell": None,
            "pending_buy": None,
            "basis_broken": False,
        }
        for i in range(slots)
    ]
    daily, transactions, decisions = [], [], []
    durations, fees_paid = [], 0.0
    latest_ranked: list[str] = []
    traded_notional = 0.0
    normalized_turnover = 0.0
    latest_scores: dict[str, tuple[float, float]] = {}
    latest_score_date = None

    for day in dates:
        day_index = positions[day]
        day_gross = 0.0
        nav_before_trade_proxy = daily[-1]["nav_quote_proxy"] if daily else capital
        for account in accounts:
            code = account["code"]
            if code and _truth((market.get(code, {}).get(day) or {}).get("basis_break")) is True:
                account["basis_broken"] = True
        # Orders only become eligible after the prior decision close.
        for account in accounts:
            code = account["code"]
            order = account["pending_sell"]
            if code is None or order is None or day < order["eligible_date"]:
                continue
            row = market.get(code, {}).get(day)
            reason = (
                "basis_broken"
                if account["basis_broken"]
                else _fill_reason(row, "sell", conservative_fill)
            )
            if reason:
                order["attempts"] += 1
                if day == order["eligible_date"]:
                    order["replacement_code"] = None  # never reuse a failed first-day slot
                transactions.append(
                    {
                        "date": day,
                        "slot": account["slot"],
                        "code": code,
                        "side": "sell",
                        "status": "blocked",
                        "reason": reason,
                        "decision_date": order["decision_date"],
                    }
                )
                continue
            gross = account["units"] * float(row["open"])
            cost = gross * fee
            account["cash"] += gross - cost
            fees_paid += cost
            traded_notional += gross
            day_gross += gross
            durations.append(
                (date.fromisoformat(day) - date.fromisoformat(account["entry_date"])).days
            )
            transactions.append(
                {
                    "date": day,
                    "slot": account["slot"],
                    "code": code,
                    "side": "sell",
                    "status": "filled",
                    "reason": "",
                    "units": account["units"],
                    "price": float(row["open"]),
                    "gross": gross,
                    "fee": cost,
                    "nav_before_trade_proxy": nav_before_trade_proxy,
                    "decision_date": order["decision_date"],
                }
            )
            replacement_code = order.get("replacement_code")
            on_first_day = day == order["eligible_date"]
            account.update(
                code=None,
                units=0.0,
                last_mark=None,
                mark_date=None,
                entry_date=None,
                pending_sell=None,
                basis_broken=False,
            )
            if on_first_day and replacement_code is not None:
                next_day = dates[day_index + 1] if day_index + 1 < len(dates) else None
                if next_day is not None:
                    account["pending_buy"] = {
                        "code": replacement_code,
                        "decision_date": order["decision_date"],
                        "eligible_date": next_day,
                        "replacement": True,
                    }
        for account in accounts:
            order = account["pending_buy"]
            if order is None or day < order["eligible_date"]:
                continue
            code = order["code"]
            row = market.get(code, {}).get(day)
            reason = _fill_reason(row, "buy", conservative_fill)
            if reason:
                transactions.append(
                    {
                        "date": day,
                        "slot": account["slot"],
                        "code": code,
                        "side": "buy",
                        "status": "blocked",
                        "reason": reason,
                        "decision_date": order["decision_date"],
                    }
                )
            elif code in {a["code"] for a in accounts if a["code"]}:
                transactions.append(
                    {
                        "date": day,
                        "slot": account["slot"],
                        "code": code,
                        "side": "buy",
                        "status": "blocked",
                        "reason": "duplicate_holding",
                        "decision_date": order["decision_date"],
                    }
                )
            else:
                op = float(row["open"])
                gross = account["cash"] / (1 + fee)
                units = gross / op
                cost = gross * fee
                account["cash"] -= gross + cost
                account.update(
                    code=code,
                    units=units,
                    entry_date=day,
                    last_mark=op,
                    mark_date=day,
                    basis_broken=False,
                )
                fees_paid += cost
                traded_notional += gross
                day_gross += gross
                transactions.append(
                    {
                        "date": day,
                        "slot": account["slot"],
                        "code": code,
                        "side": "buy",
                        "status": "filled",
                        "reason": "",
                        "units": units,
                        "price": op,
                        "gross": gross,
                        "fee": cost,
                        "nav_before_trade_proxy": nav_before_trade_proxy,
                        "decision_date": order["decision_date"],
                    }
                )
            account["pending_buy"] = None  # no retry or substitution this month
        # The T-close feature snapshot can describe today's exposure, but no
        # T-close decision may affect today's opening fills.
        month = day[:7]
        if day == month_ends.get(month) and month in selected_months:
            latest_scores = {}
            latest_score_date = day
            for feature in by_month.get(month, []):
                if feature.get("decision_date") == day and _source(
                    market.get(feature["code"], {}).get(day)
                ):
                    momentum = _number(feature.get("momentum"))
                    vol60 = _number(feature.get("vol60"))
                    if momentum is not None and vol60 is not None:
                        latest_scores[feature["code"]] = (momentum, vol60)
        total_cash = sum(a["cash"] for a in accounts)
        marked, stale_value, known_value = 0.0, 0.0, 0.0
        snapshots = []
        for account in accounts:
            code = account["code"]
            stale = False
            if code:
                quote = None if account["basis_broken"] else _mark(market.get(code, {}).get(day))
                if quote is not None:
                    account["last_mark"] = quote
                    account["mark_date"] = day
                else:
                    stale = True
                value = account["units"] * account["last_mark"]
                marked += value
                if stale:
                    stale_value += value
                else:
                    known_value += value
            else:
                value = 0.0
            snapshots.append(
                {
                    "slot": account["slot"],
                    "cash": account["cash"],
                    "code": code,
                    "units": account["units"],
                    "market_value": value,
                    "mark": account["last_mark"],
                    "mark_date": account["mark_date"],
                    "stale": stale,
                    "basis_broken": account["basis_broken"],
                    "score_date": latest_score_date
                    if code in latest_scores and not account["basis_broken"]
                    else None,
                    "pending_sell": dict(account["pending_sell"])
                    if account["pending_sell"]
                    else None,
                    "pending_buy": dict(account["pending_buy"]) if account["pending_buy"] else None,
                }
            )
        nav = total_cash + marked
        normalized_turnover += day_gross / nav_before_trade_proxy / 2
        holding_values = {a["code"]: a["units"] * a["last_mark"] for a in accounts if a["code"]}
        broken_codes = {a["code"] for a in accounts if a["code"] and a["basis_broken"]}
        feature_unknown_value = sum(
            value
            for code, value in holding_values.items()
            if code not in latest_scores or code in broken_codes
        )
        weighted_momentum = (
            sum(value * latest_scores[code][0] for code, value in holding_values.items()) / nav
            if nav > 0 and feature_unknown_value == 0
            else None
        )
        weighted_vol60 = (
            sum(value * latest_scores[code][1] for code, value in holding_values.items()) / nav
            if nav > 0 and feature_unknown_value == 0
            else None
        )
        holding_momentum = (
            weighted_momentum * nav / marked
            if marked > 0 and weighted_momentum is not None
            else None
        )
        holding_vol60 = (
            weighted_vol60 * nav / marked if marked > 0 and weighted_vol60 is not None else None
        )
        daily.append(
            {
                "date": day,
                "score_date": latest_score_date,
                "nav_quote_proxy": nav,
                "cash": total_cash,
                "market_value": marked,
                "known_market_value": known_value,
                "stale_market_value": stale_value,
                "invested_fraction": marked / nav if nav > 0 else None,
                "traded_exposure": known_value / nav if nav > 0 else None,
                "unknown_exposure": stale_value / nav if nav > 0 else None,
                "stress_zero_stale_nav": total_cash + known_value,
                "weighted_momentum_exposure": weighted_momentum,
                "weighted_vol60_exposure": weighted_vol60,
                "holding_momentum_exposure": holding_momentum,
                "holding_vol60_exposure": holding_vol60,
                "unknown_feature_weight": feature_unknown_value / nav if nav > 0 else None,
                "max_single_stock_weight": max(holding_values.values(), default=0.0) / nav
                if nav > 0
                else None,
                "stock_hhi": sum((value / nav) ** 2 for value in holding_values.values())
                if nav > 0
                else None,
                "stale_slots": sum(s["stale"] for s in snapshots),
                "basis_broken_slots": sum(s["basis_broken"] for s in snapshots),
                "fees_cumulative": fees_paid,
                "filled_gross_today": day_gross,
                "nav_before_trade_proxy": nav_before_trade_proxy,
                "slots": snapshots,
            }
        )
        if day != month_ends.get(month) or month not in selected_months:
            continue
        rows = by_month.get(month, [])
        latest_ranked, eligible_count = _ranked_pool(rows, market, day, scheme)
        ranks = {code: i + 1 for i, code in enumerate(latest_ranked)}
        held_before = [a["code"] for a in accounts if a["code"]]
        unknown, retained, sell_planned, canceled, known_not_candidate = [], [], [], [], []
        next_day = dates[day_index + 1] if day_index + 1 < len(dates) else None
        for account in accounts:
            code = account["code"]
            if code is None:
                account["pending_buy"] = None
                continue
            f = next((r for r in rows if r["code"] == code), None)
            quote = market.get(code, {}).get(day)
            green = _truth(f.get("green")) if f else None
            metrics_known = bool(
                f and all(_number(f.get(k)) is not None for k in ("momentum", "hot", "vol60"))
            )
            known = (
                not account["basis_broken"]
                and _source(quote)
                and (
                    str(quote.get("isST")) == "1"
                    or (green is False)
                    or (green is True and _truth(f.get("eligible")) is True and metrics_known)
                )
            )
            if not known:
                unknown.append(code)
                continue  # do not invent a known non-green exit or cancel old sale
            if str(quote.get("isST")) == "1":
                known_not_candidate.append(code)
            if code in ranks and ranks[code] <= buffer_rank:
                if account["pending_sell"]:
                    canceled.append(code)
                account["pending_sell"] = None
                retained.append(code)
            else:
                if next_day is not None:
                    account["pending_sell"] = {
                        "decision_date": day,
                        "eligible_date": next_day,
                        "attempts": 0,
                        "replacement_code": None,
                    }
                sell_planned.append(code)
        # Freeze every candidate assignment at T close. Failed buys and sales
        # cannot give their reserved name to another slot later this month.
        reserved = {a["code"] for a in accounts if a["code"]}

        def next_candidate(ranked=latest_ranked, booked=reserved):
            for candidate in ranked:
                if candidate not in booked:
                    booked.add(candidate)
                    return candidate
            return None

        for account in accounts:
            if account["code"] is None and account["pending_buy"] is None:
                candidate = next_candidate()
                if candidate is not None and next_day is not None:
                    account["pending_buy"] = {
                        "code": candidate,
                        "decision_date": day,
                        "eligible_date": next_day,
                        "replacement": False,
                    }
        for account in accounts:
            order = account["pending_sell"]
            if order is not None and order["decision_date"] == day:
                order["replacement_code"] = next_candidate()
        decisions.append(
            {
                "month": month,
                "date": day,
                "scheme": scheme,
                "eligible_n": eligible_count,
                "pool_n": len(latest_ranked),
                "ranked": list(latest_ranked),
                "ranks": ranks,
                "held_before": held_before,
                "unknown_held": unknown,
                "known_not_candidate": known_not_candidate,
                "retained": retained,
                "sell_planned": sell_planned,
                "canceled_pending_sells": canceled,
                "planned_buys": [
                    {"slot": a["slot"], **a["pending_buy"]} for a in accounts if a["pending_buy"]
                ],
                "planned_replacements": [
                    {
                        "slot": a["slot"],
                        "sell_code": a["code"],
                        "replacement_code": a["pending_sell"]["replacement_code"],
                    }
                    for a in accounts
                    if a["pending_sell"] and a["pending_sell"]["decision_date"] == day
                ],
            }
        )
    # Exactly one investment month follows each month-end decision.
    daily_by_date = {row["date"]: row for row in daily}
    monthly = []
    previous_nav = capital
    for decision_month in selected_months:
        investment_month = month_add(decision_month, 1)
        end = month_ends[investment_month]
        row = daily_by_date[end]
        nav = row["nav_quote_proxy"]
        monthly.append(
            {
                "month": investment_month,
                "decision_month": decision_month,
                "date": end,
                "nav_quote_proxy": nav,
                "return_quote_proxy": nav / previous_nav - 1,
                "cash": row["cash"],
                "invested_fraction": row["invested_fraction"],
                "unknown_exposure": row["unknown_exposure"],
                "stale_slots": row["stale_slots"],
            }
        )
        previous_nav = nav
    active = [row for row in daily if first_decision <= row["date"] <= last_day]
    peak = capital
    worst = 0.0
    for row in active:
        peak = max(peak, row["nav_quote_proxy"])
        worst = min(worst, row["nav_quote_proxy"] / peak - 1)
    years = (date.fromisoformat(last_day) - date.fromisoformat(first_decision)).days / 365.2425
    final = daily_by_date[last_day]["nav_quote_proxy"]
    stress_final = daily_by_date[last_day]["stress_zero_stale_nav"]
    open_durations = [
        (date.fromisoformat(last_day) - date.fromisoformat(a["entry_date"])).days
        for a in accounts
        if a["code"]
    ]
    filled = [r for r in transactions if r["status"] == "filled"]
    summary = {
        "scheme": scheme,
        "buffer_rank": buffer_rank,
        "cost_bps": cost_bps,
        "initial_cash": capital,
        "final_nav_quote_proxy": final,
        "total_return": final / capital - 1,
        "stress_zero_stale_final": stress_final,
        "stress_zero_stale_total_return": stress_final / capital - 1,
        "cagr": (final / capital) ** (1 / years) - 1 if years > 0 else None,
        "max_drawdown": worst,
        "invested_fraction": sum(r["invested_fraction"] for r in active) / len(active),
        "traded_exposure": sum(r["traded_exposure"] for r in active) / len(active),
        "unknown_exposure": sum(r["unknown_exposure"] for r in active) / len(active),
        "stale_exposure_days": sum(r["stale_slots"] > 0 for r in active),
        "basis_broken_exposure_days": sum(r["basis_broken_slots"] > 0 for r in active),
        "turnover_oneway": normalized_turnover,
        "turnover_definition": "sum each date filled gross / prior daily quote-proxy NAV / 2",
        "traded_notional_over_2initial": traded_notional / (2 * capital),
        "transaction_count": len(filled),
        "blocked_attempts": len(transactions) - len(filled),
        "holding_duration": {
            "closed_mean_days": sum(durations) / len(durations) if durations else None,
            "closed_count": len(durations),
            "open_days": open_durations,
        },
        "fees_paid": fees_paid,
        "open_positions": sum(a["code"] is not None for a in accounts),
        "pending_sells_end": sum(a["pending_sell"] is not None for a in accounts),
        "nav_basis": "adjusted_quote_proxy_with_stale_carry_not_real_wealth",
        "stress_basis": "stale_holdings_marked_zero_diagnostic_not_real_wealth",
        "fill_basis": "restricted_quote_proxy_not_executable_lower_bound",
    }
    return {
        "daily": daily,
        "transactions": transactions,
        "monthly": monthly,
        "decisions": decisions,
        "summary": summary,
    }
