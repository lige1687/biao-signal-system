"""顶部结构：两个递减确认高点 + 跌破颈线，新高解除。

顶部只产生风险提示，不自动卖出。
被新高解除后不得继续参与 Top+Black（门禁 9）。

时间顺序（修复要求）：
  候选可用日 = 第二高点确认日。当天起逐日：
    1. 先**突破第一高点** → 候选作废，结构直接失效，**永不复活**，
       此后即使跌破颈线也不能再确认；
    2. 先**收盘跌破颈线** → 候选确认；
    3. 确认后最高价突破第一高点 → 顶部警报被新高解除（独立事件）。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import (
    Direction,
    Pivot,
    Provenance,
    Severity,
    SignalEvent,
    StructureInstance,
    StructureStatus,
)
from lei_signal.events.log import make_event
from lei_signal.features.pivots import swing_highs


def _walk_top_structure_lifecycle(
    frame: pd.DataFrame,
    *,
    candidate_date: date,
    neckline: float,
    reference_high: float,
    symbol: str,
    structure_type: str,
    provenance: Provenance,
) -> StructureInstance:
    detected = candidate_date
    neckline = float(neckline)
    reference_high = float(reference_high)
    structure_id = make_event_id(
        rule_id=f"structure_{structure_type}",
        rule_version=get_rule(structure_type).version,
        symbol=symbol,
        timeframe="1d",
        available_date=detected,
        source_id=f"neck={neckline:.6f}",
    )
    structure = StructureInstance(
        structure_id=structure_id,
        symbol=symbol,
        structure_type=structure_type,
        side="top",
        detected_date=detected,
        neckline=neckline,
        reference_high=reference_high,
        status=StructureStatus.CANDIDATE,
        provenance=provenance,
    )
    start_ts = pd.Timestamp(detected)
    forward = frame.loc[frame.index >= start_ts]
    if forward.empty:
        return structure
    for ts, row in forward.iterrows():
        # 先看突破第一高点：候选作废，之后跌破颈线也不能再确认
        if float(row["high"]) > reference_high:
            structure.status = StructureStatus.INVALIDATED
            structure.invalidated_date = ts.date()
            structure.invalidated_reason = "top_candidate_broken_by_new_high"
            return structure
        if float(row["close"]) < neckline:
            structure.confirmed_date = ts.date()
            structure.status = StructureStatus.CONFIRMED
            return _advance_top_after_confirm(structure, frame, ts)
    return structure


def _advance_top_after_confirm(
    structure: StructureInstance,
    frame: pd.DataFrame,
    confirmed_ts: pd.Timestamp,
) -> StructureInstance:
    """已确认顶部：从确认日次日起监控新高解除。

    ``reference_high`` 缺失时无法判断「是否创出新高」，
    此时保持结构原状而不是拿默认值假装比较——
    宁可让顶部警报继续有效，也不能凭空解除。
    """
    reference_high = structure.reference_high
    if reference_high is None:
        return structure
    forward = frame.loc[frame.index > confirmed_ts]
    for ts, row in forward.iterrows():
        if float(row["high"]) > reference_high:
            structure.status = StructureStatus.INVALIDATED
            structure.invalidated_date = ts.date()
            structure.invalidated_reason = "top_warning_invalidated_by_new_high"
            return structure
    return structure


def detect_top_structures(
    frame: pd.DataFrame,
    pivots: tuple[Pivot, ...],
    symbol: str,
) -> list[StructureInstance]:
    """两个确认高点构成顶部警报（按时间顺序逐日推进）。"""
    spec = get_rule("top_structure")
    highs = sorted(swing_highs(pivots), key=lambda p: p.index)
    structures: list[StructureInstance] = []
    for first, second in zip(highs, highs[1:], strict=False):
        if second.price >= first.price:
            continue
        between = frame.iloc[first.index : second.index + 1]
        if between.empty:
            continue
        neckline = float(between["low"].min())
        structures.append(
            _walk_top_structure_lifecycle(
                frame,
                candidate_date=second.available_date,
                neckline=neckline,
                reference_high=float(first.price),
                symbol=symbol,
                structure_type="top_structure",
                provenance=spec.provenance,
            )
        )
    return structures


def detect_top_structure_events(
    structures: list[StructureInstance],
    symbol: str,
) -> list[SignalEvent]:
    """顶部确认与解除事件。"""
    spec = get_rule("top_structure")
    events: list[SignalEvent] = []

    for structure in structures:
        if structure.side != "top":
            continue
        if structure.confirmed_date is not None:
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=structure.confirmed_date,
                        source_id=f"confirmed:{structure.structure_id}",
                    ),
                    symbol=symbol,
                    event_date=structure.confirmed_date,
                    available_date=structure.confirmed_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BEARISH,
                    severity=Severity.IMPORTANT,
                    strength=70,
                    reason_cn=(
                        f"顶部警报确认：第二高点低于第一高点"
                        f"({structure.reference_high:.4f})，"
                        f"收盘跌破颈线{structure.neckline:.4f}。仅为风险提示，不构成卖出指令。"
                    ),
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_structure_confirmed",
                        "neckline": structure.neckline,
                        "reference_high": structure.reference_high,
                    },
                    invalidation={
                        "condition": f"最高价突破第一高点{structure.reference_high}"
                    },
                    structure_id=structure.structure_id,
                )
            )
        if structure.invalidated_date is not None:
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=structure.invalidated_date,
                        source_id=f"invalidated:{structure.structure_id}",
                    ),
                    symbol=symbol,
                    event_date=structure.invalidated_date,
                    available_date=structure.invalidated_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BULLISH,
                    severity=Severity.WATCH,
                    strength=40,
                    reason_cn=(
                        f"顶部警报被新高解除：最高价突破第一高点"
                        f"{structure.reference_high:.4f}"
                    ),
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_warning_invalidated_by_new_high",
                        "reference_high": structure.reference_high,
                    },
                    invalidation={"condition": "已解除"},
                    structure_id=structure.structure_id,
                )
            )
    return events


__all__ = ["detect_top_structure_events", "detect_top_structures"]
