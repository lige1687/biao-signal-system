"""持续观察状态机。

核心不变量（架构第 6 节）：
  1. 先前信号不因其他条件当天没满足而被丢弃。
  2. 「共同确认」读取**当前状态**，不要求当天重新穿越 EMA20。
  3. 长趋势改善时，即使 EMA20 交叉已经过去，也能升级为趋势增强。
  4. 任一时刻触及 C 永久终止关联底部结构；后续上涨不能复活。
  5. 同一标的可同时保留多个底部结构；选最近有效者为主结构，但不删除其他。
  6. 顶部与底部可暂时并存，界面显示冲突，不静默覆盖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lei_signal.domain.types import (
    LongTrendState,
    SignalColor,
    Stage,
    StructureInstance,
)


@dataclass
class DayState:
    """某一交易日的观察状态。"""

    day: date
    stage: Stage
    color: SignalColor
    live_bottoms: list[StructureInstance] = field(default_factory=list)
    primary_bottom: StructureInstance | None = None
    active_top: StructureInstance | None = None
    early_strength_active: bool = False
    early_strength_date: date | None = None
    joint_confirmed_now: bool = False
    daily_long: LongTrendState = LongTrendState.UNKNOWN
    weekly_long: LongTrendState = LongTrendState.UNKNOWN
    long_supportive: bool = False
    reasons: list[str] = field(default_factory=list)


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
) -> list[DayState]:
    """逐日推进状态机。

    每天重新读取「当前仍然有效的状态」，而不是要求所有事件同一天发生。
    这使得 6 月的短期转强可以在 8 月长趋势改善时推动升级。
    """
    from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state

    if early_strength_state is None:
        early_strength_state = ema20_reclaim_state(frame)
    if joint_state is None:
        joint_state = dual_ma_bull_state(frame)

    bottoms = [s for s in structures if s.side == "bottom"]
    tops = [s for s in structures if s.side == "top"]

    history: list[DayState] = []
    early_active = False
    early_date: date | None = None

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

        # 早期转强是**持续状态**：一旦出现就保留，直到被转黑或触及 C 否定。
        if bool(early_strength_state.loc[timestamp]):
            early_active = True
            early_date = day
        if color is SignalColor.BLACK:
            early_active = False
            early_date = None
        joint_now = bool(joint_state.loc[timestamp])

        daily_long = LongTrendState(str(row.get("long_trend", "unknown")))
        weekly_long = LongTrendState.UNKNOWN
        if weekly_trend is not None and not weekly_trend.empty:
            visible = weekly_trend.loc[weekly_trend.index <= timestamp]
            if not visible.empty:
                weekly_long = LongTrendState(str(visible["long_trend"].iloc[-1]))
        long_supportive = daily_long in _IMPROVING_STATES or weekly_long in _IMPROVING_STATES

        stage, reasons = _resolve_stage(
            color=color,
            live_bottoms=live_bottoms,
            confirmed_bottoms=confirmed_bottoms,
            active_top=active_top,
            early_active=early_active,
            joint_now=joint_now,
            long_supportive=long_supportive,
            day=day,
            structures=bottoms,
        )

        history.append(
            DayState(
                day=day,
                stage=stage,
                color=color,
                live_bottoms=live_bottoms,
                primary_bottom=primary,
                active_top=active_top,
                early_strength_active=early_active,
                early_strength_date=early_date,
                joint_confirmed_now=joint_now,
                daily_long=daily_long,
                weekly_long=weekly_long,
                long_supportive=long_supportive,
                reasons=reasons,
            )
        )
    return history


def _resolve_stage(
    *,
    color: SignalColor,
    live_bottoms: list[StructureInstance],
    confirmed_bottoms: list[StructureInstance],
    active_top: StructureInstance | None,
    early_active: bool,
    joint_now: bool,
    long_supportive: bool,
    day: date,
    structures: list[StructureInstance],
) -> tuple[Stage, list[str]]:
    """决定当天阶段。

    机会阶段与风险阶段分开判断：风险不删除底部结构，只改变提示层级。
    """
    reasons: list[str] = []

    # 当天刚刚触及 C 的结构 -> 失效提示（但不影响其他仍有效结构）
    invalidated_today = [
        s for s in structures if s.invalidated_date == day
    ]
    if invalidated_today and not live_bottoms:
        reasons.append("有效底部结构因触及C而全部失效")
        return Stage.INVALIDATED, reasons

    # 机会阶段（自下而上升级）
    opportunity = Stage.NO_CLUE
    if live_bottoms:
        opportunity = Stage.BOTTOM_WATCH
        reasons.append(f"存在{len(live_bottoms)}个有效底部线索")
    if confirmed_bottoms:
        opportunity = Stage.STRUCTURE_CONFIRMED
        reasons.append("底部结构已确认")
    if live_bottoms and early_active:
        opportunity = Stage.EARLY_STRENGTH
        reasons.append("EMA20重新站上且向上（早期转强仍有效）")
    if live_bottoms and joint_now:
        # 不要求今天重新穿越 EMA20
        opportunity = Stage.JOINT_CONFIRMED
        reasons.append("双均线当前共同向上（共同确认，读取当前状态）")
    if opportunity is Stage.JOINT_CONFIRMED and long_supportive:
        opportunity = Stage.TREND_REINFORCED
        reasons.append("日线或周线长周期趋势转为改善/支持（趋势增强）")

    # 风险阶段：只在存在风险时覆盖提示层级
    if color is SignalColor.BLACK:
        reasons.append("当前为黑色关键性波动")
        if active_top is not None:
            reasons.append("同时存在有效顶部警报（Top+Black）")
        return Stage.KEY_RISK, reasons
    if active_top is not None:
        reasons.append("存在有效顶部警报，与底部结构并存（冲突）")
        return Stage.RISK_WATCH, reasons
    if color is SignalColor.GRAY and opportunity in (
        Stage.JOINT_CONFIRMED,
        Stage.TREND_REINFORCED,
    ):
        reasons.append("颜色转灰，均线方向出现分歧")
        return Stage.RISK_WATCH, reasons

    return opportunity, reasons


__all__ = ["DayState", "run_state_machine"]
