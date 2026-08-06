"""买点审阅与批量扫描（表达层的数据源，不含新判定）。

**本模块不做任何买点判断。** 它只把既有确定性 DTO（可交易性门禁、条件化场景、
分层机会、盈亏比）汇总成一份便于讲解与落计划的结构，`verdict` 由字段组合派生。

判定权仍在 Python 规则层：候选买点全部来自已实现的 A/B/C/D 模块与 P2 场景；
止损只引场景/结构已给出的失效位；盈亏比只照抄 compute_reward_risk 的结果。
任何本模块无法从既有字段取到的数值，一律留空（None），绝不推算--
"到什么位置才是买点"只能是系统自己的触发价，不是预测。
"""
from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    BuyPointCandidateDTO,
    BuyPointReviewDTO,
    ScanItemDTO,
    ScanResponse,
    SuggestedPlanDTO,
    WatchConditionDTO,
)
from lei_signal.domain.rules_config import ruleset_version
from lei_signal.plans.store import list_plans
from lei_signal.research.module_backtest import module_of
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["opportunities"])

VERDICT_ACTIONABLE = "actionable"
VERDICT_BLOCKED = "blocked"
VERDICT_WAITING = "waiting"
VERDICT_NONE = "none"

_VERDICT_CN = {
    VERDICT_ACTIONABLE: "条件已成立",
    VERDICT_BLOCKED: "环境阻断",
    VERDICT_WAITING: "等待条件成立",
    VERDICT_NONE: "当前无机会",
}

DISCLAIMER = (
    "本审阅只汇总系统既有确定性判定（可交易性门禁 + 已实现模块的条件化场景 + "
    "盈亏比），不含预测。研究代理项已标注；下一根 K 线开盘为最早可执行时点。"
)

#: 缺失条件文案 -> 可交给系统盯盘的 rule_id（复用 holding_watch 的信号形态）。
#: 只映射语义明确的几条，映射不到就不给建议，不硬凑。
_CONDITION_SIGNAL_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("多头排列", ("ma_full_alignment",)),
    ("均线排列", ("ma_full_alignment",)),
    ("EMA20", ("ema20_reclaim_rising",)),
    ("双均线", ("dual_ma_bull_confirmed",)),
    ("颜色", ("lei_color",)),
    ("转绿", ("lei_color",)),
)


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _service(request: Request) -> Any:
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    return service


def _signal_hints(text: str) -> list[str]:
    for needle, rule_ids in _CONDITION_SIGNAL_HINTS:
        if needle in text:
            return list(rule_ids)
    return []


def _watch_conditions(
    candidates: list[BuyPointCandidateDTO],
) -> list[WatchConditionDTO]:
    """把缺失条件整理成「到什么情况才算买点」。

    区分价位型与状态型：只有当该候选给出了 key_price 且条件文案确实在讲价格
    （突破/站上/收回/跌破）时才附价位。否则标 state，不贴数字--
    缺「完整多头排列未成立」这类条件没有单一价格，硬贴就是编造。
    """
    price_words = ("突破", "站上", "收回", "跌破", "回到", "上沿", "下沿", "参考位")
    out: list[WatchConditionDTO] = []
    seen: set[str] = set()
    for cand in candidates:
        for text in cand.missing_conditions:
            if text in seen:
                continue
            seen.add(text)
            is_price = any(word in text for word in price_words)
            out.append(
                WatchConditionDTO(
                    text_cn=text,
                    kind="price" if (is_price and cand.key_price is not None) else "state",
                    price=cand.key_price if (is_price and cand.key_price is not None) else None,
                    as_signal_rule_ids=_signal_hints(text),
                )
            )
    return out


def _candidate_from_scenario(scenario: Any) -> BuyPointCandidateDTO:
    rule_id = scenario.scenario_id
    event = getattr(scenario, "supporting_event", None)
    if event is not None and getattr(event, "rule_id", None):
        rule_id = event.rule_id
    return BuyPointCandidateDTO(
        scenario_id=scenario.scenario_id,
        scenario_cn=scenario.scenario_cn,
        module=module_of(rule_id),
        direction=scenario.direction,
        state=scenario.state,
        state_cn=scenario.state_cn,
        rule_id=rule_id,
        lifecycle_id=getattr(event, "lifecycle_id", None) if event else None,
        satisfied_conditions=list(scenario.satisfied_conditions),
        missing_conditions=list(scenario.missing_conditions),
        key_price=scenario.key_price,
        # 场景卡只给失效文案不给失效价；不编造价位，交由建计划时人工确认。
        invalidation_price=None,
        invalidation_cn=scenario.invalidation_cn,
        reward_risk_ratio=scenario.reward_risk_ratio,
        reward_risk_target=scenario.reward_risk_target,
        reward_risk_target_source_cn=scenario.reward_risk_target_source_cn,
        reward_risk_computable=scenario.reward_risk_computable,
        next_step_cn=scenario.next_step_cn,
        caveat_cn=scenario.caveat_cn,
    )


def _candidate_from_opportunity(opp: Any) -> BuyPointCandidateDTO:
    """分层机会（底部结构/回撤）-> 候选。失效价取结构 C 点（系统已算）。"""
    event = getattr(opp, "supporting_event", None)
    rule_id = getattr(event, "rule_id", None) if event else None
    structure = getattr(opp, "structure", None)
    scenario_cn = "底部结构条件化做多"
    if structure is not None:
        scenario_cn = f"{structure.structure_type_cn}·条件化做多"
    return BuyPointCandidateDTO(
        scenario_id=rule_id or "trade_opportunity",
        scenario_cn=scenario_cn,
        module=module_of(rule_id) if rule_id else None,
        direction=getattr(opp, "direction", "long"),
        state=opp.state,
        state_cn=getattr(opp, "state_cn", ""),
        rule_id=rule_id,
        lifecycle_id=getattr(opp, "lifecycle_id", None),
        satisfied_conditions=list(opp.satisfied_conditions),
        missing_conditions=list(opp.missing_conditions),
        key_price=getattr(opp, "b1_price", None),
        # 结构 C 点是系统已确认的失效位，可作止损引用
        invalidation_price=getattr(structure, "c_price", None) if structure else None,
        invalidation_cn=opp.invalidation_cn,
        reward_risk_ratio=getattr(opp, "reward_risk_ratio", None),
        reward_risk_target=getattr(opp, "reward_risk_target", None),
        reward_risk_target_source_cn=getattr(opp, "reward_risk_target_source_cn", None),
        reward_risk_computable=getattr(opp, "reward_risk_computable", False),
        next_step_cn=opp.next_step_cn,
        caveat_cn=getattr(opp, "caveat_cn", ""),
    )


def build_review(
    result: Any,
    *,
    symbol: str,
    display_name: str = "",
    active_plan_ids: tuple[str, ...] = (),
) -> BuyPointReviewDTO:
    """汇总既有判定为买点审阅。无新判定、无新数值。"""
    from lei_signal.api.routes.symbols import _assessment_dto  # noqa: PLC0415

    assessment = _assessment_dto(result)
    frame = result.frame
    last_close = float(frame.iloc[-1]["close"]) if len(frame) else None
    return _review_from_assessment(
        assessment,
        last_close=last_close,
        symbol=symbol,
        display_name=display_name or symbol,
        active_plan_ids=active_plan_ids,
    )


def _review_from_assessment(
    assessment: Any,
    *,
    last_close: float | None,
    symbol: str,
    display_name: str = "",
    active_plan_ids: tuple[str, ...] = (),
) -> BuyPointReviewDTO:
    """从 AssessmentDTO 汇总买点审阅（测试入口，避开完整 analyze 管线）。"""
    candidates: list[BuyPointCandidateDTO] = [
        _candidate_from_scenario(s) for s in assessment.conditional_scenarios
    ]
    for opp in (*assessment.trade_opportunities, *assessment.pullback_opportunities):
        candidates.append(_candidate_from_opportunity(opp))
    # 只讲活着的候选；已失效的不构成买点
    candidates = [c for c in candidates if c.state != "invalidated"]

    tradability = assessment.tradability
    tradable = bool(tradability.tradable) if tradability else False
    confirmed = [c for c in candidates if c.state == "confirmed"]

    if confirmed and tradable:
        verdict = VERDICT_ACTIONABLE
    elif candidates and not tradable:
        verdict = VERDICT_BLOCKED
    elif candidates:
        verdict = VERDICT_WAITING
    else:
        verdict = VERDICT_NONE

    # 排序：confirmed 优先，其次 R/R 可计算且更高者靠前（只排序，不改数值）
    candidates.sort(
        key=lambda c: (
            0 if c.state == "confirmed" else 1,
            -(c.reward_risk_ratio or 0.0),
        )
    )

    suggested: SuggestedPlanDTO | None = None
    if verdict == VERDICT_ACTIONABLE:
        best = confirmed[0]
        suggested = SuggestedPlanDTO(
            symbol=symbol,
            module=best.module or "A",
            direction=best.direction,
            entry_rule_id=best.rule_id,
            entry_lifecycle_id=best.lifecycle_id,
            entry_trigger_cn=best.scenario_cn,
            invalidation_price=best.invalidation_price,
            target_b_price=best.reward_risk_target,
            target_b_source=best.reward_risk_target_source_cn,
            reward_risk_at_plan=best.reward_risk_ratio,
        )

    watch = _watch_conditions(candidates) if verdict != VERDICT_ACTIONABLE else []

    if verdict == VERDICT_ACTIONABLE:
        summary = (
            f"{len(confirmed)} 个场景条件已成立，可交易性未阻断；"
            "下一根 K 线开盘为最早可执行时点（参考，非指令）。"
        )
    elif verdict == VERDICT_BLOCKED:
        reasons = "、".join(tradability.blocking_reasons) if tradability else ""
        summary = (
            f"存在 {len(candidates)} 个场景，但环境阻断：{reasons or '见门禁明细'}"
            "（规格 §13，按规则不开新仓）。"
        )
    elif verdict == VERDICT_WAITING:
        summary = (
            f"{len(candidates)} 个场景在观察中，尚有条件未成立；"
            "下列条件成立即构成系统定义的买点。"
        )
    else:
        summary = "当前没有任何活跃的条件化场景，无买点可言。"

    return BuyPointReviewDTO(
        symbol=symbol,
        display_name=display_name or symbol,
        as_of=assessment.as_of,
        last_close=last_close,
        verdict=verdict,
        verdict_cn=_VERDICT_CN[verdict],
        summary_cn=summary,
        tradability=tradability,
        candidates=candidates,
        watch_conditions=watch,
        suggested_plan=suggested,
        has_active_plan=bool(active_plan_ids),
        active_plan_ids=list(active_plan_ids),
        ruleset_version=ruleset_version(),
        disclaimer_cn=DISCLAIMER,
    )


def _active_plan_ids(db_path: str, symbol: str) -> tuple[str, ...]:
    with closing(connect(db_path)) as conn:
        return tuple(
            p.plan_id
            for p in list_plans(conn, symbol=symbol)
            if p.state in ("armed", "entered")
        )


@router.get("/symbols/{symbol}/buy-point-review", response_model=BuyPointReviewDTO)
def buy_point_review(request: Request, symbol: str, refresh: bool = False) -> BuyPointReviewDTO:
    """买点审阅：当前是否构成系统定义的买点、图什么信号、止损与盈亏比。"""
    entry = _service(request).get(symbol, refresh=refresh)
    if entry.result is None:
        raise HTTPException(status_code=502, detail=entry.error or "分析不可用")
    return build_review(
        entry.result,
        symbol=symbol,
        display_name=getattr(entry.result, "display_name", "") or symbol,
        active_plan_ids=_active_plan_ids(_db_path(request), symbol),
    )


@router.get("/opportunities/scan", response_model=ScanResponse)
def scan_opportunities(
    request: Request,
    symbols: str | None = None,
    refresh: bool = False,
    only_with_candidates: bool = True,
) -> ScanResponse:
    """一键扫自选：哪些标的当前有系统定义的买点、哪些还没建计划。"""
    service = _service(request)
    db_path = _db_path(request)
    if symbols:
        wanted = [s.strip() for s in symbols.split(",") if s.strip()]
    else:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(connect(db_path)) as conn:
            wanted = [item.symbol for item in list_watchlist(conn)]
    if not wanted:
        return ScanResponse(
            generated_at=datetime.now(UTC).isoformat(), scanned=0, items=[]
        )

    entries = service.get_many(wanted, refresh=refresh)
    items: list[ScanItemDTO] = []
    for symbol in wanted:
        entry = entries.get(symbol)
        if entry is None or entry.result is None:
            items.append(ScanItemDTO(
                symbol=symbol, verdict=VERDICT_NONE, verdict_cn=_VERDICT_CN[VERDICT_NONE],
                error=(entry.error if entry else "分析不可用"),
            ))
            continue
        try:
            review = build_review(
                entry.result, symbol=symbol,
                display_name=getattr(entry.result, "display_name", "") or symbol,
                active_plan_ids=_active_plan_ids(db_path, symbol),
            )
        except Exception as exc:  # noqa: BLE001  单标的失败不影响整体
            items.append(ScanItemDTO(
                symbol=symbol, verdict=VERDICT_NONE, verdict_cn=_VERDICT_CN[VERDICT_NONE],
                error=f"审阅失败：{exc}",
            ))
            continue
        if only_with_candidates and review.verdict == VERDICT_NONE:
            continue
        best = review.candidates[0] if review.candidates else None
        missing = "；".join(w.text_cn for w in review.watch_conditions[:2])
        items.append(ScanItemDTO(
            symbol=symbol,
            display_name=review.display_name,
            verdict=review.verdict,
            verdict_cn=review.verdict_cn,
            best_scenario_cn=best.scenario_cn if best else None,
            best_state=best.state if best else None,
            reward_risk_ratio=best.reward_risk_ratio if best else None,
            reward_risk_computable=bool(best.reward_risk_computable) if best else False,
            blocking_reasons=(
                list(review.tradability.blocking_reasons) if review.tradability else []
            ),
            missing_summary_cn=missing,
            has_active_plan=review.has_active_plan,
        ))
    # actionable 排前，其次 blocked/waiting；同档按 R/R 降序
    rank = {VERDICT_ACTIONABLE: 0, VERDICT_BLOCKED: 1, VERDICT_WAITING: 2, VERDICT_NONE: 3}
    items.sort(key=lambda i: (rank.get(i.verdict, 9), -(i.reward_risk_ratio or 0.0)))
    return ScanResponse(
        generated_at=datetime.now(UTC).isoformat(), scanned=len(wanted), items=items
    )


__all__ = [
    "VERDICT_ACTIONABLE",
    "VERDICT_BLOCKED",
    "VERDICT_NONE",
    "VERDICT_WAITING",
    "build_review",
    "router",
]
