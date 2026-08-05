"""飞书 Webhook 通知与签名回执的无网络测试。"""
from __future__ import annotations

from dataclasses import replace

import pytest

from lei_signal.notify.base import NotificationButton, NotificationPayload
from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier
from lei_signal.notify.render import merge_daily_summaries
from lei_signal.notify.signing import build_action_url, sign_action, verify_action


def test_signing_round_trip_and_tamper_rejection() -> None:
    signature = sign_action("secret", "plan-1", "action-1", expires_at=200, nonce="n1")
    signed = verify_action(
        "secret",
        plan_id="plan-1",
        action_id="action-1",
        expires_at=200,
        nonce="n1",
        signature=signature,
        now=100,
    )
    assert signed.plan_id == "plan-1"
    with pytest.raises(ValueError, match="签名无效"):
        verify_action(
            "secret",
            plan_id="plan-1",
            action_id="action-2",
            expires_at=200,
            nonce="n1",
            signature=signature,
            now=100,
        )


def test_signing_rejects_expired_and_missing_secret() -> None:
    signature = sign_action("secret", "plan-1", "action-1", expires_at=100, nonce="n1")
    with pytest.raises(ValueError, match="过期"):
        verify_action(
            "secret",
            plan_id="plan-1",
            action_id="action-1",
            expires_at=100,
            nonce="n1",
            signature=signature,
            now=101,
        )
    with pytest.raises(ValueError, match="未配置"):
        build_action_url("https://example.test", "", "plan-1", "action-1", now=100)


def test_feishu_card_uses_object_card_and_open_url() -> None:
    payload = NotificationPayload(
        title="LEI 监督员",
        body_md="rule_id:test_rule · 判定方式为研究代理",
        tier=1,
        plan_id="plan-1",
    )
    captured: dict = {}

    class Response:
        status_code = 200
        text = "ok"

        @staticmethod
        def json() -> dict:
            return {"code": 0}

    class Session:
        @staticmethod
        def post(url, *, json, timeout):
            captured.update({"url": url, "json": json, "timeout": timeout})
            return Response()

    assert FeishuWebhookNotifier("https://example.test/hook", session=Session()).send(payload)
    body = captured["json"]
    assert body["msg_type"] == "interactive"
    assert isinstance(body["card"], dict)
    assert body["card"]["config"]["wide_screen_mode"] is True
    assert len(body["card"]["elements"]) == 1

    button_payload = replace(
        payload,
        buttons=(NotificationButton("处理", "https://example.test/action"),),
    )
    card = FeishuWebhookNotifier._card(button_payload)
    action = card["elements"][1]["actions"][0]
    assert action["behaviors"] == [
        {"type": "open_url", "default_url": "https://example.test/action"}
    ]


def test_feishu_missing_webhook_is_best_effort() -> None:
    payload = NotificationPayload("title", "body", 2, "plan-1")
    assert not FeishuWebhookNotifier(None).send(payload)


def test_daily_summaries_merge_tier_two_only() -> None:
    first = NotificationPayload("a", "first", 2, "p1", action_id="a1")
    second = NotificationPayload("b", "second", 2, "p2", action_id="a2")
    urgent = NotificationPayload("urgent", "urgent", 1, "p1")
    summary = merge_daily_summaries([first, urgent, second])
    assert summary is not None
    assert summary.title == "LEI 监督员 · 每日待办汇总"
    assert "first" in summary.body_md and "second" in summary.body_md
    assert summary.plan_id == "daily-summary"
    assert merge_daily_summaries([urgent]) is None
