"""Step 3 E2E 验证: 模拟 PromotePlanDialog 提交, 端到端比对与设计预期.

设计预期 (Step 3 决策 2, 2026-08-09):
  1) watch 处于 pending_confirmation -> 一站式 create + confirm + entered
  2) plan.source 持久化为 'watch_promoted' (与 default 'user' 区分)
  3) plan.plan_kind='entry' (后端硬编码, 客户端不可改)
  4) plan.ruleset_version='watch_promoted_v1' (后端硬编码)
  5) watch.promoted_plan_id 回填, watch.state=promoted
  6) 缺失五项预案 -> 400
  7) 同一 watch 二次 promote -> 409
  8) auto_enter=False -> plan 落 armed, watch 仍 promoted
  9) watch 处于 active (非 pending) -> 400
 10) 无效 direction -> 400
 11) 用户覆盖 invalidation_price 预填, 落库必须是覆盖值
 12) short + module C 象限也走得通
 13) 5 项预案 + invalidation_price 在 revision_no=0 落快照 (复议根基)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.services import AnalysisService
from lei_signal.api import watch_subscriptions as ws
from lei_signal.plans.store import frozen_snapshot, get_plan
from lei_signal.storage.sqlite_store import connect


def _client(tmp_path):  # noqa: ANN001
    db = str(tmp_path / "e2e.db")
    svc = AnalysisService(analyze_fn=None, sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=svc)
    app.state.plans_db_path = db
    return TestClient(app), db


def _seed_pending_watch_payload(
    db: str,
    *,
    symbol: str = "SZ300750",
    direction: str = "long",
    module: str = "A",
    level: float = 14.20,
    triggered_price: float = 14.18,
) -> dict:
    conn = connect(db)
    try:
        w = ws.create_watch(
            conn, symbol=symbol, direction=direction, module=module,
            watch_kind="price", watch_text_cn="回踩 14.20 算买点",
            level=level, source_rule_id="RULE_DOUBLE_MA",
            as_signal_rule_ids=("RULE_DOUBLE_MA",),
        )
        ws.mark_triggered(
            conn, w.watch_id, triggered_price=triggered_price,
            triggered_reason_cn="长: 14:45 价 14.18 <= 14.20*(1+0.005)=14.27",
        )
        final = ws.get_watch(conn, w.watch_id)
        return {
            "watch_id": final.watch_id,
            "symbol": final.symbol,
            "direction": final.direction,
            "module": final.module,
            "level": final.level,
            "triggered_price": final.triggered_price,
            "watch_text_cn": final.watch_text_cn,
            "source_rule_id": final.source_rule_id,
        }
    finally:
        conn.close()


def _modal_payload(
    watch: dict,
    *,
    auto_enter: bool = True,
    valid_until: str = "2026-09-30",
    reason: str = "watch 命中建计划: 回踩 14.20 算买点",
    override_invalidation: float | None = None,
    override_entry_price: float | None = None,
    playbook: dict | None = None,
) -> dict:
    pb = playbook or {
        "thesis_cn": "t",
        "invalidation_criteria_cn": "i",
        "drawdown_playbook_cn": "d",
        "take_profit_plan_cn": "tp",
        "stop_plan_cn": "sp",
    }
    return {
        "module": watch["module"],
        "direction": watch["direction"],
        "valid_until": valid_until,
        "reason": reason,
        "entry_trigger_cn": watch["watch_text_cn"],
        "entry_price_ref": override_entry_price if override_entry_price is not None else watch["triggered_price"],
        "invalidation_price": override_invalidation if override_invalidation is not None else watch["level"],
        "target_b_price": 16.50,
        "reward_risk_at_plan": 2.5,
        "thesis_cn": pb["thesis_cn"],
        "invalidation_criteria_cn": pb["invalidation_criteria_cn"],
        "drawdown_playbook_cn": pb["drawdown_playbook_cn"],
        "take_profit_plan_cn": pb["take_profit_plan_cn"],
        "stop_plan_cn": pb["stop_plan_cn"],
        "watch_signal_rule_ids": ["RULE_DOUBLE_MA"],
        "auto_enter": auto_enter,
    }


# 1~5) 端到端 happy path -- 「单一可信测试」
def test_e2e_modal_submit_produces_expected_db_state(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch)
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    plan = body["plan"]
    assert plan["state"] == "entered"
    assert plan["entered_on"] is not None
    assert plan["source"] == "watch_promoted"
    assert plan["plan_kind"] == "entry"
    assert plan["ruleset_version"] == "watch_promoted_v1"
    assert body["watch"]["state"] == "promoted"
    assert body["watch"]["promoted_plan_id"] == plan["plan_id"]
    assert plan["entry_price_ref"] == 14.18
    assert plan["invalidation_price"] == 14.20
    assert plan["entry_rule_id"] == "RULE_DOUBLE_MA"
    assert plan["entry_trigger_cn"] == "回踩 14.20 算买点"
    assert plan["watch_signal_rule_ids"] == ["RULE_DOUBLE_MA"]
    assert plan["thesis_cn"] == "t"
    assert plan["stop_plan_cn"] == "sp"
    conn = connect(db)
    try:
        reloaded = get_plan(conn, plan["plan_id"])
    finally:
        conn.close()
    assert reloaded is not None
    assert reloaded.source == "watch_promoted"
    assert reloaded.plan_kind == "entry"
    assert reloaded.ruleset_version == "watch_promoted_v1"


# 6) 缺失五项预案 -> 400
def test_e2e_modal_submit_missing_playbook_returns_400(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch, playbook={
        "thesis_cn": "t", "invalidation_criteria_cn": "i",
        "drawdown_playbook_cn": "d", "take_profit_plan_cn": "tp",
        "stop_plan_cn": "",
    })
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert ("armed 必填" in detail) or ("校验失败" in detail)
    assert "stop_plan_cn" in detail


# 7) 同一 watch 二次 promote -> 409
def test_e2e_double_promote_returns_409(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch)
    r1 = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r1.status_code == 201
    plan_id = r1.json()["plan"]["plan_id"]
    r2 = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r2.status_code == 409
    assert plan_id in r2.json()["detail"]


# 8) auto_enter=False -> armed, watch 仍 promoted
def test_e2e_auto_enter_false_lands_armed(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch, auto_enter=False)
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r.status_code == 201
    plan = r.json()["plan"]
    assert plan["state"] == "armed"
    assert plan["entered_on"] is None
    assert r.json()["watch"]["state"] == "promoted"


# 9) watch 处于 active -> 400
def test_e2e_active_watch_cannot_promote(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    conn = connect(db)
    try:
        w = ws.create_watch(
            conn, symbol="SZ300750", direction="long", module="A",
            watch_kind="price", watch_text_cn="t", level=14.20,
        )
    finally:
        conn.close()
    r = client.post(
        f"/api/watch/{w.watch_id}/promote",
        json=_modal_payload({
            "watch_id": w.watch_id, "symbol": w.symbol, "direction": w.direction,
            "module": w.module, "level": 14.20, "triggered_price": None,
            "watch_text_cn": "t", "source_rule_id": None,
        }),
    )
    assert r.status_code == 400
    assert "pending_confirmation" in r.json()["detail"]


# 10) 无效 direction -> 400
def test_e2e_invalid_direction_returns_400(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch)
    payload["direction"] = "sideways"
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r.status_code == 400
    assert "direction" in r.json()["detail"]


# 11) 用户覆盖 invalidation_price -> 落库必须是覆盖值
def test_e2e_user_override_invalidation_persisted(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch, override_invalidation=13.50)
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r.status_code == 201
    plan = r.json()["plan"]
    assert plan["invalidation_price"] == 13.50
    conn = connect(db)
    try:
        reloaded = get_plan(conn, plan["plan_id"])
    finally:
        conn.close()
    assert reloaded.invalidation_price == 13.50


# 12) short + module C 象限
def test_e2e_short_module_c_promote_works(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(
        db, direction="short", module="C", level=18.00, triggered_price=18.05,
    )
    payload = _modal_payload(watch)
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    assert r.status_code == 201
    plan = r.json()["plan"]
    assert plan["direction"] == "short"
    assert plan["module"] == "C"
    assert plan["state"] == "entered"


# 13) 5 项预案 + invalidation_price 在 revision_no=0 落快照
def test_e2e_playbook_snapshot_frozen_at_revision_zero(tmp_path) -> None:  # noqa: ANN001
    client, db = _client(tmp_path)
    watch = _seed_pending_watch_payload(db)
    payload = _modal_payload(watch)
    r = client.post(f"/api/watch/{watch['watch_id']}/promote", json=payload)
    plan_id = r.json()["plan"]["plan_id"]
    conn = connect(db)
    try:
        snap = frozen_snapshot(conn, plan_id)
    finally:
        conn.close()
    assert snap is not None
    assert snap["thesis_cn"] == "t"
    assert snap["stop_plan_cn"] == "sp"
    assert snap["invalidation_price"] == 14.20
