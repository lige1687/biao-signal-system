"""从 ``SymbolDetailDTO`` 裁剪出 ``MonitorContext``（规格 §7.2 上下文裁剪）。

只取监督判定需要的字段，其余 DTO 字段一律不给判定层。判定层（monitor）不依赖
API schema，只依赖 ``MonitorContext``；本模块是唯一的 DTO 适配点。
"""
from __future__ import annotations

from typing import Any

import pandas as pd

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


def _opp_direction(opp: Any) -> str:
    """机会自身方向。ConditionalScenarioDTO 有 direction；回撤/结构机会为做多。

    做空镜像事件的 evidence 带 direction_side=short，优先采信它。
    """
    supporting = getattr(opp, "supporting_event", None)
    if supporting is not None:
        evidence = getattr(supporting, "evidence", None) or {}
        side = evidence.get("direction_side")
        if side in ("long", "short"):
            return str(side)
    direction = getattr(opp, "direction", None)
    if direction in ("long", "short"):
        return str(direction)
    return "long"


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
        direction=_opp_direction(opp),
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


def context_from_result(result: Any, *, cache_fallback_used: bool = False) -> MonitorContext:
    """从 ``AnalysisResult`` 构建 MonitorContext（监督员 live/fixture 取数路径）。

    复用路由 ``_assessment_dto`` 的全部机会/可交易性/退出/R/R 拼装逻辑，避免与
    看盘界面分叉。lazy import 以免 plans 包在加载期拖入整个路由模块。
    """
    from lei_signal.api.routes.symbols import _assessment_dto  # noqa: PLC0415
    from lei_signal.domain.rules_config import ruleset_version  # noqa: PLC0415

    assessment = _assessment_dto(result)
    frame = result.frame
    last_row = frame.iloc[-1]
    last_bar_date = frame.index[-1].date().isoformat()
    current_close = float(last_row["close"]) if len(frame) else None
    ema20 = (
        float(last_row["ema20"])
        if "ema20" in frame.columns and pd.notna(last_row.get("ema20"))
        else None
    )

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
    new_event_rule_ids = tuple(
        e.rule_id for e in result.assessment.new_events if e.rule_id
    )
    tradability = assessment.tradability
    return MonitorContext(
        last_bar_date=last_bar_date,
        cache_fallback_used=cache_fallback_used,
        current_close=current_close,
        ema20=ema20,
        tradability_tradable=bool(tradability.tradable) if tradability else True,
        tradability_blocking_reasons=tuple(
            tradability.blocking_reasons if tradability else ()
        ),
        ruleset_version=ruleset_version(),
        opportunities=tuple(opportunities),
        exit_signals=exit_signals,
        new_event_rule_ids=new_event_rule_ids,
    )


__all__ = ["context_from_result", "from_symbol_detail"]
