"""Research-only bottom observation and daily-close exit-price comparisons.

Prices are adjusted observations, not executable orders or account returns. The
incremental detector preserves the frozen first-observation grammar in
``original_a_waiting.daily_bottom_events`` without rescanning every prefix.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import deque

from lei_signal.research.original_a_waiting import IDENTITY_VERSION, _append_merge, _number, _rows

PERIODS = (("2021-2023", "2021-01-01", "2023-12-31"),
           ("2024-2025", "2024-01-01", "2025-12-31"),
           ("2026H1", "2026-01-01", "2026-06-30"))


def _advance(pending, previous, bar):
    """Process one immutable merged group; return pending and confirmations."""
    confirmations = []
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
    return pending, confirmations


def _event(snapshot, *, asset, day, segment_start, segment_n, position, close):
    identity = [asset, "1d", segment_start, "bottom", snapshot["M1"]["first_date"],
                snapshot["M2"]["first_date"], IDENTITY_VERSION]
    key = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    first_groups = {name: {field: snapshot[name][field] for field in
                           ("first_date", "completed_date", "source_bars", "first_position", "last_position")}
                    for name in ("M1", "M2", "Mk")}
    m1, m2, mk = (first_groups[name] for name in ("M1", "M2", "Mk"))
    span = position - snapshot["M1"]["last_position"]
    simple_three = (all(group["source_bars"] == 1 for group in (m1, m2, mk))
                    and span == 2 and m1["last_position"] + 1 == m2["first_position"]
                    and m2["last_position"] + 1 == mk["first_position"])
    return {"identity_key": key, "identity_tuple": identity,
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
                                  "final_price": snapshot["final_price"]}}


def daily_bottom_events_incremental(rows, *, asset):
    """Return frozen first events in O(rows) time and O(groups + events) space.

    Only the final merged group may change. ``prefix_pending`` is the state
    before that group; on a containment merge, that group alone is reprocessed.
    """
    if not isinstance(asset, str) or not asset:
        raise ValueError("asset is required")
    groups, seen, events = [], set(), []
    segment_start, segment_n = None, 0
    prefix_pending = None
    for position, raw in enumerate(_rows(rows)):
        qualified = raw.get("qualified")
        if type(qualified) is not bool:
            raise ValueError("daily qualified must be boolean")
        if not qualified:
            groups, segment_start, segment_n, prefix_pending = [], None, 0, None
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
        old_count = len(groups)
        old_last = groups[-1] if groups else None
        old_before_last = groups[-2] if len(groups) > 1 else None
        _append_merge(groups, {"date": day, "high": high, "low": low}, position)
        if old_last is not None and len(groups) > old_count:
            # The old final group is now immutable: commit its state once.
            prefix_pending, _ = _advance(prefix_pending, old_before_last, old_last)
        previous = groups[-2] if len(groups) > 1 else None
        _, snapshots = _advance(prefix_pending, previous, groups[-1])
        for snapshot in snapshots:
            identity = [asset, "1d", segment_start, "bottom", snapshot["M1"]["first_date"],
                        snapshot["M2"]["first_date"], IDENTITY_VERSION]
            key = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if key in seen:
                continue
            if snapshot["detected_confirmed_date"] != day:
                raise ValueError("new first identity appeared after its confirmation date")
            seen.add(key)
            events.append(_event(snapshot, asset=asset, day=day, segment_start=segment_start,
                                 segment_n=segment_n, position=position, close=close))
    return events


def _period(day):
    return next((name for name, start, end in PERIODS if start <= day <= end), None)


def _valid_day(row):
    if row.get("qualified") is not True:
        return False
    try:
        high = _number(row.get("adjusted_high"), "adjusted_high")
        low = _number(row.get("adjusted_low"), "adjusted_low")
        close = _number(row.get("adjusted_close"), "adjusted_close")
        opened = _number(row.get("adjusted_open"), "adjusted_open")
        return min(high, low, close, opened) > 0 and low <= min(opened, close) and high >= max(opened, close)
    except ValueError:
        return False


def _daily_features(daily):
    """Finite-history indicators, reset at unqualified or invalid daily rows."""
    features = []
    windows = {n: deque(maxlen=n) for n in (20, 60, 120)}
    emas = {n: None for n in (20, 60, 120)}
    count = 0
    history = []
    for row in daily:
        if not _valid_day(row):
            windows = {n: deque(maxlen=n) for n in (20, 60, 120)}
            emas = {n: None for n in (20, 60, 120)}
            count, history = 0, []
            features.append(None)
            continue
        price = float(row["adjusted_close"])
        lag20 = history[-20] if len(history) >= 20 else None
        lag60 = history[-60] if len(history) >= 60 else None
        lag120 = history[-120] if len(history) >= 120 else None
        count += 1
        for n in (20, 60, 120):
            windows[n].append(price)
            if count == n:
                emas[n] = sum(windows[n]) / n
            elif count > n:
                emas[n] = (2 / (n + 1)) * price + (1 - 2 / (n + 1)) * emas[n]
        history.append(price)
        features.append({"continuous_n": count, "ema20": emas[20], "ema60": emas[60],
                         "ema120": emas[120], "sma60": sum(windows[60]) / 60 if count >= 60 else None,
                         "sma120": sum(windows[120]) / 120 if count >= 120 else None,
                         "lag20": lag20, "lag60": lag60, "lag120": lag120})
    return features


def _policy(daily, start, end, signal_index, reason, start_price, hold_return):
    exit_index = min(signal_index + 1, end) if signal_index is not None else end
    exit_price = float(daily[exit_index]["adjusted_close"])
    change = 100 * (exit_price / start_price - 1)
    path = [start_price] + [float(daily[i]["adjusted_close"]) for i in range(start, exit_index + 1)]
    delta = change - hold_return
    return {"end_adjusted_close": exit_price, "return_pct": change, "loss_pct": 100 * max(0, 1 - min(path) / start_price),
            "exit_date": daily[exit_index]["date"] if signal_index is not None and signal_index + 1 <= end else None,
            "exit_reason": reason if signal_index is not None and signal_index + 1 <= end else None,
            "exposure_trading_days": exit_index - start,
            "minus_hold_pp": delta,
            "avoided_downside_pp": max(delta, 0), "missed_upside_pp": max(-delta, 0)}


def evaluate_asset(daily, events, asset, horizons=(20, 30)):
    """Compare adjusted closing-price opportunities from saved first-bottom events.

    A trigger observed on day d ends observation at day d+1 close. This is a
    descriptive policy contrast; no intraday fill, stops, fees, or account path.
    Unknown rows remain in the output with all four policies unset.
    """
    daily = list(_rows(daily))
    if not isinstance(asset, str) or not asset:
        raise ValueError("asset is required")
    if any(type(h) is not int or h <= 0 for h in horizons):
        raise ValueError("horizons must be positive integers")
    by_date = {row["date"]: i for i, row in enumerate(daily)}
    features = _daily_features(daily)
    result = []
    for event in events:
        if event.get("asset") != asset:
            raise ValueError("event asset mismatch")
        start = by_date.get(event.get("first_seen"))
        for horizon in horizons:
            base = {"asset": asset, "identity_key": event.get("identity_key"),
                    "first_seen": event.get("first_seen"), "horizon": horizon,
                    "period": _period(event.get("first_seen", "")), "status": "unknown",
                    "unknown_reason": None, "background_rising": None,
                    "hold": None, "frozen_bottom": None, "reverse20": None, "combined": None}
            reason = None
            end = None if start is None else start + horizon
            if event.get("warm252") is not True:
                reason = "not_warm252"
            elif start is None:
                reason = "missing_start"
            elif end >= len(daily):
                reason = "immature_horizon"
            elif base["period"] is None or _period(daily[end]["date"]) != base["period"]:
                reason = "cross_period"
            elif any(not _valid_day(row) for row in daily[start:end + 1]):
                reason = "unqualified_or_missing_price"
            elif features[start] is None or features[start]["continuous_n"] < 252:
                reason = "insufficient_qualified_history"
            else:
                try:
                    anchor = _number(event.get("anchor_adjusted_low"), "anchor_adjusted_low")
                    first_close = _number(event.get("adjusted_close_at_first"), "adjusted_close_at_first")
                    if anchor <= 0 or not math.isclose(first_close, float(daily[start]["adjusted_close"]), rel_tol=1e-10, abs_tol=1e-10):
                        reason = "event_price_mismatch"
                except ValueError:
                    reason = "missing_event_price"
            if reason is not None:
                base["unknown_reason"] = reason
                result.append(base)
                continue
            start_price = float(daily[start]["adjusted_close"])
            hold_return = 100 * (float(daily[end]["adjusted_close"]) / start_price - 1)
            f = features[start]
            base["background_rising"] = bool(f["sma60"] > f["sma120"] and f["ema60"] > f["ema120"]
                                             and start_price > f["lag60"] and start_price > f["lag120"])
            bottom_signal = next((i for i in range(start + 1, end) if float(daily[i]["adjusted_low"]) < anchor), None)
            reverse_signal = next((i for i in range(start, end)
                                   if features[i] is not None and features[i]["ema20"] is not None
                                   and features[i]["lag20"] is not None
                                   and float(daily[i]["adjusted_close"]) < features[i]["ema20"]
                                   and float(daily[i]["adjusted_close"]) < features[i]["lag20"]), None)
            signals = [(i, name) for i, name in ((bottom_signal, "frozen_bottom"), (reverse_signal, "reverse20")) if i is not None]
            both_signal, both_reason = min(signals, key=lambda x: x[0]) if signals else (None, None)
            if bottom_signal is not None and bottom_signal == reverse_signal:
                both_reason = "both"
            for name, signal, why in (("hold", None, None), ("frozen_bottom", bottom_signal, "frozen_bottom"),
                                      ("reverse20", reverse_signal, "reverse20"),
                                      ("combined", both_signal, both_reason)):
                base[name] = _policy(daily, start, end, signal, why, start_price, hold_return)
            base.update(status="known", unknown_reason=None, end_date=daily[end]["date"],
                        start_adjusted_close=start_price, anchor_adjusted_low=anchor)
            result.append(base)
    return result
