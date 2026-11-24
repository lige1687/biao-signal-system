"""Retrospective monthly ranking within LEI-green stocks.

This is a research adaptation, not a production signal or a reproduction of
the original US residual-momentum portfolio. Feature functions stop at the
decision close; future quote inspection lives in ``future_outcome`` only.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from statistics import mean, stdev

import numpy as np
import pandas as pd

from lei_signal.features.indicators import seeded_ema
from lei_signal.research.fip import (
    hac_mean,
    month_add,
    rank_midpercent,
)
from lei_signal.rules.lei_color import classify_colors

ARMS = (
    "all_green",
    "ordinary",
    "arithmetic_control",
    "scaled_control",
    "residual",
    "high52",
    "ordinary_high52",
)
TOP_SHARE = 0.30
REQUIRED_MONTHS = 36
MIN_COMMON = 30


def factor_table(rows: Sequence[Sequence[object]]) -> dict[str, tuple[float, float, float, float]]:
    """Read CH3 decimal monthly RF, market excess, SMB and VMG values."""
    result = {}
    for row in rows:
        if not row or row[0] in (None, "mnthdt"):
            continue
        stamp = str(int(row[0]))
        month = f"{stamp[:4]}-{stamp[4:6]}"
        values = tuple(float(x) for x in row[1:5])
        if len(values) != 4 or not all(math.isfinite(x) for x in values):
            raise ValueError(f"bad CH3 factors: {month}")
        if month in result:
            raise ValueError(f"duplicate CH3 month: {month}")
        result[month] = values
    return result


def residual_scores(
    month_returns: Sequence[float], factors: Sequence[Sequence[float]]
) -> dict[str, float]:
    """Fit 36 excess-return months; score prior 11 months excluding T.

    q = y - X @ slopes retains fitted alpha. It deliberately differs from
    full OLS residual y - X @ [intercept, slopes].
    """
    if len(month_returns) != REQUIRED_MONTHS or len(factors) != REQUIRED_MONTHS:
        raise ValueError("need exactly 36 aligned months")
    values = np.asarray(month_returns, dtype=float)
    f = np.asarray(factors, dtype=float)
    if f.shape != (REQUIRED_MONTHS, 4) or not np.isfinite(values).all() or not np.isfinite(f).all():
        raise ValueError("incomplete monthly return or CH3 factor")
    y = values - f[:, 0]
    x = np.column_stack((np.ones(REQUIRED_MONTHS), f[:, 1:]))
    if np.linalg.matrix_rank(x) != 4:
        raise ValueError("CH3 design matrix lacks full rank")
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    q = y - f[:, 1:] @ beta[1:]
    last11 = slice(-12, -1)
    raw = values[last11]
    excess = y[last11]
    adj = q[last11]
    sd_excess, sd_adj = stdev(excess), stdev(adj)
    # Numerical OLS roundoff can leave a tiny positive SD for an exactly
    # explained series. In decimal monthly-return units this is zero noise.
    if sd_excess <= 1e-12 or sd_adj <= 1e-12 or not math.isfinite(sd_excess + sd_adj):
        raise ValueError("nonpositive eleven-month sample standard deviation")
    return {
        "ordinary": math.prod(1 + v for v in raw) - 1,
        "arithmetic_control": float(sum(excess)),
        "scaled_control": float(sum(excess) / sd_excess),
        "residual": float(sum(adj) / sd_adj),
        "alpha": float(beta[0]),
        "residual_sd": float(sd_adj),
    }


def _valid_daily(row: Mapping, previous: Mapping | None) -> bool:
    try:
        close, preclose = float(row["close"]), float(row["preclose"])
        if not all(math.isfinite(x) and x > 0 for x in (close, preclose)):
            return False
        if row["adjustflag"] != "2" or row["tradestatus"] not in ("0", "1"):
            return False
        traded = row["tradestatus"] == "1"
        pct_raw = row.get("pctChg")
        pct_text = "" if pct_raw is None else str(pct_raw).strip()
        if traded and not pct_text:
            return False
        if pct_text and abs(close / preclose - 1 - float(pct_text) / 100) > 1e-6:
            return False
        if not traded:
            volume_text = str(row.get("volume", "")).strip()
            volume = float(volume_text) if volume_text else 0.0
            if abs(close / preclose - 1) > 1e-6 or volume != 0:
                return False
        return previous is None or abs(float(previous["close"]) / preclose - 1) <= 1e-6
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


def _month_ends(calendar: Sequence[str]) -> dict[str, str]:
    ends = {}
    for day in calendar:
        ends[day[:7]] = day
    return ends


def qualified_features(
    rows: Sequence[dict],
    calendar: Sequence[str],
    factors: Mapping[str, Sequence[float]],
    code: str,
    first_month: str,
    last_month: str,
) -> list[dict]:
    """One source-qualified stock; evaluate only quotes through each T close."""
    dates = list(calendar)
    by_date = {r["date"]: r for r in rows}
    ends = _month_ends(dates)
    calendar_by_month = defaultdict(list)
    for day in dates:
        calendar_by_month[day[:7]].append(day)
    chronological = sorted(by_date)
    closes = pd.Series([float(by_date[d]["close"]) for d in chronological], index=chronological)
    # Never fill a missing calendar row. The 36-month qualification below
    # separately rejects any gap that reaches a decision window.
    ema = seeded_ema(closes, 20)
    colors = classify_colors(
        pd.DataFrame({"close": closes, "ema20": ema, "close_lag20": closes.shift(20)})
    )
    output = []
    month = first_month
    date_index = {d: i for i, d in enumerate(dates)}
    while month <= last_month:
        decision = ends.get(month)
        reasons = []
        last36 = [month_add(month, -35 + i) for i in range(36)]
        month_returns = []
        if decision not in by_date:
            reasons.append("decision_quote_missing")
        else:
            r = by_date[decision]
            if r["tradestatus"] != "1" or r["isST"] != "0" or float(r["volume"]) <= 0:
                reasons.append("decision_not_traded_or_st")
            if colors.loc[decision, "signal_color"] != "green":
                reasons.append("not_green")
        prior_end = ends.get(month_add(month, -36))
        if prior_end not in by_date:
            reasons.append("prior_month_end_missing")
        for m in last36:
            scheduled = calendar_by_month.get(m, [])
            if not scheduled or any(d not in by_date for d in scheduled):
                reasons.append("month_calendar_gap")
                break
            daily = []
            for d in scheduled:
                prev = by_date.get(dates[date_index[d] - 1]) if date_index[d] else None
                r = by_date[d]
                if not _valid_daily(r, prev):
                    reasons.append("invalid_month_price_identity")
                    break
                daily.append(float(r["close"]) / float(r["preclose"]) - 1)
            if reasons and reasons[-1] == "invalid_month_price_identity":
                break
            prior = ends.get(month_add(m, -1))
            if prior not in by_date:
                reasons.append("prior_month_end_missing")
                break
            endpoint = float(by_date[scheduled[-1]]["close"]) / float(by_date[prior]["close"]) - 1
            compounded = math.prod(1 + v for v in daily) - 1
            if abs(endpoint - compounded) > 1e-6:
                reasons.append("monthly_endpoint_product_disagreement")
                break
            month_returns.append(endpoint)
        f = [factors.get(m) for m in last36]
        if any(x is None for x in f):
            reasons.append("ch3_month_missing")
        high52 = math.nan
        if decision in date_index:
            ix = date_index[decision]
            window = dates[max(0, ix - 251) : ix + 1]
            if len(window) != 252 or any(d not in by_date for d in window):
                reasons.append("high52_window_gap")
            else:
                high52 = float(by_date[decision]["close"]) / max(
                    float(by_date[d]["close"]) for d in window
                )
        scores = {
            "ordinary": math.nan,
            "arithmetic_control": math.nan,
            "scaled_control": math.nan,
            "residual": math.nan,
            "alpha": math.nan,
            "residual_sd": math.nan,
        }
        if len(month_returns) == 36 and all(x is not None for x in f):
            try:
                scores = residual_scores(month_returns, f)
            except ValueError as exc:
                reasons.append(str(exc))
        output.append(
            {
                "code": code,
                "month": month,
                "decision_date": decision,
                "eligible": not reasons,
                "reasons": sorted(set(reasons)),
                "high52": high52,
                **scores,
            }
        )
        month = month_add(month, 1)
    return output


def select_arms(
    features: Sequence[Mapping], min_common: int = MIN_COMMON
) -> tuple[dict[str, list[str]], str]:
    """Rank before touching any future quote; stable code order breaks ties."""
    good = sorted((r for r in features if r["eligible"]), key=lambda r: r["code"])
    if len(good) < min_common:
        return {}, "common_eligible_below_minimum"
    k = math.ceil(len(good) * TOP_SHARE)
    scores = {
        key: {r["code"]: float(r[key]) for r in good}
        for key in ("ordinary", "arithmetic_control", "scaled_control", "residual", "high52")
    }
    ranks = {key: rank_midpercent(val) for key, val in scores.items()}
    scores["ordinary_high52"] = {
        code: (ranks["ordinary"][code] + ranks["high52"][code]) / 2 for code in scores["ordinary"]
    }
    arms = {"all_green": [r["code"] for r in good]}
    for name, values in scores.items():
        arms[name] = sorted(values, key=lambda code: (-values[code], code))[:k]
    return arms, ""


def future_outcome(
    by_date: Mapping[str, Mapping],
    calendar: Sequence[str],
    decision: str,
    entry: str,
    exit_day: str,
) -> dict:
    """Strict idealized next-open quote path, preserving unknown selections."""
    path = [d for d in calendar if decision <= d <= exit_day]
    result = {"return": None, "adverse": None, "opportunity": None, "reason": ""}
    if not path or entry not in path or exit_day not in path or any(d not in by_date for d in path):
        return {**result, "reason": "future_calendar_row_missing"}
    for i, day in enumerate(path[:-1]):
        previous = by_date[path[i - 1]] if i else None
        r = by_date[day]
        if not _valid_daily(r, previous):
            return {**result, "reason": "future_price_identity_invalid"}
        try:
            op, hi, lo, cl = (float(r[x]) for x in ("open", "high", "low", "close"))
            if not (0 < lo <= op <= hi and lo <= cl <= hi):
                return {**result, "reason": "future_ohlc_invalid"}
        except (KeyError, TypeError, ValueError):
            return {**result, "reason": "future_ohlc_invalid"}
    exit_quote = by_date[exit_day]
    try:
        exit_preclose = float(exit_quote["preclose"])
        previous_close = float(by_date[path[-2]]["close"])
        if (
            exit_quote["adjustflag"] != "2"
            or not math.isfinite(exit_preclose)
            or exit_preclose <= 0
            or abs(previous_close / exit_preclose - 1) > 1e-6
        ):
            return {**result, "reason": "exit_preclose_identity_invalid"}
    except (KeyError, TypeError, ValueError, IndexError):
        return {**result, "reason": "exit_preclose_identity_invalid"}
    for d in (entry, exit_day):
        r = by_date[d]
        if (
            r["tradestatus"] != "1"
            or float(r["volume"]) <= 0
            or not math.isfinite(float(r["open"]))
            or float(r["open"]) <= 0
        ):
            return {**result, "reason": "entry_or_exit_not_executable_quote"}
    entry_open = float(by_date[entry]["open"])
    holding = [d for d in path if entry <= d < exit_day]
    close_path = [float(by_date[d]["close"]) / entry_open - 1 for d in holding]
    exit_return = float(exit_quote["open"]) / entry_open - 1
    return {
        "return": exit_return,
        "adverse": min([0.0, exit_return, *close_path]),
        "opportunity": max([0.0, exit_return, *close_path]),
        "reason": "",
    }


def arm_month(codes: Sequence[str], outcomes: Mapping[str, Mapping]) -> dict:
    n = len(codes)
    if not n:
        raise ValueError("empty arm")
    known = [outcomes[c] for c in codes if outcomes[c]["return"] is not None]
    contribution = sum(float(x["return"]) for x in known) / n
    missing = (n - len(known)) / n
    return {
        "selected_n": n,
        "known_n": len(known),
        "mean_known_stock_return": mean(float(x["return"]) for x in known) if known else None,
        "unknown_weight": missing,
        "known_weighted_contribution": contribution,
        "strict_lower_bound": contribution - missing,
        "strict_upper_bound": None if missing else contribution,
        "scenario_minus100": contribution - missing,
        "scenario_zero": contribution,
        "scenario_plus100": contribution + missing,
        "complete_return": contribution if not missing else None,
        "mean_adverse": mean(x["adverse"] for x in known) if known else None,
        "mean_opportunity": mean(x["opportunity"] for x in known) if known else None,
    }


def drift_turnover(
    previous_codes: Sequence[str] | None,
    previous_outcomes: Mapping[str, Mapping] | None,
    new_codes: Sequence[str],
) -> dict:
    """Half-L1 rebalance with previous holdings drifted through realized returns."""
    if previous_codes is None:
        return {"half_l1": 1.0, "traded_gross": 1.0, "reason": "initial_purchase"}
    if previous_outcomes is None or any(
        previous_outcomes[c]["return"] is None for c in previous_codes
    ):
        return {"half_l1": None, "traded_gross": None, "reason": "unknown_previous_outcome"}
    prior = {
        c: (1 + float(previous_outcomes[c]["return"])) / len(previous_codes) for c in previous_codes
    }
    wealth = sum(prior.values())
    if wealth <= 0:
        return {"half_l1": None, "traded_gross": None, "reason": "nonpositive_previous_wealth"}
    prior = {c: v / wealth for c, v in prior.items()}
    target = {c: 1 / len(new_codes) for c in new_codes}
    half = sum(abs(target.get(c, 0) - prior.get(c, 0)) for c in set(target) | set(prior)) / 2
    return {"half_l1": half, "traded_gross": 2 * half, "reason": ""}


def costs(gross: float | None) -> dict[str, float | None]:
    return {
        f"cost_{bps}bps": None if gross is None else gross * bps / 10000 for bps in (10, 25, 50)
    }


def paired_summary(
    months: Sequence[str],
    arms: Mapping[str, Mapping[str, Mapping]],
    candidate: str,
    baseline: str = "ordinary",
) -> dict:
    paired = []
    for m in months:
        a = arms.get(m, {}).get(candidate, {}).get("complete_return")
        b = arms.get(m, {}).get(baseline, {}).get("complete_return")
        paired.append(None if a is None or b is None else float(a) - float(b))
    estimate = hac_mean(paired, lag=3)
    return {
        "candidate": candidate,
        "baseline": baseline,
        "calendar_months": len(months),
        "paired_months": estimate["n"],
        "minimum_36_months_for_inference": estimate["n"] >= 36,
        "mean_increment": estimate["mean"],
        "se": estimate["se"],
        "ci_low": estimate["ci_low"],
        "ci_high": estimate["ci_high"],
        "periods": {
            period: hac_mean([paired[i] for i, m in enumerate(months) if lo <= m <= hi], lag=3)
            for period, (lo, hi) in {
                "2016-2020": ("2016-01", "2020-12"),
                "2021-2025": ("2021-01", "2025-12"),
            }.items()
        },
    }
