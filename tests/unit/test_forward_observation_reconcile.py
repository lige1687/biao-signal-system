"""Independent read-only reconciliation checks for stored forward accounts."""

import sqlite3
from datetime import UTC, datetime, timedelta

from lei_signal.forward_observation import initialize, process_observation
from lei_signal.forward_observation.reconcile import reconcile


BASE = datetime(2026, 10, 20, 1, 0, tzinfo=UTC)


def _config():
    return {
        "schema_version": 1,
        "group": {"symbol": "510300.SS", "name": "沪深300ETF"},
        "initial_cash": 100000,
        "fee_bps": 10,
        "slippage_bps": 5,
        "lot_size": 100,
        "max_quote_age_seconds": 120,
        "accounts": [
            {"id": "buy", "name": "持有", "kind": "buy_hold", "role": "passive_baseline"},
            {"id": "cash", "name": "现金", "kind": "cash", "role": "cash_reference"},
        ],
    }


def _quote(name, minutes, **changes):
    source = BASE + timedelta(minutes=minutes)
    item = {
        "id": name,
        "symbol": "510300.SS",
        "name": "沪深300ETF",
        "source": "synthetic-test",
        "source_time": source.isoformat(),
        "received_at": (source + timedelta(seconds=10)).isoformat(),
        "last": 4.0,
        "bid": 3.99,
        "ask": 4.0,
        "bid_size": 100000,
        "ask_size": 100000,
        "market_open": True,
        "quality": "valid",
        "reasons": [],
        "corporate_actions_checked_from": (BASE - timedelta(days=1)).date().isoformat(),
        "corporate_actions_checked_through": source.date().isoformat(),
        "corporate_actions": [],
        "is_eod": False,
    }
    item.update(changes)
    item["id"] = name
    return item


def _valid_db(path):
    initialize(path, _config(), BASE.isoformat())
    first = _quote("partial", 1, ask_size=100)
    process_observation(path, first, (BASE + timedelta(minutes=1, seconds=10)).isoformat())
    second = _quote("complete", 2)
    process_observation(path, second, (BASE + timedelta(minutes=2, seconds=10)).isoformat())
    close = _quote("close", 1440, market_open=False, is_eod=True, last=4.2)
    process_observation(path, close, (BASE + timedelta(minutes=1450)).isoformat())


def test_reconciles_partial_fill_and_daily_valuations_read_only(tmp_path):
    db = tmp_path / "forward.db"
    _valid_db(db)

    result = reconcile(db)

    assert result["status"] == "checked"
    assert result["passed"] is True
    assert result["counts"] == {
        "accounts": 2, "orders": 1, "fills": 2, "observations": 3, "valuations": 2
    }
    assert result["counts"]["valuations"] == 2  # separate cash and buy account closes
    assert {check["name"] for check in result["checks"]} >= {
        "spec_hash", "observation_hash", "order_filled_qty", "fill_event_match", "valuation_equity"
    }
    with sqlite3.connect(db) as conn:
        order_qty = conn.execute("SELECT filled_qty FROM orders").fetchone()[0]
        fill_qty = conn.execute("SELECT SUM(qty) FROM fills").fetchone()[0]
        assert order_qty == fill_qty
        assert order_qty > 100


def test_detects_manually_changed_order_fill_total(tmp_path):
    db = tmp_path / "tampered.db"
    _valid_db(db)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE orders SET filled_qty=100")

    result = reconcile(db)

    assert result["passed"] is False
    assert any(reason.startswith("order_filled_qty:") for reason in result["reasons"])


def test_missing_database_is_not_started(tmp_path):
    result = reconcile(tmp_path / "missing.db")
    assert result == {
        "status": "not_started", "passed": False, "checks": [], "counts": {},
        "reasons": ["database_missing"],
    }
