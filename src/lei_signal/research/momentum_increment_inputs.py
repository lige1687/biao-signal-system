"""In-memory adapters for the bounded CN and six-ETF momentum question.

Callers qualify and hash the saved sources before passing decoded rows here.
No file, provider, account or market-effect operation occurs in this module.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date

from lei_signal.research.fip import month_add
from lei_signal.research.high52_revalidation import adapt_back_adjusted
from lei_signal.research.momentum_increment_diagnostics import daily_scores

ETF_SYMBOLS = (
    "510300.SS",
    "510050.SS",
    "510500.SS",
    "512100.SS",
    "159915.SZ",
    "588000.SS",
)
SCORE_KEYS = ("mom20", "mom60", "mom120", "mom252", "skip20", "skip21", "vol60", "scaled_skip21")
LABEL_KEYS = ("return", "adverse", "opportunity", "adverse_flat_as_unknown_return")


def _finite(value: object) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _calendar(calendar: Sequence[str]) -> list[str]:
    axis = list(calendar)
    if not axis or axis != sorted(set(axis)):
        raise ValueError("full exchange calendar must be nonempty, sorted and unique")
    for day in axis:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("calendar contains a non-ISO date")
    return axis


def exchange_trading_days(payload: Mapping) -> list[str]:
    """Read the saved official-calendar shape without inventing missing dates."""
    if (
        payload.get("authority") != "exchange_official"
        or payload.get("market") != "CN"
        or payload.get("months_failed")
        or not isinstance(payload.get("days"), Mapping)
    ):
        raise ValueError("qualified CN exchange calendar required")
    days = payload["days"]
    if not days or any(type(row.get("is_trading_day")) is not bool for row in days.values()):
        raise ValueError("calendar day flag missing or invalid")
    _calendar(sorted(days))
    return _calendar(sorted(day for day, row in days.items() if row["is_trading_day"]))


def cn_symbol_inputs(
    code: str,
    calendar: Sequence[str],
    daily_payload: Mapping,
    action_payload: Mapping,
    monthly_rows: Sequence[Mapping],
) -> dict:
    """Join old formation facts to a fore-adjusted full-calendar price series.

    The saved old green flag and future labels are read only. A source break
    becomes a missing price at its exact calendar date, invalidating any score
    window crossing it; a later valid observation never closes that gap.
    """
    axis = _calendar(calendar)
    adapted = adapt_back_adjusted(
        daily_payload, action_payload, code, axis, factor_field="foreAdjustFactor"
    )
    broken = set(adapted["break_dates"])
    by_day = {row["date"]: row for row in adapted["rows"]}
    prices = {day: by_day[day]["close"] for day in axis if day in by_day and day not in broken}
    score_by_day = daily_scores(axis, prices)
    end_by_month = {day[:7]: day for day in axis}
    first_by_month = {}
    for day in axis:
        first_by_month.setdefault(day[:7], day)
    records = []
    seen = set()
    for original in monthly_rows:
        if original.get("code") != code:
            continue
        decision = original.get("decision_date")
        month = original.get("month")
        if not isinstance(month, str) or decision != end_by_month.get(month):
            raise ValueError("old formation date is not the supplied exchange month end")
        holding_month = month_add(month, 1)
        following_month = month_add(month, 2)
        expected_entry = first_by_month.get(holding_month)
        expected_exit = first_by_month.get(following_month)
        if expected_entry is None or expected_exit is None:
            raise ValueError("exchange calendar lacks future label month")
        if (
            original.get("holding_month") != holding_month
            or original.get("entry_date") != expected_entry
            or original.get("exit_date") != expected_exit
        ):
            raise ValueError("old future label dates disagree with exchange calendar")
        if decision in seen:
            raise ValueError("duplicate old code/formation date")
        seen.add(decision)
        green = original.get("green")
        if not isinstance(green, bool):
            raise ValueError("old green flag must be known at formation")
        source = by_day.get(decision)
        formation_close = _finite(prices.get(decision))
        volume = _finite(source.get("volume")) if source is not None else None
        reasons = []
        if source is None:
            reasons.append("formation_quote_missing")
        if decision in broken:
            reasons.append("formation_source_break")
        if formation_close is None or formation_close <= 0:
            reasons.append("formation_positive_close_missing")
        if source is not None and (
            source.get("tradestatus") != "1"
            or source.get("isST") != "0"
            or volume is None
            or volume <= 0
        ):
            reasons.append("formation_not_traded_or_st")
        records.append(
            {
                "code": code,
                "month": month,
                "decision_date": decision,
                "green": green,
                "formation_eligible": not reasons,
                "formation_reasons": reasons,
                "scores": score_by_day[decision]["scores"],
                "score_reasons": score_by_day[decision]["reasons"],
                "future_labels": {key: _finite(original.get(key)) for key in LABEL_KEYS},
                "label_basis": (
                    "saved_next_month_first_open_to_following_month_first_open_adjusted_quote"
                ),
                "holding_month": holding_month,
                "label_dates": {"entry_date": expected_entry, "exit_date": expected_exit},
            }
        )
    return {
        "code": code,
        "calendar": axis,
        "prices": prices,
        "source_break_dates": sorted(broken),
        "price_basis": adapted["research_price_basis"],
        "records": sorted(records, key=lambda row: row["decision_date"]),
    }


def _economic_prices(
    calendar: Sequence[str], warm_rows: Sequence[Mapping], formal_rows: Sequence[Mapping]
) -> dict[str, float]:
    """Keep warm and formal rows on the same exchange axis without compression."""
    allowed = set(calendar)
    warm_dates = [row.get("date") for row in warm_rows]
    formal_dates = [row.get("date") for row in formal_rows]
    if warm_dates != sorted(set(warm_dates)) or formal_dates != sorted(set(formal_dates)):
        raise ValueError("warm/formal symbol dates must each be sorted and unique")
    if warm_dates and formal_dates and warm_dates[-1] >= formal_dates[0]:
        raise ValueError("warm/formal periods overlap or reverse")
    prices = {}
    seen = set()
    for row in (*warm_rows, *formal_rows):
        day = row["date"]
        if day not in allowed or day in seen:
            raise ValueError("ETF quote outside fixed exchange calendar or duplicated")
        seen.add(day)
        price = _finite(row.get("economic_index"))
        if price is not None:
            if price <= 0:
                raise ValueError("ETF economic index must be positive where present")
            prices[day] = price
    return prices


def etf_monthly_inputs(
    calendar: Sequence[str],
    warm_by_symbol: Mapping[str, Sequence[Mapping]],
    formal_by_symbol: Mapping[str, Sequence[Mapping]],
    first_month: str,
    last_month: str,
) -> list[dict]:
    """Six fixed ETFs, month-end formation, and exact +21-session outcomes.

    ``factor_qualified`` depends only on formation scores. Outcomes are
    separate: unknown future economic prices do not drop or reweight an ETF.
    """
    axis = _calendar(calendar)
    if set(warm_by_symbol) != set(ETF_SYMBOLS) or set(formal_by_symbol) != set(ETF_SYMBOLS):
        raise ValueError("all and only the fixed six ETF sources are required")
    if first_month > last_month:
        raise ValueError("formation month range reversed")
    by_code = {
        code: _economic_prices(axis, warm_by_symbol[code], formal_by_symbol[code])
        for code in ETF_SYMBOLS
    }
    scores = {code: daily_scores(axis, by_code[code]) for code in ETF_SYMBOLS}
    month_ends = {day[:7]: day for day in axis}
    positions = {day: i for i, day in enumerate(axis)}
    result = []
    months = [first_month]
    while months[-1] < last_month:
        months.append(month_add(months[-1], 1))
    if months[-1] != last_month or any(month not in month_ends for month in months):
        raise ValueError("formation month missing from fixed exchange calendar")
    for month in months:
        decision = month_ends[month]
        i = positions[decision]
        target = axis[i + 21] if i + 21 < len(axis) else None
        records = []
        for code in ETF_SYMBOLS:
            values = by_code[code]
            score = scores[code][decision]
            if target is None:
                outcome, outcome_reason = None, "target_outside_calendar"
            elif any(day not in values for day in axis[i : i + 22]):
                outcome, outcome_reason = None, "future_calendar_price_gap"
            else:
                outcome = values[target] / values[decision] - 1
                outcome_reason = None
            records.append(
                {
                    "code": code,
                    "scores": score["scores"],
                    "score_reasons": score["reasons"],
                    "future_return": outcome,
                    "future_reason": outcome_reason,
                }
            )
        factor_qualified = {
            key: all(row["scores"][key] is not None for row in records) for key in SCORE_KEYS
        }
        result.append(
            {
                "month": month,
                "decision_date": decision,
                "target_date": target,
                "rows": records,
                "factor_qualified": factor_qualified,
                "mix_qualified": all(factor_qualified[key] for key in ("mom20", "mom60", "mom120")),
                "group_count": 3,
                "top_count": 2,
                "price_basis": "saved_economic_index_not_executable_account",
                "label_basis": "formation_close_to_fixed_plus21_exchange_sessions_economic_index",
                "green_subset_status": "not_evaluated_no_qualified_historical_green_flags",
            }
        )
    return result
