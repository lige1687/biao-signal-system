"""飞书 Webhook 动作链接签名。

自定义机器人无法提供操作者身份，因此动作链接只证明“由 LEI 签发”，不能证明点击者是谁。
链接短时有效，nonce 只能消费一次，写操作仍由回执端点做幂等校验。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True, slots=True)
class SignedAction:
    plan_id: str
    action_id: str
    expires_at: int
    nonce: str


def _message(plan_id: str, action_id: str, expires_at: int, nonce: str) -> bytes:
    return f"{plan_id}\n{action_id}\n{expires_at}\n{nonce}".encode()


def sign_action(
    secret: str,
    plan_id: str,
    action_id: str,
    *,
    expires_at: int,
    nonce: str,
) -> str:
    """为动作上下文生成十六进制 HMAC-SHA256。"""
    if not secret:
        raise ValueError("FEISHU_ACTION_SECRET 未配置")
    return hmac.new(
        secret.encode(), _message(plan_id, action_id, expires_at, nonce), hashlib.sha256
    ).hexdigest()


def build_action_url(
    base_url: str,
    secret: str,
    plan_id: str,
    action_id: str,
    *,
    ttl_seconds: int = 900,
    now: int | None = None,
) -> str:
    """生成短期有效的回执页 URL。"""
    issued_at = int(time.time()) if now is None else now
    expires_at = issued_at + ttl_seconds
    nonce = secrets.token_urlsafe(16)
    signature = sign_action(
        secret, plan_id, action_id, expires_at=expires_at, nonce=nonce
    )
    query = urlencode(
        {
            "plan_id": plan_id,
            "action_id": action_id,
            "expires_at": str(expires_at),
            "nonce": nonce,
            "signature": signature,
        }
    )
    return f"{base_url.rstrip('/')}/api/feishu-webhook/action?{query}"


def verify_action(
    secret: str,
    *,
    plan_id: str,
    action_id: str,
    expires_at: int,
    nonce: str,
    signature: str,
    now: int | None = None,
) -> SignedAction:
    """校验签名和有效期；nonce 是否已使用由持久层判断。"""
    current = int(time.time()) if now is None else now
    if expires_at < current:
        raise ValueError("动作链接已过期，请等待下一次提醒或重新生成")
    expected = sign_action(
        secret, plan_id, action_id, expires_at=expires_at, nonce=nonce
    )
    if not hmac.compare_digest(expected, signature):
        raise ValueError("动作链接签名无效")
    return SignedAction(plan_id, action_id, expires_at, nonce)


__all__ = ["SignedAction", "build_action_url", "sign_action", "verify_action"]
