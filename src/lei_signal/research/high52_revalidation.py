"""Source qualification for a bounded historical-cohort high52 follow-up.

The old 600-stock experiment is immutable. This module audits its missing
quotes and adapts a separately acquired 300-stock historical cohort. It
produces no account returns and never infers a fill from a daily quote.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation, localcontext
from datetime import date

import pandas as pd

from lei_signal.features.indicators import seeded_ema
from lei_signal.research.fip import SOURCE_FIELDS, month_add
from lei_signal.research.green_momentum import residual_scores
from lei_signal.rules.lei_color import classify_colors

ADJUSTMENT_FIELDS = (
    "code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor", "adjustFactor"
)
SCORES = ("ordinary", "arithmetic_control", "scaled_control", "residual", "alpha", "residual_sd")


def decimal_interval(value: str) -> tuple[Decimal, Decimal]:
    """Closed interval implied by a finite positive, rounded source string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("blank numeric source field")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid numeric source field") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("nonpositive numeric source field")
    half_unit = Decimal(1).scaleb(number.as_tuple().exponent) / 2
    return number - half_unit, number + half_unit


def product_interval(left: tuple[Decimal, Decimal], right: tuple[Decimal, Decimal]):
    if left[0] <= 0 or right[0] <= 0:
        raise ValueError("product factors must remain positive")
    return left[0] * right[0], left[1] * right[1]


def intervals_overlap(left, right) -> bool:
    return max(left[0], right[0]) <= min(left[1], right[1])


def price_identity(previous_close: str, previous_factor: str,
                   current_preclose: str, current_factor: str,
                   same_effective_factor: bool | None = None) -> dict:
    """Compare adjacent factor-adjusted prices using original string precision."""
    if same_effective_factor is None:
        same_effective_factor = previous_factor == current_factor
    if same_effective_factor:
        if previous_factor != current_factor:
            raise ValueError("same effective factor has different source values")
        # The effective factor is one source number shared by both sides. Its
        # rounding uncertainty is perfectly correlated and cancels in the
        # equality test; treating it as two independent values creates false
        # overlaps for disjoint raw-price intervals.
        return quoted_price_identity(previous_close, current_preclose)
    with localcontext() as context:
        context.prec = 50
        prior = product_interval(decimal_interval(previous_close), decimal_interval(previous_factor))
        current = product_interval(decimal_interval(current_preclose), decimal_interval(current_factor))
        prior_mid = Decimal(previous_close) * Decimal(previous_factor)
        current_mid = Decimal(current_preclose) * Decimal(current_factor)
        return {"intervals_overlap": intervals_overlap(prior, current),
                "center_relative_gap": float(prior_mid/current_mid - 1),
                "prior_interval": (str(prior[0]), str(prior[1])),
                "current_interval": (str(current[0]), str(current[1]))}


def quoted_price_identity(previous_close: str, current_preclose: str) -> dict:
    """Check two already adjusted source quotes without inventing factor precision."""
    prior, current = decimal_interval(previous_close), decimal_interval(current_preclose)
    return {"intervals_overlap": intervals_overlap(prior, current),
            "center_relative_gap": float(Decimal(previous_close) / Decimal(current_preclose) - 1),
            "prior_interval": tuple(map(str, prior)),
            "current_interval": tuple(map(str, current))}


def pct_identity(close: str, preclose: str, pct_chg: str) -> bool:
    """Reuse legacy 1e-6 return tolerance for provider pctChg cross-check.

    Vendor pctChg is displayed with padded decimals but derives from prices at
    different precision. This check is separate from the strict adjacent-price
    interval test, which is never relaxed by a percent tolerance.
    """
    try:
        pct = Decimal(pct_chg)
        if not pct.is_finite():
            raise ValueError("nonfinite pctChg")
        return abs(float(Decimal(close) / Decimal(preclose) - 1 - pct / 100)) <= 1e-6
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid pctChg") from exc


def _source_rows(payload: Mapping, fields: Sequence[str], code: str) -> list[dict]:
    if payload.get("error_code") != "0" or payload.get("fields") != list(fields):
        raise ValueError("source schema or provider error")
    raw = payload.get("data")
    if not isinstance(raw, list):
        raise ValueError("source data is not a list")
    rows, previous = [], ""
    for i, values in enumerate(raw):
        if not isinstance(values, list) or len(values) != len(fields):
            raise ValueError(f"source row width:{i}")
        row = dict(zip(fields, values, strict=True))
        day = row["date"] if "date" in row else row["dividOperateDate"]
        try:
            date.fromisoformat(day)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid source date:{i}") from exc
        if row["code"] != code or day <= previous:
            raise ValueError(f"source code/date/order:{i}")
        rows.append(row)
        previous = day
    return rows


def adapt_back_adjusted(daily_payload: Mapping, action_payload: Mapping, code: str,
                        calendar: Sequence[str], factor_field: str = "backAdjustFactor") -> dict:
    """Apply only chosen factors effective by each date; preserve every failed day.

    The resulting values are research prices, not official total return or
    executable prices. A failed identity is a breakpoint, never backfilled.
    """
    if factor_field not in ("foreAdjustFactor", "backAdjustFactor"):
        raise ValueError("unsupported source factor field")
    daily = _source_rows(daily_payload, SOURCE_FIELDS, code)
    actions = _source_rows(action_payload, ADJUSTMENT_FIELDS, code)
    if any(r["adjustflag"] != "3" for r in daily):
        raise ValueError("mixed or non-raw adjustment flag; quarantine source")
    allowed = set(calendar)
    end_date = calendar[-1]
    factors = []
    for action in actions:
        decimal_interval(action[factor_field])
        factors.append((action["dividOperateDate"], action[factor_field]))
    rows, breaks, failures = [], set(), defaultdict(list)
    raw_by_day, factor_by_day = {}, {}
    previous_row = None
    previous_calendar_index = None
    factor_index = 0
    active_factor = None
    calendar_index = {day: i for i, day in enumerate(calendar)}
    for raw in daily:
        day = raw["date"]
        if day > end_date:
            break
        raw_by_day[day] = raw
        if day not in allowed:
            raise ValueError(f"daily source outside bound calendar: {day}")
        while factor_index < len(factors) and factors[factor_index][0] <= day:
            active_factor = factors[factor_index][1]
            factor_index += 1
        factor_by_day[day] = (active_factor, factor_index)
        if active_factor is None:
            breaks.add(day)
            failures[day].append("back_factor_unavailable")
            previous_row = None
            previous_calendar_index = None
            continue
        if previous_row is not None and calendar_index[day] != previous_calendar_index + 1:
            breaks.add(day)
            failures[day].append("calendar_gap_before_row")
        try:
            if raw["tradestatus"] not in ("0", "1"):
                raise ValueError("status_invalid")
            for name in ("close", "preclose"):
                decimal_interval(raw[name])
            if raw["tradestatus"] == "1":
                for name in ("open", "high", "low"):
                    decimal_interval(raw[name])
                lo, hi, op, cl = (Decimal(raw[name]) for name in ("low", "high", "open", "close"))
                if not (lo <= min(op, cl) <= max(op, cl) <= hi):
                    raise ValueError("ohlc_incoherent")
                if not raw["pctChg"] or not pct_identity(raw["close"], raw["preclose"], raw["pctChg"]):
                    failures[day].append("reported_pct_disagrees_with_raw_price")
                    breaks.add(day)
            else:
                volume = Decimal(raw["volume"]) if raw["volume"] else Decimal(0)
                if volume != 0 or not intervals_overlap(decimal_interval(raw["close"]),
                                                        decimal_interval(raw["preclose"])):
                    failures[day].append("suspended_quote_not_flat")
                    breaks.add(day)
                if raw["pctChg"] and not pct_identity(raw["close"], raw["preclose"], raw["pctChg"]):
                    failures[day].append("suspended_reported_pct_invalid")
                    breaks.add(day)
            identity = None
            adjacent = previous_row is not None and calendar_index[day] == previous_calendar_index + 1
            if previous_row is not None:
                identity = price_identity(
                    previous_row["close"], previous_row["factor"], raw["preclose"], active_factor,
                    same_effective_factor=previous_row["factor_event_index"] == factor_index,
                )
                if not identity["intervals_overlap"]:
                    failures[day].append("adjusted_preclose_break")
                    breaks.add(day)
            factor = Decimal(active_factor)
            adjusted = {name: str(Decimal(raw[name]) * factor) if raw[name] else ""
                        for name in ("open", "high", "low", "close", "preclose")}
            quoted_preclose = adjusted["preclose"]
            normalized = bool(adjacent and identity and identity["intervals_overlap"])
            if normalized:
                adjusted["preclose"] = str(Decimal(previous_row["close"]) *
                                           Decimal(previous_row["factor"]))
            delta = Decimal(adjusted["preclose"]) - Decimal(quoted_preclose)
            derived_pct = (Decimal(adjusted["close"]) / Decimal(adjusted["preclose"]) - 1) * 100
            rows.append({**raw, **{f"raw_{name}": raw[name] for name in
                                    ("open", "high", "low", "close", "preclose", "pctChg")},
                         **adjusted, "raw_adjustflag": "3",
                         "adjustflag": "derived_adjusted", "factor_field": factor_field,
                         "effective_factor": active_factor,
                         "quoted_adjusted_preclose": quoted_preclose,
                         "normalized_preclose": normalized,
                         "preclose_normalization_delta": str(delta),
                         "preclose_identity_intervals": identity,
                         "derived_pctChg": str(derived_pct),
                         "pctChg_basis": "vendor_raw_unadjusted"})
            previous_row = {**raw, "factor": active_factor, "factor_event_index": factor_index}
            previous_calendar_index = calendar_index[day]
        except (ValueError, InvalidOperation, KeyError) as exc:
            breaks.add(day)
            failures[day].append(str(exc))
            previous_row = None
            previous_calendar_index = None
    return {"rows": rows, "break_dates": sorted(breaks),
            "failures": dict(failures), "source_rows": len(daily),
            "action_rows": len(actions), "research_price_basis": f"raw_ohlc_times_effective_{factor_field}",
            "raw_by_day": raw_by_day, "factor_by_day": factor_by_day}


def candidate_features(adapted: Mapping, calendar: Sequence[str], factors: Mapping[str, Sequence[float]],
                       code: str, first_month: str, last_month: str) -> list[dict]:
    """Old green/36m/11m/252-session definitions on a separately qualified source."""
    rows = adapted["rows"]
    by_day = {r["date"]: r for r in rows}
    breaks = set(adapted["break_dates"])
    chronological = sorted(by_day)
    close = pd.Series([float(by_day[d]["close"]) for d in chronological], index=chronological)
    colors = classify_colors(pd.DataFrame({"close": close, "ema20": seeded_ema(close, 20),
                                            "close_lag20": close.shift(20)}))
    by_month = defaultdict(list)
    month_ends = {}
    for day in calendar:
        by_month[day[:7]].append(day)
        month_ends[day[:7]] = day
    date_index = {d: i for i, d in enumerate(calendar)}
    output = []
    month = first_month
    while month <= last_month:
        decision = month_ends.get(month)
        reasons = []
        if decision not in by_day:
            reasons.append("decision_quote_missing")
        else:
            r = by_day[decision]
            if r["tradestatus"] != "1" or r["isST"] != "0" or not r["volume"] or Decimal(r["volume"]) <= 0:
                reasons.append("decision_not_traded_or_st")
            if colors.loc[decision, "signal_color"] != "green":
                reasons.append("not_green")
        prior_month = month_add(month, -36)
        prior_end = month_ends.get(prior_month)
        if prior_end not in by_day:
            reasons.append("prior_month_end_missing")
        last36 = [month_add(month, -35 + i) for i in range(36)]
        returns = []
        for m in last36:
            scheduled = by_month.get(m, [])
            if not scheduled or any(d not in by_day for d in scheduled):
                reasons.append("month_calendar_gap")
                break
            if any(d in breaks for d in scheduled):
                reasons.append("adjusted_price_break_in_window")
                break
            prior = month_ends.get(month_add(m, -1))
            if prior not in by_day:
                reasons.append("prior_month_end_missing")
                break
            endpoint = float(by_day[scheduled[-1]]["close"]) / float(by_day[prior]["close"]) - 1
            daily_compound = math.prod(float(by_day[d]["close"]) /
                                       float(by_day[d]["preclose"]) for d in scheduled) - 1
            if abs(endpoint - daily_compound) > 1e-6:
                reasons.append("monthly_daily_compound_disagrees")
                break
            returns.append(endpoint)
        factor_rows = [factors.get(m) for m in last36]
        if any(row is None for row in factor_rows):
            reasons.append("ch3_month_missing")
        high52 = math.nan
        if decision in date_index:
            i = date_index[decision]
            window = calendar[max(0, i-251):i+1]
            if len(window) != 252 or any(d not in by_day or d in breaks for d in window):
                reasons.append("high52_window_gap_or_break")
            else:
                high52 = (float(by_day[decision]["close"]) /
                          max(float(by_day[d]["close"]) for d in window))
        scores = {key: math.nan for key in SCORES}
        if len(returns) == 36 and all(row is not None for row in factor_rows):
            try:
                scores.update(residual_scores(returns, factor_rows))
            except ValueError as exc:
                reasons.append(str(exc))
        output.append({"code": code, "month": month, "decision_date": decision,
                       "eligible": not reasons, "reasons": sorted(set(reasons)),
                       "high52": high52, **scores})
        month = month_add(month, 1)
    return output


def quote_status(row: Mapping | None) -> str:
    if row is None:
        return "missing"
    if row["tradestatus"] == "0":
        return "suspended"
    if row["tradestatus"] != "1":
        return "status_invalid"
    try:
        op, volume = float(row.get("raw_open", row["open"])), float(row["volume"])
    except (TypeError, ValueError):
        return "open_or_volume_missing"
    if not math.isfinite(op) or not math.isfinite(volume) or op <= 0 or volume <= 0:
        return "open_or_volume_invalid"
    return "traded_quote_unverified_fill"


def audit_unknowns(outcomes: Sequence[Mapping], source_payloads: Mapping[str, Mapping],
                   calendar: Sequence[str], out_dates: Mapping[str, str]) -> list[dict]:
    """Inspect frozen unknown rows without computing substitute future returns."""
    unknown = [row for row in outcomes if row.get("return") in (None, "")]
    by_source = {}
    for code in {r["code"] for r in unknown}:
        payload = source_payloads[code]
        by_source[code] = {r["date"]: r for r in _source_rows(payload, SOURCE_FIELDS, code)}
    positions = {day: i for i, day in enumerate(calendar)}
    answer = []
    for original in unknown:
        code, entry, exit_day = original["code"], original["entry_date"], original["exit_date"]
        by_day = by_source[code]
        if entry not in positions or exit_day not in positions:
            raise ValueError("unknown record outside bound calendar")
        entry_status = quote_status(by_day.get(entry))
        exit_status = quote_status(by_day.get(exit_day))
        rec = {"month": original["month"], "code": code, "original_reason": original["reason"],
               "entry_date": entry, "exit_date": exit_day,
               "entry_status": entry_status, "exit_status": exit_status,
               "entry_blocked": entry_status != "traded_quote_unverified_fill",
               "exit_blocked": exit_status != "traded_quote_unverified_fill",
               "cohort_out_date": out_dates.get(code, ""),
               "first_gap_date": "", "first_gap_previous_date": "",
               "gap_intervals_overlap": None, "gap_center_relative": None}
        for role, date in (("entry", entry), ("exit", exit_day)):
            first_day, delay = "", None
            if rec[f"{role}_blocked"]:
                for offset, day in enumerate(calendar[positions[date]+1:], 1):
                    if quote_status(by_day.get(day)) == "traded_quote_unverified_fill":
                        first_day, delay = day, offset
                        break
            rec[f"{role}_first_later_traded_quote"] = first_day
            rec[f"{role}_delay_sessions"] = delay
        rec["entry_later_quote_before_planned_exit"] = bool(
            rec["entry_first_later_traded_quote"] and rec["entry_first_later_traded_quote"] < exit_day
        )
        path = calendar[positions[original["decision_date"]]:positions[exit_day]+1]
        for prior, day in zip(path, path[1:]):
            previous, current = by_day.get(prior), by_day.get(day)
            if previous is None or current is None:
                rec["first_gap_date"] = day
                rec["first_gap_previous_date"] = prior
                break
            try:
                identity = quoted_price_identity(previous["close"], current["preclose"])
            except ValueError:
                continue
            if not identity["intervals_overlap"]:
                rec["first_gap_date"] = day
                rec["first_gap_previous_date"] = prior
                rec["gap_intervals_overlap"] = identity["intervals_overlap"]
                rec["gap_center_relative"] = identity["center_relative_gap"]
                break
        answer.append(rec)
    return answer


def execution_quote_audit(row: Mapping | None) -> dict:
    """Describe a raw endpoint quote; never infer a fill or exchange limit."""
    if row is None:
        return {"quote_status": "missing", "directional_flat_quote": False,
                "flat_direction": "", "flat_assessment_available": False,
                "fill_confirmed": False}
    status = quote_status(row)
    flat_direction = ""
    flat_available = False
    if status == "traded_quote_unverified_fill":
        try:
            prices = [Decimal(row.get(f"raw_{name}", row[name]))
                      for name in ("open", "high", "low", "close")]
            preclose = Decimal(row.get("raw_preclose", row["preclose"]))
            if not all(p.is_finite() and p > 0 for p in prices + [preclose]):
                raise ValueError("invalid raw endpoint OHLC")
            flat_available = True
            if all(price == prices[0] for price in prices):
                flat_direction = "up" if prices[0] > preclose else (
                    "down" if prices[0] < preclose else "unchanged")
        except (KeyError, InvalidOperation, ValueError):
            flat_available = False
    return {"quote_status": status,
            "directional_flat_quote": flat_direction in ("up", "down"),
            "flat_direction": flat_direction,
            "flat_assessment_available": flat_available,
            "fill_confirmed": False}


def adjusted_future_outcome(adapted: Mapping, calendar: Sequence[str], decision: str,
                            entry: str, exit_day: str) -> dict:
    """Fixed next-open quote path with source breaks and fill uncertainty separate.

    `return` is only an idealized quote comparison. The sensitivity treats an
    upward one-price entry or downward one-price exit as unknown, retaining
    selected weight. The opposite directions are recorded, with no fill claim.
    """
    positions = {day: i for i, day in enumerate(calendar)}
    result = {"return": None, "adverse": None, "opportunity": None,
              "adverse_flat_as_unknown_return": None, "reason": ""}
    if any(day not in positions for day in (decision, entry, exit_day)) or not (
        positions[decision] < positions[entry] < positions[exit_day]
    ):
        return {**result, "reason": "invalid_fixed_calendar_endpoints"}
    path = calendar[positions[decision]:positions[exit_day]+1]
    by_day = {row["date"]: row for row in adapted["rows"]}
    raw_by_day = adapted.get("raw_by_day", {})
    factor_by_day = adapted.get("factor_by_day", {})
    entry_audit = execution_quote_audit(by_day.get(entry))
    exit_audit = execution_quote_audit(raw_by_day.get(exit_day))
    result.update({f"entry_{key}": val for key, val in entry_audit.items()})
    result.update({f"exit_{key}": val for key, val in exit_audit.items()})
    if any(day not in by_day for day in path[:-1]) or exit_day not in raw_by_day:
        return {**result, "reason": "future_calendar_row_missing"}
    if any(day in set(adapted["break_dates"]) for day in path[1:-1]):
        return {**result, "reason": "future_adjusted_price_break"}
    for day in path[:-1]:
        row = by_day[day]
        try:
            close, pre = float(row["close"]), float(row["preclose"])
            if not all(math.isfinite(value) and value > 0 for value in (close, pre)):
                return {**result, "reason": "future_adjusted_ohlc_invalid"}
            if row["tradestatus"] != "0":
                low, high, op = (float(row[name]) for name in ("low", "high", "open"))
                if not (0 < low <= min(op, close) <= max(op, close) <= high):
                    return {**result, "reason": "future_adjusted_ohlc_invalid"}
            # A saved halted row can contain a valid flat close with blank
            # open/high/low. The path excursion uses closes only; inventing
            # intraday quotes or declaring the next-open endpoint unknown would
            # both distort the comparison. Entry/exit tradability is checked
            # separately from their original raw quotes below.
        except (KeyError, TypeError, ValueError):
            return {**result, "reason": "future_adjusted_ohlc_invalid"}
    if entry_audit["quote_status"] != "traded_quote_unverified_fill" or \
            exit_audit["quote_status"] != "traded_quote_unverified_fill":
        return {**result, "reason": "entry_or_exit_no_traded_quote"}
    prior_row = by_day[path[-2]]
    exit_raw = raw_by_day[exit_day]
    prior_factor = factor_by_day.get(path[-2])
    exit_factor = factor_by_day.get(exit_day)
    if prior_factor is None or exit_factor is None or exit_factor[0] is None:
        return {**result, "reason": "exit_factor_unavailable"}
    try:
        exit_identity = price_identity(
            prior_row["raw_close"], prior_factor[0], exit_raw["preclose"], exit_factor[0],
            same_effective_factor=prior_factor[1] == exit_factor[1],
        )
        if not exit_identity["intervals_overlap"]:
            return {**result, "reason": "exit_preclose_identity_invalid"}
        exit_open = float(Decimal(exit_raw["open"]) * Decimal(exit_factor[0]))
    except (ValueError, InvalidOperation, KeyError):
        return {**result, "reason": "exit_preclose_identity_invalid"}
    entry_open = float(by_day[entry]["open"])
    if not (math.isfinite(entry_open) and math.isfinite(exit_open) and
            entry_open > 0 and exit_open > 0):
        return {**result, "reason": "endpoint_open_invalid"}
    holding = [day for day in path if entry <= day < exit_day]
    close_path = [float(by_day[day]["close"]) / entry_open - 1 for day in holding]
    exit_return = exit_open / entry_open - 1
    result.update({"return": exit_return,
                   "adverse": min([0.0, exit_return, *close_path]),
                   "opportunity": max([0.0, exit_return, *close_path]),
                   "adverse_flat_as_unknown_return": (
                       None if entry_audit["flat_direction"] == "up" or
                       exit_audit["flat_direction"] == "down" or
                       not entry_audit["flat_assessment_available"] or
                       not exit_audit["flat_assessment_available"] else exit_return)})
    return result


def decompose_increment(candidate: Sequence[str], baseline: Sequence[str],
                        outcomes: Mapping[str, Mapping], return_field: str = "return") -> dict:
    """Explain a fixed selected-weight difference without filling unknowns."""
    candidate_weight = 1 / len(candidate)
    baseline_weight = 1 / len(baseline)
    selected_candidate, selected_baseline = set(candidate), set(baseline)
    pieces = {"added_gain": 0.0, "added_loss": 0.0,
              "avoided_loss": 0.0, "foregone_gain": 0.0}
    unknown_coefficient = 0.0
    unknown_absolute_weight = 0.0
    for code in selected_candidate | selected_baseline:
        weight = candidate_weight * (code in selected_candidate) - baseline_weight * (code in selected_baseline)
        value = outcomes[code][return_field]
        if value is None:
            unknown_coefficient += weight
            unknown_absolute_weight += abs(weight)
        elif weight > 0 and value >= 0:
            pieces["added_gain"] += weight * value
        elif weight > 0:
            pieces["added_loss"] += weight * value
        elif value < 0:
            pieces["avoided_loss"] += weight * value
        else:
            pieces["foregone_gain"] += weight * value
    known = sum(pieces.values())
    return {**pieces, "known_increment": known,
            "unknown_weight_coefficient_same_shock": unknown_coefficient,
            "unknown_absolute_weight": unknown_absolute_weight,
            "same_shock_minus100": known - unknown_coefficient,
            "same_shock_zero": known,
            "same_shock_plus100": known + unknown_coefficient,
            "adverse_mixed_assignment": known - unknown_absolute_weight,
            "favorable_mixed_assignment": known + unknown_absolute_weight,
            "break_even_same_shock": (-known / unknown_coefficient
                                       if unknown_coefficient else None)}
