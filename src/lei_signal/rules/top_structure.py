"""顶部结构：两个递减确认高点 + 跌破颈线，新高解除。

顶部只产生风险提示，不自动卖出。
被新高解除后不得继续参与 Top+Black（门禁 9）。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import (
    Direction,
    Pivot,
    Severity,
    SignalEvent,
    StructureInstance,
    StructureStatus,
)
from lei_signal.events.log import make_event
from lei_signal.features.pivots import swing_highs


def detect_top_structures(
    frame: pd.DataFrame,
    pivots: tuple[Pivot, ...],
    symbol: str,
) -> list[StructureInstance]:
    """两个确认高点构成顶部警报。

    第二高点低于第一高点；两高点之间最低价为颈线；
    收盘跌破颈线时确认；后续最高价突破第一高点时警报失效。
    """
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
        detected = second.available_date

        structure = StructureInstance(
            structure_id=make_event_id(
                rule_id="structure_top",
                rule_version=spec.version,
                symbol=symbol,
                timeframe="1d",
                available_date=detected,
                source_id=f"neck={neckline:.6f}",
            ),
            symbol=symbol,
            structure_type="top_structure",
            side="top",
            detected_date=detected,
            neckline=neckline,
            reference_high=float(first.price),
            status=StructureStatus.CANDIDATE,
            provenance=spec.provenance,
        )

        after = frame.loc[frame.index > pd.Timestamp(detected)]
        if after.empty:
            structures.append(structure)
            continue

        # 确认：收盘跌破颈线
        breakdown = after.loc[after["close"] < neckline]
        if not breakdown.empty:
            structure.confirmed_date = breakdown.index[0].date()
            structure.status = StructureStatus.CONFIRMED

            # 解除：确认后最高价突破第一高点
            post = after.loc[after.index > breakdown.index[0]]
            new_high = post.loc[post["high"] > first.price]
            if not new_high.empty:
                structure.status = StructureStatus.INVALIDATED
                structure.invalidated_date = new_high.index[0].date()
                structure.invalidated_reason = "top_warning_invalidated_by_new_high"
        structures.append(structure)
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
