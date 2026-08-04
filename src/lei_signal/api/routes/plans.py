"""计划台账 REST 路由（监督员 v1）。

CRUD + 触发判定 + 待办。判定权在 plans/ 判定层（Python），本路由只做编排与 DTO 映射。
不接 LLM；LLM 讲解由 skill 侧调 /alerts 后用 grounding.render_alerts 完成。
"""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    ActionItemDTO,
    CreatePlanRequest,
    DeferRequest,
    PlanAlertDTO,
    PlanDTO,
    RevisionRequest,
)
from lei_signal.plans.actions import (
    handle_supersede,
    validate_resume_on,
)
from lei_signal.plans.context import context_from_result
from lei_signal.plans.drift import check_revision
from lei_signal.plans.models import VERDICT_WITHIN_PLAYBOOK
from lei_signal.plans.monitor import evaluate_plan
from lei_signal.plans.store import (
    append_revision,
    confirm_plan,
    create_plan,
    get_plan,
    list_action_items,
    list_plans,
    set_entered,
    transition_state,
    update_action_item,
)
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["plans"])


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _to_plan_dto(plan) -> PlanDTO:  # noqa: ANN001
    return PlanDTO(
        plan_id=plan.plan_id, symbol=plan.symbol, module=plan.module,
        direction=plan.direction, entry_rule_id=plan.entry_rule_id,
        entry_lifecycle_id=plan.entry_lifecycle_id, entry_trigger_cn=plan.entry_trigger_cn,
        entry_price_ref=plan.entry_price_ref, invalidation_price=plan.invalidation_price,
        target_b_price=plan.target_b_price, target_b_source=plan.target_b_source,
        reward_risk_at_plan=plan.reward_risk_at_plan, valid_until=plan.valid_until,
        state=plan.state, ruleset_version=plan.ruleset_version, reason=plan.reason,
        thesis_cn=plan.thesis_cn, invalidation_criteria_cn=plan.invalidation_criteria_cn,
        drawdown_playbook_cn=plan.drawdown_playbook_cn,
        take_profit_plan_cn=plan.take_profit_plan_cn, stop_plan_cn=plan.stop_plan_cn,
        entered_on=plan.entered_on, exited_on=plan.exited_on,
        exit_reason_rule_id=plan.exit_reason_rule_id, superseded_by=plan.superseded_by,
        created_at=plan.created_at, updated_at=plan.updated_at,
    )


def _to_alert_dto(a) -> PlanAlertDTO:  # noqa: ANN001
    return PlanAlertDTO(
        code=a.code, severity=a.severity, rule_id=a.rule_id, evidence=dict(a.evidence),
        principle_source=a.principle_source, logic_provenance=a.logic_provenance,
        caveat_cn=a.caveat_cn, actionable_from=a.actionable_from,
        data_as_of=a.data_as_of, next_step_cn=a.next_step_cn, action_kind=a.action_kind,
    )


def _to_action_dto(i) -> ActionItemDTO:  # noqa: ANN001
    return ActionItemDTO(
        action_id=i.action_id, plan_id=i.plan_id, kind=i.kind,
        source_alert_code=i.source_alert_code, state=i.state, due_from=i.due_from,
        nag_count=i.nag_count, last_nagged_bar_date=i.last_nagged_bar_date,
        resume_on=i.resume_on, closed_on=i.closed_on, close_kind=i.close_kind,
    )


@router.post("/plans", response_model=PlanDTO, status_code=201)
def post_plan(request: Request, body: CreatePlanRequest) -> PlanDTO:
    with closing(connect(_db_path(request))) as conn:
        plan = create_plan(
            conn, symbol=body.symbol, module=body.module, direction=body.direction,
            ruleset_version=body.ruleset_version, reason=body.reason,
            valid_until=body.valid_until, entry_rule_id=body.entry_rule_id,
            entry_lifecycle_id=body.entry_lifecycle_id, entry_trigger_cn=body.entry_trigger_cn,
            entry_price_ref=body.entry_price_ref, invalidation_price=body.invalidation_price,
            target_b_price=body.target_b_price, target_b_source=body.target_b_source,
            reward_risk_at_plan=body.reward_risk_at_plan, thesis_cn=body.thesis_cn,
            invalidation_criteria_cn=body.invalidation_criteria_cn,
            drawdown_playbook_cn=body.drawdown_playbook_cn,
            take_profit_plan_cn=body.take_profit_plan_cn, stop_plan_cn=body.stop_plan_cn,
        )
        return _to_plan_dto(plan)


@router.post("/plans/{plan_id}/confirm", response_model=PlanDTO)
def confirm(request: Request, plan_id: str) -> PlanDTO:
    with closing(connect(_db_path(request))) as conn:
        try:
            return _to_plan_dto(confirm_plan(conn, plan_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/plans", response_model=list[PlanDTO])
def list_plans_endpoint(
    request: Request, symbol: str | None = None, state: str | None = None
) -> list[PlanDTO]:
    with closing(connect(_db_path(request))) as conn:
        return [_to_plan_dto(p) for p in list_plans(conn, symbol=symbol, state=state)]


@router.get("/plans/{plan_id}", response_model=PlanDTO)
def get_plan_endpoint(request: Request, plan_id: str) -> PlanDTO:
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        return _to_plan_dto(plan)


@router.post("/plans/{plan_id}/revise")
def revise(request: Request, plan_id: str, body: RevisionRequest) -> dict:
    """追加修订。drift.check_revision 判定；within_playbook 才 apply_change。"""
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        old = getattr(plan, body.changed_field, None)
        changes: dict[str, object] = {body.changed_field: body.new_value}
        verdict = check_revision(plan, changes)
        append_revision(
            conn, plan_id, changed_field=body.changed_field,
            old_value=str(old) if old is not None else None,
            new_value=str(body.new_value) if body.new_value is not None else None,
            verdict=verdict.verdict,
            verdict_reason_cn=body.verdict_reason_cn or verdict.reason_cn,
            changed_by=body.changed_by,
            apply_change=(verdict.verdict == VERDICT_WITHIN_PLAYBOOK),
        )
        return {
            "verdict": verdict.verdict,
            "reason_cn": verdict.reason_cn,
            "plan": _to_plan_dto(get_plan(conn, plan_id)),
        }


@router.post("/plans/{plan_id}/enter", response_model=PlanDTO)
def enter_plan(request: Request, plan_id: str) -> PlanDTO:
    """armed -> entered，并顶替同标的同向既有计划（决策 5）。"""
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        entered = set_entered(conn, plan_id, entered_on=plan.valid_until)
        handle_supersede(conn, entered)
        return _to_plan_dto(get_plan(conn, plan_id))


@router.get("/plans/{plan_id}/alerts", response_model=list[PlanAlertDTO])
def plan_alerts(request: Request, plan_id: str) -> list[PlanAlertDTO]:
    """对计划标的取当日确定性 DTO，跑 evaluate_plan。"""
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    entry = service.get(plan.symbol)
    if entry.result is None:
        raise HTTPException(status_code=502, detail=entry.error or "分析不可用")
    ctx = context_from_result(entry.result)
    alerts = evaluate_plan(plan, ctx)
    return [_to_alert_dto(a) for a in alerts]


@router.get("/plans/{plan_id}/actions", response_model=list[ActionItemDTO])
def list_actions(request: Request, plan_id: str, state: str | None = None) -> list[ActionItemDTO]:
    with closing(connect(_db_path(request))) as conn:
        return [_to_action_dto(i) for i in list_action_items(conn, plan_id, state=state)]


@router.post("/plans/{plan_id}/actions/{action_id}/defer", response_model=ActionItemDTO)
def defer_action(
    request: Request, plan_id: str, action_id: str, body: DeferRequest
) -> ActionItemDTO:
    """推迟待办。必填 reason_cn + resume_on（决策 4c），resume_on 校验不过即 422。"""
    with closing(connect(_db_path(request))) as conn:
        # resume_on 校验需要当日 ctx：取计划标的的 DTO
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        service = getattr(request.app.state, "analysis_service", None)
        if service is not None:
            entry = service.get(plan.symbol)
            if entry.result is not None:
                ctx = context_from_result(entry.result)
                try:
                    validate_resume_on(body.resume_on, ctx)
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
        import json

        from lei_signal.plans.store import add_annotation
        item = update_action_item(
            conn, action_id, state="deferred",
            resume_on=json.dumps(body.resume_on, ensure_ascii=False),
            closed_on=None, close_kind=None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=f"待办不存在: {action_id}")
        add_annotation(
            conn, plan_id, ref_kind="action", ref_id=action_id,
            kind="defer_reason", reason_cn=body.reason_cn, author="user",
        )
        return _to_action_dto(item)


@router.post("/plans/{plan_id}/actions/{action_id}/done", response_model=ActionItemDTO)
def done_action(request: Request, plan_id: str, action_id: str) -> ActionItemDTO:
    with closing(connect(_db_path(request))) as conn:
        item = update_action_item(
            conn, action_id, state="done", closed_on=None, close_kind="done",
        )
        if item is None:
            raise HTTPException(status_code=404, detail=f"待办不存在: {action_id}")
        # ENTER done -> plan entered；EXIT done -> plan exited
        plan = get_plan(conn, plan_id)
        if plan is not None and item.kind == "ENTER" and plan.state == "armed":
            set_entered(conn, plan_id, entered_on=plan.valid_until)
            handle_supersede(conn, get_plan(conn, plan_id))  # type: ignore[arg-type]
        elif plan is not None and item.kind == "EXIT" and plan.state == "entered":
            transition_state(conn, plan_id, "exited")
        return _to_action_dto(item)
