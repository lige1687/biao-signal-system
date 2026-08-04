"""事件生命周期：为每个事件分配 ``valid_until`` / ``lifecycle_id`` / ``ended_event_id``。

从 ``compose.pipeline`` 抽出，理由：pipeline 只应负责编排（取数 → 规则 → 结构 →
状态机 → 解释），生命周期是事件域自身的规则，集中在 pipeline 会让编排层不断膨胀。

区间语义（全局唯一标准，不得在别处另立口径）
------------------------------------------------
事件在某日 ``day`` 处于 active，当且仅当::

    available_date <= day < valid_until

即 ``valid_until`` 是**开区间上界（exclusive）**：

* 状态在 D 日结束 → ``valid_until = D`` → 该事件在 **D 日当天已不算 active**，
  归入 ended（「当日结束不算 active」）；
* 单次脉冲事件 → ``valid_until = available_date + 1 天`` → 只在当日作为 new 出现；
* 直到样本末仍未结束 → ``valid_until = last_date + 1 天``，而**不是** ``None``。

``valid_until is None`` 只表示「尚未分配」。本模块执行完毕后，任何事件都不应再
保持 ``None``——否则该事件会被解释层视为「永久有效」而无限累积。

生命周期分类
------------------------------------------------
==================  ====================================================
类别                 结束条件
==================  ====================================================
PULSE                触发次日即结束（历史事实，不是持续状态）
CHAIN                同一规则的下一个 start 结束上一个实例
PAIRED               显式的 ``*_ended`` 配对事件结束对应 start
STRUCTURE            跟随关联结构的生命周期（失效日结束）
STRUCTURE_BOUND      绑定底部结构的转强：结构失效或转黑即结束
==================  ====================================================
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, timedelta
from typing import TYPE_CHECKING

from lei_signal.domain.types import SignalColor, SignalEvent, StructureInstance

if TYPE_CHECKING:
    from lei_signal.state.machine import DayState

#: 脉冲事件（按 rule_id）：客观历史事实，触发日之后立即结束。
#: 摆动点、量能、反转 K 线、C 触及/跌破、双均线开口读数、长周期交叉都属于此类。
PULSE_RULES = frozenset(
    {
        "swing_pivots",
        "volume_proxies",
        "bottom_c_lifecycle",
        "bullish_engulfing",
        "bullish_outside_reversal",
        "bearish_engulfing",
        "bearish_outside_reversal",
        "bullish_reversal_bottom",
        "dual_ma_spread",
        "long_trend",
        "first_ma_pullback",
    }
)

#: 链式状态事件（按 rule_id）：规则内只允许一个实例 active，
#: 下一个 start 出现即结束上一个实例。
CHAIN_RULES = frozenset({"lei_color", "dual_ma_bull_confirmed"})

#: 显式 start/end 配对（按 evidence["sub_rule"]）。
#: 注意这些是 **sub_rule**，不是 rule_id——两者混用会让分类整段失效。
PAIRED_SUB_RULES: dict[str, str] = {
    "key_wave_black_started": "key_wave_black_ended",
    "top_plus_black": "top_plus_black_ended",
}

#: 所有结束标记 sub_rule：这些事件本身永远不能 active。
END_SUB_RULES = frozenset(PAIRED_SUB_RULES.values()) | {
    "top_warning_invalidated_by_new_high",
}

#: 跟随结构生命周期的事件（按 rule_id）。
STRUCTURE_RULES = frozenset({"higher_low_bottom", "double_bottom", "top_structure"})

#: 绑定到具体底部结构的早期转强。
STRUCTURE_BOUND_RULES = frozenset({"ema20_reclaim_rising"})


def _sub_rule(event: SignalEvent) -> str:
    value = event.evidence.get("sub_rule")
    return value if isinstance(value, str) else ""


def _next_day(day: date) -> date:
    return day + timedelta(days=1)


def _sort_key(event: SignalEvent) -> tuple[date, str]:
    return (event.available_date, event.event_id)


def _instance_id(prefix: str, scope: str | None, day: date) -> str:
    """状态实例 ID：同一状态重新进入必然产生不同的 ID（含进入日期）。"""
    return f"{prefix}:{scope or '-'}:{day.isoformat()}"


def _structure_end(
    structure: StructureInstance | None,
    horizon: date,
) -> date:
    """结构关联事件的结束日（exclusive）。

    结构在 I 日失效 → 事件 ``valid_until = I`` → I 日当天已不是 active，
    与「``invalidated_date <= day`` 即视为已死」的口径一致。
    """
    if structure is None or structure.invalidated_date is None:
        return horizon
    return min(structure.invalidated_date, horizon)


def _chain_state_holds(rule_id: str, event: SignalEvent, state: DayState) -> bool:
    """链式状态事件在某日是否仍然成立。

    独立的纯函数：不捕获任何循环变量，避免闭包延迟绑定（ruff B023）。
    """
    if rule_id == "lei_color":
        return state.color.value == event.evidence.get("color")
    if rule_id == "dual_ma_bull_confirmed":
        return bool(state.joint_confirmed_now)
    return False


def _chain_state_stop(
    rule_id: str,
    event: SignalEvent,
    history: list[DayState],
    horizon: date,
) -> date:
    """链式事件真正停止成立的那一天（exclusive 上界）。

    从进入日往后连续扫描，取「最后一个仍成立的交易日 + 1 天」。
    若一路成立到样本末，结果自然等于 ``horizon``。

    必须对**每一个**实例都做这次扫描，不能只处理最后一个：
    像 ``dual_ma_bull_confirmed`` 这类「只在进入态时发事件」的规则，
    状态可以 true → false → true，两次 start 之间存在一段 false。
    若用「下一个 start」当结束点，中间那段 false 会被误判为仍然成立。
    """
    last_holding: date | None = None
    for state in history:
        if state.day < event.available_date:
            continue
        if _chain_state_holds(rule_id, event, state):
            last_holding = state.day
        else:
            break
    if last_holding is None:
        # 进入当日即不成立（理论上不该发生）：给出零长度区间而不是永久有效
        return event.available_date
    return min(_next_day(last_holding), horizon)


def assign_lifecycles(
    events: list[SignalEvent],
    structures: list[StructureInstance],
    history: list[DayState],
    last_date: date,
) -> list[SignalEvent]:
    """为所有事件写入 ``valid_until`` / ``lifecycle_id`` / ``ended_event_id``。

    就地修改并返回同一批事件（``SignalEvent`` 为可变 dataclass）。
    返回后保证**没有任何事件** ``valid_until is None``。
    """
    if not events:
        return events

    horizon = _next_day(last_date)
    structure_by_id = {s.structure_id: s for s in structures}
    black_days = sorted(
        state.day for state in history if state.color is SignalColor.BLACK
    )

    chain_groups: dict[str, list[SignalEvent]] = defaultdict(list)
    paired_starts: dict[tuple[str, str | None], list[SignalEvent]] = defaultdict(list)
    paired_ends: dict[tuple[str, str | None], list[SignalEvent]] = defaultdict(list)
    structure_groups: dict[tuple[str, str | None], list[SignalEvent]] = defaultdict(list)
    bound_groups: dict[str, list[SignalEvent]] = defaultdict(list)
    fallback_groups: dict[tuple[str, str], list[SignalEvent]] = defaultdict(list)

    for event in events:
        sub_rule = _sub_rule(event)
        # 结束标记事件：本身是脉冲，且永远不进 active
        if sub_rule in END_SUB_RULES:
            _mark_pulse(event, horizon)
            start_key = _paired_key_for_end(sub_rule, event)
            if start_key is not None:
                paired_ends[start_key].append(event)
            continue
        if event.rule_id in PULSE_RULES:
            _mark_pulse(event, horizon)
            continue
        if sub_rule in PAIRED_SUB_RULES:
            paired_starts[(sub_rule, event.structure_id)].append(event)
            continue
        if event.rule_id in CHAIN_RULES:
            chain_groups[event.rule_id].append(event)
            continue
        if event.rule_id in STRUCTURE_BOUND_RULES:
            bound_groups[event.structure_id or ""].append(event)
            continue
        if event.rule_id in STRUCTURE_RULES:
            structure_groups[(event.rule_id, event.structure_id)].append(event)
            continue
        # 未登记的规则：按 (rule_id, sub_rule) 链式收敛，
        # 保证新规则接入时不会因为忘记登记而无限累积 active 事件。
        fallback_groups[(event.rule_id, sub_rule)].append(event)

    _assign_chain(chain_groups, history, horizon)
    _assign_paired(paired_starts, paired_ends, horizon)
    _assign_structure(structure_groups, structure_by_id, horizon)
    _assign_structure_bound(bound_groups, structure_by_id, black_days, horizon)
    _assign_fallback(fallback_groups, horizon)

    return events


def _mark_pulse(event: SignalEvent, horizon: date) -> None:
    event.valid_until = min(_next_day(event.available_date), horizon)
    event.lifecycle_id = None


def _paired_key_for_end(
    sub_rule: str,
    event: SignalEvent,
) -> tuple[str, str | None] | None:
    """把结束事件映射回它所结束的 start 分组键。"""
    for start_sub, end_sub in PAIRED_SUB_RULES.items():
        if end_sub == sub_rule:
            return (start_sub, event.structure_id)
    return None


def _assign_chain(
    groups: dict[str, list[SignalEvent]],
    history: list[DayState],
    horizon: date,
) -> None:
    for rule_id, group in groups.items():
        group.sort(key=_sort_key)
        for index, event in enumerate(group):
            # 主判据：状态自身停止成立的那一天
            end = _chain_state_stop(rule_id, event, history, horizon)
            # 附加上界：同规则的下一个 start 必然终止上一个实例
            following = next(
                (
                    later
                    for later in group[index + 1 :]
                    if later.available_date > event.available_date
                ),
                None,
            )
            if following is not None:
                end = min(end, following.available_date)
            event.valid_until = max(end, event.available_date)
            event.lifecycle_id = _instance_id(
                rule_id, _sub_rule(event), event.available_date
            )


def _assign_paired(
    starts: dict[tuple[str, str | None], list[SignalEvent]],
    ends: dict[tuple[str, str | None], list[SignalEvent]],
    horizon: date,
) -> None:
    for key, group in starts.items():
        sub_rule, scope = key
        group.sort(key=_sort_key)
        pending = deque(sorted(ends.get(key, []), key=_sort_key))
        for event in group:
            # 丢弃发生在本次进入之前的结束事件（属于更早的实例）
            while pending and pending[0].available_date <= event.available_date:
                pending.popleft()
            if pending:
                closing = pending.popleft()
                event.valid_until = min(closing.available_date, horizon)
                event.ended_event_id = closing.event_id
            else:
                # 没有配对的结束事件 = 状态一直持续到样本末
                event.valid_until = horizon
            event.lifecycle_id = _instance_id(sub_rule, scope, event.available_date)


def _assign_structure(
    groups: dict[tuple[str, str | None], list[SignalEvent]],
    structure_by_id: dict[str, StructureInstance],
    horizon: date,
) -> None:
    for key, group in groups.items():
        rule_id, scope = key
        structure = structure_by_id.get(scope) if scope else None
        end = _structure_end(structure, horizon)
        group.sort(key=_sort_key)
        for index, event in enumerate(group):
            following = next(
                (
                    later
                    for later in group[index + 1 :]
                    if later.available_date > event.available_date
                ),
                None,
            )
            candidate = end if following is None else min(following.available_date, end)
            event.valid_until = max(candidate, event.available_date)
            event.lifecycle_id = _instance_id(rule_id, scope, event.available_date)


def _assign_structure_bound(
    groups: dict[str, list[SignalEvent]],
    structure_by_id: dict[str, StructureInstance],
    black_days: list[date],
    horizon: date,
) -> None:
    """EMA20 早期转强：每个底部结构一条独立的生命周期链。

    * C 失效只终止**对应结构**的转强，不影响其他结构（多结构多对多）；
    * 颜色转黑立即终止；
    * **分档升级事件与开启事件共享 ``lifecycle_id``**，同属一条观察实例。
      因此结束点按「实例」而不是按「事件」计算：升级不得提前结束开启事件，
      同一实例内所有事件共享同一个 ``valid_until``。若按事件计算，一次
      early_watch → structure_confirmed 的升级会把开启事件的活跃区间截成
      一两天，研究层看到的持有窗口全是错的。
    * 转黑之后再次转强 → 新实例（新 ``lifecycle_id``），旧实例在新实例开始日结束；
    * 新底部结构不会继承旧结构的转强：分组键就是 structure_id。
    """
    for structure_id, group in groups.items():
        structure = structure_by_id.get(structure_id)
        end = _structure_end(structure, horizon)
        group.sort(key=_sort_key)
        instances = _split_instances(group)
        for index, instance in enumerate(instances):
            opened = instance[0].available_date
            candidate = end
            following = next(
                (
                    later[0].available_date
                    for later in instances[index + 1 :]
                    if later[0].available_date > opened
                ),
                None,
            )
            if following is not None:
                candidate = min(candidate, following)
            black = next((d for d in black_days if d > opened), None)
            if black is not None:
                candidate = min(candidate, black)
            for event in instance:
                event.valid_until = max(candidate, event.available_date)
                if event.lifecycle_id is None:
                    event.lifecycle_id = _instance_id(
                        event.rule_id, structure_id, opened
                    )


def _split_instances(group: list[SignalEvent]) -> list[list[SignalEvent]]:
    """把同一结构下的事件按 ``lifecycle_id`` 切成若干条观察实例。

    ``lifecycle_id is None`` 的事件各自独立成实例——绝不静默并入相邻实例，
    否则一个忘记赋 ID 的新规则会悄悄继承别人的生命周期。
    输入需已按 ``_sort_key`` 排序；输出按各实例首个事件的时间排序。
    """
    ordered: list[list[SignalEvent]] = []
    by_lifecycle: dict[str, list[SignalEvent]] = {}
    for event in group:
        key = event.lifecycle_id
        if key is None:
            ordered.append([event])
            continue
        bucket = by_lifecycle.get(key)
        if bucket is None:
            bucket = []
            by_lifecycle[key] = bucket
            ordered.append(bucket)
        bucket.append(event)
    ordered.sort(key=lambda events: _sort_key(events[0]))
    return ordered


def _assign_fallback(
    groups: dict[tuple[str, str], list[SignalEvent]],
    horizon: date,
) -> None:
    for key, group in groups.items():
        rule_id, sub_rule = key
        group.sort(key=_sort_key)
        for index, event in enumerate(group):
            following = next(
                (
                    later
                    for later in group[index + 1 :]
                    if later.available_date > event.available_date
                ),
                None,
            )
            event.valid_until = (
                horizon if following is None else min(following.available_date, horizon)
            )
            event.lifecycle_id = _instance_id(rule_id, sub_rule, event.available_date)


__all__ = [
    "CHAIN_RULES",
    "END_SUB_RULES",
    "PAIRED_SUB_RULES",
    "PULSE_RULES",
    "STRUCTURE_BOUND_RULES",
    "STRUCTURE_RULES",
    "assign_lifecycles",
]
