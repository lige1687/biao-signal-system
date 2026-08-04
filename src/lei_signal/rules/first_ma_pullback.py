"""趋势成立后的首次 SMA20/60/120 回撤研究代理。

本模块实现严格前向状态机：趋势生命周期、拉开距离、首次触碰、确认和失败均按
交易日顺序推进；任何一天的结论只依赖当日及此前数据。每个趋势生命周期内，
每条目标均线最多产生一次首次触碰，确认或失败后均视为已消耗。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "first_ma_pullback"
SUB_RULE_TOUCHED = "first_ma_pullback_touched"
SUB_RULE_CONFIRMED = "first_ma_pullback_confirmed"
SUB_RULE_FAILED = "first_ma_pullback_failed"


@dataclass(slots=True)
class _MaState:
    armed: bool = False
    consumed: bool = False
    touch_position: int | None = None
    touch_date: date | None = None
    touch_ma: float | None = None


def _required_columns(periods: tuple[int, ...]) -> set[str]:
    columns = {"open", "high", "low", "close", "atr14", "signal_color"}
    for period in periods:
        columns.add(f"sma{period}")
        columns.add(f"sma{period}_slope")
    return columns


def _params(
    spec: RuleSpec,
) -> tuple[tuple[int, ...], int, float, float, float, float, int, int, bool]:
    periods = tuple(int(value) for value in spec.param("ma_periods"))
    if periods != (20, 60, 120):
        raise ValueError("first_ma_pullback 初版只支持 ma_periods=[20, 60, 120]")
    return (
        periods,
        int(spec.param("trend_slope_lookback")),
        float(spec.param("min_separation_pct")),
        float(spec.param("min_separation_atr")),
        float(spec.param("touch_tolerance_pct")),
        float(spec.param("touch_tolerance_atr")),
        int(spec.param("confirmation_window")),
        int(spec.param("max_trend_age_bars")),
        bool(spec.param("require_green_confirmation")),
    )


def _finite(row: pd.Series, columns: tuple[str, ...]) -> bool:
    return all(pd.notna(row.get(column)) for column in columns)


def _trend_anchor(frame: pd.DataFrame, position: int, lookback: int) -> bool:
    if position < lookback:
        return False
    row = frame.iloc[position]
    previous = frame.iloc[position - lookback]
    columns = ("close", "sma20", "sma60", "sma120")
    if not _finite(row, columns) or not _finite(previous, ("sma20", "sma60", "sma120")):
        return False
    return bool(
        float(row["close"]) > float(row["sma20"])
        and float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and float(row["sma20"]) > float(previous["sma20"])
        and float(row["sma60"]) > float(previous["sma60"])
        and float(row["sma120"]) > float(previous["sma120"])
        and str(row["signal_color"]) == "green"
    )


def _hard_reset(frame: pd.DataFrame, position: int, lookback: int) -> tuple[bool, str]:
    if position < lookback:
        return True, "长周期数据不足"
    row = frame.iloc[position]
    previous = frame.iloc[position - lookback]
    columns = ("close", "sma20", "sma60", "sma120")
    if not _finite(row, columns) or not _finite(previous, ("sma60",)):
        return True, "长周期数据不足"
    if str(row["signal_color"]) == "black":
        return True, "LEI 颜色转黑"
    if float(row["close"]) < float(row["sma120"]):
        return True, "收盘跌破 SMA120"
    if float(row["sma20"]) <= float(row["sma60"]):
        return True, "SMA20 不再高于 SMA60"
    if float(row["sma60"]) <= float(row["sma120"]):
        return True, "SMA60 不再高于 SMA120"
    if float(row["sma60"]) <= float(previous["sma60"]):
        return True, "SMA60 中期方向不再向上"
    return False, ""


def _tolerance(ma_value: float, atr: float, pct: float, atr_multiple: float) -> float:
    return max(ma_value * pct, atr * atr_multiple)


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    sub_rule: str,
    ma_period: int,
    ma_value: float,
    atr: float,
    close: float,
    anchor_date: date,
    touch_date: date,
    distance_pct: float,
    distance_atr: float,
    reclaimed_intraday: bool,
    failure_reason: str | None = None,
) -> SignalEvent:
    label = f"SMA{ma_period}"
    if sub_rule == SUB_RULE_TOUCHED:
        reason = f"首次回撤触碰 {label}：趋势成立并先拉开距离后，价格第一次返回均线附近"
        severity = Severity.WATCH
        strength = 55
    elif sub_rule == SUB_RULE_CONFIRMED:
        reason = f"首次回撤 {label} 确认：收盘重新站于均线上方，均线方向和多头排列仍保持"
        severity = Severity.IMPORTANT
        strength = 75
    else:
        reason = f"首次回撤 {label} 失败：{failure_reason or '确认条件未在窗口内成立'}"
        severity = Severity.INFO
        strength = 35

    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{lifecycle_id}:{ma_period}:{sub_rule}",
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
            "ma_period": ma_period,
            "ma_name": label,
            "ma_value": ma_value,
            "atr14": atr,
            "close": close,
            "trend_anchor_date": anchor_date.isoformat(),
            "touch_date": touch_date.isoformat(),
            "distance_to_ma_pct": distance_pct,
            "distance_to_ma_atr": distance_atr,
            "intraday_broke_and_reclaimed": reclaimed_intraday,
            "failure_reason": failure_reason,
        },
        invalidation={
            "condition": (
                f"收盘有效跌破 {label} 容差、完整多头排列或 SMA60 中期方向破坏、"
                "LEI 颜色转黑，或确认窗口耗尽"
            )
        },
    )


def detect_first_ma_pullback_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别趋势成立后的首次 SMA20/60/120 回撤事件。"""
    spec = get_rule(RULE_ID)
    (
        periods,
        slope_lookback,
        min_separation_pct,
        min_separation_atr,
        touch_tolerance_pct,
        touch_tolerance_atr,
        confirmation_window,
        max_trend_age_bars,
        require_green_confirmation,
    ) = _params(spec)
    if confirmation_window <= 0 or max_trend_age_bars <= 0 or slope_lookback <= 0:
        raise ValueError("first_ma_pullback 的窗口参数必须为正")
    if frame.empty or not _required_columns(periods).issubset(frame.columns):
        return []

    events: list[SignalEvent] = []
    active = False
    can_open = True
    anchor_position: int | None = None
    anchor_date: date | None = None
    lifecycle_id: str | None = None
    states = {period: _MaState() for period in periods}

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        anchor_now = _trend_anchor(frame, position, slope_lookback)

        if not active:
            if not anchor_now:
                can_open = True
                continue
            if not can_open:
                continue
            active = True
            can_open = False
            anchor_position = position
            anchor_date = day
            lifecycle_id = f"{RULE_ID}:{symbol}:{day.isoformat()}"
            states = {period: _MaState() for period in periods}

        assert anchor_position is not None and anchor_date is not None and lifecycle_id is not None
        reset, reset_reason = _hard_reset(frame, position, slope_lookback)
        expired = position - anchor_position >= max_trend_age_bars
        if reset or expired:
            for period, state in states.items():
                if state.touch_position is None or state.consumed:
                    continue
                row = frame.iloc[position]
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_FAILED,
                        ma_period=period,
                        ma_value=float(row[f"sma{period}"]),
                        atr=float(row["atr14"]),
                        close=float(row["close"]),
                        anchor_date=anchor_date,
                        touch_date=state.touch_date or day,
                        distance_pct=(float(row["close"]) / float(row[f"sma{period}"]) - 1.0),
                        distance_atr=(
                            (float(row["close"]) - float(row[f"sma{period}"]))
                            / float(row["atr14"])
                        ),
                        reclaimed_intraday=False,
                        failure_reason=(reset_reason if reset else "趋势生命周期超过最长观察期"),
                    )
                )
                state.consumed = True
            active = False
            continue

        row = frame.iloc[position]
        atr = float(row["atr14"])
        if not pd.notna(atr) or atr <= 0:
            continue

        for period, state in states.items():
            ma_value = float(row[f"sma{period}"])
            close = float(row["close"])
            low = float(row["low"])
            open_price = float(row["open"])
            distance_pct = close / ma_value - 1.0
            distance_atr = (close - ma_value) / atr

            was_armed = state.armed
            if not state.armed and not state.consumed:
                state.armed = (
                    distance_pct >= min_separation_pct
                    and distance_atr >= min_separation_atr
                )

            tolerance = _tolerance(
                ma_value, atr, touch_tolerance_pct, touch_tolerance_atr
            )
            # 必须在更早交易日已经拉开距离；同一根长 K 线既拉开又下探不算
            # “先拉开、再返回”，避免把锚点日或扩张日误判为首次回撤。
            if was_armed and not state.consumed and state.touch_position is None:
                touched = low <= ma_value + tolerance and close >= ma_value - tolerance
                if touched:
                    state.touch_position = position
                    state.touch_date = day
                    state.touch_ma = ma_value
                    events.append(
                        _make_event(
                            spec=spec,
                            symbol=symbol,
                            day=day,
                            lifecycle_id=lifecycle_id,
                            sub_rule=SUB_RULE_TOUCHED,
                            ma_period=period,
                            ma_value=ma_value,
                            atr=atr,
                            close=close,
                            anchor_date=anchor_date,
                            touch_date=day,
                            distance_pct=distance_pct,
                            distance_atr=distance_atr,
                            reclaimed_intraday=low < ma_value <= close,
                        )
                    )

            if state.touch_position is None or state.consumed:
                continue

            bars_since_touch = position - state.touch_position
            hard_price_failure = close < ma_value - tolerance
            arrangement_holds = bool(
                float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
            )
            ma_rising = float(row[f"sma{period}_slope"]) > 0
            green_ok = not require_green_confirmation or str(row["signal_color"]) == "green"
            confirmed = bool(
                bars_since_touch < confirmation_window
                and close >= ma_value
                and close > open_price
                and ma_rising
                and arrangement_holds
                and green_ok
            )
            if confirmed:
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_CONFIRMED,
                        ma_period=period,
                        ma_value=ma_value,
                        atr=atr,
                        close=close,
                        anchor_date=anchor_date,
                        touch_date=state.touch_date or day,
                        distance_pct=distance_pct,
                        distance_atr=distance_atr,
                        reclaimed_intraday=low < ma_value <= close,
                    )
                )
                state.consumed = True
                continue

            window_expired = bars_since_touch >= confirmation_window - 1
            if hard_price_failure or window_expired:
                reason = (
                    f"收盘跌破 SMA{period} 容差"
                    if hard_price_failure
                    else f"{confirmation_window} 根确认窗口耗尽"
                )
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_FAILED,
                        ma_period=period,
                        ma_value=ma_value,
                        atr=atr,
                        close=close,
                        anchor_date=anchor_date,
                        touch_date=state.touch_date or day,
                        distance_pct=distance_pct,
                        distance_atr=distance_atr,
                        reclaimed_intraday=False,
                        failure_reason=reason,
                    )
                )
                state.consumed = True

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_FAILED",
    "SUB_RULE_TOUCHED",
    "detect_first_ma_pullback_events",
]
