"""假突破快速收回研究代理。

严格前向状态机：参考位只取此前已完成日 K 的滚动最高价；有效突破后进入观察，
盘中刺穿参考位（被打回）后，在确认窗口内重新收回且趋势不破坏即确认；真跌破或
窗口耗尽则失败。每次有效突破独立计数，确认或失败后本轮消耗。
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
SUB_RULE_WATCH = "false_breakout_reclaim_watch"
SUB_RULE_CONFIRMED = "false_breakout_reclaim_confirmed"
SUB_RULE_FAILED = "false_breakout_reclaim_failed"


@dataclass(slots=True)
class _WatchState:
    active: bool = False
    breakout_position: int | None = None
    breakout_date: date | None = None
    reference: float | None = None
    shaken: bool = False
    shaken_position: int | None = None
    emitted_watch: bool = False
    consumed: bool = False


def _params(spec: RuleSpec) -> tuple[int, float, float, int, bool]:
    return (
        int(spec.param("reference_lookback")),
        float(spec.param("breakout_pct")),
        float(spec.param("fail_breakdown_pct")),
        int(spec.param("reclaim_window")),
        bool(spec.param("require_green")),
    )


def _arrangement_holds(row: pd.Series) -> bool:
    return bool(
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
    )


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
    shaken_date: date | None,
    arrangement_holds: bool,
    reclaim_window: int,
    failure_reason: str | None = None,
) -> SignalEvent:
    distance_pct = (close / reference - 1.0) * 100.0 if reference else 0.0
    if sub_rule == SUB_RULE_WATCH:
        reason = (
            "假突破快速收回观察：有效突破前高/结构位后被打回（盘中刺穿参考位），"
            "等待窗口内重新收回"
        )
        severity = Severity.WATCH
        strength = 55
    elif sub_rule == SUB_RULE_CONFIRMED:
        reason = "假突破快速收回确认：被打回后窗口内重新站回参考位上方，完整多头排列仍保持"
        severity = Severity.IMPORTANT
        strength = 75
    else:
        reason = f"假突破快速收回失败：{failure_reason or '确认窗口耗尽'}"
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
        direction=Direction.BULLISH if sub_rule != SUB_RULE_FAILED else Direction.NEUTRAL,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "reference_price": reference,
            "breakout_date": breakout_date.isoformat(),
            "shaken_date": shaken_date.isoformat() if shaken_date else None,
            "close": close,
            "distance_to_reference_pct": distance_pct,
            "arrangement_holds": arrangement_holds,
            "reclaim_window": reclaim_window,
            "failure_reason": failure_reason,
        },
        invalidation={
            "condition": (
                "收盘真跌破参考位、完整多头排列破坏、LEI 颜色转黑，或确认窗口耗尽"
            )
        },
    )


def detect_false_breakout_reclaim_events(
    frame: pd.DataFrame, symbol: str
) -> list[SignalEvent]:
    """识别假突破快速收回事件。"""
    spec = get_rule(RULE_ID)
    (
        lookback,
        breakout_pct,
        fail_pct,
        reclaim_window,
        require_green,
    ) = _params(spec)
    if lookback <= 0 or reclaim_window <= 0:
        raise ValueError("false_breakout_reclaim 的窗口参数必须为正")
    required = {"open", "high", "low", "close", "signal_color", "sma20", "sma60", "sma120"}
    if frame.empty or not required.issubset(frame.columns):
        return []

    # 参考位 = 此前 lookback 根已完成日 K 的最高 high，严格前移一日，无未来泄漏。
    reference_series = frame["high"].rolling(window=lookback).max().shift(1)

    events: list[SignalEvent] = []
    state = _WatchState()

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        if position < lookback + 1:
            continue
        row = frame.iloc[position]
        ref = reference_series.iloc[position]
        if not pd.notna(ref) or ref <= 0:
            continue
        close = float(row["close"])
        low = float(row["low"])
        green = str(row["signal_color"]) == "green"
        arrangement = _arrangement_holds(row)

        if not state.active:
            prior_close = float(frame.iloc[position - 1]["close"])
            breached = close >= ref * (1.0 + breakout_pct)
            prior_below = prior_close < ref * (1.0 + breakout_pct)
            if breached and prior_below:
                # 进入观察；不 continue，使突破当日的盘中打回也能在同一根被捕获。
                state = _WatchState(
                    active=True,
                    breakout_position=position,
                    breakout_date=day,
                    reference=ref,
                )
            else:
                continue

        assert (
            state.breakout_position is not None
            and state.reference is not None
            and state.breakout_date is not None
        )
        # 被打回：盘中刺穿参考位（低点触及/跌破参考位），首次打回发出 watch。
        if not state.shaken and low <= state.reference:
            state.shaken = True
            state.shaken_position = position
            events.append(
                _make_event(
                    spec=spec,
                    symbol=symbol,
                    day=day,
                    lifecycle_id=f"{RULE_ID}:{symbol}:{state.breakout_date.isoformat()}",
                    sub_rule=SUB_RULE_WATCH,
                    reference=state.reference,
                    breakout_date=state.breakout_date,
                    close=close,
                    shaken_date=day,
                    arrangement_holds=arrangement,
                    reclaim_window=reclaim_window,
                )
            )
            state.emitted_watch = True

        if state.shaken:
            assert state.shaken_position is not None
            bars_since_shake = position - state.shaken_position
            # 真跌破：收盘低于参考位 fail_pct，假突破确认失败。
            if close < state.reference * (1.0 - fail_pct):
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=f"{RULE_ID}:{symbol}:{state.breakout_date.isoformat()}",
                        sub_rule=SUB_RULE_FAILED,
                        reference=state.reference,
                        breakout_date=state.breakout_date,
                        close=close,
                        shaken_date=frame.index[state.shaken_position].date(),
                        arrangement_holds=arrangement,
                        reclaim_window=reclaim_window,
                        failure_reason="收盘真跌破参考位，假突破确认失败",
                    )
                )
                state.active = False
                state.consumed = True
                continue
            # 收回：被打回后窗口内重新站回参考位上方且趋势不破坏。
            reclaim_ok = close >= state.reference and arrangement and (not require_green or green)
            if reclaim_ok:
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=f"{RULE_ID}:{symbol}:{state.breakout_date.isoformat()}",
                        sub_rule=SUB_RULE_CONFIRMED,
                        reference=state.reference,
                        breakout_date=state.breakout_date,
                        close=close,
                        shaken_date=frame.index[state.shaken_position].date(),
                        arrangement_holds=arrangement,
                        reclaim_window=reclaim_window,
                    )
                )
                state.active = False
                state.consumed = True
                continue
            if bars_since_shake >= reclaim_window - 1:
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=f"{RULE_ID}:{symbol}:{state.breakout_date.isoformat()}",
                        sub_rule=SUB_RULE_FAILED,
                        reference=state.reference,
                        breakout_date=state.breakout_date,
                        close=close,
                        shaken_date=frame.index[state.shaken_position].date(),
                        arrangement_holds=arrangement,
                        reclaim_window=reclaim_window,
                        failure_reason=f"{reclaim_window} 根确认窗口耗尽仍未收回",
                    )
                )
                state.active = False
                state.consumed = True
                continue
        else:
            bars_since_breakout = position - state.breakout_position
            if close < state.reference * (1.0 - fail_pct):
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=f"{RULE_ID}:{symbol}:{state.breakout_date.isoformat()}",
                        sub_rule=SUB_RULE_FAILED,
                        reference=state.reference,
                        breakout_date=state.breakout_date,
                        close=close,
                        shaken_date=None,
                        arrangement_holds=arrangement,
                        reclaim_window=reclaim_window,
                        failure_reason="收盘真跌破参考位，假突破确认失败",
                    )
                )
                state.active = False
                state.consumed = True
                continue
            if bars_since_breakout >= reclaim_window - 1:
                # 窗口内从未被打回：干净突破，不构成本场景，静默结束本轮。
                state.active = False
                state.consumed = True

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_FAILED",
    "SUB_RULE_WATCH",
    "detect_false_breakout_reclaim_events",
]
