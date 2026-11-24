"""Source-only FIP research arithmetic. This is not an LEI trading rule.

All feature functions consume observations available by the decision close. An
outcome is deliberately absent from this module's monthly feature builder.
"""
from __future__ import annotations

import math
from datetime import date
from statistics import mean, stdev
from typing import Iterable, Mapping, Sequence

import numpy as np

from lei_signal.domain.rules_config import get_rule


SOURCE_FIELDS = (
    "date", "code", "open", "high", "low", "close", "preclose", "volume",
    "amount", "adjustflag", "tradestatus", "pctChg", "isST",
)


def month_add(month: str, offset: int) -> str:
    year, number = map(int, month.split("-"))
    index = year * 12 + number - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def fip_score(returns: Iterable[float], pret: float) -> float:
    """Sign(PRET) × (negative−positive)/observed, with traded zeros counted."""
    values = tuple(float(x) for x in returns)
    if not values or not math.isfinite(pret) or pret == 0 or any(not math.isfinite(x) for x in values):
        return math.nan
    return math.copysign(1.0, pret) * (sum(x < 0 for x in values) - sum(x > 0 for x in values)) / len(values)


def compounded_return(returns: Iterable[float]) -> float:
    values = tuple(returns)
    if not values or any(not math.isfinite(x) or x <= -1 for x in values):
        return math.nan
    return math.prod(1 + x for x in values) - 1


def rank_midpercent(values: Mapping[str, float]) -> dict[str, float]:
    """Ascending percentile ranks; equal values share their group's middle rank."""
    ordered = sorted((float(v), str(k)) for k, v in values.items() if math.isfinite(v))
    n = len(ordered)
    answer: dict[str, float] = {}
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        mid = ((i + 1) + j) / 2 / n
        answer.update((key, mid) for _, key in ordered[i:j])
        i = j
    return answer


def tied_quantile_bins(values: Mapping[str, float], bins: int = 5) -> dict[str, int]:
    if bins < 1:
        raise ValueError("bins must be positive")
    return {key: min(bins, max(1, math.ceil(rank * bins))) for key, rank in rank_midpercent(values).items()}


def hac_mean(values: Sequence[float | None], lag: int = 6) -> dict[str, float | int]:
    """Bartlett HAC mean; None retains its calendar position as a missing month."""
    axis = [float(v) if v is not None and math.isfinite(v) else math.nan for v in values]
    x = [v for v in axis if math.isfinite(v)]
    n = len(x)
    if n == 0:
        return {"n": 0, "mean": math.nan, "se": math.nan, "t": math.nan, "ci_low": math.nan, "ci_high": math.nan}
    center = mean(x)
    residual = [v - center if math.isfinite(v) else math.nan for v in axis]
    variance = sum(v * v for v in residual if math.isfinite(v)) / n
    for k in range(1, min(lag, len(axis) - 1) + 1):
        variance += 2 * (1 - k / (lag + 1)) * sum(
            residual[t] * residual[t-k] for t in range(k, len(axis))
            if math.isfinite(residual[t]) and math.isfinite(residual[t-k])
        ) / n
    se = math.sqrt(max(0.0, variance / n))
    return {"n": n, "mean": center, "se": se, "t": center / se if se > 0 else math.nan,
            "ci_low": center - 1.96 * se, "ci_high": center + 1.96 * se}


def qualify_source(payload: Mapping, code: str, calendar_dates: set[str]) -> tuple[list[dict], list[str]]:
    """Validate one saved provider response; any flag mismatch quarantines all rows."""
    failures: list[str] = []
    if payload.get("fields") != list(SOURCE_FIELDS) or payload.get("error_code") != "0":
        failures.append("schema_or_provider_error")
    raw = payload.get("data")
    if not isinstance(raw, list):
        return [], failures + ["data_not_list"]
    rows: list[dict] = []
    previous = ""
    for i, item in enumerate(raw):
        if not isinstance(item, list) or len(item) != len(SOURCE_FIELDS):
            failures.append(f"width:{i}")
            continue
        row = dict(zip(SOURCE_FIELDS, item))
        day = row["date"]
        try:
            date.fromisoformat(day)
            close = float(row["close"])
            preclose = float(row["preclose"]) if row["preclose"] else math.nan
        except (ValueError, TypeError):
            failures.append(f"bad_date_or_price:{i}")
            continue
        if row["code"] != code or day <= previous or day not in calendar_dates:
            failures.append(f"code_date_calendar:{i}")
        if row["adjustflag"] != "2":
            failures.append(f"returned_adjustflag:{i}")
        if row["tradestatus"] not in ("0", "1") or row["isST"] not in ("0", "1"):
            failures.append(f"bad_status:{i}")
        if not math.isfinite(close) or close <= 0:
            failures.append(f"bad_close:{i}")
        row["close_float"] = close
        row["preclose_float"] = preclose
        row["daily_return"] = close / preclose - 1 if row["tradestatus"] == "1" and math.isfinite(preclose) and preclose > 0 else math.nan
        try:
            row["pct_return"] = float(row["pctChg"]) / 100 if row["tradestatus"] == "1" else math.nan
        except (ValueError, TypeError):
            row["pct_return"] = math.nan
        if row["tradestatus"] == "1" and not math.isfinite(row["daily_return"]):
            failures.append(f"bad_traded_preclose:{i}")
        if row["tradestatus"] == "1" and not math.isfinite(row["pct_return"]):
            failures.append(f"bad_traded_pctchg:{i}")
        previous = day
        rows.append(row)
    return (rows if not failures else []), failures


def monthly_features(rows: Sequence[dict], trading_dates: Sequence[str], code: str,
                     first_month: str = "2014-12", last_month: str = "2025-06") -> list[dict]:
    """One row per decision month; no future observations are accessed.

    PRET endpoint is exact common month-end close(T−1)/close(T−12)−1.
    A separately named compounded observed-return diagnostic preserves any
    discrepancy caused by provider preclose or missing observations.
    """
    ends: dict[str, str] = {}
    for day in trading_dates:
        ends[day[:7]] = day
    by_day = {row["date"]: row for row in rows}
    date_index = {day: i for i, day in enumerate(trading_dates)}
    clock_rule = get_rule("clock_classifier")
    for row in rows:
        day = row["date"]
        previous = by_day.get(trading_dates[date_index[day]-1]) if day in date_index and date_index[day] > 0 else None
        row["adjacent_preclose_break"] = (
            previous is not None and row["tradestatus"] == "1"
            and math.isfinite(row["preclose_float"]) and row["preclose_float"] > 0
            and abs(previous["close_float"] / row["preclose_float"] - 1) > 1e-6
        )
        row["pct_return_disagreement"] = (
            row["tradestatus"] == "1" and math.isfinite(row["daily_return"])
            and math.isfinite(row["pct_return"])
            and abs(row["daily_return"] - row["pct_return"]) > 1e-6
        )
    output: list[dict] = []
    month = first_month
    while month <= last_month:
        decision = ends.get(month)
        start = ends.get(month_add(month, -12))
        finish = ends.get(month_add(month, -1))
        window_begin = month_add(month, -11) + "-01"
        scheduled = [day for day in trading_dates if window_begin <= day <= finish] if finish else []
        formation = [by_day[day] for day in scheduled if day in by_day]
        observed = [row for row in formation if row["tradestatus"] == "1" and math.isfinite(row["pct_return"])]
        returns = [row["pct_return"] for row in observed]
        reasons: list[str] = []
        if not rows:
            reasons.append("source_unqualified")
        if not decision or decision not in by_day:
            reasons.append("decision_quote_missing")
        elif by_day[decision]["tradestatus"] != "1" or by_day[decision]["isST"] != "0":
            reasons.append("decision_not_tradeable_or_st")
        if not start or not finish or start not in by_day or finish not in by_day:
            reasons.append("formation_endpoint_missing")
        if len(formation) != len(scheduled):
            reasons.append("formation_calendar_row_missing")
        if any(not math.isfinite(row["preclose_float"]) or row["preclose_float"] <= 0 for row in formation):
            reasons.append("formation_preclose_invalid")
        if any(row["adjacent_preclose_break"] for row in formation):
            reasons.append("formation_adjacent_preclose_break")
        if any(row["pct_return_disagreement"] for row in formation):
            reasons.append("formation_pct_return_disagreement")
        if len(returns) < 200:
            reasons.append("formation_traded_returns_below_200")
        pret = by_day[finish]["close_float"] / by_day[start]["close_float"] - 1 if start in by_day and finish in by_day else math.nan
        if not math.isfinite(pret) or pret == 0:
            reasons.append("formation_pret_zero_or_missing")
        close_preclose_returns = [row["daily_return"] for row in observed if math.isfinite(row["daily_return"])]
        compounded = compounded_return(close_preclose_returns)
        vol = stdev(close_preclose_returns) * math.sqrt(252) if len(close_preclose_returns) >= 2 else math.nan
        clock_days = trading_dates[max(0, date_index[decision] - 119):date_index[decision] + 1] if decision in date_index else []
        clock_complete = len(clock_days) == 120 and all(day in by_day for day in clock_days)
        s20, s60 = clock_slopes([by_day[day]["close_float"] for day in clock_days]) if clock_complete else (math.nan, math.nan)
        clock_ii = (
            s60 >= float(clock_rule.param("type2_min_s60"))
            and not (s60 > float(clock_rule.param("type1_min_s60"))
                     or (s20 >= float(clock_rule.param("type1_s20_multiple")) * s60
                         and s60 > float(clock_rule.param("type1_s60_floor"))))
        ) if math.isfinite(s20) and math.isfinite(s60) else None
        output.append({"code": code, "month": month, "decision_date": decision,
                       "formation_start_date": start, "formation_end_date": finish,
                       "scheduled_formation_days": len(scheduled), "observed_formation_rows": len(formation),
                       "observed_traded_returns": len(returns), "eligible": not reasons,
                       "reasons": reasons, "pret_endpoint": pret, "pret_compounded_observed": compounded,
                       "pret_difference": compounded - pret if math.isfinite(compounded) and math.isfinite(pret) else math.nan,
                       "fip_endpoint": fip_score(returns, pret),
                       "fip_compounded_observed": fip_score(returns, compounded),
                       "volatility_annualized": vol,
                       "clock_120_calendar_quotes_complete": clock_complete,
                       "clock_s20": s20, "clock_s60": s60, "clock_type_ii_proxy": clock_ii,
                       "pct_return_disagreements": sum(row["pct_return_disagreement"] for row in formation),
                       "adjacent_preclose_breaks": sum(row["adjacent_preclose_break"] for row in formation)})
        month = month_add(month, 1)
    return output


def clock_slopes(closes: Sequence[float]) -> tuple[float, float]:
    """Research copy of production's SMA20/60 annualized log slope math.

    Caller must supply a complete 120 scheduled-trading-day window; no
    production clock classification or rule thresholds are imported here.
    """
    rule = get_rule("clock_classifier")
    if (int(rule.param("window")) != 60 or int(rule.param("window_s20")) != 20
            or float(rule.param("annualization")) != 252):
        raise ValueError("clock slope ledger changed; review research copy before use")
    if len(closes) < 120 or any(not math.isfinite(x) or x <= 0 for x in closes[-120:]):
        return math.nan, math.nan
    q = closes[-120:]
    sma60_now, sma60_prior = mean(q[-60:]), mean(q[:60])
    sma20_now, sma20_prior = mean(q[-20:]), mean(q[-40:-20])
    return math.log(sma20_now / sma20_prior) / 20 * 252, math.log(sma60_now / sma60_prior) / 60 * 252


def future_endpoint_return(row: Mapping, by_day: Mapping[str, Mapping], month_ends: Mapping[str, str],
                           trading_dates: Sequence[str]) -> tuple[float, str]:
    """Exact T to T+6 quote, requiring a continuous qualified price path."""
    decision = row["decision_date"]
    end = month_ends.get(month_add(row["month"], 6))
    if not end:
        return math.nan, "future_calendar_endpoint_missing"
    scheduled = [day for day in trading_dates if decision <= day <= end]
    if not scheduled or len(scheduled) != sum(day in by_day for day in scheduled):
        return math.nan, "future_calendar_row_missing"
    start_quote, end_quote = by_day.get(decision), by_day.get(end)
    if not start_quote or not end_quote:
        return math.nan, "future_quote_missing"
    if start_quote["tradestatus"] != "1" or end_quote["tradestatus"] != "1":
        return math.nan, "future_endpoint_not_traded"
    for previous_day, day in zip(scheduled, scheduled[1:]):
        previous, current = by_day[previous_day], by_day[day]
        preclose = float(current["preclose_float"])
        close = float(current["close_float"])
        if not math.isfinite(preclose) or preclose <= 0 or not math.isfinite(close) or close <= 0:
            return math.nan, "future_path_price_invalid"
        if current["tradestatus"] == "1":
            if abs(float(previous["close_float"]) / preclose - 1) > 1e-6:
                return math.nan, "future_adjacent_preclose_break"
            if not math.isfinite(current["pct_return"]) or abs(close / preclose - 1 - current["pct_return"]) > 1e-6:
                return math.nan, "future_pct_return_disagreement"
    start, finish = float(start_quote["close_float"]), float(end_quote["close_float"])
    if not math.isfinite(start) or not math.isfinite(finish) or start <= 0 or finish <= 0:
        return math.nan, "future_endpoint_price_invalid"
    return finish / start - 1, ""


def group_stats(members: Sequence[Mapping], top_gainers: set[str] | None = None) -> dict:
    """Initial-stock equal weight; unknown outcomes keep their original weight."""
    n = len(members)
    known = [float(r["future_return"]) for r in members if math.isfinite(r["future_return"])]
    k = len(known)
    known_sum = sum(known)
    finite_mean = lambda key: mean(float(r[key]) for r in members if math.isfinite(r[key])) if any(math.isfinite(r[key]) for r in members) else math.nan
    selected = {r["code"] for r in members}
    return {
        "selected_n": n, "known_n": k, "unknown_n": n-k,
        "unknown_weight": (n-k)/n if n else math.nan,
        "known_weighted_contribution": known_sum/n if n else math.nan,
        "known_conditional_mean": known_sum/k if k else math.nan,
        "scenario_minus_100pct": (known_sum-(n-k))/n if n else math.nan,
        "scenario_zero": known_sum/n if n else math.nan,
        "scenario_plus_100pct": (known_sum+(n-k))/n if n else math.nan,
        "known_loss_probability": sum(v < 0 for v in known)/k if k else math.nan,
        "known_p10": float(np.quantile(known, .10)) if k else math.nan,
        "positive_contribution": sum(max(0, v) for v in known)/n if n else math.nan,
        "negative_contribution": sum(min(0, v) for v in known)/n if n else math.nan,
        "pret_mean": finite_mean("pret_endpoint"),
        "volatility_mean": finite_mean("volatility_annualized"),
        "top_gainers_retained": len(selected & top_gainers) if top_gainers is not None else None,
        "top_gainers_known_scope": len(top_gainers) if top_gainers is not None else None,
        "top_gainers_retention_fraction": len(selected & top_gainers)/len(top_gainers) if top_gainers else math.nan,
    }


def monthly_regression(rows: Sequence[Mapping], min_n: int = 30) -> dict:
    """Same complete known cases for nested positive-PRET regressions."""
    keys = ("pret_endpoint", "volatility_annualized", "clock_s20", "clock_s60", "fip_endpoint")
    past_eligible = [r for r in rows if r["pret_endpoint"] > 0
                     and all(math.isfinite(r[key]) for key in keys)]
    ranks = {key: rank_midpercent({r["code"]: r[key] for r in past_eligible}) for key in keys}
    eligible = [r for r in past_eligible if math.isfinite(r["future_return"])]
    if len(eligible) < min_n:
        return {"n": len(eligible), "past_rank_n": len(past_eligible), "reason": "below_minimum_30"}
    base = np.asarray([[1.0] + [ranks[key][r["code"]] for key in keys[:4]] for r in eligible])
    continuity = np.asarray([1 - ranks["fip_endpoint"][r["code"]] for r in eligible])
    added = np.column_stack((base, continuity))
    if np.linalg.matrix_rank(added) != added.shape[1]:
        return {"n": len(eligible), "past_rank_n": len(past_eligible), "reason": "rank_deficient"}
    y = np.asarray([r["future_return"] for r in eligible])
    beta_base = np.linalg.lstsq(base, y, rcond=None)[0]
    beta_added = np.linalg.lstsq(added, y, rcond=None)[0]
    total = float(np.sum((y-y.mean())**2))
    if total <= 0:
        return {"n": len(eligible), "past_rank_n": len(past_eligible), "reason": "constant_outcome"}
    r2_base = 1 - float(np.sum((y-base @ beta_base)**2))/total
    r2_added = 1 - float(np.sum((y-added @ beta_added)**2))/total
    return {"n": len(eligible), "past_rank_n": len(past_eligible), "reason": "", "continuity_coefficient": float(beta_added[-1]),
            "r2_base": r2_base, "r2_added": r2_added, "r2_increment": r2_added-r2_base}
