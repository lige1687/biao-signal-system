"""量能信号（全部为 research_proxy）。

阈值 1.5 来自配置且标注研究代理。量能只作支持/冲突标签，
**不得**成为底部结构或入场的硬门槛。

修复 7：
  * volume_up_surge：Close 上涨 + 量比 >= 阈值（不要求结构颈线）。
  * breakout_volume：Close 突破某个明确结构颈线 + 量比 >= 阈值；
    无结构颈线时只能叫「放量上行」，不能叫「放量突破」。
  * pullback_shrink：是简单滚动代理（比较最近两段均量），
    不是真正的趋势分段；事件触发条件明确写在规则账本中。
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
    up_surge_ratio = float(spec.param("up_surge_ratio", 2.0))
    bearish_ratio = float(spec.param("bearish_ratio", 2.0))
    lookback = int(spec.param("shrink_lookback", 3))

    result = frame.copy()
    if "volume_ratio20" not in result.columns:
        raise ValueError("量能标签需要 volume_ratio20 列")

    ratio = result["volume_ratio20"]
    close = result["close"]
    rising = close > close.shift(1)
    falling = close < close.shift(1)

    result["volume_up_surge"] = (rising & (ratio >= up_surge_ratio)).fillna(False)
    result["bearish_expansion"] = (falling & (ratio >= bearish_ratio)).fillna(False)

    # 回调缩量（简单滚动代理）：当前处于下跌段，
    # 且最近 lookback 日均量 < 前 lookback 日均量
    recent_mean = result["volume"].rolling(lookback, min_periods=lookback).mean()
    prior_mean = recent_mean.shift(lookback)
    result["pullback_shrink"] = (
        falling & (recent_mean < prior_mean)
    ).fillna(False)
    return result


def detect_volume_events(
    frame: pd.DataFrame,
    symbol: str,
    *,
    structure_necklines: dict[pd.Timestamp, dict] | None = None,
) -> list[SignalEvent]:
    """量能事件。

    三个独立标签：
      * volume_up_surge：放量上行（不要求颈线）。
      * breakout_volume：放量突破某结构颈线（必须能找到颈线）。
      * pullback_shrink：回调缩量（简单滚动代理）。
      * bearish_expansion：下跌放量（风险标签）。
    """
    spec = get_rule("volume_proxies")
    events: list[SignalEvent] = []

    up_surge_ratio = float(spec.param("up_surge_ratio", 2.0))
    breakout_ratio = float(spec.param("breakout_ratio", 2.0))
    bearish_ratio = float(spec.param("bearish_ratio", 2.0))
    structure_necklines = structure_necklines or {}

    definitions = (
        (
            "volume_up_surge",
            "volume_up_surge",
            Direction.BULLISH,
            Severity.INFO,
            "放量上行：成交量达到20日均量的1.5倍以上（研究代理）",
            up_surge_ratio,
        ),
        (
            "bearish_expansion",
            "bearish_expansion",
            Direction.BEARISH,
            Severity.WATCH,
            "下跌放量：收盘下跌且成交量达到20日均量的1.5倍以上（研究代理）",
            bearish_ratio,
        ),
        (
            "pullback_shrink",
            "pullback_shrink",
            Direction.BULLISH,
            Severity.INFO,
            "回调缩量：最近3日均量低于前3日均量（简单滚动代理，研究代理）",
            None,
        ),
    )

    for label, column, direction, severity, reason, threshold in definitions:
        if column not in frame.columns:
            continue
        state = frame[column].astype(bool)
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
                        "threshold": threshold,
                    },
                    invalidation={"condition": "量能回落到阈值以下"},
                )
            )

    # 放量突破：必须有结构颈线 + 收盘突破 + 量比达到阈值
    if "volume_ratio20" in frame.columns:
        rising = frame["close"] > frame["close"].shift(1)
        ratio_ok = frame["volume_ratio20"] >= breakout_ratio
        for timestamp, neckline in structure_necklines.items():
            if timestamp not in frame.index:
                continue
            if not (rising.loc[timestamp] and ratio_ok.loc[timestamp]):
                continue
            row = frame.loc[timestamp]
            trade_date = timestamp.date()
            events.append(
                make_event(
                    event_id=make_event_id(
                        rule_id=spec.rule_id,
                        rule_version=spec.version,
                        symbol=symbol,
                        timeframe="1d",
                        available_date=trade_date,
                        source_id="breakout_volume",
                    ),
                    symbol=symbol,
                    event_date=trade_date,
                    available_date=trade_date,
                    rule_id=spec.rule_id,
                    rule_version=spec.version,
                    direction=Direction.BULLISH,
                    severity=Severity.INFO,
                    strength=55,
                    reason_cn=(
                        f"放量突破：收盘价突破结构颈线 {neckline['neckline']:.4f}，"
                        f"且成交量比 {float(row['volume_ratio20']):.2f} 达到阈值"
                    ),
                    provenance=spec.provenance,
                    structure_id=neckline.get("structure_id"),
                    evidence={
                        "sub_rule": "breakout_volume",
                        "neckline": float(neckline["neckline"]),
                        "structure_id": neckline.get("structure_id"),
                        "volume_ratio20": float(row["volume_ratio20"]),
                        "threshold": breakout_ratio,
                    },
                    invalidation={"condition": "回落到颈线以下"},
                )
            )

    return events


__all__ = ["compute_volume_labels", "detect_volume_events"]
