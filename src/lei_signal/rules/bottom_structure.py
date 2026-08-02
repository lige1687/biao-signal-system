"""底部结构：高低点抬高、双底、反转 K 线底部。

绝对约束（架构 2.1 / 15 + 修复要求）：
  底部结构识别器**不得**读取 EMA60/EMA120 或周线趋势。
  长周期不支持只能作为组合层的冲突标签，不能在此 Block 结构。

每个结构按时间顺序推进状态：候选 → 确认 → 失效，绝不能跳过候选。
  候选成立后，**逐日**检查：
    1. 先触及或跌破候选 C：候选永久失效，之后突破颈线不能再确认；
    2. 先收盘突破颈线：结构确认。
  已确认结构从确认后的下一交易日起继续检查 C。
  失效结构永不复活。
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


def _walk_bottom_structure_lifecycle(
    frame: pd.DataFrame,
    *,
    candidate_date: date,
    c_price: float,
    neckline: float,
    symbol: str,
    structure_type: str,
    provenance: Provenance,
    source_event_ids: tuple[str, ...] = (),
    source_rule_id: str | None = None,
    structure_id_override: str | None = None,
    confirm_immediately: bool = False,
) -> StructureInstance:
    """逐日推进底部候选 → 确认 → 失效。

    严格按时间顺序：
      * 候选自 `candidate_date` 当天成立；
      * 从**下一交易日**起逐日检查：
          - 先看是否触及 C：是则立即失效；
          - 之后看是否突破颈线：是则确认；
      * 一旦失效，结构**永不复活**——突破颈线也不能再确认。
      * 如果 `confirm_immediately=True`（用于反转 K 线底部），
        候选当日即确认，但仍从次日监控 C 触及。

    此函数**不**引用未来数据；它使用 `frame` 整体但在状态推进时按日期
    单调推进（每个候选都是从 candidate_date 起向前）。
    """
    detected = candidate_date
    c_price = float(c_price)
    neckline = float(neckline)
    structure_id = structure_id_override or _structure_id(
        symbol, structure_type, detected, c_price
    )
    structure = StructureInstance(
        structure_id=structure_id,
        symbol=symbol,
        structure_type=structure_type,
        side="bottom",
        detected_date=detected,
        c_price=c_price,
        neckline=neckline,
        status=StructureStatus.CANDIDATE,
        source_event_ids=source_event_ids,
        source_rule_id=source_rule_id,
        provenance=provenance,
    )
    if confirm_immediately:
        structure.confirmed_date = detected
        structure.status = StructureStatus.CONFIRMED
    # 从候选日的**下一交易日**起逐日监控。
    # 注意：候选日不参与失效/确认判断（结构当时尚未存在/尚未被承认）。
    start_ts = pd.Timestamp(detected)
    forward = frame.loc[frame.index > start_ts]
    if forward.empty:
        return structure
    for ts, row in forward.iterrows():
        if float(row["low"]) <= c_price:
            structure.status = StructureStatus.INVALIDATED
            structure.invalidated_date = ts.date()
            structure.invalidated_reason = "bottom_C_touched_in_candidate"
            return structure
        if not confirm_immediately and float(row["close"]) > neckline:
            structure.confirmed_date = ts.date()
            structure.status = StructureStatus.CONFIRMED
            return _advance_confirmed(structure, frame, ts)
    return structure


def _advance_confirmed(
    structure: StructureInstance,
    frame: pd.DataFrame,
    confirmed_ts: pd.Timestamp,
) -> StructureInstance:
    """已确认结构从确认日次日起监控 C 触及。"""
    forward = frame.loc[frame.index > confirmed_ts]
    for ts, row in forward.iterrows():
        if float(row["low"]) <= structure.c_price:
            structure.status = StructureStatus.INVALIDATED
            structure.invalidated_date = ts.date()
            structure.invalidated_reason = "bottom_C_touched"
            return structure
    return structure


def detect_higher_low_bottoms(
    frame: pd.DataFrame,
    pivots: tuple[Pivot, ...],
    symbol: str,
) -> list[StructureInstance]:
    """高低点抬高型底部：时间顺序推进。"""
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
        structures.append(
            _walk_bottom_structure_lifecycle(
                frame,
                candidate_date=second.available_date,
                c_price=c_price,
                neckline=neckline,
                symbol=symbol,
                structure_type="higher_low_bottom",
                provenance=spec.provenance,
            )
        )
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
    atr_column = "atr14" if "atr14" in frame.columns else None
    structures: list[StructureInstance] = []
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
        structures.append(
            _walk_bottom_structure_lifecycle(
                frame,
                candidate_date=second.available_date,
                c_price=c_price,
                neckline=neckline,
                symbol=symbol,
                structure_type="double_bottom",
                provenance=spec.provenance,
            )
        )
    return structures


def detect_reversal_bottoms(
    frame: pd.DataFrame,
    symbol: str,
    reversal_events: list[SignalEvent] | None = None,
) -> list[StructureInstance]:
    """强势反转 K 线独立形成候选底部。

    反转 K 线**自身即为确认日**，但仍必须按时间顺序：
      候选可用日（反转 K 线当日）→ 立即确认 → 从次日监控 C 触及。
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
        neckline = float(row["high"])
        source_rule = (
            "bullish_engulfing"
            if bool(engulfing.loc[timestamp])
            else "bullish_outside_reversal"
        )
        structure = _walk_bottom_structure_lifecycle(
            frame,
            candidate_date=trade_date,
            c_price=c_price,
            neckline=neckline,
            symbol=symbol,
            structure_type="bullish_reversal_bottom",
            provenance=spec.provenance,
            source_event_ids=tuple(event_by_date.get(trade_date, ())),
            source_rule_id=source_rule,
            confirm_immediately=True,
        )
        # 反转 K 线当日的 close 通常 > open；确认就发生在此刻（不依赖未来突破）
        # 已经在 _walk 内部走完 candidate→confirmed；之后正常监控 C
        structures.append(structure)
    return structures


def apply_c_lifecycle(
    frame: pd.DataFrame,
    structures: list[StructureInstance],
    symbol: str,
) -> list[SignalEvent]:
    """C 生命周期：触及即永久失效。

    严格按时间顺序：自确认日的**下一交易日**起：
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
