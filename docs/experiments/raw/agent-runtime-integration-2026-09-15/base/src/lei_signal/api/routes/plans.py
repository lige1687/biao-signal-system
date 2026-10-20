"""计划台账 REST 路由（监督员 v1）。

CRUD + 触发判定 + 待办。判定权在 plans/ 判定层（Python），本路由只做编排与 DTO 映射。
不接 LLM；LLM 讲解由 skill 侧调 /alerts 后用 grounding.render_alerts 完成。
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    ActionItemDTO,
    ConformanceReportDTO,
    CreateHoldingWatchRequest,
    CreatePlanRequest,
    DeferRequest,
    DraftUpdateRequest,
    PlanAlertDTO,
    PlanDTO,
    PlansSummaryDTO,
    RevisionRequest,
)
from lei_signal.plans.actions import (
    handle_supersede,
    validate_resume_on,
)
from lei_signal.plans.conformance import evaluate_draft_conformance
from lei_signal.plans.context import context_from_result
from lei_signal.plans.drift import check_revision
from lei_signal.plans.models import PLAN_KIND_HOLDING_WATCH, VERDICT_WITHIN_PLAYBOOK
from lei_signal.plans.monitor import evaluate_plan
from lei_signal.plans.store import (
    append_revision,
    confirm_holding_watch,
    confirm_plan,
    count_open_action_items,
    create_plan,
    get_plan,
    list_action_items,
    list_plans,
    set_entered,
    set_exited,
    update_action_item,
    update_draft,
    validate_entry_confirm_fields,
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
        plan_kind=plan.plan_kind, take_profit_price=plan.take_profit_price,
        stop_price=plan.stop_price,
        watch_signal_rule_ids=list(plan.watch_signal_rule_ids),
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


def _draft_request_hash(body: CreatePlanRequest) -> str:
    """03B-R3 S6：草稿请求编号绑定的**完整业务内容摘要**——原会话/问题/
    对象/全部计划字段。任何字段或归属变化都会改变摘要（409）。产物由原
    问题决定（摘要已含问题号），不重复计入。"""
    import hashlib

    payload = {
        "source_session_id": body.source_session_id or "",
        "source_question_id": body.source_question_id,
        "symbol": body.symbol,
        "module": body.module, "direction": body.direction,
        "ruleset_version": body.ruleset_version, "reason": body.reason,
        "valid_until": body.valid_until,
        "entry_rule_id": body.entry_rule_id,
        "entry_lifecycle_id": body.entry_lifecycle_id,
        "entry_trigger_cn": body.entry_trigger_cn,
        "entry_price_ref": body.entry_price_ref,
        "invalidation_price": body.invalidation_price,
        "target_b_price": body.target_b_price,
        "target_b_source": body.target_b_source,
        "reward_risk_at_plan": body.reward_risk_at_plan,
        "thesis_cn": body.thesis_cn,
        "invalidation_criteria_cn": body.invalidation_criteria_cn,
        "drawdown_playbook_cn": body.drawdown_playbook_cn,
        "take_profit_plan_cn": body.take_profit_plan_cn,
        "stop_plan_cn": body.stop_plan_cn,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _verify_discussion_source(conn, body: CreatePlanRequest) -> tuple[dict, str | None]:
    """03B-R3 S5：保存前由**服务端**核对原问题归属与冻结依据——不信任客户端
    自报 source_refs。返回 (冻结 source_refs, artifact_id)。校验失败抛 ValueError
    （映射 409/422）。"""
    if not body.source_question_id:
        raise ValueError("REQ_SOURCE_INVALID:对话式保存必须携带原问题（source_question_id）")
    qrow = conn.execute(
        "SELECT session_id, meta_json FROM agent_messages "
        "WHERE message_id = ? AND role = 'user'",
        (body.source_question_id,)).fetchone()
    if qrow is None:
        raise ValueError(f"REQ_SOURCE_INVALID:原问题不存在（message_id="
                         f"{body.source_question_id}），不能凭空声称讨论来源")
    if body.source_session_id and body.source_session_id != qrow["session_id"]:
        raise ValueError(
            f"REQ_SOURCE_CONFLICT:原问题属于会话 {qrow['session_id']}，"
            f"与传入会话 {body.source_session_id} 不一致")
    try:
        snap = (json.loads(qrow["meta_json"] or "{}") or {}).get("discussion_v1") or {}
    except json.JSONDecodeError:
        snap = {}
    q_symbol = snap.get("symbol")
    if q_symbol and q_symbol != body.symbol:
        raise ValueError(
            f"REQ_SOURCE_CONFLICT:原问题绑定标的 {q_symbol}，草稿却是 "
            f"{body.symbol}；不能跨对象保存")
    # 服务端计划产物：优先取该问题**精确绑定**的回答上的产物（S5）
    artifact = None
    arow = conn.execute(
        "SELECT meta_json FROM agent_messages "
        "WHERE question_id = ? AND role = 'assistant' "
        "ORDER BY message_id DESC LIMIT 1", (body.source_question_id,)).fetchone()
    if arow is not None:
        try:
            artifact = (json.loads(arow["meta_json"] or "{}") or {}).get("plan_artifact")
        except json.JSONDecodeError:
            artifact = None
    if artifact is not None:
        if artifact.get("symbol") != body.symbol:
            raise ValueError(
                f"REQ_SOURCE_CONFLICT:服务端计划产物绑定标的 "
                f"{artifact.get('symbol')}，草稿却是 {body.symbol}")
        refs = {
            "artifact_id": artifact.get("artifact_id"),
            "ruleset": artifact.get("ruleset_ref"),
            "evidence_refs": artifact.get("evidence_refs") or [],
            "rule_refs": artifact.get("rule_refs") or [],
            "origin_symbol": body.symbol,
            "origin_question_id": body.source_question_id,
            "fields": artifact.get("fields") or {},
            "frozen_at": artifact.get("created_at"),
            "note_cn": "依据取自服务端计划产物冻结（不读今天的规则充当当时依据）",
        }
        return refs, artifact.get("artifact_id")
    # 旧记录/非整理计划类问题：无产物 → 依据取自**提问快照冻结**，如实标注
    refs = {
        "artifact_id": None,
        "ruleset": None,
        "evidence_refs": snap.get("evidence_refs") or [],
        "rule_refs": snap.get("rule_refs") or [],
        "origin_symbol": body.symbol,
        "origin_question_id": body.source_question_id,
        "fields": {},
        "note_cn": "该问题无服务端计划产物（非整理计划类问题或旧记录）；"
                   "依据取自提问快照冻结，来源可考",
    }
    return refs, None


@router.post("/plans", response_model=PlanDTO, status_code=201)
def post_plan(request: Request, body: CreatePlanRequest) -> PlanDTO:
    """建计划草稿。03B-R3 S5/S6：携带 client_request_id 的对话式保存——
    服务端核对原问题归属（不信任客户端 source_refs）并冻结产物依据；
    编号绑定完整业务摘要：同编号同内容返回原 draft，换任何字段/归属 409；
    草稿+绑定+编号同一事务，竞争失败不留孤立草稿。非讨论手动建草稿
    （无编号）原入口保留，不声称讨论来源。"""
    with closing(connect(_db_path(request))) as conn:
        if body.client_request_id:
            # S6：同编号先比完整业务摘要（比 plan_id 更严：内容变了即冲突）
            existing = conn.execute(
                "SELECT * FROM agent_plan_draft_bindings "
                "WHERE client_request_id = ?",
                (body.client_request_id,)).fetchone()
            if existing is not None:
                if existing["request_hash"] and existing["request_hash"] != \
                        _draft_request_hash(body):
                    raise HTTPException(status_code=409, detail={
                        "code": "DRAFT_REQUEST_CONFLICT",
                        "message": ("相同草稿编号已用于不同业务内容/归属"
                                    "（对象或任一计划字段不同）；请换编号"),
                    })
                plan = get_plan(conn, existing["plan_id"])
                if plan is not None:
                    return _to_plan_dto(plan)
            try:
                refs, artifact_id = _verify_discussion_source(conn, body)
            except ValueError as exc:
                msg = str(exc)
                code, _, detail = msg.partition(":")
                status = 409 if code == "REQ_SOURCE_CONFLICT" else 422
                raise HTTPException(status_code=status, detail={
                    "code": code, "message": detail or msg}) from exc
            request_hash = _draft_request_hash(body)
            conn.execute("BEGIN IMMEDIATE")
            try:
                # 事务内复查（并发同编号：只有一个能创建草稿+绑定）
                row2 = conn.execute(
                    "SELECT * FROM agent_plan_draft_bindings "
                    "WHERE client_request_id = ?",
                    (body.client_request_id,)).fetchone()
                if row2 is not None:
                    conn.rollback()
                    if row2["request_hash"] and row2["request_hash"] != request_hash:
                        raise HTTPException(status_code=409, detail={
                            "code": "DRAFT_REQUEST_CONFLICT",
                            "message": "相同草稿编号已用于不同业务内容/归属；请换编号",
                        })
                    plan = get_plan(conn, row2["plan_id"])
                    if plan is not None:
                        return _to_plan_dto(plan)
                refs.setdefault("ruleset", None)
                plan = create_plan(
                    conn, symbol=body.symbol, module=body.module,
                    direction=body.direction,
                    ruleset_version=body.ruleset_version, reason=body.reason,
                    valid_until=body.valid_until, entry_rule_id=body.entry_rule_id,
                    entry_lifecycle_id=body.entry_lifecycle_id,
                    entry_trigger_cn=body.entry_trigger_cn,
                    entry_price_ref=body.entry_price_ref,
                    invalidation_price=body.invalidation_price,
                    target_b_price=body.target_b_price,
                    target_b_source=body.target_b_source,
                    reward_risk_at_plan=body.reward_risk_at_plan,
                    thesis_cn=body.thesis_cn,
                    invalidation_criteria_cn=body.invalidation_criteria_cn,
                    drawdown_playbook_cn=body.drawdown_playbook_cn,
                    take_profit_plan_cn=body.take_profit_plan_cn,
                    stop_plan_cn=body.stop_plan_cn,
                    commit=False)
                from datetime import UTC, datetime

                refs["invalidation_price_origin"] = (
                    "suggested_plan" if artifact_id and
                    plan.invalidation_price is not None else
                    ("user_draft" if plan.invalidation_price is not None
                     else "missing"))
                conn.execute(
                    "INSERT INTO agent_plan_draft_bindings (client_request_id, "
                    "plan_id, session_id, question_id, symbol, source_refs_json, "
                    "request_hash, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (body.client_request_id, plan.plan_id,
                     body.source_session_id or qrow_session(conn, body), body.source_question_id,
                     plan.symbol,
                     json.dumps(refs, ensure_ascii=False),
                     request_hash, datetime.now(UTC).isoformat()))
                conn.commit()
            except HTTPException:
                raise
            except sqlite3.IntegrityError:
                conn.rollback()
                row3 = conn.execute(
                    "SELECT * FROM agent_plan_draft_bindings "
                    "WHERE client_request_id = ?",
                    (body.client_request_id,)).fetchone()
                if row3 is not None:
                    if row3["request_hash"] and row3["request_hash"] != request_hash:
                        raise HTTPException(status_code=409, detail={
                            "code": "DRAFT_REQUEST_CONFLICT",
                            "message": "相同草稿编号已用于不同业务内容/归属；请换编号",
                        }) from None
                    plan = get_plan(conn, row3["plan_id"])
                    if plan is not None:
                        return _to_plan_dto(plan)
                raise
            return _to_plan_dto(plan)
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


def qrow_session(conn, body) -> str | None:  # noqa: ANN001
    """服务端可靠反查原 session（工作台未传 source_session_id 时的兜底）。"""
    if body.source_question_id:
        row = conn.execute(
            "SELECT session_id FROM agent_messages WHERE message_id = ?",
            (body.source_question_id,)).fetchone()
        if row is not None:
            return row["session_id"]
    return body.source_session_id or ""


@router.post("/plans/holding-watch", response_model=PlanDTO, status_code=201)
def post_holding_watch(request: Request, body: CreateHoldingWatchRequest) -> PlanDTO:
    """建持仓盯盘 draft（不再一步 confirm）。

    确认统一走 ``POST /plans/{plan_id}/confirm``，过退出逻辑核对（方向合理性等）
    后再 draft->entered。校验（两项退出预案 + 至少一个触发条件）仍在
    ``store.confirm_holding_watch``。
    """
    with closing(connect(_db_path(request))) as conn:
        plan = create_plan(
            conn, symbol=body.symbol, module=body.module, direction=body.direction,
            ruleset_version=body.ruleset_version, reason=body.reason,
            valid_until=body.valid_until,
            take_profit_plan_cn=body.take_profit_plan_cn,
            stop_plan_cn=body.stop_plan_cn,
            plan_kind=PLAN_KIND_HOLDING_WATCH,
            take_profit_price=body.take_profit_price,
            stop_price=body.stop_price,
            watch_signal_rule_ids=body.watch_signal_rule_ids,
        )
        return _to_plan_dto(plan)


@router.get("/plans/{plan_id}/conformance", response_model=ConformanceReportDTO)
def plan_conformance(request: Request, plan_id: str) -> ConformanceReportDTO:
    """草稿符合性核对：硬阻断项 + 软建议项 + 系统检测对照。

    判定权在 Python（``evaluate_draft_conformance``），无 LLM、无新数值。
    """
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
    report = evaluate_draft_conformance(plan, ctx)
    return ConformanceReportDTO(
        can_confirm=report.can_confirm,
        hard_issues=[_to_alert_dto(a) for a in report.hard_issues],
        soft_issues=[_to_alert_dto(a) for a in report.soft_issues],
        system_detected=report.system_detected,
    )


@router.put("/plans/{plan_id}/draft", response_model=PlanDTO)
def update_draft_endpoint(
    request: Request, plan_id: str, body: DraftUpdateRequest
) -> PlanDTO:
    """编辑 draft 字段（仅 draft 态，无 drift）。未传字段不改，传 null 清空。"""
    updates = body.model_dump(exclude_unset=True)
    with closing(connect(_db_path(request))) as conn:
        try:
            plan = update_draft(conn, plan_id, updates)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return _to_plan_dto(plan)


@router.post("/plans/{plan_id}/confirm", response_model=PlanDTO)
def confirm(request: Request, plan_id: str) -> PlanDTO:
    """draft -> armed（entry）/ entered（holding_watch）。

    04B 确认边界（总控决定 2026-09-08，修复 p1：分析缺席时缺失效价计划被放行）：
    - 字段缺失/非法（技术 entry 缺失效价、价格 NaN/Inf/零/负）-> 422
      ``INVALIDATION_PRICE_REQUIRED``，先于分析依赖判断（store 层共享校验）；
    - 分析服务缺席/无结果/调用异常 -> 503 ``ANALYSIS_UNAVAILABLE``「暂时无法核实，
      请保留草稿后重试」——不再降级放行，state 与确认审计均不变；
    - 已过期 -> 409 ``PLAN_EXPIRED``；规则集版本不符 -> 409 ``RULESET_VERSION_CHANGED``
      （版本未知不拦，与监督员 hint 同口径）；符合性硬阻断维持 422（既有客户端
      ConfirmPlanError 约定），detail 一律带结构化 code。
    """
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        if plan.state != "draft":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "PLAN_NOT_DRAFT",
                    "message": f"只有 draft 可确认，当前 state={plan.state}",
                },
            )
        try:
            validate_entry_confirm_fields(plan)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALIDATION_PRICE_REQUIRED", "message": str(exc)},
            ) from exc
        today = datetime.now(UTC).date().isoformat()
        if plan.valid_until and plan.valid_until < today:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "PLAN_EXPIRED",
                    "message": (
                        f"计划有效期至 {plan.valid_until}，已过期；"
                        "请修改有效期或重建草稿后再确认"
                    ),
                },
            )

    # 分析依赖：缺席/无结果/异常一律 503，不允许跳过符合性检查继续确认
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ANALYSIS_UNAVAILABLE",
                "message": "暂时无法核实，请保留草稿后重试",
                "reason": "分析服务未就绪",
            },
        )
    try:
        entry = service.get(plan.symbol)
    except Exception as exc:  # noqa: BLE001 依赖故障是可重试状态，不是计划问题
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ANALYSIS_UNAVAILABLE",
                "message": "暂时无法核实，请保留草稿后重试",
                "reason": f"分析调用失败：{exc}",
            },
        ) from exc
    if entry is None or getattr(entry, "result", None) is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ANALYSIS_UNAVAILABLE",
                "message": "暂时无法核实，请保留草稿后重试",
                "reason": getattr(entry, "error", None) or "分析无结果",
            },
        )
    ctx = context_from_result(entry.result)
    if plan.ruleset_version and plan.ruleset_version != ctx.ruleset_version:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RULESET_VERSION_CHANGED",
                "message": (
                    f"计划基于规则集 {plan.ruleset_version}，当前为 "
                    f"{ctx.ruleset_version}；请复核后重建草稿"
                ),
            },
        )
    report = evaluate_draft_conformance(plan, ctx)
    if not report.can_confirm:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CONFORMANCE_HARD_BLOCK",
                "message": "存在硬阻断项，无法确认",
                "hard_issues": [
                    _to_alert_dto(a).model_dump() for a in report.hard_issues
                ],
            },
        )
    with closing(connect(_db_path(request))) as conn:
        try:
            if plan.plan_kind == PLAN_KIND_HOLDING_WATCH:
                entered_on = datetime.now(UTC).date().isoformat()
                confirmed = confirm_holding_watch(
                    conn, plan_id, entered_on=entered_on
                )
            else:
                confirmed = confirm_plan(conn, plan_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "PLAN_INVALID", "message": str(exc)},
            ) from exc
        return _to_plan_dto(confirmed)


@router.get("/plans/summary", response_model=PlansSummaryDTO)
def plans_summary(request: Request) -> PlansSummaryDTO:
    """顶栏红点：未处理待办数 + 活跃计划数 + 今日机会数 + 买卖信号合计。"""
    from lei_signal.api.opportunity_scan import (  # noqa: PLC0415
        count_opportunities,
        today_date,
    )
    from lei_signal.api.signal_alerts_store import count_sell_alerts  # noqa: PLC0415

    with closing(connect(_db_path(request))) as conn:
        open_actions = count_open_action_items(conn)
        active = list_plans(conn, state="armed") + list_plans(conn, state="entered")
        today_opps = count_opportunities(conn, today_date())
        today_sell = count_sell_alerts(conn, today_date())
    return PlansSummaryDTO(
        open_actions=open_actions,
        active_plans=len(active),
        today_opportunities=today_opps,
        today_signal_total=today_opps + today_sell,
    )


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
        entered = set_entered(
            conn, plan_id, entered_on=datetime.now(UTC).date().isoformat()
        )
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
        # 入场/退出日取该待办 due_from（系统判定的可执行日），两侧同源；缺 due_from
        # 时退回当日（仅日期，无数量金额）。
        plan = get_plan(conn, plan_id)
        executed_on = item.due_from or datetime.now(UTC).date().isoformat()
        if plan is not None and item.kind == "ENTER" and plan.state == "armed":
            set_entered(conn, plan_id, entered_on=executed_on)
            handle_supersede(conn, get_plan(conn, plan_id))  # type: ignore[arg-type]
        elif plan is not None and item.kind == "EXIT" and plan.state == "entered":
            set_exited(conn, plan_id, exited_on=executed_on)
        return _to_action_dto(item)
