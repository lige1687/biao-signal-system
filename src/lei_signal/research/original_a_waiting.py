"""Research-only first-bottom and hourly waiting descriptions, without trading decisions.

Bottom merge, confirmation and first-identity grammar are copied in minimal form from
docs/experiments/raw/strict-bottom-first-description-2026-10-01/feature/
structure_first_observed.py, SHA256
48e15ddb5e4ff7e10fa85e8e4763e100d515afb6aed708d500ddd24a34d204f1.
EMA matches src/lei_signal/features/indicators.py::seeded_ema, source SHA256
098b931d3527f8b8a9e77961e62402c5a79eefcfce0e91b84bb565e65f5f5c26.
No archived runner is imported. All price inputs must already be adjusted and qualified.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import deque


IDENTITY_VERSION = "strict_bottom_first_observed_anchors_v1"
WINDOWS = (20, 60, 120)


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _rows(rows, *, time=False):
    previous = None
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            raise ValueError("rows need date strings")
        key = (row["date"], row.get("time")) if time else row["date"]
        if time and not isinstance(row.get("time"), str):
            raise ValueError("hour rows need time strings")
        if previous is not None and key <= previous:
            raise ValueError("rows must be strictly ordered without duplicates")
        previous = key
        yield row


def _append_merge(groups, bar, position):
    """Frozen one-step left-to-right containment merge; no recursive merge."""
    high, low, day = bar["high"], bar["low"], bar["date"]
    if groups:
        last = groups[-1]
        contains = ((high <= last["high"] and low >= last["low"]) or
                    (high >= last["high"] and low <= last["low"]))
        if contains:
            groups[-1] = {**last, "high": max(last["high"], high),
                          "low": min(last["low"], low), "completed_date": day,
                          "last_position": position, "source_bars": last["source_bars"] + 1}
            return
    groups.append({"high": high, "low": low, "first_date": day,
                   "completed_date": day, "first_position": position,
                   "last_position": position, "source_bars": 1})


def _bottom_snapshots(groups):
    pending = None
    confirmations = []
    for index, bar in enumerate(groups):
        previous = groups[index - 1] if index else None
        if pending is not None:
            m1, m2 = pending
            if bar["low"] < m1["low"]:
                pending = None
            elif bar["high"] > m2["high"]:
                confirmations.append({"M1": copy.deepcopy(m1), "M2": copy.deepcopy(m2),
                                      "Mk": copy.deepcopy(bar), "reference_price": m1["low"],
                                      "trigger_price": m2["high"], "final_price": bar["high"],
                                      "detected_confirmed_date": bar["completed_date"]})
                pending = None
        if previous is not None and pending is None and bar["low"] > previous["low"]:
            pending = (previous, bar)
    return confirmations


def daily_bottom_events(rows, *, asset):
    """Emit each first identity once, including first events before 252 qualified days.

    ``qualified`` false breaks the source segment; historical first facts stay fixed.
    ``warm252`` is set only at first observation, never retroactively.
    """
    if not isinstance(asset, str) or not asset:
        raise ValueError("asset is required")
    groups, seen, events = [], set(), []
    segment_start, segment_n = None, 0
    for position, raw in enumerate(_rows(rows)):
        qualified = raw.get("qualified")
        if type(qualified) is not bool:
            raise ValueError("daily qualified must be boolean")
        if not qualified:
            groups, segment_start, segment_n = [], None, 0
            continue
        day = raw["date"]
        high = _number(raw.get("adjusted_high"), "adjusted_high")
        low = _number(raw.get("adjusted_low"), "adjusted_low")
        close = _number(raw.get("adjusted_close"), "adjusted_close")
        opened = _number(raw.get("adjusted_open"), "adjusted_open")
        if min(opened, high, low, close) <= 0 or low > min(opened, close) or high < max(opened, close):
            raise ValueError("invalid adjusted daily OHLC")
        if segment_start is None:
            segment_start = day
        segment_n += 1
        _append_merge(groups, {"date": day, "high": high, "low": low}, position)
        for snapshot in _bottom_snapshots(groups):
            identity = [asset, "1d", segment_start, "bottom", snapshot["M1"]["first_date"],
                        snapshot["M2"]["first_date"], IDENTITY_VERSION]
            key = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if key in seen:
                continue
            if snapshot["detected_confirmed_date"] != day:
                raise ValueError("new first identity appeared after its confirmation date")
            seen.add(key)
            first_groups = {name: {field: snapshot[name][field] for field in
                                   ("first_date", "completed_date", "source_bars",
                                    "first_position", "last_position")}
                            for name in ("M1", "M2", "Mk")}
            m1, m2, mk = (first_groups[name] for name in ("M1", "M2", "Mk"))
            span = position - snapshot["M1"]["last_position"]
            simple_three = (all(group["source_bars"] == 1 for group in (m1, m2, mk))
                            and span == 2
                            and m1["last_position"] + 1 == m2["first_position"]
                            and m2["last_position"] + 1 == mk["first_position"])
            events.append({"identity_key": key, "identity_tuple": identity,
                           "identity_sha256": hashlib.sha256(key.encode()).hexdigest(),
                           "asset": asset, "first_seen": day, "source_segment_first_date": segment_start,
                           "continuous_daily_n_at_first": segment_n, "warm252": segment_n >= 252,
                           "anchor_adjusted_low": snapshot["reference_price"],
                           "adjusted_close_at_first": close,
                           "trigger_adjusted_high": snapshot["trigger_price"],
                           "final_adjusted_high": snapshot["final_price"],
                           "confirmation_span_daily_bars": span,
                           "simple_three_raw_bars": simple_three,
                           "snapshot_at_first": {**first_groups,
                                                 "reference_price": snapshot["reference_price"],
                                                 "trigger_price": snapshot["trigger_price"],
                                                 "final_price": snapshot["final_price"]}})
    return events


def hourly_arrangement(rows):
    """Finite-history EMA/SMA strict 20>60>120 state for each observed hour.

    Each EMA starts with its first N-close SMA seed, as seeded_ema does. ``n>=120`` only makes
    the finite-history proxy defined; it does not establish sufficient EMA burn-in.
    Any unqualified hour invalidates the entire day and resets the next segment.
    """
    source = list(_rows(rows, time=True))
    bad_days = {r["date"] for r in source if type(r.get("hour_qualified")) is not bool or not r["hour_qualified"]}
    ema = {}
    windows = {n: deque(maxlen=n) for n in WINDOWS}
    count = 0
    states = []
    for row in source:
        good = row["date"] not in bad_days
        if not good:
            ema = {}
            windows = {n: deque(maxlen=n) for n in WINDOWS}
            count = 0
            states.append({"date": row["date"], "time": row["time"],
                           "hour_qualified": False, "bull": None, "continuous_hour_n": 0,
                           "adjusted_close": None, "ema": None, "sma": None})
            continue
        price = _number(row.get("adjusted_close"), "hour adjusted_close")
        if price <= 0:
            raise ValueError("hour adjusted_close must be positive")
        count += 1
        for n in WINDOWS:
            windows[n].append(price)
            if count == n:
                ema[n] = sum(windows[n]) / n
            elif count > n:
                ema[n] = (2 / (n + 1)) * price + (1 - 2 / (n + 1)) * ema[n]
        sma = {n: sum(windows[n]) / n for n in WINDOWS if len(windows[n]) == n}
        bull = ((ema[20] > ema[60] > ema[120]) and
                (sma[20] > sma[60] > sma[120])) if count >= 120 else None
        states.append({"date": row["date"], "time": row["time"],
                       "hour_qualified": True, "bull": bull, "continuous_hour_n": count,
                       "adjusted_close": price,
                       "ema": {n: ema[n] for n in WINDOWS} if count >= 120 else None,
                       "sma": sma if count >= 120 else None})
    return states


def describe_waits(events, hour_states, daily_rows):
    """Classify every first event through observed hours; no intraday order inference.

    Daily low is whole-day information. Bull plus a same-day anchor breach is
    ambiguous even if an hourly path seems to suggest an order. Wait length counts
    observed hourly bars only, including the confirming bar; lunch adds nothing.
    """
    days = list(_rows(daily_rows))
    hours = list(_rows(hour_states, time=True))
    by_day = {}
    for hour in hours:
        by_day.setdefault(hour["date"], []).append(hour)
    day_index = {day["date"]: i for i, day in enumerate(days)}
    results = []
    for event in events:
        start = event["first_seen"]
        if start not in day_index:
            raise ValueError("event start date missing from daily rows")
        anchor = _number(event["anchor_adjusted_low"], "anchor_adjusted_low")
        start_close = _number(event["adjusted_close_at_first"], "adjusted_close_at_first")
        opening = next((h for h in by_day.get(start, []) if h["time"] == "15:00"), None)
        initial_n = opening["continuous_hour_n"] if opening else None
        result = {"identity_key": event["identity_key"], "first_seen": start,
                  "warm252": event.get("warm252"), "anchor_adjusted_low": anchor,
                  "start_adjusted_close": start_close, "initial_hour_n": initial_n,
                  "confirmation_hour_n": None, "wait_observed_hours": None,
                  "confirmation_date": None, "confirmation_time": None,
                  "confirmation_adjusted_close": None, "price_change_pct": None,
                  "terminal_date": start, "terminal_time": "15:00",
                  "daily_broken": False, "status": None, "not_full_A": True}
        if opening is None or not opening.get("hour_qualified") or opening.get("bull") is None:
            result["status"] = "initial_unknown"
        elif opening["bull"] is True:
            result.update(status="already", wait_observed_hours=0,
                          confirmation_hour_n=initial_n, confirmation_date=start,
                          confirmation_time="15:00", confirmation_adjusted_close=opening["adjusted_close"],
                          price_change_pct=0.0)
        elif opening["bull"] is not False:
            raise ValueError("bull must be True, False or None")
        else:
            waited = 0
            for day in days[day_index[start] + 1:]:
                date = day["date"]
                daily_good = day.get("qualified") is True
                day_hours = by_day.get(date, [])
                hours_good = bool(day_hours) and all(h.get("hour_qualified") is True for h in day_hours)
                low = _number(day.get("adjusted_low"), "adjusted_low") if daily_good else None
                broken = low is not None and low < anchor
                if not daily_good or not hours_good or any(h.get("bull") is None for h in day_hours):
                    result.update(status="data_gap", daily_broken=broken, wait_observed_hours=waited,
                                  terminal_date=date, terminal_time=None)
                    break
                bull_hours = [h for h in day_hours if h["bull"] is True]
                if bull_hours and broken:
                    result.update(status="same_day_ambiguous", daily_broken=True,
                                  wait_observed_hours=waited + day_hours.index(bull_hours[0]) + 1,
                                  terminal_date=date, terminal_time=None)
                    break
                if broken:
                    result.update(status="broken_before_confirm", daily_broken=True,
                                  wait_observed_hours=waited + len(day_hours),
                                  terminal_date=date, terminal_time=None)
                    break
                if bull_hours:
                    first = bull_hours[0]
                    result.update(status="confirmed", wait_observed_hours=waited + day_hours.index(first) + 1,
                                  confirmation_date=date, confirmation_time=first["time"],
                                  terminal_date=date, terminal_time=first["time"],
                                  confirmation_adjusted_close=first["adjusted_close"],
                                  confirmation_hour_n=first["continuous_hour_n"],
                                  price_change_pct=100 * (first["adjusted_close"] / start_close - 1))
                    break
                waited += len(day_hours)
            if result["status"] is None:
                result.update(status="censored", wait_observed_hours=waited,
                              terminal_date=days[-1]["date"], terminal_time="15:00")
        results.append(result)
    return results
