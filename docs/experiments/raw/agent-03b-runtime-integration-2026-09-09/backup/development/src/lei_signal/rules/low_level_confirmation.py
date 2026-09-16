"""日线信号后的次级别确认研究代理（日线 OHLC 代理）。

本规则是用户交易笔记里“低级别/小时确认”的研究代理量化。当前系统只接入日线，
真 60 分钟数据尚未连接，因此用日线 OHLC 的“盘中刺穿参考支撑后收盘收回”与
反转 K 线作为次级别确认的日线代理，并在界面明确标注“日线代理 / 未接 60 分钟”。

严格前向：触发只取当日及此前已完成日 K；次级别确认特征在触发后确认窗口内出现。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "low_level_confirmation"
SUB_RULE_WATCH = "low_level_confirmation_watch"
SUB_RULE_CONFIRMED = "low_level_confirmation_confirmed"

#: 日线做多触发条件（双均线共同确认为代表的日线做多信号，可由 frame 直接判定）。
TRIGGER_NAME = "双均线共同确认（日线做多信号代理）"


@dataclass(slots=True)
class _Episode:
    active: bool = False
    trigger_position: int | None = None
    trigger_date: date | None = None
    reference: float | None = None
    confirmed: bool = False


def _params(spec: RuleSpec) -> tuple[int, float]:
    return (
        int(spec.param("confirmation_window")),
        float(spec.param("reclaim_tolerance_pct")),
    )


def _daily_long_trigger(row: pd.Series) -> bool:
    """日线做多信号代理：完整多头排列中收阳站上 EMA20/SMA20 且两者方向向上。"""
    return bool(
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and str(row["signal_color"]) == "green"
        and float(row["close"]) >= float(row["ema20"])
        and float(row["close"]) >= float(row["sma20"])
        and float(row["close"]) > float(row["open"])
        and float(row["sma20_slope"]) > 0
    )


def _intraday_reclaim(row: pd.Series, reference: float, tol: float) -> bool:
    """盘中刺穿参考支撑（低点触及/略破）但收盘收回上方。"""
    return bool(float(row["low"]) <= reference * (1.0 + tol) and float(row["close"]) >= reference)


def _reversal_candle(frame: pd.DataFrame, position: int) -> bool:
    if position < 1:
        return False
    cur = frame.iloc[position]
    prev = frame.iloc[position - 1]
    cur_o, cur_c = float(cur["open"]), float(cur["close"])
    prev_o, prev_c = float(prev["open"]), float(prev["close"])
    prev_h, prev_l = float(prev["high"]), float(prev["low"])
    cur_l = float(cur["low"])
    engulfing = bool(
        prev_c < prev_o and cur_c > cur_o and cur_o <= prev_c and cur_c >= prev_o
    )
    outside = bool(cur_l <= prev_l and cur_c >= prev_h and cur_c > cur_o)
    return engulfing or outside


def detect_low_level_confirmation_events(
    frame: pd.DataFrame, symbol: str
) -> list[SignalEvent]:
    """识别日线做多信号后的次级别确认（日线代理）。"""
    spec = get_rule(RULE_ID)
    window, tol = _params(spec)
    if window <= 0:
        raise ValueError("low_level_confirmation 的确认窗口必须为正")
    required = {
        "open",
        "high",
        "low",
        "close",
        "signal_color",
        "ema20",
        "sma20",
        "sma60",
        "sma120",
        "sma20_slope",
    }
    if frame.empty or not required.issubset(frame.columns):
        return []

    events: list[SignalEvent] = []
    episode = _Episode()
    prev_trigger = False

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        row = frame.iloc[position]
        if not all(pd.notna(row.get(col)) for col in required):
            prev_trigger = False
            continue
        trigger = _daily_long_trigger(row)

        # 触发日（False->True 跳变）发出 watch，记录参考支撑 = 当日 SMA20。
        if trigger and not prev_trigger and not episode.active:
            episode = _Episode(
                active=True,
                trigger_position=position,
                trigger_date=day,
                reference=float(row["sma20"]),
            )
            events.append(
                _make_event(
                    spec=spec,
                    symbol=symbol,
                    day=day,
                    sub_rule=SUB_RULE_WATCH,
                    reference=float(row["sma20"]),
                    close=float(row["close"]),
                    trigger_name=TRIGGER_NAME,
                )
            )

        # 触发后窗口内寻找次级别确认特征。
        if episode.active and not episode.confirmed:
            assert episode.reference is not None
            assert episode.trigger_position is not None
            bars_since = position - episode.trigger_position
            signature = _intraday_reclaim(row, episode.reference, tol) or _reversal_candle(
                frame, position
            )
            close_ok = float(row["close"]) >= episode.reference
            if signature and close_ok and bars_since < window:
                events.append(
                    _make_event(
                        spec=spec,
                        symbol=symbol,
                        day=day,
                        sub_rule=SUB_RULE_CONFIRMED,
                        reference=episode.reference,
                        close=float(row["close"]),
                        trigger_name=TRIGGER_NAME,
                        signature=(
                            "盘中刺穿参考支撑后收回"
                            if _intraday_reclaim(row, episode.reference, tol)
                            else "反转 K 线"
                        ),
                    )
                )
                episode.confirmed = True
                episode.active = False

        # 触发条件消失则本轮结束（等待下一次跳变）。
        if not trigger:
            if episode.active and not episode.confirmed:
                episode.active = False
            prev_trigger = False
        else:
            prev_trigger = True

    return events


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    sub_rule: str,
    reference: float,
    close: float,
    trigger_name: str,
    signature: str | None = None,
) -> SignalEvent:
    distance_pct = (close / reference - 1.0) * 100.0 if reference else 0.0
    if sub_rule == SUB_RULE_WATCH:
        reason = (
            "日线做多信号触发，等待次级别确认（日线代理：盘中刺穿参考支撑后收回，"
            "或反转 K 线）"
        )
        severity = Severity.WATCH
        strength = 55
    else:
        reason = f"次级别确认（日线代理）：{signature or '出现确认特征'}，增强日线信号可信度"
        severity = Severity.IMPORTANT
        strength = 72

    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{day.isoformat()}:{sub_rule}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.BULLISH,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=f"{RULE_ID}:{symbol}:{day.isoformat()}",
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "trigger_name": trigger_name,
            "reference_price": reference,
            "close": close,
            "distance_to_reference_pct": distance_pct,
            "confirmation_signature": signature,
            "data_proxy": "日线 OHLC 代理（系统未接入 60 分钟数据）",
        },
        invalidation={
            "condition": (
                "触发信号失效（完整多头排列或双均线共同确认不再成立），"
                "或收盘跌破参考支撑"
            )
        },
    )


__all__ = [
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_WATCH",
    "detect_low_level_confirmation_events",
]
