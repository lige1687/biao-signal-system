"""Read-only account-input preflight; never creates orders or infers cash/shares.

CLI: ``PYTHONPATH=src python -m lei_signal.research.account_input_review INPUT.json``
(``-`` reads stdin). The input is either the existing portfolio response/snapshot,
or a confirmed account document::

    {"account_id":"A", "as_of":"2026-10-31", "source_id":"broker-export-1",
     "confirmation":{"basis":"broker_statement","reference":"export-1"},
     "captured_at":"2026-10-31T16:00:00+08:00", "currency":"CNY",
     "cash":[{"currency":"CNY","available":1000,"as_of":"2026-10-31",
              "available_on":"2026-10-31","source_id":"broker-export-1"}],
     "holdings":[{"code":"510300","currency":"CNY","total_shares":100,
                  "sellable_shares":100,"as_of":"2026-10-31",
                  "settlement_date":"2026-10-31","source_id":"broker-export-1"}],
     "requests":[{"id":"r1","currency":"CNY","amount":500}]}

``requests`` are optional proposed cash uses, not orders. ``sale_receipts`` may
identify dependencies, but proceeds are *never* added to available cash: the
confirmed cash snapshot must already include usable proceeds. Findings are
machine-readable and a ``ready`` result only means input completeness, not
trade approval, point-in-time readiness, independently authenticated provenance,
or strategy validity. ``confirmation`` is a declaration, not verification.

A sale dependency requires a receipt with matching ``account_id``, ``currency``,
``source_id``, ``as_of``, ``status='settled'``, ``available_on`` and an explicit
``included_in_cash=true`` declaration. This declaration is not independently
reconciled against a broker balance; request totals are still capped by cash.

All requests are assessed at the account ``as_of`` date. A request carrying an
explicit ``as_of`` must match it; future funding is outside this preflight.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _captured(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        stamp = datetime.fromisoformat(value)
        return stamp.tzinfo is not None and stamp.utcoffset() is not None
    except ValueError:
        return False


def _capture_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _timestamp(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if _captured(value) else None


def review_account_input(payload: Any) -> dict[str, Any]:
    """Validate a JSON-compatible document without reading or writing state."""
    findings: list[dict[str, str]] = []

    def add(level: str, code: str, path: str, message: str) -> None:
        findings.append({"level": level, "code": code, "path": path, "message": message})

    if not isinstance(payload, dict):
        add("error", "document_type", "$", "Account input must be a JSON object.")
        return {"status": "invalid", "ready": False, "input_kind": "unknown", "findings": findings}

    # PortfolioHolding and the /portfolio DTO contain market_value, not actual
    # shares. load_snapshot uses holdings_by_group; the API uses groups[].holdings.
    legacy = "holdings_by_group" in payload or "groups" in payload
    if legacy:
        mixed = any(key in payload for key in ("account_id", "cash", "holdings", "confirmation"))
        if mixed:
            add(
                "error",
                "ambiguous_portfolio_account",
                "$",
                "Grouped valuation snapshot and flat account fields must be separate documents.",
            )
        add(
            "missing",
            "confirmed_account",
            "$",
            "Portfolio snapshot is valuation evidence, not a confirmed account input.",
        )
        for field in (
            "account_id",
            "cash",
            "confirmed_total_shares",
            "sellable_shares",
            "settlement",
            "source_id",
        ):
            add(
                "missing",
                field,
                "$",
                f"Confirmed {field} is unavailable from the portfolio snapshot.",
            )
        add(
            "warning",
            "market_value_only",
            "$",
            "market_value and implied_shares must not be treated as executable shares "
            "or available cash.",
        )
        return {
            "status": "invalid" if mixed else "incomplete",
            "ready": False,
            "input_kind": "ambiguous" if mixed else "portfolio_snapshot",
            "findings": findings,
            "availability_at_decision": "unknown",
            "provenance_verification": "declared_unverified",
        }

    kind = "declared_account"
    account_id = payload.get("account_id")
    source = payload.get("source_id")
    currency = payload.get("currency")
    if not isinstance(account_id, str) or not account_id.strip():
        add("missing", "account_id", "$.account_id", "A stable account identity is required.")
    if not isinstance(source, str) or not source.strip():
        add("missing", "source_id", "$.source_id", "A named source identity is required.")
    confirmation = payload.get("confirmation")
    if (
        not isinstance(confirmation, dict)
        or confirmation.get("basis")
        not in ("broker_statement", "custodian_statement", "user_confirmed_record")
        or not isinstance(confirmation.get("reference"), str)
        or not confirmation["reference"].strip()
    ):
        add(
            "missing",
            "confirmation",
            "$.confirmation",
            "Declare a broker/custodian statement or user-confirmed record and its "
            "reference; authenticity is not verified here.",
        )
    if (
        payload.get("estimated") is True
        or payload.get("valuation_derived") is True
        or (isinstance(confirmation, dict) and confirmation.get("estimated") is True)
    ):
        add(
            "error",
            "estimated_input",
            "$",
            "Valuation-derived account input cannot certify executable cash or shares.",
        )
    if isinstance(source, str) and source.casefold().replace("_", "-") in (
        "portfolio-estimate",
        "valuation-estimate",
        "implied-shares",
    ):
        add(
            "error",
            "valuation_source",
            "$.source_id",
            "Known valuation-derived source cannot certify executable account fields.",
        )
    if not _captured(payload.get("captured_at")):
        add(
            "missing",
            "captured_at",
            "$.captured_at",
            "A timezone-aware source capture timestamp is required.",
        )
    if not isinstance(currency, str) or not currency.strip():
        add("missing", "currency", "$.currency", "The account currency is required.")
    as_of = _date(payload.get("as_of"))
    if as_of is None:
        add("missing", "as_of", "$.as_of", "An ISO account effective date is required.")
    if (
        as_of
        and _captured(payload.get("captured_at"))
        and _capture_date(payload["captured_at"]) < as_of
    ):
        add(
            "error",
            "capture_before_effective",
            "$.captured_at",
            "Source was captured before the account effective date.",
        )
    decision_at = payload.get("decision_at")
    availability = "unknown"
    if decision_at is not None:
        decision = _timestamp(decision_at)
        captured = _timestamp(payload.get("captured_at"))
        if decision is None:
            add(
                "error",
                "decision_at",
                "$.decision_at",
                "Decision timestamp must include a timezone.",
            )
        elif captured is None:
            availability = "unknown"
        elif captured > decision or (as_of and as_of > decision.date()):
            availability = "unavailable"
            add(
                "error",
                "unavailable_at_decision",
                "$.decision_at",
                "Account evidence was not available at the decision timestamp.",
            )
        else:
            availability = "declared_available"

    def rows(name: str, required: bool = False) -> list[Any]:
        value = payload.get(name)
        if value is None and required:
            add(
                "missing",
                name,
                f"$.{name}",
                f"Confirmed {name} are required; an empty list is valid.",
            )
            return []
        if value is None:
            return []
        if not isinstance(value, list):
            add("error", "list_type", f"$.{name}", f"{name} must be a list.")
            return []
        return value

    cash_rows = rows("cash", required=True)
    holdings = rows("holdings", required=True)
    requests = rows("requests")
    receipts = rows("sale_receipts")
    cash_by_currency: dict[str, float] = {}
    seen_cash: set[str] = set()

    def identity(row: dict, path: str) -> None:
        if row.get("estimated") is True or row.get("valuation_derived") is True:
            add(
                "error",
                "estimated_input",
                path,
                "Estimated or valuation-derived data cannot certify available cash or shares.",
            )
        row_source = row.get("source_id")
        if not isinstance(row_source, str) or not row_source.strip():
            add("missing", "row_source", f"{path}.source_id", "Row source identity is required.")
        elif source and row_source != source:
            add(
                "error",
                "source_conflict",
                f"{path}.source_id",
                "Row and account source identities differ.",
            )
        row_date = _date(row.get("as_of"))
        if row_date is None:
            add("missing", "row_as_of", f"{path}.as_of", "Row effective date is required.")
        elif as_of and row_date != as_of:
            add(
                "error", "date_conflict", f"{path}.as_of", "Row and account effective dates differ."
            )

    for i, row in enumerate(cash_rows):
        path = f"$.cash[{i}]"
        if not isinstance(row, dict):
            add("error", "row_type", path, "Cash row must be an object.")
            continue
        identity(row, path)
        cur = row.get("currency")
        if not isinstance(cur, str) or not cur.strip():
            add("missing", "cash_currency", f"{path}.currency", "Cash currency is required.")
            continue
        if cur in seen_cash:
            add(
                "error",
                "duplicate_cash",
                path,
                "One confirmed available-cash row per currency is allowed.",
            )
        seen_cash.add(cur)
        if currency and cur != currency:
            add(
                "error",
                "currency_conflict",
                path,
                "Cash currency differs from account currency; no FX conversion is inferred.",
            )
        amount = _number(row.get("available"))
        if amount is None:
            add(
                "error",
                "invalid_amount",
                f"{path}.available",
                "Available cash must be finite and nonnegative.",
            )
        available_on = _date(row.get("available_on"))
        if available_on is None:
            add(
                "missing",
                "available_on",
                f"{path}.available_on",
                "Cash availability date is required.",
            )
        elif as_of and available_on > as_of:
            add(
                "error",
                "cash_not_available",
                f"{path}.available_on",
                "Cash is not available at the account effective date.",
            )
        if (
            amount is not None
            and available_on is not None
            and (as_of is None or available_on <= as_of)
            and cur not in cash_by_currency
        ):
            cash_by_currency[cur] = amount

    if currency and currency not in seen_cash:
        add(
            "missing",
            "account_cash",
            "$.cash",
            "No confirmed available cash row for account currency.",
        )

    seen_codes: set[str] = set()
    for i, row in enumerate(holdings):
        path = f"$.holdings[{i}]"
        if not isinstance(row, dict):
            add("error", "row_type", path, "Holding row must be an object.")
            continue
        identity(row, path)
        if "implied_shares" in row:
            add(
                "error",
                "implied_not_confirmed",
                path,
                "implied_shares is valuation-derived, even when total_shares is also supplied.",
            )
        code = row.get("code")
        if not isinstance(code, str) or not code.strip():
            add("missing", "holding_code", f"{path}.code", "Security identity is required.")
        elif code in seen_codes:
            add(
                "error",
                "duplicate_security",
                f"{path}.code",
                "Security appears more than once in this account input.",
            )
        else:
            seen_codes.add(code)
        if not isinstance(row.get("currency"), str) or not row["currency"].strip():
            add("missing", "holding_currency", f"{path}.currency", "Holding currency is required.")
        elif currency and row["currency"] != currency:
            add(
                "error",
                "currency_conflict",
                f"{path}.currency",
                "Holding and account currencies differ; no FX conversion is inferred.",
            )
        total = _number(row.get("total_shares"))
        sellable = _number(row.get("sellable_shares"))
        if total is None:
            add(
                "missing" if "total_shares" not in row else "error",
                "total_shares",
                f"{path}.total_shares",
                "Confirmed total shares must be finite and nonnegative.",
            )
        if sellable is None:
            add(
                "missing" if "sellable_shares" not in row else "error",
                "sellable_shares",
                f"{path}.sellable_shares",
                "Confirmed sellable shares must be finite and nonnegative.",
            )
        if total is not None and sellable is not None and sellable > total:
            add("error", "sellable_exceeds_total", path, "Sellable shares exceed total shares.")
        settled = _date(row.get("settlement_date"))
        if settled is None:
            add(
                "missing",
                "settlement_date",
                f"{path}.settlement_date",
                "Confirmed settlement date is required.",
            )
        elif as_of and settled > as_of and sellable is not None and sellable > 0:
            add(
                "error",
                "unsettled_sellable",
                path,
                "Positive sellable shares conflict with future settlement date.",
            )

    receipt_by_id: dict[str, dict] = {}
    for i, row in enumerate(receipts):
        path = f"$.sale_receipts[{i}]"
        if not isinstance(row, dict):
            add("error", "row_type", path, "Sale receipt must be an object.")
            continue
        identity(row, path)
        rid, status = row.get("id"), row.get("status")
        if not isinstance(rid, str) or not rid.strip() or rid in receipt_by_id:
            add("error", "receipt_id", path, "Sale receipt needs a unique nonempty id.")
        else:
            receipt_by_id[rid] = row
        if not isinstance(row.get("account_id"), str) or not row["account_id"].strip():
            add(
                "missing",
                "sale_account_id",
                f"{path}.account_id",
                "Sale account identity is required.",
            )
        elif account_id and row["account_id"] != account_id:
            add(
                "error",
                "sale_account_conflict",
                f"{path}.account_id",
                "Sale belongs to a different account.",
            )
        if not isinstance(row.get("currency"), str) or not row["currency"].strip():
            add("missing", "sale_currency", f"{path}.currency", "Sale currency is required.")
        elif currency and row["currency"] != currency:
            add(
                "error",
                "sale_currency_conflict",
                f"{path}.currency",
                "Sale currency differs from account currency.",
            )
        if status not in ("failed", "pending", "settled"):
            add(
                "error",
                "receipt_status",
                f"{path}.status",
                "Status must be failed, pending, or settled.",
            )
        if status == "settled":
            available_on = _date(row.get("available_on"))
            if available_on is None:
                add(
                    "missing",
                    "sale_available_on",
                    f"{path}.available_on",
                    "Settled sale cash availability date is required.",
                )
            elif as_of and available_on > as_of:
                add(
                    "error",
                    "sale_cash_unavailable",
                    f"{path}.available_on",
                    "Sale cash is not available at account effective date.",
                )
            if row.get("included_in_cash") is not True:
                add(
                    "missing" if "included_in_cash" not in row else "error",
                    "sale_not_in_cash",
                    f"{path}.included_in_cash",
                    "Declare that settled proceeds are already included in confirmed "
                    "available cash; no proceeds are added here.",
                )

    seen_requests: set[str] = set()
    requested_by_currency: dict[str, float] = {}
    for i, row in enumerate(requests):
        path = f"$.requests[{i}]"
        if not isinstance(row, dict):
            add("error", "row_type", path, "Cash request must be an object.")
            continue
        rid, cur = row.get("id"), row.get("currency")
        if "as_of" in row:
            request_date = _date(row["as_of"])
            if request_date is None or (as_of and request_date != as_of):
                add(
                    "error",
                    "request_date_conflict",
                    f"{path}.as_of",
                    "Request date must match the account effective date.",
                )
        if not isinstance(rid, str) or not rid.strip() or rid in seen_requests:
            add("error", "request_id", f"{path}.id", "Cash request needs a unique nonempty id.")
        else:
            seen_requests.add(rid)
        if not isinstance(cur, str) or not cur.strip():
            add("missing", "request_currency", f"{path}.currency", "Request currency is required.")
        elif currency and cur != currency:
            add(
                "error",
                "currency_conflict",
                f"{path}.currency",
                "Request currency differs from account currency.",
            )
        amount = _number(row.get("amount"))
        if amount is None:
            add(
                "error",
                "invalid_amount",
                f"{path}.amount",
                "Cash request must be finite and nonnegative.",
            )
        elif isinstance(cur, str) and cur:
            combined = requested_by_currency.get(cur, 0) + amount
            if not math.isfinite(combined):
                add(
                    "error",
                    "request_sum_overflow",
                    "$.requests",
                    "Combined cash requests are not finite.",
                )
            else:
                requested_by_currency[cur] = combined
        sale_id = row.get("depends_on_sale_id")
        if sale_id is not None:
            if not isinstance(sale_id, str) or sale_id not in receipt_by_id:
                add(
                    "error",
                    "unknown_sale",
                    f"{path}.depends_on_sale_id",
                    "Referenced sale receipt is absent.",
                )
            else:
                sale = receipt_by_id[sale_id]
                if (
                    sale.get("status") != "settled"
                    or sale.get("included_in_cash") is not True
                    or (
                        as_of
                        and (
                            _date(sale.get("available_on")) is None
                            or _date(sale.get("available_on")) > as_of
                        )
                    )
                ):
                    add(
                        "error",
                        "sale_cash_unavailable",
                        f"{path}.depends_on_sale_id",
                        "Sale is not settled and included in confirmed available cash "
                        "at this date.",
                    )
                if sale.get("currency") != cur:
                    add(
                        "error",
                        "sale_request_currency_conflict",
                        f"{path}.depends_on_sale_id",
                        "Sale and request currencies differ.",
                    )
                if sale.get("account_id") != account_id:
                    add(
                        "error",
                        "sale_account_conflict",
                        f"{path}.depends_on_sale_id",
                        "Sale and request account identities differ.",
                    )
                if sale.get("source_id") != source:
                    add(
                        "error",
                        "sale_source_conflict",
                        f"{path}.depends_on_sale_id",
                        "Sale and account source identities differ.",
                    )
    for cur, requested in requested_by_currency.items():
        if cur in cash_by_currency and requested > cash_by_currency[cur] + 1e-9:
            add(
                "error",
                "shared_cash_exceeded",
                "$.requests",
                f"Combined {cur} requests exceed confirmed available cash; the same "
                "cash cannot fund multiple requests.",
            )

    status = (
        "invalid"
        if any(f["level"] == "error" for f in findings)
        else ("incomplete" if any(f["level"] == "missing" for f in findings) else "ready")
    )
    return {
        "status": status,
        "ready": status == "ready",
        "input_kind": kind,
        "account_id": account_id if isinstance(account_id, str) else None,
        "as_of": payload.get("as_of") if isinstance(payload.get("as_of"), str) else None,
        "source_id": source if isinstance(source, str) else None,
        "availability_at_decision": availability,
        "provenance_verification": "declared_unverified",
        "cash_available": cash_by_currency,
        "cash_requested": requested_by_currency,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only confirmed account input audit")
    parser.add_argument("input", help="JSON file path, or - for stdin")
    args = parser.parse_args(argv)
    try:
        raw = (
            sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        )
        payload = json.loads(raw)
        result = review_account_input(payload)
    except (OSError, ValueError) as exc:
        result = {
            "status": "invalid",
            "ready": False,
            "input_kind": "unknown",
            "findings": [
                {"level": "error", "code": "input_read", "path": "$", "message": str(exc)}
            ],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
