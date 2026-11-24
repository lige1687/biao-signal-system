"""Pure, conservative qualification of raw BaoStock intraday bars.

The slot labels are a research end-of-bar interpretation pending a comparison
with the vendor's own historical data. No arrival or revision claim is made.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

SLOTS_60 = ("1030", "1130", "1400", "1500")
SLOTS_15 = (
    "0945", "1000", "1015", "1030", "1045", "1100", "1115", "1130",
    "1315", "1330", "1345", "1400", "1415", "1430", "1445", "1500",
)
PRICE_TOL = Decimal("0.00000001")
AMOUNT_UNIT = Decimal("0.0001")


def _day(value: object) -> str:
    s = str(value)
    if len(s) == 10 and s[4] == s[7] == "-":
        date.fromisoformat(s)
        return s
    if len(s) == 8 and s.isdigit():
        return date.fromisoformat(f"{s[:4]}-{s[4:6]}-{s[6:]}").isoformat()
    raise ValueError("invalid date")


def _number(value: object, *, positive: bool = False) -> Decimal:
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid decimal") from None
    if not n.is_finite() or (n <= 0 if positive else n < 0):
        raise ValueError("nonfinite or out-of-range decimal")
    return n


def _ohlc(row: dict, *, minute: bool) -> dict:
    result = {k: _number(row[k], positive=True) for k in ("open", "high", "low", "close")}
    if result["high"] < max(result["open"], result["close"], result["low"]) or result["low"] > min(result["open"], result["close"]):
        raise ValueError("inconsistent OHLC")
    for k in ("volume", "amount"):
        if minute or k in row:
            result[k] = _number(row[k])
    return result


def _aggregate(rows: list[dict]) -> dict:
    return {
        "open": rows[0]["open"], "high": max(r["high"] for r in rows),
        "low": min(r["low"] for r in rows), "close": rows[-1]["close"],
        "volume": sum((r["volume"] for r in rows), Decimal(0)),
        "amount": sum((r["amount"] for r in rows), Decimal(0)),
    }


def audit_intraday_asset(
    code: str, bars15: list[dict[str, str]], bars60: list[dict[str, str]],
    daily_raw: list[dict[str, str]], daily_backadj: list[dict[str, str]],
    factors: list[dict[str, str]], calendar: list[str],
) -> dict:
    """Return JSON-compatible numerical qualification and dated findings; never write data."""
    findings: list[dict] = []
    by_day: dict[str, dict] = {}
    compared_fields: dict[tuple[str, str, str], bool] = {}
    comparisons = {name: {"matched": 0, "mismatched": 0, "max_abs_diff": {}, "examples": [],
                          "fields": {}}
                   for name in ("15_to_60", "60_to_daily", "backadj_ratio", "factor_ratio")}

    def issue(day: str | None, layer: str, kind: str, detail: str, *, price: bool = False, quantity: bool = False) -> None:
        findings.append({"date": day, "layer": layer, "kind": kind, "detail": detail})
        if day in by_day:
            by_day[day]["reasons"].append(f"{layer}:{kind}")
            if price:
                by_day[day]["price_ok"] = False
            if quantity:
                by_day[day]["quantity_ok"] = False

    try:
        days = [_day(d) for d in calendar]
    except ValueError as exc:
        raise ValueError("calendar must contain real YYYY-MM-DD dates") from exc
    if days != sorted(set(days)):
        raise ValueError("calendar must be strictly ascending and unique")
    for d in days:
        by_day[d] = {"date": d, "status": "unknown", "price_ok": True,
                     "quantity_ok": True, "reasons": [], "bars15": 0, "bars60": 0}
    day_set = set(days)

    def parse_bars(rows: list[dict], label: str, slots: tuple[str, ...]) -> dict[str, dict[str, dict]]:
        parsed: dict[str, dict[str, dict]] = defaultdict(dict)
        seen: set[tuple[str, str]] = set()
        previous: tuple[str, str] | None = None
        for i, row in enumerate(rows):
            try:
                d = _day(row["date"])
                stamp = str(row["time"])
                if len(stamp) != 17 or not stamp.isdigit() or stamp[:8] != d.replace("-", "") or stamp[12:] != "00000":
                    raise ValueError("invalid minute time")
                slot = stamp[8:12]
                if slot not in slots:
                    raise ValueError("unexpected session slot")
                if row["code"] != code:
                    raise ValueError("asset code mismatch")
                if str(row["adjustflag"]) != "3":
                    raise ValueError("minute price is not raw")
                values = _ohlc(row, minute=True)
            except (KeyError, ValueError) as exc:
                fallback = None
                try:
                    fallback = _day(row.get("date"))
                except ValueError:
                    pass
                issue(fallback, label, "invalid_row", f"row {i}: {exc}", price=True, quantity=True)
                continue
            key = (d, slot)
            if previous is not None and key <= previous:
                issue(d, label, "order", f"row {i}: {key} after {previous}", price=True, quantity=True)
            previous = key
            if key in seen:
                issue(d, label, "duplicate", f"row {i}: {key}", price=True, quantity=True)
                continue
            seen.add(key)
            if d not in day_set:
                issue(d, label, "outside_calendar", f"row {i}: {d}")
                continue
            parsed[d][slot] = values
        return parsed

    p15 = parse_bars(bars15, "bars15", SLOTS_15)
    p60 = parse_bars(bars60, "bars60", SLOTS_60)

    def parse_daily(rows: list[dict], label: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        previous: str | None = None
        for i, row in enumerate(rows):
            try:
                d = _day(row["date"])
                if row["code"] != code:
                    raise ValueError("asset code mismatch")
                required_flag = "3" if label == "daily_raw" else "1"
                if str(row["adjustflag"]) != required_flag:
                    raise ValueError(f"expected adjustflag={required_flag}")
                if label == "daily_raw":
                    if str(row["tradestatus"]) not in ("0", "1"):
                        raise ValueError("invalid tradestatus")
                    if str(row["tradestatus"]) == "0":
                        vals = {"tradestatus": "0"}
                    else:
                        vals = _ohlc(row, minute=False)
                        vals["preclose"] = _number(row["preclose"], positive=True)
                        vals["pctChg"] = _number_signed(row["pctChg"])
                        vals["tradestatus"] = "1"
                else:
                    vals = _ohlc(row, minute=False)
            except (KeyError, ValueError) as exc:
                try:
                    fallback = _day(row.get("date"))
                except ValueError:
                    fallback = None
                issue(fallback, label, "invalid_row", f"row {i}: {exc}",
                      price=label == "daily_raw")
                continue
            if previous is not None and d <= previous:
                issue(d, label, "order_or_duplicate", f"row {i}: {d}", price=True)
            previous = d
            if d in out:
                issue(d, label, "duplicate", f"row {i}: {d}", price=True)
            else:
                out[d] = vals
        return out

    raw = parse_daily(daily_raw, "daily_raw")
    adjusted = parse_daily(daily_backadj, "daily_backadj")

    def compare(layer: str, d: str, expected: dict, actual: dict, fields: tuple[str, ...], amount_bars: int = 1) -> None:
        stat = comparisons[layer]
        diffs = {}
        for field in fields:
            field_stat = stat["fields"].setdefault(field, {"matched": 0, "mismatched": 0})
            if field not in expected or field not in actual:
                issue(d, layer, "missing_field", field, price=field in ("open", "high", "low", "close"), quantity=True)
                diffs[field] = "missing"
                field_stat["mismatched"] += 1
                compared_fields[(layer, d, field)] = False
                continue
            diff = abs(expected[field] - actual[field])
            tolerance = AMOUNT_UNIT * amount_bars if field == "amount" else PRICE_TOL if field in ("open", "high", "low", "close") else Decimal(0)
            stat["max_abs_diff"][field] = str(max(Decimal(stat["max_abs_diff"].get(field, "0")), diff))
            if diff > tolerance:
                diffs[field] = str(diff)
                field_stat["mismatched"] += 1
                compared_fields[(layer, d, field)] = False
                kind = "daily_close_difference" if layer == "60_to_daily" and field == "close" else "mismatch"
                issue(d, layer, kind, f"{field}: difference {diff}", price=field in ("open", "high", "low", "close"), quantity=field in ("volume", "amount"))
            else:
                field_stat["matched"] += 1
                compared_fields.setdefault((layer, d, field), True)
        if diffs:
            stat["mismatched"] += 1
            if len(stat["examples"]) < 5:
                stat["examples"].append({"date": d, "differences": diffs})
        else:
            stat["matched"] += 1

    for d in days:
        record = by_day[d]
        r15, r60 = p15.get(d, {}), p60.get(d, {})
        record["bars15"], record["bars60"] = len(r15), len(r60)
        day_raw = raw.get(d)
        if day_raw is None:
            record["status"] = "daily_unknown"
            issue(d, "daily_raw", "missing", "no raw daily row; suspension cannot be inferred", price=True)
        elif day_raw["tradestatus"] == "0":
            record["status"] = "suspended"
            record["price_ok"] = False
            record["quantity_ok"] = False
            if r15 or r60:
                issue(d, "session", "bars_on_suspended_day", "daily status is suspended", price=True)
            continue
        else:
            record["status"] = "trading"
        if len(r15) != 16 or set(r15) != set(SLOTS_15):
            issue(d, "bars15", "incomplete", f"{len(r15)}/16; missing {sorted(set(SLOTS_15)-set(r15))}", price=True, quantity=True)
        if len(r60) != 4 or set(r60) != set(SLOTS_60):
            issue(d, "bars60", "incomplete", f"{len(r60)}/4; missing {sorted(set(SLOTS_60)-set(r60))}", price=True, quantity=True)
        for j, slot in enumerate(SLOTS_60):
            quarter = SLOTS_15[j * 4:(j + 1) * 4]
            if all(s in r15 for s in quarter) and slot in r60:
                compare("15_to_60", d, _aggregate([r15[s] for s in quarter]), r60[slot],
                        ("open", "high", "low", "close", "volume", "amount"), 4)
        if all(s in r60 for s in SLOTS_60) and day_raw and record["status"] == "trading":
            compare("60_to_daily", d, _aggregate([r60[s] for s in SLOTS_60]), day_raw,
                    ("open", "high", "low", "close", "volume", "amount"), 4)

        back = adjusted.get(d)
        if day_raw and back and record["status"] == "trading":
            ratio = back["close"] / day_raw["close"]
            target = {k: day_raw[k] * ratio for k in ("open", "high", "low", "close")}
            compare("backadj_ratio", d, target, back, ("open", "high", "low", "close"))
        elif day_raw and record["status"] == "trading":
            issue(d, "daily_backadj", "missing", "adjusted daily row missing")

    parsed_factors: list[tuple[str, Decimal]] = []
    bad_factor_dates: set[str] = set()
    unknown_factor_date_error = False
    previous_factor: str | None = None
    for i, row in enumerate(factors):
        try:
            d = _day(row["dividOperateDate"])
            if row["code"] != code:
                raise ValueError("asset code mismatch")
            for name in ("backAdjustFactor", "foreAdjustFactor", "adjustFactor"):
                _number(row[name], positive=True)
            factor = _number(row["backAdjustFactor"], positive=True)
        except (KeyError, ValueError) as exc:
            try:
                bad_day = _day(row.get("dividOperateDate"))
                bad_factor_dates.add(bad_day)
            except ValueError:
                unknown_factor_date_error = True
            issue(None, "factors", "invalid_row", f"row {i}: {exc}")
            continue
        if previous_factor is not None and d <= previous_factor:
            issue(None, "factors", "order_or_duplicate", f"row {i}: {d}")
            bad_factor_dates.add(d)
        previous_factor = d
        parsed_factors.append((d, factor))
    factor_dates = Counter(d for d, _ in parsed_factors)
    for d, count in factor_dates.items():
        if count > 1:
            bad_factor_dates.add(d)
    # The records must be ordered and unique; ambiguous effective dates are
    # never resolved by sorting or choosing a convenient factor value.
    parsed_factors.sort()
    for d in days:
        if d not in raw or d not in adjusted or by_day[d]["status"] != "trading":
            continue
        prior = [(fd, value) for fd, value in parsed_factors if fd <= d]
        latest_bad = max((fd for fd in bad_factor_dates if fd <= d), default=None)
        if unknown_factor_date_error:
            issue(d, "factors", "unknown_effective_date", "invalid factor cannot be assigned to a safe interval")
            continue
        if latest_bad is not None and not prior:
            issue(d, "factors", "ambiguous_effective_factor", f"factor on {latest_bad} invalid or duplicated")
            continue
        if not prior:
            issue(d, "factors", "no_prior_factor", "no factor effective on or before this date")
            continue
        factor_day, factor = prior[-1]
        if latest_bad is not None and latest_bad >= factor_day:
            issue(d, "factors", "ambiguous_effective_factor", f"factor on {latest_bad} invalid or duplicated")
            continue
        actual = adjusted[d]["close"] / raw[d]["close"]
        price_diff = abs(raw[d]["close"] * factor - adjusted[d]["close"])
        ratio_diff = abs(factor - actual)
        stat = comparisons["factor_ratio"]
        stat["max_abs_diff"]["ratio"] = str(max(Decimal(stat["max_abs_diff"].get("ratio", "0")), ratio_diff))
        stat["max_abs_diff"]["price"] = str(max(Decimal(stat["max_abs_diff"].get("price", "0")), price_diff))
        field_stat = stat["fields"].setdefault("raw_close_times_factor", {"matched": 0, "mismatched": 0})
        good = price_diff <= PRICE_TOL
        field_stat["matched" if good else "mismatched"] += 1
        compared_fields[("factor_ratio", d, "price")] = good
        stat["matched" if good else "mismatched"] += 1
        if not good:
            issue(d, "factor_ratio", "mismatch", f"raw close × effective factor vs adjusted close: {price_diff}")
            if len(stat["examples"]) < 5:
                stat["examples"].append({"date": d, "price_difference": str(price_diff), "ratio_difference": str(ratio_diff)})
        by_day[d]["factor_date"] = factor_day

    runs: list[dict] = []
    current: list[str] = []
    for d in days + [""]:
        if d and by_day[d]["status"] == "trading" and by_day[d]["price_ok"]:
            current.append(d)
        elif current:
            runs.append({"start": current[0], "end": current[-1], "trading_days": len(current)})
            current = []
    qualified = any(r["status"] == "trading" for r in by_day.values()) and all(
        r["status"] == "trading" and r["price_ok"] for r in by_day.values()
    )
    for r in by_day.values():
        r["qualified_for_price_descriptive_use"] = r["status"] == "trading" and r["price_ok"]
        r["qualified_for_quantity_use"] = r["qualified_for_price_descriptive_use"] and r["quantity_ok"]
        reasons = set(r["reasons"])
        r["intraday_15_to_60_internal_qualified"] = (
            r["status"] == "trading" and r["bars15"] == 16 and r["bars60"] == 4
            and not any(x.startswith(("bars15:", "bars60:")) for x in reasons)
            and all(compared_fields.get(("15_to_60", r["date"], k)) is True
                    for k in ("open", "high", "low", "close"))
        )
        r["intraday_15_to_60_quantity_qualified"] = (
            r["intraday_15_to_60_internal_qualified"]
            and all(compared_fields.get(("15_to_60", r["date"], k)) is True
                    for k in ("volume", "amount"))
        )
        r["daily_ohl_qualified"] = (
            r["status"] == "trading" and r["bars60"] == 4
            and not any(x.startswith("bars60:") for x in reasons)
            and all(compared_fields.get(("60_to_daily", r["date"], k)) is True
                    for k in ("open", "high", "low"))
        )
        r["adjusted_basis_qualified"] = (
            r["status"] == "trading" and "daily_backadj:invalid_row" not in reasons
            and "daily_backadj:duplicate" not in reasons
            and "daily_backadj:order_or_duplicate" not in reasons
            and all(compared_fields.get(("backadj_ratio", r["date"], k)) is True
                    for k in ("open", "high", "low", "close"))
            and compared_fields.get(("factor_ratio", r["date"], "price")) is True
        )
        r["reasons"] = sorted(set(r["reasons"]))
    trading_days = [r for r in by_day.values() if r["status"] == "trading"]
    return {
        "code": code, "bar_label_interpretation": "research_end_of_bar_unverified",
        "arrival_unknown": True, "revisions_unknown": True,
        "numerical_continuity": qualified, "qualified_for_price_descriptive_use": qualified,
        "intraday_15_to_60_internal_qualified": bool(trading_days) and all(
            r["intraday_15_to_60_internal_qualified"] for r in trading_days),
        "intraday_15_to_60_quantity_qualified": bool(trading_days) and all(
            r["intraday_15_to_60_quantity_qualified"] for r in trading_days),
        "daily_ohl_qualified": bool(trading_days) and all(r["daily_ohl_qualified"] for r in trading_days),
        "adjusted_basis_qualified": bool(trading_days) and all(r["adjusted_basis_qualified"] for r in trading_days),
        "qualified_for_full_A": False, "not_full_A": True,
        "trading_executability_unknown": True,
        "days": [by_day[d] for d in days], "continuous_runs": runs,
        "longest_run": max(runs, key=lambda r: r["trading_days"], default=None),
        "comparisons": comparisons, "findings": findings,
    }


def _number_signed(value: object) -> Decimal:
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid decimal") from None
    if not n.is_finite():
        raise ValueError("nonfinite decimal")
    return n
