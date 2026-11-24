"""Month-end green-stock selection research; no trading-rule or outcome fitting.

Prices are the qualified ``adapt_back_adjusted(..., factor_field='foreAdjustFactor')``
research series. Feature rows use only observations through their decision close.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from statistics import stdev

import numpy as np

from lei_signal.research.fip import month_add


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _month_ends(calendar: Sequence[str]) -> dict[str, str]:
    return {day[:7]: day for day in calendar}


def monthly_features(
    adapted: Mapping, calendar: Sequence[str], code: str, first_month: str, last_month: str
) -> list[dict]:
    """T close, exact T-1/T-12 endpoints and 60 log returns on market dates.

    A missing row or adapter break resets the EMA seed; no observation is
    compressed over a market date. Every T-11..T calendar day must be present.
    """
    basis = adapted.get("research_price_basis")
    if basis not in {
        "raw_ohlc_times_effective_foreAdjustFactor",
        "vendor_adjusted_with_verified_single_code_overlay",
    }:
        raise ValueError("features require an approved adjusted-price basis")
    dates = list(calendar)
    if dates != sorted(set(dates)):
        raise ValueError("calendar must be sorted and unique")
    allowed_dates = set(dates)
    rows = {row["date"]: row for row in adapted["rows"] if row["date"] in allowed_dates}
    breaks = set(adapted["break_dates"])
    ends = _month_ends(dates)
    by_month: dict[str, list[str]] = defaultdict(list)
    for day in dates:
        by_month[day[:7]].append(day)
    positions = {day: index for index, day in enumerate(dates)}
    closes: list[float | None] = []
    ema: list[float | None] = []
    segment: list[float] = []
    previous_ema: float | None = None
    for day in dates:
        close = _finite(rows[day].get("close")) if day in rows else None
        if day in breaks or close is None or close <= 0:
            closes.append(None)
            ema.append(None)
            segment = []
            previous_ema = None
            continue
        closes.append(close)
        segment.append(close)
        if len(segment) == 20:
            previous_ema = sum(segment) / 20
        elif len(segment) > 20:
            previous_ema = 2 / 21 * close + 19 / 21 * previous_ema
        ema.append(previous_ema)
    output = []
    month = first_month
    while month <= last_month:
        decision = ends.get(month)
        prior = ends.get(month_add(month, -1))
        anchor = ends.get(month_add(month, -12))
        reasons: list[str] = []
        required_months = [month_add(month, offset) for offset in range(-11, 1)]
        window = [day for m in required_months for day in by_month.get(m, ())]
        if any(not by_month.get(m) for m in required_months):
            reasons.append("month_calendar_missing")
        if any(day not in rows or closes[positions[day]] is None for day in window):
            reasons.append("month_calendar_gap_or_invalid_close")
        if any(day in breaks for day in window):
            reasons.append("adjusted_price_break_in_window")
        if decision is None or decision not in rows:
            reasons.append("decision_quote_missing")
        if (
            anchor is None
            or anchor not in rows
            or closes[positions[anchor]] is None
            or anchor in breaks
        ):
            reasons.append("anchor_month_end_missing_or_break")
        if prior is None or prior not in rows or closes[positions[prior]] is None:
            reasons.append("prior_month_end_missing")
        green: bool | None = None
        momentum = hot = vol60 = None
        if decision in positions and decision in rows:
            ix = positions[decision]
            current = closes[ix]
            old20 = closes[ix - 20] if ix >= 20 else None
            if current is not None and old20 is not None and ema[ix] is not None:
                green = current > ema[ix] and current > old20
            if green is False:
                reasons.append("not_green")
            elif green is None:
                reasons.append("green_unknown")
            if current is not None and prior in positions and closes[positions[prior]] is not None:
                hot = current / closes[positions[prior]] - 1
            if prior in positions and anchor in positions:
                prior_close, anchor_close = closes[positions[prior]], closes[positions[anchor]]
                if prior_close is not None and anchor_close is not None:
                    momentum = prior_close / anchor_close - 1
            if ix >= 60 and all(v is not None for v in closes[ix - 60 : ix + 1]):
                log_returns = [math.log(closes[j] / closes[j - 1]) for j in range(ix - 59, ix + 1)]
                vol60 = stdev(log_returns)
        if momentum is None:
            reasons.append("momentum_endpoint_missing")
        if hot is None:
            reasons.append("recent_month_endpoint_missing")
        if vol60 is None:
            reasons.append("vol60_window_gap")
        if decision in rows:
            row = rows[decision]
            volume = _finite(row.get("volume"))
            if (
                row.get("tradestatus") != "1"
                or row.get("isST") != "0"
                or volume is None
                or volume <= 0
            ):
                reasons.append("decision_not_traded_or_st")
        output.append(
            {
                "code": code,
                "month": month,
                "decision_date": decision,
                "eligible": not reasons,
                "reasons": sorted(set(reasons)),
                "green": green,
                "price_basis": basis,
                "momentum": momentum,
                "hot": hot,
                "vol60": vol60,
            }
        )
        month = month_add(month, 1)
    return output


def select_weights(features: Sequence[Mapping], min_common: int = 30) -> dict:
    """Five equal-count momentum groups; cool/hot half within each group."""
    good = [row for row in features if row["eligible"]]
    if len(good) < min_common:
        return {
            "weights": {},
            "groups": {},
            "scores": {},
            "concentration_hhi": {},
            "eligible_n": len(good),
            "reason": "common_eligible_below_minimum",
        }
    if len({row["code"] for row in good}) != len(good):
        raise ValueError("duplicate eligible code")
    if any(
        any(_finite(row.get(key)) is None for key in ("momentum", "hot", "vol60")) for row in good
    ):
        raise ValueError("eligible feature has nonfinite score")
    ranked = sorted(good, key=lambda row: (float(row["momentum"]), row["code"]))
    bins = np.array_split(np.arange(len(ranked)), 5)
    n = len(ranked)
    groups: dict[str, int] = {}
    weights = {name: {} for name in ("all_green", "cool", "hot", "ordinary")}
    for row in ranked:
        weights["all_green"][row["code"]] = 1 / n
    for group_id, indices in enumerate(bins, 1):
        members = [ranked[int(i)] for i in indices]
        for row in members:
            groups[row["code"]] = group_id
        k = len(members) // 2
        if not k:
            continue
        by_hot = sorted(members, key=lambda row: (float(row["hot"]), row["code"]))
        member_weight = (len(members) / n) / k
        for row in by_hot[:k]:
            weights["cool"][row["code"]] = member_weight
        for row in by_hot[-k:]:
            weights["hot"][row["code"]] = member_weight
    ordinary = sorted(good, key=lambda row: (-float(row["momentum"]), row["code"]))[
        : math.ceil(n * 0.30)
    ]
    weights["ordinary"] = {row["code"]: 1 / len(ordinary) for row in ordinary}
    scores = {
        row["code"]: {key: float(row[key]) for key in ("momentum", "hot", "vol60")} for row in good
    }
    concentration = {name: sum(w * w for w in arm.values()) for name, arm in weights.items()}
    return {
        "weights": weights,
        "groups": groups,
        "scores": scores,
        "concentration_hhi": concentration,
        "eligible_n": n,
        "reason": "",
    }


def _checked_weights(weights: Mapping[str, float]) -> dict[str, float]:
    if not weights:
        raise ValueError("empty weights")
    values = {code: float(weight) for code, weight in weights.items()}
    if any(not math.isfinite(weight) or weight < 0 for weight in values.values()):
        raise ValueError("invalid weight")
    if not math.isclose(sum(values.values()), 1, rel_tol=0, abs_tol=1e-9):
        raise ValueError("weights must sum to one")
    return values


def weighted_month(
    weights: Mapping[str, float], outcomes: Mapping[str, Mapping], field: str = "return"
) -> dict:
    """Preserve unknown original weight; never renormalize known names."""
    values = _checked_weights(weights)

    def result_for(name: str) -> tuple[float, float, float | None]:
        known = 0.0
        unknown = 0.0
        for code, weight in values.items():
            raw = outcomes.get(code, {}).get(name)
            number = _finite(raw)
            if number is None:
                unknown += weight
            else:
                known += weight * number
        return known, unknown, known if unknown == 0 else None

    contribution, unknown, complete = result_for(field)
    adverse, adverse_unknown, adverse_complete = result_for("adverse")
    opportunity, opportunity_unknown, opportunity_complete = result_for("opportunity")
    return {
        "selected_n": len(values),
        "known_weighted_contribution": contribution,
        "unknown_weight": unknown,
        "complete_return": complete,
        "known_weighted_adverse": adverse,
        "unknown_adverse_weight": adverse_unknown,
        "mean_adverse": adverse_complete,
        "known_weighted_opportunity": opportunity,
        "unknown_opportunity_weight": opportunity_unknown,
        "mean_opportunity": opportunity_complete,
    }


def weighted_turnover(
    previous_weights: Mapping[str, float] | None,
    previous_outcomes: Mapping[str, Mapping] | None,
    new_weights: Mapping[str, float],
) -> dict:
    """Drift prior weights by observed returns, then gross L1 rebalance."""
    target = _checked_weights(new_weights)
    if previous_weights is None:
        return {"traded_gross": 1.0, "half_l1": 1.0, "reason": "initial_purchase"}
    previous = _checked_weights(previous_weights)
    if previous_outcomes is None:
        return {"traded_gross": None, "half_l1": None, "reason": "unknown_previous_outcome"}
    drifted = {}
    for code, weight in previous.items():
        ret = _finite(previous_outcomes.get(code, {}).get("return"))
        if ret is None:
            return {"traded_gross": None, "half_l1": None, "reason": "unknown_previous_outcome"}
        drifted[code] = weight * (1 + ret)
    wealth = sum(drifted.values())
    if wealth <= 0 or any(value < 0 for value in drifted.values()):
        return {"traded_gross": None, "half_l1": None, "reason": "nonpositive_previous_wealth"}
    drifted = {code: value / wealth for code, value in drifted.items()}
    gross = sum(
        abs(target.get(code, 0) - drifted.get(code, 0)) for code in set(target) | set(drifted)
    )
    return {"traded_gross": gross, "half_l1": gross / 2, "reason": ""}


def decomposition(
    candidate_weights: Mapping[str, float],
    baseline_weights: Mapping[str, float],
    outcomes: Mapping[str, Mapping],
    field: str = "return",
) -> dict:
    """Explain explicit candidate-minus-baseline weights without filling gaps."""
    candidate, baseline = _checked_weights(candidate_weights), _checked_weights(baseline_weights)
    pieces = {key: 0.0 for key in ("added_gain", "added_loss", "avoided_loss", "foregone_gain")}
    unknown_absolute_weight = 0.0
    for code in set(candidate) | set(baseline):
        delta = candidate.get(code, 0) - baseline.get(code, 0)
        number = _finite(outcomes.get(code, {}).get(field))
        if number is None:
            unknown_absolute_weight += abs(delta)
        elif delta > 0 and number >= 0:
            pieces["added_gain"] += delta * number
        elif delta > 0:
            pieces["added_loss"] += delta * number
        elif number < 0:
            pieces["avoided_loss"] += delta * number
        else:
            pieces["foregone_gain"] += delta * number
    return {
        **pieces,
        "known_increment": sum(pieces.values()),
        "unknown_absolute_weight": unknown_absolute_weight,
        "complete_increment": sum(pieces.values()) if unknown_absolute_weight == 0 else None,
    }


def _rank(values: Sequence[float]) -> np.ndarray:
    """Average ranks for exact ties, ascending 1..N."""
    array = np.asarray(values, dtype=float)
    order = np.argsort(array, kind="stable")
    ranks = np.empty(len(array), dtype=float)
    i = 0
    while i < len(array):
        j = i + 1
        while j < len(array) and array[order[j]] == array[order[i]]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2
        i = j
    return ranks


def _residual_correlation(
    x: np.ndarray, y: np.ndarray, controls: np.ndarray
) -> tuple[float | None, str]:
    if len(x) <= controls.shape[1] or np.linalg.matrix_rank(controls) < controls.shape[1]:
        return None, "rank_deficient"
    xres = x - controls @ np.linalg.lstsq(controls, x, rcond=None)[0]
    yres = y - controls @ np.linalg.lstsq(controls, y, rcond=None)[0]
    if np.linalg.norm(xres) < 1e-9 or np.linalg.norm(yres) < 1e-9:
        return None, "rank_deficient"
    return float(np.corrcoef(xres, yres)[0, 1]), ""


def partial_rank_correlations(
    features: Sequence[Mapping], outcomes: Mapping[str, Mapping], groups: Mapping[str, int]
) -> dict:
    """Same-month association on common known names; groups stay pre-outcome frozen.

    Full control uses intercept, momentum rank, vol60 rank and groups 2..5.
    This is descriptive association, not a fitted prediction model.
    """
    common = sorted(
        (
            row
            for row in features
            if row.get("eligible")
            and row["code"] in groups
            and all(_finite(row.get(key)) is not None for key in ("hot", "momentum", "vol60"))
            and _finite(outcomes.get(row["code"], {}).get("return")) is not None
        ),
        key=lambda row: row["code"],
    )
    n = len(common)
    answer = {
        "n": n,
        "raw": None,
        "momentum": None,
        "full": None,
        "raw_reason": "",
        "momentum_reason": "",
        "full_reason": "",
    }
    if n < 3:
        return {
            **answer,
            "raw_reason": "insufficient_common",
            "momentum_reason": "insufficient_common",
            "full_reason": "insufficient_common",
        }
    x = _rank([-float(row["hot"]) for row in common])
    y = _rank([float(outcomes[row["code"]]["return"]) for row in common])
    m = _rank([float(row["momentum"]) for row in common])
    v = _rank([float(row["vol60"]) for row in common])
    ones = np.ones(n)
    dummies = np.column_stack(
        [[float(groups[row["code"]] == g) for row in common] for g in range(2, 6)]
    )
    for key, controls in (
        ("raw", ones[:, None]),
        ("momentum", np.column_stack((ones, m))),
        ("full", np.column_stack((ones, m, v, dummies))),
    ):
        answer[key], answer[f"{key}_reason"] = _residual_correlation(x, y, controls)
    return answer
