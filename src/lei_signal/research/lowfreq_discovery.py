"""Frozen, retrospective cross-sectional selection study; no trading decisions.

The input contract binds a historical cohort, exchange calendar, BaoStock daily
responses and the frozen design by path and SHA-256. This module never fetches
data or imports an archived experiment's implementation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

DESIGN_ID = "lowfreq-expanded-discovery-2026-10-19"
DESIGN_SHA256 = "c1943599b5365f484cbfa1553ccbd6c0358909e1c3a9468a115ec8cedc202539"
METHODS = ("pool_equal", "momentum_top20", "short_top20") + tuple(
    f"momentum_q{i}" for i in range(1, 6)
)
CODE_RE = re.compile(r"^(?:sh\.60|sz\.00|sz\.30)\d{4}$")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bound(spec):
    path = Path(spec["path"]).expanduser().resolve()
    if not path.is_file() or _sha(path) != spec["sha256"]:
        raise ValueError(f"missing or changed input: {path}")
    return json.loads(path.read_text(encoding="utf-8")), path


def _table(doc, required):
    fields = doc["fields"]
    if len(fields) != len(set(fields)) or not set(required) <= set(fields):
        raise ValueError(f"missing or repeated table columns: {required}")
    rows = []
    for values in doc["data"]:
        if len(values) != len(fields):
            raise ValueError("table row length differs from fields")
        rows.append(dict(zip(fields, values)))
    return rows


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _month_next(month):
    y, m = map(int, month.split("-"))
    return f"{y + (m == 12):04d}-{m % 12 + 1:02d}"


def _decision_and_execution_dates(calendar, first="2015-01", last="2025-12"):
    by_month = defaultdict(list)
    for day in calendar:
        by_month[day[:7]].append(day)
    result = []
    month = first
    while True:
        prev = f"{int(month[:4]) - 1}-12" if month.endswith("-01") else f"{month[:5]}{int(month[5:]) - 1:02d}"
        after = _month_next(month)
        if not by_month[prev] or not by_month[month] or not by_month[after]:
            raise ValueError(f"calendar lacks decision/entry/exit month: {month}")
        result.append((month, by_month[prev][-1], by_month[month][0], by_month[after][0]))
        if month == last:
            return result
        month = after


def _cohort(doc, asof, sample_size):
    rows = _table(doc, ("code",))
    codes, metadata = [], {}
    for row in rows:
        code = row["code"]
        if not CODE_RE.fullmatch(code):
            continue
        if "type" in row and str(row["type"]) not in ("1", ""):
            continue
        ipo = row.get("ipoDate") or row.get("ipo_date")
        out = row.get("outDate") or row.get("out_date")
        if not ipo:
            raise ValueError(f"historical IPO date missing: {code}")
        date.fromisoformat(ipo)
        if out:
            date.fromisoformat(out)
        if ipo and ipo > asof:
            continue
        if out and out <= asof:
            continue
        codes.append(code)
        metadata[code] = {"ipo": ipo, "out": out or None}
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate historical cohort code")
    ordered = sorted(codes, key=lambda code: (hashlib.sha256(("lowfreq-20141231-v1|" + code).encode()).hexdigest(), code))
    chosen = ordered[:sample_size]
    return chosen, len(codes), {code: metadata[code] for code in chosen}


def _calendar(doc):
    rows = _table(doc, ("calendar_date", "is_trading_day"))
    days = []
    prior = ""
    for row in rows:
        day = row["calendar_date"]
        date.fromisoformat(day)
        if day <= prior:
            raise ValueError("calendar must be unique and increasing")
        prior = day
        if str(row["is_trading_day"]) in ("1", "True", "true"):
            days.append(day)
    return days


def _quotes(doc, code, request, calendar=None, membership=None):
    if request.get("adjustflag") != "2" or request.get("frequency") != "d" or request.get("code") != code:
        raise ValueError("BaoStock daily front-adjusted request identity required")
    if request.get("start_date", "9999") > "2013-01-01" or request.get("end_date", "0000") < "2026-01-15":
        raise ValueError("source request does not cover frozen raw window")
    if doc.get("error_code") != "0":
        raise ValueError(f"BaoStock response failed: {code}")
    rows = _table(doc, ("date", "code", "close", "amount", "tradestatus", "isST"))
    quote, valid, errors = {}, [], []
    prior = ""
    for row in rows:
        day = row["date"]
        date.fromisoformat(day)
        if day <= prior or row["code"] != code:
            raise ValueError(f"unordered, repeated, or wrong-code quote: {code} {day}")
        prior = day
        if str(row["tradestatus"]) not in ("0", "1") or str(row["isST"]) not in ("0", "1"):
            errors.append((day, "invalid_status_or_isST"))
        close = _number(row["close"])
        traded = str(row["tradestatus"]) == "1"
        normalized_halt_amount = (str(row["tradestatus"]) == "0"
                                  and row["amount"] in ("", None))
        amount = 0.0 if normalized_halt_amount else _number(row["amount"])
        if (close is None or close <= 0 or amount is None or amount < 0) and day >= (membership or {}).get("ipo", day):
            errors.append((day, "invalid_price_or_amount"))
        if not traded and amount != 0:
            errors.append((day, "halt_amount_not_zero"))
        item = {"date": day, "close": close, "amount": amount, "traded": traded,
                "status_valid": str(row["tradestatus"]) in ("0", "1"),
                "normalized_halt_amount": normalized_halt_amount,
                "is_st": str(row["isST"]) == "1"}
        quote[day] = item
        if traded and close is not None and close > 0 and str(row["isST"]) in ("0", "1"):
            valid.append(item)
    if calendar is not None:
        outside = set(quote) - set(calendar)
        if outside:
            raise ValueError(f"quote date outside frozen calendar: {code} {min(outside)}")
        ipo = membership["ipo"]
        out = membership["out"]
        for day in calendar:
            if day >= ipo and (out is None or day <= out) and day not in quote:
                errors.append((day, "expected_listed_day_missing_from_source"))
    return quote, valid, sorted(set(errors))


def _sample_std(values):
    if len(values) < 2:
        return None
    center = statistics.fmean(values)
    return math.sqrt(math.fsum((x - center) ** 2 for x in values) / (len(values) - 1))


def _features(valid, calendar=None, quotes=None):
    """Use only each asset's actual, positive quote prefix, never a shared grid."""
    result = {}
    positions = {day: i for i, day in enumerate(calendar)} if calendar is not None else None
    for i, row in enumerate(valid):
        q = row["close"]
        momentum = q21 = volatility = liquidity = None
        if i >= 252:
            momentum = valid[i - 21]["close"] / valid[i - 252]["close"] - 1
        if i >= 21:
            q21 = q / valid[i - 21]["close"] - 1
        if positions is None:
            if i >= 60:
                changes = [valid[j]["close"] / valid[j - 1]["close"] - 1 for j in range(i - 59, i + 1)]
                volatility = _sample_std(changes) * math.sqrt(252)
            if i >= 19:
                amounts = [_number(valid[j]["amount"]) for j in range(i - 19, i + 1)]
                if all(x is not None and x >= 0 for x in amounts):
                    liquidity = math.fsum(amounts) / 20
        else:
            at = positions.get(row["date"])
            if at is not None and at >= 60:
                levels = [quotes.get(d, {}).get("close") for d in calendar[at - 60:at + 1]]
                if len(levels) == 61 and all(v is not None and v > 0 for v in levels):
                    changes = [levels[j] / levels[j - 1] - 1 for j in range(1, 61)]
                    volatility = _sample_std(changes) * math.sqrt(252)
            if at is not None and at >= 19:
                amounts = [quotes.get(d, {}).get("amount") for d in calendar[at - 19:at + 1]]
                if len(amounts) == 20 and all(v is not None and v >= 0 for v in amounts):
                    liquidity = math.fsum(amounts) / 20
        result[row["date"]] = {"momentum": momentum, "short": q21,
                                "vol60": volatility, "amount20": liquidity,
                                "valid_count": i + 1,
                                "momentum_252_start_date": valid[i - 252]["date"] if i >= 252 else None,
                                "momentum_21_calendar_days": (date.fromisoformat(row["date"]) - date.fromisoformat(valid[i - 21]["date"])).days if i >= 21 else None,
                                "momentum_252_calendar_days": (date.fromisoformat(row["date"]) - date.fromisoformat(valid[i - 252]["date"])).days if i >= 252 else None}
    return result


def _rank_partition(items, parts):
    base, extra = divmod(len(items), parts)
    groups, start = [], 0
    for k in range(parts):
        end = start + base + (k < extra)
        groups.append(items[start:end])
        start = end
    return groups


def _weights(members):
    if not members:
        return {}
    return {code: 1 / len(members) for code in members}


def _selections(panel):
    qualified = [r for r in panel if r["eligibility_reason"] == "eligible"]
    momentum = sorted(qualified, key=lambda r: (-r["momentum"], r["code"]))
    short = sorted(qualified, key=lambda r: (-r["short"], r["code"]))
    top = math.ceil(len(qualified) * .2)
    groups = _rank_partition(momentum, 5)
    names = {"pool_equal": [r["code"] for r in qualified],
             "momentum_top20": [r["code"] for r in momentum[:top]],
             "short_top20": [r["code"] for r in short[:top]]}
    for i, group in enumerate(groups, 1):
        names[f"momentum_q{i}"] = [r["code"] for r in group]
    return {method: _weights(names[method]) for method in METHODS}, qualified


def _conditional_groups(qualified, include_short=False):
    """Nine or 27 fixed cells; all partitions use decision-time features only."""
    vol = _rank_partition(sorted(qualified, key=lambda r: (r["vol60"], r["code"])), 3)
    cells = []
    for vi, group in enumerate(vol, 1):
        liquidity = _rank_partition(sorted(group, key=lambda r: (r["amount20"], r["code"])), 3)
        for li, subgroup in enumerate(liquidity, 1):
            subcells = _rank_partition(sorted(subgroup, key=lambda r: (r["short"], r["code"])), 3) if include_short else [subgroup]
            for si, members in enumerate(subcells, 1):
                ranked = sorted(members, key=lambda r: (-r["momentum"], r["code"]))
                top = ranked[:math.ceil(len(ranked) / 5)]
                cells.append({"vol_group": vi, "amount_group": li,
                              "short_group": si if include_short else None,
                              "all": _weights([r["code"] for r in members]),
                              "top": _weights([r["code"] for r in top]), "n": len(members)})
    return cells


def _combined_cell_weights(cells, pool_count):
    top, all_members = defaultdict(float), defaultdict(float)
    for cell in cells:
        share = cell["n"] / pool_count if pool_count else 0
        for code, weight in cell["top"].items():
            top[code] += share * weight
        for code, weight in cell["all"].items():
            all_members[code] += share * weight
    return dict(top), dict(all_members)


def _outcome(quotes, entry, exit_day):
    a, b = quotes.get(entry), quotes.get(exit_day)
    if not a or not b:
        return None, "missing_entry_or_exit", None
    if not a.get("status_valid", True) or not b.get("status_valid", True):
        return None, "invalid_entry_or_exit_status", None
    for endpoint in (a, b):
        amount = endpoint.get("amount")
        if amount is None or amount < 0 or (not endpoint["traded"] and amount != 0):
            return None, "invalid_entry_or_exit_amount", None
    proxy = None
    if (a["close"] is not None and b["close"] is not None
            and a["close"] > 0 and b["close"] > 0):
        proxy = b["close"] / a["close"] - 1
    if proxy is None:
        return None, "invalid_entry_or_exit", None
    if not a["traded"] or not b["traded"]:
        return proxy, "observed_mark_halted_entry_or_exit", proxy
    return proxy, "observed", proxy


def _weighted_outcome(weights, outcomes, halt_flags=None):
    halt_flags = halt_flags or {}
    if not weights:
        return {"observed_contribution": None, "unknown_weight": 0.0,
                "unknown_count": 0, "scenario_minus100": None,
                "scenario_zero": None, "known_only_return": None,
                "entry_halt_weight": 0.0, "exit_halt_weight": 0.0,
                "either_halt_weight": 0.0,
                "empty_selection": True}
    observed = unknown = 0.0
    for code, weight in weights.items():
        value = outcomes[code][0]
        if value is None:
            unknown += weight
        else:
            observed += weight * value
    return {"observed_contribution": observed, "unknown_weight": unknown,
            "unknown_count": sum(outcomes[c][0] is None for c in weights),
            "entry_halt_weight": math.fsum(w for c, w in weights.items() if halt_flags.get(c, (False, False))[0]),
            "exit_halt_weight": math.fsum(w for c, w in weights.items() if halt_flags.get(c, (False, False))[1]),
            "either_halt_weight": math.fsum(w for c, w in weights.items() if any(halt_flags.get(c, (False, False)))),
            "scenario_minus100": observed - unknown,
            "scenario_zero": observed,
            "known_only_return": observed if unknown == 0 else None,
            "empty_selection": False}


def _mean(values):
    values = [v for v in values if v is not None]
    return math.fsum(values) / len(values) if values else None


def _times(value, factor):
    return None if value is None else value * factor


def _contrast(months, left, right, scenario):
    result = []
    for row in months:
        a, b = row["methods"][left][scenario], row["methods"][right][scenario]
        result.append(None if a is None or b is None else a - b)
    return result


def _blocks(values, lengths, draws, seed):
    if not values or not any(v is not None for v in values):
        return {}
    result = {}
    n = len(values)
    for length in lengths:
        rng = random.Random(seed)
        samples, finite_counts = [], []
        for _ in range(draws):
            selected = []
            for _ in range(math.ceil(n / length)):
                start = rng.randrange(n)
                selected.extend(values[(start + offset) % n] for offset in range(length))
            chosen = selected[:n]
            point = _mean(chosen)
            if point is not None:
                samples.append(point)
                finite_counts.append(sum(v is not None for v in chosen))
        if not samples:
            result[str(length)] = {"percentile_95": None, "valid_draws": 0,
                                   "draws_requested": draws, "finite_months_range": None}
            continue
        samples.sort()
        def quantile(p):
            at = (len(samples) - 1) * p / 100
            lo = math.floor(at)
            return samples[lo] + (samples[math.ceil(at)] - samples[lo]) * (at - lo)
        result[str(length)] = {"percentile_95": [quantile(2.5), quantile(97.5)],
                               "valid_draws": len(samples), "draws_requested": draws,
                               "finite_months_range": [min(finite_counts), max(finite_counts)]}
    return result


def _risk_summary(values):
    if not values or any(v is None for v in values):
        return None
    wealth = peak = 1.0
    drawdown = 0.0
    for value in values:
        wealth *= 1 + value
        peak = max(peak, wealth)
        drawdown = max(drawdown, 1 - wealth / peak)
    worst = sorted(values)[:math.ceil(len(values) / 10)]
    return {"monthly_mean": _mean(values), "monthly_std": _sample_std(values),
            "worst_month": min(values), "mean_worst10pct_months": _mean(worst),
            "marked_price_cumulative": wealth - 1, "marked_price_max_drawdown": drawdown}


def _turnover(current, previous):
    if previous is None:
        return None
    return .5 * math.fsum(abs(current.get(c, 0) - previous.get(c, 0)) for c in current.keys() | previous.keys())


def _relative_unknown(left, right, outcomes):
    if not left or not right:
        return None
    observed = adverse = favorable = 0.0
    for code in left.keys() | right.keys():
        delta = left.get(code, 0) - right.get(code, 0)
        value = outcomes[code][0]
        if value is None:
            adverse -= max(delta, 0)
            favorable -= min(delta, 0)
        else:
            observed += delta * value
    return {"observed_delta": observed, "adverse_unknown_minus100_or_zero": observed + adverse,
            "favorable_unknown_minus100_or_zero": observed + favorable}


def _relevant_errors(decision, calendar, selected_codes, source_quotes, source_features,
                     source_errors, membership):
    """Block only a source fault in a candidate's decision-time dependency window."""
    at = calendar.index(decision)
    result = []
    for code in selected_codes:
        member = membership[code]
        if decision < member["ipo"] or (member["out"] is not None and decision > member["out"]):
            continue
        quote = source_quotes[code].get(decision)
        feature = source_features[code].get(decision)
        if quote is not None and not quote["traded"]:
            dependency_start = decision
        elif feature and feature["momentum_252_start_date"]:
            dependency_start = min(feature["momentum_252_start_date"], calendar[max(0, at - 60)])
        else:
            dependency_start = max(membership[code]["ipo"], calendar[max(0, at - 360)])
        result.extend({"code": code, "date": day, "reason": reason,
                       "dependency_start": dependency_start, "decision_date": decision}
                      for day, reason in source_errors[code] if dependency_start <= day <= decision)
    return result


def _evaluate(design, selected_codes, sources, calendar, membership):
    source_quotes, source_features, source_errors = {}, {}, {}
    for code in selected_codes:
        source = sources[code]
        quote, valid, errors = _quotes(source["data"], code, source["request"], calendar, membership[code])
        source_quotes[code] = quote
        source_features[code] = _features(valid, calendar, quote)
        source_errors[code] = errors
    periods = _decision_and_execution_dates(calendar)
    monthly, selections, per_stock, conditional = [], [], [], []
    previous = {m: None for m in METHODS}
    for month, decision, entry, exit_day in periods:
        panel = []
        for code in selected_codes:
            q = source_quotes[code].get(decision)
            f = source_features[code].get(decision)
            reason = "eligible"
            member = membership[code]
            if decision < member["ipo"] or (member["out"] is not None and decision > member["out"]):
                reason = "outside_historical_listing"
            elif q is None or not q["traded"] or q["close"] is None or q["close"] <= 0:
                reason = "no_actual_month_end_quote"
            elif f is None or f["valid_count"] < 253:
                reason = "under_253_actual_quotes"
            elif any(f[k] is None or not math.isfinite(f[k]) for k in ("momentum", "short", "vol60", "amount20")):
                reason = "incomplete_factor"
            elif q["is_st"]:
                reason = "historical_isST"
            panel.append({"month": month, "decision_date": decision, "code": code,
                          "eligibility_reason": reason, **(f or {})})
        errors = _relevant_errors(decision, calendar, selected_codes, source_quotes,
                                  source_features, source_errors, membership)
        blocked = bool(errors)
        weights, qualified = _selections(panel) if not blocked else ({m: {} for m in METHODS}, [])
        cells9 = _conditional_groups(qualified)
        cells27 = _conditional_groups(qualified, include_short=True)
        outcomes = {code: _outcome(source_quotes[code], entry, exit_day) for code in selected_codes}
        halt_flags = {code: (
            bool(source_quotes[code].get(entry) and source_quotes[code][entry]["status_valid"]
                 and not source_quotes[code][entry]["traded"]),
            bool(source_quotes[code].get(exit_day) and source_quotes[code][exit_day]["status_valid"]
                 and not source_quotes[code][exit_day]["traded"])) for code in selected_codes}
        method_results = {}
        for method in METHODS:
            wr = _weighted_outcome(weights[method], outcomes, halt_flags)
            wr["target_replacement_turnover"] = (_turnover(weights[method], previous[method])
                                                  if not blocked and qualified else None)
            method_results[method] = wr
            previous[method] = weights[method] if not blocked and qualified else None
            for code, weight in weights[method].items():
                selections.append({"month": month, "method": method, "code": code,
                                   "target_weight": weight, "decision_date": decision,
                                   "entry_date": entry, "exit_date": exit_day})
        for item in panel:
            code = item["code"]
            outcome, outcome_reason, proxy = outcomes[code]
            per_stock.append({**item, "entry_date": entry, "exit_date": exit_day,
                              "future_return": outcome, "outcome_reason": outcome_reason,
                              "entry_traded": (source_quotes[code].get(entry) or {}).get("traded"),
                              "exit_traded": (source_quotes[code].get(exit_day) or {}).get("traded"),
                              "entry_halt": halt_flags[code][0], "exit_halt": halt_flags[code][1],
                              "either_halt": any(halt_flags[code]),
                              "suspension_marked_price_proxy": proxy if outcome is None else None,
                              **{f"weight_{m}": weights[m].get(code, 0) for m in METHODS}})
        n = len(qualified)
        cells_by_kind = {}
        for kind, cells in (("vol_amount_9", cells9), ("vol_amount_short_27", cells27)):
            cell_rows = []
            combined_top, combined_all = _combined_cell_weights(cells, n)
            for cell in cells:
                cell_rows.append({"vol_group": cell["vol_group"], "amount_group": cell["amount_group"],
                                  "short_group": cell["short_group"], "n": cell["n"],
                                  "share_of_pool": cell["n"] / n if n else 0,
                                  "top_n": len(cell["top"]),
                                  "all": _weighted_outcome(cell["all"], outcomes, halt_flags),
                                  "top": _weighted_outcome(cell["top"], outcomes, halt_flags)})
            cells_by_kind[kind] = cell_rows
            combined = {"top": _weighted_outcome(combined_top, outcomes, halt_flags),
                        "all": _weighted_outcome(combined_all, outcomes, halt_flags),
                        "relative_adversarial": _relative_unknown(combined_top, combined_all, outcomes)}
            cells_by_kind[kind] = {"cells": cell_rows, "combined": combined}
        conditional.append({"month": month, "cells_by_kind": cells_by_kind})
        monthly.append({"month": month, "decision_date": decision, "entry_date": entry,
                        "exit_date": exit_day, "pool_count": n,
                        "status": "data_error" if blocked else ("empty_pool" if n == 0 else "evaluated"),
                        "data_errors": errors, "ineligible_count": len(panel) - n if not blocked else None,
                        "methods": method_results,
                        "relative_adversarial": {
                            "momentum_top20_minus_pool_equal": _relative_unknown(weights["momentum_top20"], weights["pool_equal"], outcomes),
                            "momentum_top20_minus_short_top20": _relative_unknown(weights["momentum_top20"], weights["short_top20"], outcomes)}})
    return monthly, selections, per_stock, conditional


def _aggregate(monthly, selections, per_stock, conditional, design):
    scenarios = ("scenario_minus100", "scenario_zero")
    performance = {"scope": "retrospective selection, not executable account",
                   "months": len(monthly), "methods": {}, "comparisons": {}, "uncertainty": {},
                   "unknown_outcome_scenarios": list(scenarios)}
    annual = []
    for method in METHODS:
        records = [r["methods"][method] for r in monthly]
        performance["methods"][method] = {
            "defined_months": {scenario: sum(r[scenario] is not None for r in records) for scenario in scenarios},
            "mean_pct": {scenario: _times(_mean([r[scenario] for r in records]), 100) for scenario in scenarios},
            "mean_unknown_weight": _mean([r["unknown_weight"] for r in records]),
            "months_with_unknown": sum(r["unknown_weight"] > 0 for r in records),
            "months_empty_selection": sum(r["empty_selection"] for r in records),
            "mean_entry_halt_weight": _mean([r["entry_halt_weight"] for r in records if not r["empty_selection"]]),
            "mean_exit_halt_weight": _mean([r["exit_halt_weight"] for r in records if not r["empty_selection"]]),
            "mean_either_halt_weight": _mean([r["either_halt_weight"] for r in records if not r["empty_selection"]]),
            "months_with_entry_halt": sum(r["entry_halt_weight"] > 0 for r in records),
            "months_with_exit_halt": sum(r["exit_halt_weight"] > 0 for r in records),
            "months_with_either_halt": sum(r["either_halt_weight"] > 0 for r in records),
            "mean_target_replacement_turnover": _mean([r["target_replacement_turnover"] for r in records if r["target_replacement_turnover"] is not None]),
            "scenarios": {scenario: _risk_summary([r[scenario] for r in records]) for scenario in scenarios}}
    for scenario in scenarios:
        for left, right in (("momentum_top20", "pool_equal"), ("momentum_top20", "short_top20")):
            key = f"{left}_minus_{right}"
            values = _contrast(monthly, left, right, scenario)
            entry = performance["comparisons"].setdefault(key, {})
            entry[scenario] = {"mean_percentage_points": _times(_mean(values), 100),
                               "defined_months": sum(v is not None for v in values),
                               "monthly_values": values,
                               "leave_one_year_out_percentage_points": {
                                   str(y): _times(_mean([v for r, v in zip(monthly, values) if not r["month"].startswith(str(y))]), 100)
                                   for y in range(2015, 2026)}}
            performance["uncertainty"][f"{key}:{scenario}"] = _blocks(
                values, design["uncertainty"]["circular_month_block_lengths"],
                design["uncertainty"]["draws"], design["uncertainty"]["seed"])
            relative = [r["relative_adversarial"].get(key) for r in monthly]
            entry["unknown_relative_adversarial"] = {
                "defined_months": sum(v is not None for v in relative),
                "adverse_mean_percentage_points": _times(_mean([v["adverse_unknown_minus100_or_zero"] for v in relative if v is not None]), 100),
                "favorable_mean_percentage_points": _times(_mean([v["favorable_unknown_minus100_or_zero"] for v in relative if v is not None]), 100)}
    for year in range(2015, 2026):
        segment = [r for r in monthly if r["month"].startswith(str(year))]
        annual.append({"year": year, "months": len(segment), **{
            f"{m}_{scenario}_mean_pct": _times(_mean([r["methods"][m][scenario] for r in segment]), 100)
            for m in METHODS for scenario in scenarios}})
    # Conditional comparison preserves each original cell's share of the pool.
    increment = []
    for record in conditional:
        for kind, bundle in record["cells_by_kind"].items():
            for cell in bundle["cells"]:
                for scenario in scenarios:
                    delta = cell["top"][scenario] - cell["all"][scenario] if cell["n"] else None
                    increment.append({"month": record["month"], "control": kind,
                                      "vol_group": cell["vol_group"], "amount_group": cell["amount_group"],
                                      "short_group": cell["short_group"], "n": cell["n"],
                                      "share_of_pool": cell["share_of_pool"], "scenario": scenario,
                                      "top_minus_cell_pct": _times(delta, 100),
                                      "weighted_increment_pct": _times(delta, 100 * cell["share_of_pool"]),
                                      "top_unknown_weight": cell["top"]["unknown_weight"],
                                      "cell_unknown_weight": cell["all"]["unknown_weight"]})
    performance["conditional_increment_mean_pct"] = {}
    performance["conditional_comparisons"] = {}
    for kind in ("vol_amount_9", "vol_amount_short_27"):
        bundles = [r["cells_by_kind"][kind]["combined"] for r in conditional]
        entry = {}
        for scenario in scenarios:
            values = [None if b["top"][scenario] is None or b["all"][scenario] is None
                      else b["top"][scenario] - b["all"][scenario] for b in bundles]
            entry[scenario] = {"mean_percentage_points": _times(_mean(values), 100),
                               "defined_months": sum(v is not None for v in values),
                               "monthly_values": values,
                               "block_intervals": _blocks(values, design["uncertainty"]["circular_month_block_lengths"],
                                                          design["uncertainty"]["draws"], design["uncertainty"]["seed"])}
        relative = [b["relative_adversarial"] for b in bundles]
        entry["unknown_relative_adversarial"] = {}
        for label, key in (("adverse", "adverse_unknown_minus100_or_zero"),
                           ("favorable", "favorable_unknown_minus100_or_zero")):
            values = [None if r is None else r[key] for r in relative]
            entry["unknown_relative_adversarial"][label] = {
                "mean_percentage_points": _times(_mean(values), 100),
                "defined_months": sum(v is not None for v in values),
                "monthly_values": values,
                "block_intervals": _blocks(values, design["uncertainty"]["circular_month_block_lengths"],
                                           design["uncertainty"]["draws"], design["uncertainty"]["seed"])}
        performance["conditional_comparisons"][kind] = entry
        performance["conditional_increment_mean_pct"][kind] = {
            scenario: entry[scenario]["mean_percentage_points"] for scenario in scenarios}
    for i in range(1, 6):
        method = f"momentum_q{i}"
        performance.setdefault("quintile_means_pct", {})[method] = {
            scenario: _times(_mean([r["methods"][method][scenario] for r in monthly]), 100) for scenario in scenarios}
    # Contribution is an attribution of the frozen selected lists, without reranking.
    contributions = defaultdict(float)
    defined = {r["month"] for r in monthly if all(r["methods"][m]["scenario_zero"] is not None
                                                   for m in ("momentum_top20", "pool_equal"))}
    for row in per_stock:
        y = row["future_return"]
        if y is not None and row["month"] in defined:
            contributions[row["code"]] += (row["weight_momentum_top20"] - row["weight_pool_equal"]) * y / len(defined)
    headline = _mean(_contrast(monthly, "momentum_top20", "pool_equal", "scenario_zero"))
    reconciliation = math.fsum(contributions.values())
    if headline is not None and not math.isclose(reconciliation, headline, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("per-stock observed contributions do not reconcile to headline increment")
    performance["per_stock_excess_contribution_reconciliation"] = {
        "defined_months": len(defined), "contribution_sum_pct": 100 * reconciliation,
        "headline_scenario_zero_pct": _times(headline, 100)}
    performance["per_stock_excess_contribution_pct"] = {
        code: 100 * val for code, val in sorted(contributions.items())}
    largest = sorted(contributions, key=lambda c: (-contributions[c], c))[:5]
    performance["largest_five_observed_contributors"] = largest
    performance["remove_largest_five_without_reranking_observed_contribution_pct"] = 100 * math.fsum(
        val for code, val in contributions.items() if code not in largest)
    # These costs are break-even per unit of target-list replacement, not fee estimates.
    turnover = [r["methods"]["momentum_top20"]["target_replacement_turnover"] for r in monthly]
    total_turnover = math.fsum(x for x in turnover if x is not None)
    performance["break_even_per_target_replacement_cost"] = {
        scenario: (_mean(_contrast(monthly, "momentum_top20", "pool_equal", scenario)) * len(monthly) / total_turnover
                   if total_turnover and all(r["pool_count"] for r in monthly) else None) for scenario in scenarios}
    performance["period_split"] = {label: {scenario: {
        "defined_months": sum(r["methods"]["momentum_top20"][scenario] is not None for r in rows),
        "momentum_minus_pool_mean_pct": _times(_mean(_contrast(rows, "momentum_top20", "pool_equal", scenario)), 100),
        "momentum_minus_short_mean_pct": _times(_mean(_contrast(rows, "momentum_top20", "short_top20", scenario)), 100)}
        for scenario in scenarios} for label, rows in (
            ("2015-2019", [r for r in monthly if r["month"] < "2020-01"]),
            ("2020-2025", [r for r in monthly if r["month"] >= "2020-01"]))}
    return performance, annual, increment


def _write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row)) if rows else ["empty"]
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def _check_output_parent(spec, out):
    parent = Path(spec["output_parent"]).expanduser().resolve()
    destination = Path(out).expanduser().resolve()
    if not parent.is_dir() or destination.parent != parent or destination.exists():
        raise ValueError("output must be one new child of the bound external result directory")
    if parent.stat().st_dev == Path(__file__).stat().st_dev:
        raise ValueError("large study output must use a separate mounted device")
    return destination


def run_study(contract, out):
    """Evaluate a frozen, hash-bound contract and create a new output directory."""
    spec = json.loads(Path(contract).read_text()) if isinstance(contract, (str, Path)) else contract
    if spec.get("schema") != "lowfreq-evaluator-contract/1":
        raise ValueError("wrong evaluator contract schema")
    design, design_path = _bound(spec["design"])
    if (spec["design"]["sha256"] != DESIGN_SHA256 or design.get("research_id") != DESIGN_ID
            or design.get("version") != "design-v3" or not design.get("frozen_before_performance")):
        raise ValueError("wrong or unfrozen design")
    cohort_doc, _ = _bound(spec["cohort"])
    calendar_doc, _ = _bound(spec["calendar"])
    selected, historical_count, membership = _cohort(cohort_doc, design["universe"]["asof"], design["universe"]["sample_size"])
    if not selected:
        raise ValueError("empty historical cohort")
    calendar = _calendar(calendar_doc)
    source_specs = spec["sources"]
    if len({s["code"] for s in source_specs}) != len(source_specs):
        raise ValueError("duplicate source code")
    supplied = {s["code"] for s in source_specs}
    if supplied != set(selected):
        raise ValueError(f"source files must exactly match fixed cohort: missing={sorted(set(selected)-supplied)[:5]}")
    sources = {}
    for item in source_specs:
        if item["code"] not in selected:
            continue
        if item.get("status") != "ok":
            raise ValueError(f"source request failed or unqualified: {item['code']}")
        payload, _ = _bound(item)
        sources[item["code"]] = {"data": payload, "request": item["request"]}
    normalized_halt_amount_rows = 0
    for source in sources.values():
        for row in _table(source["data"], ("amount", "tradestatus")):
            normalized_halt_amount_rows += (str(row["tradestatus"]) == "0"
                                            and row["amount"] in ("", None))
    monthly, selections, per_stock, conditional = _evaluate(design, selected, sources, calendar, membership)
    performance, annual, increment = _aggregate(monthly, selections, per_stock, conditional, design)
    quality = {"historical_candidates": historical_count, "fixed_sample_count": len(selected),
               "sample_reached_600": len(selected) == 600,
               "sample_codes": selected, "monthly_full_rows": len(per_stock),
               "expected_monthly_full_rows": len(selected) * 132,
               "ineligible_reasons": dict(__import__("collections").Counter(
                   r["eligibility_reason"] for r in per_stock if r["eligibility_reason"] != "eligible")),
               "month_status_counts": dict(__import__("collections").Counter(r["status"] for r in monthly)),
               "actual_evaluated_months": sum(r["status"] == "evaluated" for r in monthly),
               "normalized_halt_amount_rows": normalized_halt_amount_rows,
               "ten_year_support_met": sum(r["status"] == "evaluated" for r in monthly) >= 120,
               "unknown_source_value_warning": "-100% and 0% scenarios are assumptions, not recovery-value bounds",
               "historical_cohort_completeness": "provider cross-check only; no complete exchange-level verification"}
    if len(monthly) != 132 or len(per_stock) != len(selected) * 132:
        raise ValueError("incomplete 132-month fixed-cohort panel")
    destination = _check_output_parent(spec, out)
    destination.mkdir(parents=False, exist_ok=False)
    _write_csv(destination / "monthly.csv", monthly)
    _write_csv(destination / "selections.csv", selections)
    _write_csv(destination / "per_stock_month.csv", per_stock)
    _write_csv(destination / "annual.csv", annual)
    _write_csv(destination / "increment.csv", increment)
    for name, payload in (("quality.json", quality), ("performance.json", performance)):
        with (destination / name).open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
    files = {p.name: _sha(p) for p in destination.iterdir()
             if p.is_file() and not p.name.startswith("._") and p.name != ".DS_Store"}
    manifest = {"schema": "lowfreq-result-manifest/1", "design_path": str(design_path),
                "design_sha256": spec["design"]["sha256"], "input_contract_sha256": _sha(contract) if isinstance(contract, (str, Path)) else None,
                "source_count": len(sources), "source_hashes": {s["code"]: s["sha256"] for s in source_specs if s["code"] in sources},
                "outputs": files, "market_execution": "retrospective_only", "production_authorized": False}
    with (destination / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return {"output": str(destination), "quality": quality, "performance": performance,
            "manifest_sha256": _sha(destination / "manifest.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = run_study(args.contract, args.out)
    print(json.dumps({"output": result["output"], "manifest_sha256": result["manifest_sha256"]}))


if __name__ == "__main__":
    main()
