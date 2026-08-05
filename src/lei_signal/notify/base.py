"""通知渠道协议与渠道无关载荷。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class NotificationButton:
    """通知中的链接按钮。自定义机器人仅支持打开链接。"""

    label: str
    url: str
    style: str = "primary"


@dataclass(frozen=True, slots=True)
class NotificationPayload:
    """由判定结果渲染出的渠道无关通知。"""

    title: str
    body_md: str
    tier: int
    plan_id: str
    action_id: str | None = None
    buttons: tuple[NotificationButton, ...] = field(default_factory=tuple)
    rule_ids: frozenset[str] = field(default_factory=frozenset)


class Notifier(Protocol):
    """通知投递器。失败返回 False，不阻断后续计划。"""

    def send(self, payload: NotificationPayload) -> bool:
        """投递一条通知。"""
        ...


__all__ = ["NotificationButton", "NotificationPayload", "Notifier"]
