"""Dated descriptive statistics for the market observation panel."""

from __future__ import annotations

import calendar
from bisect import bisect_right
from collections import deque
from datetime import date, timedelta
from math import isfinite, log, sqrt
from statistics import fmean, pstdev, stdev

WINDOWS = {"daily": (252, 20, 756), "weekly": (156, 4, 260), "monthly": (60, 0, None)}


def month_end(year: int, month: int) -> date:
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, calendar.monthrange(year, month)[1])


def _point_date(value: str) -> date:
    if len(value) == 7:
        year, month = (int(part) for part in value.split("-"))
        if 1 <= month <= 12:
            return month_end(year, month)
    return date.fromisoformat(value)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        return None
    return float(value)


def _statistics(rows: list[dict], frequency: str) -> dict:
    window, moving, limit = WINDOWS[frequency]
    history: deque[float] = deque(maxlen=window)
    recent: deque[float | None] = deque(maxlen=moving)
    points = []
    previous = date.min
    count = 0
    for row in rows:
        day = _point_date(row["date"])
        if day <= previous:
            raise ValueError(f"Unordered or duplicate date: {day}")
        previous = day
        value = _number(row["value"])
        recent.append(value)
        ma20 = fmean(recent) if moving and len(recent) == moving and None not in recent else None
        if value is not None:
            count += 1
            history.append(value)
        mean = fmean(history) if len(history) == window and value is not None else None
        std = pstdev(history, mean) if mean is not None else None
        point = {"date": day.isoformat(), "value": value, "ma20": ma20, "mean": mean, "std": std}
        for factor, suffix in ((1.5, "1_5"), (2.0, "2_0")):
            delta = std * factor if std is not None else None
            point[f"band_upper_{suffix}"] = mean + delta if delta is not None else None
            point[f"band_lower_{suffix}"] = mean - delta if delta is not None else None
        points.append(point)
    latest = points[-1] if points else {}
    value, mean, std = (latest.get(key) for key in ("value", "mean", "std"))
    zscore = (value - mean) / std if std else None
    percentile = None
    if mean is not None:
        # Midrank over the other observations. A unique window minimum/maximum maps to 0/100.
        lower = sum(prior < value for prior in history)
        ties = sum(prior == value for prior in history) - 1
        percentile = 100 * (lower + ties / 2) / (window - 1)
    return {
        "points": points[-limit:] if limit else points,
        "window": window,
        "observations": count,
        "current_zscore": round(zscore, 1) if zscore is not None else None,
        "current_zscore_raw": zscore,
        "current_percentile": percentile,
    }


def build_card(card: dict) -> dict:
    frequency = card["frequency"]
    lines = [{**line, **_statistics(line["points"], frequency)} for line in card.get("lines", [])]
    return {**card, **_statistics(card["points"], frequency), "lines": lines}


def volatility(prices: list[dict]) -> tuple[list[dict], list[dict]]:
    """Annualized sample volatility of daily log returns. Missing closes break both windows."""
    returns: deque[float | None] = deque(maxlen=60)
    short, long = [], []
    previous = None
    for row in prices:
        close = _number(row["value"])
        returns.append(
            log(close / previous) if close and previous and close > 0 and previous > 0 else None
        )
        previous = close
        for length, output in ((20, short), (60, long)):
            samples = list(returns)[-length:]
            value = (
                stdev(samples) * sqrt(252) * 100
                if len(samples) == length and None not in samples
                else None
            )
            output.append({"date": row["date"], "value": value})
    return short, long


def _survey_window(rows: list[tuple[date, date, float]], day: date) -> float | None:
    values = [
        (survey_day, value)
        for survey_day, known, value in rows
        if day - timedelta(days=59) <= survey_day <= known <= day
    ]
    if len(values) < 6 or max(survey_day for survey_day, _ in values) < day - timedelta(days=21):
        return None
    return fmean(value for _, value in values)


def nowcast(
    margin: list[dict], aaii: list[dict], naaim: list[dict], official_end: date, as_of: date
) -> list[dict]:
    """Monthly proxy using complete inputs and strictly prior month baselines.

    Margin data are eligible at the end of the following month, a conservative
    approximation when FINRA's historical publication timestamps are unavailable.
    Survey inputs use their known/estimated release dates, and their 60-day means
    are computed over the last 60 calendar days of survey weeks. The reference
    has up to 60 prior months and needs at least 24 readings per component.
    """
    margin_values = {
        _point_date(row["date"]): value
        for row in margin
        if (value := _number(row["value"])) is not None and value > 0
    }
    known_margin = []
    for month, value in sorted(margin_values.items()):
        previous = margin_values.get(month_end(month.year - 1, month.month))
        if previous is not None:
            known_margin.append((month_end(month.year, month.month + 1), value / previous - 1))
    margin_dates = [released for released, _ in known_margin]

    surveys = [
        [
            (date.fromisoformat(row["date"]), date.fromisoformat(row["available_at"][:10]), value)
            for row in rows
            if row.get("available_at") and (value := _number(row["value"])) is not None
        ]
        for rows in (aaii, naaim)
    ]
    if as_of <= official_end:
        return []
    baselines = [deque(maxlen=60) for _ in range(3)]
    output = []
    cursor = month_end(official_end.year - 5, official_end.month + 1)
    while True:
        day = min(cursor, as_of)
        idx = bisect_right(margin_dates, day) - 1
        # A long reporting gap should not turn the last disclosure into a live input.
        margin_yoy = (
            known_margin[idx][1] if idx >= 0 and (day - margin_dates[idx]).days <= 62 else None
        )
        components = [margin_yoy, *(_survey_window(rows, day) for rows in surveys)]
        scores = []
        for baseline, value in zip(baselines, components, strict=True):
            valid = [sample for sample in baseline if sample is not None]
            if value is not None and len(valid) >= 24:
                mean = fmean(valid)
                std = pstdev(valid, mean)
                if std > 0:
                    scores.append((value - mean) / std)
            baseline.append(value)
        if day > official_end:
            output.append(
                {"date": day.isoformat(), "value": fmean(scores) if len(scores) == 3 else None}
            )
        if day == as_of:
            break
        cursor = month_end(cursor.year, cursor.month + 1)
    return output
