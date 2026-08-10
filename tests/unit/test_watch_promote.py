"""Step 3: 从 watch 落计划 (POST /api/watch/{id}/promote).

覆盖:
  - happy path: pending_confirmation -> promote -> armed/entered,
    watch=promoted, plan.source=watch_promoted
  - 状态机守门: state=active 时 400; state=promoted 时 409
  - 必填校验: 五项预案/valid_until/reason 缺一 -> 400
  - auto_enter=False: plan 落 armed, watch 仍 promoted
  - 默认 invalidation_price 从 watch.level 预填, entry_price_ref 从 triggered_price
  - 404: watch_id 不存在
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.services import AnalysisService
from lei_signal.api import watch_subscriptions as ws
from lei_signal.plans.store import get_plan
from lei_signal.storage.sqlite_store import connect


def _client(tmp_path):  # noqa: ANN001
    db = str(tmp_path / "promote.db")
    # 用空 svc 即可: 测试不走 /api/symbols/* 路径
    svc = AnalysisService(analyze_fn=None, sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=svc)
    app.state.plans_db_path = db
    return TestClient(app), db


def _seed_pending_watch(db: str) -> str:
    """铺一条 pending_confirmation 状态的 watch, 返回 watch_id."""
    conn = connect(db)
    try:
        w = ws.create_watch(
            conn, symbol="SZ300750", direction="long", module="A",
            watch_kind="price", watch_text_cn="回踩 14.20 算买点", level=14.20,
            source_rule_id="RULE_DOUBLE_MA",
            as_signal_rule_ids=("RULE_DOUBLE_MA",),
        )
        ws.mark_triggered(
            conn, w.watch_id, triggered_price=14.18,
            triggered_reason_cn="长: 14:45 价 14.18 ≤ 14.20×(1+0.005)=14.27",
        )
        return w.watch_id
    finally:
        conn.close()


def _valid_body() -> dict:
    return {
        "reason": "watch 命中建计划",
        "valid_until": "2026-09-30",
        "thesis_cn": "t",
        "invalidation_criteria_cn": "i",
        "drawdown_playbook_cn": "d",
        "take_profit_plan_cn": "tp",
        "stop_plan_cn": "sp",
    }


def test_promote_happy_path_arms_and_enters(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    wid = _seed_pending_watch(db)
    r = client.post(f"/api/watch/{wid}/promote", json=_valid_body())
    assert r.status_code == 201, r.text
    body = r.json()
    plan = body["plan"]
    watch = body["watch"]
    assert plan["state"] == "entered"
    assert plan["source"] == "watch_promoted"
    assert plan["plan_kind"] == "entry"
    assert plan["entered_on"] == datetime.now(UTC).date().isoformat()
    assert plan["symbol"] == "SZ300750"
    assert plan["invalidation_price"] == 14.20  # 默认从 watch.level 预填
    assert plan["entry_price_ref"] == 14.18    # 默认从 watch.triggered_price
    assert plan["entry_rule_id"] == "RULE_DOUBLE_MA"
    assert watch["state"] == "promoted"
    assert watch["promoted_plan_id"] == plan["plan_id"]


def test_promote_state_active_returns_400(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    conn = connect(db)
    try:
        w = ws.create_watch(
            conn, symbol="SZ300750", direction="long", module="A",
            watch_kind="price", watch_text_cn="t", level=14.20,
        )
    finally:
        conn.close()
    r = client.post(f"/api/watch/{w.watch_id}/promote", json=_valid_body())
    assert r.status_code == 400
    assert "pending_confirmation" in r.json()["detail"]


def test_promote_already_promoted_returns_409(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    wid = _seed_pending_watch(db)
    # 第一次 promote 成功
    r1 = client.post(f"/api/watch/{wid}/promote", json=_valid_body())
    assert r1.status_code == 201
    # 第二次 promote 冲突
    r2 = client.post(f"/api/watch/{wid}/promote", json=_valid_body())
    assert r2.status_code == 409
    assert "已落过计划" in r2.json()["detail"]


def test_promote_missing_playbook_returns_400(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    wid = _seed_pending_watch(db)
    body = _valid_body()
    del body["stop_plan_cn"]
    r = client.post(f"/api/watch/{wid}/promote", json=body)
    assert r.status_code == 400
    assert "校验失败" in r.json()["detail"] or "armed 必填" in r.json()["detail"]


def test_promote_auto_enter_false_lands_armed(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    wid = _seed_pending_watch(db)
    body = _valid_body()
    body["auto_enter"] = False
    r = client.post(f"/api/watch/{wid}/promote", json=body)
    assert r.status_code == 201, r.text
    plan = r.json()["plan"]
    watch = r.json()["watch"]
    assert plan["state"] == "armed"
    assert plan["entered_on"] is None
    # watch 仍然进入 promoted (落过计划 = promoted, 不管 plan 状态)
    assert watch["state"] == "promoted"
    assert watch["promoted_plan_id"] == plan["plan_id"]


def test_promote_404_when_watch_missing(tmp_path) -> None:  # noqa: ANN001
    client, _ = _client(tmp_path)
    r = client.post("/api/watch/ws_NOPE/promote", json=_valid_body())
    assert r.status_code == 404


def test_promote_persists_source_through_get_plan(tmp_path) -> None:  # noqa: ANN001
    """底层 _row_to_plan 必须能读出 source=watch_promoted (回归测试)."""
    client, db = _client(tmp_path)
    wid = _seed_pending_watch(db)
    r = client.post(f"/api/watch/{wid}/promote", json=_valid_body())
    plan_id = r.json()["plan"]["plan_id"]
    conn = connect(db)
    try:
        plan = get_plan(conn, plan_id)
    finally:
        conn.close()
    assert plan is not None
    assert plan.source == "watch_promoted"
    assert plan.plan_kind == "entry"
