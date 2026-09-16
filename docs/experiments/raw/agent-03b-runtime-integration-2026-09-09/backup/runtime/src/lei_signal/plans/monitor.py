"""监督判定（纯函数，无 IO 无 LLM）。

``evaluate_plan(plan, ctx) -> list[PlanAlert]``：给定计划与当日确定性上下文，
产出带 ``rule_id`` 溯源的 alert 列表。判定权完全在 Python，LLM 不参与。

红线 1：``actionable_from`` = ``next_trading_day(last_bar_date)``，由代码算。
红线 2：§14/§13 相关 alert 两层标注（原文出处 + research_proxy + caveat）。
红线 3：阈值走 ``get_rule``，源码无裸数值。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, TradingCalendar
from lei_signal.domain.rules_config import get_rule
from lei_signal.plans.models import (
    PLAN_KIND_HOLDING_WATCH,
    SEVERITY_BLOCK,
    SEVERITY_HINT,
    SEVERITY_REMIND,
    PlanAlert,
    TradePlan,
)
from lei_signal.research.module_backtest import MODULE_MAP

#: 已实现交易模块集合，由 module_backtest.MODULE_MAP 派生（单一来源）。
#: 新增模块只需在 MODULE_MAP 登记，监督员对它的 MODULE_NOT_IMPLEMENTED 自动消失。
IMPLEMENTED_MODULES: frozenset[str] = frozenset(
    module for module, *_ in MODULE_MAP.values()
)

# alert codes
ENTRY_CONDITIONS_MET = "ENTRY_CONDITIONS_MET"
ENTRY_BLOCKED_BY_TRADABILITY = "ENTRY_BLOCKED_BY_TRADABILITY"
ENTRY_RR_BELOW_IDEAL = "ENTRY_RR_BELOW_IDEAL"
ENTRY_RR_NOT_COMPUTABLE = "ENTRY_RR_NOT_COMPUTABLE"
ENTRY_CONDITIONS_LOST = "ENTRY_CONDITIONS_LOST"
INVALIDATION_BREACHED = "INVALIDATION_BREACHED"
EXIT_TRIGGERED = "EXIT_TRIGGERED"
TAKE_PROFIT_REACHED = "TAKE_PROFIT_REACHED"
STOP_PRICE_BREACHED = "STOP_PRICE_BREACHED"
TAKE_PROFIT_APPROACHING = "TAKE_PROFIT_APPROACHING"
STOP_PRICE_APPROACHING = "STOP_PRICE_APPROACHING"
SIGNAL_WATCH_TRIGGERED = "SIGNAL_WATCH_TRIGGERED"
PLAN_EXPIRING = "PLAN_EXPIRING"
PLAN_STALE_RULESET = "PLAN_STALE_RULESET"
PLAN_ORPHANED = "PLAN_ORPHANED"
MODULE_NOT_IMPLEMENTED = "MODULE_NOT_IMPLEMENTED"
DATA_STALE = "DATA_STALE"

PLAN_DISCIPLINE_RULE = "plan_discipline_guard"
TRADABILITY_RULE = "tradability_gate"
RR_RULE = "reward_risk_filter"
HOLDING_WATCH_RULE = "holding_watch_guard"

#: resume_on 可引用的点路径（决策 4c）：超出此集合的路径 evaluate_resume 拒绝
RESOLVABLE_PATHS = ("close", "ema20", "tradability.tradable")

ACTIVE_STATES = ("armed", "entered")


@dataclass(frozen=True, slots=True)
class OpportunityRef:
    """计划入场条件在当日 DTO 中的投影。

    ``direction`` 为该机会自身的方向（long/short）。计划只能匹配同方向的机会--
    做多计划不得拿一条空头场景当入场条件（红线 4：方向/模块不得混算）。
    """

    lifecycle_id: str
    current_conditions_confirmed: bool
    state: str                          # watch/confirmed/weakened/invalidated
    rule_id: str | None
    reward_risk_ratio: float | None
    reward_risk_computable: bool
    direction: str = "long"             # long/short；缺省按做多


@dataclass(frozen=True, slots=True)
class ExitSignalRef:
    rule_id: str
    state: str                          # active/inactive


@dataclass(frozen=True, slots=True)
class MonitorContext:
    """evaluate_plan 的只读上下文（从 SymbolDetailDTO 裁剪而来）。"""

    last_bar_date: str                  # ISO 日期 = data_as_of
    cache_fallback_used: bool
    current_close: float | None
    ema20: float | None
    tradability_tradable: bool
    atr: float | None = None            # atr14，用于接近预警（None 则跳过）
    tradability_blocking_reasons: tuple[str, ...] = ()
    ruleset_version: str = ""
    opportunities: tuple[OpportunityRef, ...] = ()
    exit_signals: tuple[ExitSignalRef, ...] = ()
    new_event_rule_ids: tuple[str, ...] = ()


def _rule_provenance(rule_id: str | None) -> str:
    if rule_id is None:
        return "research_proxy"
    try:
        return get_rule(rule_id).provenance.value
    except KeyError:
        return "research_proxy"


def _alert(
    *,
    code: str,
    severity: str,
    rule_id: str | None,
    ctx: MonitorContext,
    actionable_from: str,
    evidence: dict[str, Any],
    principle_source: str | None = None,
    caveat_cn: str = "",
    action_kind: str | None = None,
    next_step_cn: str = "",
) -> PlanAlert:
    logic_provenance = (
        _rule_provenance(rule_id) if principle_source is None else "research_proxy"
    )
    return PlanAlert(
        code=code,
        severity=severity,
        rule_id=rule_id,
        evidence=evidence,
        principle_source=principle_source,
        logic_provenance=logic_provenance,
        caveat_cn=caveat_cn,
        actionable_from=actionable_from,
        data_as_of=ctx.last_bar_date,
        next_step_cn=next_step_cn,
        action_kind=action_kind,
    )


def _entry_rule_id(plan: TradePlan) -> str:
    if plan.entry_rule_id:
        try:
            get_rule(plan.entry_rule_id)
            return plan.entry_rule_id
        except KeyError:
            pass
    return PLAN_DISCIPLINE_RULE


def evaluate_plan(
    plan: TradePlan,
    ctx: MonitorContext,
    *,
    calendar: TradingCalendar = DEFAULT_TRADING_CALENDAR,
) -> list[PlanAlert]:
    """给定计划与当日上下文，产出 alert 列表。无 IO，幂等。"""
    actionable_from = calendar.next_trading_day(ctx.last_bar_date).date().isoformat()
    alerts: list[PlanAlert] = []
    active = plan.state in ACTIVE_STATES
    # 持仓盯盘：已在场内，只监督退出。入场类判定（可交易性阻断/入场条件/R-R/
    # lifecycle 孤儿/模块未实现）一律不适用--它们讲的是「该不该开新仓」。
    holding_watch = plan.plan_kind == PLAN_KIND_HOLDING_WATCH

    # DATA_STALE（陈旧数据不递增催办，但仍标注）
    if ctx.cache_fallback_used:
        alerts.append(_alert(
            code=DATA_STALE, severity=SEVERITY_HINT, rule_id=PLAN_DISCIPLINE_RULE,
            ctx=ctx, actionable_from=actionable_from,
            evidence={"cache_fallback_used": True, "last_bar_date": ctx.last_bar_date},
            caveat_cn="数据陈旧，所有 alert 仅供参考，不递增催办计数",
            next_step_cn="等待行情数据更新后再决策",
        ))

    # 计划级 meta alert（armed/entered 都适用）
    if active:
        if not holding_watch and plan.module not in IMPLEMENTED_MODULES:
            alerts.append(_alert(
                code=MODULE_NOT_IMPLEMENTED, severity=SEVERITY_HINT,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"module": plan.module},
                next_step_cn=f"模块 {plan.module} 规则未实现，无法监督",
            ))
        if (
            plan.ruleset_version
            and ctx.ruleset_version
            and plan.ruleset_version != ctx.ruleset_version
        ):
            alerts.append(_alert(
                code=PLAN_STALE_RULESET, severity=SEVERITY_HINT,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"plan_ruleset": plan.ruleset_version,
                          "current_ruleset": ctx.ruleset_version},
                action_kind="REVIEW",
                next_step_cn="计划基于旧规则集，建议复核是否仍适用",
            ))
        if plan.valid_until and ctx.last_bar_date >= plan.valid_until:
            alerts.append(_alert(
                code=PLAN_EXPIRING, severity=SEVERITY_HINT,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"valid_until": plan.valid_until, "as_of": ctx.last_bar_date},
                action_kind="REVIEW",
                next_step_cn="计划已到有效期，请给出结论（延续/结束）",
            ))

        opp = _matching_opportunity(plan, ctx)
        if not holding_watch and plan.entry_lifecycle_id and opp is None:
            alerts.append(_alert(
                code=PLAN_ORPHANED, severity=SEVERITY_HINT,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"entry_lifecycle_id": plan.entry_lifecycle_id},
                action_kind="REVIEW",
                next_step_cn="入场生命周期在当日 DTO 中找不到，建议复核计划",
            ))

        # 失效价击穿 / lifecycle 已失效（armed 与 entered 都判）
        breached = _invalidation_breached(plan, ctx, opp)
        if breached:
            alerts.append(_alert(
                code=INVALIDATION_BREACHED, severity=SEVERITY_BLOCK,
                rule_id=PLAN_DISCIPLINE_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence=breached,
                principle_source="规格 §14 原文",
                caveat_cn="原则出自规格§14（不得移动原定失效价）；击穿判定为研究代理",
                action_kind="EXIT" if plan.state == "entered" else None,
                next_step_cn="失效价已被击穿，按原定计划退出，不得事后移动失效价",
            ))

    # 入场阶段 alert（armed）。持仓盯盘不判入场。
    if plan.state == "armed" and not holding_watch:
        if not ctx.tradability_tradable:
            alerts.append(_alert(
                code=ENTRY_BLOCKED_BY_TRADABILITY, severity=SEVERITY_BLOCK,
                rule_id=TRADABILITY_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"blocking_reasons": list(ctx.tradability_blocking_reasons)},
                principle_source="规格 §13 原文",
                caveat_cn="规格§13无交易条件；可交易性判定为研究代理",
                next_step_cn="环境阻断，按规则不该开新仓",
            ))
        opp = _matching_opportunity(plan, ctx)
        if opp is not None:
            entry_rule = _entry_rule_id(plan)
            if opp.current_conditions_confirmed and opp.state != "invalidated":
                alerts.append(_alert(
                    code=ENTRY_CONDITIONS_MET, severity=SEVERITY_REMIND,
                    rule_id=entry_rule, ctx=ctx, actionable_from=actionable_from,
                    evidence={"lifecycle_id": opp.lifecycle_id,
                              "current_conditions_confirmed": True},
                    action_kind="ENTER",
                    next_step_cn="入场条件已成立，下一交易日开盘可执行（参考，非指令）",
                ))
            else:
                alerts.append(_alert(
                    code=ENTRY_CONDITIONS_LOST, severity=SEVERITY_REMIND,
                    rule_id=entry_rule, ctx=ctx, actionable_from=actionable_from,
                    evidence={"lifecycle_id": opp.lifecycle_id,
                              "current_conditions_confirmed": opp.current_conditions_confirmed,
                              "opp_state": opp.state},
                    action_kind="CLOSE_ENTER",
                    next_step_cn="入场条件不再成立，关闭 ENTER 待办",
                ))
            _rr_alerts(opp, ctx, actionable_from, alerts)

    # 退出阶段 alert（entered）
    if plan.state == "entered":
        for esig in ctx.exit_signals:
            if esig.state == "active":
                alerts.append(_alert(
                    code=EXIT_TRIGGERED, severity=SEVERITY_REMIND,
                    rule_id=esig.rule_id, ctx=ctx, actionable_from=actionable_from,
                    evidence={"exit_rule_id": esig.rule_id, "state": "active"},
                    action_kind="EXIT",
                    next_step_cn="退出条件已触发，下一交易日开盘退出（参考，非指令）",
                ))
        if holding_watch:
            _holding_watch_alerts(plan, ctx, actionable_from, alerts)

    return alerts


def _holding_watch_alerts(
    plan: TradePlan,
    ctx: MonitorContext,
    actionable_from: str,
    alerts: list[PlanAlert],
) -> None:
    """持仓盯盘退出提醒：止盈达到 / 止损击穿 / 信号命中（规则 holding_watch_guard）。

    方向感知：long 止盈在上、止损在下；short 反向。只用当日可见收盘价
    （14:45 盘中快照时为虚拟当日 bar 的快照价），不预测、不算新数值。
    """
    close = ctx.current_close
    is_long = plan.direction == "long"
    atr = ctx.atr
    # 接近预警带宽（ATR 倍数）；atr 不可用时静默跳过，不阻断。源：规则账本，不写死。
    # proximity_atr<=0 时 proximity_atr*atr<=0，而未击穿的 distance>0，
    # distance<=band 必不成立，故无需额外正负守卫--非正配置天然不报接近预警。
    proximity_atr = float(get_rule(HOLDING_WATCH_RULE).param("proximity_atr", 1.0))

    if close is not None and plan.take_profit_price is not None:
        reached = (
            close >= plan.take_profit_price if is_long else close <= plan.take_profit_price
        )
        if reached:
            alerts.append(_alert(
                code=TAKE_PROFIT_REACHED, severity=SEVERITY_REMIND,
                rule_id=HOLDING_WATCH_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"close": close, "take_profit_price": plan.take_profit_price,
                          "direction": plan.direction},
                caveat_cn="持仓盯盘触发价由人自填；比较判定为研究代理",
                action_kind="EXIT",
                next_step_cn="已达到你设定的止盈价，按你写的止盈预案处理（参考，非指令）",
            ))
        elif atr is not None:
            # 接近预警：未达到，但已在 proximity_atr*atr 带宽内。
            distance = abs(close - plan.take_profit_price)
            if distance <= proximity_atr * atr:
                alerts.append(_alert(
                    code=TAKE_PROFIT_APPROACHING, severity=SEVERITY_REMIND,
                    rule_id=HOLDING_WATCH_RULE, ctx=ctx, actionable_from=actionable_from,
                    evidence={"close": close, "take_profit_price": plan.take_profit_price,
                              "direction": plan.direction, "atr": atr,
                              "distance": distance, "distance_atr": distance / atr},
                    caveat_cn="持仓盯盘触发价由人自填；接近判定为研究代理",
                    next_step_cn=(
                        f"价格距止盈价约 {distance:.2f}（{distance / atr:.2f} ATR），"
                        "临近你设定的止盈位，留意止盈预案（参考，非指令）"
                    ),
                ))

    if close is not None and plan.stop_price is not None:
        breached = close <= plan.stop_price if is_long else close >= plan.stop_price
        if breached:
            alerts.append(_alert(
                code=STOP_PRICE_BREACHED, severity=SEVERITY_BLOCK,
                rule_id=HOLDING_WATCH_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"close": close, "stop_price": plan.stop_price,
                          "direction": plan.direction},
                principle_source="规格 §14 原文",
                caveat_cn=(
                    "原则出自规格§14（不得在亏损后移动原定失效价）；"
                    "触发价由人自填、击穿判定为研究代理"
                ),
                action_kind="EXIT",
                next_step_cn="已击穿你设定的止损价，按原定止损预案退出，不得事后下移止损",
            ))
        elif atr is not None:
            distance = abs(close - plan.stop_price)
            if distance <= proximity_atr * atr:
                alerts.append(_alert(
                    code=STOP_PRICE_APPROACHING, severity=SEVERITY_REMIND,
                    rule_id=HOLDING_WATCH_RULE, ctx=ctx, actionable_from=actionable_from,
                    evidence={"close": close, "stop_price": plan.stop_price,
                              "direction": plan.direction, "atr": atr,
                              "distance": distance, "distance_atr": distance / atr},
                    principle_source="规格 §14 原文",
                    caveat_cn=(
                        "原则出自规格§14（不得在亏损后移动原定失效价）；"
                        "触发价由人自填、接近判定为研究代理"
                    ),
                    next_step_cn=(
                        f"价格距止损价约 {distance:.2f}（{distance / atr:.2f} ATR），"
                        "临近你设定的止损位，按原定止损预案准备，不得事后下移止损"
                    ),
                ))

    if plan.watch_signal_rule_ids:
        hit = [r for r in plan.watch_signal_rule_ids if r in ctx.new_event_rule_ids]
        if hit:
            alerts.append(_alert(
                code=SIGNAL_WATCH_TRIGGERED, severity=SEVERITY_REMIND,
                rule_id=HOLDING_WATCH_RULE, ctx=ctx, actionable_from=actionable_from,
                evidence={"triggered_rule_ids": hit,
                          "watch_signal_rule_ids": list(plan.watch_signal_rule_ids)},
                caveat_cn="盯盘信号由人自选 rule_id；命中判定为研究代理",
                action_kind="EXIT",
                next_step_cn=(
                    f"你盯的信号已出现（{', '.join(hit)}），按你写的退出预案复核"
                    "（参考，非指令）"
                ),
            ))


def _matching_opportunity(
    plan: TradePlan, ctx: MonitorContext
) -> OpportunityRef | None:
    """按 lifecycle_id 匹配，且方向必须与计划一致。

    方向不一致的同名机会视为不匹配（做多计划不得拿空头场景当入场条件，红线 4）。
    """
    if not plan.entry_lifecycle_id:
        return None
    return next(
        (
            o
            for o in ctx.opportunities
            if o.lifecycle_id == plan.entry_lifecycle_id
            and o.direction == plan.direction
        ),
        None,
    )


def _invalidation_breached(
    plan: TradePlan, ctx: MonitorContext, opp: OpportunityRef | None
) -> dict[str, Any] | None:
    if (
        plan.invalidation_price is not None
        and ctx.current_close is not None
        and ctx.current_close < plan.invalidation_price
    ):
        return {"close": ctx.current_close,
                "invalidation_price": plan.invalidation_price}
    if opp is not None and opp.state == "invalidated":
        return {"lifecycle_id": opp.lifecycle_id, "opp_state": "invalidated"}
    return None


def _rr_alerts(
    opp: OpportunityRef,
    ctx: MonitorContext,
    actionable_from: str,
    alerts: list[PlanAlert],
) -> None:
    rr_min = float(get_rule(RR_RULE).param("rr_min_ideal", 3))
    if not opp.reward_risk_computable:
        alerts.append(_alert(
            code=ENTRY_RR_NOT_COMPUTABLE, severity=SEVERITY_HINT,
            rule_id=RR_RULE, ctx=ctx, actionable_from=actionable_from,
            evidence={"reward_risk_computable": False},
            principle_source="规格 §13 第 4 条 原文",
            caveat_cn="规格§13第4条列为无交易条件；目标不可计算时仅提示",
            next_step_cn="盈亏比目标不可计算，仅提示不拦截",
        ))
    elif opp.reward_risk_ratio is not None and opp.reward_risk_ratio < rr_min:
        alerts.append(_alert(
            code=ENTRY_RR_BELOW_IDEAL, severity=SEVERITY_HINT,
            rule_id=RR_RULE, ctx=ctx, actionable_from=actionable_from,
            evidence={"reward_risk_ratio": opp.reward_risk_ratio, "rr_min_ideal": rr_min},
            principle_source="规格 §13 第 4 条 原文",
            caveat_cn="规格§13第4条列为无交易条件；人类2026-08-04定为只提示不拦截，建议>3，2–3可接受",
            next_step_cn=f"R/R={opp.reward_risk_ratio:.2f}<{rr_min:g}，仅提示不拦截",
        ))


# ---------------------------------------------------------------- 推迟复活谓词（决策 4c）


def _resolve_path(ctx: MonitorContext, path: str) -> Any:
    if path == "close":
        return ctx.current_close
    if path == "ema20":
        return ctx.ema20
    if path == "tradability.tradable":
        return ctx.tradability_tradable
    raise ValueError(
        f"resume_on 引用了系统算不出的路径: {path}; 可引用: "
        f"{', '.join(RESOLVABLE_PATHS)} 或 rule_id"
    )


def _coerce_ref(ctx: MonitorContext, ref: Any) -> Any:
    """ref 若是已知路径字符串则解析为路径值，否则按字面量返回。"""
    if isinstance(ref, str) and ref in RESOLVABLE_PATHS:
        return _resolve_path(ctx, ref)
    return ref


def evaluate_resume(predicate: dict[str, Any], ctx: MonitorContext) -> bool:
    """验推迟复活谓词。两种形态：
    {"rule_id": "..."} -> 该 rule_id 在当日 new_events 中即复活；
    {"field": path, "op": op, "ref": value} -> DTO 点路径比较。
    引用系统算不出的路径/字段时抛 ValueError（skill 据此拒绝并报清单）。
    """
    if "rule_id" in predicate:
        return str(predicate["rule_id"]) in ctx.new_event_rule_ids
    if "field" not in predicate:
        raise ValueError(f"resume_on 谓词格式不合法: {predicate}")
    left = _resolve_path(ctx, str(predicate["field"]))
    right = _coerce_ref(ctx, predicate.get("ref"))
    op = str(predicate.get("op", ">="))
    if left is None or right is None:
        return False
    ops = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
           ">": lambda a, b: a > b, "<": lambda a, b: a < b,
           "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
    if op not in ops:
        raise ValueError(f"resume_on 不支持的 op: {op}; 可用: {', '.join(ops)}")
    try:
        return bool(ops[op](left, right))
    except TypeError as exc:
        raise ValueError(f"resume_on 比较类型不兼容: {left!r} {op} {right!r}") from exc


__all__ = [
    "ACTIVE_STATES",
    "DATA_STALE",
    "ENTRY_BLOCKED_BY_TRADABILITY",
    "ENTRY_CONDITIONS_LOST",
    "ENTRY_CONDITIONS_MET",
    "ENTRY_RR_BELOW_IDEAL",
    "ENTRY_RR_NOT_COMPUTABLE",
    "EXIT_TRIGGERED",
    "ExitSignalRef",
    "HOLDING_WATCH_RULE",
    "INVALIDATION_BREACHED",
    "MODULE_NOT_IMPLEMENTED",
    "MonitorContext",
    "OpportunityRef",
    "PLAN_DISCIPLINE_RULE",
    "PLAN_EXPIRING",
    "PLAN_ORPHANED",
    "PLAN_STALE_RULESET",
    "RESOLVABLE_PATHS",
    "RR_RULE",
    "SIGNAL_WATCH_TRIGGERED",
    "STOP_PRICE_APPROACHING",
    "STOP_PRICE_BREACHED",
    "TAKE_PROFIT_APPROACHING",
    "TAKE_PROFIT_REACHED",
    "TRADABILITY_RULE",
    "evaluate_plan",
    "evaluate_resume",
]
