"""Read-only price-path comparison from saved bottom/hourly waiting observations.

This is an observation score with hypothetical idle cash, not an executable
LEI strategy, fill price, or account return. Bottoms and hourly states are
inputs; this module never recomputes either signal.

Pre-run correction: confirmed participation starts at the saved first hourly
confirmation close, not that day's later daily close. No market run preceded
this correction.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from math import isfinite

DEFAULT_PERIODS = (
    ("2021-2023", "2021-01-01", "2023-12-31"),
    ("2024-2025", "2024-01-01", "2025-12-31"),
    ("2026H1", "2026-01-01", "2026-06-30"),
)


def _price(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) and number > 0 else None


def _period(day, periods):
    return next((name for name, first, last in periods if first <= day <= last), None)


def _decline(closes, entry):
    return 100.0 * max(0.0, 1.0 - min(closes) / entry)


def _unknown(row, reason):
    row.update(qualification="unknown", reason=reason, candidate_status="unknown",
               candidate_participated=None, candidate_entry_date=None,
               candidate_entry_time=None,
               candidate_entry_close=None, candidate_return_pct=None,
               candidate_risk_pct=None, participation_price_change_pct=None,
               confirmation_wait_hours=None, delta_pp=None, missed_upside_pp=None,
               avoided_downside_pp=None, timing_delta_pp=None,
               reference5_participated=None, reference5_return_pct=None,
               reference5_loss_pct=None, hourly_minus_reference5_pp=None)
    return row


def _evaluate(wait, daily, by_date, horizon, periods, asset):
    start = wait.get("first_seen")
    first_period = _period(start, periods) if isinstance(start, str) else None
    row = {"asset": asset.get("code"), "name": asset.get("name"),
           "group": asset.get("group"), "identity_key": wait.get("identity_key"),
           "first_seen": start, "period": first_period, "horizon": horizon,
           "horizon_date": None, "baseline_return_pct": None,
           "baseline_risk_pct": None, "qualification": None, "reason": None}
    if first_period is None:
        return _unknown(row, "outside_period")
    start_index = by_date.get(start)
    if start_index is None:
        return _unknown(row, "missing_start")
    end_index = start_index + horizon
    if end_index >= len(daily):
        return _unknown(row, "immature_horizon")
    end_day = daily[end_index]["date"]
    row["horizon_date"] = end_day
    if _period(end_day, periods) != first_period:
        return _unknown(row, "crosses_period")
    span = daily[start_index:end_index + 1]
    if any(day.get("qualified") is not True for day in span):
        return _unknown(row, "daily_gap")
    closes = [_price(day.get("adjusted_close")) for day in span]
    if any(price is None for price in closes):
        return _unknown(row, "missing_price")
    start_close = closes[0]
    end_close = closes[-1]
    row["baseline_return_pct"] = 100.0 * (end_close / start_close - 1.0)
    row["baseline_risk_pct"] = _decline(closes, start_close)

    if horizon >= 5:
        anchor = _price(wait.get("anchor_adjusted_low"))
        if anchor is None:
            return _unknown(row, "missing_anchor")
        first_week_lows = [_price(day.get("adjusted_low")) for day in span[1:6]]
        if any(low is None for low in first_week_lows):
            return _unknown(row, "missing_first_week_low")
        reference5_participated = not any(low < anchor for low in first_week_lows)
        reference5_entry = closes[5]
        row["reference5_participated"] = reference5_participated
        row["reference5_return_pct"] = (100.0 * (end_close / reference5_entry - 1.0)
                                         if reference5_participated else 0.0)
        row["reference5_loss_pct"] = (_decline(closes[5:], reference5_entry)
                                       if reference5_participated else 0.0)
    else:
        row["reference5_participated"] = None
        row["reference5_return_pct"] = None
        row["reference5_loss_pct"] = None

    status = wait.get("status")
    if status == "initial_unknown":
        return _unknown(row, "initial_hour_unknown")
    terminal = wait.get("terminal_date")
    if (status in {"data_gap", "same_day_ambiguous"} and
            isinstance(terminal, str) and terminal <= end_day):
        return _unknown(row, "hour_gap" if status == "data_gap" else "same_day_ambiguous")
    if status in {"data_gap", "same_day_ambiguous"} and not isinstance(terminal, str):
        return _unknown(row, "missing_terminal_date")

    confirm_day = wait.get("confirmation_date")
    confirm_time = wait.get("confirmation_time")
    if status == "confirmed":
        if not isinstance(confirm_day, str) or not isinstance(confirm_time, str):
            return _unknown(row, "missing_confirmation_time")
        try:
            confirmed_at = datetime.fromisoformat(f"{confirm_day}T{confirm_time}")
            started_at = datetime.fromisoformat(f"{start}T15:00")
        except ValueError:
            return _unknown(row, "invalid_confirmation_time")
        if confirmed_at <= started_at:
            raise ValueError("confirmation must follow the bottom at t0 15:00")
    participates = status == "already" or (
        status == "confirmed" and isinstance(confirm_day, str) and confirm_day <= end_day
    )
    if status == "censored" and (not isinstance(terminal, str) or terminal < end_day):
        return _unknown(row, "hour_observation_ended")
    if status == "broken_before_confirm" and not isinstance(terminal, str):
        return _unknown(row, "missing_terminal_date")
    if status not in {"already", "confirmed", "broken_before_confirm", "censored",
                      "data_gap", "same_day_ambiguous"}:
        return _unknown(row, "unsupported_wait_status")

    row["qualification"] = "paired"
    row["candidate_participated"] = participates
    row["missed_upside_pp"] = 0.0
    row["avoided_downside_pp"] = 0.0
    row["timing_delta_pp"] = 0.0
    if participates:
        entry_day = start if status == "already" else confirm_day
        entry_index = by_date.get(entry_day)
        if entry_index is None or not start_index <= entry_index <= end_index:
            return _unknown(row, "missing_confirmation_day")
        entry_time = "15:00" if status == "already" else confirm_time
        if status == "confirmed" and datetime.fromisoformat(
                f"{entry_day}T{entry_time}") > datetime.fromisoformat(f"{end_day}T15:00"):
            return _unknown(row, "confirmation_after_horizon_close")
        entry_close = (start_close if status == "already" else
                       _price(wait.get("confirmation_adjusted_close")))
        if entry_close is None:
            return _unknown(row, "missing_confirmation_price")
        candidate_return = 100.0 * (end_close / entry_close - 1.0)
        candidate_status = "already" if status == "already" else "confirmed_within_horizon"
        row.update(candidate_status=candidate_status,
                   candidate_entry_date=entry_day, candidate_entry_time=entry_time,
                   candidate_entry_close=entry_close,
                   candidate_return_pct=candidate_return,
                   candidate_risk_pct=_decline(
                       [entry_close, *closes[entry_index - start_index:]], entry_close),
                   participation_price_change_pct=100.0 * (entry_close / start_close - 1.0),
                   confirmation_wait_hours=(0 if status == "already" else
                                            wait.get("wait_observed_hours")),
                   timing_delta_pp=candidate_return - row["baseline_return_pct"])
    else:
        row.update(candidate_status="no_confirmation_within_horizon",
                   candidate_entry_date=None, candidate_entry_time=None,
                   candidate_entry_close=None,
                   candidate_return_pct=0.0, candidate_risk_pct=0.0,
                   participation_price_change_pct=None, confirmation_wait_hours=None,
                   missed_upside_pp=max(row["baseline_return_pct"], 0.0),
                   avoided_downside_pp=max(-row["baseline_return_pct"], 0.0))
    row["delta_pp"] = row["candidate_return_pct"] - row["baseline_return_pct"]
    row["hourly_minus_reference5_pp"] = (row["candidate_return_pct"] - row["reference5_return_pct"]
                                          if row["reference5_return_pct"] is not None else None)
    return row


def evaluate_asset(data, horizons=(20, 30), periods=DEFAULT_PERIODS):
    """Return every saved eligible event at each fixed horizon and qualification counts.

    The horizon is exactly H trading-day steps after the saved bottom date. All
    terminal prices use qualified adjusted daily closes. Confirmed participation
    starts at the saved first hourly close; later path checks use daily closes.
    """
    if not isinstance(data, dict) or not isinstance(data.get("asset"), dict):
        raise ValueError("saved per-asset payload with asset is required")
    daily, waits = data.get("daily"), data.get("waits")
    if not isinstance(daily, list) or not isinstance(waits, list):
        raise ValueError("daily and waits must be lists")
    if (not horizons or any(type(h) is not int or h <= 0 for h in horizons) or
            len(set(horizons)) != len(horizons)):
        raise ValueError("horizons must be unique positive trading-day counts")
    periods = tuple(tuple(p) for p in periods)
    if any(len(p) != 3 or not all(isinstance(x, str) for x in p) or
           date.fromisoformat(p[1]) > date.fromisoformat(p[2]) for p in periods):
        raise ValueError("periods must contain name, first date, last date")
    dates = [day.get("date") for day in daily]
    if any(not isinstance(day, str) for day in dates) or dates != sorted(set(dates)):
        raise ValueError("daily rows must have unique ascending dates")
    by_date = {day: index for index, day in enumerate(dates)}
    if len({w.get("identity_key") for w in waits}) != len(waits):
        raise ValueError("wait identity keys must be unique")

    rows = [_evaluate(wait, daily, by_date, horizon, periods, data["asset"])
            for horizon in horizons for wait in waits]
    counts = {}
    for horizon in horizons:
        for period_name in [*(p[0] for p in periods), "outside_period", "ALL"]:
            subset = [row for row in rows if row["horizon"] == horizon and
                      (period_name == "ALL" or row["period"] == (
                          None if period_name == "outside_period" else period_name))]
            reasons = Counter(row["reason"] for row in subset if row["qualification"] == "unknown")
            counts[f"{horizon}:{period_name}"] = {
                "all": len(subset),
                "paired": sum(row["qualification"] == "paired" for row in subset),
                "unknown": sum(row["qualification"] == "unknown" for row in subset),
                "participating": sum(row["candidate_participated"] is True for row in subset),
                "nonparticipating": sum(row["candidate_participated"] is False for row in subset),
                "unknown_reasons": dict(sorted(reasons.items())),
            }
    return {"asset": data["asset"], "event_rows": rows,
            "qualification_counts": counts,
            "units": {"return": "percent", "risk": "positive_percent",
                      "difference": "percentage_points"},
            "meaning": "event_level_idle_cash_observation_score_not_account_return"}
