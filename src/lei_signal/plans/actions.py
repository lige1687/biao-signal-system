"""待办状态机与催办节拍（决策 4 / 4b / 4c）。

监督员追着要结果，直到用户给结论。催办节拍绑 ``last_bar_date`` 前进（非日历日）：
数据不动不催，长假不误催。``DATA_STALE`` 不递增 ``nag_count``。推迟复活是信号触发
（复用 ``monitor.evaluate_resume``），非定时。

本模块是纯 DB 操作 + 判定，无 LLM、无网络。``daily_nag`` 是它的 launchd 入口。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, TradingCalendar
from lei_signal.domain.rules_config import get_rule
from lei_signal.plans.models import ActionItem, TradePlan
from lei_signal.plans.monitor import (
    RESOLVABLE_PATHS,
    MonitorContext,
    evaluate_plan,
    evaluate_resume,
)
from lei_signal.plans.store import (
    add_annotation,
    list_action_items,
    list_plans,
    mark_superseded,
    update_action_item,
    upsert_action_item,
)

ACTION_RESUMED = "ACTION_RESUMED"
CLOSE_KIND_CONDITIONS_LOST = "conditions_lost"
CLOSE_KIND_SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class CycleResult:
    """单计划一个数据周期的监督结果。"""

    plan_id: str
    alerts: list = field(default_factory=list)
    nagged: list[ActionItem] = field(default_factory=list)
    revived: list[ActionItem] = field(default_factory=list)
    superseded: list[str] = field(default_factory=list)
    review: ActionItem | None = None


def run_plan_cycle(
    conn: sqlite3.Connection,
    plan: TradePlan,
    ctx: MonitorContext,
    *,
    calendar: TradingCalendar = DEFAULT_TRADING_CALENDAR,
) -> CycleResult:
    """单计划一轮监督：判定 -> 同步待办 -> 复活 -> 催办 -> 到期 REVIEW -> 顶替。"""
    alerts = evaluate_plan(plan, ctx, calendar=calendar)
    sync_action_items(conn, plan, alerts)
    revived = revive_deferred(conn, plan, ctx)
    nagged = nag_open_items(conn, plan, ctx, data_stale=ctx.cache_fallback_used)
    review = ensure_review_for_expiry(conn, plan, ctx)
    superseded: list[str] = []
    if plan.state == "entered":
        superseded = handle_supersede(conn, plan)
    return CycleResult(
        plan_id=plan.plan_id, alerts=alerts, nagged=nagged,
        revived=revived, superseded=superseded, review=review,
    )


def sync_action_items(
    conn: sqlite3.Connection, plan: TradePlan, alerts: list
) -> list[ActionItem]:
    """从 alert 列表同步待办：ENTER/EXIT/REVIEW 建开放待办；CLOSE_ENTER 关闭 ENTER。

    用户主动推迟（deferred）的待办不被覆盖--只有 ``resume_on`` 满足才回 open
    （决策 4c：信号触发，非定时）。
    """
    existing_by_kind = {i.kind: i for i in list_action_items(conn, plan.plan_id)}
    items: list[ActionItem] = []
    for alert in alerts:
        kind = alert.action_kind
        if kind in ("ENTER", "EXIT", "REVIEW"):
            ex = existing_by_kind.get(kind)
            if ex is not None and ex.state == "deferred":
                continue  # 推迟项不被覆盖；由 revive_deferred 按 resume_on 复活
            items.append(upsert_action_item(
                conn, plan_id=plan.plan_id, kind=kind,
                source_alert_code=alert.code, state="open",
                due_from=alert.actionable_from,
            ))
        elif kind == "CLOSE_ENTER":
            ex = existing_by_kind.get("ENTER")
            if ex is not None and ex.state == "open":
                update_action_item(
                    conn, ex.action_id, state="expired",
                    close_kind=CLOSE_KIND_CONDITIONS_LOST,
                    closed_on=alert.actionable_from,
                )
    return items


def revive_deferred(
    conn: sqlite3.Connection, plan: TradePlan, ctx: MonitorContext
) -> list[ActionItem]:
    """验所有 deferred 项的 resume_on：满足则回 open 并记 annotation（决策 4c）。"""
    revived: list[ActionItem] = []
    for item in list_action_items(conn, plan.plan_id, state="deferred"):
        if not item.resume_on:
            continue
        try:
            predicate = json.loads(item.resume_on)
            satisfied = evaluate_resume(predicate, ctx)
        except (ValueError, json.JSONDecodeError):
            continue
        if satisfied:
            update_action_item(conn, item.action_id, state="open", close_kind=None)
            add_annotation(
                conn, plan.plan_id, ref_kind="action", ref_id=item.action_id,
                kind="review_conclusion",
                reason_cn="推迟项复活条件满足，自动回到 open", author="system",
            )
            revived.append(item)
    return revived


def nag_open_items(
    conn: sqlite3.Connection, plan: TradePlan, ctx: MonitorContext, *, data_stale: bool
) -> list[ActionItem]:
    """催办开放待办。data_stale 时不递增；同一 last_bar_date 不重复催（幂等）。"""
    if data_stale:
        return []
    nagged: list[ActionItem] = []
    for item in list_action_items(conn, plan.plan_id, state="open"):
        if item.last_nagged_bar_date == ctx.last_bar_date:
            continue  # 本 bar 已催过
        update_action_item(
            conn, item.action_id,
            nag_count=item.nag_count + 1,
            last_nagged_bar_date=ctx.last_bar_date,
        )
        nagged.append(item)
    return nagged


def handle_supersede(
    conn: sqlite3.Connection, entered_plan: TradePlan
) -> list[str]:
    """决策 5：同标的同方向只允许一条 entered。新 entered 顶替既有的 armed/entered。"""
    superseded: list[str] = []
    for other in list_plans(conn, symbol=entered_plan.symbol):
        if other.plan_id == entered_plan.plan_id:
            continue
        if other.direction != entered_plan.direction:
            continue
        if other.state not in ("armed", "entered"):
            continue
        mark_superseded(conn, other.plan_id, by_plan_id=entered_plan.plan_id)
        add_annotation(
            conn, other.plan_id, ref_kind="revision", ref_id=None,
            kind="review_conclusion",
            reason_cn=f"被同向计划 {entered_plan.plan_id} 顶替（决策5）",
            author="system",
        )
        for item in list_action_items(conn, other.plan_id):
            if item.state == "open":
                update_action_item(
                    conn, item.action_id, state="expired",
                    close_kind=CLOSE_KIND_SUPERSEDED,
                )
        superseded.append(other.plan_id)
    return superseded


def ensure_review_for_expiry(
    conn: sqlite3.Connection, plan: TradePlan, ctx: MonitorContext
) -> ActionItem | None:
    """决策 6：valid_until 到期产 REVIEW 待办，但**不改 plan 状态**。"""
    if not plan.valid_until or ctx.last_bar_date < plan.valid_until:
        return None
    existing = list_action_items(conn, plan.plan_id)
    if any(i.kind == "REVIEW" and i.state == "open" for i in existing):
        return None
    return upsert_action_item(
        conn, plan_id=plan.plan_id, kind="REVIEW",
        source_alert_code="PLAN_EXPIRING", state="open", due_from=ctx.last_bar_date,
    )


# ---------------------------------------------------------------- 推迟复活谓词校验


def resume_options(ctx: MonitorContext) -> str:
    """列出当前可引用的 rule_id / 字段，供拒绝时回执。"""
    return (
        f"可引用 rule_id（当日 new_events）: {list(ctx.new_event_rule_ids)}; "
        f"路径: {', '.join(RESOLVABLE_PATHS)}"
    )


def validate_resume_on(predicate: dict[str, Any], ctx: MonitorContext) -> None:
    """推迟时校验 resume_on 谓词可被系统计算，否则拒绝并报可引用清单。"""
    if "rule_id" in predicate:
        rid = str(predicate["rule_id"])
        try:
            get_rule(rid)
        except KeyError as exc:
            raise ValueError(
                f"resume_on 引用未注册的 rule_id: {rid}; {resume_options(ctx)}"
            ) from exc
    elif "field" in predicate:
        try:
            evaluate_resume(predicate, ctx)
        except ValueError as exc:
            raise ValueError(f"{exc}; {resume_options(ctx)}") from exc
    else:
        raise ValueError(
            f"resume_on 谓词格式不合法: {predicate}; {resume_options(ctx)}"
        )


__all__ = [
    "ACTION_RESUMED",
    "CLOSE_KIND_CONDITIONS_LOST",
    "CLOSE_KIND_SUPERSEDED",
    "ensure_review_for_expiry",
    "handle_supersede",
    "nag_open_items",
    "resume_options",
    "revive_deferred",
    "sync_action_items",
    "validate_resume_on",
]
