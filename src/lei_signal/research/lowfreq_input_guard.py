"""Read-only, fail-closed input gate for the frozen low-frequency evaluator.

This checks a historical price diagnostic, not exchange completeness, point-in-time
fundamentals, nominal-price filters, or actual order execution. Direct use of the
old evaluator remains possible and is outside this gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

DESIGN_SHA = "c1943599b5365f484cbfa1553ccbd6c0358909e1c3a9468a115ec8cedc202539"
REQUIRED = ("date", "code", "open", "high", "low", "close", "volume", "amount", "adjustflag", "tradestatus", "isST")
SUPPORTED_CLAIM = "historical_price_diagnostic"


def _day(value):
    if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("expected YYYY-MM-DD")
    return value


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return result


def select_available_records(rows, decision_at):
    """Latest available version per (code, period); unknown/future time is refused."""
    cutoff = _instant(decision_at)
    latest = {}
    for row in rows:
        key = (row["code"], row["period"])
        at = _instant(row.get("available_at"))
        if at > cutoff:
            continue
        previous = latest.get(key)
        if previous is None or at > previous[0]:
            latest[key] = (at, row)
        elif at == previous[0] and row != previous[1]:
            raise ValueError(f"conflicting source versions: {key}")
    return [item[1] for _, item in sorted(latest.items())]


def historically_listed(metadata, asof):
    """A later exit date must not remove a security from an earlier cohort."""
    day = _day(asof)
    ipo = _day(metadata.get("ipoDate") or metadata.get("ipo_date") or metadata.get("ipo"))
    out = metadata.get("outDate") or metadata.get("out_date") or metadata.get("out")
    return ipo <= day and (not out or _day(out) > day)


def frozen_selection_execution(weights, future_status):
    """Retain frozen targets; describe unavailable orders without claiming fills."""
    targets = dict(weights)
    numeric = {}
    for code, weight in targets.items():
        try:
            value = float(weight)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid long-only target weight: {code}") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid long-only target weight: {code}")
        numeric[code] = value
    total = math.fsum(numeric.values())
    if total > 1 + 1e-12:
        raise ValueError("long-only target weight exceeds 1")
    allowed = {"traded": "observed", "halted": "halted", "missing": "missing",
               "unfillable": "unfillable", "unknown": "unknown"}
    flags = {}
    for code in targets:
        status = future_status.get(code, "missing")
        if status not in allowed:
            raise ValueError(f"unknown execution status: {code}: {status}")
        flags[code] = allowed[status]
    unfilled = math.fsum(weight for code, weight in numeric.items() if flags[code] != "observed")
    return {"target_weights": targets, "flags": flags,
            "unfilled_target_weight": unfilled, "cash_target_weight": max(0.0, 1.0 - total),
            "filled_weights": None, "real_execution_verified": False}


def inspect_contract(contract, requested_claim=SUPPORTED_CLAIM):
    """Inspect actual bound bytes and every supplied row; no performance calculation."""
    issues = defaultdict(lambda: {"count": 0, "examples": []})
    warnings = defaultdict(lambda: {"count": 0, "examples": []})

    def add(bucket, key, example):
        entry = bucket[key]
        entry["count"] += 1
        code = str(example).split(":", 1)[0]
        if code.startswith(("sh.", "sz.")):
            entry.setdefault("by_code", {})[code] = entry.setdefault("by_code", {}).get(code, 0) + 1
        if len(entry["examples"]) < 5:
            entry["examples"].append(str(example))

    if requested_claim != SUPPORTED_CLAIM:
        add(issues, "unsupported_claim", requested_claim)
    try:
        spec = json.loads(Path(contract).read_text(encoding="utf-8")) if isinstance(contract, (str, Path)) else contract
        if not isinstance(spec, dict) or spec.get("schema") != "lowfreq-evaluator-contract/1":
            raise ValueError("wrong contract schema")
    except (OSError, ValueError, TypeError) as exc:
        add(issues, "contract_unreadable", exc)
        return _report(issues, warnings, 0, 0)

    def bound(item, label):
        try:
            path = Path(item["path"]).expanduser()
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("SHA-256 mismatch")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("JSON root is not an object")
            return result
        except (OSError, KeyError, TypeError, ValueError) as exc:
            add(issues, "bound_input_invalid", f"{label}: {exc}")
            return None

    design = bound(spec.get("design", {}), "design")
    cohort = bound(spec.get("cohort", {}), "cohort")
    caldoc = bound(spec.get("calendar", {}), "calendar")
    if design is not None and (spec["design"].get("sha256") != DESIGN_SHA or
                               design.get("research_id") != "lowfreq-expanded-discovery-2026-10-19" or
                               design.get("version") != "design-v3" or
                               design.get("frozen_before_performance") is not True):
        add(issues, "design_mismatch", "frozen design identity")

    def table(doc, fields, label):
        if doc is None:
            return []
        columns, data = doc.get("fields"), doc.get("data")
        if (not isinstance(columns, list) or any(not isinstance(c, str) for c in columns)
                or len(columns) != len(set(columns)) or not set(fields) <= set(columns)
                or not isinstance(data, list)):
            add(issues, "table_schema", label)
            return []
        if not data:
            add(issues, "empty_table", label)
        rows = []
        for i, values in enumerate(data):
            if not isinstance(values, list) or len(values) != len(columns):
                add(issues, "row_width", f"{label}:{i}")
            else:
                rows.append(dict(zip(columns, values)))
        return rows

    selected, membership = [], {}
    if design is not None and cohort is not None:
        try:
            asof = _day(design["universe"]["asof"])
            size = int(design["universe"]["sample_size"])
            eligible = {}
            for row in table(cohort, ("code", "ipoDate", "outDate"), "cohort"):
                code = row["code"]
                if not (code.startswith(("sh.60", "sz.00", "sz.30")) and len(code) == 9 and code[-4:].isdigit()):
                    continue
                if row.get("type", "1") not in ("1", ""):
                    continue
                if historically_listed(row, asof):
                    if code in eligible:
                        add(issues, "duplicate_cohort_code", code)
                    eligible[code] = row
            selected = sorted(eligible, key=lambda code: (hashlib.sha256(("lowfreq-20141231-v1|" + code).encode()).hexdigest(), code))[:size]
            membership = {code: eligible[code] for code in selected}
            if not selected or size <= 0:
                add(issues, "empty_selection", size)
        except (KeyError, TypeError, ValueError) as exc:
            add(issues, "cohort_invalid", exc)
    calendar = set()
    if caldoc is not None:
        prior = ""
        for row in table(caldoc, ("calendar_date", "is_trading_day"), "calendar"):
            try:
                day = _day(row["calendar_date"])
                if day <= prior:
                    add(issues, "calendar_order", day)
                prior = day
                if row["is_trading_day"] not in ("0", "1"):
                    add(issues, "calendar_status", day)
                if row["is_trading_day"] == "1":
                    calendar.add(day)
            except (KeyError, ValueError) as exc:
                add(issues, "calendar_invalid", exc)
        if not calendar:
            add(issues, "empty_trading_calendar", "calendar")

    sources = spec.get("sources")
    if not isinstance(sources, list) or not sources:
        add(issues, "empty_sources", "sources")
        sources = []
    codes = [item.get("code") for item in sources if isinstance(item, dict)]
    if any(not isinstance(code, str) for code in codes):
        add(issues, "source_spec", "non-string code")
        codes = [code for code in codes if isinstance(code, str)]
    if len(codes) != len(set(codes)):
        add(issues, "duplicate_source_code", "sources")
    if selected and set(codes) != set(selected):
        add(issues, "source_cohort_mismatch", f"missing={len(set(selected)-set(codes))}, extra={len(set(codes)-set(selected))}")
    count_rows = 0
    for item in sources:
        if not isinstance(item, dict):
            add(issues, "source_spec", "non-object")
            continue
        code = item.get("code")
        request = item.get("request") or {}
        if not isinstance(request, dict):
            add(issues, "request_identity", f"{code}:malformed request")
            request = {}
        if item.get("status") != "ok" or request.get("code") != code or request.get("frequency") != "d" or request.get("adjustflag") != "2":
            add(issues, "request_identity", code)
        try:
            start, end = _day(request["start_date"]), _day(request["end_date"])
            if start > "2013-01-01" or end < "2026-01-15" or start > end:
                add(issues, "request_window", code)
        except (KeyError, TypeError, ValueError):
            add(issues, "request_window", code)
            start, end = "9999-12-31", "0001-01-01"
        doc = bound(item, code)
        if doc is None:
            continue
        if doc.get("error_code") != "0":
            add(issues, "response_error", code)
        rows = table(doc, REQUIRED, code)
        count_rows += len(rows)
        prior = ""
        for row in rows:
            day = row.get("date")
            try:
                day = _day(day)
            except (TypeError, ValueError) as exc:
                add(issues, "quote_date", f"{code}:{day}:{exc}")
                continue
            if day <= prior:
                add(issues, "quote_order", f"{code}:{day}")
            prior = day
            if calendar and day not in calendar:
                add(issues, "outside_calendar", f"{code}:{day}")
            if not start <= day <= end:
                add(issues, "outside_request_window", f"{code}:{day}")
            if row["code"] != code:
                add(issues, "quote_code", f"{code}:{day}:{row['code']}")
            if row["adjustflag"] != request.get("adjustflag"):
                add(issues, "returned_adjustflag", f"{code}:{day}:{row['adjustflag']}")
            status, st = row["tradestatus"], row["isST"]
            if status not in ("0", "1"):
                add(issues, "invalid_tradestatus", f"{code}:{day}:{status}")
            if st not in ("0", "1"):
                add(issues, "invalid_isST", f"{code}:{day}:{st}")
            def number(field):
                try:
                    value = float(row[field])
                    if not math.isfinite(value):
                        raise ValueError("nonfinite")
                    return value
                except (TypeError, ValueError):
                    add(issues, "invalid_number", f"{code}:{day}:{field}")
                    return None
            amount = 0.0 if status == "0" and row["amount"] in ("", None) else number("amount")
            if status == "0" and row["amount"] in ("", None):
                add(warnings, "normalized_halt_amount", f"{code}:{day}")
            volume = 0.0 if status == "0" and row["volume"] in ("", None) else number("volume")
            if status == "0" and row["volume"] in ("", None):
                add(warnings, "normalized_halt_volume", f"{code}:{day}")
            if amount is not None and amount < 0 or volume is not None and volume < 0:
                add(issues, "negative_activity", f"{code}:{day}")
            if status == "0" and amount is not None and amount > 0:
                add(issues, "halt_positive_amount", f"{code}:{day}")
            if status == "0" and volume is not None and volume > 0:
                add(issues, "halt_positive_volume", f"{code}:{day}")
            prices = {field: number(field) for field in ("open", "high", "low", "close") if status == "1"}
            if status == "1" and all(v is not None for v in prices.values()):
                if any(v <= 0 for v in prices.values()):
                    add(issues, "nonpositive_traded_price", f"{code}:{day}")
                elif prices["low"] > min(prices["open"], prices["close"]) or prices["high"] < max(prices["open"], prices["close"]) or prices["high"] < prices["low"]:
                    add(issues, "inconsistent_ohlc", f"{code}:{day}")
            if status == "1" and (amount is None or volume is None):
                add(issues, "traded_activity_missing", f"{code}:{day}")
    return _report(issues, warnings, len(sources), count_rows)


def _report(issues, warnings, source_count, row_count):
    return {"status": "blocked" if issues else "historical_only_conditional",
            "source_count": source_count, "row_count": row_count,
            "blockers": dict(issues), "warnings": dict(warnings),
            "limits": ["No exchange-complete cohort proof", "No unrevised point-in-time source proof",
                       "No nominal-price or share-size filter", "No actual order-fill proof",
                       "Old evaluator direct entry remains bypassable"]}


def guarded_run_study(contract, out, requested_claim=SUPPORTED_CLAIM):
    report = inspect_contract(contract, requested_claim)
    if report["blockers"]:
        return report
    from lei_signal.research.lowfreq_discovery import run_study
    result = run_study(contract, out)
    return {**report, "result": result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--claim", default=SUPPORTED_CLAIM)
    parser.add_argument("--out")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.run and not args.out:
        parser.error("--run requires --out")
    report = guarded_run_study(args.contract, args.out, args.claim) if args.run else inspect_contract(args.contract, args.claim)
    print(json.dumps(report, ensure_ascii=False, default=str))
    return 3 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
