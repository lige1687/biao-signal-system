"""Research-only Sina ETF price qualification; no acquisition or trading.

An official pre-July-2026 SSE fund close is not required to equal the last
hour's close. Missing/corrupt hours reset the shared hourly state via explicit
unqualified slots. Daily observations and bottom identities remain frozen.
"""
from bisect import bisect_right
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from lei_signal.research.hourly_confirmation_increment import evaluate_asset

SLOTS = ("10:30", "11:30", "14:00", "15:00")
TOL = Decimal("0.00000001")


def number(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("non-numeric price") from None
    if not n.is_finite() or n <= 0:
        raise ValueError("nonpositive or nonfinite price")
    return n


def valid_bar(row):
    try:
        o, h, l, c = [number(row[k]) for k in ("open", "high", "low", "close")]
        return l <= min(o, c) <= max(o, c) <= h
    except (ValueError, KeyError):
        return False


def qualify_sina_hours(raw_hours, raw_daily, factors, saved_daily, cutoff="2026-06-30"):
    """Return price-only source branch; no interpolation or guessed factor 1.

    factors contains action effective dates and backAdjustFactor, selected
    as-of each day. This is today's vendor history, not historical arrival proof.
    Exact duplicate/nonmonotonic raw dates are rejected, not silently deduped.
    """
    by_day = defaultdict(list)
    previous = None
    for row in raw_hours:
        stamp = row["day"]
        if previous is not None and stamp <= previous:
            raise ValueError("unordered or duplicate source hour")
        previous = stamp
        day, slot = stamp[:10], stamp[11:16]
        if day <= cutoff:
            by_day[day].append((slot, row))
    raw_by_day = {}
    previous = None
    for row in raw_daily:
        day = row["day"][:10]
        if previous is not None and day <= previous:
            raise ValueError("unordered or duplicate source day")
        previous = day
        if day <= cutoff:
            raw_by_day[day] = row
    factor_dates, factor_values = [], []
    for row in factors:
        day = row["dividOperateDate"]
        if factor_dates and day <= factor_dates[-1]:
            raise ValueError("unordered or duplicate effective factor date")
        factor_dates.append(day)
        factor_values.append(number(row["backAdjustFactor"]))
    hours, audit = [], []
    previous = None
    for saved in saved_daily:
        day = saved["date"]
        if previous is not None and day <= previous:
            raise ValueError("unordered or duplicate calendar day")
        previous = day
        if day > cutoff:
            continue
        group = by_day.get(day, [])
        raw = raw_by_day.get(day)
        reason, factor, action_day = None, None, None
        factor_index = bisect_right(factor_dates, day) - 1
        if not saved.get("qualified"):
            reason = "daily_unqualified"
        elif tuple(s for s, _ in group) != SLOTS:
            reason = "missing_or_misordered_hour_slots"
        elif raw is None or not valid_bar(raw) or any(not valid_bar(b) for _, b in group):
            reason = "invalid_or_missing_source_price"
        elif factor_index < 0:
            reason = "factor_effective_date_unknown"
        else:
            action_day, factor = factor_dates[factor_index], factor_values[factor_index]
            bars = [b for _, b in group]
            for key in ("open", "high", "low", "close"):
                if abs(number(raw[key]) * factor - number(saved["adjusted_" + key])) > TOL:
                    reason = "same_date_adjusted_daily_mismatch"
                    break
            aggregate = {"open": number(bars[0]["open"]),
                         "high": max(number(b["high"]) for b in bars),
                         "low": min(number(b["low"]) for b in bars)}
            if reason is None and any(abs(aggregate[k] - number(raw[k])) > TOL for k in aggregate):
                reason = "hour_vs_daily_OHL_mismatch"
            if reason is None and not number(bars[-1]["low"]) - TOL <= number(raw["close"]) <= number(bars[-1]["high"]) + TOL:
                reason = "official_close_outside_last_hour_range"
        good = reason is None
        volume_mismatch = None
        if raw is not None and len(group) == 4:
            try:
                volume_mismatch = sum(Decimal(str(b["volume"])) for _, b in group) != Decimal(str(raw["volume"]))
            except (KeyError, InvalidOperation):
                volume_mismatch = None
        audit.append({"date": day, "qualified": good, "reason": reason,
                      "factor_effective_date": action_day,
                      "factor": str(factor) if factor is not None else None,
                      "volume_mismatch": volume_mismatch})
        for index, slot in enumerate(SLOTS):
            hours.append({"date": day, "time": slot, "hour_qualified": good,
                          "adjusted_close": float(number(group[index][1]["close"]) * factor) if good else None})
    streak = longest = 0
    for row in audit:
        streak = streak + 1 if row["qualified"] else 0
        longest = max(longest, streak)
    return {"hours": hours, "daily_audit": audit,
            "qualification": {"source_branch": "sina-etf-hour-price/1.0",
                              "reason_counts": dict(Counter(r["reason"] or "qualified" for r in audit)),
                              "longest_qualified_days": longest,
                              "volume_mismatch_days": sum(r["volume_mismatch"] is True for r in audit),
                              "scope": "price_only; no independently verified minute OHLC or volume or historical availability"}}


def evaluate_etf_observations(data, horizons=(20, 30)):
    """Reuse fixed policies with explicit simultaneous-price treatment.

    No observation after H15:00 is available for a confirmation at H15:00.
    A prior day's 15:00 hourly close and official daily close are simultaneous
    different price definitions, so that day's official close is not a later
    adverse observation. Existing original evaluator and results are untouched.
    """
    result = evaluate_asset(data, horizons=horizons)
    daily = data["daily"]
    indices = {r["date"]: i for i, r in enumerate(daily)}
    for row in result["event_rows"]:
        if row["qualification"] != "paired" or row["candidate_status"] != "confirmed_within_horizon":
            continue
        if row["candidate_entry_time"] != "15:00":
            continue
        if row["candidate_entry_date"] == row["horizon_date"]:
            row.update(qualification="unknown", reason="confirmation_at_endpoint_no_later_observation",
                       candidate_status="unknown")
            for key in ("candidate_participated", "candidate_return_pct", "candidate_risk_pct",
                        "reference5_participated", "reference5_return_pct", "reference5_loss_pct",
                        "participation_price_change_pct", "confirmation_wait_hours", "delta_pp",
                        "hourly_minus_reference5_pp", "timing_delta_pp", "missed_upside_pp",
                        "avoided_downside_pp"):
                row[key] = None
            continue
        start = indices[row["candidate_entry_date"]] + 1
        end = indices[row["horizon_date"]]
        entry = row["candidate_entry_close"]
        row["candidate_risk_pct"] = 100 * max(0.0, 1 - min(
            [entry] + [r["adjusted_close"] for r in daily[start:end + 1]]) / entry)
    # Original counts precede wrapper changes; recompute rather than expose stale counts.
    counts = {}
    for horizon in horizons:
        subset = [r for r in result["event_rows"] if r["horizon"] == horizon]
        counts[str(horizon)] = {"all": len(subset),
                               "paired": sum(r["qualification"] == "paired" for r in subset),
                               "unknown_reasons": dict(Counter(r["reason"] for r in subset if r["qualification"] != "paired"))}
    result["qualification_counts"] = counts
    result["source_branch"] = "sina-etf-hour-price/1.0"
    result["feature_definition"] = "research.structure.bottom_hourly_waiting@1.1.0"
    return result
