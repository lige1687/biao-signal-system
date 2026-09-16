"""草稿符合性判定：提交后、确认前，核对计划逻辑是否符合 LEI 体系。

与 ``monitor.evaluate_plan``（给活跃计划产 alert）不同，本模块针对 **draft** 计划，
回答「这条计划能不能按系统规则确认生效」。硬规则不达标 -> ``can_confirm=False``，
``confirm`` 端点据此 422。判定权在 Python，无 LLM，无新规则，只组合既有 DTO 字段
+ §13/§14 原则 + ``module_of``。

红线：不算 DTO 之外的新数值；§13/§14 相关 issue 两层标注（原文出处 + research_proxy）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lei_signal.domain.rules_config import get_rule
from lei_signal.plans.models import (
    PLAN_KIND_HOLDING_WATCH,
    SEVERITY_BLOCK,
    SEVERITY_HINT,
    PlanAlert,
    TradePlan,
)
from lei_signal.plans.monitor import (
    IMPLEMENTED_MODULES,
    PLAN_DISCIPLINE_RULE,
    RR_RULE,
    TRADABILITY_RULE,
    MonitorContext,
)
from lei_signal.research.module_backtest import module_of

# 硬阻断 issue codes（can_confirm=False）
MODULE_NOT_IMPLEMENTED = "MODULE_NOT_IMPLEMENTED"
ENTRY_BLOCKED_BY_TRADABILITY = "ENTRY_BLOCKED_BY_TRADABILITY"
MISSING_INVALIDATION = "MISSING_INVALIDATION"
INVALIDATION_ALREADY_BREACHED = "INVALIDATION_ALREADY_BREACHED"
MODULE_RULE_MISMATCH = "MODULE_RULE_MISMATCH"
ENTRY_RULE_NOT_ENTRY_MODULE = "ENTRY_RULE_NOT_ENTRY_MODULE"
DIRECTION_MISMATCH = "DIRECTION_MISMATCH"
TP_SL_DIRECTION_INSANE = "TP_SL_DIRECTION_INSANE"
MISSING_EXIT_TRIGGER = "MISSING_EXIT_TRIGGER"

# 软建议 issue codes（不阻断确认）
RR_BELOW_IDEAL = "RR_BELOW_IDEAL"
RR_NOT_COMPUTABLE = "RR_NOT_COMPUTABLE"
MODULE_SCENARIO_MISMATCH = "MODULE_SCENARIO_MISMATCH"
PLAN_ORPHANED = "PLAN_ORPHANED"
ENTRY_RULE_MISSING = "ENTRY_RULE_MISSING"
WATCH_SIGNAL_NOT_HIT = "WATCH_SIGNAL_NOT_HIT"


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """草稿符合性核对结果。``can_confirm`` = 无硬项。"""

    can_confirm: bool
    hard_issues: list[PlanAlert] = field(default_factory=list)
    soft_issues: list[PlanAlert] = field(default_factory=list)
    system_detected: dict[str, Any] = field(default_factory=dict)


def evaluate_draft_conformance(
    plan: TradePlan, ctx: MonitorContext
) -> ConformanceReport:
    """核对 draft 计划能否确认。按 ``plan_kind`` 分支：entry 核入场逻辑，
    holding_watch 核退出逻辑。无 IO，幂等。"""
    hard: list[PlanAlert] = []
    soft: list[PlanAlert] = []
    if plan.plan_kind == PLAN_KIND_HOLDING_WATCH:
        _holding_watch_issues(plan, ctx, hard, soft)
    else:
        _entry_issues(plan, ctx, hard, soft)
    return ConformanceReport(
        can_confirm=not hard,
        hard_issues=hard,
        soft_issues=soft,
        system_detected=_system_detected(plan, ctx),
    )


def _issue(
    *,
    code: str,
    severity: str,
    rule_id: str | None,
    ctx: MonitorContext,
    evidence: dict[str, Any],
    principle_source: str | None = None,
    caveat_cn: str = "",
    next_step_cn: str = "",
) -> PlanAlert:
    return PlanAlert(
        code=code, severity=severity, rule_id=rule_id, evidence=evidence,
        principle_source=principle_source, logic_provenance="research_proxy",
        caveat_cn=caveat_cn, actionable_from="", data_as_of=ctx.last_bar_date,
        next_step_cn=next_step_cn, action_kind=None,
    )


def _find_opportunity(plan: TradePlan, ctx: MonitorContext):
    """按 lifecycle_id（忽略方向，用于检测方向冲突）再按 rule_id 找匹配机会。"""
    if plan.entry_lifecycle_id:
        m = next(
            (o for o in ctx.opportunities
             if o.lifecycle_id == plan.entry_lifecycle_id),
            None,
        )
        if m is not None:
            return m
    if plan.entry_rule_id:
        return next(
            (o for o in ctx.opportunities if o.rule_id == plan.entry_rule_id),
            None,
        )
    return None


def _entry_issues(
    plan: TradePlan, ctx: MonitorContext,
    hard: list[PlanAlert], soft: list[PlanAlert],
) -> None:
    is_long = plan.direction == "long"

    # --- 硬阻断 ---
    if plan.module not in IMPLEMENTED_MODULES:
        hard.append(_issue(
            code=MODULE_NOT_IMPLEMENTED, severity=SEVERITY_BLOCK,
            rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, evidence={"module": plan.module},
            next_step_cn=(
                f"模块 {plan.module or '(空)'} 不在已实现模块 A/B/C/D 中，无法监督"
            ),
        ))
    if not ctx.tradability_tradable:
        hard.append(_issue(
            code=ENTRY_BLOCKED_BY_TRADABILITY, severity=SEVERITY_BLOCK,
            rule_id=TRADABILITY_RULE, ctx=ctx,
            evidence={"blocking_reasons": list(ctx.tradability_blocking_reasons)},
            principle_source="规格 §13 原文",
            caveat_cn="规格§13无交易条件；可交易性判定为研究代理",
            next_step_cn="环境阻断，按规则不该开新仓",
        ))
    if plan.invalidation_price is None:
        hard.append(_issue(
            code=MISSING_INVALIDATION, severity=SEVERITY_BLOCK,
            rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, evidence={},
            principle_source="规格 §13 第 3 条 原文",
            next_step_cn="未填失效价（§13第3条：入场依据/失效位必须入场前定义）",
        ))
    elif ctx.current_close is not None:
        # 新仓判定比 monitor 更严：当前价已到/越过失效价即不该开仓（含 ==）。
        breached = (
            ctx.current_close <= plan.invalidation_price if is_long
            else ctx.current_close >= plan.invalidation_price
        )
        if breached:
            hard.append(_issue(
                code=INVALIDATION_ALREADY_BREACHED, severity=SEVERITY_BLOCK,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                evidence={"close": ctx.current_close,
                          "invalidation_price": plan.invalidation_price,
                          "direction": plan.direction},
                principle_source="规格 §14 原文",
                caveat_cn="原则出自规格§14；击穿判定为研究代理",
                next_step_cn="失效价已被当前价击穿，不该再开此仓",
            ))

    # 入场 rule_id 与模块一致性
    if plan.entry_rule_id:
        sys_module = module_of(plan.entry_rule_id)
        if sys_module is None:
            # rule_id 未映射到 A/B/C/D：疑似把确认信号（LL/AL）当入场触发
            hard.append(_issue(
                code=ENTRY_RULE_NOT_ENTRY_MODULE, severity=SEVERITY_BLOCK,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                evidence={"entry_rule_id": plan.entry_rule_id},
                next_step_cn=(
                    f"入场规则 {plan.entry_rule_id} 未映射到 A/B/C/D 模块，"
                    "疑似把确认信号当入场触发"
                ),
            ))
        elif plan.module and sys_module != plan.module:
            hard.append(_issue(
                code=MODULE_RULE_MISMATCH, severity=SEVERITY_BLOCK,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                evidence={"plan_module": plan.module, "rule_module": sys_module,
                          "entry_rule_id": plan.entry_rule_id},
                next_step_cn=(
                    f"你选模块 {plan.module}，但入场规则 {plan.entry_rule_id} "
                    f"属于模块 {sys_module}，结构不一致"
                ),
            ))
    else:
        soft.append(_issue(
            code=ENTRY_RULE_MISSING, severity=SEVERITY_HINT,
            rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, evidence={},
            next_step_cn="未填入场信号 rule_id，系统无法核对入场逻辑，建议补上",
        ))

    # 方向冲突（红线4）
    opp = _find_opportunity(plan, ctx)
    if opp is not None and opp.direction != plan.direction:
        hard.append(_issue(
            code=DIRECTION_MISMATCH, severity=SEVERITY_BLOCK,
            rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
            evidence={"plan_direction": plan.direction, "opp_direction": opp.direction,
                      "lifecycle_id": opp.lifecycle_id},
            next_step_cn=(
                f"计划方向 {plan.direction} 与系统机会方向 {opp.direction} "
                "不一致（红线4：方向不得混算）"
            ),
        ))

    # --- 软建议 ---
    if plan.entry_lifecycle_id and opp is None:
        soft.append(_issue(
            code=PLAN_ORPHANED, severity=SEVERITY_HINT,
            rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
            evidence={"entry_lifecycle_id": plan.entry_lifecycle_id},
            next_step_cn="入场生命周期当日不在系统机会里，建议复核是否仍适用",
        ))

    rr_min = float(get_rule(RR_RULE).param("rr_min_ideal", 3))
    if plan.reward_risk_at_plan is None:
        soft.append(_issue(
            code=RR_NOT_COMPUTABLE, severity=SEVERITY_HINT,
            rule_id=RR_RULE, ctx=ctx, evidence={},
            principle_source="规格 §13 第 4 条 原文",
            caveat_cn="规格§13第4条列为无交易条件；人类2026-08-04定只提示不拦截",
            next_step_cn="盈亏比未填/不可计算，仅提示",
        ))
    elif plan.reward_risk_at_plan < rr_min:
        soft.append(_issue(
            code=RR_BELOW_IDEAL, severity=SEVERITY_HINT,
            rule_id=RR_RULE, ctx=ctx,
            evidence={"reward_risk_at_plan": plan.reward_risk_at_plan,
                      "rr_min_ideal": rr_min},
            principle_source="规格 §13 第 4 条 原文",
            caveat_cn="规格§13第4条列为无交易条件；人类2026-08-04定只提示不拦截，2-3可接受",
            next_step_cn=f"R/R={plan.reward_risk_at_plan:.2f}<{rr_min:g}，仅提示不拦截",
        ))

    # 你选的模块 vs 系统检测到的主力场景模块
    confirmed = [o for o in ctx.opportunities
                 if o.state == "confirmed" and o.rule_id]
    if confirmed:
        best = max(confirmed, key=lambda o: o.reward_risk_ratio or 0.0)
        best_mod = module_of(best.rule_id or "")
        if best_mod and plan.module and best_mod != plan.module:
            soft.append(_issue(
                code=MODULE_SCENARIO_MISMATCH, severity=SEVERITY_HINT,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                evidence={"plan_module": plan.module, "system_module": best_mod,
                          "system_rule_id": best.rule_id},
                next_step_cn=(
                    f"系统检测到的主力场景属模块 {best_mod}，你选 {plan.module}；"
                    f"若有理可忽略，否则建议改 {best_mod}"
                ),
            ))


def _holding_watch_issues(
    plan: TradePlan, ctx: MonitorContext,
    hard: list[PlanAlert], soft: list[PlanAlert],
) -> None:
    is_long = plan.direction == "long"
    close = ctx.current_close

    # 至少一个退出触发（confirm_holding_watch 已校验，提前暴露）
    if (
        plan.take_profit_price is None
        and plan.stop_price is None
        and not plan.watch_signal_rule_ids
    ):
        hard.append(_issue(
            code=MISSING_EXIT_TRIGGER, severity=SEVERITY_BLOCK,
            rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, evidence={},
            next_step_cn="持仓盯盘至少需要一个退出触发：止盈价 / 止损价 / 信号 rule_id",
        ))

    # 止盈止损方向合理性：long 止盈应在上方、止损在下方；short 反向
    if close is not None:
        if plan.take_profit_price is not None:
            tp_wrong = (
                plan.take_profit_price <= close if is_long
                else plan.take_profit_price >= close
            )
            if tp_wrong:
                hard.append(_issue(
                    code=TP_SL_DIRECTION_INSANE, severity=SEVERITY_BLOCK,
                    rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                    evidence={"take_profit_price": plan.take_profit_price,
                              "close": close, "direction": plan.direction},
                    next_step_cn=(
                        f"{'做多' if is_long else '做空'}止盈价不在当前价的"
                        f"{'上方' if is_long else '下方'}，价位或方向可能有误"
                    ),
                ))
        if plan.stop_price is not None:
            stop_wrong = (
                plan.stop_price >= close if is_long
                else plan.stop_price <= close
            )
            if stop_wrong:
                hard.append(_issue(
                    code=TP_SL_DIRECTION_INSANE, severity=SEVERITY_BLOCK,
                    rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                    evidence={"stop_price": plan.stop_price,
                              "close": close, "direction": plan.direction},
                    next_step_cn=(
                        f"{'做多' if is_long else '做空'}止损价不在当前价的"
                        f"{'下方' if is_long else '上方'}，价位或方向可能有误"
                    ),
                ))

    # 盯盘信号当日未命中（正常，仅提示）
    if plan.watch_signal_rule_ids:
        hit = [r for r in plan.watch_signal_rule_ids if r in ctx.new_event_rule_ids]
        if not hit:
            soft.append(_issue(
                code=WATCH_SIGNAL_NOT_HIT, severity=SEVERITY_HINT,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx,
                evidence={"watch_signal_rule_ids": list(plan.watch_signal_rule_ids)},
                next_step_cn="盯盘信号当日未命中（正常，仅提示）",
            ))


def _system_detected(plan: TradePlan, ctx: MonitorContext) -> dict[str, Any]:
    opp = _find_opportunity(plan, ctx)
    confirmed = [o for o in ctx.opportunities
                 if o.state == "confirmed" and o.rule_id]
    return {
        "module": module_of(plan.entry_rule_id) if plan.entry_rule_id else None,
        "direction": opp.direction if opp is not None else None,
        "scenarios": [
            {"rule_id": o.rule_id,
             "module": module_of(o.rule_id or ""),
             "direction": o.direction,
             "state": o.state}
            for o in confirmed
        ],
    }


__all__ = [
    "ConformanceReport",
    "DIRECTION_MISMATCH",
    "ENTRY_BLOCKED_BY_TRADABILITY",
    "ENTRY_RULE_MISSING",
    "ENTRY_RULE_NOT_ENTRY_MODULE",
    "INVALIDATION_ALREADY_BREACHED",
    "MISSING_EXIT_TRIGGER",
    "MISSING_INVALIDATION",
    "MODULE_NOT_IMPLEMENTED",
    "MODULE_RULE_MISMATCH",
    "MODULE_SCENARIO_MISMATCH",
    "PLAN_ORPHANED",
    "RR_BELOW_IDEAL",
    "RR_NOT_COMPUTABLE",
    "TP_SL_DIRECTION_INSANE",
    "WATCH_SIGNAL_NOT_HIT",
    "evaluate_draft_conformance",
]
