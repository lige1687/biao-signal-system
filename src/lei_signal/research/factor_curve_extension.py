"""Past-only features and frozen monthly targets for the factor curve library.

This research adapter defines rankings, never future returns or account fills.
The separate quote-account engine consumes its explicit month-end targets.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence

import numpy as np

from lei_signal.research.fip import month_add

FACTORS = (
    "momentum20", "momentum60", "momentum120", "ma_distance", "ppo",
    "residual", "downside", "lowvol", "momentum", "scaled_momentum",
)
UNIVERSES = ("all_qualified", "green_only")
DERIVED = ("momentum20", "momentum60", "momentum120", "ma_distance", "ppo", "downside")
REUSED = ("momentum", "vol60", "ordinary", "residual", "scaled_momentum")


def _finite(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _known_bool(value: object) -> bool:
    if value is True or value == "True":
        return True
    if value is False or value == "False":
        return False
    raise ValueError("green must be known at formation")


def _reasons(value: object) -> set[str]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise ValueError("residual reasons must be a list of strings")
    return set(value)


def daily_extension_features(
    adapted: Mapping, calendar: Sequence[str], code: str, first_month: str, last_month: str
) -> list[dict]:
    """Six extra scores at each decision close, with no compressed missing days.

    Every absent calendar row, nonpositive close, or source basis break starts a
    fresh segment. EMA seeds are the first complete SMA window in that segment.
    A 120-session return requires 121 consecutive closes; all six scores must
    exist before the later common-pool intersection admits a name.
    """
    if adapted.get("research_price_basis") != "raw_ohlc_times_effective_foreAdjustFactor":
        raise ValueError("unexpected adjusted research price basis")
    dates = list(calendar)
    if dates != sorted(set(dates)) or not dates:
        raise ValueError("calendar must be nonempty sorted unique dates")
    if first_month > last_month:
        raise ValueError("inverted formation range")
    by_day = {}
    for row in adapted["rows"]:
        if row["date"] in by_day:
            raise ValueError("duplicate source date")
        by_day[row["date"]] = row
    breaks = set(adapted["break_dates"])
    ends = {day[:7]: day for day in dates}
    positions = {day: i for i, day in enumerate(dates)}
    closes: list[float | None] = []
    segment_lengths: list[int] = []
    ema = {n: [] for n in (12, 20, 26, 60, 120)}
    rolling: list[float] = []
    state: dict[int, float | None] = {n: None for n in ema}
    for day in dates:
        row = by_day.get(day)
        close = _finite(row.get("close")) if row is not None else None
        if day in breaks or close is None or close <= 0:
            closes.append(None)
            segment_lengths.append(0)
            rolling = []
            state = {n: None for n in ema}
            for series in ema.values():
                series.append(None)
            continue
        closes.append(close)
        rolling.append(close)
        segment_lengths.append(len(rolling))
        for n, series in ema.items():
            if len(rolling) == n:
                state[n] = sum(rolling[-n:]) / n
            elif len(rolling) > n:
                state[n] = 2 / (n + 1) * close + (n - 1) / (n + 1) * state[n]
            series.append(state[n])
    result = []
    month = first_month
    while month <= last_month:
        day = ends.get(month)
        values = {name: None for name in DERIVED}
        reasons = []
        if day is None:
            reasons.append("formation_month_missing")
        else:
            i = positions[day]
            close = closes[i]
            segment_length = segment_lengths[i]
            if close is None:
                reasons.append("decision_close_missing_or_break")
            elif segment_length < 121:
                reasons.append("last_121_scheduled_closes_incomplete")
            else:
                for n in (20, 60, 120):
                    values[f"momentum{n}"] = close / closes[i - n] - 1
                lines = [ema[n][i] for n in (20, 60, 120)]
                lines += [sum(closes[i - n + 1:i + 1]) / n for n in (20, 60, 120)]
                values["ma_distance"] = min(abs(close - line) / line for line in lines)
                values["ppo"] = 100 * (ema[12][i] - ema[26][i]) / ema[26][i]
                logs = [math.log(closes[j] / closes[j - 1]) for j in range(i - 59, i + 1)]
                values["downside"] = -math.sqrt(sum(min(v, 0.0) ** 2 for v in logs) / 60)
        if any(_finite(value) is None for value in values.values()):
            reasons.append("derived_feature_missing")
        result.append({"code": code, "month": month, "decision_date": day,
                       **values, "qualified": not reasons, "reasons": sorted(set(reasons))})
        month = month_add(month, 1)
    return result


def _index(rows: Sequence[Mapping], label: str) -> dict[tuple[str, str], Mapping]:
    indexed = {}
    for row in rows:
        key = (row.get("month"), row.get("code"))
        if not all(isinstance(x, str) and x for x in key) or key in indexed:
            raise ValueError(f"invalid or duplicate {label} key: {key}")
        indexed[key] = row
    return indexed


def _oriented(row: Mapping, factor: str) -> float:
    if factor == "lowvol":
        return -row["vol60"]
    return row[factor]


def build_targets(
    old_rows: Sequence[Mapping], residual_rows: Sequence[Mapping],
    extension_rows: Sequence[Mapping], months: Sequence[str], calendar: Sequence[str],
    min_names: int = 30,
) -> dict:
    """Intersect past-only qualifications and freeze all 204 target schedules.

    Old rows may carry future labels, but only the explicit past-feature keys
    below are read. A residual row marked solely ``not_green`` remains eligible
    in ``all_qualified``; old green state controls the green-only subset.
    """
    axis = list(months)
    dates = list(calendar)
    if not axis or axis != sorted(set(axis)) or dates != sorted(set(dates)):
        raise ValueError("months and calendar must be sorted unique")
    if min_names < 5:
        raise ValueError("minimum pool smaller than five groups")
    ends = {day[:7]: day for day in dates}
    if any(month not in ends for month in axis):
        raise ValueError("formation month missing from market calendar")
    old = _index(old_rows, "old")
    residual = _index(residual_rows, "residual")
    derived = _index(extension_rows, "derived")
    if any(not any(key[0] == month for key in old) for month in axis):
        raise ValueError("old qualified input has a missing formation month")
    pools: dict[str, list[dict]] = defaultdict(list)
    qualification = []
    for month in axis:
        for key in sorted(k for k in old if k[0] == month):
            base = old[key]
            prior = residual.get(key)
            extra = derived.get(key)
            reason = None
            if prior is None or extra is None:
                reason = "source_feature_missing"
            elif extra.get("decision_date") != base.get("decision_date") or prior.get("decision_date") != base.get("decision_date"):
                raise ValueError(f"decision date conflicts across frozen sources: {key}")
            elif _reasons(prior.get("reasons")) - {"not_green"}:
                reason = "residual_source_unqualified"
            elif not extra.get("qualified"):
                reason = "derived_source_unqualified"
            scores = {}
            if reason is None:
                for name, source_key, source in (
                    ("momentum", "momentum", base), ("vol60", "vol60", base),
                    ("ordinary", "ordinary", prior),
                    ("residual", "residual", prior),
                    ("scaled_momentum", "scaled_control", prior),
                    *((name, name, extra) for name in DERIVED),
                ):
                    scores[name] = _finite(source.get(source_key))
                if any(value is None for value in scores.values()):
                    reason = "common_score_missing"
            qualification.append({"month": month, "code": key[1], "qualified": reason is None,
                                  "reason": reason})
            if reason is None:
                pools[month].append({"code": key[1], "green": _known_bool(base.get("green")),
                                     **scores})
    monthly, groups = [], []
    targets = {f"{universe}__{factor}__G{g}": {} for universe in UNIVERSES
               for factor in FACTORS for g in range(1, 6)}
    targets.update({f"{universe}__pool": {} for universe in UNIVERSES})
    for month in axis:
        decision = ends[month]
        universe_pools = {"all_qualified": pools[month],
                          "green_only": [row for row in pools[month] if row["green"]]}
        for universe, names in universe_pools.items():
            qualified = len(names) >= min_names
            n = len(names)
            monthly.append({"month": month, "universe": universe, "n": n,
                            "qualified": qualified, "decision_date": decision})
            pool_weights = {row["code"]: 1 / n for row in names} if qualified else {}
            targets[f"{universe}__pool"][decision] = {
                "qualified": qualified, "weights": pool_weights}
            for factor in FACTORS:
                ordered = sorted(names, key=lambda row: (_oriented(row, factor), row["code"]))
                partitions = np.array_split(np.asarray(ordered, dtype=object), 5) if qualified else ()
                for g in range(1, 6):
                    members = list(partitions[g - 1]) if qualified else []
                    codes = [row["code"] for row in members]
                    weights = {code: 1 / len(codes) for code in codes}
                    name = f"{universe}__{factor}__G{g}"
                    targets[name][decision] = {"qualified": qualified, "weights": weights}
                    groups.append({"month": month, "universe": universe, "factor": factor,
                                   "group": g, "qualified": qualified, "codes": codes,
                                   "n": len(codes)})
    if len(targets) != 102 or any(len(schedule) != len(axis) for schedule in targets.values()):
        raise ArithmeticError("incomplete target schedules")
    return {"monthly": monthly, "groups": groups, "targets": targets,
            "qualification": qualification, "factors": list(FACTORS), "months": axis}


def summarize_account(daily: Sequence[Mapping], periods: Mapping[str, Sequence[str]],
                      initial_cash: float = 100000) -> dict:
    """Project an immutable daily account into the archived curve schema."""
    if not daily or [r["date"] for r in daily] != sorted(set(r["date"] for r in daily)):
        raise ValueError("account days must be sorted unique")
    if not math.isfinite(initial_cash) or initial_cash <= 0:
        raise ValueError("invalid initial cash")
    points = {}
    peak = initial_cash
    for row in daily:
        nav = _finite(row["nav_quote_proxy"])
        if nav is None or nav <= 0:
            raise ValueError("invalid account value")
        peak = max(peak, nav)
        month = row["date"][:7]
        old = points.get(month)
        points[month] = [row["date"], nav / initial_cash, row["unknown_fraction"],
                         row["cash_fraction"],
                         min(old[4] if old else 0.0, nav / peak - 1),
                         max(old[5] if old else 0.0, row["unknown_fraction"])]
    period_stats = {}
    for label, (first, last) in periods.items():
        prior = next((row for row in reversed(daily) if row["date"][:7] < first), None)
        rows = [row for row in daily if first <= row["date"][:7] <= last]
        if prior is None or not rows:
            raise ValueError(f"incomplete account period: {label}")
        month_ends = {row["date"][:7]: row for row in rows}
        if len(month_ends) != 12 * (int(last[:4]) - int(first[:4])) + int(last[5:]) - int(first[5:]) + 1:
            raise ValueError(f"missing account month: {label}")
        values = [prior["nav_quote_proxy"]] + [row["nav_quote_proxy"] for row in rows]
        day_returns = [b / a - 1 for a, b in zip(values, values[1:])]
        month_values = [values[0]] + [row["nav_quote_proxy"] for row in month_ends.values()]
        monthly = [b / a - 1 for a, b in zip(month_values, month_values[1:])]
        running_peak = values[0]
        drawdowns = []
        for value in values:
            running_peak = max(running_peak, value)
            drawdowns.append(value / running_peak - 1)
        period_stats[label] = {
            "return": values[-1] / values[0] - 1,
            "cagr": (values[-1] / values[0]) ** (12 / len(monthly)) - 1,
            "max_drawdown": min(drawdowns),
            "volatility": statistics.stdev(day_returns) * math.sqrt(252),
            "months": len(monthly),
            "loss_month_fraction": sum(value < 0 for value in monthly) / len(monthly),
            "fee_currency": rows[-1]["fees_cumulative"] - prior["fees_cumulative"],
            "gross_turnover_monthly": sum(row["gross_traded_today"] / row["nav_before_trade"]
                                          for row in rows) / len(monthly),
            "unknown_mean": statistics.mean(row["unknown_fraction"] for row in rows),
            "unknown_max": max(row["unknown_fraction"] for row in rows),
            "unknown_days": sum(row["unknown_fraction"] > 1e-12 for row in rows),
            "cash_mean": statistics.mean(row["cash_fraction"] for row in rows),
            "final_unknown": rows[-1]["unknown_fraction"],
            "final_cash": rows[-1]["cash_fraction"],
            "monthly": dict(zip(month_ends, monthly)), "days": len(rows),
        }
    return {"points": list(points.values()), "period": period_stats}


def describe_monthly_difference(candidate: Mapping, baseline: Mapping) -> dict:
    """Return the archived descriptive difference fields on identical months."""
    months = list(candidate["monthly"])
    if months != list(baseline["monthly"]):
        raise ValueError("comparison months differ")
    values = [candidate["monthly"][m] - baseline["monthly"][m] for m in months]
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    for lag in range(1, min(3, n - 1) + 1):
        covariance = sum((values[i] - mean) * (values[i - lag] - mean)
                         for i in range(lag, n)) / n
        variance += 2 * (1 - lag / 4) * covariance
    se = math.sqrt(max(0.0, variance) / n)
    up = [candidate["monthly"][m] - baseline["monthly"][m]
          for m in months if baseline["monthly"][m] > 0]
    down = [candidate["monthly"][m] - baseline["monthly"][m]
            for m in months if baseline["monthly"][m] < 0]
    return {"mean": mean, "descriptive95": [mean - 1.96 * se, mean + 1.96 * se],
            "months": n,
            "cagr_difference": candidate["cagr"] - baseline["cagr"],
            "drawdown_difference": candidate["max_drawdown"] - baseline["max_drawdown"],
            "up_month_difference": statistics.mean(up) if up else None,
            "down_month_difference": statistics.mean(down) if down else None,
            "up_month_n": len(up), "down_month_n": len(down),
            "cash_difference": candidate["cash_mean"] - baseline["cash_mean"],
            "unknown_difference": candidate["unknown_mean"] - baseline["unknown_mean"]}
