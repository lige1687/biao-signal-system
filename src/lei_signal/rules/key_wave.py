"""关键性波动（Black）与 Top+Black 组合风险。

    key_black = Close < EMA20 且 Close < Close(t-20)

Black 与 Top+Black 必须**分别**保存和统计，
不能只保留表现较好的版本。

Top+Black 只能引用**当时仍然有效**的顶部警报：
顶部被新高解除后不得继续参与。
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
    被新高解除的顶部从 invalidated_date 起不再有效，
    因此不能继续参与 Top+Black。
    """
    for top in tops:
        if top.confirmed_date is None or top.confirmed_date > day:
            continue
        if top.invalidated_date is not None and top.invalidated_date <= day:
            continue
        return top
    return None


def detect_key_wave_events(
    frame: pd.DataFrame,
    symbol: str,
    *,
    tops: list[StructureInstance] | None = None,
) -> list[SignalEvent]:
    """黑色起始、Top+Black 与 Black without Top 事件（分别记录）。"""
    spec = get_rule("key_wave_black")
    tops = tops or []
    state = key_black_state(frame)
    starts = state & ~state.shift(1, fill_value=False)

    events: list[SignalEvent] = []
    for timestamp in frame.index[starts]:
        row = frame.loc[timestamp]
        trade_date = timestamp.date()
        evidence = {
            "close": float(row["close"]),
            "ema20": float(row["ema20"]),
            "close_lag20": float(row["close_lag20"]),
        }

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

        active_top = _active_top_on(tops, trade_date)
        if active_top is not None:
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
                    reason_cn="顶部警报仍然有效，同时出现黑色关键性波动（Top+Black 风险信号）",
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
        else:
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="black_without_top",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BEARISH,
                    severity=Severity.IMPORTANT,
                    strength=65,
                    reason_cn="出现黑色关键性波动，但当前没有有效顶部结构（Black 单独风险信号）",
                    provenance=spec.provenance,
                    evidence={"sub_rule": "black_without_top", **evidence},
                    invalidation={"condition": "颜色不再为黑色"},
                )
            )
    return events


__all__ = ["detect_key_wave_events", "key_black_state"]
