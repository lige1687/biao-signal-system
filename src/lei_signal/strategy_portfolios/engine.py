"""Deterministic, fractional-share research account for stock factor portfolios.

All prices must be in the same adjusted research quote unit. This is a
``quote_account_proxy``: fractional units and next-open fills are research
assumptions, not evidence of executable stock trades.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date as Date
import math
from statistics import stdev


SCHEMES = {"mv", "rv", "m", "v", "r", "equal"}
EPS = 1e-10


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _month_shift(day: str, months: int) -> tuple[int, int]:
    parsed = Date.fromisoformat(str(day)[:10])
    index = parsed.year * 12 + parsed.month - 1 + months
    return index // 12, index % 12 + 1


def _normalise(bars, calendar=None):
    by_date = defaultdict(dict)
    for raw in bars:
        day = str(raw["date"])[:10]
        symbol = str(raw["symbol"])
        if symbol in by_date[day]:
            raise ValueError(f"duplicate bar: {day} {symbol}")
        by_date[day][symbol] = raw
    if calendar is None:
        days = sorted(by_date)
    else:
        days = [str(day)[:10] for day in calendar]
        if len(days) != len(set(days)):
            raise ValueError("duplicate calendar date")
        days.sort()
    day_set = set(days)
    if any(day not in day_set for day in by_date):
        raise ValueError("bar date outside supplied calendar")
    return by_date, days


def build_feature_panel(bars: list[dict], calendar=None) -> list[dict]:
    """Compute point-in-time features on a shared market calendar.

    A symbol needs 253 consecutive calendar closes (including today). Invalid
    or missing closes break the run; no signal is forward-filled. Month-end
    reference prices are the last valid close *on* that market month-end, not
    a later replacement for a missing close.
    """
    by_date, days = _normalise(bars, calendar)
    if not days:
        return []
    # The terminal date may be a truncated data delivery, not a true month end.
    month_ends = {day for i, day in enumerate(days[:-1]) if day[:7] != days[i + 1][:7]}
    monthly_close: dict[str, dict[tuple[int, int], float]] = defaultdict(dict)
    recent: dict[str, list[float]] = defaultdict(list)
    result = []
    for day in days:
        for symbol, bar in sorted(by_date.get(day, {}).items()):
            close = _number(bar.get("close"))
            good_close = bool(bar.get("valid", True)) and close is not None and close > 0
            history = recent[symbol]
            # Missing calendar observations are handled below for all symbols.
            if good_close:
                history.append(close)
            else:
                history.clear()
            if day in month_ends and good_close:
                monthly_close[symbol][_month_shift(day, 0)] = close
            prev = monthly_close[symbol].get(_month_shift(day, -1))
            year_ago = monthly_close[symbol].get(_month_shift(day, -12))
            momentum = prev / year_ago - 1 if prev and year_ago else None
            recent_return = close / prev - 1 if good_close and prev else None
            volatility = None
            if len(history) >= 61:
                returns = [math.log(history[-i] / history[-i - 1]) for i in range(1, 61)]
                volatility = stdev(returns)
            sma120 = sum(history[-120:]) / 120 if len(history) >= 120 else None
            volume = _number(bar.get("volume"))
            eligible = bool(
                good_close and len(history) >= 253 and momentum is not None
                and recent_return is not None and volatility is not None
                and volume is not None and volume > 0 and bar.get("tradable") is not False
                and bar.get("eligible_buy") is not False
                and close > sma120
            )
            result.append({"date": day, "symbol": symbol, "momentum": momentum,
                           "recent_return": recent_return, "volatility": volatility,
                           "sma120": sma120, "close": close if good_close else None,
                           "eligible": eligible})
        # A missing row on a shared calendar invalidates consecutive history.
        present = by_date.get(day, {})
        for symbol in recent.keys() - present.keys():
            recent[symbol].clear()
    return result


def _percentile(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    out = {}
    start = 0
    while start < count:
        stop = start + 1
        while stop < count and ordered[stop][1] == ordered[start][1]:
            stop += 1
        # Midrank percentile, with one-name universe assigned 1.
        rank = ((start + stop - 1) / 2) / (count - 1) if count > 1 else 1.0
        for symbol, _ in ordered[start:stop]:
            out[symbol] = rank
        start = stop
    return out


def select_targets(features: list[dict], scheme: str, slots: int = 20) -> list[dict]:
    """Select one decision-date cross-section; tied scores use symbol order."""
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme: {scheme}")
    if slots <= 0:
        raise ValueError("slots must be positive")
    candidates = {row["symbol"]: row for row in features if row.get("eligible")}
    if len(candidates) != sum(bool(row.get("eligible")) for row in features):
        raise ValueError("duplicate eligible symbol")
    if not candidates:
        return []
    scores = {
        "m": _percentile({s: row["momentum"] for s, row in candidates.items()}),
        "v": _percentile({s: -row["volatility"] for s, row in candidates.items()}),
        "r": _percentile({s: -row["recent_return"] for s, row in candidates.items()}),
    }
    def score(symbol):
        if scheme == "mv":
            return (scores["m"][symbol] + scores["v"][symbol]) / 2
        if scheme == "rv":
            return (scores["r"][symbol] + scores["v"][symbol]) / 2
        if scheme == "equal":
            return 1.0
        return scores[scheme][symbol]
    chosen = sorted(candidates, key=lambda s: (-score(s), s))
    if scheme != "equal":
        chosen = chosen[:slots]
    weight = 1 / len(chosen) if scheme == "equal" else 1 / slots
    return [{"symbol": symbol, "rank": rank, "score": score(symbol),
             "target_weight": weight, "reference_price": candidates[symbol]["close"],
             "factors": {"momentum": candidates[symbol]["momentum"],
                         "recent_return": candidates[symbol]["recent_return"],
                         "volatility": candidates[symbol]["volatility"]},
             "factor_ranks": {key: scores[key][symbol] for key in ("m", "v", "r")}}
            for rank, symbol in enumerate(chosen, 1)]


def backtest(bars: list[dict], scheme: str, start: str, end: str, cost_bps: float,
             initial_cash: float = 100000, slots: int = 20, trend_exit: bool = True,
             calendar=None, feature_panel: list[dict] | None = None) -> dict:
    """Run a next-open quote account without borrowing or same-open sizing.

    Pass a panel built once with ``build_feature_panel(bars, calendar)`` to
    reuse features across independent schemes. Decisions freeze quantities
    using that day's close. Unfilled buy orders
    expire after the next opening. Failed sells remain actual holdings and are
    retried at subsequent closes while liquidation is required. An opening
    fill requires a positive open and any explicit opening status; full-day
    close, volume and validity do not gate that opening. Unknown opening
    eligibility is permitted as a quote proxy. Historical source status can overstate
    real executability; fills are research quotes, not actual executions.
    """
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme: {scheme}")
    if not isinstance(trend_exit, bool):
        raise ValueError("trend_exit must be boolean")
    fee_bps = _number(cost_bps)
    cash = _number(initial_cash)
    if fee_bps is None or fee_bps < 0 or cash is None or cash <= 0:
        raise ValueError("fees must be nonnegative and initial_cash positive")
    if slots <= 0 or start > end:
        raise ValueError("invalid slots or date range")
    fee_rate = fee_bps / 10000
    by_date, all_days = _normalise(bars, calendar)
    panel = feature_panel if feature_panel is not None else build_feature_panel(bars, all_days)
    features_by_date = defaultdict(dict)
    for row in panel:
        if start <= row["date"] <= end:
            features_by_date[row["date"]][row["symbol"]] = row
    days = [day for day in all_days if start <= day <= end]
    month_ends = {day for i, day in enumerate(all_days[:-1]) if day[:7] != all_days[i + 1][:7]}
    positions: dict[str, float] = {}
    last_price: dict[str, float] = {}
    pending = []
    target_symbols: set[str] = set()
    forced_exit: set[str] = set()
    daily, decisions, trades = [], [], []
    total_cost = 0.0
    first_decision = False
    running_peak = initial_cash

    def value(day):
        nonlocal cash
        stale = 0.0
        invested = 0.0
        for symbol, quantity in positions.items():
            bar = by_date.get(day, {}).get(symbol)
            close = _number(bar.get("close")) if bar and bar.get("valid", True) else None
            if close is not None and close > 0:
                last_price[symbol] = close
            else:
                stale += quantity * last_price[symbol]
            invested += quantity * last_price[symbol]
        equity = cash + invested
        return equity, invested, stale

    for day in days:
        # Orders live for precisely one opening; sells precede buys.
        for order in sorted(pending, key=lambda item: (item["side"] != "sell", item["symbol"])):
            symbol, side, wanted = order["symbol"], order["side"], order["quantity"]
            bar = by_date.get(day, {}).get(symbol)
            opening = _number(bar.get("open")) if bar else None
            executable = bool(bar and bar.get("open_tradable") is not False
                              and opening is not None and opening > 0)
            filled = 0.0
            reason = None
            if not executable:
                reason = "not_tradable_or_missing_open"
            elif side == "buy" and bar.get("open_buy_allowed") is False:
                reason = "not_buy_eligible_at_open"
            elif side == "sell":
                filled = min(wanted, positions.get(symbol, 0.0))
                if filled > EPS:
                    proceeds = filled * opening
                    fee = proceeds * fee_rate
                    cash += proceeds - fee
                    total_cost += fee
                    positions[symbol] -= filled
                    if positions[symbol] <= EPS:
                        del positions[symbol]
                    last_price[symbol] = opening
            else:
                affordable = cash / (opening * (1 + fee_rate))
                filled = min(wanted, max(0.0, affordable))
                if filled > EPS:
                    gross = filled * opening
                    fee = gross * fee_rate
                    cash -= gross + fee
                    total_cost += fee
                    positions[symbol] = positions.get(symbol, 0.0) + filled
                    last_price[symbol] = opening
                if filled + EPS < wanted:
                    reason = "gap_cash_shortfall" if filled > EPS else "insufficient_cash"
            if filled > EPS or reason:
                trades.append({"date": day, "decision_date": order["decision_date"],
                               "symbol": symbol, "side": side, "reason": order["reason"],
                               "requested_quantity": wanted, "quantity": filled,
                               "price": opening if executable else None,
                               "cost": filled * opening * fee_rate if executable else 0.0,
                               "unfilled_reason": reason})
        pending = []
        equity, invested, stale = value(day)
        running_peak = max(running_peak, equity)
        previous = daily[-1]["equity"] if daily else initial_cash
        daily.append({"date": day, "equity": equity, "cash": cash,
                      "drawdown": equity / running_peak - 1, "exposure": invested / equity,
                      "unknown_weight": stale / equity, "holdings_count": len(positions),
                      "return": equity / previous - 1})
        features = features_by_date[day]
        month_end = day in month_ends
        if month_end:
            first_decision = True
            targets = select_targets(list(features.values()), scheme, slots)
            target_symbols = {target["symbol"] for target in targets}
            # A later month-end may readmit a recovered name; intra-month
            # failed exits stay committed until a sale is possible.
            forced_exit.difference_update(target_symbols)
        elif not first_decision:
            continue
        else:
            targets = []
        orders = {}
        exits = set()
        for symbol, quantity in positions.items():
            row = features.get(symbol)
            close = row["close"] if row else None
            sma = row["sma120"] if row else None
            if trend_exit and close is not None and sma is not None and close < sma:
                forced_exit.add(symbol)
            if symbol in forced_exit or symbol not in target_symbols:
                exits.add(symbol)
            if symbol in exits:
                orders[symbol] = {"side": "sell", "quantity": quantity, "reason": "trend_exit" if symbol in target_symbols else "monthly_exit"}
            elif close is not None and close > 0 and quantity * close > .10 * equity:
                excess = quantity - (.05 * equity / close)
                orders[symbol] = {"side": "sell", "quantity": excess, "reason": "concentration_cap"}
        if month_end:
            for target in targets:
                symbol = target["symbol"]
                if symbol in exits:
                    continue
                price = target["reference_price"]
                current = positions.get(symbol, 0.0)
                desired = target["target_weight"] * equity / price
                delta = desired - current
                if delta < -EPS:
                    orders[symbol] = {"side": "sell", "quantity": -delta, "reason": "monthly_rebalance"}
                elif delta > EPS and symbol not in orders:
                    orders[symbol] = {"side": "buy", "quantity": delta, "reason": "monthly_rebalance"}
            decisions.append({"date": day, "scheme": scheme, "targets": targets,
                              "equity": equity, "orders": [dict(symbol=s, **o) for s, o in sorted(orders.items())]})
        pending = [dict(symbol=s, decision_date=day, **order) for s, order in sorted(orders.items())]
    final_equity = daily[-1]["equity"] if daily else initial_cash
    recovery = longest = 0
    high = initial_cash
    for row in daily:
        if row["equity"] >= high - EPS:
            high = max(high, row["equity"])
            recovery = 0
        else:
            recovery += 1
            longest = max(longest, recovery)
    summary = {"account_type": "quote_account_proxy", "scheme": scheme,
               "cumulative_return": final_equity / initial_cash - 1,
               "max_drawdown": min((row["drawdown"] for row in daily), default=0.0),
               "trade_count": sum(row["quantity"] > EPS for row in trades),
               "cost": total_cost,
               "average_exposure": sum(row["exposure"] for row in daily) / len(daily) if daily else 0.0,
               "longest_recovery_days": longest,
               "max_stale_weight": max((row["unknown_weight"] for row in daily), default=0.0),
               "fractional_research_units": True,
               "price_basis": "same_adjusted_research_quote_unit"}
    return {"summary": summary, "daily": daily, "decisions": decisions, "trades": trades}
