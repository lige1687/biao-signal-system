"""从 ``SymbolDetailDTO`` 裁剪出 ``MonitorContext``（规格 §7.2 上下文裁剪）。

只取监督判定需要的字段，其余 DTO 字段一律不给判定层。判定层（monitor）不依赖
API schema，只依赖 ``MonitorContext``；本模块是唯一的 DTO 适配点。
"""
from __future__ import annotations

from typing import Any

from lei_signal.domain.rules_config import ruleset_version
from lei_signal.plans.monitor import ExitSignalRef, MonitorContext, OpportunityRef

#: 三类机会 DTO -> OpportunityRef 的 rule_id 兜底
_OPP_RULE_FALLBACK = {
    "trade": "ema20_reclaim_rising",
}


def _opp_lifecycle_id(opp: Any) -> str | None:
    lifecycle = getattr(opp, "lifecycle_id", None)
    if lifecycle:
        return lifecycle
    supporting = getattr(opp, "supporting_event", None)
    if supporting is not None and getattr(supporting, "lifecycle_id", None):
        return supporting.lifecycle_id
    sid = getattr(opp, "scenario_id", None)
    return sid


def _opp_rule_id(opp: Any) -> str | None:
    supporting = getattr(opp, "supporting_event", None)
    if supporting is not None and getattr(supporting, "rule_id", None):
        return supporting.rule_id
    return getattr(opp, "scenario_id", None)


def _to_opportunity_ref(opp: Any) -> OpportunityRef | None:
    lifecycle_id = _opp_lifecycle_id(opp)
    if not lifecycle_id:
        return None
    return OpportunityRef(
        lifecycle_id=lifecycle_id,
        current_conditions_confirmed=bool(getattr(opp, "current_conditions_confirmed", False)),
        state=str(getattr(opp, "state", "")),
        rule_id=_opp_rule_id(opp),
        reward_risk_ratio=getattr(opp, "reward_risk_ratio", None),
        reward_risk_computable=bool(getattr(opp, "reward_risk_computable", False)),
    )


def _last_ema20(chart: dict[str, Any]) -> float | None:
    series = chart.get("ema20") if isinstance(chart, dict) else None
    if not series:
        return None
    for value in reversed(series):
        if value is not None:
            return float(value)
    return None


def from_symbol_detail(dto: Any) -> MonitorContext:
    """从 SymbolDetailDTO 裁剪 MonitorContext。"""
    meta = dto.meta
    assessment = dto.assessment
    chart = dto.chart if isinstance(dto.chart, dict) else {}
    current_close = chart.get("lastClose")
    current_close = float(current_close) if current_close is not None else None

    opportunities: list[OpportunityRef] = []
    for opp in (*assessment.trade_opportunities, *assessment.pullback_opportunities,
                *assessment.conditional_scenarios):
        ref = _to_opportunity_ref(opp)
        if ref is not None:
            opportunities.append(ref)

    exit_signals = tuple(
        ExitSignalRef(rule_id=es.rule_id, state=es.state)
        for es in assessment.exit_signals
    )
    new_event_rule_ids = tuple(e.rule_id for e in dto.new_events if e.rule_id)

    tradability = assessment.tradability
    return MonitorContext(
        last_bar_date=meta.last_bar_date or "",
        cache_fallback_used=bool(meta.cache_fallback_used),
        current_close=current_close,
        ema20=_last_ema20(chart),
        tradability_tradable=bool(tradability.tradable) if tradability else True,
        tradability_blocking_reasons=tuple(
            tradability.blocking_reasons if tradability else ()
        ),
        ruleset_version=ruleset_version(),
        opportunities=tuple(opportunities),
        exit_signals=exit_signals,
        new_event_rule_ids=new_event_rule_ids,
    )


__all__ = ["from_symbol_detail"]
