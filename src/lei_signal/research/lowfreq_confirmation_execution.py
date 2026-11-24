"""Frozen, price-only daily-close confirmation policy comparison.

This is a research policy calculation, not an implementation of original A or
an assertion that a quoted next open could have been filled.
"""

from __future__ import annotations

import math
from typing import Any


def _positive(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _hour_state(hours: dict[tuple[str, str], dict[str, Any]], day: str) -> bool | None:
    row = hours.get((day, "15:00"))
    if not row or row.get("hour_qualified") is not True:
        return None
    bull = row.get("bull")
    return bull if isinstance(bull, bool) else None


def _decision(
    policy: str,
    daily: list[dict[str, Any]],
    hours: dict[tuple[str, str], dict[str, Any]],
    start: int,
    end: int,
    anchor: float,
) -> dict[str, Any]:
    """Make each action with information available through its decision/open."""
    if policy == "direct":
        signal = start
    elif policy == "fixed5":
        signal = start + 5
        if signal + 1 > end:
            return {"status": "nonparticipation", "reason": "no_open_before_endpoint", "decision_date": None}
        for index in range(start + 1, min(signal, len(daily) - 1) + 1):
            low = _positive(daily[index], "adjusted_low")
            if low is None or daily[index].get("qualified") is not True:
                return {"status": "unknown", "reason": "daily_unqualified", "decision_date": None}
            if low < anchor:
                return {"status": "nonparticipation", "reason": "anchor_broken", "decision_date": daily[index]["date"]}
    else:
        signal = None
        for index in range(start, min(end - 1, len(daily) - 1) + 1):
            row = daily[index]
            if row.get("qualified") is not True:
                return {"status": "unknown", "reason": "daily_unqualified", "decision_date": row["date"]}
            if index > start:
                low = _positive(row, "adjusted_low")
                if low is None:
                    return {"status": "unknown", "reason": "daily_unqualified", "decision_date": row["date"]}
                if low < anchor:
                    return {"status": "nonparticipation", "reason": "anchor_broken", "decision_date": row["date"]}
            state = _hour_state(hours, row["date"])
            if state is None:
                return {"status": "unknown", "reason": "unknown_hour_while_waiting", "decision_date": row["date"]}
            if state:
                signal = index
                break
        if signal is None:
            return {"status": "nonparticipation", "reason": "never_confirmed_before_endpoint", "decision_date": None}

    if signal + 1 > end:
        return {"status": "nonparticipation", "reason": "no_open_before_endpoint", "decision_date": daily[signal]["date"] if signal < len(daily) else None}
    if signal >= len(daily) or signal + 1 >= len(daily):
        return {"status": "unknown", "reason": "missing_open", "decision_date": daily[signal]["date"] if signal < len(daily) else None}
    opening = daily[signal + 1]
    decision_close = _positive(daily[signal], "adjusted_close")
    open_price = _positive(opening, "adjusted_open")
    base = {"decision_date": daily[signal]["date"], "scheduled_open_date": opening["date"],
            "decision_close": decision_close, "wait_trading_days": signal - start}
    if open_price is None or decision_close is None:
        return {**base, "status": "unknown", "reason": "missing_open"}
    if open_price < anchor:
        return {**base, "status": "nonparticipation", "reason": "opening_gap_below_anchor",
                "scheduled_open": open_price, "next_open_minus_decision_close_pct": 100 * (open_price / decision_close - 1)}
    return {**base, "status": "participated", "reason": None,
            "entry_date": opening["date"], "entry_open": open_price,
            "next_open_minus_decision_close_pct": 100 * (open_price / decision_close - 1)}


def _outcome(decision: dict[str, Any], daily: list[dict[str, Any]], index_by_date: dict[str, int], end: int) -> dict[str, Any]:
    if decision["status"] == "unknown":
        return {**decision, "score_pct": None, "decline_pct": None}
    if decision["status"] != "participated":
        return {**decision, "score_pct": 0.0, "decline_pct": 0.0}
    entry = index_by_date[decision["entry_date"]]
    price = decision["entry_open"]
    if any(daily[i].get("qualified") is not True for i in range(entry, end + 1)):
        return {**decision, "outcome_reason": "daily_unqualified", "score_pct": None, "decline_pct": None}
    closes = [_positive(daily[i], "adjusted_close") for i in range(entry, end + 1)]
    if any(value is None for value in closes):
        return {**decision, "outcome_reason": "daily_unqualified", "score_pct": None, "decline_pct": None}
    return {**decision, "score_pct": 100 * (closes[-1] / price - 1),
            "decline_pct": max(0.0, 100 * (1 - min([price, *closes]) / price))}


def evaluate_asset(data: dict[str, Any], horizons: list[int] | tuple[int, ...], periods: list[list[str]] | list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    """Return every saved event at every horizon, including unknown outcomes.

    The decision objects use only the prefix through their scheduled open. The
    common-sample field separately describes retrospective future coverage.
    """
    asset = data["asset"]["code"]
    daily = data["daily"]
    hours = {(row["date"], row["time"]): row for row in data["hours"]}
    index_by_date = {row["date"]: index for index, row in enumerate(daily)}
    if len(index_by_date) != len(daily) or any(daily[i]["date"] >= daily[i + 1]["date"] for i in range(len(daily) - 1)):
        raise ValueError("daily dates must be strictly increasing")
    if data["asset"].get("group") != "etf":
        raise ValueError("only the eight frozen ETF inputs are in scope")
    results: list[dict[str, Any]] = []
    for event in data["events"]:
        if event.get("asset", asset) != asset:
            raise ValueError("event asset mismatch")
        first = event["first_seen"]
        start = index_by_date.get(first)
        anchor = _positive(event, "anchor_adjusted_low")
        for horizon in horizons:
            if horizon <= 0:
                raise ValueError("horizon must be positive")
            end = start + horizon if start is not None else None
            period = next((name for name, begin, finish in periods if begin <= first <= finish), None)
            record: dict[str, Any] = {"asset": asset, "identity_key": event["identity_key"], "first_seen": first,
                                      "period": period, "horizon": horizon, "horizon_date": daily[end]["date"] if end is not None and end < len(daily) else None}
            if start is None or anchor is None or period is None or end is None or end >= len(daily):
                reason = "missing_start_or_anchor" if start is None or anchor is None else "outside_period_or_immature"
                record.update(common_status="unknown", common_reason=reason,
                              initial15bull=None, paired=False,
                              policies={name: {"status": "unknown", "reason": reason, "score_pct": None, "decline_pct": None} for name in ("direct", "hourly_eod", "fixed5")})
                results.append(record)
                continue
            initial = _hour_state(hours, first)
            # A missing initial 15:00 state excludes the common comparison even
            # though the direct policy itself needs no hourly signal.
            first_common_error = None
            if initial is None:
                first_common_error = "missing_initial15_state"
            elif daily[start].get("qualified") is not True:
                first_common_error = "daily_unqualified"
            elif not periods or not any(begin <= daily[end]["date"] <= finish for _, begin, finish in periods if begin <= first <= finish):
                first_common_error = "crossperiod"
            else:
                for index in range(start, end + 1):
                    row = daily[index]
                    if row.get("qualified") is not True or any(_positive(row, key) is None for key in ("adjusted_open", "adjusted_low", "adjusted_close")):
                        first_common_error = "daily_unqualified"
                        break
            record["initial15bull"] = initial
            policies = {}
            for name in ("direct", "hourly_eod", "fixed5"):
                decision = _decision(name, daily, hours, start, end, anchor)
                policies[name] = _outcome(decision, daily, index_by_date, end)
            record["policies"] = policies
            record["paired"] = first_common_error is None and all(item["status"] != "unknown" and item["score_pct"] is not None for item in policies.values())
            if not record["paired"] and first_common_error is None:
                first_unknown = next(item for item in policies.values() if item["status"] == "unknown" or item["score_pct"] is None)
                first_common_error = first_unknown.get("outcome_reason") or first_unknown.get("reason") or "policy_unknown"
            record["common_status"] = "paired" if record["paired"] else "unknown"
            record["common_reason"] = first_common_error
            if record["paired"]:
                direct, hourly = policies["direct"], policies["hourly_eod"]
                dr, hr = direct["score_pct"], hourly["score_pct"]
                both = direct["status"] == hourly["status"] == "participated"
                direct_only = direct["status"] == "participated" and hourly["status"] != "participated"
                hourly_only = hourly["status"] == "participated" and direct["status"] != "participated"
                record["decomposition_pp"] = {
                    "timing_both": hr - dr if both else 0.0,
                    "avoided_down_direct_only": -dr if direct_only and dr < 0 else 0.0,
                    "missed_up_direct_only": -dr if direct_only and dr > 0 else 0.0,
                    "hourly_only_positive": hr if hourly_only and hr > 0 else 0.0,
                    "hourly_only_negative": hr if hourly_only and hr < 0 else 0.0,
                }
                record["delta_pp"] = hr - dr
            results.append(record)
    return results
