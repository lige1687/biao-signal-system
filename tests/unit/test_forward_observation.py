"""Boundary tests for prospective virtual accounts. No market or broker access."""

import json
import os
from datetime import UTC, datetime, timedelta

import pytest

from lei_signal.forward_observation import build_dashboard, initialize, process_observation

BASE = datetime(2026, 10, 20, 1, 0, tzinfo=UTC)


def config():
    return {
        "schema_version": 1,
        "group": {"symbol": "510300.SS", "name": "沪深300ETF华泰柏瑞"},
        "initial_cash": 100000,
        "fee_bps": 10,
        "slippage_bps": 5,
        "lot_size": 100,
        "max_quote_age_seconds": 120,
        "accounts": [
            {"id": "buy", "name": "持有", "kind": "buy_hold", "role": "passive_baseline"},
            {"id": "cash", "name": "现金", "kind": "cash", "role": "cash_reference"},
            {"id": "A", "name": "原A", "kind": "blocked", "reason": "规则未知"},
            {"id": "green", "name": "低换手绿色", "kind": "external_pending"},
        ],
    }


def quote(id, minute, **change):
    source = BASE + timedelta(minutes=minute)
    received = source + timedelta(seconds=10)
    row = {
        "id": id,
        "symbol": "510300.SS",
        "name": "沪深300ETF华泰柏瑞",
        "source": "synthetic",
        "source_time": source.isoformat(),
        "received_at": received.isoformat(),
        "last": 4.0,
        "bid": 3.99,
        "ask": 4.0,
        "bid_size": 100000,
        "ask_size": 100,
        "market_open": True,
        "quality": "valid",
        "reasons": [],
        "corporate_actions_checked_from": (BASE - timedelta(days=1)).date().isoformat(),
        "corporate_actions_checked_through": source.date().isoformat(),
        "corporate_actions": [],
        "is_eod": False,
    }
    row.update(change)
    return row


def account(view, id):
    return next(a for a in view["accounts"] if a["id"] == id)


def test_initial_is_frozen_and_read_only_get_does_not_create_db(tmp_path):
    db = tmp_path / "observation.db"
    before = build_dashboard(db, config(), BASE.isoformat())
    assert before["run"]["status"] == "not_started"
    assert not db.exists()
    view = initialize(db, config(), BASE.isoformat())
    assert view["run"]["frozen_at"] == BASE.isoformat()
    assert len(account(view, "buy")["orders"]) == 1
    assert account(view, "A")["status"] == "blocked"
    assert account(view, "green")["status"] == "external_pending"
    assert account(view, "A")["started_at"] is None
    assert account(view, "green")["frozen_at"] is None
    assert account(view, "buy")["series"] == []
    again = initialize(db, config(), BASE.isoformat())
    assert again["run"]["frozen_at"] == view["run"]["frozen_at"]
    bad = config()
    bad["initial_cash"] = 99999
    with pytest.raises(ValueError, match="configuration changed"):
        initialize(db, bad, BASE.isoformat())


def test_wait_partial_restart_and_idempotent_fill(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    too_old = quote("old", -1)
    view = process_observation(db, too_old, BASE.isoformat())
    assert account(view, "buy")["first_fill_at"] is None
    no_size = quote("no-size", 1, ask_size=None)
    view = process_observation(db, no_size, (BASE + timedelta(minutes=1, seconds=10)).isoformat())
    assert account(view, "buy")["first_fill_at"] is None
    q1 = quote("partial-one", 2, ask_size=100)
    view = process_observation(db, q1, (BASE + timedelta(minutes=2, seconds=10)).isoformat())
    buy = account(view, "buy")
    assert buy["orders"][0]["status"] == "partial"
    assert buy["orders"][0]["filled_qty"] == 100
    assert buy["first_fill_at"] is not None
    before = len(view["decisions"])
    same = process_observation(db, q1, (BASE + timedelta(minutes=2, seconds=10)).isoformat())
    assert len(same["decisions"]) == before
    q2 = quote("partial-two", 3, ask_size=100000)
    final = process_observation(db, q2, (BASE + timedelta(minutes=3, seconds=10)).isoformat())
    assert account(final, "buy")["orders"][0]["status"] == "filled"
    assert account(final, "buy")["holdings"][0]["shares"] > 100
    with pytest.raises(ValueError, match="identity conflict"):
        process_observation(
            db, dict(q2, ask=5.0), (BASE + timedelta(minutes=3, seconds=10)).isoformat()
        )


def test_eod_after_close_may_be_delayed_but_cannot_fill_and_missing_action_blocks_nav(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    eod = quote("eod", 10, market_open=False, is_eod=True)
    now = BASE + timedelta(minutes=20)
    view = process_observation(db, eod, now.isoformat())
    assert account(view, "buy")["first_fill_at"] is None
    assert account(view, "buy")["metrics"]["observations"] == 1
    assert account(view, "buy")["metrics"]["annualized_return_pct"] is None
    nextday = quote(
        "unchecked", 1440, is_eod=True, market_open=False, corporate_actions_checked_through=None
    )
    view = process_observation(db, nextday, (BASE + timedelta(minutes=1450)).isoformat())
    assert account(view, "buy")["metrics"]["observations"] == 1


def test_cash_dividend_unpaid_remains_receivable(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    q = quote("fill", 1, ask_size=100000)
    process_observation(db, q, (BASE + timedelta(minutes=1, seconds=10)).isoformat())
    action = {
        "id": "div-1",
        "type": "cash_dividend",
        "ex_date": (BASE + timedelta(days=1)).date().isoformat(),
        "pay_date": None,
        "amount": "0.10",
    }
    eod = quote("eod", 1450, market_open=False, is_eod=True, corporate_actions=[action])
    view = process_observation(db, eod, (BASE + timedelta(minutes=1460)).isoformat())
    row = account(view, "buy")["series"][0]
    assert row["receivable"] > 0
    assert row["cash"] >= 0
    assert row["equity"] == pytest.approx(row["cash"] + row["market_value"] + row["receivable"])


def test_same_source_time_and_late_actions_cannot_reuse_or_backdate(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    first = quote("first", 1, ask_size=100)
    one = process_observation(db, first, (BASE + timedelta(minutes=1, seconds=10)).isoformat())
    assert account(one, "buy")["orders"][0]["filled_qty"] == 100
    refreshed = quote(
        "refresh",
        1,
        ask_size=100,
        received_at=(BASE + timedelta(minutes=1, seconds=15)).isoformat(),
    )
    again = process_observation(
        db, refreshed, (BASE + timedelta(minutes=1, seconds=15)).isoformat()
    )
    assert account(again, "buy")["orders"][0]["filled_qty"] == 100
    late = quote(
        "late-action",
        2890,
        corporate_actions=[
            {
                "id": "late-div",
                "type": "cash_dividend",
                "ex_date": (BASE + timedelta(days=1)).date().isoformat(),
                "pay_date": None,
                "amount": "1",
            }
        ],
        is_eod=True,
        market_open=False,
    )
    result = process_observation(db, late, (BASE + timedelta(minutes=2900)).isoformat())
    assert account(result, "buy")["metrics"]["observations"] == 0
    assert any(
        "late_corporate_action_pending_reconciliation" in e["payload"].get("reasons", [])
        for e in result["decisions"]
        if e["kind"] == "waiting"
    )


def test_late_previous_close_does_not_value_next_day_holdings(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    next_day_buy = quote("next-day-buy", 1441, ask_size=100000)
    process_observation(db, next_day_buy, (BASE + timedelta(minutes=1441, seconds=10)).isoformat())
    prior_eod = quote("prior-eod-late", 840, market_open=False, is_eod=True, last=5.0)
    result = process_observation(db, prior_eod, (BASE + timedelta(minutes=1442)).isoformat())
    assert account(result, "buy")["metrics"]["observations"] == 0
    assert account(result, "buy")["holdings"][0]["last"] == 4.0
    assert account(result, "buy")["holdings"][0]["asof"] == next_day_buy["source_time"]


def test_future_invalid_source_does_not_poison_clock_or_display(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    future = quote("future", 14400)
    rejected = process_observation(db, future, (BASE + timedelta(minutes=1)).isoformat())
    assert rejected["run"]["last_source_at"] is None
    assert rejected["run"]["status"] == "waiting_quote"
    valid = quote("valid", 2)
    result = process_observation(db, valid, (BASE + timedelta(minutes=2, seconds=10)).isoformat())
    assert result["run"]["last_source_at"] == valid["source_time"]
    assert account(result, "buy")["first_fill_at"] is not None
    assert account(result, "buy")["holdings"][0]["asof"] == valid["source_time"]


def test_action_coverage_gap_blocks_then_overlapping_check_resumes(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    first = quote("first", 1)
    process_observation(db, first, (BASE + timedelta(minutes=1, seconds=10)).isoformat())
    gap = quote(
        "gap", 2881, corporate_actions_checked_from=(BASE + timedelta(days=2)).date().isoformat()
    )
    rejected = process_observation(
        db, gap, (BASE + timedelta(minutes=2881, seconds=10)).isoformat()
    )
    assert rejected["run"]["last_source_at"] == first["source_time"]
    assert any(
        "corporate_actions_coverage_gap" in e["payload"].get("reasons", [])
        for e in rejected["decisions"]
        if e["kind"] == "waiting"
    )
    covered = quote(
        "covered",
        2882,
        corporate_actions_checked_from=(BASE + timedelta(days=1)).date().isoformat(),
    )
    result = process_observation(
        db, covered, (BASE + timedelta(minutes=2882, seconds=10)).isoformat()
    )
    assert result["run"]["last_source_at"] == covered["source_time"]


def test_runner_status_checks_pid_and_heartbeat(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    status = {
        "mode": "watch",
        "status": "waiting",
        "pid": os.getpid(),
        "heartbeat_at": BASE.isoformat(),
        "next_run_at": (BASE + timedelta(minutes=5)).isoformat(),
    }
    (tmp_path / "runner-status.json").write_text(json.dumps(status))
    active = build_dashboard(db, config(), (BASE + timedelta(seconds=30)).isoformat())
    assert active["run"]["runner"]["active"] is True
    stale = build_dashboard(db, config(), (BASE + timedelta(hours=1)).isoformat())
    assert stale["run"]["runner"]["active"] is False
    assert "runner_not_active" in stale["health"]


def test_dashboard_reads_saved_independent_reconciliation(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    saved = {"status": "checked", "passed": True, "checks": [], "counts": {}, "reasons": []}
    (tmp_path / "reconciliation.json").write_text(json.dumps(saved), encoding="utf-8")
    view = build_dashboard(db, config(), BASE.isoformat())
    assert view["reconciliation"] == saved


def test_ex_date_entitlement_revision_and_payment_evidence(tmp_path):
    db = tmp_path / "ledger.db"
    initialize(db, config(), BASE.isoformat())
    # Ex-date before buying: the later holder must receive no dividend.
    ex = {
        "id": "div-one",
        "type": "cash_dividend",
        "ex_date": BASE.date().isoformat(),
        "pay_date": None,
        "amount": "1",
    }
    process_observation(
        db,
        quote("ex", 10, market_open=False, is_eod=True, corporate_actions=[ex]),
        (BASE + timedelta(minutes=20)).isoformat(),
    )
    next_day = quote("later-buy", 1441, ask_size=100000, corporate_actions=[ex])
    process_observation(db, next_day, (BASE + timedelta(minutes=1441, seconds=10)).isoformat())
    revision = dict(ex, id="div-revised", amount="1.1")
    revised = quote("revision", 1450, market_open=False, is_eod=True, corporate_actions=[revision])
    view = process_observation(db, revised, (BASE + timedelta(minutes=1460)).isoformat())
    assert account(view, "buy")["metrics"]["observations"] == 1
    assert any(
        "corporate_action_revision_pending" in e["payload"].get("reasons", [])
        for e in view["decisions"]
        if e["kind"] == "waiting"
    )
