"""Pure same-day qualification for the A-share breadth observation layer.

Qualification describes the input, not a trading signal or strategy threshold.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

_WINDOWS = (20, 50, 200)
_SOURCES = ("sh", "sz", "bj")
QFQ_CACHE_SCHEMA = 1
QFQ_SOURCE_REF = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"


def merge_kline_series(
    existing: Sequence[tuple[str, float]], incoming: Sequence[tuple[str, float]]
) -> tuple[list[tuple[str, float]], str | None]:
    """Keep old history; reject a short revised series instead of splicing scales."""
    old = {day: float(close) for day, close in existing}
    new = {day: float(close) for day, close in incoming}
    if len(old) != len(existing) or len(new) != len(incoming):
        return list(existing), "duplicate_date"
    if not new:
        return list(existing), None
    if any(not math.isfinite(x) or x <= 0 for x in (*old.values(), *new.values())):
        return list(existing), "invalid_close"
    if old:
        overlap = old.keys() & new.keys()
        if not overlap:
            return list(existing), "no_adjustment_anchor"
        if any(not math.isclose(old[d], new[d], rel_tol=1e-8, abs_tol=1e-6) for d in overlap):
            return list(existing), "adjustment_revision"
    merged = old | new
    return sorted(merged.items())[-2600:], None


def qualify_breadth(
    *,
    target_day: str,
    codes: Sequence[str],
    code_sources: Mapping[str, bool],
    series_by_symbol: Mapping[str, Sequence[tuple[str, float]]],
    revision_conflicts: int = 0,
) -> dict:
    """Compute each denominator using only members with a bar on target_day."""
    unique = list(dict.fromkeys(codes))
    source_status = {source: code_sources.get(source) is True for source in _SOURCES}
    source_complete = all(source_status.values()) and all(
        any(symbol.startswith(source) for symbol in unique) for source in _SOURCES
    )
    counts = {f"eligible{w}": 0 for w in _WINDOWS}
    above = {f"above{w}": 0 for w in _WINDOWS}
    same_day_available = 0
    for symbol in unique:
        series = series_by_symbol.get(symbol) or ()
        known = [row for row in series if row[0] <= target_day]
        if not known or known[-1][0] != target_day:
            continue
        try:
            closes = [Decimal(str(row[1])) for row in known]
        except InvalidOperation:
            continue
        if any(not close.is_finite() or close <= 0 for close in closes):
            continue
        same_day_available += 1
        for window in _WINDOWS:
            if len(closes) < window:
                continue
            counts[f"eligible{window}"] += 1
            if closes[-1] * window > sum(closes[-window:], Decimal(0)):
                above[f"above{window}"] += 1
    total = len(unique)
    missing = total - same_day_available
    reasons: list[str] = []
    if not source_complete:
        reasons.append("universe_sources_incomplete")
    if missing:
        reasons.append("same_day_bars_missing")
    if revision_conflicts:
        reasons.append("adjustment_revision_unresolved")
    for window in _WINDOWS:
        if counts[f"eligible{window}"] == 0:
            reasons.append(f"no_eligible_{window}")
        elif counts[f"eligible{window}"] < total:
            reasons.append(f"incomplete_history_{window}")
    status = "verified" if not reasons else "needs_check"
    result = {
        "target_day": target_day,
        "universe_total": total,
        "universe_qualification": "complete_sources" if source_complete else "partial_sources",
        "source_status": source_status,
        "same_day_available": same_day_available,
        "missing": missing,
        "same_day_coverage": same_day_available / total if total else 0.0,
        "calculation_status": (
            "verified_same_day_sample" if same_day_available else "no_same_day_sample"
        ),
        "status": status,
        "reasons": reasons,
        "revision_conflicts": revision_conflicts,
        **counts,
        **above,
    }
    for window in _WINDOWS:
        eligible = counts[f"eligible{window}"]
        result[f"missing{window}"] = total - eligible
        result[f"coverage{window}"] = eligible / total if total else 0.0
        result[f"ma{window}_pct"] = above[f"above{window}"] / eligible * 100 if eligible else None
    return result
