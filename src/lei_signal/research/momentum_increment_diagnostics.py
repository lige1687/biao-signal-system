"""Pure diagnostics for fixed-calendar momentum research, never trading signals.

Inputs are caller-qualified adjusted prices, formation pools, and matured labels.
This module performs no I/O and never uses outcomes to form scores or groups.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence

import numpy as np

from lei_signal.research.fip import hac_mean, month_add


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) else None


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for i in order[start:end]:
            result[i] = rank
        start = end
    return result


def _correlation(x: Sequence[float], y: Sequence[float]) -> float | None:
    mx, my = statistics.mean(x), statistics.mean(y)
    xx = sum((v - mx) ** 2 for v in x)
    yy = sum((v - my) ** 2 for v in y)
    if xx <= 1e-12 or yy <= 1e-12:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / math.sqrt(xx * yy)


def daily_scores(calendar: Sequence[str], prices: Mapping[str, object]) -> dict[str, dict]:
    """Compute each date independently on the supplied complete exchange calendar.

    A price absent from the mapping stays a missing trading observation; it never
    shifts the N-day endpoint. Nonpositive prices invalidate the affected window.
    """
    axis = list(calendar)
    if not axis or axis != sorted(set(axis)):
        raise ValueError("calendar must be nonempty, sorted and unique")
    values = [_number(prices.get(day)) for day in axis]
    result = {}

    def interval(end: int, start: int) -> tuple[list[float] | None, str | None]:
        if start < 0:
            return None, "insufficient_calendar"
        segment = values[start : end + 1]
        if any(v is None for v in segment):
            return None, "missing_price"
        if any(v <= 0 for v in segment):
            return None, "nonpositive_price"
        return segment, None

    for i, day in enumerate(axis):
        row: dict = {"scores": {}, "reasons": {}}
        for n in (20, 60, 120, 252):
            segment, reason = interval(i, i - n)
            key = f"mom{n}"
            row["scores"][key] = segment[-1] / segment[0] - 1 if segment else None
            row["reasons"][key] = reason
        for k in (20, 21):
            segment, reason = interval(i - k, i - 252)
            key = f"skip{k}"
            row["scores"][key] = segment[-1] / segment[0] - 1 if segment else None
            row["reasons"][key] = reason
        segment, reason = interval(i, i - 60)
        vol = (
            statistics.stdev([math.log(b / a) for a, b in zip(segment, segment[1:], strict=False)])
            if segment
            else None
        )
        row["scores"]["vol60"] = vol
        row["reasons"]["vol60"] = reason
        skip = row["scores"]["skip21"]
        row["scores"]["scaled_skip21"] = (
            skip / vol if skip is not None and vol and vol > 0 else None
        )
        if skip is None:
            scaled_reason = row["reasons"]["skip21"]
        elif vol is None:
            scaled_reason = reason
        elif vol == 0:
            scaled_reason = "zero_volatility"
        else:
            scaled_reason = None
        row["reasons"]["scaled_skip21"] = scaled_reason
        result[day] = row
    return result


def rank_mix(features: Mapping[str, Mapping[str, object]]) -> dict[str, dict]:
    """Average three same-pool average-tie percentile ranks at formation."""
    keys = ("mom20", "mom60", "mom120")
    codes = sorted(features)
    complete = [
        code for code in codes if all(_number(features[code].get(key)) is not None for key in keys)
    ]
    ranks: dict[str, dict[str, float]] = {code: {} for code in codes}
    for key in keys:
        if not complete:
            continue
        ranked = _ranks([_number(features[code][key]) for code in complete])
        for code, rank in zip(complete, ranked, strict=True):
            ranks[code][key] = (rank - 0.5) / len(complete)
    return {
        code: {
            "rank_components": ranks[code],
            "mix": statistics.mean(ranks[code].values()) if len(ranks[code]) == 3 else None,
            "mom60": _number(features[code].get("mom60")),
        }
        for code in codes
    }


def common_score_rows(rows: Sequence[Mapping], scores: Sequence[str]) -> list[Mapping]:
    """Lock a comparison pool using formation eligibility and scores only.

    The caller must qualify formation-day identity, quote, and trading status.
    Unknown future labels never remove a row from this common pool.
    """
    if not scores or len(set(scores)) != len(scores):
        raise ValueError("scores must be nonempty and unique")
    return [row for row in rows if row.get("formation_eligible") is True
            and all(_number(row.get(score)) is not None for score in scores)]


def rank_diagnostic(rows: Sequence[Mapping], score: str, label: str = "return") -> dict:
    """Spearman rank association on known pairs, with missing-label coverage."""
    eligible = [(row, _number(row.get(score))) for row in rows]
    eligible = [(row, value) for row, value in eligible if value is not None]
    known = [
        (value, outcome)
        for row, value in eligible
        if (outcome := _number(row.get(label))) is not None
    ]
    n = len(known)
    result = {
        "eligible": len(eligible),
        "known": n,
        "unknown": len(eligible) - n,
        "tie_fraction": None,
        "spearman": None,
        "reason": None,
    }
    if n:
        result["tie_fraction"] = 1 - len({value for value, _ in known}) / n
    if n < 3:
        result["reason"] = "fewer_than_three_known_pairs"
        return result
    correlation = _correlation(_ranks([x for x, _ in known]), _ranks([y for _, y in known]))
    result["spearman"] = correlation
    result["reason"] = None if correlation is not None else "constant_rank"
    return result


def partial_rank_diagnostic(
    rows: Sequence[Mapping], score: str, controls: Sequence[str], label: str = "return"
) -> dict:
    """Correlation of rank residuals after fixed known-control projection."""
    if not controls or len(set(controls)) != len(controls) or score in controls:
        raise ValueError("controls must be unique and separate from score")
    common = []
    for row in rows:
        values = [_number(row.get(key)) for key in (score, label, *controls)]
        if all(value is not None for value in values):
            common.append(values)
    n, p = len(common), len(controls)
    result = {
        "eligible": len(rows),
        "known_common": n,
        "unknown": len(rows) - n,
        "controls": list(controls),
        "effective_rank": None,
        "degrees_of_freedom": None,
        "partial_rank_correlation": None,
        "reason": None,
    }
    if n < max(10, p + 3):
        result["reason"] = "insufficient_common_pairs"
        return result
    matrix = np.asarray(common, dtype=float)
    x = np.asarray(_ranks(matrix[:, 0].tolist()), dtype=float)
    y = np.asarray(_ranks(matrix[:, 1].tolist()), dtype=float)
    design = np.column_stack(
        [
            np.ones(n),
            *(np.asarray(_ranks(matrix[:, j].tolist()), dtype=float) for j in range(2, p + 2)),
        ]
    )
    xfit, _, rank, _ = np.linalg.lstsq(design, x, rcond=None)
    yfit, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    result["effective_rank"] = int(rank)
    result["degrees_of_freedom"] = n - int(rank)
    if rank < p + 1:
        result["reason"] = "dependent_controls"
        return result
    association = _correlation((x - design @ xfit).tolist(), (y - design @ yfit).tolist())
    result["partial_rank_correlation"] = association
    result["reason"] = None if association is not None else "degenerate_residual"
    return result


def month_summary(months: Sequence[str], by_month: Mapping[str, object]) -> dict:
    """HAC mean over an explicit continuous month axis; gaps retain positions."""
    axis = list(months)
    if (
        not axis
        or axis != sorted(set(axis))
        or any(month_add(a, 1) != b for a, b in zip(axis, axis[1:], strict=False))
    ):
        raise ValueError("months must be continuous, sorted and unique")
    if any(month not in axis for month in by_month):
        raise ValueError("value outside month axis")
    values = [_number(by_month.get(month)) for month in axis]
    raw = hac_mean(values, lag=3)
    enough = raw["n"] >= 2
    return {
        "months": axis,
        "values": values,
        "valid_count": raw["n"],
        "mean": _number(raw["mean"]),
        "se": _number(raw["se"]) if enough else None,
        "ci_low": _number(raw["ci_low"]) if enough else None,
        "ci_high": _number(raw["ci_high"]) if enough else None,
        "reason": None if enough else "fewer_than_two_valid_months",
        "lag": 3,
    }


def groups(rows: Sequence[Mapping], score: str, count: int, label: str = "return") -> dict:
    """Near-equal ascending groups; code resolves score ties only at boundaries."""
    if count < 1 or len(rows) < count:
        raise ValueError("group count exceeds eligible names")
    codes = [row.get("code") for row in rows]
    if any(not isinstance(code, str) or not code for code in codes) or len(set(codes)) != len(
        codes
    ):
        raise ValueError("codes must be unique nonempty strings")
    if any(_number(row.get(score)) is None for row in rows):
        raise ValueError("all formation scores must be finite")
    ordered = sorted(rows, key=lambda row: (_number(row[score]), row["code"]))
    quotient, remainder = divmod(len(rows), count)
    answer = []
    cursor = 0
    for i in range(count):
        size = quotient + (i < remainder)
        chosen = ordered[cursor : cursor + size]
        cursor += size
        values = [_number(row.get(label)) for row in chosen]
        known = [value for value in values if value is not None]
        upper = _number(chosen[-1][score])
        boundary_tie = i < count - 1 and upper == _number(ordered[cursor][score])
        answer.append(
            {
                "group": i + 1,
                "codes": [row["code"] for row in chosen],
                "weights": {row["code"]: 1 / size for row in chosen},
                "boundary_tie": boundary_tie,
                "known": len(known),
                "unknown_weight": (size - len(known)) / size,
                "known_contribution": sum(known) / size,
                "complete_return": sum(known) / size if len(known) == size else None,
            }
        )
    constant = len({_number(row[score]) for row in rows}) == 1
    return {"groups": answer, "rank": rank_diagnostic(rows, score, label),
            "sorting_effect_evaluable": not constant,
            "reason": "constant_formation_score" if constant else None}


def monthly_sharpe(
    months: Sequence[str], returns: Sequence[object], risk_free: Sequence[object] | None = None
) -> dict:
    """Saved monthly account-return statistic; RF inputs are monthly decimals."""
    axis = list(months)
    if (
        not axis
        or axis != sorted(set(axis))
        or any(month_add(a, 1) != b for a, b in zip(axis, axis[1:], strict=False))
    ):
        raise ValueError("months must be a continuous sorted unique monthly axis")
    if len(returns) != len(axis) or (risk_free is not None and len(risk_free) != len(axis)):
        raise ValueError("return and RF lengths must match months")
    rf_assumption = "zero_assumed" if risk_free is None else "matched_monthly_decimal"
    vals = [_number(value) for value in returns]
    rf = [0.0] * len(axis) if risk_free is None else [_number(value) for value in risk_free]
    result = {
        "months": len(axis),
        "risk_free_assumption": rf_assumption,
        "annualization": "sqrt12_not_serial_correlation_corrected",
        "sharpe": None,
        "reason": None,
    }
    if any(value is None for value in vals + rf):
        result["reason"] = "missing_monthly_value"
    elif len(axis) < 2:
        result["reason"] = "fewer_than_two_months"
    else:
        excess = [a - b for a, b in zip(vals, rf, strict=True)]
        sd = statistics.stdev(excess)
        if sd <= 0:
            result["reason"] = "zero_excess_volatility"
        else:
            result["sharpe"] = statistics.mean(excess) / sd * math.sqrt(12)
            result["monthly_excess_mean"] = statistics.mean(excess)
            result["monthly_excess_sd"] = sd
    return result
