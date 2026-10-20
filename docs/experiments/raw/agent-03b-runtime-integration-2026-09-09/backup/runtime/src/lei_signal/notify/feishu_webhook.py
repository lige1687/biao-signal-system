"""飞书自定义机器人 Webhook 投递器。

自定义机器人只负责出站推送；按钮使用卡片的 open_url 交互，真正的写操作在 LEI
回执页完成。这样不需要 App ID/Secret，也不伪装成飞书原生回调。
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests

from lei_signal.notify.base import NotificationPayload

LOGGER = logging.getLogger(__name__)


class FeishuWebhookNotifier:
    def __init__(
        self,
        webhook_url: str | None,
        *,
        timeout_seconds: float = 8.0,
        session: Any = requests,
        dry_run: bool = False,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.session = session
        self.dry_run = dry_run

    @staticmethod
    def _card(payload: NotificationPayload) -> dict[str, Any]:
        actions = [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": button.label},
                "type": button.style,
                "behaviors": [{"type": "open_url", "default_url": button.url}],
            }
            for button in payload.buttons
        ]
        elements: list[dict[str, Any]] = [
            {"tag": "markdown", "content": payload.body_md}
        ]
        for index in range(0, len(actions), 5):
            elements.append({"tag": "action", "actions": actions[index : index + 5]})
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "red" if payload.tier == 1 else "blue",
                "title": {"tag": "plain_text", "content": payload.title},
            },
            "elements": elements,
        }

    def send(self, payload: NotificationPayload) -> bool:
        if not self.webhook_url:
            LOGGER.warning("FEISHU_WEBHOOK_URL 未配置，跳过飞书投递")
            return False
        body = {
            "msg_type": "interactive",
            # 飞书自定义机器人 Webhook 的 card 字段是 JSON 对象，不是字符串。
            "card": self._card(payload),
        }
        if self.dry_run:
            print(f"[dry-run] 飞书 Webhook: {json.dumps(body, ensure_ascii=False)}")
            return True
        for attempt in range(2):
            try:
                response = self.session.post(
                    self.webhook_url, json=body, timeout=self.timeout_seconds
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code", 0) in (0, None):
                        return True
                LOGGER.warning("飞书 Webhook 第 %s 次投递失败: %s", attempt + 1, response.text)
            except (requests.RequestException, ValueError) as exc:
                LOGGER.warning("飞书 Webhook 第 %s 次投递异常: %s", attempt + 1, exc)
        return False


__all__ = ["FeishuWebhookNotifier"]
