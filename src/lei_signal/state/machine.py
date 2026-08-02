"""持续观察状态机。

核心不变量（架构第 6 节 + Round 3 修复 1/2）：
  1. 机会阶段与风险状态**分离**保存——前者是机会维度，后者是风险维度。
     过去会把 KEY_RISK / RISK_WATCH / INVALIDATED 混进 stage，掩盖原机会阶段。
  2. **状态机消费事件层已经算好的档位链**，不再自己另算一套。
     Round 3 修复 D1/D2：让状态机逐结构投影 ``ema_reclaim_tiers`` 已写入
     ``SignalEvent.evidence['tier']`` 的档位，把「该结构该不该升级」的决定权
     完整交给事件层。状态机只负责：
        a) 把同一 ``lifecycle_id`` 的连续事件拼成一条观察实例；
        b) 决定实例是否仍有效（结构失效 / 颜色转黑 → 关闭）；
        c) 把该实例的当前档位映射到机会阶段。
  3. 状态可逐日回放，不依赖未来数据。
  4. ``early_watch`` 档只写理由、**不抬升机会阶段**——让未确认结构保持
     ``BOTTOM_WATCH``，防止越过结构确认档（真值表 #4）。
  5. 机会阶段取各结构独立推进后的最大值，绝不允许跨结构拼装条件
     （A 的确认 + B 的转强 ≠ 任何升级）。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd

from lei_signal.domain.types import (
    LongTrendState,
    RiskState,
    SignalColor,
    Stage,
    StructureInstance,
)
from lei_signal.rules.ema_reclaim_tiers import (
    EARLY_WATCH_SUB_RULES,
    TIER_EARLY_WATCH,
    TIER_JOINT_CONFIRMED,
    TIER_LONG_TREND_IMPROVED,
    TIER_RANK,
    TIER_STRUCTURE_CONFIRMED,
)


@dataclass(frozen=True, slots=True)
class StructureObservation:
    """一个底部结构在状态机侧的逐日投影。

    * ``structure_id``     关联底部结构
    * ``lifecycle_id``     该观察实例 ID（同一实例内档位只升不降不重复）
    * ``tier``             当前档位（``None`` 表示该实例已关闭，但结构仍可存活）
    * ``opened_on``        本实例开启日
    * ``last_upgraded_on`` 最近一次升级日（首次开启时 = ``opened_on``）
    """

    structure_id: str
    lifecycle_id: str
    tier: Optional[str]
    opened_on: date
    last_upgraded_on: date

    @property
    def is_active(self) -> bool:
        return self.tier is not None


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
    # 逐结构投影：状态机消费事件层档位后的快照
    # { structure_id: StructureObservation | None }
    # 不活跃的结构从该字典中**删除**（而非保留为 None），调用方用
    # ``observations.get(sid) is None`` 判断；已失效结构同理。
    observations: dict[str, StructureObservation] = field(default_factory=dict)
    # 兼容旧字段：单值化派生自 observations（primary_bottom 关联）
    early_strength_by_structure: dict[str, bool] = field(default_factory=dict)
    early_watch_by_structure: dict[str, bool] = field(default_factory=dict)
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


def _tier_is_buy_signal(tier: str | None) -> bool:
    """档位是否算「买入信号」（候选观察档不算）。"""
    return tier is not None and tier != TIER_EARLY_WATCH


def _max_active_tier_rank(observations: dict[str, StructureObservation]) -> int:
    """所有活跃观察档位中的最高 rank；无活跃时为 0。"""
    best = 0
    for obs in observations.values():
        if obs.tier is None:
            continue
        best = max(best, TIER_RANK[obs.tier])
    return best


def _max_active_tier_for_stage(
    observations: dict[str, StructureObservation],
    structure_map: dict[str, StructureInstance],
) -> tuple[Stage, int]:
    """从当前所有活跃观察中推导**抬升后**的机会阶段与最高 rank。

    严格按真值表：
      * 候选结构上的 ``early_watch`` 档 → **不返回 BOTTOM_WATCH**（观察档不抬阶段，
        但仍表明该结构值得保留观察，由 _resolve_opportunity 负责把它表现为
        BOTTOM_WATCH 而非 NO_CLUE）
      * 已确认结构上的 ``structure_confirmed`` → ``EARLY_STRENGTH``
      * 已确认结构上的 ``joint_confirmed`` → ``JOINT_CONFIRMED``
      * 已确认结构上的 ``long_trend_improved`` → ``TREND_REINFORCED``

    返回 ``(Stage.NO_CLUE, 0)`` 表示「没有任何抬升动作」。
    """
    best_stage = Stage.NO_CLUE
    best_rank = 0
    for sid, obs in observations.items():
        if obs.tier is None:
            continue
        structure = structure_map.get(sid)
        if structure is None:
            continue
        confirmed = structure.confirmed_date is not None and structure.confirmed_date <= obs.last_upgraded_on
        if obs.tier == TIER_EARLY_WATCH and not confirmed:
            # 候选观察档：不抬阶段
            continue
        if not confirmed:
            # 任何高于 early_watch 的档位都要求结构已确认；
            # 事件层保证不发出这种事件，这里再守一次。
            continue
        if obs.tier == TIER_STRUCTURE_CONFIRMED:
            stage, rank = Stage.EARLY_STRENGTH, 3
        elif obs.tier == TIER_JOINT_CONFIRMED:
            stage, rank = Stage.JOINT_CONFIRMED, 4
        elif obs.tier == TIER_LONG_TREND_IMPROVED:
            stage, rank = Stage.TREND_REINFORCED, 5
        else:
            # 兜底：未来新增档位先按字符串前缀保守处理
            stage, rank = Stage.EARLY_STRENGTH, 3
        if rank > best_rank:
            best_rank = rank
            best_stage = stage
    return best_stage, best_rank


def run_state_machine(
    frame: pd.DataFrame,
    structures: list[StructureInstance],
    *,
    weekly_trend: pd.DataFrame | None = None,
    early_strength_state: pd.Series | None = None,
    joint_state: pd.Series | None = None,
    ema_reclaim_events: list | None = None,
) -> list[DayState]:
    """逐日推进状态机（Round 3 修复 D1/D2 后版本）。

    核心变化：状态机只投影 ``ema_reclaim_events`` 中已绑定的档位事件。
    任何「全局 joint_now」/「全局 reclaim_now」都**不再**参与阶段升级；
    它们仅保留在 ``DayState`` 中作为描述性信息（供 UI 展示与维度判断）。
    """
    from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state

    if early_strength_state is None:
        early_strength_state = ema20_reclaim_state(frame)
    if joint_state is None:
        joint_state = dual_ma_bull_state(frame)

    # 把事件按结构 + lifecycle_id 索引：{ structure_id: { lifecycle_id: [events...] } }
    # 同 lifecycle_id 内按 available_date 严格单调（事件层已保证）；按此推出
    # 每个观察实例的「最新档位 + 最后升级日」。
    structure_events: dict[str, dict[str, list[object]]] = {}
    if ema_reclaim_events:
        for event in ema_reclaim_events:
            if event.rule_id != "ema20_reclaim_rising":
                continue
            if not event.structure_id:
                continue
            sub_rule = event.evidence.get("sub_rule")
            if sub_rule not in (
                *EARLY_WATCH_SUB_RULES,
                f"ema20_reclaim_rising_{TIER_STRUCTURE_CONFIRMED}",
                f"ema20_reclaim_rising_{TIER_JOINT_CONFIRMED}",
                f"ema20_reclaim_rising_{TIER_LONG_TREND_IMPROVED}",
            ):
                continue
            if event.lifecycle_id is None:
                # 没有 lifecycle_id 的事件不参与状态机投影；
                # 这种事件在事件层只应是异常值，正常流水线不会出现
                continue
            structure_events.setdefault(event.structure_id, {}).setdefault(
                event.lifecycle_id, []
            ).append(event)

    # 按结构 + lifecycle 排序，方便逐日扫描
    for sid, lifecycles in structure_events.items():
        for lid, events in lifecycles.items():
            events.sort(key=lambda e: e.available_date)

    bottoms = [s for s in structures if s.side == "bottom"]
    tops = [s for s in structures if s.side == "top"]
    structure_by_id: dict[str, StructureInstance] = {s.structure_id: s for s in structures}

    history: list[DayState] = []

    # 当前活跃观察（每日滚动更新）：{ structure_id: StructureObservation }
    active_observations: dict[str, StructureObservation] = {}
    # 当日是否刚发生过转黑（用于在 reasons 里提示）
    last_black_day: date | None = None

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

        # ---- 1) 处理颜色转黑：删除所有观察实例（结构继续存活）----
        if color is SignalColor.BLACK:
            for sid in list(active_observations.keys()):
                structure = structure_by_id.get(sid)
                if structure is None:
                    active_observations.pop(sid, None)
                    continue
                # 结构失效由下一段统一处理；这里直接删除整条观察
                active_observations.pop(sid, None)
            last_black_day = day
        else:
            last_black_day = None

        # ---- 2) 按事件逐日推进观察实例 ----
        # 取出当天所有绑定到底部结构的事件（按时间排序）
        day_events_by_sid: dict[str, list[object]] = {}
        for sid, lifecycles in structure_events.items():
            for lid, events in lifecycles.items():
                for event in events:
                    if event.available_date == day:
                        day_events_by_sid.setdefault(sid, []).append(event)

        for sid, day_events in day_events_by_sid.items():
            structure = structure_by_id.get(sid)
            if structure is None:
                continue
            # 结构已失效 → 整条观察实例永久消失
            if structure.invalidated_date is not None and structure.invalidated_date <= day:
                active_observations.pop(sid, None)
                continue
            # 不再 live 的结构（理论不会发生，但兜底）
            if not _bottom_is_live_on(structure, day):
                active_observations.pop(sid, None)
                continue
            # 转黑日不开启/推进新实例（已在第 1 步把所有 tier 关闭）
            if color is SignalColor.BLACK:
                continue
            # 同一日多条事件：按时间顺序处理后取最后档位
            current = active_observations.get(sid)
            for event in day_events:
                if current is None or current.lifecycle_id != event.lifecycle_id:
                    # 新实例开启
                    tier = event.evidence.get("tier")
                    if not isinstance(tier, str):
                        continue
                    current = StructureObservation(
                        structure_id=sid,
                        lifecycle_id=event.lifecycle_id,
                        tier=tier,
                        opened_on=event.available_date,
                        last_upgraded_on=event.available_date,
                    )
                else:
                    # 同一 lifecycle 内的升级
                    tier = event.evidence.get("tier")
                    if not isinstance(tier, str):
                        continue
                    if current.tier is None or TIER_RANK[tier] > TIER_RANK[current.tier]:
                        current = StructureObservation(
                            structure_id=current.structure_id,
                            lifecycle_id=current.lifecycle_id,
                            tier=tier,
                            opened_on=current.opened_on,
                            last_upgraded_on=event.available_date,
                        )
            if current is not None:
                active_observations[sid] = current

        # ---- 3) 失效结构清理（覆盖到当前 day）----
        for sid in list(active_observations.keys()):
            structure = structure_by_id.get(sid)
            if structure is None or not _bottom_is_live_on(structure, day):
                active_observations.pop(sid, None)

        # ---- 4) 派生机会阶段 ----
        opportunity, opp_reasons = _resolve_opportunity(
            live_bottoms=live_bottoms,
            confirmed_bottoms=confirmed_bottoms,
            observations=active_observations,
            structure_by_id=structure_by_id,
            color=color,
        )

        # 兼容字段（按结构活跃度导出）
        early_strength_map: dict[str, bool] = {}
        early_watch_map: dict[str, bool] = {}
        for sid, obs in active_observations.items():
            if obs.tier is None:
                continue
            if obs.tier == TIER_EARLY_WATCH:
                early_watch_map[sid] = True
            elif _tier_is_buy_signal(obs.tier):
                early_strength_map[sid] = True

        # 主结构早期转强（向后兼容）
        if primary is not None:
            primary_obs = active_observations.get(primary.structure_id)
            if primary_obs is not None and _tier_is_buy_signal(primary_obs.tier):
                primary_early_active = True
                primary_early_date = primary_obs.last_upgraded_on
                primary_early_sid = primary.structure_id
            else:
                primary_early_active = False
                primary_early_date = None
                primary_early_sid = None
        else:
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

        risk, risk_reasons = _resolve_risk(
            color=color,
            active_top=active_top,
            structures=structures,
            day=day,
        )

        # 在 reasons 里追加观察档的可读解释（UI 展示用）
        if any(obs.tier == TIER_EARLY_WATCH for obs in active_observations.values()):
            opp_reasons = list(opp_reasons) + ["候选结构出现 EMA20 观察档（不抬升阶段）"]

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
                observations=dict(active_observations),
                early_strength_by_structure=early_strength_map,
                early_watch_by_structure=early_watch_map,
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
    observations: dict[str, StructureObservation],
    structure_by_id: dict[str, StructureInstance],
    color: SignalColor,
) -> tuple[Stage, list[str]]:
    """机会阶段（不混入风险）。

    Round 3 修复 D1：删去「``live_bottoms and joint_now``」分支。
    机会阶段**只能**由「该结构自身的观察档位」决定：

      * 无任何 live 底部结构 → ``NO_CLUE``
      * 有 live 候选结构但无观察档位 → ``BOTTOM_WATCH``
      * 有候选结构且候选上绑定了 ``early_watch`` → **仍**为 ``BOTTOM_WATCH``
        （观察档不抬阶段）
      * 有已确认结构但**自身**没有观察档位 → ``STRUCTURE_CONFIRMED``
        （确认事实本身就是结构维度的进展；观察档位是另一个维度）
      * 已确认结构上的 ``structure_confirmed`` → ``EARLY_STRENGTH``
      * 已确认结构上的 ``joint_confirmed`` → ``JOINT_CONFIRMED``
      * 已确认结构上的 ``long_trend_improved`` → ``TREND_REINFORCED``

    真值表 13 行（见 ``ROUND3_IMPLEMENTATION_PLAN.md``）逐条对应。
    """
    reasons: list[str] = []
    if not live_bottoms:
        return Stage.NO_CLUE, reasons
    opportunity, best_rank = _max_active_tier_for_stage(observations, structure_by_id)
    # 候选观察档本身不抬阶段；如果事件层给出了更高档（结构已确认 + 转强），
    # _max_active_tier_for_stage 已将其映射到 EARLY_STRENGTH 及以上。
    if opportunity is Stage.NO_CLUE:
        # 没有活跃的观察档位时再按「结构自身状态」做兜底
        if confirmed_bottoms:
            opportunity = Stage.STRUCTURE_CONFIRMED
        else:
            opportunity = Stage.BOTTOM_WATCH
    reasons.append(
        f"存在{len(live_bottoms)}个有效底部线索，"
        f"最高活跃观察档位 rank={best_rank}"
    )
    if confirmed_bottoms:
        reasons.append(f"其中 {len(confirmed_bottoms)} 个结构已确认")
    # 阶段名放入 reasons：UI / 复核需要知道「这次为什么是这个阶段」，
    # 单看数字 rank 不直观。给一个稳定的可读名称。
    if opportunity is Stage.STRUCTURE_CONFIRMED:
        reasons.append("阶段：结构确认（已确认结构尚无转强）")
    elif opportunity is Stage.EARLY_STRENGTH:
        reasons.append("阶段：早期转强（结构确认 + EMA20 转强）")
    elif opportunity is Stage.JOINT_CONFIRMED:
        reasons.append("阶段：共同确认（双均线共同向上）")
    elif opportunity is Stage.TREND_REINFORCED:
        reasons.append("阶段：趋势增强（长周期支持/改善）")
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


__all__ = ["DayState", "StructureObservation", "run_state_machine"]
