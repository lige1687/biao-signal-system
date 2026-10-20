"""飞书签名回执页：状态推进、验签、过期与幂等。"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.notify.signing import build_action_url
from lei_signal.plans.store import (
    confirm_plan,
    create_plan,
    get_action_item,
    get_plan,
    list_annotations,
    set_entered,
    upsert_action_item,
)
from lei_signal.storage.sqlite_store import connect

SECRET = "test-only-action-secret"
RULESET = "1.3.0"


def _make_action(db_path: str, *, kind: str = "ENTER") -> tuple[str, str]:
    conn = connect(db_path)
    try:
        plan = create_plan(
            conn,
            symbol="000001.SS",
            module="A",
            direction="long",
            ruleset_version=RULESET,
            reason="测试计划",
            valid_until="2026-12-31",
            entry_rule_id="first_ma_pullback",
            entry_lifecycle_id="lc1",
            entry_trigger_cn="测试触发",
            entry_price_ref=3800.0,
            invalidation_price=3650.0,
            target_b_price=4200.0,
            target_b_source="swing_high",
            reward_risk_at_plan=3.5,
            thesis_cn="测试假设",
            invalidation_criteria_cn="测试失效条件",
            drawdown_playbook_cn="测试回撤预案",
            take_profit_plan_cn="测试止盈预案",
            stop_plan_cn="测试止损预案",
        )
        plan = confirm_plan(conn, plan.plan_id)
        item = upsert_action_item(
            conn,
            plan_id=plan.plan_id,
            kind=kind,
            source_alert_code=(
                "ENTRY_CONDITIONS_MET" if kind == "ENTER" else "EXIT_TRIGGERED"
            ),
            state="open",
            due_from="2026-08-05",
        )
        return plan.plan_id, item.action_id
    finally:
        conn.close()


def _client(tmp_path, monkeypatch) -> tuple[TestClient, str]:  # noqa: ANN001
    db_path = str(tmp_path / "feishu-actions.db")
    monkeypatch.setenv("FEISHU_ACTION_SECRET", SECRET)
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    app = create_app()
    app.state.plans_db_path = db_path
    return TestClient(app), db_path


def _signed_url(plan_id: str, action_id: str, *, now: int = 1_800_000_000) -> str:
    return build_action_url(
        "https://lei.example.test",
        SECRET,
        plan_id,
        action_id,
        ttl_seconds=900,
        now=now,
    )


def _form_from_url(url: str, *, operation: str = "done") -> dict[str, str]:
    query = parse_qs(urlparse(url).query)
    return {
        "plan_id": query["plan_id"][0],
        "action_id": query["action_id"][0],
        "expires_at": query["expires_at"][0],
        "nonce": query["nonce"][0],
        "signature": query["signature"][0],
        "operation": operation,
        "reason_cn": "",
        "resume_on_json": "",
    }


def test_done_advances_plan_and_replay_is_idempotent(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client, db_path = _client(tmp_path, monkeypatch)
    plan_id, action_id = _make_action(db_path)
    url = _signed_url(plan_id, action_id)

    page = client.get(url.replace("https://lei.example.test", ""))
    assert page.status_code == 200
    assert "待办确认" in page.text
    assert "不会自动提交交易" in page.text

    form = _form_from_url(url)
    first = client.post("/api/feishu-webhook/action/submit", data=form)
    second = client.post("/api/feishu-webhook/action/submit", data=form)
    assert first.status_code == 200
    assert "回执已记录" in first.text
    assert second.status_code == 200
    assert "无需重复提交" in second.text

    conn = connect(db_path)
    try:
        assert get_action_item(conn, action_id).state == "done"  # type: ignore[union-attr]
        assert get_plan(conn, plan_id).state == "entered"  # type: ignore[union-attr]
        done_notes = [
            note for note in list_annotations(conn, plan_id) if note.kind == "webhook_done"
        ]
        assert len(done_notes) == 1
    finally:
        conn.close()


def test_invalid_signature_and_expired_link_do_not_write(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client, db_path = _client(tmp_path, monkeypatch)
    plan_id, action_id = _make_action(db_path)
    url = _signed_url(plan_id, action_id)
    form = _form_from_url(url)
    form["signature"] = "0" * 64

    assert client.post("/api/feishu-webhook/action/submit", data=form).status_code == 401
    expired_url = _signed_url(plan_id, action_id, now=1)
    expired_path = expired_url.replace("https://lei.example.test", "")
    assert client.get(expired_path).status_code == 410

    conn = connect(db_path)
    try:
        assert get_action_item(conn, action_id).state == "open"  # type: ignore[union-attr]
        assert get_plan(conn, plan_id).state == "armed"  # type: ignore[union-attr]
    finally:
        conn.close()


def test_defer_requires_reason_and_resume_condition(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    client, db_path = _client(tmp_path, monkeypatch)
    plan_id, action_id = _make_action(db_path)
    form = _form_from_url(_signed_url(plan_id, action_id), operation="defer")

    response = client.post("/api/feishu-webhook/action/submit", data=form)
    assert response.status_code == 422
    assert "推迟必须填写原因和恢复条件" in response.json()["detail"]

    conn = connect(db_path)
    try:
        assert get_action_item(conn, action_id).state == "open"  # type: ignore[union-attr]
    finally:
        conn.close()


def test_defer_records_reason_and_predicate(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    from lei_signal.api.routes import feishu_webhook

    client, db_path = _client(tmp_path, monkeypatch)
    plan_id, action_id = _make_action(db_path)
    predicate = {"field": "close", "op": ">=", "ref": "ema20"}
    monkeypatch.setattr(
        feishu_webhook,
        "_validate_defer",
        lambda request, received_plan_id, resume_raw: predicate,
    )
    form = _form_from_url(_signed_url(plan_id, action_id), operation="defer")
    form["reason_cn"] = "条件尚未重新满足"
    form["resume_on_json"] = '{"field":"close","op":">=","ref":"ema20"}'

    response = client.post("/api/feishu-webhook/action/submit", data=form)
    assert response.status_code == 200

    conn = connect(db_path)
    try:
        item = get_action_item(conn, action_id)
        assert item is not None and item.state == "deferred"
        assert item.resume_on is not None and '"field": "close"' in item.resume_on
        reasons = [
            note.reason_cn
            for note in list_annotations(conn, plan_id)
            if note.kind == "defer_reason"
        ]
        assert reasons == ["条件尚未重新满足"]
    finally:
        conn.close()


def test_exit_done_stamps_exited_on_and_replay_is_idempotent(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """EXIT 确认盖 exited_on（与 ENTER 盖 entered_on 对称），重复提交幂等。"""
    client, db_path = _client(tmp_path, monkeypatch)
    plan_id, action_id = _make_action(db_path, kind="EXIT")
    # EXIT 分支要求计划已 entered：先把计划推进到 entered（入场日早于退出日）。
    conn = connect(db_path)
    try:
        set_entered(conn, plan_id, entered_on="2026-08-04")
    finally:
        conn.close()

    url = _signed_url(plan_id, action_id)
    form = _form_from_url(url)
    first = client.post("/api/feishu-webhook/action/submit", data=form)
    second = client.post("/api/feishu-webhook/action/submit", data=form)
    assert first.status_code == 200
    assert "回执已记录" in first.text
    assert second.status_code == 200
    assert "无需重复提交" in second.text

    conn = connect(db_path)
    try:
        assert get_action_item(conn, action_id).state == "done"  # type: ignore[union-attr]
        plan = get_plan(conn, plan_id)
        assert plan is not None and plan.state == "exited"
        # exited_on 取 EXIT 待办 due_from（系统判定的可执行日），与 entered_on 同源。
        assert plan.exited_on == "2026-08-05"
        assert plan.entered_on == "2026-08-04"  # 入场日未被退出覆盖
        done_notes = [
            note for note in list_annotations(conn, plan_id) if note.kind == "webhook_done"
        ]
        assert len(done_notes) == 1
    finally:
        conn.close()
