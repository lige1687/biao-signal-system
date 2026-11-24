"""Read-only checks of declared monthly research-account evidence.

This checks submitted arithmetic and coverage, not trades, provenance, PIT
availability, scientific validity, or permission to run an account.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from datetime import date
from pathlib import Path
from typing import Any

MAX_MONTHS = 1200
MAX_FILE_BYTES = 256 * 1024
RETURN_TOLERANCE = {"rel_tol": 1e-9, "abs_tol": 1e-10}
FEE_TOLERANCE = {"rel_tol": 1e-9, "abs_tol": 1e-8}
ROLES = {"exploration", "validation", "holdout", "unknown"}
EXPOSURES = {"seen", "unseen_declared", "unknown"}


def _finding(code: str, location: str, detail: str) -> dict[str, str]:
    return {"code": code, "location": location, "detail": detail}


def _base() -> dict[str, Any]:
    return {
        "status": "blocked", "errors": [], "warnings": [],
        "execution_authorized": False, "scientific_validity": "not_evaluated",
        "source_verified": False, "independent_validation": "not_established",
        "continuous_metrics_allowed": {"gross": False, "net": False},
        "limitations": [
            "Submitted values and pointers do not prove source provenance or point-in-time availability.",
            "Trial history and exception branches may be incomplete; this is not an account engine or approval.",
            "continuous_metrics_allowed checks only declared calendar and return-path eligibility; cost reconciliation is separate and neither proves net fees nor scientific readiness.",
        ],
    }


def _month(value: Any) -> int | None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) is None:
        return None
    year, month = int(value[:4]), int(value[5:])
    try:
        date(year, month, 1)
    except ValueError:
        return None
    return year * 12 + month


def _number(value: Any, *, positive: bool = False, nonnegative: bool = False) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        finite = math.isfinite(value)
    except (OverflowError, ValueError):
        return False
    return finite and (not positive or value > 0) and (not nonnegative or value >= 0)


def _segments(months: list[str], usable: set[str]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    start = end = None
    count = 0
    for month in months:
        if month in usable:
            if start is None:
                start = month
            end = month
            count += 1
        elif start is not None:
            segments.append({"start": start, "end": end, "count": count})
            start = end = None
            count = 0
    if start is not None:
        segments.append({"start": start, "end": end, "count": count})
    return segments


def review_account_evidence(payload: Any) -> dict[str, Any]:
    """Validate one explicitly declared calendar and two monthly return paths."""
    out = _base()
    errors, warnings = out["errors"], out["warnings"]
    incomplete = False

    if not isinstance(payload, dict):
        errors.append(_finding("invalid_payload", "$", "JSON object required"))
        return out
    if payload.get("schema") != "research-account-evidence/1":
        errors.append(_finding("invalid_schema", "schema", "Expected research-account-evidence/1"))

    months = payload.get("expected_months")
    if not isinstance(months, list) or not 1 <= len(months) <= MAX_MONTHS:
        errors.append(_finding("invalid_calendar", "expected_months", "Nonempty list of at most 1200 months required"))
        months = []
    elif any(_month(m) is None for m in months):
        errors.append(_finding("invalid_calendar_month", "expected_months", "Strict valid YYYY-MM months required"))
        months = []
    else:
        indexes = [_month(m) for m in months]
        if any(right != left + 1 for left, right in zip(indexes, indexes[1:])):
            errors.append(_finding("nonconsecutive_calendar", "expected_months", "Months must be sorted, unique and consecutive"))

    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_MONTHS:
        errors.append(_finding("invalid_rows", "rows", "List of at most 1200 rows required"))
        rows = []
    by_month: dict[str, dict] = {}
    cost_coverage = {"candidate": {"checked": [], "not_evaluated": []},
                     "benchmark": {"checked": [], "not_evaluated": []}}
    exceptions: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        place = f"rows[{index}]"
        if not isinstance(row, dict):
            errors.append(_finding("invalid_row", place, "Object required"))
            continue
        month = row.get("month")
        if _month(month) is None:
            errors.append(_finding("invalid_month", f"{place}.month", "Strict valid YYYY-MM required"))
            continue
        if month in by_month:
            errors.append(_finding("duplicate_month", f"{place}.month", month))
            continue
        if months and month not in months:
            errors.append(_finding("outside_calendar", f"{place}.month", month))
        by_month[month] = row

        for account in ("candidate", "benchmark"):
            account_place = f"{place}.{account}"
            data = row.get(account)
            if data is None:
                incomplete = True
                cost_coverage[account]["not_evaluated"].append(month)
                continue
            if not isinstance(data, dict):
                errors.append(_finding("invalid_account", account_place, "Object required"))
                cost_coverage[account]["not_evaluated"].append(month)
                continue
            for field in ("gross_return", "net_return"):
                value = data.get(field)
                if value is None:
                    incomplete = True
                elif not _number(value):
                    errors.append(_finding("invalid_return", f"{account_place}.{field}", "Finite decimal number or null required"))
            cost = data.get("cost_reconciliation")
            if cost is None:
                incomplete = True
                cost_coverage[account]["not_evaluated"].append(month)
                continue
            if not isinstance(cost, dict):
                errors.append(_finding("invalid_cost_record", f"{account_place}.cost_reconciliation", "Object required"))
                cost_coverage[account]["not_evaluated"].append(month)
                continue
            cp = f"{account_place}.cost_reconciliation"
            if cost.get("convention") != "linear_end_period":
                warnings.append(_finding("unsupported_cost_convention", f"{cp}.convention", "Only linear_end_period is checked"))
                incomplete = True
                cost_coverage[account]["not_evaluated"].append(month)
                continue
            nav, fee, trades = cost.get("nav_start"), cost.get("fee_amount"), cost.get("trades")
            valid = True
            for field, value, positive in (("nav_start", nav, True), ("fee_amount", fee, False)):
                if value is None:
                    incomplete = True
                    warnings.append(_finding("missing_cost_evidence", f"{cp}.{field}", "Required declared cost evidence is unknown"))
                    valid = False
                elif not _number(value, positive=positive, nonnegative=not positive):
                    errors.append(_finding("invalid_cost_number", f"{cp}.{field}", "Positive NAV or nonnegative finite fee required"))
                    valid = False
            if trades is None:
                incomplete = True
                warnings.append(_finding("missing_trades", f"{cp}.trades", "Explicit trade list required"))
                valid = False
                trades = []
            elif not isinstance(trades, list):
                errors.append(_finding("invalid_trades", f"{cp}.trades", "Trade list required"))
                valid = False
                trades = []
            trade_fees = 0.0
            for leg, trade in enumerate(trades):
                tp = f"{cp}.trades[{leg}]"
                if not isinstance(trade, dict):
                    errors.append(_finding("invalid_trade", tp, "Object required"))
                    valid = False
                    continue
                values = [trade.get(k) for k in ("notional", "rate_bps", "fee_amount")]
                if any(v is None for v in values):
                    incomplete = True
                    warnings.append(_finding("missing_cost_evidence", tp, "Required trade evidence is unknown"))
                    valid = False
                    continue
                if not all(_number(v, nonnegative=True) for v in values):
                    errors.append(_finding("invalid_trade_number", tp, "Nonnegative finite notional, rate and fee required"))
                    valid = False
                    continue
                notional, rate, leg_fee = values
                expected_fee = float(notional) * float(rate) / 10_000
                if not math.isfinite(expected_fee):
                    errors.append(_finding("cost_calculation_overflow", tp, "Declared fee calculation exceeds finite precision"))
                    valid = False
                elif not math.isclose(leg_fee, expected_fee, **FEE_TOLERANCE):
                    errors.append(_finding("trade_fee_mismatch", f"{tp}.fee_amount", "Declared fee differs from notional × rate_bps / 10000"))
                    valid = False
                trade_fees += leg_fee
            if valid and not math.isclose(trade_fees, fee, **FEE_TOLERANCE):
                errors.append(_finding("total_fee_mismatch", f"{cp}.fee_amount", "Declared total differs from trade fee sum"))
                valid = False
            gross, net = data.get("gross_return"), data.get("net_return")
            if valid and _number(gross) and _number(net):
                return_difference = float(gross) - float(net)
                fee_return = float(fee) / float(nav)
                if not math.isfinite(return_difference) or not math.isfinite(fee_return):
                    errors.append(_finding("cost_calculation_overflow", account_place, "Return reconciliation exceeds finite precision"))
                    valid = False
                elif not math.isclose(return_difference, fee_return, **RETURN_TOLERANCE):
                    errors.append(_finding("return_fee_mismatch", f"{account_place}.net_return", "Gross minus net differs from fee_amount / nav_start"))
                    valid = False
            else:
                incomplete = True
            cost_coverage[account]["checked" if valid and _number(gross) and _number(net) else "not_evaluated"].append(month)

        if "selection_exceptions" not in row:
            warnings.append(_finding("exceptions_unknown", f"{place}.selection_exceptions", "No declaration; absence is not zero"))
        else:
            declared = row["selection_exceptions"]
            if not isinstance(declared, list):
                errors.append(_finding("invalid_exceptions", f"{place}.selection_exceptions", "List required"))
            else:
                for j, item in enumerate(declared):
                    ep = f"{place}.selection_exceptions[{j}]"
                    if (not isinstance(item, dict) or not isinstance(item.get("reason"), str)
                            or not item["reason"].strip() or not isinstance(item.get("affected_count"), int)
                            or isinstance(item["affected_count"], bool) or item["affected_count"] < 0
                            or not _number(item.get("selected_weight_share"))
                            or not 0 <= item["selected_weight_share"] <= 1):
                        errors.append(_finding("invalid_exception", ep, "Reason, nonnegative count and share in [0,1] required"))
                        continue
                    exceptions.append({"month": month, "reason": item["reason"],
                                       "affected_count": item["affected_count"],
                                       "selected_weight_share": item["selected_weight_share"]})
                    warnings.append(_finding("exception_review", ep, "Declared selection exception needs review"))

    role = payload.get("sample_role", "unknown")
    exposure = payload.get("prior_exposure", "unknown")
    if not isinstance(role, str) or role not in ROLES:
        errors.append(_finding("invalid_sample_role", "sample_role", "Unsupported sample role"))
    if not isinstance(exposure, str) or exposure not in EXPOSURES:
        errors.append(_finding("invalid_prior_exposure", "prior_exposure", "Unsupported exposure"))
    if role == "holdout" and exposure == "seen":
        warnings.append(_finding("holdout_already_seen", "prior_exposure", "Seen holdout cannot be called unseen"))
    elif exposure in ("unknown", "unseen_declared"):
        warnings.append(_finding("independence_not_established", "prior_exposure", "Unknown or self-declared unseen is not verified"))
    if "history_reference" in payload:
        ref = payload["history_reference"]
        if not isinstance(ref, str) or not ref.strip():
            errors.append(_finding("invalid_history_reference", "history_reference", "Nonblank pointer required"))
    else:
        warnings.append(_finding("history_unknown", "history_reference", "Trial history not supplied"))

    expected = months if all(_month(m) is not None for m in months) else []
    observed = [m for m in expected if m in by_month]
    common = {}
    for field in ("gross_return", "net_return"):
        common[field] = {m for m in expected if m in by_month and all(
            isinstance(by_month[m].get(a), dict) and _number(by_month[m][a].get(field))
            for a in ("candidate", "benchmark"))}
    missing_rows = [m for m in expected if m not in by_month]
    missing_gross = [m for m in expected if m not in common["gross_return"]]
    missing_net = [m for m in expected if m not in common["net_return"]]
    path_eligible = {field: (len(common[field]) == len(expected) and bool(expected) and all(
        by_month[m][a][field] > -1 for m in expected for a in ("candidate", "benchmark")))
        for field in ("gross_return", "net_return")}
    if missing_rows or missing_gross or missing_net:
        incomplete = True
    if any(len(common[field]) == len(expected) and not path_eligible[field]
           for field in ("gross_return", "net_return")):
        warnings.append(_finding("relative_wealth_path_ineligible", "rows", "Return <= -1 prevents continuous relative wealth path"))
    out.update({
        "coverage": {
            "expected_count": len(expected), "expected_months": expected,
            "observed_months": observed, "missing_rows": missing_rows,
            "common_gross_usable_months": [m for m in expected if m in common["gross_return"]],
            "common_net_usable_months": [m for m in expected if m in common["net_return"]],
            "missing_gross_months": missing_gross, "missing_net_months": missing_net,
            "gross_segments": _segments(expected, common["gross_return"]),
            "net_segments": _segments(expected, common["net_return"]),
        },
        "continuous_metrics_allowed": {"gross": path_eligible["gross_return"],
                                       "net": path_eligible["net_return"]},
        "cost_reconciliation": cost_coverage, "selection_exceptions": exceptions,
        "sample_role": role, "prior_exposure": exposure,
        "history_reference": payload.get("history_reference"),
    })
    if errors:
        out["status"] = "blocked"
        out["continuous_metrics_allowed"] = {"gross": False, "net": False}
    elif incomplete:
        out["status"] = "incomplete"
    elif warnings:
        out["status"] = "checked_with_warnings"
    else:
        out["status"] = "checked"
    return out


def review_file(root: str | Path, relative: str | Path) -> dict[str, Any]:
    """Read one bounded, root-relative JSON object without following payload pointers."""
    out = _base()
    binding = {"relative_path": str(relative), "sha256": None, "status": "blocked"}
    out["request_binding"] = binding
    if not isinstance(relative, (str, Path)):
        out["errors"].append(_finding("invalid_path", "request_binding.relative_path", "Path string required"))
        return out
    path = Path(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        out["errors"].append(_finding("invalid_path", "request_binding.relative_path", "Root-relative path without parent traversal required"))
        return out
    try:
        root_path = Path(root).resolve()
        target = (root_path / path).resolve()
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        out["errors"].append(_finding("invalid_path", "request_binding.relative_path", str(exc)))
        return out
    if not target.is_relative_to(root_path):
        out["errors"].append(_finding("path_escape", "request_binding.relative_path", "Resolved path escapes root"))
        return out
    try:
        if not stat.S_ISREG(target.stat().st_mode):
            out["errors"].append(_finding("not_regular_file", "request_binding.relative_path", "Regular file required"))
            return out
    except OSError as exc:
        out["errors"].append(_finding("file_unavailable", "request_binding.relative_path", str(exc)))
        return out
    try:
        with target.open("rb") as handle:
            raw = handle.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        out["errors"].append(_finding("file_unavailable", "request_binding.relative_path", str(exc)))
        return out
    if len(raw) > MAX_FILE_BYTES:
        out["errors"].append(_finding("file_too_large", "request_binding.relative_path", "Maximum 256 KiB"))
        return out
    binding["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key}")
                result[key] = value
            return result

        def reject_constant(value: str) -> None:
            raise ValueError(f"non-standard numeric constant: {value}")

        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                             parse_constant=reject_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        out["errors"].append(_finding("invalid_json", "request_binding.relative_path", str(exc)))
        return out
    reviewed = review_account_evidence(payload)
    binding["status"] = "read" if reviewed["status"] != "blocked" else "invalid_content"
    reviewed["request_binding"] = binding
    return reviewed
