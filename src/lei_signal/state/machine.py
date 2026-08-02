"""持续观察状态机。

核心不变量（架构第 6 节 + 修复要求）：
  1. 机会阶段与风险状态**分离**保存——前者是机会维度，后者是风险维度。
     过去会把 KEY_RISK / RISK_WATCH / INVALIDATED 混进 stage，掩盖原机会阶段。
  2. EMA20 早期转强是**结构关联的持续状态**：
       - 当转强事件绑定到某个底部 structure_id 时，
         该结构触及 C 失效 → 关联的早期转强立即失效。
       - 新底部结构**不得继承**旧底部的早期转强。
       - 颜色转黑 → 当前所有早期转强失效。
  3. 状态可逐日回放，不依赖未来数据。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lei_signal.domain.types import (
    LongTrendState,
    RiskState,
    SignalColor,
    Stage,
    StructureInstance,
)


@dataclass
class DayState:
    """某一交易日的观察状态。机会与风险分离保存。"""

    day: date
    opportunity_stage: Stage
    risk_state: RiskState
    color: SignalColor
    live_bottoms: list[StructureInstance] = field(default_factory=list)
    primary_bottom: StructureInstance | None = None
    active_top: StructureInstance | None = None
    # 每个 structure_id 对应一个「该结构仍享有早期转强」的布尔；
    # 仅当该结构仍存在且没被 C 触及、且最近有未失效的转强事件时为 True。
    early_strength_by_structure: dict[str, bool] = field(default_factory=dict)
    # 兼容旧接口：单一早期转强标志（与 primary_bottom 关联）
    early_strength_active: bool = False
    early_strength_date: date | None = None
    early_strength_structure_id: str | None = None
    joint_confirmed_now: bool = False
    daily_long: LongTrendState = LongTrendState.UNKNOWN
    weekly_long: LongTrendState = LongTrendState.UNKNOWN
    long_supportive: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def stage(self) -> Stage:
        """综合显示阶段（保留向后兼容）。"""
        if self.risk_state is RiskState.C_INVALIDATED:
            return Stage.INVALIDATED
        if self.risk_state is RiskState.TOP_PLUS_BLACK:
            return Stage.KEY_RISK
        if self.risk_state in (RiskState.BLACK, RiskState.ACTIVE_TOP, RiskState.GRAY_WATCH):
            return Stage.RISK_WATCH
        return self.opportunity_stage

    @property
    def color_value(self) -> str:
        return self.color.value


_IMPROVING_STATES = {
    LongTrendState.LONG_IMPROVING,
    LongTrendState.LONG_BULL,
    LongTrendState.LONG_STABLE_BULL,
}


def _bottom_is_live_on(structure: StructureInstance, day: date) -> bool:
    """结构在 day 当天是否仍然有效。

    永久失效语义：一旦 invalidated_date <= day，此后任何一天都不再有效，
    即使价格重新上涨也不能复活。
    """
    if structure.side != "bottom":
        return False
    if structure.detected_date > day:
        return False
    return not (structure.invalidated_date is not None and structure.invalidated_date <= day)


def _top_is_active_on(structure: StructureInstance, day: date) -> bool:
    if structure.side != "top":
        return False
    if structure.confirmed_date is None or structure.confirmed_date > day:
        return False
    return not (structure.invalidated_date is not None and structure.invalidated_date <= day)


def run_state_machine(
    frame: pd.DataFrame,
    structures: list[StructureInstance],
    *,
    weekly_trend: pd.DataFrame | None = None,
    early_strength_state: pd.Series | None = None,
    joint_state: pd.Series | None = None,
    ema_reclaim_events: list | None = None,
) -> list[DayState]:
    """逐日推进状态机。

    early_strength_state 是可选的「全局」逐日 EMA20 早期转强布尔，
    用于决定哪些日期**有机会**生成结构关联事件（基础过滤）；
    真实结构关联来自 ema_reclaim_events（已绑定到具体 structure_id）。

    当某底部 structure_id 的失效日 <= day，
    该结构对应的早期转强立即失效，不影响其他结构。
    """
    from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state

    if early_strength_state is None:
        early_strength_state = ema20_reclaim_state(frame)
    if joint_state is None:
        joint_state = dual_ma_bull_state(frame)
    # 按结构 + 日期索引：{ structure_id: { day: event } }
    ema_reclaim_by_structure_day: dict[str, dict[date, object]] = {}
    if ema_reclaim_events:
        for event in ema_reclaim_events:
            if event.rule_id != "ema20_reclaim_rising":
                continue
            if not event.structure_id:
                continue
            ema_reclaim_by_structure_day.setdefault(
                event.structure_id, {}
            )[event.available_date] = event

    bottoms = [s for s in structures if s.side == "bottom"]
    tops = [s for s in structures if s.side == "top"]

    history: list[DayState] = []
    # 按结构记录早期转强：{ structure_id: (active, last_reclaim_date) }
    # 当颜色转黑时，所有结构都标记失效（不复活）。
    per_structure_early: dict[str, tuple[bool, date | None]] = {}

    for timestamp, row in frame.iterrows():
        day = timestamp.date()
        color = SignalColor(str(row.get("signal_color", "unknown")))

        live_bottoms = [s for s in bottoms if _bottom_is_live_on(s, day)]
        confirmed_bottoms = [
            s
            for s in live_bottoms
            if s.confirmed_date is not None and s.confirmed_date <= day
        ]
        active_top = next((t for t in tops if _top_is_active_on(t, day)), None)

        # 主结构：最近确认的有效结构（不删除其他）
        primary = None
        if confirmed_bottoms:
            primary = max(confirmed_bottoms, key=lambda s: (s.confirmed_date, s.detected_date))
        elif live_bottoms:
            primary = max(live_bottoms, key=lambda s: s.detected_date)

        # 逐结构更新 early_strength 状态（修复 3：仅在有事件关联时 active）
        reclaim_now_global = bool(early_strength_state.loc[timestamp])
        if color is SignalColor.BLACK:
            # 转黑：所有关联早期转强立即失效
            per_structure_early = {
                sid: (False, last_date) for sid, (_, last_date) in per_structure_early.items()
            }
        else:
            new_per_structure: dict[str, tuple[bool, date | None]] = {}
            for structure in live_bottoms:
                prev_active, last_date = per_structure_early.get(
                    structure.structure_id, (False, None)
                )
                # 修复 3：必须存在绑定到该结构 + 当日的 ema_reclaim 事件才标记 active。
                # 旧的「全局 reclaim_now=True 即所有结构 active」是 bug。
                has_bound_event = (
                    ema_reclaim_by_structure_day.get(structure.structure_id, {}).get(day)
                    is not None
                )
                if has_bound_event and reclaim_now_global:
                    new_per_structure[structure.structure_id] = (True, day)
                else:
                    new_per_structure[structure.structure_id] = (prev_active, last_date)
            per_structure_early = new_per_structure

        # 至少一个底部结构仍享有早期转强
        any_early = any(active for active, _ in per_structure_early.values())
        # 单一主结构早期转强（向后兼容）：取主结构
        if primary is not None and per_structure_early.get(primary.structure_id, (False, None))[0]:
            primary_early_active = True
            primary_early_date = per_structure_early[primary.structure_id][1]
            primary_early_sid = primary.structure_id
        else:
            # 没有关联主结构时，**禁止**回退到全局「最近」早期转强
            primary_early_active = False
            primary_early_date = None
            primary_early_sid = None

        joint_now = bool(joint_state.loc[timestamp])

        daily_long = LongTrendState(str(row.get("long_trend", "unknown")))
        weekly_long = LongTrendState.UNKNOWN
        if weekly_trend is not None and not weekly_trend.empty:
            visible = weekly_trend.loc[weekly_trend.index <= timestamp]
            if not visible.empty:
                weekly_long = LongTrendState(str(visible["long_trend"].iloc[-1]))
        long_supportive = daily_long in _IMPROVING_STATES or weekly_long in _IMPROVING_STATES

        opportunity, opp_reasons = _resolve_opportunity(
            live_bottoms=live_bottoms,
            confirmed_bottoms=confirmed_bottoms,
            any_early_strength=any_early,
            joint_now=joint_now,
            long_supportive=long_supportive,
        )
        risk, risk_reasons = _resolve_risk(
            color=color,
            active_top=active_top,
            structures=structures,
            day=day,
        )

        reasons = opp_reasons + risk_reasons
        history.append(
            DayState(
                day=day,
                opportunity_stage=opportunity,
                risk_state=risk,
                color=color,
                live_bottoms=live_bottoms,
                primary_bottom=primary,
                active_top=active_top,
                early_strength_by_structure={
                    sid: active for sid, (active, _) in per_structure_early.items()
                },
                early_strength_active=primary_early_active,
                early_strength_date=primary_early_date,
                early_strength_structure_id=primary_early_sid,
                joint_confirmed_now=joint_now,
                daily_long=daily_long,
                weekly_long=weekly_long,
                long_supportive=long_supportive,
                reasons=reasons,
            )
        )
    return history


def _resolve_opportunity(
    *,
    live_bottoms: list[StructureInstance],
    confirmed_bottoms: list[StructureInstance],
    any_early_strength: bool,
    joint_now: bool,
    long_supportive: bool,
) -> tuple[Stage, list[str]]:
    """机会阶段（不混入风险）。"""
    reasons: list[str] = []
    opportunity = Stage.NO_CLUE
    if live_bottoms:
        opportunity = Stage.BOTTOM_WATCH
        reasons.append(f"存在{len(live_bottoms)}个有效底部线索")
    if confirmed_bottoms:
        opportunity = Stage.STRUCTURE_CONFIRMED
        reasons.append("底部结构已确认")
    if live_bottoms and any_early_strength:
        opportunity = Stage.EARLY_STRENGTH
        reasons.append("早期转强仍有效（结构关联）")
    if live_bottoms and joint_now:
        opportunity = Stage.JOINT_CONFIRMED
        reasons.append("双均线当前共同向上（共同确认）")
    if opportunity is Stage.JOINT_CONFIRMED and long_supportive:
        opportunity = Stage.TREND_REINFORCED
        reasons.append("日线或周线长周期趋势支持/改善（趋势增强）")
    return opportunity, reasons


def _resolve_risk(
    *,
    color: SignalColor,
    active_top: StructureInstance | None,
    structures: Iterable[StructureInstance],
    day: date,
) -> tuple[RiskState, list[str]]:
    """风险状态（与机会阶段分离）。"""
    reasons: list[str] = []
    bottoms = [s for s in structures if s.side == "bottom"]
    invalidated_today = [
        s for s in bottoms
        if s.invalidated_date == day
        and s.status.value == "invalidated"
    ]
    if invalidated_today:
        reasons.append("C 触及/跌破，关联底部结构已失效")
        return RiskState.C_INVALIDATED, reasons
    if color is SignalColor.BLACK:
        reasons.append("当前为黑色关键性波动")
        if active_top is not None:
            reasons.append("同时存在有效顶部警报（Top+Black 组合）")
            return RiskState.TOP_PLUS_BLACK, reasons
        return RiskState.BLACK, reasons
    if active_top is not None:
        reasons.append("存在有效顶部警报")
        return RiskState.ACTIVE_TOP, reasons
    if color is SignalColor.GRAY:
        reasons.append("颜色转灰（方向分歧）")
        return RiskState.GRAY_WATCH, reasons
    return RiskState.NORMAL, reasons


__all__ = ["DayState", "run_state_machine"]
