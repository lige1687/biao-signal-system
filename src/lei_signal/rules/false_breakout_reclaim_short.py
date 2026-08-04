"""假突破反向 · 做空镜像骨架（规格模块 D2，研究代理）。

这是 false_breakout_reclaim（D1 多头假跌破）的做空镜像接口骨架：价格向上突破压力位
后被打回（拉回），且 SMA20 方向下行（sma20_slope<0）+ 完整空头排列时，确认为做空信号。
与做多侧对称但方向相反；事件 direction=BEARISH。

骨架性质：实现镜像状态机接口与方向透传，但参数（reclaim_bars / fail_pct 等）沿用
做多侧默认值并标注待确认，不冒充作者做空标准。系统当前为研究/回测化，不含下单。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "false_breakout_reclaim"
SUB_RULE_SHORT_WATCH = "false_breakout_reclaim_short_watch"
SUB_RULE_SHORT_CONFIRMED = "false_breakout_reclaim_short_confirmed"
SUB_RULE_SHORT_FAILED = "false_breakout_reclaim_short_failed"


@dataclass(slots=True)
class _ShortWatchState:
    active: bool = False
    breakout_position: int | None = None
    breakout_date: date | None = None
    reference: float | None = None
    emitted_watch: bool = False
    consumed: bool = False


def _params(spec: RuleSpec) -> tuple[int, float, float, int]:
    return (
        int(spec.param("reference_lookback")),
        float(spec.param("breakout_pct")),
        float(spec.param("fail_breakdown_pct")),
        int(spec.param("reclaim_window")),
    )


def _bearish_arrangement(row: pd.Series) -> bool:
    return bool(float(row["sma20"]) < float(row["sma60"]) < float(row["sma120"]))


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    sub_rule: str,
    reference: float,
    breakout_date: date,
    close: float,
    sma20_slope: float,
    arrangement_holds: bool,
    reclaim_window: int,
    failure_reason: str | None = None,
) -> SignalEvent:
    distance_pct = (close / reference - 1.0) * 100.0 if reference else 0.0
    if sub_rule == SUB_RULE_SHORT_WATCH:
        reason = "假突破做空镜像观察：向上突破压力位后被打回，等待 SMA20 下行确认做空"
        severity = Severity.WATCH
        strength = 55
    elif sub_rule == SUB_RULE_SHORT_CONFIRMED:
        reason = (
            "假突破做空镜像确认：突破压力位后拉回，SMA20 方向下行且完整空头排列成立"
        )
        severity = Severity.IMPORTANT
        strength = 75
    else:
        reason = f"假突破做空镜像失败：{failure_reason or '确认窗口耗尽'}"
        severity = Severity.INFO
        strength = 35

    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{lifecycle_id}:{sub_rule}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.BEARISH if sub_rule != SUB_RULE_SHORT_FAILED else Direction.NEUTRAL,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "direction_side": "short",
            "reference_price": reference,
            "breakout_date": breakout_date.isoformat(),
            "close": close,
            "distance_to_reference_pct": distance_pct,
            "sma20_slope": sma20_slope,
            "arrangement_holds": arrangement_holds,
            "reclaim_window": reclaim_window,
            "failure_reason": failure_reason,
        },
        invalidation={
            "condition": (
                "收盘重新站上压力位、完整空头排列破坏、SMA20 重新上行，或确认窗口耗尽"
            )
        },
    )


def detect_false_breakout_reclaim_short_events(
    frame: pd.DataFrame, symbol: str
) -> list[SignalEvent]:
    """识别假突破做空镜像事件（骨架）。方向=BEARISH。"""
    spec = get_rule(RULE_ID)
    lookback, breakout_pct, fail_pct, reclaim_window = _params(spec)
    if lookback <= 0 or reclaim_window <= 0:
        raise ValueError("false_breakout_reclaim 的窗口参数必须为正")
    required = {"open", "high", "low", "close", "sma20", "sma60", "sma120", "sma20_slope"}
    if frame.empty or not required.issubset(frame.columns):
        return []

    # 压力位 = 此前 lookback 根已完成日 K 的最高 high（与做多侧同参考位来源）
    reference_series = frame["high"].rolling(window=lookback).max().shift(1)

    events: list[SignalEvent] = []
    state = _ShortWatchState()

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        if position < lookback + 1:
            continue
        row = frame.iloc[position]
        ref = reference_series.iloc[position]
        if not pd.notna(ref) or ref <= 0:
            continue
        close = float(row["close"])
        sma20_slope = float(row["sma20_slope"])
        arrangement = _bearish_arrangement(row)
        lifecycle_id = f"{RULE_ID}:short:{symbol}:{day.isoformat()}"

        if not state.active:
            prior_close = float(frame.iloc[position - 1]["close"])
            breached = close >= ref * (1.0 + breakout_pct)
            prior_below = prior_close < ref * (1.0 + breakout_pct)
            if breached and prior_below:
                state = _ShortWatchState(
                    active=True,
                    breakout_position=position,
                    breakout_date=day,
                    reference=ref,
                )
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_SHORT_WATCH, reference=ref,
                        breakout_date=day, close=close, sma20_slope=sma20_slope,
                        arrangement_holds=arrangement, reclaim_window=reclaim_window,
                    )
                )
                state.emitted_watch = True
            else:
                continue

        assert (
            state.breakout_position is not None
            and state.reference is not None
            and state.breakout_date is not None
        )
        bars_since = position - state.breakout_position
        # 拉回 + 确认做空：收盘回到压力位下方，SMA20 下行，完整空头排列
        rejected = close < state.reference
        if rejected and sma20_slope < 0 and arrangement:
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                    sub_rule=SUB_RULE_SHORT_CONFIRMED, reference=state.reference,
                    breakout_date=state.breakout_date, close=close,
                    sma20_slope=sma20_slope, arrangement_holds=arrangement,
                    reclaim_window=reclaim_window,
                )
            )
            state.active = False
            state.consumed = True
            continue
        # 失败：重新强势站上压力位上方，或窗口耗尽
        fail_rebound = close > state.reference * (1.0 + breakout_pct + fail_pct)
        if fail_rebound or bars_since >= reclaim_window:
            reason = (
                "重新强势站上压力位" if fail_rebound
                else f"{reclaim_window} 根确认窗口耗尽"
            )
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                    sub_rule=SUB_RULE_SHORT_FAILED, reference=state.reference,
                    breakout_date=state.breakout_date, close=close,
                    sma20_slope=sma20_slope, arrangement_holds=arrangement,
                    reclaim_window=reclaim_window, failure_reason=reason,
                )
            )
            state.active = False
            state.consumed = True

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_SHORT_CONFIRMED",
    "SUB_RULE_SHORT_FAILED",
    "SUB_RULE_SHORT_WATCH",
    "detect_false_breakout_reclaim_short_events",
]
