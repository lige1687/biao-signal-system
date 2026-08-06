"""监督员 agent 表达层路由：接地问答（LLM 只表达，判定权在 Python）。

复用 /alerts 的确定性判定（evaluate_plan），把 alert 讲成人话或回答用户提问。
LLM 输出必须过 ``verify_grounding``（禁用词 + rule_id 白名单），失败降级
``render_alerts`` 模板。plans.py 明确「不接 LLM」，故本路由独立成文件。
"""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.routes.plans import _to_alert_dto
from lei_signal.api.schemas import (
    BuyPointChatReply,
    BuyPointChatRequest,
    PlanChatReply,
    PlanChatRequest,
)
from lei_signal.plans.context import context_from_result
from lei_signal.plans.grounding import render_alerts, verify_grounding
from lei_signal.plans.llm import (
    build_context_payload,
    chat_ark,
    chat_buy_point,
    load_ark_config,
)
from lei_signal.plans.monitor import evaluate_plan
from lei_signal.plans.store import get_plan, list_action_items
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["agent"])

#: message 为空时的默认概括指令（走 SYSTEM_PROMPT 既定输出格式）。
_DEFAULT_SUMMARY_PROMPT = "请按输出格式概括当前监督结果与待办。"


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


@router.post("/plans/{plan_id}/chat", response_model=PlanChatReply)
def plan_chat(request: Request, plan_id: str, body: PlanChatRequest) -> PlanChatReply:
    """对计划提问。message 空 -> 当前 alert 接地摘要；非空 -> 接地问答。

    LLM 不可用或输出未过 grounding -> 降级模板（grounded=False）。
    """
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        action_items = list_action_items(conn, plan_id, state="open")

    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    entry = service.get(plan.symbol)
    if entry.result is None:
        raise HTTPException(status_code=502, detail=entry.error or "分析不可用")

    ctx = context_from_result(entry.result)
    alerts = evaluate_plan(plan, ctx)
    alert_dtos = [_to_alert_dto(a) for a in alerts]
    rule_ids = {a.rule_id for a in alerts if a.rule_id}

    config = load_ark_config()
    reply: str | None = None
    grounded = False
    if config is not None:
        payload = build_context_payload(
            alerts, plan=plan, action_items=action_items, context_min=None,
        )
        message = body.message.strip() or _DEFAULT_SUMMARY_PROMPT
        raw = chat_ark(payload, message, config)
        if raw is not None:
            ok, _ = verify_grounding(raw, rule_ids)
            if ok:
                reply = raw
                grounded = True

    if reply is None:
        # 降级：判定层模板直出，不经过 LLM
        reply = render_alerts(alerts, plan=plan, action_items=action_items)
        grounded = False
    return PlanChatReply(
        reply=reply, grounded=grounded, plan_id=plan_id, alerts=alert_dtos,
    )


_BP_DEFAULT_PROMPT = "请概括当前买点审阅：是否构成系统定义的买点、图什么信号、止损与盈亏比。"


@router.post("/symbols/{symbol}/buy-point-chat", response_model=BuyPointChatReply)
def buy_point_chat(
    request: Request, symbol: str, body: BuyPointChatRequest
) -> BuyPointChatReply:
    """就买点审阅提问。LLM 只讲解 review 的确定性字段，不自行判断买点。

    输出过 verify_grounding（禁用词 + rule_id 白名单 = review 内出现的 rule_id），
    失败降级为 review 结构化文本直出（grounded=False）。
    """
    from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
        buy_point_review,
    )

    review = buy_point_review(request, symbol)
    review_dict = review.model_dump()
    rule_ids = {c.rule_id for c in review.candidates if c.rule_id}
    if (
        review.suggested_plan
        and review.suggested_plan.entry_rule_id
    ):
        rule_ids.add(review.suggested_plan.entry_rule_id)
    # 确保白名单非空时才校验；空时 verify_grounding 仍查禁用词
    allowed = rule_ids or {""}

    config = load_ark_config()
    reply: str | None = None
    grounded = False
    if config is not None:
        message = body.message.strip() or _BP_DEFAULT_PROMPT
        raw = chat_buy_point(review_dict, message, config)
        if raw is not None:
            ok, _ = verify_grounding(raw, allowed)
            if ok:
                reply = raw
                grounded = True

    if reply is None:
        # 降级：把 review 讲成结构化文本，不经过 LLM
        reply = _buy_point_template(review)
        grounded = False
    return BuyPointChatReply(
        reply=reply, grounded=grounded, symbol=symbol, review=review,
    )


def _buy_point_template(review) -> str:  # noqa: ANN001
    """review 降级模板：结构化直出，不经过 LLM。"""
    lines = [
        f"【买点审阅】{review.display_name} · {review.verdict_cn}",
        f"数据日：{review.as_of}（收盘 {review.last_close or '-'}）",
        review.summary_cn,
    ]
    if review.tradability and not review.tradability.tradable:
        reasons = "、".join(review.tradability.blocking_reasons) or "见门禁明细"
        lines.append(f"阻断：{reasons}（规格 §13）")
    for c in review.candidates:
        lines.append(f"\n· {c.scenario_cn} [{c.state_cn}] rule_id:{c.rule_id or '-'}")
        if c.satisfied_conditions:
            lines.append(f"  已满足：{'；'.join(c.satisfied_conditions)}")
        if c.missing_conditions:
            lines.append(f"  还缺：{'；'.join(c.missing_conditions)}")
        stop = c.invalidation_price or "（系统未给出，建计划时人工确认）"
        lines.append(f"  关键价 {c.key_price or '-'} · 止损 {stop}")
        if c.reward_risk_computable:
            lines.append(f"  盈亏比 {c.reward_risk_ratio}（目标 {c.reward_risk_target}）")
        else:
            lines.append("  盈亏比目标不可计算")
        lines.append("  判定方式为研究代理")
    if review.watch_conditions:
        lines.append("\n【到什么情况才算买点】")
        for w in review.watch_conditions:
            if w.kind == "price":
                lines.append(f"· {w.text_cn}（价位 {w.price}）")
            else:
                lines.append(f"· {w.text_cn}（状态型条件，无单一价位）")
    if review.suggested_plan:
        sp = review.suggested_plan
        lines.append(
            f"\n【可落计划预填】模块{sp.module} · {sp.direction} · "
            f"entry_rule_id:{sp.entry_rule_id}"
        )
    lines.append(f"\n{review.disclaimer_cn}")
    return "\n".join(lines)


__all__ = ["router"]
