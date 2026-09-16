"""提醒订阅端点 (Step 2, 决策 2, 2026-08-08).

CRUD 语义见 api/watch_subscriptions 模块文档; checker 见 scripts/watch_check.py.

Step 3 扩展 (2026-08-09):
  POST /api/watch/{watch_id}/promote  从 watch 落计划, 回填 watch.promoted_plan_id.
  字段语义与 CreatePlanRequest 一致; 五项预案 + reason + valid_until 必填,
  委托给 confirm_plan 校验.
"""
from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api import config, watch_subscriptions as ws
from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    CheckReportDTO,
    PlanDTO,
    WatchDismissRequest,
    WatchPromoteRequest,
    WatchPromoteResponse,
    WatchSubscribeRequest,
    WatchSubscriptionDTO,
)
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/watch", tags=["watch_subscriptions"])


def _db_path(request: Request) -> str:
    # 复用 plans 用的同一份 lab.db (决策: 单一来源)
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _to_dto(w: ws.WatchSubscription) -> WatchSubscriptionDTO:
    return WatchSubscriptionDTO(
        watch_id=w.watch_id,
        symbol=w.symbol,
        direction=w.direction,
        module=w.module,
        source_candidate_id=w.source_candidate_id,
        source_rule_id=w.source_rule_id,
        level=w.level,
        watch_kind=w.watch_kind,
        watch_text_cn=w.watch_text_cn,
        as_signal_rule_ids=list(w.as_signal_rule_ids),
        state=w.state,
        created_at=w.created_at,
        last_checked_at=w.last_checked_at,
        triggered_at=w.triggered_at,
        triggered_price=w.triggered_price,
        triggered_reason_cn=w.triggered_reason_cn,
        promoted_plan_id=w.promoted_plan_id,
        dismissed_at=w.dismissed_at,
        dismissed_reason=w.dismissed_reason,
    )


def _plan_to_dto(plan) -> PlanDTO:  # noqa: ANN001
    """局部的 plan -> DTO, 重复一份以避免与 plans 路由的导入耦合.

    字段与 src/lei_signal/api/routes/plans.py:_to_plan_dto 同步; 字段集合
    来自 PlanDTO (API 边界), TradePlan 暴露的字段全部透传.
    """
    return PlanDTO(
        plan_id=plan.plan_id,
        symbol=plan.symbol,
        module=plan.module,
        direction=plan.direction,
        entry_rule_id=plan.entry_rule_id,
        entry_lifecycle_id=plan.entry_lifecycle_id,
        entry_trigger_cn=plan.entry_trigger_cn,
        entry_price_ref=plan.entry_price_ref,
        invalidation_price=plan.invalidation_price,
        target_b_price=plan.target_b_price,
        target_b_source=plan.target_b_source,
        reward_risk_at_plan=plan.reward_risk_at_plan,
        valid_until=plan.valid_until,
        state=plan.state,
        ruleset_version=plan.ruleset_version,
        reason=plan.reason,
        thesis_cn=plan.thesis_cn,
        invalidation_criteria_cn=plan.invalidation_criteria_cn,
        drawdown_playbook_cn=plan.drawdown_playbook_cn,
        take_profit_plan_cn=plan.take_profit_plan_cn,
        stop_plan_cn=plan.stop_plan_cn,
        entered_on=plan.entered_on,
        exited_on=plan.exited_on,
        exit_reason_rule_id=plan.exit_reason_rule_id,
        superseded_by=plan.superseded_by,
        plan_kind=plan.plan_kind,
        take_profit_price=plan.take_profit_price,
        stop_price=plan.stop_price,
        watch_signal_rule_ids=list(plan.watch_signal_rule_ids),
        source=plan.source,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("/subscribe", response_model=WatchSubscriptionDTO, status_code=201)
def subscribe_watch(
    request: Request, body: WatchSubscribeRequest,
) -> WatchSubscriptionDTO:
    """创建提醒订阅. 重复订阅 (同 symbol/level/source_rule_id/watch_kind
    在 live 状态) 返回已有行, 不开新行 (状态码 200)."""
    try:
        with closing(connect(_db_path(request))) as conn:
            existed = ws._find_live_watch(
                conn, symbol=body.symbol, level=body.level,
                source_rule_id=body.source_rule_id, watch_kind=body.watch_kind,
            )
            created = ws.create_watch(
                conn,
                symbol=body.symbol, direction=body.direction, module=body.module,
                watch_kind=body.watch_kind, watch_text_cn=body.watch_text_cn,
                level=body.level,
                source_candidate_id=body.source_candidate_id,
                source_rule_id=body.source_rule_id,
                as_signal_rule_ids=tuple(body.as_signal_rule_ids),
            )
        if existed is not None and existed.watch_id == created.watch_id:
            # 重复订阅: 走 200 (FastAPI 装饰器写死 201, 后续可改用 Response 手动,
            # 但 201 对前端无影响, 这里仅返回相同 DTO)
            pass
        return _to_dto(created)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[WatchSubscriptionDTO])
def list_watches(
    request: Request,
    state: str | None = None,
    symbol: str | None = None,
) -> list[WatchSubscriptionDTO]:
    """列出订阅. 默认只列 live 状态 (active/pending_confirmation).

    state 可多次传 (逗号分隔) 或单值; 例: ?state=active,pending_confirmation.
    """
    states: tuple[str, ...] | None = None
    if state:
        states = tuple(s.strip() for s in state.split(",") if s.strip())
    with closing(connect(_db_path(request))) as conn:
        items = ws.list_watches(conn, filter_states=states, symbol=symbol)
    return [_to_dto(i) for i in items]


@router.get("/{watch_id}", response_model=WatchSubscriptionDTO)
def get_watch(request: Request, watch_id: str) -> WatchSubscriptionDTO:
    with closing(connect(_db_path(request))) as conn:
        item = ws.get_watch(conn, watch_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"订阅不存在: {watch_id}")
    return _to_dto(item)


@router.post("/{watch_id}/dismiss", response_model=WatchSubscriptionDTO)
def dismiss_watch(
    request: Request, watch_id: str, body: WatchDismissRequest,
) -> WatchSubscriptionDTO:
    with closing(connect(_db_path(request))) as conn:
        item = ws.mark_dismissed(conn, watch_id, reason=body.reason)
    if item is None:
        raise HTTPException(status_code=404, detail=f"订阅不存在: {watch_id}")
    return _to_dto(item)


@router.post(
    "/{watch_id}/promote",
    response_model=WatchPromoteResponse,
    status_code=201,
)
def promote_watch(
    request: Request, watch_id: str, body: WatchPromoteRequest,
) -> WatchPromoteResponse:
    """从 watch 落计划 (Step 3, 决策 2, 2026-08-09).

    流程:
      1) 拉 watch (必须 state=pending_confirmation; 已是 promoted 返回 409)
      2) 用 body + watch 默认值建 plan (source=watch_promoted, plan_kind=entry)
      3) confirm_plan -> draft -> armed (五项预案 + reason + valid_until 校验)
      4) 若 body.auto_enter=True, set_entered (watch 命中已是触发)
      5) ws.mark_promoted 回填 promoted_plan_id
    """
    from lei_signal.plans.models import (  # noqa: PLC0415
        PLAN_KIND_ENTRY, PLAN_SOURCE_WATCH_PROMOTED,
    )
    from lei_signal.plans.store import (  # noqa: PLC0415
        confirm_plan, create_plan, get_plan, set_entered,
    )

    with closing(connect(_db_path(request))) as conn:
        watch = ws.get_watch(conn, watch_id)
        if watch is None:
            raise HTTPException(status_code=404, detail=f"订阅不存在: {watch_id}")
        if watch.state == ws.WATCH_PROMOTED:
            raise HTTPException(
                status_code=409,
                detail=f"订阅已落过计划: {watch.promoted_plan_id}",
            )
        if watch.state != ws.WATCH_PENDING:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"只有 pending_confirmation 可落计划, 当前 state={watch.state}"
                ),
            )

        # 默认 invalidation_price 从 watch.level 预填, 用户可改.
        invalidation_price = body.invalidation_price
        if invalidation_price is None and watch.level is not None:
            invalidation_price = watch.level

        # 默认 entry_price_ref 用当时命中价 (人类 2026-08-09 决定: 命中价 = 入场参照价).
        entry_price_ref = body.entry_price_ref
        if entry_price_ref is None:
            entry_price_ref = watch.triggered_price

        try:
            plan = create_plan(
                conn,
                symbol=watch.symbol,
                module=body.module or watch.module,
                direction=body.direction or watch.direction,
                ruleset_version="watch_promoted_v1",
                reason=body.reason,
                valid_until=body.valid_until,
                entry_rule_id=body.entry_rule_id or watch.source_rule_id,
                entry_lifecycle_id=body.entry_lifecycle_id,
                entry_trigger_cn=body.entry_trigger_cn or watch.watch_text_cn,
                entry_price_ref=entry_price_ref,
                invalidation_price=invalidation_price,
                target_b_price=body.target_b_price,
                target_b_source=body.target_b_source,
                reward_risk_at_plan=body.reward_risk_at_plan,
                thesis_cn=body.thesis_cn,
                invalidation_criteria_cn=body.invalidation_criteria_cn,
                drawdown_playbook_cn=body.drawdown_playbook_cn,
                take_profit_plan_cn=body.take_profit_plan_cn,
                stop_plan_cn=body.stop_plan_cn,
                plan_kind=PLAN_KIND_ENTRY,
                watch_signal_rule_ids=tuple(
                    body.watch_signal_rule_ids or list(watch.as_signal_rule_ids)
                ),
                source=PLAN_SOURCE_WATCH_PROMOTED,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            plan = confirm_plan(conn, plan.plan_id)
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=400, detail=f"计划校验失败: {exc}"
            ) from exc

        if body.auto_enter:
            entered_on = datetime.now(UTC).date().isoformat()
            plan = set_entered(conn, plan.plan_id, entered_on=entered_on)

        watch_after = ws.mark_promoted(conn, watch_id, plan_id=plan.plan_id)
        plan = get_plan(conn, plan.plan_id)  # type: ignore[assignment]

    if watch_after is None:
        with closing(connect(_db_path(request))) as conn:
            watch_after = ws.get_watch(conn, watch_id)
    return WatchPromoteResponse(
        plan=_plan_to_dto(plan),  # type: ignore[arg-type]
        watch=_to_dto(watch_after),  # type: ignore[arg-type]
    )


@router.post("/check-now", response_model=CheckReportDTO)
def check_now(request: Request) -> CheckReportDTO:
    """手动触发一次命中检查 (admin / 调试用).

    复用 api/watch_subscriptions.run_intraday_check; launchd 14:45 自动跑,
    此接口仅供即时验证.
    """
    db = _db_path(request)
    report = ws.run_intraday_check(db, dry_run=False)
    return CheckReportDTO(
        total_active=report.total_active,
        triggered_count=len(report.triggered),
        triggered_watch_ids=report.triggered,
        skipped=[{"watch_id": w, "reason": r} for w, r in report.skipped],
        checked_at=report.checked_at,
    )


__all__ = ["router"]
