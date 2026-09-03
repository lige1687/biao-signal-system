"""标的级端点：符号解析、详情、市场环境徽章、刷新。"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from lei_signal.api import config, labels
from lei_signal.api.card_mapper import (
    event_dto,
    is_intraday_forming,
    structure_brief,
    to_explanation_dto,
)
from lei_signal.api.config import DETAIL_MAX_BARS, RECENT_EVENTS_LIMIT
from lei_signal.api.explanations import CONCEPTS, MARK_KIND_CONCEPTS, lookup
from lei_signal.api.market_context_service import MarketContextDTO, MarketContextService
from lei_signal.api.macd_events import build_macd_events
from lei_signal.api.news_marks import build_news_marks
from lei_signal.api.overview import build_today_overview
from lei_signal.api.quotes import TencentQuoteProvider
from lei_signal.api.routes.dashboard import assemble_dashboard
from lei_signal.api.schemas import (
    AssessmentDTO,
    ColorBacktestDTO,
    ColorBacktestSideDTO,
    ColorPerformanceDTO,
    ConditionalScenarioDTO,
    ConditionCheckDTO,
    DashboardResponse,
    EventDTO,
    ExitSignalDTO,
    FactorDTO,
    MarketBadgeDTO,
    MetaDTO,
    PullbackBacktestDTO,
    PullbackBacktestSideDTO,
    PullbackOpportunityDTO,
    PullbackPerformanceDTO,
    RefreshRequest,
    ResolveResultDTO,
    RiskAlertDTO,
    ScenarioBacktestDTO,
    ScenarioBacktestSideDTO,
    SymbolDetailDTO,
    TradabilityDTO,
    TradeOpportunityDTO,
)
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.data.providers import _classify_error, default_provider
from lei_signal.data.symbols import MARKET_CN, resolve_symbol
from lei_signal.data.validation import DataUnavailableError
from lei_signal.domain.rules_config import get_rule
from lei_signal.features.indicators import average_true_range
from lei_signal.features.weekly_context import weekly_env_series
from lei_signal.rules.clock_classifier import TYPE2_STEADY_UP, clock_series
from lei_signal.domain.types import (
    COLOR_CN,
    STAGE_CN,
    DailyAssessment,
    SignalEvent,
    StructureInstance,
)
from lei_signal.market_context.types import MarketId
from lei_signal.research.alignment_backtest import build_alignment_backtest
from lei_signal.research.color_backtest import ColorBacktestSide, build_color_backtest
from lei_signal.research.exit_variant_backtest import build_exit_variant_backtest
from lei_signal.research.false_breakout_backtest import build_false_breakout_backtest
from lei_signal.research.first_ma_pullback_backtest import (
    build_first_ma_pullback_backtest,
)
from lei_signal.research.low_level_backtest import build_low_level_backtest
from lei_signal.research.module_backtest import build_module_backtest
from lei_signal.research.reward_risk_backtest import build_reward_risk_backtest
from lei_signal.research.scenario_backtest_common import ScenarioBacktestReport
from lei_signal.rules.dense_breakout import (
    RULE_ID as DB_RULE_ID,
)
from lei_signal.rules.dense_breakout import (
    SUB_RULE_CONFIRMED as DB_CONFIRMED,
)
from lei_signal.rules.dense_breakout import (
    SUB_RULE_FAILED as DB_FAILED,
)
from lei_signal.rules.dense_breakout import (
    SUB_RULE_WATCH as DB_WATCH,
)
from lei_signal.rules.dense_breakout import (
    _recent_dense_upper_bound as _db_recent_upper,
)
from lei_signal.rules.ema_reclaim_tiers import (
    SUB_RULE_BY_TIER,
    TIER_EARLY_WATCH,
    TIER_JOINT_CONFIRMED,
    TIER_LONG_TREND_IMPROVED,
    TIER_RANK,
    TIER_STRUCTURE_CONFIRMED,
)
from lei_signal.rules.exit_ema20_costbasis import (
    RULE_ID as EXIT_RULE_ID,
)
from lei_signal.rules.false_breakout_reclaim import (
    RULE_ID as FO_RULE_ID,
)
from lei_signal.rules.false_breakout_reclaim import (
    SUB_RULE_CONFIRMED as FO_CONFIRMED,
)
from lei_signal.rules.false_breakout_reclaim import (
    SUB_RULE_FAILED as FO_FAILED,
)
from lei_signal.rules.false_breakout_reclaim import (
    SUB_RULE_WATCH as FO_WATCH,
)
from lei_signal.rules.false_breakout_reclaim_short import (
    SUB_RULE_SHORT_CONFIRMED as FO_SHORT_CONFIRMED,
)
from lei_signal.rules.false_breakout_reclaim_short import (
    SUB_RULE_SHORT_FAILED as FO_SHORT_FAILED,
)
from lei_signal.rules.false_breakout_reclaim_short import (
    SUB_RULE_SHORT_WATCH as FO_SHORT_WATCH,
)
from lei_signal.rules.first_ma_pullback import (
    SUB_RULE_CONFIRMED as PULLBACK_CONFIRMED,
)
from lei_signal.rules.first_ma_pullback import (
    SUB_RULE_FAILED as PULLBACK_FAILED,
)
from lei_signal.rules.first_ma_pullback import (
    SUB_RULE_TOUCHED as PULLBACK_TOUCHED,
)
from lei_signal.rules.low_level_confirmation import (
    RULE_ID as LL_RULE_ID,
)
from lei_signal.rules.low_level_confirmation import (
    SUB_RULE_CONFIRMED as LL_CONFIRMED,
)
from lei_signal.rules.low_level_confirmation import (
    SUB_RULE_WATCH as LL_WATCH,
)
from lei_signal.rules.ma_full_alignment import (
    RULE_ID as AL_RULE_ID,
)
from lei_signal.rules.ma_full_alignment import (
    SUB_RULE_BEARISH_START as AL_BEARISH,
)
from lei_signal.rules.ma_full_alignment import (
    SUB_RULE_BROKEN as AL_BROKEN,
)
from lei_signal.rules.ma_full_alignment import (
    SUB_RULE_BULLISH_START as AL_BULLISH,
)
from lei_signal.rules.ma_full_alignment import (
    ema_slope_accel_for_frame,
)
from lei_signal.rules.reward_risk_filter import (
    TARGET_SOURCE_CN,
    compute_reward_risk,
)
from lei_signal.rules.tradability_gate import evaluate_tradability
from lei_signal.rules.two_b_reversal import (
    RULE_ID as TB_RULE_ID,
)
from lei_signal.rules.two_b_reversal import (
    SUB_RULE_FAILED as TB_FAILED,
)
from lei_signal.rules.two_b_reversal import (
    SUB_RULE_V1 as TB_V1,
)
from lei_signal.rules.two_b_reversal import (
    SUB_RULE_V2 as TB_V2,
)
from lei_signal.rules.two_b_reversal import (
    SUB_RULE_V3 as TB_V3,
)
from lei_signal.state.machine import DayState, StructureObservation
from lei_signal.ui.echarts_kline import serialize_result

router = APIRouter(prefix="/api", tags=["symbols"])

#: 盘口快照源（换手率/量比/市值）。仅 A 股覆盖，失败或不支持时返回 None，
#: 概述面板显示「—」，绝不影响 K 线与信号。
_QUOTE_PROVIDER = TencentQuoteProvider()


def _quote_provider(request: Request) -> TencentQuoteProvider | None:
    """盘口源。测试可通过 app.state.quote_provider 注入替身或置 None 禁用，
    避免单测发起真实网络请求。"""
    return getattr(request.app.state, "quote_provider", _QUOTE_PROVIDER)

#: 与 Streamlit 端 _CALENDAR_NOTE 同口径（周线完成时点保守说明）。
CALENDAR_NOTE_CN = (
    "周线完成口径：默认交易日历只认周一至周五，不含节假日表。"
    "逢节假日短周，周线完成判定会晚于实际最后交易日收盘（保守方向）。"
)


def _service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def _db_path(request: Request) -> str:
    return request.app.state.watchlist_db_path


@router.get("/symbols/resolve", response_model=ResolveResultDTO)
def resolve(q: str, probe: bool = False) -> ResolveResultDTO:
    """解析用户输入为标准符号。probe=true 时试取行情确认数据可得并取回名称。"""
    try:
        info = resolve_symbol(q)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dto = ResolveResultDTO(
        symbol=info.symbol,
        market=info.market.value,
        market_cn=MARKET_CN.get(info.market.value, info.market.value),
        bare_code=info.bare_code,
        timezone=info.timezone,
    )
    override = config.INDEX_OVERRIDES.get(info.symbol)
    if override is not None:
        dto.display_name = override.display_name
        dto.market_cn = override.market_cn
    if probe:
        try:
            price_data = default_provider().fetch(info.symbol)
            dto.probe_ok = True
            dto.display_name = override.display_name if override else price_data.display_name
        except DataUnavailableError as exc:
            dto.probe_ok = False
            dto.probe_error = _classify_error(exc)
    return dto


_TIER_NEXT_STEP_CN = {
    TIER_EARLY_WATCH: "等待同一底部结构确认，再进入结构确认档。",
    TIER_STRUCTURE_CONFIRMED: "等待收盘站上 EMA20/SMA20 且两线同时向上。",
    TIER_JOINT_CONFIRMED: "等待日线或已完成周线长周期支持/改善。",
    TIER_LONG_TREND_IMPROVED: "已达最高档；继续管理 C 点、颜色和顶部风险。",
}


def _latest_tier_event(
    assessment: DailyAssessment,
    observation: StructureObservation,
):
    candidates = [
        event
        for event in assessment.active_events
        if event.rule_id == "ema20_reclaim_rising"
        and event.structure_id == observation.structure_id
        and event.lifecycle_id == observation.lifecycle_id
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda event: (
            int(event.evidence.get("tier_rank", 0)),
            event.available_date,
        ),
    )


def _current_tier_conditions(
    observation: StructureObservation,
    structure: StructureInstance,
    state: DayState,
) -> tuple[bool, list[str], list[str]]:
    """描述今天仍成立的原子条件，不回写/降级历史最高档。"""
    tier = observation.tier
    if tier is None:
        return False, [], ["本轮 EMA20 转强生命周期已关闭"]
    satisfied = ["本轮 EMA20 转强生命周期仍有效"]
    missing: list[str] = []

    structure_confirmed_now = (
        structure.confirmed_date is not None and structure.confirmed_date <= state.day
    )
    if structure_confirmed_now:
        satisfied.append("底部结构已确认")
    else:
        missing.append("底部结构尚未确认")

    if state.color.value == "green":
        satisfied.append("当前 LEI 为绿色")
    elif state.color.value == "gray":
        missing.append("当前转灰，短周期方向出现分歧")
    else:
        missing.append("当前不是绿色")

    if state.joint_confirmed_now:
        satisfied.append("EMA20/SMA20 今天共同向上")
    elif TIER_RANK[tier] >= TIER_RANK[TIER_JOINT_CONFIRMED]:
        missing.append("本轮曾达共同确认，但今天双均线共同确认已不成立")
    elif structure_confirmed_now:
        missing.append("等待 EMA20/SMA20 今天共同向上")

    if state.long_supportive:
        satisfied.append("日线或已完成周线长周期支持/改善")
    elif TIER_RANK[tier] >= TIER_RANK[TIER_LONG_TREND_IMPROVED]:
        missing.append("本轮曾达长周期改善档，但今天长周期支持已减弱")
    elif TIER_RANK[tier] >= TIER_RANK[TIER_JOINT_CONFIRMED]:
        missing.append("等待日线或已完成周线长周期支持/改善")

    if tier == TIER_EARLY_WATCH:
        current_confirmed = not structure_confirmed_now
    elif tier == TIER_STRUCTURE_CONFIRMED:
        current_confirmed = structure_confirmed_now and state.color.value == "green"
    elif tier == TIER_JOINT_CONFIRMED:
        current_confirmed = structure_confirmed_now and state.joint_confirmed_now
    else:
        current_confirmed = (
            structure_confirmed_now and state.joint_confirmed_now and state.long_supportive
        )
    return current_confirmed, satisfied, missing


def _build_trade_opportunities(result: AnalysisResult) -> list[TradeOpportunityDTO]:
    if not result.history:
        return []
    state = result.history[-1]
    structures = {structure.structure_id: structure for structure in result.structures}
    close = float(result.frame["close"].iloc[-1]) if len(result.frame) else None
    opportunities: list[TradeOpportunityDTO] = []

    for observation in sorted(
        state.observations.values(),
        key=lambda item: (TIER_RANK.get(item.tier or "", 0), item.last_upgraded_on),
        reverse=True,
    ):
        if not observation.is_active or observation.tier is None:
            continue
        structure = structures.get(observation.structure_id)
        if structure is None or not structure.is_live:
            continue
        current_confirmed, satisfied, missing = _current_tier_conditions(
            observation, structure, state
        )
        tier = observation.tier
        buy_reference = tier != TIER_EARLY_WATCH
        if not buy_reference:
            opportunity_state, opportunity_state_cn = "watch", "观察"
        elif current_confirmed:
            opportunity_state, opportunity_state_cn = "confirmed", "条件确认"
        else:
            opportunity_state, opportunity_state_cn = "weakened", "确认减弱"
        latest_event = _latest_tier_event(result.assessment, observation)
        sub_rule = SUB_RULE_BY_TIER[tier]

        opportunities.append(
            TradeOpportunityDTO(
                state=opportunity_state,
                state_cn=opportunity_state_cn,
                structure=structure_brief(structure, close=close),
                lifecycle_id=observation.lifecycle_id,
                reached_tier=tier,
                reached_tier_cn=labels.TIER_CN.get(tier, tier),
                reached_tier_rank=TIER_RANK[tier],
                opened_on=observation.opened_on.isoformat(),
                last_upgraded_on=observation.last_upgraded_on.isoformat(),
                is_buy_reference=buy_reference,
                current_conditions_confirmed=current_confirmed,
                satisfied_conditions=satisfied,
                missing_conditions=missing,
                next_step_cn=_TIER_NEXT_STEP_CN[tier],
                invalidation_cn=(
                    "颜色转黑关闭本轮转强生命周期；底部触及或跌破 C 点永久失效。"
                ),
                b1_price=result.assessment.b1_price,
                distance_to_b1_pct=result.assessment.distance_to_b1_pct,
                explanation=to_explanation_dto(
                    lookup(rule_id="ema20_reclaim_rising", sub_rule=sub_rule)
                ),
                supporting_event=(
                    event_dto(latest_event, as_of=result.assessment.as_of)
                    if latest_event is not None
                    else None
                ),
            )
        )
    return opportunities


def _build_pullback_opportunities(result: AnalysisResult) -> list[PullbackOpportunityDTO]:
    """模块 A（V2，first_ma_pullback 3.x）回撤机会卡。

    V2 语义：每个 (趋势生命周期, 均线, 触碰日) 是一个独立回撤周期；卡片展示
    仍未失败周期的当前条件（时钟二类 / SMA 排列与方向 / 周线环境 / A4 触发态）。
    """
    if result.frame.empty:
        return []
    last_day = result.frame.index[-1].date()
    row = result.frame.iloc[-1]
    spec = get_rule("first_ma_pullback")
    distance_atr = float(spec.param("ma_touch_distance_atr", 1.0))
    atr_period = int(spec.param("ma_touch_atr_period", 20))
    atr20 = average_true_range(result.frame, atr_period)
    atr20_last = atr20.iloc[-1]
    clock2_now = int(clock_series(result.frame).iloc[-1]) == TYPE2_STEADY_UP
    weekly_now = bool(weekly_env_series(result.frame).iloc[-1])
    events = [event for event in result.events if event.rule_id == "first_ma_pullback"]
    by_scope: dict[tuple[str, int, str], list] = {}
    for event in events:
        lifecycle_id = event.lifecycle_id
        period = int(event.evidence.get("ma_period", 0))
        touch_day = str(event.evidence.get("touch_date") or event.available_date.isoformat())
        if lifecycle_id is None or period not in (20, 60, 120):
            continue
        by_scope.setdefault((lifecycle_id, period, touch_day), []).append(event)

    opportunities: list[PullbackOpportunityDTO] = []
    for (lifecycle_id, period, _touch_day), group in by_scope.items():
        ordered = sorted(group, key=lambda event: (event.available_date, event.event_id))
        touched = next(
            (event for event in ordered if event.evidence.get("sub_rule") == PULLBACK_TOUCHED),
            None,
        )
        confirmed = next(
            (
                event
                for event in ordered
                if event.evidence.get("sub_rule") == PULLBACK_CONFIRMED
            ),
            None,
        )
        failed = next(
            (event for event in ordered if event.evidence.get("sub_rule") == PULLBACK_FAILED),
            None,
        )
        if touched is None or failed is not None:
            continue

        ma_value = float(row[f"sma{period}"])
        close = float(row["close"])
        close_lag = row.get(f"close_lag{period}")
        atr20_value = (
            float(atr20_last) if pd.notna(atr20_last) and atr20_last > 0 else None
        )
        band = (
            ma_value + distance_atr * atr20_value
            if atr20_value is not None
            else ma_value
        )
        arrangement = bool(float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"]))
        ma_rising = (
            pd.notna(close_lag) and close > float(close_lag)
        )
        in_zone = close <= band
        current_holds = arrangement and ma_rising and clock2_now and weekly_now

        # 已入场的周期只在环境条件至今仍成立时持续展示；历史事件保留在事件日志与回测中。
        if confirmed is not None and not current_holds:
            continue

        state = "confirmed" if confirmed is not None else "watch"
        is_first = bool(touched.evidence.get("is_first_touch", False))
        satisfied: list[str] = ["完整多头排列保持"] if arrangement else []
        missing: list[str] = []
        if clock2_now:
            satisfied.append("日线时钟二类（稳定上涨）")
        else:
            missing.append("日线时钟不在二类（门禁阻断新入场）")
        if weekly_now:
            satisfied.append("周线多头环境")
        else:
            missing.append("周线多头环境不成立")
        if ma_rising:
            satisfied.append(f"SMA{period} 仍处上行方向（抵扣价判据）")
        else:
            missing.append(f"SMA{period} 不再上行")
        if confirmed is None and in_zone:
            satisfied.append("价格仍在回撤触碰带内")
        elif confirmed is None:
            missing.append("收盘已离开回撤触碰带（周期将结束）")

        anchor_date = lifecycle_id.rsplit(":", 1)[-1]
        source_event = confirmed or touched
        sub_rule = PULLBACK_CONFIRMED if confirmed is not None else PULLBACK_TOUCHED
        entry_variant = str(confirmed.evidence.get("entry_variant", "")) if confirmed else ""
        stop_price = (
            confirmed or touched
        ).evidence.get("stop_price")
        opportunities.append(
            PullbackOpportunityDTO(
                state=state,
                state_cn=(
                    f"入场信号（A4 { '早期版' if entry_variant == 'early' else '确认版' }）"
                    if confirmed is not None
                    else ("首次触碰待入场" if is_first else "非首次触碰待入场")
                ),
                ma_period=period,
                ma_name=f"SMA{period}",
                lifecycle_id=lifecycle_id,
                trend_anchor_date=anchor_date,
                touch_date=touched.available_date.isoformat(),
                confirmed_date=confirmed.available_date.isoformat() if confirmed else None,
                latest_date=last_day.isoformat(),
                ma_value=ma_value,
                close=close,
                distance_to_ma_pct=(close / ma_value - 1.0) * 100.0,
                current_conditions_confirmed=current_holds if confirmed is not None else False,
                satisfied_conditions=satisfied,
                missing_conditions=missing,
                next_step_cn=(
                    "持仓以 A5 结构低点为失效价，按退出规则管理（A6 三版见回测分组）。"
                    if confirmed is not None
                    else (
                        "等待 A3（底部构造或 EMA20 收复）+ A4（站上 EMA20 且 EMA20 上行）触发；"
                        "收盘跌破本轮回撤低点则周期失败。"
                    )
                ),
                invalidation_cn=(
                    f"收盘跌破本轮回撤结构低点"
                    f"（{f'{stop_price:.2f}' if stop_price is not None else '见事件 stop_price'}）"
                    f"，或趋势生命周期重置（SMA 排列破坏/跌破 SMA120/转黑）。"
                ),
                explanation=to_explanation_dto(
                    lookup(rule_id="first_ma_pullback", sub_rule=sub_rule)
                ),
                supporting_event=event_dto(source_event, as_of=result.assessment.as_of),
                **_rr_fields(result, confirmed),
            )
        )
    return sorted(
        opportunities,
        key=lambda item: (item.state != "confirmed", item.ma_period),
    )


def _alignment_kind(row: pd.Series) -> str | None:  # noqa: ANN001
    if (
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and float(row["sma20_slope"]) > 0
        and float(row["sma60_slope"]) > 0
        and float(row["sma120_slope"]) > 0
    ):
        return "bullish"
    if (
        float(row["sma20"]) < float(row["sma60"]) < float(row["sma120"])
        and float(row["sma20_slope"]) < 0
        and float(row["sma60_slope"]) < 0
        and float(row["sma120_slope"]) < 0
    ):
        return "bearish"
    return None


def _fo_scenario(result: AnalysisResult) -> ConditionalScenarioDTO | None:
    spec = get_rule(FO_RULE_ID)
    window = int(spec.param("reclaim_window"))
    require_green = bool(spec.param("require_green"))
    events = [e for e in result.events if e.rule_id == FO_RULE_ID]
    if not events:
        return None
    last = result.frame.iloc[-1]
    last_day = result.frame.index[-1].date()
    arrangement = float(last["sma20"]) > float(last["sma60"]) > float(last["sma120"])
    green = str(last["signal_color"]) == "green"
    candidates: list[ConditionalScenarioDTO] = []
    by_lc: dict[str, list] = {}
    for event in events:
        by_lc.setdefault(event.lifecycle_id or "", []).append(event)
    for group in by_lc.values():
        ordered = sorted(group, key=lambda e: e.available_date)
        latest = ordered[-1]
        if latest.evidence.get("sub_rule") == FO_FAILED:
            continue
        watch = next((e for e in ordered if e.evidence.get("sub_rule") == FO_WATCH), None)
        if watch is None:
            continue
        confirmed = next((e for e in ordered if e.evidence.get("sub_rule") == FO_CONFIRMED), None)
        ref = float(watch.evidence.get("reference_price") or 0.0)
        price_holds = float(last["close"]) >= ref
        if confirmed is not None:
            if not (arrangement and (not require_green or green) and price_holds):
                continue
            state, state_cn = "confirmed", "条件确认"
        else:
            bars_since = (
                sum(
                    1
                    for ts in result.frame.index
                    if watch.available_date <= ts.date() <= last_day
                )
                - 1
            )
            if bars_since >= window:
                continue
            state, state_cn = "watch", "被打回待收回"
        satisfied = ["完整多头排列保持"] if arrangement else []
        missing: list[str] = []
        if green or not require_green:
            satisfied.append("当前 LEI 为绿色")
        else:
            missing.append("当前 LEI 不是绿色")
        if price_holds:
            satisfied.append("收盘仍在参考位上方")
        else:
            missing.append("收盘已跌破参考位")
        source = confirmed or watch
        sub = FO_CONFIRMED if confirmed is not None else FO_WATCH
        candidates.append(
            ConditionalScenarioDTO(
                scenario_id=FO_RULE_ID,
                scenario_cn="假突破快速收回",
                direction="long",
                direction_cn="潜在做多",
                state=state,
                state_cn=state_cn,
                anchor_date=str(watch.evidence.get("breakout_date", "")),
                trigger_date=watch.available_date.isoformat(),
                latest_date=last_day.isoformat(),
                key_price=ref,
                reference_price=ref,
                distance_pct=(float(last["close"]) / ref - 1.0) * 100.0 if ref else None,
                current_conditions_confirmed=state == "confirmed",
                satisfied_conditions=satisfied,
                missing_conditions=missing,
                next_step_cn=(
                    "继续管理完整多头排列、转黑与参考位得失。"
                    if state == "confirmed"
                    else f"等待最多 {window} 根已完成日 K 内重新站回参考位上方且趋势保持。"
                ),
                invalidation_cn="收盘真跌破参考位、完整多头排列破坏、转黑或确认窗口耗尽。",
                caveat_cn="研究代理：源自用户交易笔记，以日线 OHLC 判定，不冒充 LEI 原始规则。",
                explanation=to_explanation_dto(lookup(rule_id=FO_RULE_ID, sub_rule=sub)),
                supporting_event=event_dto(source, as_of=result.assessment.as_of),
                **_rr_fields(result, confirmed),
            )
        )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda c: (c.state == "confirmed", c.trigger_date or ""),
    )


def _fo_short_scenario(result: AnalysisResult) -> ConditionalScenarioDTO | None:
    """假突破做空镜像场景（方向=short，研究代理·骨架）。

    与 _fo_scenario 同源(rule_id)但仅取做空子规则；trend_following 关系上
    属于 D 模块，与做多侧 D 分桶隔离，不在同一笔交易中改写理由。
    """
    spec = get_rule(FO_RULE_ID)
    window = int(spec.param("reclaim_window"))
    short_sub_rules = {FO_SHORT_WATCH, FO_SHORT_CONFIRMED, FO_SHORT_FAILED}
    short_events = [
        e for e in result.events
        if e.rule_id == FO_RULE_ID and e.evidence.get("sub_rule") in short_sub_rules
    ]
    if not short_events:
        return None
    last = result.frame.iloc[-1]
    last_day = result.frame.index[-1].date()
    arrangement = float(last["sma20"]) < float(last["sma60"]) < float(last["sma120"])
    candidates: list[ConditionalScenarioDTO] = []
    by_lc: dict[str, list] = {}
    for event in short_events:
        by_lc.setdefault(event.lifecycle_id or "", []).append(event)
    for group in by_lc.values():
        ordered = sorted(group, key=lambda e: e.available_date)
        latest = ordered[-1]
        if latest.evidence.get("sub_rule") == FO_SHORT_FAILED:
            continue
        watch = next((e for e in ordered if e.evidence.get("sub_rule") == FO_SHORT_WATCH), None)
        if watch is None:
            continue
        confirmed = next(
            (e for e in ordered if e.evidence.get("sub_rule") == FO_SHORT_CONFIRMED), None
        )
        ref = float(watch.evidence.get("reference_price") or 0.0)
        price_below = float(last["close"]) < ref
        if confirmed is not None:
            if not (arrangement and price_below):
                continue
            state, state_cn = "confirmed", "做空确认"
        else:
            bars_since = (
                sum(
                    1 for ts in result.frame.index
                    if watch.available_date <= ts.date() <= last_day
                ) - 1
            )
            if bars_since >= window:
                continue
            state, state_cn = "watch", "拉回待确认做空"
        satisfied = ["完整空头排列保持"] if arrangement else []
        missing: list[str] = []
        if price_below:
            satisfied.append("收盘仍在压力位下方")
        else:
            missing.append("收盘已站回压力位上方")
        source = confirmed or watch
        sub = FO_SHORT_CONFIRMED if confirmed is not None else FO_SHORT_WATCH
        candidates.append(
            ConditionalScenarioDTO(
                scenario_id=FO_RULE_ID,
                scenario_cn="假突破做空镜像",
                direction="short",
                direction_cn="潜在做空",
                state=state,
                state_cn=state_cn,
                anchor_date=str(watch.evidence.get("breakout_date", "")),
                trigger_date=watch.available_date.isoformat(),
                latest_date=last_day.isoformat(),
                key_price=ref,
                reference_price=ref,
                distance_pct=(float(last["close"]) / ref - 1.0) * 100.0 if ref else None,
                current_conditions_confirmed=state == "confirmed",
                satisfied_conditions=satisfied,
                missing_conditions=missing,
                next_step_cn=(
                    "做空条件已确认；继续管理空头排列、SMA20 方向与压力位得失。"
                    if state == "confirmed"
                    else f"等待最多 {window} 根已完成日 K 内收盘拉回压力位下方、SMA20 方向下行。"
                ),
                invalidation_cn=(
                    "重新强势站上压力位、完整空头排列破坏、SMA20 重新上行，或确认窗口耗尽。"
                ),
                caveat_cn=(
                    "研究代理·骨架：做空镜像接口，参数沿用做多侧默认值并标注待确认，"
                    "不冒充 LEI 原始做空标准；跌用绿色（A 股惯例）。"
                ),
                explanation=to_explanation_dto(lookup(rule_id=FO_RULE_ID, sub_rule=sub)),
                supporting_event=event_dto(source, as_of=result.assessment.as_of),
            )
        )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda c: (c.state == "confirmed", c.trigger_date or ""),
    )


def _ll_scenario(result: AnalysisResult) -> ConditionalScenarioDTO | None:
    spec = get_rule(LL_RULE_ID)
    window = int(spec.param("confirmation_window"))
    events = [e for e in result.events if e.rule_id == LL_RULE_ID]
    if not events:
        return None
    last = result.frame.iloc[-1]
    last_day = result.frame.index[-1].date()
    arrangement = float(last["sma20"]) > float(last["sma60"]) > float(last["sma120"])
    green = str(last["signal_color"]) == "green"
    candidates: list[ConditionalScenarioDTO] = []
    by_lc: dict[str, list] = {}
    for event in events:
        by_lc.setdefault(event.lifecycle_id or "", []).append(event)
    for group in by_lc.values():
        ordered = sorted(group, key=lambda e: e.available_date)
        latest = ordered[-1]
        if latest.evidence.get("sub_rule") not in (LL_WATCH, LL_CONFIRMED):
            continue
        watch = next((e for e in ordered if e.evidence.get("sub_rule") == LL_WATCH), None)
        if watch is None:
            continue
        confirmed = next((e for e in ordered if e.evidence.get("sub_rule") == LL_CONFIRMED), None)
        ref = float(watch.evidence.get("reference_price") or 0.0)
        price_holds = float(last["close"]) >= ref
        trigger_holds = arrangement and green and price_holds
        if confirmed is not None:
            if not trigger_holds:
                continue
            state, state_cn = "confirmed", "次级别确认"
        else:
            bars_since = (
                sum(
                    1
                    for ts in result.frame.index
                    if watch.available_date <= ts.date() <= last_day
                )
                - 1
            )
            if bars_since >= window or not trigger_holds:
                continue
            state, state_cn = "watch", "等待次级别确认"
        satisfied = ["完整多头排列保持"] if arrangement else []
        missing: list[str] = []
        if green:
            satisfied.append("当前 LEI 为绿色")
        else:
            missing.append("当前 LEI 不是绿色")
        if price_holds:
            satisfied.append("收盘仍在参考支撑上方")
        else:
            missing.append("收盘已跌破参考支撑")
        source = confirmed or watch
        sub = LL_CONFIRMED if confirmed is not None else LL_WATCH
        candidates.append(
            ConditionalScenarioDTO(
                scenario_id=LL_RULE_ID,
                scenario_cn="次级别确认（日线代理）",
                direction="long",
                direction_cn="潜在做多",
                state=state,
                state_cn=state_cn,
                anchor_date=watch.available_date.isoformat(),
                trigger_date=watch.available_date.isoformat(),
                latest_date=last_day.isoformat(),
                key_price=ref,
                reference_price=ref,
                distance_pct=(float(last["close"]) / ref - 1.0) * 100.0 if ref else None,
                current_conditions_confirmed=state == "confirmed",
                satisfied_conditions=satisfied,
                missing_conditions=missing,
                next_step_cn=(
                    "日线信号已获次级别确认；继续管理排列、转黑与参考支撑。"
                    if state == "confirmed"
                    else f"等待最多 {window} 根已完成日 K 内出现盘中收回或反转 K 线。"
                ),
                invalidation_cn="日线做多信号失效（排列/双均线共同确认不再成立）或收盘跌破参考支撑。",
                caveat_cn=(
                    "研究代理：以日线 OHLC 代理 60 分钟次级别确认，系统未接入真 60 分钟数据，"
                    "不冒充 LEI 原始规则。"
                ),
                explanation=to_explanation_dto(lookup(rule_id=LL_RULE_ID, sub_rule=sub)),
                supporting_event=event_dto(source, as_of=result.assessment.as_of),
            )
        )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda c: (c.state == "confirmed", c.trigger_date or ""),
    )


def _alignment_scenario(result: AnalysisResult) -> ConditionalScenarioDTO | None:
    last = result.frame.iloc[-1]
    last_day = result.frame.index[-1].date()
    kind = _alignment_kind(last)
    slope_accel = ema_slope_accel_for_frame(result.frame)
    events = [e for e in result.events if e.rule_id == AL_RULE_ID]
    ordered = sorted(events, key=lambda e: e.available_date)
    latest_start = None
    for event in ordered:
        sub = event.evidence.get("sub_rule")
        if sub in (AL_BULLISH, AL_BEARISH):
            latest_start = event
        elif sub == AL_BROKEN:
            latest_start = None
    if latest_start is not None:
        anchor_date = latest_start.available_date.isoformat()
        direction = "long" if latest_start.evidence.get("alignment_kind") == "bullish" else "short"
    else:
        anchor_date = last_day.isoformat()
        direction = "long" if kind == "bullish" else "short"
    if kind is None:
        state, state_cn = "invalidated", "排列已破坏"
    else:
        state, state_cn = "confirmed", "排列成立"
    satisfied: list[str] = []
    missing: list[str] = []
    if kind == "bullish":
        satisfied.append("SMA20>SMA60>SMA120 且三条 SMA 方向均向上")
    elif kind == "bearish":
        satisfied.append("SMA20<SMA60<SMA120 且三条 SMA 方向均向下")
    else:
        missing.append("当前不完整多头/空头排列")
    slope_note = ""
    if slope_accel is not None:
        slope_note = (
            f"；EMA20 斜率 {slope_accel['ema20_slope_pct']:.2f}%，"
            f"加速度 {slope_accel['ema20_accel_pct']:.2f}%"
        )
        if slope_accel["ema20_accel_pct"] > 0:
            satisfied.append("EMA20 动能加速")
        elif slope_accel["ema20_accel_pct"] < 0:
            missing.append("EMA20 动能减速")
    sub = (
        AL_BULLISH
        if kind == "bullish"
        else AL_BEARISH
        if kind == "bearish"
        else AL_BROKEN
    )
    return ConditionalScenarioDTO(
        scenario_id=AL_RULE_ID,
        scenario_cn="完整均线排列 + EMA 斜率加速度",
        direction=direction,
        direction_cn="潜在做多" if direction == "long" else "潜在做空",
        state=state,
        state_cn=state_cn,
        anchor_date=anchor_date,
        trigger_date=anchor_date,
        latest_date=last_day.isoformat(),
        key_price=float(last["ema20"]) if "ema20" in result.frame.columns else float(last["close"]),
        reference_price=None,
        distance_pct=None,
        current_conditions_confirmed=kind is not None,
        satisfied_conditions=satisfied,
        missing_conditions=missing,
        next_step_cn=(
            "作为场景卡底层确认维度；结合颜色、结构与回撤管理风险。"
            + slope_note
        ),
        invalidation_cn="均线相对位置或方向不再满足完整排列（多头/空头）。",
        caveat_cn="研究代理：源自用户交易笔记，斜率/加速度为标准化代理指标，不冒充 LEI 原始规则。",
        explanation=to_explanation_dto(lookup(rule_id=AL_RULE_ID, sub_rule=sub)),
        supporting_event=(
            event_dto(latest_start, as_of=result.assessment.as_of)
            if latest_start is not None
            else None
        ),
    )


def _dense_breakout_scenario(result: AnalysisResult) -> ConditionalScenarioDTO | None:
    """均线密集区突破场景卡（模块 B，研究代理）。

    key_price / reference_price 优先用「最近 N 日 high 的滚动上沿」
    （规则规格 dense_recompute_lookback，默认 90），回退到事件里的
    locked ref (B1 横盘时锁定的 breakout_reference)。locked ref 仍
    通过 caveat_cn 透出，避免静默丢失旧锚点信息。
    """
    events = [e for e in result.events if e.rule_id == DB_RULE_ID]
    if not events:
        return None
    last = result.frame.iloc[-1]
    last_day = result.frame.index[-1].date()
    close = float(last["close"])
    arrangement = float(last["sma20"]) > float(last["sma60"]) > float(last["sma120"])
    db_spec = get_rule(DB_RULE_ID)
    recompute_lookback = int(db_spec.param("dense_recompute_lookback", 90))
    recent_upper = _db_recent_upper(result.frame, recompute_lookback)
    candidates: list[ConditionalScenarioDTO] = []
    by_lc: dict[str, list] = {}
    for event in events:
        by_lc.setdefault(event.lifecycle_id or "", []).append(event)
    for group in by_lc.values():
        ordered = sorted(group, key=lambda e: e.available_date)
        if ordered[-1].evidence.get("sub_rule") == DB_FAILED:
            continue
        watch = next((e for e in ordered if e.evidence.get("sub_rule") == DB_WATCH), None)
        if watch is None:
            continue
        confirmed = next(
            (e for e in ordered if e.evidence.get("sub_rule") == DB_CONFIRMED), None
        )
        if confirmed is not None:
            locked_ref = float(confirmed.evidence.get("breakout_reference")
                               or watch.evidence.get("reference_price") or 0.0)
        else:
            locked_ref = float(watch.evidence.get("reference_price") or 0.0)
        if locked_ref <= 0:
            continue
        # key_price 走「当前密集区上沿」, 即近期 high 滚动值;
        # 拿不到再回退到 locked_ref。两种 ref 同时存在, locked_ref 通过 caveat 透传。
        ref = recent_upper if recent_upper is not None else locked_ref
        if ref <= 0:
            continue
        price_holds = close >= ref
        if confirmed is not None:
            if not (arrangement and price_holds):
                continue
            state, state_cn = "confirmed", "条件确认"
        else:
            state, state_cn = "watch", "横盘待突破"
        satisfied = ["完整多头排列保持"] if arrangement else []
        missing: list[str] = []
        if price_holds:
            satisfied.append(f"收盘仍在当前密集区上沿 ({ref:.2f}) 上方")
        else:
            missing.append(f"收盘未站上当前密集区上沿 ({ref:.2f})")
        if not arrangement:
            missing.append("完整多头排列未成立")
        source = confirmed or watch
        sub = DB_CONFIRMED if confirmed is not None else DB_WATCH
        # caveat 同时透出当前 dense upper 和原始 locked ref (B1 锁定值),
        # 避免只看到当前 dense upper 而不知道 B1 当初是基于哪个价位判定的。
        # 区间下沿也透出, 用户常把「上沿」和「下沿」搞混, 给一个完整 range 更直观。
        recent_window = (
            result.frame.iloc[-recompute_lookback:]
            if len(result.frame) >= recompute_lookback
            else result.frame
        )
        recent_low = float(recent_window["low"].min()) if not recent_window.empty else None
        if recent_upper is not None and recent_low is not None:
            range_note = (
                f"近 {recompute_lookback} 日 high {recent_upper:.2f} / low {recent_low:.2f}"
            )
        else:
            range_note = ""
        if recent_upper is not None and abs(recent_upper - locked_ref) > 0.01:
            fallback_note = f"近 {recompute_lookback} 日 high 滚动"
            ref_note = (
                f"当前密集区上沿 {recent_upper:.2f}（{range_note or fallback_note}）"
                f"；原始锁定参考 {locked_ref:.2f}（B1 观察时锁定的密集区上沿，"
                f"已脱节，仅作历史参考）"
            )
        else:
            ref_note = f"密集区上沿 {ref:.2f}"
        candidates.append(
            ConditionalScenarioDTO(
                scenario_id=DB_RULE_ID,
                scenario_cn="均线密集区突破",
                direction="long",
                direction_cn="潜在做多",
                state=state,
                state_cn=state_cn,
                anchor_date=watch.available_date.isoformat(),
                trigger_date=watch.available_date.isoformat(),
                latest_date=last_day.isoformat(),
                key_price=ref,
                reference_price=ref,
                distance_pct=(close / ref - 1.0) * 100.0 if ref else None,
                current_conditions_confirmed=state == "confirmed",
                satisfied_conditions=satisfied,
                missing_conditions=missing,
                next_step_cn=(
                    "继续管理完整多头排列、转黑与密集区上沿得失。"
                    if state == "confirmed"
                    else "等待收盘突破密集区上沿且完整多头排列成立。"
                ),
                invalidation_cn=(
                    f"收盘跌回当前密集区上沿 ({ref:.2f}) 下方且 SMA20 方向向下弯曲、"
                    "完整多头排列破坏或转黑。"
                ),
                caveat_cn=(
                    f"研究代理：源自规格 §9 模块 B；{ref_note}。"
                    "横盘阈值复用 tradability_gate（V2 §17 已定（原则）：2%/126 交易日），"
                    "不冒充 LEI 原始规则。"
                ),
                explanation=to_explanation_dto(lookup(rule_id=DB_RULE_ID, sub_rule=sub)),
                supporting_event=event_dto(source, as_of=result.assessment.as_of),
                **_rr_fields(result, confirmed),
            )
        )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda c: (c.state == "confirmed", c.trigger_date or ""),
    )


_TB_VERSION_RANK = {TB_V1: 1, TB_V2: 2, TB_V3: 3}
_TB_VERSION_CN = {TB_V1: "v1", TB_V2: "v2", TB_V3: "v3"}


def _two_b_reversal_scenario(result: AnalysisResult) -> ConditionalScenarioDTO | None:
    """2B/破底翻场景卡（模块 C，研究代理）。取最新活跃结构的最高版本确认。"""
    events = [e for e in result.events if e.rule_id == TB_RULE_ID]
    if not events:
        return None
    last = result.frame.iloc[-1]
    last_day = result.frame.index[-1].date()
    close = float(last["close"])
    ranked: list[tuple[int, str, ConditionalScenarioDTO]] = []
    by_lc: dict[str, list] = {}
    for event in events:
        by_lc.setdefault(event.lifecycle_id or "", []).append(event)
    for group in by_lc.values():
        ordered = sorted(group, key=lambda e: e.available_date)
        if any(e.evidence.get("sub_rule") == TB_FAILED for e in ordered):
            continue
        confirmed_events = [
            e for e in ordered if e.evidence.get("sub_rule") in _TB_VERSION_RANK
        ]
        if not confirmed_events:
            continue
        best = max(
            confirmed_events, key=lambda e: _TB_VERSION_RANK[e.evidence["sub_rule"]]
        )
        l1 = float(best.evidence.get("l1_price") or 0.0)
        l2 = float(best.evidence.get("l2_price") or 0.0)
        if l1 <= 0 or l2 <= 0:
            continue
        sub_rule = best.evidence["sub_rule"]
        version = _TB_VERSION_CN[sub_rule]
        price_holds = close >= l1
        not_failed = close > l2
        if not (price_holds and not_failed):
            continue
        satisfied = [f"收盘站上 L1({l1:.2f})", f"收盘未跌破 L2({l2:.2f})"]
        candidates_dto = ConditionalScenarioDTO(
            scenario_id=TB_RULE_ID,
            scenario_cn=f"2B/破底翻·{version}",
            direction="long",
            direction_cn="潜在做多",
            state="confirmed",
            state_cn=f"2B·{version}确认",
            anchor_date=str(best.evidence.get("breakout_date", "")),
            trigger_date=best.available_date.isoformat(),
            latest_date=last_day.isoformat(),
            key_price=l1,
            reference_price=l2,
            distance_pct=(close / l1 - 1.0) * 100.0 if l1 else None,
            current_conditions_confirmed=True,
            satisfied_conditions=satisfied,
            missing_conditions=[],
            next_step_cn="继续管理 L2 失效线；跌破 L2 即 2B 彻底失效。",
            invalidation_cn=f"收盘跌破 L2({l2:.4f})，2B 结构彻底失效。",
            caveat_cn=(
                "研究代理：V2 规格 §9 C1 已填实结构定义，代码仍为 v1 L1/L2 口径"
                "（pending_v2 重写排期）；two_b_reclaim_bars=5〔标定 V2.1，待彪哥确认〕，"
                "不冒充 LEI 原始规则。"
            ),
            explanation=to_explanation_dto(lookup(rule_id=TB_RULE_ID, sub_rule=sub_rule)),
            supporting_event=event_dto(best, as_of=result.assessment.as_of),
            **_rr_fields(result, best),
        )
        ranked.append((_TB_VERSION_RANK[sub_rule], best.available_date.isoformat(), candidates_dto))
    if not ranked:
        return None
    return max(ranked, key=lambda item: (item[0], item[1]))[2]


def _build_conditional_scenarios(result: AnalysisResult) -> list[ConditionalScenarioDTO]:
    if result.frame.empty:
        return []
    scenarios: list[ConditionalScenarioDTO] = []
    for builder in (
        _fo_scenario,
        _fo_short_scenario,
        _ll_scenario,
        _alignment_scenario,
        _dense_breakout_scenario,
        _two_b_reversal_scenario,
    ):
        scenario = builder(result)
        if scenario is not None:
            scenarios.append(scenario)
    return scenarios


def _build_exit_signals(result: AnalysisResult) -> list[ExitSignalDTO]:
    """持仓退出状态（研究代理）：当前退出条件是否成立 + 最近一次触发。

    只展示退出规则的当前状态与最近触发事件，不输出自动卖出指令。
    """
    if result.frame.empty:
        return []
    last_row = result.frame.iloc[-1]
    exit_events = [e for e in result.events if e.rule_id == EXIT_RULE_ID]
    ordered = sorted(exit_events, key=lambda e: e.available_date)
    last_trigger = ordered[-1] if ordered else None
    sub_rule = last_trigger.evidence.get("sub_rule") if last_trigger else None

    spec = get_rule(EXIT_RULE_ID)
    period = int(spec.param("costbasis_period", 20))
    costbasis_col = f"close_lag{period}"
    close = last_row.get("close")
    ema20 = last_row.get("ema20")
    lag = last_row.get(costbasis_col)
    has_values = (
        close is not None
        and ema20 is not None
        and lag is not None
        and pd.notna(close)
        and pd.notna(ema20)
        and pd.notna(lag)
    )
    if has_values:
        close_f, ema20_f, lag_f = float(close), float(ema20), float(lag)
        active = close_f < ema20_f and close_f < lag_f
        reference_values = {
            "ema20": ema20_f,
            f"close_lag{period}": lag_f,
            "distance_to_ema20_pct": (close_f / ema20_f - 1.0) * 100.0,
            "distance_to_costbasis_pct": (close_f / lag_f - 1.0) * 100.0,
        }
    else:
        close_f = None
        active = False
        reference_values = {}

    state, state_cn = ("active", "退出条件当前成立") if active else (
        "inactive",
        "退出条件当前不成立",
    )
    return [
        ExitSignalDTO(
            rule_id=EXIT_RULE_ID,
            rule_cn=labels.RULE_CN.get(EXIT_RULE_ID, EXIT_RULE_ID),
            sub_rule=sub_rule,
            sub_rule_cn=labels.SUB_RULE_CN.get(sub_rule) if sub_rule else None,
            direction="bearish",
            direction_cn=labels.DIRECTION_CN.get("bearish", "偏空"),
            state=state,
            state_cn=state_cn,
            last_trigger_date=(
                last_trigger.available_date.isoformat() if last_trigger else None
            ),
            close=close_f,
            reference_values=reference_values,
            reason_cn=(
                "持仓退出参考：收盘同时跌破 EMA20 与 "
                f"{period} 日抵扣价即触发（A6①），下一交易日开盘退出"
            ),
            invalidation_cn="退出触发为单次事件，不因后续价格回升而回溯改写。",
            research_proxy=True,
            explanation=to_explanation_dto(lookup(rule_id=EXIT_RULE_ID, sub_rule=sub_rule)),
            supporting_event=(
                event_dto(last_trigger, as_of=result.assessment.as_of)
                if last_trigger is not None
                else None
            ),
        )
    ]


def _build_tradability(result: AnalysisResult) -> TradabilityDTO | None:
    """可交易性门禁（研究代理）：趋势类型 + 9 条无交易条件。只算展示不做硬拦截。"""
    if result.frame.empty:
        return None
    position = len(result.frame) - 1
    tr = evaluate_tradability(result.frame, position)
    return TradabilityDTO(
        trend_type=tr.trend_type,
        trend_type_cn=tr.trend_type_cn,
        tradable=tr.tradable,
        blocking_reasons=list(tr.blocking_reasons),
        condition_checks=[
            ConditionCheckDTO(
                code=c.code, label_cn=c.label_cn, blocked=c.blocked, detail_cn=c.detail_cn
            )
            for c in tr.condition_checks
        ],
        research_proxy=True,
        caveat_cn=(
            "研究代理：均线纠缠度+ATR分位+斜率分类，cluster_threshold=2%/"
            "minimum_consolidation_bars=126 已定（原则，V2 §17），acceleration/bias 为"
            " v1 判据、V2 时钟五类口径 pending_v2；多周期(条件7)用日线颜色翻转代理，"
            "60min 未接入。"
        ),
    )


def _rr_fields(result: AnalysisResult, entry_event: SignalEvent | None) -> dict:
    """盈亏比字段（研究代理，只算不强制）。entry_event 为入场确认事件。"""
    if entry_event is None:
        return {"reward_risk_computable": False}
    rr = compute_reward_risk(result.frame, entry_event, result.pivots)
    return {
        "reward_risk_ratio": rr.reward_risk,
        "reward_risk_target": rr.target_b,
        "reward_risk_target_source_cn": TARGET_SOURCE_CN.get(
            rr.target_source, "目标不可计算"
        ),
        "reward_risk_computable": rr.computable,
    }


def _build_scenario_backtests(result: AnalysisResult) -> list[ScenarioBacktestDTO]:
    if result.frame.empty:
        return []
    # 2 参 builder：(frame, events)
    two_arg = [
        ("false_breakout_reclaim", "假突破快速收回", build_false_breakout_backtest),
        ("ma_full_alignment", "完整均线排列", build_alignment_backtest),
        ("low_level_confirmation", "次级别确认（日线代理）", build_low_level_backtest),
        ("exit_variants", "模块A持仓退出（A6三版本）", build_exit_variant_backtest),
        ("module_groups", "按交易模块分组（A/B/C/D）", build_module_backtest),
    ]
    out: list[ScenarioBacktestDTO] = []
    for scenario_id, scenario_cn, build in two_arg:
        report = build(result.frame, result.events)
        if report is not None:
            out.append(_scenario_dto(scenario_id, scenario_cn, report))
    rr_report = build_reward_risk_backtest(result.frame, result.events, result.pivots)
    if rr_report is not None:
        out.append(_scenario_dto("reward_risk", "盈亏比分桶（只算不强制）", rr_report))
    return out


def _scenario_dto(
    scenario_id: str, scenario_cn: str, report: ScenarioBacktestReport
) -> ScenarioBacktestDTO:
    return ScenarioBacktestDTO(
        scenario_id=scenario_id,
        scenario_cn=scenario_cn,
        start_date=report.start_date,
        end_date=report.end_date,
        total_bars=report.total_bars,
        research_disclaimer_cn=report.research_disclaimer_cn,
        sides=[
            ScenarioBacktestSideDTO(
                key=side.key,
                title_cn=side.title_cn,
                entry_rule_cn=side.entry_rule_cn,
                exit_rule_cn=side.exit_rule_cn,
                total_signals=side.total_signals,
                open_trades=side.open_trades,
                stats=[
                    PullbackPerformanceDTO(
                        key=stat.key,
                        label_cn=stat.label_cn,
                        sample_count=stat.sample_count,
                        incomplete_count=stat.incomplete_count,
                        win_rate=stat.win_rate,
                        mean_return=stat.mean_return,
                        median_return=stat.median_return,
                        mean_mfe=stat.mean_mfe,
                        mean_mae=stat.mean_mae,
                        mean_holding_days=stat.mean_holding_days,
                    )
                    for stat in side.stats
                ],
            )
            for side in report.sides
        ],
    )


def _assessment_dto(result: AnalysisResult) -> AssessmentDTO:
    assessment = result.assessment
    return AssessmentDTO(
        as_of=assessment.as_of.isoformat(),
        color=assessment.color.value,
        color_cn=COLOR_CN.get(assessment.color.value, assessment.color.value),
        stage=assessment.stage.value,
        stage_cn=STAGE_CN.get(assessment.stage.value, assessment.stage.value),
        opportunity_stage=assessment.opportunity_stage.value,
        opportunity_stage_cn=STAGE_CN.get(
            assessment.opportunity_stage.value, assessment.opportunity_stage.value
        ),
        risk_state=assessment.risk_state.value,
        risk_state_cn=labels.RISK_STATE_CN.get(
            assessment.risk_state.value, assessment.risk_state.value
        ),
        stage_change_reason_cn=assessment.stage_change_reason_cn,
        dimensions=dict(assessment.dimensions),
        supports=[
            FactorDTO(
                dimension=f.dimension,
                label_cn=f.label_cn,
                detail_cn=f.detail_cn,
                rule_id=f.rule_id,
            )
            for f in assessment.supports
        ],
        conflicts=[
            FactorDTO(
                dimension=f.dimension,
                label_cn=f.label_cn,
                detail_cn=f.detail_cn,
                rule_id=f.rule_id,
            )
            for f in assessment.conflicts
        ],
        risks=[
            RiskAlertDTO(
                priority=r.priority,
                code=r.code,
                label_cn=r.label_cn,
                detail_cn=r.detail_cn,
            )
            for r in assessment.risks
        ],
        joint_confirmed_now=assessment.joint_confirmed_now,
        trade_opportunities=_build_trade_opportunities(result),
        pullback_opportunities=_build_pullback_opportunities(result),
        conditional_scenarios=_build_conditional_scenarios(result),
        exit_signals=_build_exit_signals(result),
        tradability=_build_tradability(result),
    )


def _color_backtest_dto(result: AnalysisResult) -> ColorBacktestDTO | None:
    report = build_color_backtest(result.frame)
    if report is None:
        return None

    def side_dto(side: ColorBacktestSide) -> ColorBacktestSideDTO:
        # report 的 dataclass 是内部研究对象；只在此处显式映射 API 边界。
        return ColorBacktestSideDTO(
            side=side.side,
            title_cn=side.title_cn,
            entry_rule_cn=side.entry_rule_cn,
            exit_rule_cn=side.exit_rule_cn,
            total_signals=side.total_signals,
            open_trades=side.open_trades,
            stats=[
                ColorPerformanceDTO(
                    key=stat.key,
                    label_cn=stat.label_cn,
                    sample_count=stat.sample_count,
                    win_rate=stat.win_rate,
                    mean_return=stat.mean_return,
                    median_return=stat.median_return,
                    mean_mfe=stat.mean_mfe,
                    mean_mae=stat.mean_mae,
                    mean_holding_days=stat.mean_holding_days,
                )
                for stat in side.stats
            ],
        )

    return ColorBacktestDTO(
        start_date=report.start_date,
        end_date=report.end_date,
        total_bars=report.total_bars,
        long=side_dto(report.long),
        short=side_dto(report.short),
        methodology_cn=(
            "固定周期为信号收盘后5/10/20/60/120个交易日；信号退出列中，做多于首次"
            "转灰或转黑时退出，做空于首次重新转绿时退出。每次翻色作为独立研究信号，"
            "观察窗口可以重叠；全部按当时可见收盘价计算，未计手续费、滑点、融券成本、"
            "涨跌停与停牌。"
        ),
    )


def _pullback_backtest_dto(result: AnalysisResult) -> PullbackBacktestDTO | None:
    report = build_first_ma_pullback_backtest(result.frame, result.events)
    if report is None:
        return None
    return PullbackBacktestDTO(
        start_date=report.start_date,
        end_date=report.end_date,
        total_bars=report.total_bars,
        research_disclaimer_cn=report.research_disclaimer_cn,
        sides=[
            PullbackBacktestSideDTO(
                ma_period=side.ma_period,
                title_cn=side.title_cn,
                entry_rule_cn=side.entry_rule_cn,
                exit_rule_cn=side.exit_rule_cn,
                total_signals=side.total_signals,
                open_trades=side.open_trades,
                stats=[
                    PullbackPerformanceDTO(
                        key=stat.key,
                        label_cn=stat.label_cn,
                        sample_count=stat.sample_count,
                        incomplete_count=stat.incomplete_count,
                        win_rate=stat.win_rate,
                        mean_return=stat.mean_return,
                        median_return=stat.median_return,
                        mean_mfe=stat.mean_mfe,
                        mean_mae=stat.mean_mae,
                        mean_holding_days=stat.mean_holding_days,
                    )
                    for stat in side.stats
                ],
            )
            for side in report.sides
        ],
    )


def _market_badge_dto(dto: MarketContextDTO) -> MarketBadgeDTO:
    """Build the badge from the same DTO that drives the full snapshot."""
    return MarketBadgeDTO(
        summary=dto.summary,
        summary_cn=dto.summary_cn,
        data_status=dto.data_status,
        reasons_cn=dto.reasons_cn,
    )


def _market_context_service(request: Request) -> MarketContextService:
    svc = getattr(request.app.state, "market_context_service", None)
    if svc is None:
        # Fall back to a per-request instance — covers tests that build a
        # raw FastAPI app without going through create_app.
        svc = MarketContextService()
        request.app.state.market_context_service = svc
    return svc


def _market_badge(request: Request, symbol: str, as_of: date) -> MarketBadgeDTO:
    """市场环境徽章 — sourced from the shared market-context service.

    The badge is built from the same ``MarketContextDTO`` that the full
    snapshot endpoint returns, so the chip and the panel can never
    disagree about whether today's environment is tailwind or unknown.
    """
    try:
        dto = _market_context_service(request).get_snapshot(symbol, as_of)
        return _market_badge_dto(dto)
    except Exception as exc:
        return MarketBadgeDTO(
            summary="unknown",
            summary_cn=labels.CONTEXT_SUMMARY_CN["unknown"],
            data_status="unavailable",
            reasons_cn=[f"市场环境分析失败：{exc}"],
        )


def _detail_dto(
    request: Request,
    symbol: str,
    result: AnalysisResult,
    *,
    data_time: str,
    persist_warning: str | None = None,
    quote_provider: TencentQuoteProvider | None = None,
) -> SymbolDetailDTO:
    override = config.INDEX_OVERRIDES.get(symbol)
    display_name = override.display_name if override else result.display_name
    market_cn = override.market_cn if override else result.price_data.info.market_cn

    report = result.price_data.report
    last_bar = report.last_date.date() if report.last_date is not None else date.today()
    close = float(result.frame["close"].iloc[-1]) if len(result.frame) else None

    structures = [
        structure_brief(s, close=close) for s in result.structures
    ]
    recent = sorted(result.events, key=lambda e: e.available_date, reverse=True)[
        :RECENT_EVENTS_LIMIT
    ]

    # MACD 副图事件（金叉/死叉/穿0轴）在 API 层合并进 chart：serialize_result
    # 属于冻结的 Streamlit 目录（见 AGENTS.md），扩展数据一律在这里叠加。
    chart = serialize_result(result, color_mode="red_green", max_bars=DETAIL_MAX_BARS)
    chart["macdEvents"] = build_macd_events(result, max_bars=DETAIL_MAX_BARS)
    # 消息日标记（参考层）：该标的 importance≥6 的消息按交易日聚合上图，
    # 消息面与技术面同屏对照；newsfeed 无数据/查询失败静默降级为空列表。
    try:
        chart["newsMarks"] = build_news_marks(
            config.sqlite_path(),
            symbol=symbol,
            display_name=display_name,
            dates=list(chart.get("dates") or []),
        )
    except Exception:  # noqa: BLE001 - 展示层增强，失败不影响详情主流程
        chart["newsMarks"] = []

    return SymbolDetailDTO(
        symbol=symbol,
        display_name=display_name,
        market_cn=market_cn,
        meta=MetaDTO(
            provider=report.provider,
            adjusted=report.adjusted,
            data_time=data_time,
            last_bar_date=last_bar.isoformat(),
            is_intraday_forming=is_intraday_forming(result),
            cache_fallback_used=result.cache_fallback_used,
            cache_age_seconds=result.cache_age_seconds,
            sqlite_persisted=result.sqlite_persisted,
            persist_warning=persist_warning,
            data_warnings=list(report.warnings),
            calendar_note_cn=CALENDAR_NOTE_CN,
        ),
        chart=chart,
        assessment=_assessment_dto(result),
        new_events=[
            event_dto(e, as_of=result.assessment.as_of) for e in result.assessment.new_events
        ],
        recent_events=[event_dto(e, as_of=result.assessment.as_of) for e in recent],
        live_structures=[s for s in structures if s.status in ("candidate", "confirmed", "active")],
        closed_structures=[
            s for s in structures if s.status in ("invalidated", "expired")
        ],
        market_badge=_market_badge(request, symbol, last_bar),
        today=build_today_overview(
            result,
            quote=quote_provider.fetch(symbol) if quote_provider is not None else None,
        ),
        color_backtest=_color_backtest_dto(result),
        first_ma_pullback_backtest=_pullback_backtest_dto(result),
        scenario_backtests=_build_scenario_backtests(result),
        concepts={
            key: dto
            for key in CONCEPTS
            if (dto := to_explanation_dto(CONCEPTS[key])) is not None
        },
        mark_concepts=dict(MARK_KIND_CONCEPTS),
        disclaimer_cn=config.DISCLAIMER_CN,
    )


@router.get("/symbols/{symbol}/detail", response_model=SymbolDetailDTO)
def symbol_detail(request: Request, symbol: str, refresh: bool = False) -> SymbolDetailDTO:
    entry = _service(request).get(symbol, refresh=refresh)
    if entry.result is None:
        raise HTTPException(status_code=502, detail=entry.error or "分析不可用")
    return _detail_dto(
        request,
        symbol,
        entry.result,
        data_time=entry.fetched_at.isoformat(),
        persist_warning=entry.persist_conflict,
        quote_provider=_quote_provider(request),
    )


@router.get("/symbols/{symbol}/events", response_model=list[EventDTO])
def symbol_events(
    request: Request,
    symbol: str,
    structure_id: str | None = None,
    on_date: str | None = None,
    rule_id: str | None = None,
    limit: int = 50,
) -> list[EventDTO]:
    """按需查事件：点击图上标记后取该结构/该日的绑定事件。

    为什么单独开端点：全量事件约 4858 条（≈4.5MB JSON），不能塞进详情响应；
    但详情里只带最近 60 条时，点击多年前的结构标记会得到空的「相关事件」。
    这里按 structure_id / 日期 / 规则过滤，按可用日倒序返回。
    """
    entry = _service(request).get(symbol)
    if entry.result is None:
        raise HTTPException(status_code=502, detail=entry.error or "分析不可用")

    events = entry.result.events
    if structure_id:
        events = [e for e in events if e.structure_id == structure_id]
    if on_date:
        try:
            target = date.fromisoformat(on_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"日期格式无效：{on_date}") from exc
        events = [e for e in events if e.available_date == target or e.event_date == target]
    if rule_id:
        events = [e for e in events if e.rule_id == rule_id]

    ordered = sorted(events, key=lambda e: e.available_date, reverse=True)
    as_of = entry.result.assessment.as_of
    return [event_dto(e, as_of=as_of) for e in ordered[: max(1, min(limit, 200))]]


@router.get("/symbols/{symbol}/market-context", response_model=MarketBadgeDTO)
def symbol_market_context(request: Request, symbol: str) -> MarketBadgeDTO:
    entry = _service(request).get(symbol)
    as_of = date.today()
    if entry.result is not None and entry.result.price_data.report.last_date is not None:
        as_of = entry.result.price_data.report.last_date.date()
    return _market_badge(request, symbol, as_of)


@router.get("/symbols/{symbol}/market-context/full")
def symbol_market_context_full(request: Request, symbol: str) -> dict:
    """Full market-context snapshot — same source as the badge."""
    entry = _service(request).get(symbol)
    as_of = date.today()
    if entry.result is not None and entry.result.price_data.report.last_date is not None:
        as_of = entry.result.price_data.report.last_date.date()
    dto = _market_context_service(request).get_snapshot(symbol, as_of)
    return _dto_to_dict(dto)


@router.get("/symbols/{symbol}/market-context/breadth-history")
def symbol_market_context_breadth_history(
    request: Request,
    symbol: str,
    market_id: str = Query(..., description="e.g. CSI_300, STAR_50"),
    lookback_days: int = Query(120, ge=1, le=1260),
) -> dict:
    """Return the breadth history for one reference market."""
    try:
        mid = MarketId(market_id)
    except ValueError:
        return {"market_id": market_id, "error": "unknown_market", "history": []}
    history = _market_context_service(request).get_breadth_history(
        mid, lookback_days=lookback_days,
    )
    return {"market_id": market_id, "lookback_days": lookback_days, "history": history}


@router.get("/market-context/data-status")
def market_context_data_status(request: Request, market_id: str) -> dict:
    """Provenance + coverage for one market."""
    try:
        mid = MarketId(market_id)
    except ValueError:
        return {"market_id": market_id, "error": "unknown_market"}
    return _market_context_service(request).data_status(mid)


def _a_share_breadth_derived() -> dict[str, Any]:
    """CN_ALL_A 面板的 delta_5 / 百分位派生值（带 TTL，失败返回全 None）。"""
    try:
        from lei_signal.market_context.a_share_breadth import get_ma_breadth_derived

        return {
            "breadth_20_delta_5": d["breadth_20_delta_5"],
            "breadth_50_delta_5": d["breadth_50_delta_5"],
            "percentile_20": d["percentile_20"],
            "percentile_50": d["percentile_50"],
        } if (d := get_ma_breadth_derived()) else {}
    except Exception:  # noqa: BLE001 — 派生值缺失不影响主面板
        return {}


@router.get("/market-context/global-strip")
def market_context_global_strip(request: Request) -> dict[str, Any]:
    """Return the two global panels (CN_ALL_A + SP500) for the topbar strip.

    全A(CN_ALL_A) 走真全A源（腾讯快照+交易所代码列表，涨跌家数），替换原
    fixture/dapanyuntu 假 B 系列；标普500(SP500) 保持原 service 计算（美股）。
    """
    from datetime import date as _date

    panels = _market_context_service(request).get_global_snapshots(_date.today())
    out: list[dict[str, Any]] = []
    for p in panels:
        snap = p.snapshots[0] if p.snapshots else None
        if snap is None:
            out.append({"market_id": p.symbol, "summary": p.summary, "data_status": p.data_status})
            continue
        mid = snap["market_id"]
        if mid == "SP500":
            # 美股：原 service 口径（B20/B50/B200 上方占比）
            out.append({
                "market_id": mid,
                "display_name": _GLOBAL_DISPLAY.get(mid, mid),
                "summary": p.summary,
                "summary_cn": p.summary_cn,
                "data_status": p.data_status,
                "breadth_20": snap["breadth_20"],
                "breadth_50": snap["breadth_50"],
                "breadth_200": snap.get("breadth_200"),
                "breadth_20_delta_5": snap["breadth_20_delta_5"],
                "breadth_50_delta_5": snap["breadth_50_delta_5"],
                "percentile_20": snap["percentile_20"],
                "percentile_50": snap["percentile_50"],
                "long_regime": snap["long_regime"],
                "heat_state": snap["heat_state"],
                "drawdown_from_ath": snap["drawdown_from_ath"],
                "alerts": _breadth_alerts(
                    snap.get("breadth_50"),
                    snap.get("breadth_200"),
                    snap.get("breadth_20"),
                ),
                "updated_at": p.updated_at,
            })
        # CN_ALL_A 在下方用真全A源覆盖，这里跳过原假 B 系列
    # —— 全A(CN_ALL_A)：真全A涨跌家数，替换原 fixture/dapanyuntu 假样本 ——
    from lei_signal.market_context.a_share_breadth import (
        get_a_share_breadth,
        get_cached_ma_breadth,
    )

    # 全A(CN_ALL_A)：读「本机收盘后预计算的冻结快照」（B系列 + 收盘涨跌家数 + 交易日）。
    # 磁盘文件缓存，重启不丢；次日整天与周末都直接读这份，不再实时重算。
    # 仅当缓存缺失（首次部署/未跑预计算）才回退到实时涨跌家数，B 系列优雅降级为 None。
    cached = get_cached_ma_breadth()
    if cached:
        ma20 = cached.get("ma20_pct")
        ma50 = cached.get("ma50_pct")
        ma200 = cached.get("ma200_pct")
        up = cached.get("up") or 0
        down = cached.get("down") or 0
        flat = cached.get("flat") or 0
        total = cached.get("total") or 0
        up_pct = cached.get("up_pct")
        adv_dec = cached.get("adv_dec_ratio")
        limit_up = cached.get("limit_up") or 0
        limit_down = cached.get("limit_down") or 0
        as_of = cached.get("as_of")
        trading_day = cached.get("date")
        src_detail = cached.get("source") or "本机收盘后预计算(腾讯日K线)"
        status = "ok"
    else:
        # 缓存缺失：实时涨跌家数兜底，B 系列为 None（绝不伪造）
        b = get_a_share_breadth(include_ma=False)
        ma20 = ma50 = ma200 = None
        up, down, flat = b.up, b.down, b.flat
        total = b.total
        up_pct, adv_dec = b.up_pct, b.adv_dec_ratio
        limit_up, limit_down = b.limit_up, b.limit_down
        as_of = b.as_of
        trading_day = None
        src_detail = b.source_detail
        status = b.data_status

    cn_all_entry: dict[str, Any] = {
        "market_id": "CN_ALL_A",
        "display_name": _GLOBAL_DISPLAY.get("CN_ALL_A", "全A"),
        "summary": "real_a_share",
        "summary_cn": "真全A·涨跌家数+宽度" if ma20 is not None else "真全A涨跌家数(宽度待计算)",
        "data_status": status,
        # MA 上方占比：来自冻结快照（本机收盘后预计算），无缓存则 None
        "breadth_20": ma20,
        "breadth_50": ma50,
        "breadth_200": ma200,
        # 5日变化 + 点时百分位：从预计算历史派生（TTL 缓存），无历史时为 None
        **_a_share_breadth_derived(),
        "long_regime": (
            ("bull" if (ma200 or 0) >= 50 else "bear") if ma200 is not None else "unknown"
        ),
        "heat_state": "unknown",
        "drawdown_from_ath": None,
        "alerts": _ad_alerts(adv_dec or 0) + (
            _breadth_alerts(ma50, ma200, ma20) if ma20 is not None else []
        ),
        "updated_at": as_of,
        # 真全A涨跌家数（来自冻结快照，核心、最权威）
        "is_real_a_share": True,
        "up": up,
        "down": down,
        "flat": flat,
        "total": total,
        "up_pct": up_pct,
        "adv_dec_ratio": adv_dec,
        "limit_up": limit_up,
        "limit_down": limit_down,
        # 冻结快照元信息：前端展示"宽度·截至 X 收盘"
        "breadth_as_of": as_of,
        "breadth_trading_day": trading_day,
        "breadth_source": src_detail,
        "source_detail": src_detail,
    }
    out.insert(0, cn_all_entry)
    return {"panels": out, "sentiment": _build_sentiment_summary()}


def _find_sentiment_file(series: str) -> "Path | None":
    """在 LEI_SENTIMENT_ROOT 下找 naaim/aaii 数据文件（csv 或 parquet，大小写兼容）。"""
    root = os.environ.get("LEI_SENTIMENT_ROOT")
    if not root:
        return None
    root_path = Path(root)
    for ext in (".csv", ".parquet"):
        for name in (f"{series}{ext}", f"{series.upper()}{ext}"):
            p = root_path / name
            if p.exists():
                return p
    return None


@router.get("/market-context/sentiment/history")
def market_context_sentiment_history(
    series: str = Query("naaim", description="naaim 或 aaii"),
    limit: int = Query(1040, ge=10, le=5000, description="最多返回期数（周频，1040≈20年）"),
) -> dict[str, Any]:
    """NAAIM / AAII 全历史观测（按调查周升序），供前端画情绪历史曲线。

    与 global-strip 的 sentiment 摘要同源（同一加载器）；坏数据不抛错，
    返回空列表由前端优雅降级。
    """
    from lei_signal.market_context.sentiment import (
        load_aaii_observations,
        load_naaim_observations,
    )

    key = series.lower()
    if key not in ("naaim", "aaii"):
        return {"series": series, "error": "unknown_series", "observations": []}
    path = _find_sentiment_file(key)
    if path is None:
        return {"series": key, "error": "file_not_found", "observations": []}
    try:
        obs = load_aaii_observations(path) if key == "aaii" else load_naaim_observations(path)
    except Exception as exc:  # noqa: BLE001 — 坏数据不炸接口
        return {"series": key, "error": f"load_failed: {exc}", "observations": []}
    ordered = sorted(obs, key=lambda o: o.survey_week)[-limit:]
    out: list[dict[str, Any]] = []
    for o in ordered:
        row: dict[str, Any] = {
            "survey_week": o.survey_week.isoformat(),
            # 发布时间（AAII/NAAIM 周四发布）：投影散点用它对齐标普入场价，避免前视
            "available_at": o.available_at.isoformat() if o.available_at else None,
            "label": o.label.value,
            "percentile": o.percentile,
        }
        if key == "naaim":
            row["exposure_index"] = o.exposure_index
        else:
            row["bullish"] = o.bullish
            row["neutral"] = o.neutral
            row["bearish"] = o.bearish
            row["bull_bear"] = o.bull_bear
        out.append(row)
    return {"series": key, "count": len(out), "observations": out}


def _build_sentiment_summary() -> dict[str, Any]:
    """Read NAAIM / AAII sentiment from ``LEI_SENTIMENT_ROOT`` and return a
    summary for the React frontend.

    Mirrors the logic in ``lei_signal.ui.app._render_sentiment_section`` so both
    frontends agree. Returns ``present=False`` sub-objects when the root is unset
    or a file is missing, and never raises on bad data (the UI degrades
    gracefully).
    """
    root = os.environ.get("LEI_SENTIMENT_ROOT")
    summary: dict[str, Any] = {"root_set": bool(root), "naaim": None, "aaii": None}
    if not root:
        return summary

    from pathlib import Path

    from lei_signal.market_context.sentiment import (
        load_aaii_observations,
        load_naaim_observations,
    )

    root_path = Path(root)
    _SENT_LABEL_CN = {
        "extreme_low": "极端悲观",
        "low": "悲观",
        "neutral": "中性",
        "high": "乐观",
        "extreme_high": "极端乐观",
        "unknown": "样本不足",
    }

    def _find(series: str) -> Path | None:
        for ext in (".csv", ".parquet"):
            for name in (f"{series}{ext}", f"{series.upper()}{ext}"):
                p = root_path / name
                if p.exists():
                    return p
        return None

    def _latest(obs):
        return max(obs, key=lambda o: o.available_at) if obs else None

    naaim_path = _find("naaim")
    if naaim_path is not None:
        try:
            latest = _latest(load_naaim_observations(naaim_path))
            if latest is not None:
                summary["naaim"] = {
                    "label": latest.label.value,
                    "label_cn": _SENT_LABEL_CN.get(latest.label.value, latest.label.value),
                    "exposure_index": latest.exposure_index,
                    "percentile": latest.percentile,
                    "survey_week": latest.survey_week.isoformat() if latest.survey_week else None,
                    "available_at": latest.available_at.isoformat() if latest.available_at else None,
                    "source": latest.source,
                    "license_status": latest.license_status,
                    "current_eligible": latest.current_eligible,
                }
        except Exception:  # noqa: BLE001 — bad data must not break the strip
            pass

    aaii_path = _find("aaii")
    if aaii_path is not None:
        try:
            latest = _latest(load_aaii_observations(aaii_path))
            if latest is not None:
                summary["aaii"] = {
                    "label": latest.label.value,
                    "label_cn": _SENT_LABEL_CN.get(latest.label.value, latest.label.value),
                    "bullish": latest.bullish,
                    "neutral": latest.neutral,
                    "bearish": latest.bearish,
                    "bull_bear": latest.bull_bear,
                    "survey_week": latest.survey_week.isoformat() if latest.survey_week else None,
                    "available_at": latest.available_at.isoformat() if latest.available_at else None,
                    "source": latest.source,
                    "license_status": latest.license_status,
                    "current_eligible": latest.current_eligible,
                }
        except Exception:  # noqa: BLE001
            pass

    return summary



class SentimentIngest(BaseModel):
    """前端手动录入一期情绪读数（NAAIM 暴露指数 / AAII 多空三值）。"""
    series: str
    survey_week: str
    exposure: float | None = None
    bullish: float | None = None
    neutral: float | None = None
    bearish: float | None = None
    available_at: str | None = None


def _append_sentiment_observation(
    series: str,
    survey_week: str,
    *,
    exposure: float | None = None,
    bullish: float | None = None,
    neutral: float | None = None,
    bearish: float | None = None,
    available_at: str | None = None,
) -> "Path":
    """写入一期情绪读数到 LEI_SENTIMENT_ROOT（复用 ingest_sentiment.py 的纯函数）。"""
    import importlib.util
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "scripts" / "round5_repro" / "ingest_sentiment.py"
    spec = importlib.util.spec_from_file_location("ingest_sentiment_mod", str(script))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    root = os.environ.get("LEI_SENTIMENT_ROOT") or str(mod.DEFAULT_ROOT)
    root = Path(root)
    if series == "naaim":
        row = mod.build_naaim_row(
            mod._parse_survey_week(survey_week), exposure, available_at=available_at,
        )
        path = mod.append_observation(root, "naaim", row, mod.NAAIM_COLUMNS, mod.NAAIM_FILENAME)
    else:
        row = mod.build_aaii_row(
            mod._parse_survey_week(survey_week), bullish, neutral, bearish,
            available_at=available_at,
        )
        path = mod.append_observation(root, "aaii", row, mod.AAII_COLUMNS, mod.AAII_FILENAME)
    return path


@router.post("/market-context/sentiment")
def ingest_sentiment_endpoint(payload: SentimentIngest):
    """前端「更新情绪」按钮：手动录入一期读数并写盘，随后 global-strip 自动反映。"""
    series = payload.series.lower()
    if series not in ("naaim", "aaii"):
        raise HTTPException(status_code=400, detail="series 必须是 naaim 或 aaii")
    if series == "naaim" and payload.exposure is None:
        raise HTTPException(status_code=400, detail="naaim 需要 exposure")
    if series == "aaii" and None in (payload.bullish, payload.neutral, payload.bearish):
        raise HTTPException(status_code=400, detail="aaii 需要 bullish/neutral/bearish")
    try:
        path = _append_sentiment_observation(
            series, payload.survey_week,
            exposure=payload.exposure, bullish=payload.bullish,
            neutral=payload.neutral, bearish=payload.bearish,
            available_at=payload.available_at,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"写入失败：{exc}")
    return {"ok": True, "path": str(path)}


@router.get("/market-context/breadth-history")
def market_context_breadth_history(
    request: Request,
    market_id: str = Query(..., description="e.g. CN_ALL_A, SP500"),
    lookback_days: int = Query(1260, ge=1, le=12600),
) -> dict:
    """Return the breadth history time-series for one global panel.

    Powers the expanded trend chart in the market-breadth snapshot panel
    (A股 全A / 美股 标普500). Reuses the same persisted revisions the
    global-strip reads from, so the frontend never recomputes breadth.
    """
    try:
        mid = MarketId(market_id)
    except ValueError:
        return {"market_id": market_id, "error": "unknown_market", "history": []}
    # 全A(CN_ALL_A) 走本机预计算落盘的真宽度历史（MA 上方占比），
    # 不再返回原 fixture/dapanyuntu 假序列；缓存为空时返回空（趋势图显示占位）。
    if mid == MarketId.CN_ALL_A:
        from lei_signal.market_context.a_share_breadth import get_ma_breadth_history
        # 全A 真宽度历史已预计算落盘（最多 ~1260 交易日），强制返回全量，
        # 不被前端 lookback 截断，叠加图/趋势图才能铺满整个窗口。
        hist = get_ma_breadth_history(lookback_days=12600)
        return {
            "market_id": market_id,
            "lookback_days": lookback_days,
            "history": [
                {
                    "date": h["date"],
                    "breadth_20": h.get("ma20_pct"),
                    "breadth_50": h.get("ma50_pct"),
                    "breadth_200": h.get("ma200_pct"),
                }
                for h in hist
            ],
        }
    # 标普500 走本机预计算落盘的真实宽度历史（成分股站上 MA 占比），
    # 不再返回空（lab.db 无 SP500 快照）。无数据返回 []，前端标「数据缺失」。
    if mid == MarketId.SP500:
        from lei_signal.market_context.us_breadth import get_sp500_breadth_history
        # 强制返回全量（最多 ~1260 交易日），不被前端 lookback 截断，
        # 叠加图/趋势图才能铺满整个窗口，与 A股支路边对称。
        hist = get_sp500_breadth_history(lookback_days=12600)
        return {
            "market_id": market_id,
            "lookback_days": lookback_days,
            "history": [
                {
                    "date": h["date"],
                    "breadth_20": h.get("breadth_20"),
                    "breadth_50": h.get("breadth_50"),
                    "breadth_200": h.get("breadth_200"),
                }
                for h in hist
            ],
        }
    history = _market_context_service(request).get_breadth_history(
        mid, lookback_days=lookback_days,
    )
    return {"market_id": market_id, "lookback_days": lookback_days, "history": history}


@router.get("/market-context/a-share-breadth")
def market_context_a_share_breadth(
    request: Request,
    include_ma: bool = Query(
        False,
        description="含 MA20/50/200 上方占比(券商金工口径)，需正常网络环境拉个股历史K线",
    ),
) -> dict:
    """真全A市场宽度：替换原 fixture 假全A样本。

    核心维度 = 涨跌家数（腾讯实时快照 + 沪深交易所代码列表），覆盖真全A，
    默认即算、受限网络可验。可选维度 = MA20/50/200 上方占比（akshare 东财历史K线，
    券商金工"全A宽度"口径），受限网络下自动降级、绝不伪造。
    """
    from lei_signal.market_context.a_share_breadth import get_a_share_breadth

    b = get_a_share_breadth(include_ma=include_ma)
    return {
        "as_of": b.as_of,
        "up": b.up,
        "down": b.down,
        "flat": b.flat,
        "total": b.total,
        "up_pct": b.up_pct,
        "adv_dec_ratio": b.adv_dec_ratio,
        "limit_up": b.limit_up,
        "limit_down": b.limit_down,
        "ma20_pct": b.ma20_pct,
        "ma50_pct": b.ma50_pct,
        "ma200_pct": b.ma200_pct,
        "data_status": b.data_status,
        "source_detail": b.source_detail,
    }


# 宽度极值阈值（% 站上均线个股占比）。
# 行业通用标准：80% 超买 / 20% 超卖 / 50% 多空分界
# （TradingView 宽度脚本、marketinout %Above50MA、thetrading.tools / pomegra.io
#  等 quant 通用框架均以此为准）。华泰证券《A股择时之技术面指标测试》(2021)
# 亦建议对 A 股采用默认/标准参数、警惕参数过拟合，故 A股/美股共用此标准值。
_HOT_THRESHOLD = 80.0
_COLD_THRESHOLD = 20.0


def _breadth_alerts(
    b50: float | None,
    b200: float | None,
    b20: float | None = None,
) -> list[dict[str, str]]:
    """Check breadth extremes and return alert dicts.

    Two tiers:
    - **reversal**: B50 AND B200 both ≥80 (top) or both ≤20 (bottom).
      These are the rare "both timeframes agree on an extreme" signals
      the user wants prominently highlighted.
    - **stage**: B50 alone ≥80 or ≤20 (B200 not confirmed). Less strong,
      but still a warning that one timeframe is at an extreme.

    When B50 is unavailable (e.g. CN_ALL_A from dapanyuntu, which only
    publishes MA20), fall back to B20 so the alert still fires - but
    label it as B20-based so the user knows it's a shorter lookback.
    """
    alerts: list[dict[str, str]] = []

    # Pick the best available "medium" breadth: B50 preferred, B20 fallback.
    medium = b50 if b50 is not None else b20
    medium_label = "B50" if b50 is not None else ("B20" if b20 is not None else "")

    if medium is None:
        return alerts

    # Reversal: both medium AND B200 at the same extreme.
    if b200 is not None:
        if medium >= _HOT_THRESHOLD and b200 >= _HOT_THRESHOLD:
            alerts.append({
                "level": "reversal",
                "type": "reversal_top",
                "title": "⚠️ 反转顶部信号",
                "desc": (
                    f"{medium_label}={medium:.1f}% 且 B200={b200:.1f}%，"
                    "同时高于80%，大概率是趋势反转位置"
                ),
            })
        elif medium <= _COLD_THRESHOLD and b200 <= _COLD_THRESHOLD:
            alerts.append({
                "level": "reversal",
                "type": "reversal_bottom",
                "title": "⚠️ 反转底部信号",
                "desc": (
                    f"{medium_label}={medium:.1f}% 且 B200={b200:.1f}%，"
                    "同时低于20%，大概率是趋势反转位置"
                ),
            })

    # Stage: medium alone at an extreme (B200 not confirmed or not available).
    if medium >= _HOT_THRESHOLD:
        already = any(a["type"] == "reversal_top" for a in alerts)
        if not already:
            alerts.append({
                "level": "stage",
                "type": "stage_top",
                "title": "阶段性顶部预警",
                "desc": f"{medium_label}={medium:.1f}%，高于80%，大概率是阶段性顶部",
            })
    elif medium <= _COLD_THRESHOLD:
        already = any(a["type"] == "reversal_bottom" for a in alerts)
        if not already:
            alerts.append({
                "level": "stage",
                "type": "stage_bottom",
                "title": "短期底部预警",
                "desc": f"{medium_label}={medium:.1f}%，低于20%，大概率是短期底部",
            })

    return alerts


def _ad_alerts(adv_dec: float | None) -> list[dict[str, str]]:
    """真全A涨跌家数维度的简易情绪预警（替换原 B 系列阈值预警）。

    涨跌比 AD = 上涨家数 / 下跌家数。AD 越低说明跌多涨少、广度越弱；
    AD 越高说明涨多跌少、广度越强（过强需防追高）。阈值仅为直观参考，
    非券商金工严格框架。
    """
    if adv_dec is None:
        return []
    alerts: list[dict[str, str]] = []
    if adv_dec <= 0.4:
        alerts.append({
            "level": "stage",
            "type": "ad_ice",
            "title": "⚠️ 普跌·广度冰点",
            "desc": f"涨跌比 {adv_dec:.2f}（涨/跌），跌多涨少，全市场广度极弱",
        })
    elif adv_dec >= 2.5:
        alerts.append({
            "level": "stage",
            "type": "ad_hot",
            "title": "🔥 普涨·广度过热",
            "desc": f"涨跌比 {adv_dec:.2f}（涨/跌），涨多跌少，注意追高风险",
        })
    return alerts


_GLOBAL_DISPLAY = {
    "CN_ALL_A": "全A",
    "SP500": "标普500",
    "CSI_300": "沪深300",
    "STAR_50": "科创50",
}


@router.get("/market-context/forward-stats")
def market_context_forward_stats(
    request: Request,
    market_id: str,
    percentile: float = Query(..., ge=0.0, le=100.0),
    bucket_half_width: float = Query(5.0, gt=0.0, le=25.0),
) -> dict:
    """Return the forward 5/20/60-day index return distribution for past
    sessions where the 20-day breadth percentile fell in the same bucket
    as the current one."""
    try:
        mid = MarketId(market_id)
    except ValueError:
        return {"market_id": market_id, "error": "unknown_market"}
    return _market_context_service(request).get_forward_stats(
        mid, percentile, bucket_half_width=bucket_half_width,
    )


def _dto_to_dict(dto: MarketContextDTO) -> dict:
    return {
        "symbol": dto.symbol,
        "as_of": dto.as_of.isoformat(),
        "summary": dto.summary,
        "summary_cn": dto.summary_cn,
        "data_status": dto.data_status,
        "reasons_cn": dto.reasons_cn,
        "conflicts_cn": dto.conflicts_cn,
        "source_kind": dto.source_kind,
        "provenance": dto.provenance,
        "updated_at": dto.updated_at,
        "snapshots": dto.snapshots,
    }


@router.post("/refresh", response_model=DashboardResponse)
def refresh(request: Request, body: RefreshRequest) -> DashboardResponse:
    """刷新按钮。symbols 为空 = 全量重取；指定 symbols = 只驱逐并重取这些。"""
    service = _service(request)
    db_path = _db_path(request)
    if body.symbols:
        service.get_many(body.symbols, refresh=True)
        return assemble_dashboard(service, db_path, refresh=False)
    return assemble_dashboard(service, db_path, refresh=True)


@router.get("/meta/indices", response_model=list[ResolveResultDTO])
def dashboard_indices_meta() -> list[ResolveResultDTO]:
    """默认大盘清单（前端图例/调试用）。"""
    return [
        ResolveResultDTO(
            symbol=idx.symbol,
            market="",
            market_cn=idx.market_cn,
            bare_code=idx.symbol,
            timezone="",
            display_name=idx.display_name,
        )
        for idx in config.DASHBOARD_INDICES
    ]
