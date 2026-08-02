"""关键性波动（Black）与 Top+Black 组合风险。

    key_black = Close < EMA20 且 Close < Close(t-20)
    top_black_state = 存在有效顶部警报 且 当前颜色为黑色

Black 与 Top+Black 必须**分别**保存和统计，
不能只保留表现较好的版本。

Top+Black 只能引用**当时仍然有效**的顶部警报：
顶部被新高解除后不得继续参与。

Top+Black 必须**完整覆盖两种顺序**：
  1) 顶部先确认 → 后转黑：先出现 active_top（黑未到），转黑当天 combined_state 变 True。
  2) 先转黑 → 黑色持续期间顶部才确认：黑色已持续，top 确认日 combined_state 变 True。
Top+Black 状态在顶部失效或颜色不再为黑时结束；重新进入可产生新事件。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent, StructureInstance
from lei_signal.events.log import make_event


def key_black_state(frame: pd.DataFrame) -> pd.Series:
    """逐日黑色状态。与 lei_color 的 black 严格等价。"""
    ready = frame[["close", "ema20", "close_lag20"]].notna().all(axis=1)
    return (
        ready & (frame["close"] < frame["ema20"]) & (frame["close"] < frame["close_lag20"])
    ).fillna(False)


def _active_top_on(
    tops: list[StructureInstance],
    day: date,
) -> StructureInstance | None:
    """当天仍然有效的顶部警报。

    有效条件：已确认（confirmed_date <= day），且未在 day 当天或之前失效。
    被新高解除的顶部从 invalidated_date 起不再有效。
    """
    for top in tops:
        if top.confirmed_date is None or top.confirmed_date > day:
            continue
        if top.invalidated_date is not None and top.invalidated_date <= day:
            continue
        return top
    return None


def _evidence_for_row(row: pd.Series) -> dict[str, float]:
    return {
        "close": float(row["close"]),
        "ema20": float(row["ema20"]),
        "close_lag20": float(row["close_lag20"]),
    }


def detect_key_wave_events(
    frame: pd.DataFrame,
    symbol: str,
    *,
    tops: list[StructureInstance] | None = None,
) -> list[SignalEvent]:
    """黑色起始 + 黑色结束 + Top+Black 组合状态事件。

    关键事件：
      key_wave_black_started / key_wave_black_ended
      top_plus_black_started / top_plus_black_ended
    """
    spec = get_rule("key_wave_black")
    tops = tops or []
    state = key_black_state(frame)

    events: list[SignalEvent] = []
    in_black = False
    in_top_black = False
    current_top: StructureInstance | None = None

    for timestamp in frame.index:
        row = frame.loc[timestamp]
        trade_date = timestamp.date()
        is_black = bool(state.loc[timestamp])
        active_top = _active_top_on(tops, trade_date) if is_black else None
        combined = is_black and active_top is not None

        # --- 黑色起始 / 结束 ---
        if is_black and not in_black:
            evidence = _evidence_for_row(row)
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="key_wave_black_started",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BEARISH,
                    severity=Severity.IMPORTANT,
                    strength=70,
                    reason_cn="关键性波动：收盘价同时低于EMA20与20个交易日前收盘价（转为黑色）",
                    provenance=spec.provenance,
                    evidence={"sub_rule": "key_wave_black_started", **evidence},
                    invalidation={"condition": "颜色转为灰色或绿色"},
                )
            )
            in_black = True
        elif in_black and not is_black:
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="key_wave_black_ended",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.NEUTRAL,
                    severity=Severity.INFO,
                    strength=40,
                    reason_cn="关键性波动结束：颜色已转回灰色或绿色",
                    provenance=spec.provenance,
                    evidence={"sub_rule": "key_wave_black_ended"},
                    invalidation={"condition": "下一次转黑时重新记录"},
                )
            )
            in_black = False

        # --- Top+Black 组合状态起始 / 结束 ---
        if combined and not in_top_black:
            # 组合状态从 False 变 True：记录一次事件
            evidence = _evidence_for_row(row)
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="top_plus_black",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BEARISH,
                    severity=Severity.CRITICAL,
                    strength=90,
                    reason_cn="Top+Black 组合状态成立：存在有效顶部警报且当日颜色为黑色",
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_plus_black",
                        **evidence,
                        "top_structure_id": active_top.structure_id,
                        "top_neckline": active_top.neckline,
                        "top_reference_high": active_top.reference_high,
                    },
                    invalidation={
                        "condition": "顶部被新高解除，或颜色不再为黑色"
                    },
                    structure_id=active_top.structure_id,
                )
            )
            in_top_black = True
            current_top = active_top
        elif in_top_black and not combined:
            # 组合状态结束：记录结束事件
            reason = ""
            if not is_black:
                reason = "颜色不再为黑色"
            elif active_top is None:
                reason = "顶部警报被新高解除"
            else:
                reason = "组合状态结束"
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="top_plus_black_ended",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.NEUTRAL,
                    severity=Severity.WATCH,
                    strength=50,
                    reason_cn=f"Top+Black 组合状态结束：{reason}",
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_plus_black_ended",
                        "ended_top_id": current_top.structure_id if current_top else None,
                    },
                    invalidation={"condition": "重新进入 Top+Black 状态时再记录"},
                    structure_id=current_top.structure_id if current_top else None,
                )
            )
            in_top_black = False
            current_top = None

        # --- 黑色但无顶部：记录 black_without_top 起始（仅在状态从有顶转无顶时）---
        if is_black and active_top is None and current_top is not None:
            # 顶部失效但仍黑：记录 top_plus_black_ended
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="top_plus_black_ended",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.NEUTRAL,
                    severity=Severity.WATCH,
                    strength=50,
                    reason_cn="Top+Black 组合状态结束：顶部警报被新高解除",
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_plus_black_ended",
                        "ended_top_id": current_top.structure_id if current_top else None,
                    },
                    invalidation={"condition": "重新进入 Top+Black 状态时再记录"},
                    structure_id=current_top.structure_id if current_top else None,
                )
            )
            in_top_black = False
            current_top = None
        if in_top_black and current_top is not None and active_top is not None and (
            current_top.structure_id != active_top.structure_id
        ):
            # 顶部轮换：旧的失效，新的确认；记录旧组合状态结束
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="top_plus_black_ended",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.NEUTRAL,
                    severity=Severity.WATCH,
                    strength=50,
                    reason_cn="Top+Black 组合状态结束：旧顶部失效",
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_plus_black_ended",
                        "ended_top_id": current_top.structure_id,
                    },
                    invalidation={"condition": "重新进入 Top+Black 状态时再记录"},
                    structure_id=current_top.structure_id,
                )
            )
            in_top_black = False
            current_top = None
            # 当天也产生新的 top+black 起始
            evidence = _evidence_for_row(row)
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="top_plus_black",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BEARISH,
                    severity=Severity.CRITICAL,
                    strength=90,
                    reason_cn="Top+Black 组合状态成立：存在有效顶部警报且当日颜色为黑色",
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": "top_plus_black",
                        **evidence,
                        "top_structure_id": active_top.structure_id,
                        "top_neckline": active_top.neckline,
                        "top_reference_high": active_top.reference_high,
                    },
                    invalidation={"condition": "顶部被新高解除，或颜色不再为黑色"},
                    structure_id=active_top.structure_id,
                )
            )
            in_top_black = True
            current_top = active_top

    return events


__all__ = ["detect_key_wave_events", "key_black_state"]
