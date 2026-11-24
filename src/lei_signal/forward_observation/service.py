"""Deterministic forward observation of separate virtual cash accounts.

Only explicit calls may write the supplied SQLite path. No quote, broker, or
scheduler is called here. Existing historical research is never imported.
"""

from __future__ import annotations

import json
import os
from contextlib import closing
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

from .models import canonical, digest, frozen_spec, instant, money
from .store import event, read_only, transaction


def _spec(db) -> dict:
    row = db.execute("SELECT spec FROM run WHERE id=1").fetchone()
    if not row:
        raise ValueError("forward observation not initialized")
    return json.loads(row[0])


def initialize(db_path: str | Path, config: dict, now: str) -> dict:
    """Freeze the exact version and queue one passive buy order, once."""
    at = instant(now).isoformat()
    with transaction(db_path) as db:
        row = db.execute("SELECT spec,spec_hash FROM run WHERE id=1").fetchone()
        if row:
            saved = json.loads(row["spec"])
            if saved["config_hash"] != digest(config):
                raise ValueError("frozen configuration changed")
        else:
            spec = frozen_spec(config, at)
            db.execute(
                "INSERT INTO run(id,spec,spec_hash,last_run_at) VALUES(1,?,?,?)",
                (canonical(spec), digest(spec), at),
            )
            event(
                db,
                id="freeze:" + digest(spec)[:20],
                at=at,
                kind="frozen",
                payload={"spec_hash": digest(spec)},
            )
            symbol = spec["assets"][0]["symbol"]
            for account in spec["accounts"]:
                aid = account["id"]
                if account["kind"] == "buy_hold":
                    oid = "initial-buy:" + aid + ":" + digest(spec)[:16]
                    db.execute(
                        "INSERT INTO orders(id,account_id,created_at,symbol,status) "
                        "VALUES(?,?,?,?,?)",
                        (oid, aid, at, symbol, "queued"),
                    )
                    event(
                        db,
                        id="decision:" + oid,
                        at=at,
                        kind="decision",
                        account_id=aid,
                        payload={
                            "action": "queue_initial_buy",
                            "order_id": oid,
                            "known_at": at,
                            "cash_budget": spec["initial_cash"],
                        },
                    )
                    event(
                        db,
                        id="order:" + oid,
                        at=at,
                        kind="order_queued",
                        account_id=aid,
                        payload={"order_id": oid, "symbol": symbol, "tif": "GTC"},
                    )
                elif account["kind"] == "cash":
                    event(
                        db,
                        id="decision:cash:" + aid,
                        at=at,
                        kind="decision",
                        account_id=aid,
                        payload={"action": "hold_cash", "cash_interest_rate": "0"},
                    )
                elif account["kind"] not in {"blocked", "external_pending"}:
                    raise ValueError("unsupported strategy kind")
    return build_dashboard(db_path, config, at)


def _state(db, aid: str, initial: Decimal) -> dict[str, Decimal]:
    cash, shares, receivable, fees = initial, Decimal(0), Decimal(0), Decimal(0)
    rows = db.execute(
        "SELECT kind,payload FROM events WHERE account_id=? AND kind IN "
        "('fill','split','dividend_ex','dividend_pay') ORDER BY rowid",
        (aid,),
    ).fetchall()
    for row in rows:
        p = json.loads(row["payload"])
        if row["kind"] == "fill":
            q, price, fee = Decimal(p["qty"]), Decimal(p["price"]), Decimal(p["fee"])
            cash -= q * price + fee
            shares += q
            fees += fee
        elif row["kind"] == "split":
            shares += Decimal(p["delta_shares"])
        elif row["kind"] == "dividend_ex":
            receivable += Decimal(p["amount"])
        elif row["kind"] == "dividend_pay":
            amount = Decimal(p["amount"])
            receivable -= amount
            cash += amount
    if min(cash, shares, receivable) < Decimal("-0.00000001"):
        raise ValueError("negative account balance")
    return {"cash": cash, "shares": shares, "receivable": receivable, "fees": fees}


def _shares_before(db, aid: str, initial: Decimal, day: str) -> Decimal:
    """Entitlement uses shares acquired before the ex date, not today's fills."""
    shares = Decimal(0)
    for row in db.execute(
        "SELECT kind,at,payload FROM events WHERE account_id=? "
        "AND kind IN ('fill','split') ORDER BY rowid",
        (aid,),
    ):
        if instant(row["at"]).date().isoformat() >= day:
            continue
        payload = json.loads(row["payload"])
        shares += Decimal(payload["qty"] if row["kind"] == "fill" else payload["delta_shares"])
    return shares


def _actions(db, observation: dict, spec: dict, at: str) -> None:
    day = instant(observation["source_time"]).date().isoformat()
    for action in observation.get("corporate_actions") or []:
        key = str(action.get("id") or "")
        if not key or action.get("type") not in {"split", "cash_dividend", "dividend_payment"}:
            raise ValueError("corporate action needs stable id and supported type")
        prior = db.execute("SELECT payload FROM actions WHERE id=?", (key,)).fetchone()
        body = canonical(action)
        if prior and prior[0] != body:
            raise ValueError("corporate action revision needs new id")
        if not prior:
            effective = action.get("ex_date") or action.get("pay_date")
            if not effective or (
                action.get("pay_date")
                and action.get("ex_date")
                and action["pay_date"] < action["ex_date"]
            ):
                raise ValueError("invalid corporate action dates")
            econ = (
                action.get("economic_id") or f"{action['type']}:{observation['symbol']}:{effective}"
            )
            if action["type"] == "cash_dividend" and money(action.get("amount")) < 0:
                raise ValueError("negative dividend")
            if action["type"] == "split":
                money(action.get("ratio"), positive=True)
            db.execute(
                "INSERT INTO actions(id,economic_key,payload,ex_date,pay_date,status) "
                "VALUES(?,?,?,?,?,?)",
                (key, econ, body, effective, action.get("pay_date"), "recorded"),
            )
    for row in db.execute(
        "SELECT id,payload,ex_date,pay_date FROM actions ORDER BY ex_date,id"
    ).fetchall():
        action = json.loads(row["payload"])
        if row["ex_date"] > day:
            continue
        for account in spec["accounts"]:
            if account["kind"] != "buy_hold":
                continue
            aid = account["id"]
            entitled = _shares_before(db, aid, money(spec["initial_cash"]), row["ex_date"])
            if action["type"] == "split":
                ratio = money(action.get("ratio"), positive=True)
                eid = f"split:{row['id']}:{aid}"
                if not db.execute("SELECT 1 FROM events WHERE id=?", (eid,)).fetchone():
                    event(
                        db,
                        id=eid,
                        at=at,
                        kind="split",
                        account_id=aid,
                        payload={
                            "action_id": row["id"],
                            "ratio": str(ratio),
                            "delta_shares": str(entitled * (ratio - 1)),
                        },
                    )
            elif action["type"] == "cash_dividend":
                eid = f"dividend-ex:{row['id']}:{aid}"
                if not db.execute("SELECT 1 FROM events WHERE id=?", (eid,)).fetchone():
                    amount = entitled * money(action.get("amount"))
                    event(
                        db,
                        id=eid,
                        at=at,
                        kind="dividend_ex",
                        account_id=aid,
                        payload={"action_id": row["id"], "amount": str(amount)},
                    )
                if row["pay_date"] and row["pay_date"] <= day:
                    payid = f"dividend-pay:{row['id']}:{aid}"
                    if not db.execute("SELECT 1 FROM events WHERE id=?", (payid,)).fetchone():
                        original = db.execute(
                            "SELECT payload FROM events WHERE id=?", (eid,)
                        ).fetchone()
                        amount = json.loads(original[0])["amount"]
                        event(
                            db,
                            id=payid,
                            at=at,
                            kind="dividend_pay",
                            account_id=aid,
                            payload={"action_id": row["id"], "amount": amount},
                        )
            else:
                distribution_id = action.get("distribution_id")
                original = db.execute(
                    "SELECT payload FROM events WHERE id=?",
                    (f"dividend-ex:{distribution_id}:{aid}",),
                ).fetchone()
                if original and action["pay_date"] <= day:
                    payid = f"dividend-pay:{distribution_id}:{aid}"
                    if not db.execute("SELECT 1 FROM events WHERE id=?", (payid,)).fetchone():
                        amount = json.loads(original[0])["amount"]
                        event(
                            db,
                            id=payid,
                            at=at,
                            kind="dividend_pay",
                            account_id=aid,
                            payload={
                                "action_id": distribution_id,
                                "amount": amount,
                                "payment_evidence_id": row["id"],
                            },
                        )


def _quality(observation: dict, spec: dict, at: str, *, valuation: bool = False) -> list[str]:
    reasons = list(observation.get("reasons") or [])
    source = instant(observation["source_time"])
    received = instant(observation["received_at"])
    now = instant(at)
    if source < instant(spec["started_at"]) or not (source <= received <= now):
        reasons.append("source_time_outside_forward_sequence")
    age = spec["max_quote_age_seconds"]
    if not valuation and (
        (received - source).total_seconds() > age or (now - received).total_seconds() > age
    ):
        reasons.append("stale_quote")
    if observation.get("quality") not in {"valid", "ok", True}:
        reasons.append("source_quality_not_valid")
    if not valuation and not observation.get("market_open"):
        reasons.append("market_not_open")
    for field in ("last",) if valuation else ("last", "bid", "ask"):
        try:
            money(observation.get(field), positive=True)
        except ValueError:
            reasons.append(f"{field}_missing_or_invalid")
    if (
        observation.get("corporate_actions_checked_through") is None
        or observation["corporate_actions_checked_through"] < source.date().isoformat()
    ):
        reasons.append("corporate_actions_not_checked")
    return list(dict.fromkeys(reasons))


def _action_quality(db, observation: dict, spec: dict) -> list[str]:
    day = instant(observation["source_time"]).date().isoformat()
    first = instant(spec["started_at"]).date().isoformat()
    reasons = []
    for action in observation.get("corporate_actions") or []:
        effective = action.get("ex_date") or action.get("pay_date")
        if not action.get("id") or not effective:
            reasons.append("corporate_action_identity_or_date_missing")
            continue
        old = db.execute("SELECT payload FROM actions WHERE id=?", (str(action["id"]),)).fetchone()
        if old:
            if old[0] != canonical(action):
                reasons.append("corporate_action_revision_pending")
            continue
        econ = (
            action.get("economic_id") or f"{action.get('type')}:{observation['symbol']}:{effective}"
        )
        previous = db.execute("SELECT id FROM actions WHERE economic_key=?", (econ,)).fetchone()
        if previous:
            reasons.append("corporate_action_revision_pending")
        elif first <= effective < day and action.get("type") != "dividend_payment":
            reasons.append("late_corporate_action_pending_reconciliation")
    return list(dict.fromkeys(reasons))


def _coverage_quality(db, observation: dict, spec: dict) -> list[str]:
    """Require an unbroken checked interval since the actual start."""
    checked_from = observation.get("corporate_actions_checked_from")
    checked_through = observation.get("corporate_actions_checked_through")
    if not checked_from or not checked_through:
        return ["corporate_actions_coverage_unknown"]
    try:
        first = date.fromisoformat(checked_from)
        last = date.fromisoformat(checked_through)
    except (TypeError, ValueError):
        return ["corporate_actions_coverage_invalid"]
    if first > last:
        return ["corporate_actions_coverage_invalid"]
    row = db.execute("SELECT actions_verified_through FROM run WHERE id=1").fetchone()
    prior = date.fromisoformat(row[0]) if row and row[0] else None
    start = instant(spec["started_at"]).date()
    if first > (prior + timedelta(days=1) if prior else start):
        return ["corporate_actions_coverage_gap"]
    return []


def process_observation(db_path: str | Path, observation: dict, now: str) -> dict:
    """Record an actual post-freeze quote and advance only eligible virtual orders."""
    at = instant(now).isoformat()
    oid = str(observation.get("id") or "")
    if not oid:
        raise ValueError("observation id required")
    declared = str(observation.get("hash") or "")
    body = {k: v for k, v in observation.items() if k != "hash"}
    calculated = digest(body)
    if declared and declared != calculated:
        raise ValueError("observation hash does not match content")
    with transaction(db_path) as db:
        spec = _spec(db)
        source_at = instant(observation["source_time"]).isoformat()
        received_at = instant(observation["received_at"]).isoformat()
        prior = db.execute("SELECT payload_hash FROM observations WHERE id=?", (oid,)).fetchone()
        if prior:
            if prior[0] != calculated:
                raise ValueError("observation identity conflict")
            return build_dashboard(db_path, None, at)
        if observation.get("symbol") != spec["assets"][0]["symbol"]:
            raise ValueError("symbol outside frozen universe")
        duplicate_source = (
            db.execute(
                "SELECT 1 FROM observations WHERE source_at=? "
                "AND json_extract(payload,'$.symbol')=? LIMIT 1",
                (source_at, observation["symbol"]),
            ).fetchone()
            is not None
        )
        last_source = db.execute("SELECT last_source_at FROM run WHERE id=1").fetchone()[0]
        out_of_order = bool(last_source and instant(source_at) < instant(last_source))
        db.execute(
            "INSERT INTO observations(id,payload_hash,payload,source_at,received_at) "
            "VALUES(?,?,?,?,?)",
            (oid, calculated, canonical(body), source_at, received_at),
        )
        db.execute("UPDATE run SET last_run_at=? WHERE id=1", (at,))
        reasons = _quality(observation, spec, at)
        valuation_reasons = (
            _quality(observation, spec, at, valuation=True) if observation.get("is_eod") else []
        )
        action_reasons = _action_quality(db, observation, spec)
        coverage_reasons = _coverage_quality(db, observation, spec)
        reasons.extend(action_reasons + coverage_reasons)
        valuation_reasons.extend(action_reasons + coverage_reasons)
        if duplicate_source:
            reasons.append("duplicate_source_time")
        if out_of_order:
            reasons.append("out_of_order_source_time")
            valuation_reasons.append("out_of_order_source_time")
        accepted = not reasons or (observation.get("is_eod") and not valuation_reasons)
        if accepted:
            prior_coverage = db.execute(
                "SELECT actions_verified_through FROM run WHERE id=1"
            ).fetchone()[0]
            db.execute(
                "UPDATE run SET last_source_at=?,actions_verified_through=? WHERE id=1",
                (
                    source_at,
                    max(
                        prior_coverage or observation["corporate_actions_checked_through"],
                        observation["corporate_actions_checked_through"],
                    ),
                ),
            )
        event(
            db,
            id="source:" + oid,
            at=at,
            kind="source",
            observation_id=oid,
            payload={
                "source": observation.get("source"),
                "source_time": source_at,
                "received_at": received_at,
                "quality": observation.get("quality"),
                "reasons": reasons,
                "valuation_reasons": valuation_reasons,
                "hash": calculated,
            },
        )
        if reasons:
            event(
                db,
                id="wait:" + oid,
                at=at,
                kind="waiting",
                observation_id=oid,
                payload={"reasons": reasons},
            )
        if accepted:
            _actions(db, observation, spec, at)
        if not reasons and not observation.get("is_eod"):
            for account in spec["accounts"]:
                if account["kind"] != "buy_hold":
                    continue
                aid = account["id"]
                order = db.execute(
                    "SELECT * FROM orders WHERE account_id=? AND status IN ('queued','partial')",
                    (aid,),
                ).fetchone()
                if not order or instant(order["created_at"]) >= instant(source_at):
                    continue
                ask = money(observation["ask"], positive=True)
                slippage = money(spec["execution"]["slippage_rate"])
                commission = money(spec["execution"]["commission_rate"])
                price = ask * (1 + slippage)
                state = _state(db, aid, money(spec["initial_cash"]))
                lot = spec["execution"]["lot"]
                request_qty = order["requested_qty"]
                if request_qty is None:
                    request_qty = (
                        int(
                            (state["cash"] / (price * (1 + commission)) / lot).to_integral_value(
                                rounding=ROUND_DOWN
                            )
                        )
                        * lot
                    )
                    db.execute(
                        "UPDATE orders SET requested_qty=?,first_quote_id=? WHERE id=?",
                        (request_qty, oid, order["id"]),
                    )
                if request_qty == 0:
                    db.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order["id"],))
                    event(
                        db,
                        id=f"cancel:{order['id']}:{oid}",
                        at=at,
                        kind="cancelled",
                        account_id=aid,
                        observation_id=oid,
                        payload={"order_id": order["id"], "reason": "cannot_afford_one_lot"},
                    )
                    continue
                remaining = request_qty - order["filled_qty"]
                size = observation.get("ask_size")
                available = 0 if size is None else int(money(size) // lot) * lot
                affordable = (
                    int(
                        (state["cash"] / (price * (1 + commission)) / lot).to_integral_value(
                            rounding=ROUND_DOWN
                        )
                    )
                    * lot
                )
                qty = min(remaining, available, affordable)
                if qty > 0:
                    fee = price * qty * commission
                    fid = f"fill:{order['id']}:{oid}"
                    db.execute(
                        "INSERT INTO fills(id,order_id,observation_id,at,qty,price,fee) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (fid, order["id"], oid, at, qty, str(price), str(fee)),
                    )
                    event(
                        db,
                        id=fid,
                        at=at,
                        kind="fill",
                        account_id=aid,
                        observation_id=oid,
                        payload={
                            "order_id": order["id"],
                            "qty": qty,
                            "price": str(price),
                            "fee": str(fee),
                        },
                    )
                    filled = order["filled_qty"] + qty
                    status = "filled" if filled == request_qty else "partial"
                    db.execute(
                        "UPDATE orders SET filled_qty=?,status=? WHERE id=?",
                        (filled, status, order["id"]),
                    )
                    if status == "partial":
                        event(
                            db,
                            id=f"partial:{order['id']}:{oid}",
                            at=at,
                            kind="partially_filled",
                            account_id=aid,
                            observation_id=oid,
                            payload={
                                "order_id": order["id"],
                                "remaining_qty": request_qty - filled,
                            },
                        )
                else:
                    event(
                        db,
                        id=f"unfilled:{order['id']}:{oid}",
                        at=at,
                        kind="waiting",
                        account_id=aid,
                        observation_id=oid,
                        payload={"reason": "no_quote_size_or_cash_or_lot", "order_id": order["id"]},
                    )
        if observation.get("is_eod") and not valuation_reasons:
            _value_day(db, spec, observation, at)
        elif observation.get("is_eod"):
            event(
                db,
                id="valuation-wait:" + oid,
                at=at,
                kind="waiting",
                observation_id=oid,
                payload={"reasons": valuation_reasons, "purpose": "valuation"},
            )
    return build_dashboard(db_path, None, at)


def _value_day(db, spec: dict, observation: dict, at: str) -> None:
    day = instant(observation["source_time"]).date().isoformat()
    last = money(observation["last"], positive=True)
    for account in spec["accounts"]:
        if account["kind"] not in {"cash", "buy_hold"}:
            continue
        aid = account["id"]
        state = (
            _state(db, aid, money(spec["initial_cash"]))
            if account["kind"] == "buy_hold"
            else {
                "cash": money(spec["initial_cash"]),
                "shares": Decimal(0),
                "receivable": Decimal(0),
                "fees": Decimal(0),
            }
        )
        market = state["shares"] * last
        equity = state["cash"] + market + state["receivable"]
        if equity < 0:
            raise ValueError("negative equity")
        payload = {
            "date": day,
            "equity": float(equity),
            "cash": float(state["cash"]),
            "receivable": float(state["receivable"]),
            "market_value": float(market),
            "nav": float(equity / money(spec["initial_cash"])),
            "fees": float(state["fees"]),
            "exposure_pct": float(market / equity * 100) if equity else 0.0,
            "source_time": observation["source_time"],
            "valid": True,
            "stale": False,
            "provisional": False,
        }
        existing = db.execute(
            "SELECT id,payload FROM valuations WHERE account_id=? AND day=?", (aid, day)
        ).fetchone()
        if existing:
            # A later quote does not silently revise the day's frozen first close.
            continue
        db.execute(
            "INSERT INTO valuations(id,account_id,day,observation_id,payload) VALUES(?,?,?,?,?)",
            (f"valuation:{aid}:{day}", aid, day, observation["id"], canonical(payload)),
        )
        event(
            db,
            id=f"valuation:{aid}:{day}",
            at=at,
            kind="valuation",
            account_id=aid,
            observation_id=observation["id"],
            payload={"date": day, "equity": str(equity)},
        )


def _metrics(rows: list[dict], started_at: str) -> dict:
    if not rows:
        return {
            "cumulative_return_pct": None,
            "annualized_return_pct": None,
            "sharpe": None,
            "max_drawdown_pct": None,
            "observations": 0,
            "wait_days": None,
            "wait_reason": "not_calculated",
            "reason": "no_valid_eod_valuation",
        }
    peak = 1.0
    max_dd = 0.0
    for row in rows:
        peak = max(peak, row["nav"])
        row["drawdown_pct"] = (row["nav"] / peak - 1) * 100
        max_dd = min(max_dd, row["drawdown_pct"])
    elapsed = (instant(rows[-1]["source_time"]) - instant(started_at)).days
    cumulative = (rows[-1]["nav"] - 1) * 100
    annualized = ((rows[-1]["nav"] ** (365.25 / elapsed) - 1) * 100) if elapsed >= 365 else None
    # Sharpe is intentionally withheld until a full year of valid daily returns.
    returns = [b["nav"] / a["nav"] - 1 for a, b in zip(rows, rows[1:], strict=False)]
    sharpe = None
    span = (instant(rows[-1]["source_time"]) - instant(rows[0]["source_time"])).days
    if len(returns) >= 252 and span <= len(returns) * 1.7:
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        if variance > 0:
            sharpe = mean / variance**0.5 * 252**0.5
    return {
        "cumulative_return_pct": cumulative,
        "annualized_return_pct": annualized,
        "sharpe": sharpe,
        "max_drawdown_pct": max_dd,
        "observations": len(rows),
        "wait_days": None,
        "wait_reason": "not_calculated",
        "reason": None
        if annualized is not None and sharpe is not None
        else "insufficient_duration_or_variation",
    }


def build_dashboard(
    db_path: str | Path, config: dict | None, now: str, range: str = "since_start"
) -> dict:
    """Read-only view; absent DB is an explicit not-started state."""
    if range not in {"since_start", "common"}:
        raise ValueError("range must be since_start or common")
    at = instant(now).isoformat()
    db = read_only(db_path)
    if db is None:
        accounts = config.get("accounts", []) if config else []
        return {
            "schema_version": 1,
            "generated_at": at,
            "range": range,
            "run": {
                "status": "not_started",
                "frozen_at": None,
                "started_at": None,
                "last_run_at": None,
                "last_source_at": None,
                "next_run_at": None,
                "runner": None,
            },
            "accounts": [_empty_account(a) for a in accounts],
            "decisions": [],
            "health": ["not_started"],
            "sources": [],
            "pending": ["等待真实启用与合格报价"],
            "reconciliation": {
                "status": "not_available",
                "passed": None,
                "reasons": ["reconciliation_not_recorded"],
            },
        }
    with closing(db):
        row = db.execute("SELECT * FROM run WHERE id=1").fetchone()
        if not row:
            return build_dashboard("/nonexistent-forward-observation-ledger", config, at, range)
        spec = json.loads(row["spec"])
        config_changed = config is not None and digest(config) != spec["config_hash"]
        observations = db.execute(
            "SELECT * FROM observations ORDER BY source_at DESC,id DESC LIMIT 100"
        ).fetchall()
        latest = None
        for observed in observations:
            candidate = json.loads(observed["payload"])
            source_event = db.execute(
                "SELECT payload FROM events WHERE id=?", ("source:" + observed["id"],)
            ).fetchone()
            if (
                source_event
                and not json.loads(source_event[0]).get("reasons")
                and not _quality(candidate, spec, at)
            ):
                latest = candidate
                break
        account_views = []
        for account in spec["accounts"]:
            view = _empty_account(account)
            view["rules"] = account["rules"]
            aid = account["id"]
            if account["kind"] in {"blocked", "external_pending"}:
                view["status"] = account["kind"]
                account_views.append(view)
                continue
            view["frozen_at"] = spec["frozen_at"]
            view["started_at"] = spec["started_at"]
            valuation_rows = db.execute(
                "SELECT payload FROM valuations WHERE account_id=? ORDER BY day", (aid,)
            ).fetchall()
            series = [json.loads(r[0]) for r in valuation_rows]
            view["series"] = series
            view["status"] = "observing" if series else "waiting_quote"
            view["orders"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM orders WHERE account_id=? ORDER BY created_at,id", (aid,)
                )
            ]
            fills = db.execute(
                "SELECT at FROM fills f JOIN orders o ON o.id=f.order_id "
                "WHERE o.account_id=? ORDER BY f.at LIMIT 1",
                (aid,),
            ).fetchone()
            view["first_fill_at"] = fills[0] if fills else None
            if account["kind"] == "buy_hold" and not fills:
                view["status"] = "waiting_execution"
            decision = db.execute(
                "SELECT at FROM events WHERE account_id=? AND kind='decision' "
                "ORDER BY rowid LIMIT 1",
                (aid,),
            ).fetchone()
            view["first_decision_at"] = decision[0] if decision else None
            state = (
                _state(db, aid, money(spec["initial_cash"]))
                if account["kind"] == "buy_hold"
                else {
                    "cash": money(spec["initial_cash"]),
                    "shares": Decimal(0),
                    "receivable": Decimal(0),
                    "fees": Decimal(0),
                }
            )
            fresh = (
                latest
                and not _quality(latest, spec, at)
                and instant(latest["source_time"]) >= instant(spec["started_at"])
            )
            price = money(latest["last"], positive=True) if fresh else None
            if state["shares"]:
                asof = (
                    latest["source_time"]
                    if price
                    else (series[-1]["source_time"] if series else None)
                )
                view["holdings"] = [
                    {
                        "symbol": spec["assets"][0]["symbol"],
                        "shares": float(state["shares"]),
                        "last": float(price) if price else None,
                        "market_value": float(state["shares"] * price) if price else None,
                        "asof": asof,
                        "stale": price is None,
                    }
                ]
            account_views.append(view)
        if range == "common":
            active = [a for a in account_views if a["kind"] in {"buy_hold", "cash"}]
            common = (
                set.intersection(
                    *(set(r["date"] for r in a["series"] if r["valid"]) for a in active)
                )
                if active
                else set()
            )
            for a in active:
                a["series"] = [r for r in a["series"] if r["date"] in common]
                if a["series"]:
                    first = a["series"][0]["nav"]
                    for r in a["series"]:
                        r["nav"] /= first
        for a in account_views:
            first = (
                a["series"][0]["source_time"]
                if range == "common" and a["series"]
                else spec["started_at"]
            )
            a["metrics"] = _metrics(a["series"], first)
            if a["kind"] == "buy_hold":
                end = a["first_fill_at"] or at
                a["metrics"]["wait_days"] = max(
                    0, (instant(end) - instant(spec["started_at"])).days
                )
                a["metrics"]["wait_reason"] = (
                    "filled" if a["first_fill_at"] else "still_waiting_fill"
                )
            elif a["kind"] == "cash":
                a["metrics"]["wait_days"] = 0
                a["metrics"]["wait_reason"] = "cash_reference"
            if a["kind"] in {"cash", "buy_hold"} and a["series"]:
                recent = db.execute(
                    "SELECT source_at,payload FROM observations ORDER BY source_at DESC LIMIT 1"
                ).fetchone()
                if (
                    recent
                    and json.loads(recent["payload"]).get("is_eod")
                    and a["series"][-1]["date"] < instant(recent["source_at"]).date().isoformat()
                ):
                    a["status"] = "stale"
                    a["reasons"] = list(a["reasons"]) + ["latest_eod_valuation_missing"]
        events = [
            dict(r)
            for r in db.execute(
                "SELECT id,at,kind,account_id,observation_id,payload "
                "FROM events ORDER BY rowid DESC LIMIT 300"
            )
        ]
        for e in events:
            e["payload"] = json.loads(e["payload"])
        health = ["simulated_only_no_broker"]
        if config_changed:
            health.append("current_config_differs_frozen")
        runner = None
        heartbeat = Path(db_path).parent / "runner-status.json"
        if heartbeat.is_file():
            try:
                runner = json.loads(heartbeat.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                health.append("runner_heartbeat_unreadable")
        else:
            health.append("runner_heartbeat_missing")
        if isinstance(runner, dict):
            pid_alive = False
            pid = runner.get("pid")
            if isinstance(pid, int) and pid > 0:
                try:
                    os.kill(pid, 0)
                    pid_alive = True
                except (OSError, ValueError):
                    pass
            try:
                heartbeat_age = max(
                    0, (instant(at) - instant(runner["heartbeat_at"])).total_seconds()
                )
            except (KeyError, TypeError, ValueError):
                heartbeat_age = None
            interval = (config or {}).get("schedule", {}).get("interval_seconds", 300)
            fresh = heartbeat_age is not None and heartbeat_age <= max(120, int(interval) * 2 + 30)
            runner["pid_alive"] = pid_alive
            runner["heartbeat_fresh"] = fresh
            runner["heartbeat_age_seconds"] = heartbeat_age
            runner["active"] = (
                runner.get("mode") == "watch"
                and runner.get("status") in {"starting", "waiting"}
                and pid_alive
                and fresh
            )
            if not runner["active"]:
                health.append("runner_not_active")
        reconciliation = {
            "status": "not_available",
            "passed": None,
            "reasons": ["reconciliation_not_recorded"],
        }
        reconciliation_path = Path(db_path).parent / "reconciliation.json"
        if reconciliation_path.is_file():
            try:
                reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                health.append("reconciliation_unreadable")
        status = "observing" if row["last_source_at"] else "waiting_quote"
        return {
            "schema_version": 1,
            "generated_at": at,
            "range": range,
            "run": {
                "status": status,
                "frozen_at": spec["frozen_at"],
                "started_at": spec["started_at"],
                "last_run_at": row["last_run_at"],
                "last_source_at": row["last_source_at"],
                "next_run_at": runner.get("next_run_at") if isinstance(runner, dict) else None,
                "runner": runner,
            },
            "accounts": account_views,
            "decisions": events,
            "health": health,
            "sources": [
                {
                    "id": r["id"],
                    "source_time": r["source_at"],
                    "received_at": r["received_at"],
                    "hash": r["payload_hash"],
                }
                for r in observations
            ],
            "pending": ["完整原A及其他负责人策略待规则和资料齐备"],
            "reconciliation": reconciliation,
        }


def _empty_account(account: dict) -> dict:
    kind = account.get("kind", "blocked")
    reasons = account.get("reasons") or ([account["reason"]] if account.get("reason") else [])
    if isinstance(reasons, str):
        reasons = [reasons]
    return {
        "id": account.get("id"),
        "name": account.get("name") or account.get("id"),
        "kind": kind,
        "role": account.get("role"),
        "status": kind if kind in {"blocked", "external_pending"} else "not_started",
        "reasons": reasons,
        "rules": account.get("rules") or {},
        "frozen_at": None,
        "started_at": None,
        "first_decision_at": None,
        "first_fill_at": None,
        "metrics": _metrics([], "2000-01-01T00:00:00+00:00"),
        "series": [],
        "holdings": [],
        "orders": [],
    }
