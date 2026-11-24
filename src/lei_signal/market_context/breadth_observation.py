"""Pure breadth reading aids; descriptive only, separate from trading classifiers.

Bands use the last 1260 valid observations, including the current reading, with
252 observations required. Quantiles use linear interpolation and percentile
uses the same <= convention as breadth.rolling_percentile_at. Five-record
changes retain the original date axis; missing values are never forward-filled.
This module neither qualifies historical constituents nor reads index prices.
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right, insort
from collections import deque
from collections.abc import Mapping, Sequence
from datetime import date
from numbers import Real
from typing import Any

_LOOKBACK = 1260
_MIN_OBSERVATIONS = 252
_PERIODS = (20, 50, 200)
_MARKET_LIMITS = {"CN_ALL_A": (20.0, 80.0), "SP500": (15.0, 85.0)}


def _percentage(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) and 0 <= number <= 100 else None


def _valid_dates(history: Sequence[Mapping[str, Any]]) -> bool:
    previous = ""
    for row in history:
        if not isinstance(row, Mapping):
            return False
        day = row.get("date")
        if not isinstance(day, str) or len(day) != 10 or day <= previous:
            return False
        try:
            if date.fromisoformat(day).isoformat() != day:
                return False
        except ValueError:
            return False
        previous = day
    return True


def _quantile(ordered: list[float], q: float) -> float:
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _event(position: str, previous: str) -> str:
    if "unknown" in (position, previous):
        return "unknown"
    if position == "high":
        return "stay_high" if previous == "high" else "enter_high"
    if position == "low":
        return "stay_low" if previous == "low" else "enter_low"
    if previous == "high":
        return "exit_high"
    if previous == "low":
        return "exit_low"
    return "none"


def _horizon_history(values: list[float | None]) -> list[dict[str, Any]]:
    queue: deque[float] = deque()
    ordered: list[float] = []
    result: list[dict[str, Any]] = []
    previous_position = "unknown"
    for i, value in enumerate(values):
        if value is not None:
            if len(queue) == _LOOKBACK:
                ordered.pop(bisect_left(ordered, queue.popleft()))
            queue.append(value)
            insort(ordered, value)
        sample_count = len(queue)
        delta = None
        if value is not None and i >= 5 and values[i - 5] is not None:
            delta = value - values[i - 5]
        status = ("missing" if value is None else
                  "ready" if sample_count >= _MIN_OBSERVATIONS else "insufficient")
        row = {
            "lower": None, "median": None, "upper": None, "percentile": None,
            "delta_5": delta, "sample_count": sample_count, "status": status,
            "position": "unknown", "event": "unknown",
        }
        if status == "ready":
            lower, median, upper = (_quantile(ordered, q) for q in (.1, .5, .9))
            position = ("flat" if lower == upper == value else "low" if value <= lower else
                        "high" if value >= upper else "middle")
            row.update({
                "lower": lower, "median": median, "upper": upper,
                "percentile": bisect_right(ordered, value) / sample_count * 100.0,
                "position": position, "event": _event(position, previous_position),
            })
        previous_position = row["position"]
        result.append(row)
    return result


def _state(
    values: dict[int, list[float | None]],
    horizons: dict[str, dict[str, Any]],
    i: int,
    limits: tuple[float, float],
) -> dict[str, str]:
    b20, b50, b200 = (values[period][i] for period in _PERIODS)
    d20, d50 = (horizons[str(period)]["delta_5"] for period in (20, 50))
    if any(value is None for value in (b20, b50, d20, d50)):
        return {"code": "unknown", "label": "参与状态待观察", "tone": "unknown",
                "summary": "20/50日宽度或5条记录前的比较值不足，暂不能描述参与变化。"}

    low, high = limits
    prior = [(values[20][j], values[50][j]) for j in range(max(0, i - 5), i)]
    recent_low = any(a is not None and b is not None and a <= low and b <= low
                     for a, b in prior)
    recent_high = any(a is not None and b is not None and a >= high and b >= high
                      for a, b in prior)
    if d20 > 0 and d50 > 0:
        if recent_low:
            code, label, tone = "recovering", "低位修复", "supportive"
            detail = f"此前5条记录曾有20/50日宽度同时不高于{low:g}%，目前均回升。"
        elif b20 >= 50 and b50 >= 50 and b200 is not None and b200 >= 50:
            code, label, tone = "expanding", "上涨参与延续", "supportive"
            detail = "20/50日宽度均回升，三个周期均至少有半数股票站在均线上方。"
        else:
            code, label, tone = "improving", "参与回升", "supportive"
            detail = "20/50日宽度均回升，三个周期尚未同时支持广泛参与。"
    elif d20 < 0 and d50 < 0:
        if recent_high:
            code, label, tone = "retreating", "高位回落", "caution"
            detail = f"此前5条记录曾有20/50日宽度同时不低于{high:g}%，目前均回落。"
        elif b200 is not None and b200 < 50:
            code, label, tone = "weakening", "弱势参与延续", "caution"
            detail = "20/50日宽度均回落，200日均线上方股票仍不足半数。"
        else:
            code, label, tone = "contracting", "上涨参与收缩", "caution"
            detail = "20/50日均线上方股票的比例均减少。"
    elif d20 == 0 and d50 == 0:
        code, label, tone = "flat", "参与暂稳", "neutral"
        detail = "20/50日宽度与5条记录前相同。"
    else:
        code, label, tone = "mixed", "短期分歧", "neutral"
        detail = "20/50日宽度的变化方向不一致。"
    changes = f"较5条记录前分别变化{d20:+.1f}、{d50:+.1f}个百分点。"
    long_note = "200日宽度资料不足，长期参与情况未知。" if b200 is None else ""
    return {"code": code, "label": label, "tone": tone,
            "summary": detail + changes + long_note}


def build_breadth_observation(
    history: Sequence[Mapping[str, Any]], market_id: str,
    *, tail_observations: int | None = None,
) -> dict[str, Any]:
    """Return reading metadata without mutating history or changing trading rules.

    Invalid date axes produce a local explicit error, leaving the original API
    history untouched. A missing current reading never inherits yesterday's
    bands or position. Missing observations still occupy their original dates
    for delta_5 and prevent invented crossings between adjacent rows.
    tail_observations limits only transport, after the full history calculation.
    """
    result: dict[str, Any] = {
        "method_version": "breadth.observation@1.0.0",
        "lookback_observations": _LOOKBACK, "min_observations": _MIN_OBSERVATIONS,
        "lower_quantile": .1, "upper_quantile": .9, "includes_current": True,
        "total_observations": len(history) if isinstance(history, Sequence) else 0,
        "returned_observations": 0,
        "history": [], "latest": None,
    }
    if market_id not in _MARKET_LIMITS:
        return {**result, "error": "unsupported_market"}
    if not isinstance(history, Sequence) or not _valid_dates(history):
        return {**result, "error": "invalid_date_axis"}
    values = {period: [_percentage(row.get(f"breadth_{period}")) for row in history]
              for period in _PERIODS}
    readings = {period: _horizon_history(values[period]) for period in _PERIODS}
    rows = []
    for i, source in enumerate(history):
        horizons = {str(period): readings[period][i] for period in _PERIODS}
        rows.append({"date": source["date"], "horizons": horizons,
                     "state": _state(values, horizons, i, _MARKET_LIMITS[market_id])})
    result["history"] = (rows if tail_observations is None else
                         rows[max(0, len(rows) - tail_observations):])
    result["returned_observations"] = len(result["history"])
    result["latest"] = rows[-1] if rows else None
    return result
