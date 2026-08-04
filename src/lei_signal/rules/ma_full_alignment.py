"""完整均线排列 + EMA 斜率加速度研究代理。

把 20/60/120 完整多头/空头排列作为场景卡底层确认维度（前向状态机：非排列→排列→
破坏），并用 EMA20 斜率与加速度标准化描述动能变化。排列本身为状态型事件，有起止；
斜率/加速度为研究代理指标，仅作确认维度。
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "ma_full_alignment"
SUB_RULE_BULLISH_START = "ma_alignment_bullish_start"
SUB_RULE_BEARISH_START = "ma_alignment_bearish_start"
SUB_RULE_BROKEN = "ma_alignment_broken"


@dataclass(slots=True)
class _AlignmentState:
    kind: str | None = None  # None | "bullish" | "bearish"


def _params(spec: RuleSpec) -> tuple[tuple[int, ...], int, int, int]:
    return (
        tuple(int(value) for value in spec.param("periods")),
        int(spec.param("slope_lookback")),
        int(spec.param("accel_lookback")),
        int(spec.param("ema_slope_period")),
    )


def _bullish(row: pd.Series) -> bool:
    return bool(
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and float(row["sma20_slope"]) > 0
        and float(row["sma60_slope"]) > 0
        and float(row["sma120_slope"]) > 0
    )


def _bearish(row: pd.Series) -> bool:
    return bool(
        float(row["sma20"]) < float(row["sma60"]) < float(row["sma120"])
        and float(row["sma20_slope"]) < 0
        and float(row["sma60_slope"]) < 0
        and float(row["sma120_slope"]) < 0
    )


def _alignment_kind(row: pd.Series) -> str | None:
    if _bullish(row):
        return "bullish"
    if _bearish(row):
        return "bearish"
    return None


def ema_slope_accel_for_frame(frame: pd.DataFrame) -> dict | None:
    """返回最后一行 EMA20 斜率与加速度（研究代理指标），不可用时返回 None。"""
    if frame.empty or "ema20" not in frame.columns:
        return None
    slope_lookback = int(get_rule(RULE_ID).param("slope_lookback", 1))
    accel_lookback = int(get_rule(RULE_ID).param("accel_lookback", 1))
    series = frame["ema20"].astype(float)
    if len(series) <= slope_lookback + accel_lookback:
        return None
    last = float(series.iloc[-1])
    prev_slope = float(series.iloc[-1 - slope_lookback])
    slope_pct = (last - prev_slope) / prev_slope if prev_slope else 0.0
    earlier = float(series.iloc[-1 - (slope_lookback + accel_lookback)])
    prev_slope_earlier = (prev_slope - earlier) / earlier if earlier else 0.0
    accel_pct = slope_pct - prev_slope_earlier
    return {
        "ema_period": int(get_rule(RULE_ID).param("ema_slope_period", 20)),
        "ema20": last,
        "ema20_slope_pct": slope_pct * 100.0,
        "ema20_accel_pct": accel_pct * 100.0,
    }


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day,  # noqa: ANN001
    sub_rule: str,
    kind: str,
    slope_accel: dict | None,
) -> SignalEvent:
    if sub_rule == SUB_RULE_BULLISH_START:
        reason = "完整多头排列成立：SMA20>SMA60>SMA120 且三条 SMA 方向均向上"
        severity = Severity.IMPORTANT
        strength = 70
        direction = Direction.BULLISH
    elif sub_rule == SUB_RULE_BEARISH_START:
        reason = "完整空头排列成立：SMA20<SMA60<SMA120 且三条 SMA 方向均向下"
        severity = Severity.IMPORTANT
        strength = 70
        direction = Direction.BEARISH
    else:
        reason = f"完整{kind}排列破坏：均线方向或相对位置不再满足"
        severity = Severity.INFO
        strength = 35
        direction = Direction.NEUTRAL

    evidence = {
        "sub_rule": sub_rule,
        "research_proxy": True,
        "alignment_kind": kind,
        "alignment_cn": {"bullish": "完整多头排列", "bearish": "完整空头排列"}.get(kind, "无排列"),
    }
    if slope_accel is not None:
        evidence.update(
            {
                "ema20": slope_accel["ema20"],
                "ema20_slope_pct": slope_accel["ema20_slope_pct"],
                "ema20_accel_pct": slope_accel["ema20_accel_pct"],
            }
        )

    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{kind}:{sub_rule}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=direction,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        evidence=evidence,
        invalidation={
            "condition": (
                "均线相对位置或方向不再满足完整排列（多头：SMA20>SMA60>SMA120 且均向上；"
                "空头反之）"
            )
        },
    )


def detect_ma_alignment_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别完整均线排列的成立与破坏事件。"""
    spec = get_rule(RULE_ID)
    _params(spec)  # 校验参数存在
    required = {"sma20", "sma60", "sma120", "sma20_slope", "sma60_slope", "sma120_slope"}
    if frame.empty or not required.issubset(frame.columns):
        return []

    events: list[SignalEvent] = []
    state = _AlignmentState()
    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        row = frame.iloc[position]
        if not all(pd.notna(row.get(col)) for col in required):
            continue
        kind = _alignment_kind(row)
        if kind == state.kind:
            continue
        # 离开旧排列（若有）先发破坏事件
        if state.kind is not None:
            events.append(
                _make_event(
                    spec=spec,
                    symbol=symbol,
                    day=day,
                    sub_rule=SUB_RULE_BROKEN,
                    kind=state.kind,
                    slope_accel=ema_slope_accel_for_frame(frame.iloc[: position + 1]),
                )
            )
        # 进入新排列
        if kind is not None:
            events.append(
                _make_event(
                    spec=spec,
                    symbol=symbol,
                    day=day,
                    sub_rule=(
                        SUB_RULE_BULLISH_START
                        if kind == "bullish"
                        else SUB_RULE_BEARISH_START
                    ),
                    kind=kind,
                    slope_accel=ema_slope_accel_for_frame(frame.iloc[: position + 1]),
                )
            )
        state.kind = kind

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_BROKEN",
    "SUB_RULE_BULLISH_START",
    "SUB_RULE_BEARISH_START",
    "detect_ma_alignment_events",
    "ema_slope_accel_for_frame",
]
