"""消息面重大事件推送（参考层，宏观线；持仓线等通路交接后接入）。

推送什么（用户口径 2026-09-04）：
1. 危机状态机事件（V4 刚崩警示 / V3 出清企稳，最高优先）——触发即推；
2. 当日宏观/风险类重大消息（category ∈ {macro, risk} 且 importance ≥ 8）
   ——美联储议息、非农、战争等系统性事件；
3. 「影响窗口」：importance ≥ 9 的事件发布后 3 日内持续随推送出现
   （标"X日前 · 影响窗口"）——关键信息的影响不止当天。

铁律（对齐 notify/handoff-feishu-notifier）：
- 参考层信息推送：文案只有事实与读数，无买卖指令（llm_note 本身不给建议）；
- best-effort：任何投递失败记日志不抛出，绝不阻断管线；
- 未配置任何渠道时静默跳过（dry-run 可显式验证）。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from lei_signal.notify.base import NotificationPayload
from lei_signal.newsfeed.store import NewsStore

logger = logging.getLogger(__name__)

#: 当日重大事件门槛（宏观/风险类）。
PUSH_IMPORTANCE = 8
#: 影响窗口：≥9 分事件的持续天数（含发布日）。
IMPACT_WINDOW_DAYS = 3

_DIR_ARROW = {"bullish": "利多↑", "bearish": "利空↓", "neutral": ""}


def _major_rows(store: NewsStore, today: str) -> tuple[list[dict], list[dict]]:
    """(当日≥8分宏观/风险, 3日内≥9分非今日) —— 后者即影响窗口。"""
    rows = store.query_items(
        category=None, scored="scored", min_importance=PUSH_IMPORTANCE, limit=200
    )[0]
    fresh: list[dict] = []
    window: list[dict] = []
    for r in rows:
        d = dict(r)
        day = str(d.get("published_at") or "")[:10]
        cat = d.get("category")
        imp = d.get("importance") or 0
        if cat not in ("macro", "risk"):
            continue
        if day == today:
            fresh.append(d)
        elif imp >= 9 and _within_days(day, today, IMPACT_WINDOW_DAYS):
            d["_days_ago"] = _days_between(day, today)
            window.append(d)
    fresh.sort(key=lambda x: -(x.get("importance") or 0))
    window.sort(key=lambda x: -(x.get("importance") or 0))
    return fresh, window


def _days_between(day: str, today: str) -> int:
    from datetime import date

    try:
        return (date.fromisoformat(today) - date.fromisoformat(day)).days
    except ValueError:
        return 99


def _within_days(day: str, today: str, n: int) -> bool:
    return 1 <= _days_between(day, today) < n


def _fmt_item(d: dict) -> str:
    arrow = _DIR_ARROW.get(d.get("direction") or "", "")
    note = (d.get("llm_note") or "").strip()
    head = f"**★{d.get('importance')} {arrow} {d.get('title', '')[:48]}**".replace(
        "  ", " "
    )
    suffix = ""
    if "_days_ago" in d:
        suffix = f"（{d['_days_ago']}日前 · 影响窗口内）"
    line = f"- {head}{suffix}"
    if note:
        line += f"\n  {note[:60]}"
    return line


def build_push_payloads(db_path: str | Path) -> list[NotificationPayload]:
    """组装待投递的通知（纯读库与本地文件，不发网络）。无内容返回空列表。"""
    from datetime import datetime

    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    payloads: list[NotificationPayload] = []

    # 1) 危机状态机（触发即推，最高优先）
    try:
        from lei_signal.market_context.crisis_events import get_crisis_states

        crisis = get_crisis_states()
    except Exception:  # noqa: BLE001 — 危机读数失败不影响消息推送
        crisis = None
    for a in (crisis or {}).get("alerts", []):
        payloads.append(
            NotificationPayload(
                title=f"⚠ {a['title']}",
                body_md=f"{a['desc']}\n\n*研究代理 · 环境层参考事件，不构成买卖建议*",
                tier=1,
                plan_id="newsfeed-crisis",
            )
        )

    # 2) 宏观重大事件 + 影响窗口
    store = NewsStore(db_path)
    try:
        fresh, window = _major_rows(store, today)
    finally:
        store.close()
    if fresh or window:
        lines: list[str] = []
        if fresh:
            lines.append("**今日重大宏观/风险事件**")
            lines += [_fmt_item(d) for d in fresh[:5]]
        if window:
            lines.append("\n**仍在影响窗口（≥9分）**")
            lines += [_fmt_item(d) for d in window[:3]]
        lines.append("\n*消息面参考层 · 非交易信号 · 详情打开资讯流页*")
        payloads.append(
            NotificationPayload(
                title=f"📰 消息面 · 今日重大事件 {len(fresh)} 条"
                + (f"（窗口内 {len(window)}）" if window else ""),
                body_md="\n".join(lines),
                tier=2,
                plan_id="newsfeed-macro",
            )
        )
    return payloads


def push_daily_brief(db_path: str | Path, *, dry_run: bool = False) -> int:
    """管线打分完成后调用：组装并投递。返回成功投递条数（0=无内容或全失败）。"""
    if "pytest" in __import__("sys").modules and not dry_run:
        return 0
    payloads = build_push_payloads(db_path)
    if not payloads:
        return 0
    from lei_signal.notify.macos import MacNotifier

    notifiers = [MacNotifier(dry_run=dry_run)]
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    if webhook or dry_run:
        from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier

        notifiers.append(
            FeishuWebhookNotifier(webhook if not dry_run else None, dry_run=dry_run)
        )
    sent = 0
    for p in payloads:
        for n in notifiers:
            try:
                if n.send(p):
                    sent += 1
                    break
            except Exception:  # noqa: BLE001 — 单渠道失败试下一渠道
                logger.warning("消息面推送渠道失败：%s", type(n).__name__)
    return sent


__all__ = [
    "IMPACT_WINDOW_DAYS",
    "PUSH_IMPORTANCE",
    "build_push_payloads",
    "push_daily_brief",
]
