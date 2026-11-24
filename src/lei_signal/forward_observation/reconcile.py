"""Read-only independent accounting reconciliation for forward observations."""

from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models import digest

_ZERO = Decimal("0")
_TOL = Decimal("0.00000001")


def _decimal(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def reconcile(db_path: str | Path) -> dict:
    """Read stored facts and independently check cash, shares, fees and valuations."""
    path = Path(db_path)
    if not path.is_file():
        return {
            "status": "not_started",
            "passed": False,
            "checks": [],
            "counts": {},
            "reasons": ["database_missing"],
        }

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []

    def record(name: str, ok: bool, detail: str | None = None) -> None:
        checks.append({"name": name, "passed": bool(ok), **({"detail": detail} if detail else {})})
        if not ok:
            reasons.append(f"{name}:{detail or 'mismatch'}")

    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        run = db.execute("SELECT spec,spec_hash FROM run WHERE id=1").fetchone()
        if run is None:
            return {
                "status": "not_started",
                "passed": False,
                "checks": [],
                "counts": {},
                "reasons": ["run_not_initialized"],
            }
        try:
            spec = json.loads(run["spec"])
            initial = _decimal(spec["initial_cash"])
            accounts = {item["id"]: item for item in spec["accounts"]}
        except (ValueError, TypeError, KeyError) as exc:
            record("spec_valid", False, str(exc))
            spec, initial, accounts = {}, _ZERO, {}
        spec_ok = bool(spec) and digest(spec) == run["spec_hash"]
        record("spec_hash", spec_ok, None if spec_ok else "stored spec hash mismatch")

        observations: dict[str, dict] = {}
        observation_rows = db.execute("SELECT id,payload_hash,payload FROM observations").fetchall()
        for row in observation_rows:
            try:
                payload = json.loads(row["payload"])
                ok = digest(payload) == row["payload_hash"]
                observations[row["id"]] = payload
            except (ValueError, TypeError):
                ok = False
            record("observation_hash", ok, None if ok else row["id"])

        orders = {row["id"]: row for row in db.execute("SELECT * FROM orders")}
        fills = db.execute("SELECT * FROM fills ORDER BY rowid").fetchall()
        fill_qty: dict[str, int] = {}
        fill_counts = 0
        for row in fills:
            fill_counts += 1
            order = orders.get(row["order_id"])
            fill_qty[row["order_id"]] = fill_qty.get(row["order_id"], 0) + row["qty"]
            try:
                qty, price, fee = int(row["qty"]), _decimal(row["price"]), _decimal(row["fee"])
                good_amount = qty > 0 and price > 0 and fee >= 0
            except (ValueError, TypeError):
                good_amount = False
            record("fill_amounts", good_amount, row["id"])
            event_row = db.execute("SELECT * FROM events WHERE id=?", (row["id"],)).fetchone()
            matched = False
            try:
                payload = json.loads(event_row["payload"]) if event_row else {}
                matched = bool(
                    event_row
                    and event_row["kind"] == "fill"
                    and event_row["account_id"] == (order["account_id"] if order else None)
                    and event_row["observation_id"] == row["observation_id"]
                    and row["observation_id"] in observations
                    and payload.get("order_id") == row["order_id"]
                    and int(payload.get("qty")) == int(row["qty"])
                    and _decimal(payload.get("price")) == _decimal(row["price"])
                    and _decimal(payload.get("fee")) == _decimal(row["fee"])
                )
            except (ValueError, TypeError, InvalidOperation):
                matched = False
            record("fill_event_match", matched, row["id"])

        for order_id, order in orders.items():
            matched_qty = fill_qty.get(order_id, 0) == order["filled_qty"]
            record("order_filled_qty", matched_qty, order_id)
            if order["requested_qty"] is not None:
                valid_order = (
                    order["requested_qty"] >= 0
                    and 0 <= order["filled_qty"] <= order["requested_qty"]
                )
                record("order_quantity_bounds", valid_order, order_id)

        for row in db.execute("SELECT * FROM events WHERE observation_id IS NOT NULL"):
            record("event_observation_binding", row["observation_id"] in observations, row["id"])

        # Replay account economics in immutable event insertion order. At each
        # valuation event, this state is the historical state for that close.
        balances: dict[str, dict[str, Decimal]] = {}
        for aid, account in accounts.items():
            if account.get("kind") in {"buy_hold", "cash"}:
                balances[aid] = {
                    "cash": initial,
                    "shares": _ZERO,
                    "receivable": _ZERO,
                    "fees": _ZERO,
                }

        valuation_count = 0
        valuation_rows = {row["id"]: row for row in db.execute("SELECT * FROM valuations")}
        for event_row in db.execute("SELECT rowid,* FROM events ORDER BY rowid"):
            aid = event_row["account_id"]
            if aid not in balances:
                continue
            kind = event_row["kind"]
            try:
                payload = json.loads(event_row["payload"])
                state = balances[aid]
                if kind == "fill":
                    qty = _decimal(payload["qty"])
                    price = _decimal(payload["price"])
                    fee = _decimal(payload["fee"])
                    cost = qty * price
                    state["cash"] -= cost + fee
                    state["shares"] += qty
                    state["fees"] += fee
                    if min(qty, price) <= 0 or fee < 0:
                        record("event_nonnegative_amounts", False, event_row["id"])
                elif kind == "split":
                    state["shares"] += _decimal(payload["delta_shares"])
                elif kind == "dividend_ex":
                    amount = _decimal(payload["amount"])
                    record("event_nonnegative_amounts", amount >= 0, event_row["id"])
                    state["receivable"] += amount
                elif kind == "dividend_pay":
                    amount = _decimal(payload["amount"])
                    record("event_nonnegative_amounts", amount >= 0, event_row["id"])
                    state["receivable"] -= amount
                    state["cash"] += amount
                elif kind == "valuation":
                    valuation_count += 1
                    oid = event_row["observation_id"]
                    observation = observations.get(oid or "")
                    vrow = valuation_rows.get(event_row["id"])
                    valid = bool(vrow and observation and vrow["observation_id"] == oid)
                    if not valid:
                        record("valuation_binding", False, event_row["id"])
                        continue
                    vp = json.loads(vrow["payload"])
                    last = _decimal(observation.get("last"))
                    cash, shares, receivable = state["cash"], state["shares"], state["receivable"]
                    equity = cash + shares * last + receivable
                    stored_cash = _decimal(vp["cash"])
                    stored_shares_value = _decimal(vp["market_value"])
                    stored_receivable = _decimal(vp["receivable"])
                    stored_fees = _decimal(vp["fees"])
                    stored_equity = _decimal(vp["equity"])
                    valuation_ok = (
                        last > 0
                        and min(cash, shares, receivable, equity) >= -_TOL
                        and abs(stored_cash - cash) <= _TOL
                        and abs(stored_shares_value - shares * last) <= _TOL
                        and abs(stored_receivable - receivable) <= _TOL
                        and abs(stored_fees - state["fees"]) <= _TOL
                        and abs(stored_equity - equity) <= _TOL
                        and vp.get("valid") is True
                    )
                    record("valuation_equity", valuation_ok, event_row["id"])
                    record(
                        "valuation_nonnegative",
                        min(cash, shares, receivable, equity) >= -_TOL,
                        event_row["id"],
                    )
                if min(state["cash"], state["shares"], state["receivable"]) < -_TOL:
                    record("account_nonnegative", False, f"{aid}:{event_row['id']}")
            except (ValueError, TypeError, KeyError, InvalidOperation, ZeroDivisionError) as exc:
                record("event_replay", False, f"{event_row['id']}:{exc}")

        orphan_valuations = set(valuation_rows) - {
            row["id"] for row in db.execute("SELECT id FROM events WHERE kind='valuation'")
        }
        record(
            "valuation_event_coverage",
            not orphan_valuations,
            ",".join(sorted(orphan_valuations)) or None,
        )
        counts = {
            "accounts": len(balances),
            "orders": len(orders),
            "fills": fill_counts,
            "observations": len(observations),
            "valuations": len(valuation_rows),
        }
    except sqlite3.Error as exc:
        record("database_read", False, str(exc))
        counts = {}
    finally:
        if db is not None:
            db.close()

    passed = bool(checks) and all(item["passed"] for item in checks)
    return {
        "status": "checked",
        "passed": passed,
        "checks": checks,
        "counts": counts,
        "reasons": reasons,
    }
