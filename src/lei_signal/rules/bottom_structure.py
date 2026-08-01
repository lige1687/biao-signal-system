"""底部结构：高低点抬高、双底、反转 K 线底部。

绝对约束（架构 2.1 / 15）：
  底部结构识别器**不得**读取 EMA60/EMA120 或周线趋势。
  长周期不支持只能作为组合层的冲突标签，不能在此 Block 结构。

每个结构保存 C、颈线、来源事件与生命周期。
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
from lei_signal.features.pivots import swing_lows
from lei_signal.rules.reversals import (
    bullish_engulfing_state,
    bullish_outside_reversal_state,
)


def _structure_id(symbol: str, structure_type: str, anchor: date, c_price: float) -> str:
    """结构 ID 必须确定性，使重复运行产生同一 ID。"""
    return make_event_id(
        rule_id=f"structure_{structure_type}",
        rule_version=get_rule(structure_type).version,
        symbol=symbol,
        timeframe="1d",
        available_date=anchor,
        source_id=f"c={c_price:.6f}",
    )


def detect_higher_low_bottoms(
    frame: pd.DataFrame,
    pivots: tuple[Pivot, ...],
    symbol: str,
) -> list[StructureInstance]:
    """高低点抬高型底部。

    连续两个确认摆动低点，第二个高于第一个；两低点之间最高价为颈线；
    收盘突破颈线时确认。C = 第一个（较低的）低点。
    """
    spec = get_rule("higher_low_bottom")
    lows = sorted(swing_lows(pivots), key=lambda p: p.index)
    structures: list[StructureInstance] = []

    for first, second in zip(lows, lows[1:], strict=False):
        if second.price <= first.price:
            continue
        between = frame.iloc[first.index : second.index + 1]
        if between.empty:
            continue
        neckline = float(between["high"].max())
        c_price = float(first.price)

        # 候选自第二个低点确认日起成立
        detected = second.available_date
        structure = StructureInstance(
            structure_id=_structure_id(symbol, "higher_low_bottom", detected, c_price),
            symbol=symbol,
            structure_type="higher_low_bottom",
            side="bottom",
            detected_date=detected,
            c_price=c_price,
            neckline=neckline,
            status=StructureStatus.CANDIDATE,
            provenance=spec.provenance,
        )
        # 确认：确认日之后首个收盘突破颈线
        after = frame.loc[frame.index > pd.Timestamp(detected)]
        breakout = after.loc[after["close"] > neckline]
        if not breakout.empty:
            structure.confirmed_date = breakout.index[0].date()
            structure.status = StructureStatus.CONFIRMED
        structures.append(structure)
    return structures


def detect_double_bottoms(
    frame: pd.DataFrame,
    pivots: tuple[Pivot, ...],
    symbol: str,
) -> list[StructureInstance]:
    """双底：两低点价差不超过第二低点处 1 ATR。"""
    spec = get_rule("double_bottom")
    max_diff_atr = float(spec.param("max_diff_atr", 1.0))
    lows = sorted(swing_lows(pivots), key=lambda p: p.index)
    structures: list[StructureInstance] = []

    atr_column = "atr14" if "atr14" in frame.columns else None

    for first, second in zip(lows, lows[1:], strict=False):
        if atr_column is None:
            continue
        atr_value = frame[atr_column].iloc[second.index]
        if pd.isna(atr_value) or atr_value <= 0:
            continue
        if abs(second.price - first.price) > max_diff_atr * float(atr_value):
            continue

        between = frame.iloc[first.index : second.index + 1]
        neckline = float(between["high"].max())
        c_price = float(min(first.price, second.price))
        detected = second.available_date

        structure = StructureInstance(
            structure_id=_structure_id(symbol, "double_bottom", detected, c_price),
            symbol=symbol,
            structure_type="double_bottom",
            side="bottom",
            detected_date=detected,
            c_price=c_price,
            neckline=neckline,
            status=StructureStatus.CANDIDATE,
            provenance=spec.provenance,
        )
        after = frame.loc[frame.index > pd.Timestamp(detected)]
        breakout = after.loc[after["close"] > neckline]
        if not breakout.empty:
            structure.confirmed_date = breakout.index[0].date()
            structure.status = StructureStatus.CONFIRMED
        structures.append(structure)
    return structures


def detect_reversal_bottoms(
    frame: pd.DataFrame,
    symbol: str,
    reversal_events: list[SignalEvent] | None = None,
) -> list[StructureInstance]:
    """强势反转 K 线独立形成候选底部，不要求先出现双底。

    这是修正「第二根阳线直接反包但系统完全没记录」的核心：
    反转 K 线自身即可建立结构，C = 反转 K 线最低价，
    且**不检查任何长周期条件**。
    """
    spec = get_rule("bullish_reversal_bottom")
    engulfing = bullish_engulfing_state(frame)
    outside = bullish_outside_reversal_state(frame)
    trigger = engulfing | outside

    event_by_date: dict[date, list[str]] = {}
    for event in reversal_events or []:
        if event.direction is Direction.BULLISH:
            event_by_date.setdefault(event.event_date, []).append(event.event_id)

    structures: list[StructureInstance] = []
    for timestamp in frame.index[trigger]:
        row = frame.loc[timestamp]
        trade_date = timestamp.date()
        c_price = float(row["low"])
        source_rule = (
            "bullish_engulfing"
            if bool(engulfing.loc[timestamp])
            else "bullish_outside_reversal"
        )
        structures.append(
            StructureInstance(
                structure_id=_structure_id(
                    symbol, "bullish_reversal_bottom", trade_date, c_price
                ),
                symbol=symbol,
                structure_type="bullish_reversal_bottom",
                side="bottom",
                detected_date=trade_date,
                c_price=c_price,
                neckline=float(row["high"]),   # 反转K线高点作为参考颈线
                confirmed_date=trade_date,     # 反转K线自身即确认（收盘可知）
                status=StructureStatus.CONFIRMED,
                source_event_ids=tuple(event_by_date.get(trade_date, ())),
                source_rule_id=source_rule,
                provenance=spec.provenance,
            )
        )
    return structures


def apply_c_lifecycle(
    frame: pd.DataFrame,
    structures: list[StructureInstance],
    symbol: str,
) -> list[SignalEvent]:
    """C 生命周期：触及即永久失效。

    自确认日的**下一交易日**起：
      Low <= C   -> bottom_C_touched，结构永久失效
      Close < C  -> bottom_C_close_broken（区分盘中触及与收盘跌破）

    触及 C 后旧结构永久失效，后续上涨不能使它复活。
    """
    spec = get_rule("bottom_c_lifecycle")
    events: list[SignalEvent] = []

    for structure in structures:
        if structure.side != "bottom" or structure.c_price is None:
            continue
        if structure.confirmed_date is None:
            continue

        after = frame.loc[frame.index > pd.Timestamp(structure.confirmed_date)]
        if after.empty:
            continue

        touched = after.loc[after["low"] <= structure.c_price]
        if touched.empty:
            continue

        touch_timestamp = touched.index[0]
        touch_date = touch_timestamp.date()
        row = touched.iloc[0]

        # 结构永久失效
        structure.status = StructureStatus.INVALIDATED
        structure.invalidated_date = touch_date
        structure.invalidated_reason = "bottom_C_touched"

        events.append(
            make_event(
                event_id=make_event_id(
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    symbol=symbol,
                    timeframe="1d",
                    available_date=touch_date,
                    source_id=f"touched:{structure.structure_id}",
                ),
                symbol=symbol,
                event_date=touch_date,
                available_date=touch_date,
                rule_id=spec.rule_id,
                rule_version=spec.version,
                direction=Direction.BEARISH,
                severity=Severity.CRITICAL,
                strength=95,
                reason_cn=(
                    f"最低价触及或跌破结构C({structure.c_price:.4f})，"
                    f"该底部结构永久失效"
                ),
                provenance=spec.provenance,
                evidence={
                    "sub_rule": "bottom_C_touched",
                    "c_price": structure.c_price,
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "structure_type": structure.structure_type,
                },
                invalidation={"condition": "已永久失效，后续上涨不能复活"},
                structure_id=structure.structure_id,
            )
        )

        # 收盘有效跌破单独记录
        close_broken = after.loc[after["close"] < structure.c_price]
        if not close_broken.empty:
            break_date = close_broken.index[0].date()
            break_row = close_broken.iloc[0]
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=break_date,
                        source_id=f"close_broken:{structure.structure_id}",
                    ),
                    symbol=symbol,
                    event_date=break_date,
                    available_date=break_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BEARISH,
                    severity=Severity.CRITICAL,
                    strength=98,
                    reason_cn=(
                        f"收盘价有效跌破结构C({structure.c_price:.4f})"
                    ),
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "bottom_C_close_broken",
                        "c_price": structure.c_price,
                        "close": float(break_row["close"]),
                    },
                    invalidation={"condition": "已永久失效"},
                    structure_id=structure.structure_id,
                )
            )
    return events


def detect_bottom_structure_events(
    structures: list[StructureInstance],
    symbol: str,
) -> list[SignalEvent]:
    """底部结构候选与确认事件。"""
    events: list[SignalEvent] = []
    for structure in structures:
        spec = get_rule(structure.structure_type)
        events.append(
            make_event(
                event_id=make_event_id(
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    symbol=symbol,
                    timeframe="1d",
                    available_date=structure.detected_date,
                    source_id=f"candidate:{structure.structure_id}",
                ),
                symbol=symbol,
                event_date=structure.detected_date,
                available_date=structure.detected_date,
                rule_id=spec.rule_id,
                rule_version=spec.version,
                direction=Direction.BULLISH,
                severity=Severity.WATCH,
                strength=45,
                reason_cn=_candidate_reason(structure),
                provenance=spec.provenance,
                evidence={
                    "sub_rule": "candidate",
                    "c_price": structure.c_price,
                    "neckline": structure.neckline,
                    "structure_type": structure.structure_type,
                },
                invalidation={"condition": f"最低价触及C({structure.c_price})"},
                structure_id=structure.structure_id,
            )
        )
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
                    direction=Direction.BULLISH,
                    severity=Severity.IMPORTANT,
                    strength=65,
                    reason_cn=_confirmed_reason(structure),
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "confirmed",
                        "c_price": structure.c_price,
                        "neckline": structure.neckline,
                        "structure_type": structure.structure_type,
                    },
                    invalidation={"condition": f"最低价触及C({structure.c_price})"},
                    structure_id=structure.structure_id,
                )
            )
    return events


_TYPE_CN = {
    "higher_low_bottom": "高低点抬高型底部",
    "double_bottom": "双底",
    "bullish_reversal_bottom": "阳线反转底部",
}


def _candidate_reason(structure: StructureInstance) -> str:
    name = _TYPE_CN.get(structure.structure_type, structure.structure_type)
    suffix = "（研究代理规则）" if structure.provenance is Provenance.RESEARCH_PROXY else ""
    return f"{name}候选成立，C={structure.c_price:.4f}，颈线={structure.neckline:.4f}{suffix}"


def _confirmed_reason(structure: StructureInstance) -> str:
    name = _TYPE_CN.get(structure.structure_type, structure.structure_type)
    if structure.structure_type == "bullish_reversal_bottom":
        return f"{name}成立（反转K线自身即确认），C={structure.c_price:.4f}"
    return f"{name}确认：收盘突破颈线{structure.neckline:.4f}，C={structure.c_price:.4f}"


__all__ = [
    "apply_c_lifecycle",
    "detect_bottom_structure_events",
    "detect_double_bottoms",
    "detect_higher_low_bottoms",
    "detect_reversal_bottoms",
]
