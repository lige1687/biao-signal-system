"""严格构造识别（规格 §7.1–§7.3 / 手册 2.6，V2.1 标定，§15 第一轮落地）。

主实现 = 严格构造识别（〔标定 V2.1，待彪哥确认〕；备选代理 = 已确认
swing 左3右3 分形，见 ``features/pivots.py``，档位敏感性 2/2、3/3、5/5）：

- **包含关系剔除**（规格 §7.3 / 手册 2.6 复杂构造）：一根 K 线的高低区间
  完全包住若干 K 线时，被包含者视为不存在——合并为一条合成 K 线
  （high 取 max、low 取 min），其完成时点 = 被合并组最后一根真实 K 线的
  收盘（此前所有组成 K 线均已收盘，合并结果在当日收盘即完全可知，无泄漏）。
- **顶部构造**：合并后 M1→M2 的 M2.high < M1.high（lower high，LH）已建立，
  后续合并 K 线 M_k（“第三根”，可以隔多根，对应复杂构造）的
  M_k.low < M2.low（lower low，LL）即确认，确认日 = M_k 完成日当根收盘
  生效、不额外等待（与「最简构造就是三根 K 线」一致）。
- **极端构造**（规格 §7.3）：创新高的 K 线直接杀出 lower low 的两根情形
  （M2.low 已 < M1.low）同样适用上述规则——仍需其后的合并 K 线创出低于
  M2.low 的新低才确认。
- **失效**：顶部确认后价格重新突破构造前最高点（M1.high，higher high）
  -> 本构造作废，重新找下一个；底部镜像（跌破 M1.low 创新低作废）。
- **波段**：顶 + 底相连 = 一个波段，最小 3+3=6 根不共用——作为后验统计
  维度记录（evidence.min_wave_bars），不改变构造确认本身。

构造是路标不是路（规格 §7.4）：本模块只产生确认/失效事件，不产生交易
指令；可被新高/新低破坏，破坏了就找下一个，不抱旧信号当圣杯。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "strict_structure"
SUB_RULE_TOP_CONFIRMED = "top_structure_strict_confirmed"
SUB_RULE_BOTTOM_CONFIRMED = "bottom_structure_strict_confirmed"
SUB_RULE_TOP_INVALIDATED = "top_structure_strict_invalidated"
SUB_RULE_BOTTOM_INVALIDATED = "bottom_structure_strict_invalidated"

SIDE_TOP = "top"
SIDE_BOTTOM = "bottom"


@dataclass(frozen=True, slots=True)
class MergedBar:
    """包含合并后的合成 K 线。完成日 = 组内最后一根真实 K 线日期。"""

    high: float
    low: float
    first_date: date
    completed_date: date
    source_bars: int


@dataclass(frozen=True, slots=True)
class _Pending:
    """LH/HL 已建立、等待第三根（LL/HH）确认的候选构造。"""

    ref_price: float      # M1 极值（顶部=high，底部=low）
    ref_date: date
    trigger_price: float  # M2 极值（顶部=low，底部=high）
    trigger_date: date
    merged_count: int


@dataclass(slots=True)
class StrictStructure:
    """一次已确认的顶/底构造及其失效轨迹。"""

    side: str
    confirmed_date: date
    # 顶部：reference_price = 构造前最高点（M1.high）；trigger_price = M2.low；
    # final_price = 确认 LL 的 M_k.low。底部镜像。
    reference_price: float
    trigger_price: float
    final_price: float
    reference_date: date
    contained_bars_merged: int
    structure_id: str = ""
    invalidated_date: date | None = None
    invalidated_reason: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.invalidated_date is None


def _params(spec: RuleSpec) -> tuple[bool, int, int]:
    return (
        bool(spec.param("containment_merge", True)),
        int(spec.param("min_bars", 3)),
        int(spec.param("min_wave_bars", 6)),
    )


def merge_contained_bars(frame: pd.DataFrame) -> list[MergedBar]:
    """把日线按包含关系合并为合成 K 线序列。

    相邻两根 K 线区间互含（任一方的 [low, high] 完全覆盖另一方）即合并；
    合并结果继续与下一根比较（链式包含）。非包含则开新条。
    """
    merged: list[MergedBar] = []
    for timestamp, row in frame.iterrows():
        day = timestamp.date()
        high = float(row["high"])
        low = float(row["low"])
        if merged:
            last = merged[-1]
            contains = (
                high <= last.high and low >= last.low
            ) or (
                high >= last.high and low <= last.low
            )
            if contains:
                merged[-1] = MergedBar(
                    high=max(last.high, high),
                    low=min(last.low, low),
                    first_date=last.first_date,
                    completed_date=day,
                    source_bars=last.source_bars + 1,
                )
                continue
        merged.append(
            MergedBar(
                high=high, low=low, first_date=day, completed_date=day, source_bars=1
            )
        )
    return merged


def detect_strict_structures(frame: pd.DataFrame) -> list[StrictStructure]:
    """识别全部严格顶/底构造（含后续失效轨迹），按确认日升序。

    顶部与底部是两台独立的状态机（各自跟踪 LH/HL 起点），同一根合并 K 线
    可能同时推进两台机器（顶部确认后底部构造随后形成，波段交替）。
    """
    _containment, _min_bars, _min_wave = _params(get_rule(RULE_ID))
    bars = merge_contained_bars(frame)
    structures: list[StrictStructure] = []
    pending_top: _Pending | None = None
    pending_bottom: _Pending | None = None

    for index, bar in enumerate(bars):
        previous = bars[index - 1] if index > 0 else None

        # ---- 顶部：LH = M2.high < M1.high；LL = M_k.low < M2.low ----
        if pending_top is not None:
            if bar.high > pending_top.ref_price:
                pending_top = None  # 构造前最高点被突破：候选作废，重新找下一个
            elif bar.low < pending_top.trigger_price:
                structures.append(
                    StrictStructure(
                        side=SIDE_TOP,
                        confirmed_date=bar.completed_date,
                        reference_price=pending_top.ref_price,
                        trigger_price=pending_top.trigger_price,
                        final_price=bar.low,
                        reference_date=pending_top.ref_date,
                        contained_bars_merged=pending_top.merged_count,
                    )
                )
                pending_top = None

        # ---- 底部：HL = M2.low > M1.low；HH = M_k.high > M2.high ----
        if pending_bottom is not None:
            if bar.low < pending_bottom.ref_price:
                pending_bottom = None  # 构造前最低点被跌破：候选作废
            elif bar.high > pending_bottom.trigger_price:
                structures.append(
                    StrictStructure(
                        side=SIDE_BOTTOM,
                        confirmed_date=bar.completed_date,
                        reference_price=pending_bottom.ref_price,
                        trigger_price=pending_bottom.trigger_price,
                        final_price=bar.high,
                        reference_date=pending_bottom.ref_date,
                        contained_bars_merged=pending_bottom.merged_count,
                    )
                )
                pending_bottom = None

        # ---- 新候选起点：与前一合并 K 线比较 ----
        if previous is not None:
            if pending_top is None and bar.high < previous.high:
                pending_top = _Pending(
                    ref_price=previous.high,
                    ref_date=previous.completed_date,
                    trigger_price=bar.low,
                    trigger_date=bar.completed_date,
                    merged_count=previous.source_bars + bar.source_bars,
                )
            if pending_bottom is None and bar.low > previous.low:
                pending_bottom = _Pending(
                    ref_price=previous.low,
                    ref_date=previous.completed_date,
                    trigger_price=bar.high,
                    trigger_date=bar.completed_date,
                    merged_count=previous.source_bars + bar.source_bars,
                )

    for structure in structures:
        structure.structure_id = (
            f"strict_{'top' if structure.side == SIDE_TOP else 'bottom'}:"
            f"{structure.confirmed_date.isoformat()}"
        )

    # ---- 失效轨迹：确认后价格重新突破构造前极值（含盘中） ----
    if structures:
        highs = {
            timestamp.date(): float(row["high"])
            for timestamp, row in frame.iterrows()
        }
        lows = {
            timestamp.date(): float(row["low"])
            for timestamp, row in frame.iterrows()
        }
        for structure in structures:
            if structure.side == SIDE_TOP:
                for day in sorted(d for d in highs if d > structure.confirmed_date):
                    if highs[day] > structure.reference_price:
                        structure.invalidated_date = day
                        structure.invalidated_reason = "higher_high_breaks_top"
                        break
            else:
                for day in sorted(d for d in lows if d > structure.confirmed_date):
                    if lows[day] < structure.reference_price:
                        structure.invalidated_date = day
                        structure.invalidated_reason = "new_low_breaks_bottom"
                        break
    return structures


def _confirmed_event(
    *, spec: RuleSpec, symbol: str, structure: StrictStructure
) -> SignalEvent:
    is_top = structure.side == SIDE_TOP
    sub_rule = SUB_RULE_TOP_CONFIRMED if is_top else SUB_RULE_BOTTOM_CONFIRMED
    reason = (
        "严格顶部构造确认：包含合并后 lower high + lower low 三根完成，"
        "第三根收盘当根生效（规格 §7.1/§7.3，手册 2.6）"
        if is_top
        else "严格底部构造确认：包含合并后 higher low + higher high 三根完成，"
        "第三根收盘当根生效（规格 §7.2/§7.3，手册 2.6）"
    )
    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=structure.confirmed_date,
            source_id=f"{structure.structure_id}:{sub_rule}",
        ),
        symbol=symbol,
        event_date=structure.confirmed_date,
        available_date=structure.confirmed_date,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.BEARISH if is_top else Direction.BULLISH,
        severity=Severity.WATCH,
        strength=60,
        reason_cn=reason,
        provenance=spec.provenance,
        structure_id=structure.structure_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "side": structure.side,
            "reference_price": structure.reference_price,
            "reference_date": structure.reference_date.isoformat(),
            "trigger_price": structure.trigger_price,
            "final_price": structure.final_price,
            "contained_bars_merged": structure.contained_bars_merged,
            "min_wave_bars": 6,
        },
        invalidation={
            "condition": (
                "顶部构造：价格重新突破构造前最高点（reference_price）即作废；"
                "底部构造：价格重新跌破构造前最低点（reference_price）即作废"
                "（规格 §7.3，可被新高/新低破坏，破坏了就找下一个）"
            )
        },
    )


def _invalidated_event(
    *, spec: RuleSpec, symbol: str, structure: StrictStructure
) -> SignalEvent:
    is_top = structure.side == SIDE_TOP
    sub_rule = SUB_RULE_TOP_INVALIDATED if is_top else SUB_RULE_BOTTOM_INVALIDATED
    reason = (
        "严格顶部构造失效：价格重新突破构造前最高点，本构造作废、重新找下一个"
        if is_top
        else "严格底部构造失效：价格重新跌破构造前最低点创新低，本构造作废、重新找下一个"
    )
    assert structure.invalidated_date is not None
    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=structure.invalidated_date,
            source_id=f"{structure.structure_id}:{sub_rule}",
        ),
        symbol=symbol,
        event_date=structure.invalidated_date,
        available_date=structure.invalidated_date,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.NEUTRAL,
        severity=Severity.INFO,
        strength=30,
        reason_cn=reason,
        provenance=spec.provenance,
        structure_id=structure.structure_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "side": structure.side,
            "confirmed_date": structure.confirmed_date.isoformat(),
            "reference_price": structure.reference_price,
            "invalidated_reason": structure.invalidated_reason,
        },
    )


def detect_strict_structure_events(
    frame: pd.DataFrame, symbol: str
) -> list[SignalEvent]:
    """严格顶/底构造确认与失效事件（按 available_date 升序）。"""
    if frame.empty or not {"high", "low"}.issubset(frame.columns):
        return []
    spec = get_rule(RULE_ID)
    events: list[SignalEvent] = []
    for structure in detect_strict_structures(frame):
        events.append(_confirmed_event(spec=spec, symbol=symbol, structure=structure))
        if structure.invalidated_date is not None:
            events.append(
                _invalidated_event(spec=spec, symbol=symbol, structure=structure)
            )
    events.sort(key=lambda event: (event.available_date, event.event_id))
    return events


__all__ = [
    "MergedBar",
    "RULE_ID",
    "SIDE_BOTTOM",
    "SIDE_TOP",
    "SUB_RULE_BOTTOM_CONFIRMED",
    "SUB_RULE_BOTTOM_INVALIDATED",
    "SUB_RULE_TOP_CONFIRMED",
    "SUB_RULE_TOP_INVALIDATED",
    "StrictStructure",
    "detect_strict_structure_events",
    "detect_strict_structures",
    "merge_contained_bars",
]
