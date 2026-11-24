"""Follow-ups use a temporary SQLite database and a fake saved decision."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from lei_signal.copilot import decision_followups as followups
from lei_signal.storage.sqlite_store import connect
from tests.unit.test_decision_journal import _confirm, _review
from tests.unit.test_decision_journal import env as decision_env


@pytest.fixture()
def env(tmp_path, monkeypatch):
    yield from decision_env.__wrapped__(tmp_path, monkeypatch)


def _saved(client):
    review = _review(client).json()
    decision = _confirm(client, review).json()
    return decision, review


def _body(review, kind="wait", **changes):
    return {
        "kind": kind,
        "client_request_id": str(uuid.uuid4()),
        "confirmed": True,
        "review_id": review["review_id"],
        "occurred_on": date.today().isoformat(),
        "note": "继续等原先关注的条件",
        **changes,
    }


def _plan(conn, plan_id="p1", symbol="510300.SH"):
    now = date.today().isoformat()
    conn.execute(
        "INSERT INTO trade_plans(plan_id,symbol,module,direction,valid_until,state,"
        "ruleset_version,reason,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (plan_id, symbol, "A", "long", now, "armed", "v1", "测试计划", now, now),
    )


def _trade(conn, trade_id="t1", code="510300", day=None):
    day = day or date.today().isoformat()
    conn.execute(
        "INSERT INTO fund_trades(trade_id,fund_code,fund_name,side,amount,trade_date,"
        "price_status,source,note,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (trade_id, code, "甲基金", "sell", 100.0, day, "pending", "web", "", day, day),
    )


def test_wait_and_review_are_confirmed_append_only_without_transaction(env):
    client, path, *_ = env
    decision, review = _saved(client)
    url = f"/api/decisions/{decision['decision_id']}/followups"
    payload = _body(review)
    assert client.post(url, json={**payload, "confirmed": False}).status_code == 422
    first = client.post(url, json=payload)
    assert first.status_code == 200, first.text
    followup = first.json()["followups"][0]
    assert followup["kind"] == "wait"
    assert followup["reference"] is None
    assert followup["decision_snapshot"]["thought"] == decision["thought"]
    assert client.post(url, json=payload).json()["followups"] == first.json()["followups"]
    assert client.post(url, json={**payload, "note": "换了内容"}).status_code == 409
    assert client.post(url, json=_body(review, "review", note="")).status_code == 422
    assert client.post(url, json=_body(review, "no_action", note="尚未执行")).status_code == 200
    assert client.post(url, json=_body(review, "review", note="原条件仍未满足")).status_code == 200
    assert [
        f["kind"]
        for f in client.get(f"/api/decisions/{decision['decision_id']}").json()["followups"]
    ] == ["wait", "no_action", "review"]
    with connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM fund_trades").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM trade_plans").fetchone()[0] == 0


def test_reject_old_day_future_day_and_stale_review(env):
    client, _, _, _, _ = env
    decision, review = _saved(client)
    url = f"/api/decisions/{decision['decision_id']}/followups"
    assert (
        client.post(
            url, json=_body(review, occurred_on=(date.today() - timedelta(days=2)).isoformat())
        ).status_code
        == 409
    )
    assert (
        client.post(
            url, json=_body(review, occurred_on=(date.today() + timedelta(days=1)).isoformat())
        ).status_code
        == 422
    )
    assert client.post(url, json=_body(review, review_id="other-review")).status_code == 409
    newer = _review(client, cid="second", decision_id=decision["decision_id"]).json()
    assert _confirm(client, newer, cid="second-confirm").status_code == 200
    assert client.post(url, json=_body(review)).status_code == 409


def test_plan_requires_confirmed_same_holding_mapping_and_frozen_candidate(env):
    client, path, workspace, *_ = env
    workspace["items"][0]["plan"] = {"plan_id": "p1"}
    with connect(path) as conn:
        _plan(conn)
        _plan(conn, "p2", "510300.SH")
        conn.commit()
    decision, review = _saved(client)
    url = f"/api/decisions/{decision['decision_id']}"
    options = client.get(url + "/followup-options").json()["items"]
    plans = [item for item in options if item["kind"] == "plan"]
    assert [item["reference_id"] for item in plans] == ["p1"]
    candidate = plans[0]
    assert candidate["href"] == "/plans?plan_id=p1"
    assert (
        candidate["label"]
        == f"甲基金计划 · 已确认，等待条件 · {date.today().isoformat()}建立 · 测试计划"
    )
    assert "510300" not in candidate["label"] and "armed" not in candidate["label"]
    payload = _body(
        review, "plan", reference_id="p1", reference_fingerprint=candidate["reference_fingerprint"]
    )
    assert (
        client.post(url + "/followups", json={**payload, "reference_id": "p2"}).status_code == 409
    )
    with connect(path) as conn:
        conn.execute(
            "UPDATE trade_plans SET invalidation_price=0.8,stop_price=0.7 WHERE plan_id='p1'"
        )
        conn.commit()
    assert client.post(url + "/followups", json=payload).status_code == 409
    new_candidate = next(
        i for i in client.get(url + "/followup-options").json()["items"] if i["kind"] == "plan"
    )
    saved = client.post(
        url + "/followups",
        json={**payload, "reference_fingerprint": new_candidate["reference_fingerprint"]},
    )
    assert saved.status_code == 200, saved.text
    frozen = saved.json()["followups"][0]
    assert frozen["reference"]["snapshot"]["invalidation_price"] == 0.8
    assert frozen["reference"]["snapshot"]["stop_price"] == 0.7
    with connect(path) as conn:
        conn.execute("UPDATE trade_plans SET invalidation_price=0.5 WHERE plan_id='p1'")
        conn.commit()
    assert client.get(url).json()["followups"][0] == frozen
    replay = client.post(
        url + "/followups",
        json={**payload, "reference_fingerprint": new_candidate["reference_fingerprint"]},
    )
    assert replay.status_code == 200
    assert replay.json()["followups"][0] == frozen
    with connect(path) as conn:
        conn.execute("UPDATE trade_plans SET state='unexpected' WHERE plan_id='p1'")
        conn.commit()
    unknown = next(
        i for i in client.get(url + "/followup-options").json()["items"] if i["kind"] == "plan"
    )
    assert "状态待核" in unknown["label"] and "unexpected" not in unknown["label"]


def test_trade_uses_exact_confirmed_fund_code_and_trade_day(env):
    client, path, *_ = env
    with connect(path) as conn:
        _trade(conn)
        _trade(conn, "wrong", "510300.SH")
        _trade(conn, "old", "510300", (date.today() - timedelta(days=1)).isoformat())
        conn.commit()
    decision, review = _saved(client)
    url = f"/api/decisions/{decision['decision_id']}"
    trades = [
        item
        for item in client.get(url + "/followup-options").json()["items"]
        if item["kind"] == "trade"
    ]
    assert [item["reference_id"] for item in trades] == ["t1"]
    candidate = trades[0]
    payload = _body(
        review, "trade", reference_id="t1", reference_fingerprint=candidate["reference_fingerprint"]
    )
    assert (
        client.post(
            url + "/followups",
            json={**payload, "occurred_on": (date.today() - timedelta(days=1)).isoformat()},
        ).status_code
        == 409
    )
    result = client.post(url + "/followups", json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["followups"][0]["reference"]["snapshot"]["trade_id"] == "t1"
    with connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM fund_trades").fetchone()[0] == 3


def test_missing_source_tables_are_explicit_gaps(env):
    client, path, *_ = env
    decision, _ = _saved(client)
    with connect(path) as conn:
        conn.execute("DROP TABLE trade_plans")
        conn.execute("DROP TABLE fund_trades")
        conn.commit()
    result = client.get(f"/api/decisions/{decision['decision_id']}/followup-options")
    assert result.status_code == 200
    assert result.json()["items"] == []
    assert "计划台账尚未建立，暂不能关联计划" in result.json()["limitations"]
    assert "基金成交台账尚未建立，暂不能关联成交" in result.json()["limitations"]
    with connect(path) as conn:
        conn.execute("CREATE TABLE fund_trades(trade_id TEXT, fund_code TEXT)")
        conn.commit()
        with pytest.raises(sqlite3.OperationalError, match="trade_date"):
            followups.options(conn, decision["decision_id"])


def test_confirmed_utc_17_is_next_shanghai_day(env):
    client, path, *_ = env
    decision, review = _saved(client)
    shanghai_day = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    prior_utc_day = shanghai_day - timedelta(days=1)
    confirmed_utc = f"{prior_utc_day.isoformat()}T17:00:00+00:00"
    with connect(path) as conn:
        conn.execute(
            "UPDATE decision_confirmations SET confirmed_at=? WHERE decision_id=?",
            (confirmed_utc, decision["decision_id"]),
        )
        conn.commit()
    url = f"/api/decisions/{decision['decision_id']}/followups"
    assert (
        client.post(url, json=_body(review, occurred_on=prior_utc_day.isoformat())).status_code
        == 409
    )
    assert (
        client.post(url, json=_body(review, occurred_on=shanghai_day.isoformat())).status_code
        == 200
    )


def test_index_symbol_cannot_map_to_fund_trade(env):
    _, path, *_ = env
    with connect(path) as conn:
        _trade(conn, code="510300")
        conn.commit()
        forged_symbol = {
            "subject": {"kind": "symbol", "id": "510300.SH", "key": "symbol:510300.SH"},
            "latest_review": {"facts": [{"key": "holding_code", "value": "510300"}]},
        }
        assert followups._reference(conn, forged_symbol, "trade", "t1") is None
