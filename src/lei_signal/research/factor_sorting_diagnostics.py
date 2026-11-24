"""Pure, retrospective sorting diagnostics for a fixed qualified monthly pool.

Formation membership never consults a future result. All returns are adjusted
quote proxies, not executable portfolio returns or a prediction model.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence

from lei_signal.research.fip import hac_mean, month_add

FACTORS = ("momentum", "high52", "cool", "lowvol")
UNIVERSES = ("all_qualified", "green_only")
PERIODS = {
    "early": ("2015-01", "2018-12"),
    "middle": ("2019-01", "2021-12"),
    "late": ("2022-01", "2025-12"),
}
MIN_NAMES = 30


def _finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def _green(value):
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError("green must be known at formation")


def _score(row, factor):
    if factor == "cool":
        return -row["hot"]
    if factor == "lowvol":
        return -row["vol60"]
    return row[factor]


def _bins(rows, factor):
    """Near-equal quintiles; exact score ties are resolved by code."""
    ordered = sorted(rows, key=lambda row: (_score(row, factor), row["code"]))
    quotient, remainder = divmod(len(ordered), 5)
    answer = []
    cursor = 0
    for index in range(5):
        size = quotient + (index < remainder)
        answer.append(ordered[cursor : cursor + size])
        cursor += size
    return answer


def _average(values):
    return sum(values) / len(values) if values else None


def _ranks(values):
    ordered = sorted(enumerate(values), key=lambda pair: (pair[1], pair[0]))
    result = [0.0] * len(values)
    cursor = 0
    while cursor < len(values):
        stop = cursor + 1
        while stop < len(values) and ordered[stop][1] == ordered[cursor][1]:
            stop += 1
        rank = (cursor + 1 + stop) / 2
        for original, _ in ordered[cursor:stop]:
            result[original] = rank
        cursor = stop
    return result


def _spearman(rows, factor):
    known = sorted((row for row in rows if row["return"] is not None), key=lambda r: r["code"])
    n = len(known)
    result = {"spearman": None, "spearman_known_pairs": n, "spearman_reason": None}
    if n < 3:
        result["spearman_reason"] = "fewer_than_three_known_pairs"
        return result
    x = _ranks([_score(row, factor) for row in known])
    y = _ranks([row["return"] for row in known])
    mx, my = sum(x) / n, sum(y) / n
    xx = sum((value - mx) ** 2 for value in x)
    yy = sum((value - my) ** 2 for value in y)
    if xx <= 0 or yy <= 0:
        result["spearman_reason"] = "constant_rank"
        return result
    result["spearman"] = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / math.sqrt(
        xx * yy
    )
    return result


def _weighted(rows, weights, field):
    """Retain every formation weight, including weights with unknown results."""
    known_n = 0
    known_weight = 0.0
    contribution = 0.0
    for row in rows:
        weight = weights.get(row["code"], 0.0)
        if weight == 0:
            continue
        value = row[field]
        if value is not None:
            known_n += 1
            known_weight += weight
            contribution += weight * value
    unknown_weight = sum(weights.values()) - known_weight
    if abs(unknown_weight) < 1e-12:
        unknown_weight = 0.0
    return {
        "known": known_n,
        "unknown_weight": unknown_weight,
        "known_contribution": contribution,
        "known_conditional_mean": contribution / known_weight if known_weight > 0 else None,
        "complete": contribution if unknown_weight == 0 else None,
    }


def _exposure(rows, weights):
    return {
        key: sum(weights[row["code"]] * row[key] for row in rows if row["code"] in weights)
        for key in ("momentum", "high52", "hot", "vol60")
    }


def _group(rows, group_id, pool_n, factor):
    n = len(rows)
    weights = {row["code"]: 1 / n for row in rows}
    ret = _weighted(rows, weights, "return")
    adverse = _weighted(rows, weights, "adverse")
    sensitivity = _weighted(rows, weights, "adverse_flat_as_unknown_return")
    known_returns = [row["return"] for row in rows if row["return"] is not None]
    return {
        "group": group_id,
        "codes": [row["code"] for row in rows],
        "n": n,
        "pool_weight": n / pool_n,
        "known": ret["known"],
        "unknown_weight": ret["unknown_weight"],
        "unknown_pool_weight": (n - ret["known"]) / pool_n,
        "complete_return": ret["complete"],
        "known_contribution": ret["known_contribution"] * n / pool_n,
        "known_sum_over_n": ret["known_contribution"],
        "known_conditional_mean": ret["known_conditional_mean"],
        "complete_adverse": adverse["complete"],
        "known_adverse_sum_over_n": adverse["known_contribution"],
        "unknown_adverse_weight": adverse["unknown_weight"],
        "complete_restrictive_return": sensitivity["complete"],
        "unknown_restrictive_weight": sensitivity["unknown_weight"],
        "loss_frequency_known": sum(value < 0 for value in known_returns) / len(known_returns)
        if known_returns
        else None,
        "loss_frequency_complete": sum(value < 0 for value in known_returns) / n
        if len(known_returns) == n
        else None,
        "mean_oriented_score": _average([_score(row, factor) for row in rows]),
        "mean_exposure": _exposure(rows, weights),
    }


def _difference(candidate, baseline, rows, field):
    """Explicit candidate-minus-baseline weights; no result-based reweighting."""
    by_code = {row["code"]: row for row in rows}
    known = 0.0
    unknown_absolute_weight = 0.0
    for code in candidate.keys() | baseline.keys():
        delta = candidate.get(code, 0.0) - baseline.get(code, 0.0)
        value = by_code[code][field]
        if value is None:
            unknown_absolute_weight += abs(delta)
        else:
            known += delta * value
    if unknown_absolute_weight < 1e-12:
        unknown_absolute_weight = 0.0
    return {
        "known_increment": known,
        "unknown_absolute_weight": unknown_absolute_weight,
        "complete_increment": known if unknown_absolute_weight == 0 else None,
    }


def _stratified_weights(strata, factor, total_n):
    weights = {}
    chosen = []
    for segment in strata:
        picks = sorted(segment, key=lambda row: (-_score(row, factor), row["code"]))[
            : len(segment) // 2
        ]
        weight = len(segment) / total_n / len(picks)
        for row in picks:
            weights[row["code"]] = weight
            chosen.append(row["code"])
    return weights, chosen


def _increment_row(month, holding_month, label, candidate, baseline, rows):
    candidate_ret = _weighted(rows, candidate, "return")
    baseline_ret = _weighted(rows, baseline, "return")
    ret = _difference(candidate, baseline, rows, "return")
    adverse = _difference(candidate, baseline, rows, "adverse")
    restrictive = _difference(candidate, baseline, rows, "adverse_flat_as_unknown_return")
    # Main comparisons require the same complete green pool for all methods.
    pool_return_complete = all(row["return"] is not None for row in rows)
    pool_adverse_complete = all(row["adverse"] is not None for row in rows)
    pool_restrictive_complete = all(
        row["adverse_flat_as_unknown_return"] is not None for row in rows
    )
    return {
        "month": month,
        "holding_month": holding_month,
        "comparison": label,
        "n": len(rows),
        "candidate_n": len(candidate),
        "candidate_codes": sorted(candidate),
        "candidate_weights": dict(sorted(candidate.items())),
        "baseline_n": len(baseline),
        "baseline_weights": dict(sorted(baseline.items())),
        "candidate_known_contribution": candidate_ret["known_contribution"],
        "candidate_unknown_weight": candidate_ret["unknown_weight"],
        "baseline_known_contribution": baseline_ret["known_contribution"],
        "baseline_unknown_weight": baseline_ret["unknown_weight"],
        "known_subset_difference": (
            candidate_ret["known_conditional_mean"] - baseline_ret["known_conditional_mean"]
            if candidate_ret["known_conditional_mean"] is not None
            and baseline_ret["known_conditional_mean"] is not None
            else None
        ),
        "known_increment": ret["known_increment"],
        "unknown_absolute_weight": ret["unknown_absolute_weight"],
        "complete_return_increment": ret["complete_increment"] if pool_return_complete else None,
        "known_adverse_increment": adverse["known_increment"],
        "unknown_adverse_absolute_weight": adverse["unknown_absolute_weight"],
        "complete_adverse_increment": adverse["complete_increment"]
        if pool_adverse_complete
        else None,
        "complete_restrictive_return_increment": restrictive["complete_increment"]
        if pool_restrictive_complete
        else None,
        "unknown_restrictive_absolute_weight": restrictive["unknown_absolute_weight"],
        "candidate_exposure": _exposure(rows, candidate),
        "baseline_exposure": _exposure(rows, baseline),
    }


def _summaries(months, monthly, increments):
    by_sort = {(row["month"], row["universe"], row["factor"]): row for row in monthly}
    by_increment = {(row["month"], row["comparison"]): row for row in increments}
    definitions = {"all": None, **PERIODS}
    result = {"sorts": [], "increments": []}
    sort_metrics = (
        "g5_minus_pool_return",
        "g5_minus_g1_return",
        "g5_adverse_minus_pool",
        "g5_minus_pool_restrictive_return",
        "g5_minus_g1_restrictive_return",
        "g5_loss_frequency",
        "winner_capture_complete",
        "spearman",
        "g5_entry_fraction",
    )
    increment_metrics = (
        "complete_return_increment",
        "complete_adverse_increment",
        "complete_restrictive_return_increment",
    )
    comparisons = (
        "high52_vs_green",
        "cool_vs_green",
        "lowvol_vs_green",
        "high52_vs_momentum_top20",
        "cool_vs_lowvol",
    )
    for period, bounds in definitions.items():
        period_months = [
            month
            for month in months
            if bounds is None or bounds[0] <= month_add(month, 1) <= bounds[1]
        ]
        for universe in UNIVERSES:
            for factor in FACTORS:
                series = [by_sort[(month, universe, factor)] for month in period_months]
                result["sorts"].append(
                    {
                        "period": period,
                        "universe": universe,
                        "factor": factor,
                        "calendar_months": len(period_months),
                        "qualified_months": sum(row["qualified"] for row in series),
                        "metrics": {
                            key: _clean(hac_mean([row[key] for row in series], lag=3))
                            for key in sort_metrics
                        },
                    }
                )
        for comparison in comparisons:
            series = [by_increment.get((month, comparison)) for month in period_months]
            result["increments"].append(
                {
                    "period": period,
                    "comparison": comparison,
                    "calendar_months": len(period_months),
                    "qualified_months": sum(row is not None for row in series),
                    "metrics": {
                        key: _clean(hac_mean([row[key] if row else None for row in series], lag=3))
                        for key in increment_metrics
                    },
                }
            )
    return result


def analyze(rows: Sequence[Mapping], months: Sequence[str]) -> dict:
    """Evaluate fixed formation sorting, with a complete month axis and gaps.

    The caller must supply past-qualified names with all four finite features.
    Only return, adverse, and restrictive return may be unknown. No I/O occurs.
    """
    axis = list(months)
    if not axis or axis != sorted(set(axis)):
        raise ValueError("months must be nonempty, sorted and unique")
    for month in axis:
        if len(month) != 7 or month_add(month, 0) != month:
            raise ValueError("invalid formation month")
    by_month = defaultdict(list)
    seen = set()
    for original in rows:
        code, month = original.get("code"), original.get("month")
        if not isinstance(code, str) or not code or month not in axis:
            raise ValueError("row code or month absent from supplied formation axis")
        if (month, code) in seen:
            raise ValueError("duplicate code in formation month")
        seen.add((month, code))
        if original.get("holding_month") != month_add(month, 1):
            raise ValueError("holding month does not follow formation month")
        row = {
            "code": code,
            "month": month,
            "holding_month": original["holding_month"],
            "green": _green(original.get("green")),
        }
        for key in ("momentum", "high52", "hot", "vol60"):
            row[key] = _finite(original.get(key))
            if row[key] is None:
                raise ValueError(f"non-finite past feature: {month}/{code}/{key}")
        for key in ("return", "adverse", "adverse_flat_as_unknown_return"):
            row[key] = _finite(original.get(key))
        if row["adverse"] is not None and row["adverse"] > 1e-9:
            raise ValueError("adverse is an entry-relative minimum and must be nonpositive")
        by_month[month].append(row)

    monthly, groups, increments, coverage = [], [], [], []
    previous_g5 = {(universe, factor): None for universe in UNIVERSES for factor in FACTORS}
    previous_month = None
    for month in axis:
        all_rows = sorted(by_month[month], key=lambda row: row["code"])
        universe_rows = {
            "all_qualified": all_rows,
            "green_only": [row for row in all_rows if row["green"]],
        }
        holding_month = month_add(month, 1)
        for universe, pool in universe_rows.items():
            n = len(pool)
            qualified = n >= MIN_NAMES
            coverage.append(
                {
                    "month": month,
                    "holding_month": holding_month,
                    "universe": universe,
                    "n": n,
                    "qualified": qualified,
                    "known_return": sum(row["return"] is not None for row in pool),
                    "known_adverse": sum(row["adverse"] is not None for row in pool),
                }
            )
            for factor in FACTORS:
                record = {
                    "month": month,
                    "holding_month": holding_month,
                    "universe": universe,
                    "factor": factor,
                    "qualified": qualified,
                    "n": n,
                    "group_n": 5 if qualified else 0,
                    "complete_pool_return": None,
                    "pool_unknown_weight": None,
                    "g5_unknown_weight": None,
                    "g1_unknown_weight": None,
                    "g5_minus_pool_return": None,
                    "g5_minus_g1_return": None,
                    "known_g5_minus_pool_contribution": None,
                    "known_g5_minus_g1_contribution": None,
                    "known_subset_g5_minus_pool": None,
                    "known_subset_g5_minus_g1": None,
                    "complete_pool_adverse": None,
                    "g5_adverse_minus_pool": None,
                    "complete_pool_restrictive_return": None,
                    "pool_unknown_restrictive_weight": None,
                    "g5_minus_pool_restrictive_return": None,
                    "g5_minus_g1_restrictive_return": None,
                    "g5_loss_frequency": None,
                    "g5_loss_frequency_known": None,
                    "winner_capture_complete": None,
                    "winner_capture_known": None,
                    "winner_known_pool_n": None,
                    "winner_known_g5_n": None,
                    "g5_entry_fraction": None,
                    "spearman": None,
                    "spearman_known_pairs": 0,
                    "spearman_reason": "unqualified_month",
                }
                if not qualified:
                    previous_g5[(universe, factor)] = None
                    monthly.append(record)
                    continue
                bins = _bins(pool, factor)
                these_groups = [
                    _group(items, index, n, factor) for index, items in enumerate(bins, 1)
                ]
                for item in these_groups:
                    groups.append(
                        {
                            "month": month,
                            "holding_month": holding_month,
                            "universe": universe,
                            "factor": factor,
                            **item,
                        }
                    )
                pool_weights = {row["code"]: 1 / n for row in pool}
                pool_return = _weighted(pool, pool_weights, "return")
                pool_adverse = _weighted(pool, pool_weights, "adverse")
                pool_restrictive = _weighted(pool, pool_weights, "adverse_flat_as_unknown_return")
                g1, g5 = these_groups[0], these_groups[-1]
                g5_members = set(g5["codes"])
                previous = previous_g5[(universe, factor)]
                entry = (
                    len(g5_members - previous) / len(g5_members)
                    if previous is not None
                    and previous_month is not None
                    and month_add(previous_month, 1) == month
                    else None
                )
                previous_g5[(universe, factor)] = g5_members
                winners = {
                    row["code"]
                    for row in pool
                    if row["return"] is not None and row["return"] >= 0.20
                }
                g5_winners = len(winners & g5_members)
                complete_return = pool_return["complete"] is not None
                complete_adverse = pool_adverse["complete"] is not None
                complete_restrictive = pool_restrictive["complete"] is not None
                record.update(
                    {
                        "complete_pool_return": pool_return["complete"],
                        "pool_unknown_weight": pool_return["unknown_weight"],
                        "g5_unknown_weight": g5["unknown_weight"],
                        "g1_unknown_weight": g1["unknown_weight"],
                        "g5_minus_pool_return": g5["complete_return"] - pool_return["complete"]
                        if complete_return
                        else None,
                        "g5_minus_g1_return": g5["complete_return"] - g1["complete_return"]
                        if complete_return
                        else None,
                        "known_g5_minus_pool_contribution": g5["known_sum_over_n"]
                        - pool_return["known_contribution"],
                        "known_g5_minus_g1_contribution": g5["known_sum_over_n"]
                        - g1["known_sum_over_n"],
                        "known_subset_g5_minus_pool": g5["known_conditional_mean"]
                        - pool_return["known_conditional_mean"]
                        if g5["known_conditional_mean"] is not None
                        and pool_return["known_conditional_mean"] is not None
                        else None,
                        "known_subset_g5_minus_g1": g5["known_conditional_mean"]
                        - g1["known_conditional_mean"]
                        if g5["known_conditional_mean"] is not None
                        and g1["known_conditional_mean"] is not None
                        else None,
                        "complete_pool_adverse": pool_adverse["complete"],
                        "g5_adverse_minus_pool": g5["complete_adverse"] - pool_adverse["complete"]
                        if complete_adverse
                        else None,
                        "complete_pool_restrictive_return": pool_restrictive["complete"],
                        "pool_unknown_restrictive_weight": pool_restrictive["unknown_weight"],
                        "g5_minus_pool_restrictive_return": g5["complete_restrictive_return"]
                        - pool_restrictive["complete"]
                        if complete_restrictive
                        else None,
                        "g5_minus_g1_restrictive_return": g5["complete_restrictive_return"]
                        - g1["complete_restrictive_return"]
                        if complete_restrictive
                        else None,
                        "g5_loss_frequency": g5["loss_frequency_complete"]
                        if complete_return
                        else None,
                        "g5_loss_frequency_known": g5["loss_frequency_known"],
                        "winner_capture_complete": g5_winners / len(winners)
                        if complete_return and winners
                        else None,
                        "winner_capture_known": g5_winners / len(winners) if winners else None,
                        "winner_known_pool_n": len(winners),
                        "winner_known_g5_n": g5_winners,
                        "g5_entry_fraction": entry,
                        **_spearman(pool, factor),
                    }
                )
                monthly.append(record)
        green = universe_rows["green_only"]
        if len(green) >= MIN_NAMES:
            n = len(green)
            strata = _bins(green, "momentum")
            baseline = {row["code"]: 1 / n for row in green}
            picks = {
                factor: _stratified_weights(strata, factor, n)[0]
                for factor in ("high52", "cool", "lowvol")
            }
            top_n = math.ceil(n * 0.20)
            top = sorted(green, key=lambda row: (-row["momentum"], row["code"]))[:top_n]
            top_weights = {row["code"]: 1 / top_n for row in top}
            for label, candidate, comparator in (
                ("high52_vs_green", picks["high52"], baseline),
                ("cool_vs_green", picks["cool"], baseline),
                ("lowvol_vs_green", picks["lowvol"], baseline),
                ("high52_vs_momentum_top20", picks["high52"], top_weights),
                ("cool_vs_lowvol", picks["cool"], picks["lowvol"]),
            ):
                increments.append(
                    _increment_row(month, holding_month, label, candidate, comparator, green)
                )
        previous_month = month
    result = {
        "monthly": monthly,
        "groups": groups,
        "increments": increments,
        "summary": _summaries(axis, monthly, increments),
        "coverage": coverage,
    }
    return _clean(result)
