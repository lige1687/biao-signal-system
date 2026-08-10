"""监督员 agent 表达层路由：接地问答（LLM 只表达，判定权在 Python）。

复用 /alerts 的确定性判定（evaluate_plan），把 alert 讲成人话或回答用户提问。
LLM 输出必须过 ``verify_grounding``（禁用词 + rule_id 白名单），失败降级
``render_alerts`` 模板。plans.py 明确「不接 LLM」，故本路由独立成文件。
"""
from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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
            ok, reason = verify_grounding(raw, rule_ids)
            if ok:
                reply = raw
                grounded = True
            else:
                logger.warning("计划 chat 接地校验未过，降级模板：%s", reason)

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
            ok, reason = verify_grounding(raw, allowed)
            if ok:
                reply = raw
                grounded = True
            else:
                logger.warning("买点 chat 接地校验未过，降级模板：%s", reason)

    if reply is None:
        # 降级：把 review 讲成结构化文本，不经过 LLM
        reply = _buy_point_template(review)
        grounded = False
    return BuyPointChatReply(
        reply=reply, grounded=grounded, symbol=symbol, review=review,
    )


def _buy_point_template(review) -> str:  # noqa: ANN001
    """review 降级模板：结构化直出，不经过 LLM。
    与 LLM 路径一致：每个候选只列依据/关键价/状态，止损和盈亏比在文末统一提示。

    recency 后: candidates 是近期独立候选, resonance_groups 是价位共振,
    historical_structures 是过期结构 (不展开)。
    """
    lines = [
        f"【买点审阅】{review.display_name} · {review.verdict_cn}",
        f"数据日：{review.as_of}（收盘 {review.last_close or '-'}）",
        review.summary_cn,
    ]
    if review.tradability and not review.tradability.tradable:
        reasons = "、".join(review.tradability.blocking_reasons) or "见门禁明细"
        lines.append(f"阻断：{reasons}（规格 §13）")
    # 1. 共振组 (合并展示, 避免重复)
    for g in review.resonance_groups:
        n_rules = len(g.rule_ids)
        rules_str = " / ".join(g.rule_ids)
        lines.append(
            f"\n· 共振买点（{n_rules} 个 rule 共识）"
            f" 价位 {g.level:.2f}（±{g.tolerance_pct*100:.1f}% 内）"
        )
        lines.append(f"  rule_ids: {rules_str}")
        for c in g.candidates:
            lines.append(
                f"  - {c.scenario_cn} [{c.state_cn}] rule_id:{c.rule_id or '-'}"
                f" 关键价 {c.key_price or '-'}"
            )
    # 2. 独立近期候选 (recency 过滤后, weakened 已静默丢弃, 无需再筛)
    for i, c in enumerate(review.candidates, start=1):
        circled = "①②③④⑤⑥⑦⑧⑨⑩"[i - 1] if i <= 10 else str(i)
        lines.append(
            f"\n· 买点{circled} {c.scenario_cn} [{c.state_cn}] "
            f"rule_id:{c.rule_id or '-'}"
        )
        lines.append(f"  关键价：{c.key_price or '系统未给出'}")
        if c.satisfied_conditions:
            lines.append(f"  已满足：{'；'.join(c.satisfied_conditions)}")
        if c.missing_conditions:
            lines.append(f"  还缺：{'；'.join(c.missing_conditions)}")
        if c.next_step_cn:
            lines.append(f"  触发：{c.next_step_cn}")
        lines.append("  判定方式为研究代理")
    # 3. 历史结构 (一笔带过, 不展开)
    if review.historical_structures:
        n = len(review.historical_structures)
        rules = sorted({h.rule_id for h in review.historical_structures if h.rule_id})
        rules_str = "、".join(rules) if rules else "-"
        lines.append(
            f"\n另有 {n} 个历史结构（{rules_str} 等）已超出 recency 窗口，"
            f"在审阅卡片底部单列, 不构成当下买点。"
        )
    if review.watch_conditions:
        lines.append("\n【到什么情况才算买点】")
        for w in review.watch_conditions:
            if w.kind == "price":
                lines.append(f"· {w.text_cn}（价位 {w.price}）")
            else:
                lines.append(f"· {w.text_cn}（状态型条件）")
    # 止损 / 盈亏比 / 落计划 一句话收尾
    lines.append(
        "\n止损价与盈亏比在落计划时再确认（需用户给认错位 + 目标位，"
        "系统不算 R/R）。五项交易假设必须由人写。"
    )
    if review.suggested_plan:
        sp = review.suggested_plan
        lines.append(
            f"可落计划预填：模块{sp.module} · {sp.direction} · "
            f"entry_rule_id:{sp.entry_rule_id}"
        )
    lines.append(f"\n{review.disclaimer_cn}")
    return "\n".join(lines)


__all__ = ["router"]
