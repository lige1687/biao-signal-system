"""Describe drawdown and relative-wealth episodes in two supplied NAV paths."""

from datetime import date
import math
from typing import Any, Iterable

_TOL = 1e-12


def _validate(rows: Iterable[dict[str, Any]], name: str) -> tuple[list[date], list[float]]:
    if isinstance(rows, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of row dictionaries")
    try:
        items = list(rows)
    except TypeError as exc:
        raise ValueError(f"{name} must be an iterable of row dictionaries") from exc
    dates: list[date] = []
    values: list[float] = []
    for index, row in enumerate(items):
        if not isinstance(row, dict) or "date" not in row or "nav" not in row:
            raise ValueError(f"{name}[{index}] must contain date and nav")
        raw_date = row["date"]
        if not isinstance(raw_date, str):
            raise ValueError(f"{name}[{index}].date must be YYYY-MM-DD")
        try:
            parsed = date.fromisoformat(raw_date)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name}[{index}].date must be YYYY-MM-DD") from exc
        if parsed.isoformat() != raw_date:
            raise ValueError(f"{name}[{index}].date must be YYYY-MM-DD")
        raw_nav = row["nav"]
        if isinstance(raw_nav, bool) or not isinstance(raw_nav, (int, float)):
            raise ValueError(f"{name}[{index}].nav must be a positive finite number")
        try:
            nav = float(raw_nav)
        except (OverflowError, ValueError) as exc:
            raise ValueError(f"{name}[{index}].nav must be a positive finite number") from exc
        if not math.isfinite(nav) or nav <= 0:
            raise ValueError(f"{name}[{index}].nav must be a positive finite number")
        dates.append(parsed)
        values.append(nav)
    if len(dates) < 2:
        raise ValueError(f"{name} must contain at least two rows")
    if any(b <= a for a, b in zip(dates, dates[1:])):
        raise ValueError(f"{name} dates must be unique and strictly ascending")
    return dates, values


def _episodes(dates: list[date], series: list[float], threshold: float = 1.0) -> list[dict[str, Any]]:
    """Find continuous intervals below a threshold, resetting at each recovery."""
    result = []
    active = False
    start_index = 0
    worst = 0.0
    for i, value in enumerate(series):
        below = value < threshold - _TOL
        if active:
            if not below:
                result.append(_episode(dates, start_index, i, True, worst))
                active = False
            else:
                worst = min(worst, value / threshold - 1.0)
        elif below:
            active = True
            start_index = i
            worst = value / threshold - 1.0
    if active:
        result.append(_episode(dates, start_index, len(series) - 1, False, worst))
    return result


def _episode(dates: list[date], start: int, end: int, recovered: bool, depth: float) -> dict[str, Any]:
    anchor = start - 1
    return {
        "anchor_date": dates[anchor].isoformat(),
        "first_below_date": dates[start].isoformat(),
        "end_date": dates[end].isoformat(),
        "recovered": recovered,
        "elapsed_calendar_days": (dates[end] - dates[anchor]).days,
        "observations_below": end - start + (0 if recovered else 1),
        "depth_pct": depth * 100.0,
    }


def _summarize(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [episode for episode in episodes if episode["recovered"]]
    ongoing = next((episode for episode in episodes if not episode["recovered"]), None)
    longest = max(completed, key=lambda e: (e["elapsed_calendar_days"], e["observations_below"])) if completed else None
    return {
        "episodes": episodes,
        "longest_completed": longest,
        "ongoing": ongoing,
        "max_depth_pct": min((e["depth_pct"] for e in episodes), default=0.0),
    }


def compare_nav_paths(
    baseline_rows: Iterable[dict[str, Any]],
    candidate_rows: Iterable[dict[str, Any]],
    *,
    cashflow_adjusted: bool,
    calendar: str,
) -> dict[str, Any]:
    """Compare two NAV sequences using only supplied, cashflow-adjusted values.

    The caller must assert cashflow adjustment. No annualization, simulation,
    resampling, or NAV modification is performed. A fixed 1e-12 tolerance is
    used only to absorb floating point representation noise around equality.
    """
    if cashflow_adjusted is not True:
        raise ValueError("cashflow_adjusted must be True")
    if calendar not in {"calendar_day", "observed_dates"}:
        raise ValueError("calendar must be calendar_day or observed_dates")
    base_dates, base_nav = _validate(baseline_rows, "baseline_rows")
    cand_dates, cand_nav = _validate(candidate_rows, "candidate_rows")
    if base_dates != cand_dates:
        raise ValueError("baseline_rows and candidate_rows dates must match exactly")
    dates = base_dates
    if calendar == "calendar_day" and any((b - a).days != 1 for a, b in zip(dates, dates[1:])):
        raise ValueError("calendar_day requires every consecutive calendar date")

    base = _finite_positive_path([v / base_nav[0] for v in base_nav], "normalized baseline")
    cand = _finite_positive_path([v / cand_nav[0] for v in cand_nav], "normalized candidate")
    relative = _finite_positive_path([c / b for b, c in zip(base, cand)], "relative wealth")
    relative[0] = 1.0
    def drawdown_path(path: list[float]) -> list[float]:
        peak = path[0]
        out = []
        for value in path:
            peak = max(peak, value)
            out.append(value / peak)
        return _finite_positive_path(out, "drawdown path")

    baseline_drawdown_path = drawdown_path(base)
    candidate_drawdown_path = drawdown_path(cand)
    relative_peak = drawdown_path(relative)
    end_relative_wealth_change_pct = (relative[-1] - 1.0) * 100.0
    if not math.isfinite(end_relative_wealth_change_pct):
        raise ValueError("end relative wealth change percentage must be finite")
    return {
        "date_range": {"start": dates[0].isoformat(), "end": dates[-1].isoformat()},
        "sample_count": len(dates),
        "calendar": calendar,
        "calendar_description": "输入包含连续自然日净值记录；不保证每日有新报价或可以成交" if calendar == "calendar_day" else "仅按输入中共同观察日期计数，间隔可不连续",
        "tolerance": {"value": _TOL, "purpose": "仅处理浮点数相等误差，不是研究阈值"},
        "baseline_drawdowns": _summarize(_episodes(dates, baseline_drawdown_path)),
        "candidate_drawdowns": _summarize(_episodes(dates, candidate_drawdown_path)),
        "relative_underperformance": _summarize(_episodes(dates, relative)),
        "relative_peak_pullbacks": _summarize(_episodes(dates, relative_peak)),
        "end_relative_wealth_change_pct": end_relative_wealth_change_pct,
    }


def _finite_positive_path(values: list[float], name: str) -> list[float]:
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError(f"{name} contains a non-positive or non-finite derived value")
    return values
