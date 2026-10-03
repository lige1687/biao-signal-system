"""Two fixed research previews; declared calendars are not source qualification."""

from __future__ import annotations

import math
from datetime import date

import numpy as np
from tsfresh_calculators import autocorrelation, mean_abs_change

SCHEMA = "tsfresh-candidate-input/1.0"
WINDOW = 20  # Engineering comparison to existing ret20/vol20, not an optimized rule.


def iso_day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("require an ISO date")
    return value


def candidate_preview(payload, as_of):
    """Read only; require 21 consecutive valid closes per declared asset."""
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"require schema {SCHEMA}")
    if payload.get("data_mode") not in {"synthetic", "historical_reconstruction"}:
        raise ValueError("only synthetic or historical_reconstruction preview is supported")
    if payload.get("price_series") != "economic_price":
        raise ValueError("require economic_price; this utility does not adjust raw quotes")
    note = payload.get("source_note")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("declare source_note and its limitations")
    calendar = [iso_day(d) for d in payload["calendar"]]
    if not calendar or calendar != sorted(set(calendar)):
        raise ValueError("require the complete ordered unique declared calendar")
    as_of = iso_day(as_of)
    if as_of not in calendar:
        raise ValueError("as_of must occur in the declared calendar; no fallback date")
    assets = payload["assets"]
    if (
        not isinstance(assets, list)
        or not assets
        or any(not isinstance(a, str) or not a.strip() for a in assets)
        or len(assets) != len(set(assets))
    ):
        raise ValueError("declare unique nonempty assets")
    calendar_set = set(calendar)
    asset_set = set(assets)
    indexed = {a: {} for a in assets}
    for row in payload["bars"]:
        day, asset = iso_day(row["date"]), row["asset"]
        if day not in calendar_set or asset not in asset_set:
            raise ValueError("bar date/asset lies outside the declared domain")
        if day in indexed[asset]:
            raise ValueError("duplicate asset/date")
        indexed[asset][day] = row
    days = calendar[: calendar.index(as_of) + 1]
    output = []
    for asset in assets:
        segment = []
        last_break = None
        for day in days:
            row = indexed[asset].get(day)
            reason = None
            if row is None:
                reason = "missing_bar"
            elif row.get("status") != "quoted":
                reason = "not_quoted"
            elif row.get("action_known") is not True:
                reason = "action_unknown"
            else:
                close = row.get("close")
                if isinstance(close, bool) or not isinstance(close, (int, float)):
                    reason = "invalid_close"
                else:
                    try:
                        close = float(close)
                        if not math.isfinite(close) or close <= 0:
                            reason = "invalid_close"
                    except OverflowError:
                        reason = "invalid_close"
            if reason:
                segment = []
                last_break = {"date": day, "reason": reason}
            else:
                segment.append((day, close))
        item = {
            "asset": asset,
            "date": as_of,
            "continuous_prices": len(segment),
            "last_break": last_break,
            "values": None,
            "baseline": None,
        }
        if len(segment) < WINDOW + 1:
            output.append(
                {**item, "status": "unknown", "reason": "need_21_consecutive_valid_prices"}
            )
            continue
        window = segment[-(WINDOW + 1) :]
        log_prices = 100 * np.log([price for _, price in window])
        returns = np.diff(log_prices)
        ac = float(autocorrelation(returns, lag=1))
        # tsfresh uses np.isclose(var, 0); never convert its NaN to zero.
        ac_known = math.isfinite(ac)
        ratio_log = float((log_prices[-1] - log_prices[0]) / 100)
        try:
            ret20 = 100 * math.expm1(ratio_log)
        except OverflowError as exc:
            raise ValueError("price ratio outside finite preview range") from exc
        if not math.isfinite(ret20):
            raise ValueError("price ratio outside finite preview range")
        output.append(
            {
                **item,
                "status": "available" if ac_known else "partial",
                "window_start": window[0][0],
                "window_end": window[-1][0],
                "values": {
                    "mean_abs_log_change20": float(mean_abs_change(log_prices)),
                    "return_autocorrelation20_lag1": ac if ac_known else None,
                },
                "unknown_reasons": {}
                if ac_known
                else {"return_autocorrelation20_lag1": "upstream_near_zero_variance"},
                "baseline": {
                    "ret20_pct": ret20,
                    "vol20_annualized_pct": float(np.std(returns, ddof=1) * math.sqrt(252)),
                },
            }
        )
    return {
        "schema": "tsfresh-candidate-preview/1.0",
        "as_of": as_of,
        "upstream": "tsfresh 0.21.2 selected calculators",
        "window_returns": WINDOW,
        "units": {
            "mean_abs_log_change20": "log-return percentage points per declared session",
            "return_autocorrelation20_lag1": "dimensionless; upstream full-window normalization",
        },
        "data_mode": payload["data_mode"],
        "source_note": note,
        "scope": (
            "candidate calculation only; not a registered factor or effect/production approval"
        ),
        "limitations": [
            "calendar and historical availability are caller declarations",
            "economic prices and action_known are not independently verified here",
            "lag-one estimator is not clipped to [-1,1]",
        ],
        "rows": output,
    }
