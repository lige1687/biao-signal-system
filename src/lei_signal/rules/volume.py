"""量能信号（全部为 research_proxy）。

阈值 1.5 来自配置且标注研究代理。量能只作支持/冲突标签，
**不得**成为底部结构或入场的硬门槛。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event


def compute_volume_labels(frame: pd.DataFrame) -> pd.DataFrame:
    """逐日量能标签。"""
    spec = get_rule("volume_proxies")
    breakout_ratio = float(spec.param("breakout_ratio", 1.5))
    bearish_ratio = float(spec.param("bearish_ratio", 1.5))
    lookback = int(spec.param("shrink_lookback", 3))

    result = frame.copy()
    if "volume_ratio20" not in result.columns:
        raise ValueError("量能标签需要 volume_ratio20 列")

    ratio = result["volume_ratio20"]
    close = result["close"]
    rising = close > close.shift(1)
    falling = close < close.shift(1)

    result["volume_surge"] = (ratio >= breakout_ratio).fillna(False)
    result["bearish_expansion"] = (falling & (ratio >= bearish_ratio)).fillna(False)

    # 回调缩量：当前处于回调（近 lookback 日收盘下行）且均量低于前一段
    recent_mean = result["volume"].rolling(lookback, min_periods=lookback).mean()
    prior_mean = recent_mean.shift(lookback)
    result["pullback_shrink"] = (
        falling & (recent_mean < prior_mean)
    ).fillna(False)
    result["breakout_volume_ready"] = (rising & (ratio >= breakout_ratio)).fillna(False)
    return result


def detect_volume_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """量能事件。放量突破需要结构颈线配合，由结构层补充；
    此处记录「放量上行」「下跌放量」「回调缩量」三类可独立核对的代理事件。
    """
    spec = get_rule("volume_proxies")
    events: list[SignalEvent] = []

    definitions = (
        (
            "breakout_volume",
            "breakout_volume_ready",
            Direction.BULLISH,
            Severity.INFO,
            "放量上行：成交量达到20日均量的1.5倍以上（研究代理）",
        ),
        (
            "bearish_expansion",
            "bearish_expansion",
            Direction.BEARISH,
            Severity.WATCH,
            "下跌放量：收盘下跌且成交量达到20日均量的1.5倍以上（研究代理）",
        ),
        (
            "pullback_shrink",
            "pullback_shrink",
            Direction.BULLISH,
            Severity.INFO,
            "回调缩量：回调期间近3日均量低于前一段（研究代理）",
        ),
    )

    for label, column, direction, severity, reason in definitions:
        if column not in frame.columns:
            continue
        state = frame[column].astype(bool)
        # 只在状态起始记录，避免连续放量每天重复
        starts = state & ~state.shift(1, fill_value=False)
        for timestamp in frame.index[starts]:
            row = frame.loc[timestamp]
            trade_date = timestamp.date()
            ratio = row.get("volume_ratio20")
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id=label,
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=direction,
                    severity=severity,
                    strength=35,
                    reason_cn=reason,
                    provenance=spec.provenance,
                    evidence={
                        "sub_rule": label,
                        "volume": float(row["volume"]),
                        "volume_ratio20": float(ratio) if pd.notna(ratio) else None,
                        "threshold": float(spec.param("breakout_ratio", 1.5)),
                    },
                    invalidation={"condition": "量能回落到阈值以下"},
                )
            )
    return events


__all__ = ["compute_volume_labels", "detect_volume_events"]
