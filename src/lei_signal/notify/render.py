"""监督周期结果到通知载荷的确定性渲染。"""
from __future__ import annotations

from lei_signal.notify.base import NotificationButton, NotificationPayload
from lei_signal.notify.signing import build_action_url
from lei_signal.plans.actions import CycleResult
from lei_signal.plans.grounding import RESEARCH_PROXY_MARKER, verify_grounding
from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan

#: Tier1 逐条即时推：已在场内、必须马上知道的退出类事件。
#: 持仓盯盘的止损击穿/止盈达到/信号命中同属此列--价位到了才推，晚一天就没意义。
_TIER1_CODES = frozenset({
    "EXIT_TRIGGERED",
    "INVALIDATION_BREACHED",
    "STOP_PRICE_BREACHED",
    "TAKE_PROFIT_REACHED",
    "SIGNAL_WATCH_TRIGGERED",
})
_TIER2_CODES = frozenset({"ENTRY_CONDITIONS_MET", "PLAN_EXPIRING"})
_TIER3_CODES = frozenset(
    {
        "ENTRY_RR_BELOW_IDEAL",
        "ENTRY_RR_NOT_COMPUTABLE",
        "MODULE_NOT_IMPLEMENTED",
        "PLAN_STALE_RULESET",
        "PLAN_ORPHANED",
    }
)


def _alert_line(alert: PlanAlert) -> str:
    provenance = alert.principle_source or "规则账本"
    line = f"**{alert.code}** · {alert.next_step_cn or alert.code}\n"
    line += f"rule_id:{alert.rule_id or '-'} · {provenance} · {RESEARCH_PROXY_MARKER}"
    return line


def _safe_body(body: str, alerts: list[PlanAlert]) -> tuple[str, frozenset[str]]:
    rule_ids = frozenset(a.rule_id for a in alerts if a.rule_id)
    ok, _ = verify_grounding(body, set(rule_ids))
    if ok:
        return body, rule_ids
    fallback = "\n".join(
        f"{a.code} · rule_id:{a.rule_id or '-'} · {RESEARCH_PROXY_MARKER}" for a in alerts
    )
    return fallback, rule_ids


def _action_detail(
    plan: TradePlan,
    item: ActionItem,
    alerts: list[PlanAlert],
) -> tuple[str, frozenset[str]]:
    related = [a for a in alerts if a.code == item.source_alert_code]
    body_lines = [
        f"**{plan.symbol} · {item.kind} 待办**",
        f"催办第 {item.nag_count} 次 · 可执行日 {item.due_from or '-'}",
    ]
    body_lines.extend(_alert_line(a) for a in related)
    return _safe_body("\n\n".join(body_lines), related)


def _action_button(
    plan: TradePlan,
    item: ActionItem,
    *,
    action_base_url: str,
    action_secret: str,
) -> NotificationButton | None:
    if not action_base_url or not action_secret:
        return None
    return NotificationButton(
        "处理此待办",
        build_action_url(action_base_url, action_secret, plan.plan_id, item.action_id),
    )


def _action_payload(
    plan: TradePlan,
    item: ActionItem,
    alerts: list[PlanAlert],
    *,
    action_base_url: str,
    action_secret: str,
) -> NotificationPayload:
    body, rule_ids = _action_detail(plan, item, alerts)
    button = _action_button(
        plan, item, action_base_url=action_base_url, action_secret=action_secret
    )
    return NotificationPayload(
        title="LEI 监督员 · 待办确认",
        body_md=body,
        tier=1,
        plan_id=plan.plan_id,
        action_id=item.action_id,
        buttons=(button,) if button else (),
        rule_ids=rule_ids,
    )


def _summary_payload(
    plan: TradePlan,
    items: list[ActionItem],
    alerts: list[PlanAlert],
    *,
    action_base_url: str,
    action_secret: str,
) -> NotificationPayload:
    details: list[str] = []
    rule_ids: set[str] = set()
    buttons: list[NotificationButton] = []
    for item in items:
        detail, item_rule_ids = _action_detail(plan, item, alerts)
        details.append(detail)
        rule_ids.update(item_rule_ids)
        button = _action_button(
            plan, item, action_base_url=action_base_url, action_secret=action_secret
        )
        if button:
            buttons.append(
                NotificationButton(f"处理 {item.kind}（第 {item.nag_count} 次）", button.url)
            )
    related_alerts = [
        alert
        for alert in alerts
        if any(alert.code == item.source_alert_code for item in items)
    ]
    handled_codes = {item.source_alert_code for item in items}
    summary_alerts = [
        a for a in alerts if a.code in _TIER2_CODES and a.code not in handled_codes
    ]
    if summary_alerts:
        details.extend(_alert_line(a) for a in summary_alerts)
        rule_ids.update(a.rule_id for a in summary_alerts if a.rule_id)
    body, safe_rule_ids = _safe_body(
        "\n\n".join(details), related_alerts + summary_alerts
    )
    return NotificationPayload(
        title=f"LEI 监督员 · {plan.symbol} 每日汇总",
        body_md=body,
        tier=2,
        plan_id=plan.plan_id,
        action_id=items[0].action_id if items else None,
        buttons=tuple(buttons),
        rule_ids=safe_rule_ids or frozenset(rule_ids),
    )


def render_cycle(
    plan: TradePlan,
    result: CycleResult,
    *,
    action_base_url: str,
    action_secret: str,
) -> list[NotificationPayload]:
    """按通知分级渲染一轮结果。

    DATA_STALE 不投催办；Tier 1 单独推；开放待办按待办投；其余 Tier 2 汇总。
    """
    if any(a.code == "DATA_STALE" for a in result.alerts):
        return []

    tier1_items = [
        item for item in result.nagged if item.source_alert_code in _TIER1_CODES
    ]
    tier2_items = [
        item for item in result.nagged if item.source_alert_code not in _TIER1_CODES
    ]
    payloads = [
        _action_payload(
            plan,
            item,
            result.alerts,
            action_base_url=action_base_url,
            action_secret=action_secret,
        )
        for item in tier1_items
    ]
    handled_codes = {item.source_alert_code for item in result.nagged}

    tier1 = [
        a for a in result.alerts if a.code in _TIER1_CODES and a.code not in handled_codes
    ]
    for alert in tier1:
        body, rule_ids = _safe_body(_alert_line(alert), [alert])
        payloads.append(
            NotificationPayload(
                title=f"LEI 监督员 · {alert.code}",
                body_md=body,
                tier=1,
                plan_id=plan.plan_id,
                rule_ids=rule_ids,
            )
        )

    tier2 = [
        a
        for a in result.alerts
        if a.code in _TIER2_CODES
        and a.code not in handled_codes
        and a.code not in _TIER3_CODES
    ]
    if tier2_items or tier2:
        payloads.append(
            _summary_payload(
                plan,
                tier2_items,
                result.alerts,
                action_base_url=action_base_url,
                action_secret=action_secret,
            )
        )
    return payloads


def merge_daily_summaries(
    payloads: list[NotificationPayload],
) -> NotificationPayload | None:
    """将一轮监督中的 Tier 2 合并成一张卡，避免按计划刷屏。"""
    summaries = [payload for payload in payloads if payload.tier == 2]
    if not summaries:
        return None
    plan_ids = list(dict.fromkeys(payload.plan_id for payload in summaries))
    buttons = tuple(button for payload in summaries for button in payload.buttons)
    if len(buttons) > 50:
        buttons = buttons[:50]
    rule_ids = frozenset(rule_id for payload in summaries for rule_id in payload.rule_ids)
    return NotificationPayload(
        title="LEI 监督员 · 每日待办汇总",
        body_md="\n\n---\n\n".join(payload.body_md for payload in summaries),
        tier=2,
        plan_id=plan_ids[0] if len(plan_ids) == 1 else "daily-summary",
        buttons=buttons,
        rule_ids=rule_ids,
    )


__all__ = ["merge_daily_summaries", "render_cycle"]
