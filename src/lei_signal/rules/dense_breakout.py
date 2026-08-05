"""均线密集区突破研究代理（规格 §9 模块 B）。

严格前向状态机：横盘密集区识别 -> 突破确认 -> 跌回失效，按交易日顺序推进，
任何一天的结论只依赖当日及此前数据。每个密集区生命周期内只允许一次突破确认，
确认或失败后均视为已消耗。

横盘阈值（cluster_threshold / minimum_consolidation_bars / entanglement_lookback）
复用 tradability_gate，单一来源避免漂移；本规则只声明突破相关参数。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.rules.tradability_gate import _entanglement_series

RULE_ID = "dense_breakout"
SUB_RULE_WATCH = "dense_breakout_watch"
SUB_RULE_CONFIRMED = "dense_breakout_confirmed"
SUB_RULE_FAILED = "dense_breakout_failed"

#: 本规则需要但向 tradability_gate 借用的横盘参数名。读取同一份账本，避免双写阈值。
_TRADABILITY_PARAMS = ("cluster_threshold", "minimum_consolidation_bars", "entanglement_lookback")


@dataclass(slots=True)
class _ZoneState:
    active: bool = False
    consumed: bool = False
    lifecycle_id: str | None = None
    breakout_reference: float | None = None  # 确认时锁定的密集区上沿，用于 B3 跌回判定
    dissolve_counter: int = 0


def _params(spec: RuleSpec) -> tuple[int, float, int, int, bool]:
    """合并本规则参数与 tradability_gate 横盘参数。"""
    tradability = get_rule("tradability_gate")
    cluster_threshold = float(tradability.param("cluster_threshold", 0.02))
    min_bars = int(tradability.param("minimum_consolidation_bars", 120))
    ent_lookback = int(tradability.param("entanglement_lookback", 20))
    breakout_lookback = int(spec.param("breakout_lookback", 60))
    require_full_alignment = bool(spec.param("require_full_alignment", True))
    if breakout_lookback <= 0 or ent_lookback <= 0 or min_bars <= 0:
        raise ValueError("dense_breakout 的窗口参数必须为正")
    return breakout_lookback, cluster_threshold, min_bars, ent_lookback, require_full_alignment


def _required_columns() -> set[str]:
    return {
        "open", "high", "low", "close", "signal_color", "atr14",
        "sma20", "sma60", "sma120", "ema20", "ema60", "ema120",
        "sma20_slope", "sma60_slope", "sma120_slope", "ema20_slope",
    }


def _bullish_alignment(row: pd.Series) -> bool:
    """完整多头排列：SMA20>SMA60>SMA120 且三线斜率均向上（复用 ma_full_alignment 口径）。"""
    return bool(
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and float(row["sma20_slope"]) > 0
        and float(row["sma60_slope"]) > 0
        and float(row["sma120_slope"]) > 0
    )


def _consolidating_mask(
    frame: pd.DataFrame,
    cluster_threshold: float,
    min_bars: int,
    ent_lookback: int,
) -> pd.Series:
    """逐日横盘判定：纠缠度低且持续，且数据充足。复用 tradability_gate 的纠缠度口径。"""
    entanglement = _entanglement_series(frame)
    rolling_mean = entanglement.rolling(window=ent_lookback, min_periods=1).mean()
    position_index = pd.Series(range(len(frame)), index=frame.index)
    return (
        (entanglement <= cluster_threshold)
        & (rolling_mean <= cluster_threshold * 1.5)
        & (position_index >= min_bars)
    ).fillna(False)


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    sub_rule: str,
    reference: float,
    close: float,
    arrangement_holds: bool,
    sma20_slope: float | None = None,
    breakout_reference: float | None = None,
    failure_reason: str | None = None,
) -> SignalEvent:
    distance_pct = (close / reference - 1.0) * 100.0 if reference else 0.0
    if sub_rule == SUB_RULE_WATCH:
        reason = (
            "均线密集区突破观察：六线纠缠压缩至 cluster_threshold 内并持续，"
            "横盘阶段等待价格收盘突破密集区上沿且完整多头排列成立"
        )
        severity = Severity.WATCH
        strength = 55
        direction = Direction.NEUTRAL
    elif sub_rule == SUB_RULE_CONFIRMED:
        reason = (
            "均线密集区突破确认：收盘突破密集区上沿，且完整多头排列成立"
            "（SMA20>SMA60>SMA120 且三线方向向上）"
        )
        severity = Severity.IMPORTANT
        strength = 75
        direction = Direction.BULLISH
    else:
        reason = f"均线密集区突破失败：{failure_reason or '确认条件未成立'}"
        severity = Severity.INFO
        strength = 35
        direction = Direction.NEUTRAL

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
        direction=direction,
        severity=severity,
        strength=strength,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "reference_price": reference,
            "breakout_reference": breakout_reference,
            "close": close,
            "distance_to_reference_pct": distance_pct,
            "arrangement_holds": arrangement_holds,
            "sma20_slope": sma20_slope,
            "failure_reason": failure_reason,
        },
        invalidation={
            "condition": (
                "确认后收盘跌回密集区上沿下方且 SMA20 方向向下弯曲，"
                "或完整多头排列破坏、LEI 颜色转黑"
            )
        },
    )


def detect_dense_breakout_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别均线密集区突破事件（B1 环境 / B2 触发 / B3 失效）。"""
    spec = get_rule(RULE_ID)
    (
        breakout_lookback,
        cluster_threshold,
        min_bars,
        ent_lookback,
        require_full_alignment,
    ) = _params(spec)
    if frame.empty or not _required_columns().issubset(frame.columns):
        return []

    # 密集区上沿 = 此前 breakout_lookback 根已完成日 K 的最高 high，严格前移一日，无未来泄漏。
    reference_series = frame["high"].rolling(window=breakout_lookback).max().shift(1)
    consolidating = _consolidating_mask(frame, cluster_threshold, min_bars, ent_lookback)

    events: list[SignalEvent] = []
    state = _ZoneState()

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        row = frame.iloc[position]
        ref = reference_series.iloc[position]
        is_consolidating = bool(consolidating.iloc[position])
        close = float(row["close"])
        sma20_slope = float(row["sma20_slope"])

        if not state.active:
            # B1：横盘密集区首次成立 -> 开启生命周期，发 watch。
            if is_consolidating and pd.notna(ref) and ref > 0:
                lifecycle_id = f"{RULE_ID}:{symbol}:{day.isoformat()}"
                state = _ZoneState(
                    active=True,
                    consumed=False,
                    lifecycle_id=lifecycle_id,
                )
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day,
                        lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_WATCH, reference=float(ref),
                        close=close, arrangement_holds=_bullish_alignment(row),
                    )
                )
            continue

        assert state.lifecycle_id is not None
        lifecycle_id = state.lifecycle_id

        if not state.consumed:
            # B2：收盘突破密集区上沿 + 完整多头排列 -> 确认。
            arrangement = _bullish_alignment(row)
            breakout = pd.notna(ref) and ref > 0 and close > float(ref)
            if breakout and (arrangement or not require_full_alignment):
                state.consumed = True
                state.breakout_reference = float(ref)
                state.dissolve_counter = 0
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day,
                        lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_CONFIRMED, reference=float(ref),
                        close=close, arrangement_holds=arrangement,
                        breakout_reference=state.breakout_reference,
                    )
                )
                continue
            # 密集区消散（连续 ent_lookback 日不再 consolidating）-> 静默结束，允许新密集区。
            if not is_consolidating:
                state.dissolve_counter += 1
                if state.dissolve_counter >= ent_lookback:
                    state = _ZoneState()
            else:
                state.dissolve_counter = 0
            continue

        # 已确认：B3 跌回密集区 + SMA20 下弯 -> 失效（优先判定，不受消散影响）。
        br = state.breakout_reference
        if br is not None and close < br and sma20_slope < 0:
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day,
                    lifecycle_id=lifecycle_id,
                    sub_rule=SUB_RULE_FAILED, reference=br,
                    close=close, arrangement_holds=_bullish_alignment(row),
                    sma20_slope=sma20_slope, breakout_reference=br,
                    failure_reason="收盘跌回密集区上沿下方且 SMA20 方向向下弯曲",
                )
            )
            state = _ZoneState()
            continue
        # 突破后再次进入横盘密集 = 新密集区。此前已离开密集足够久则静默结束旧生命周期，
        # 允许下一根开启新生命周期；否则继续持有 breakout_reference 等待 B3。
        if is_consolidating:
            if state.dissolve_counter >= ent_lookback:
                state = _ZoneState()
            else:
                state.dissolve_counter = 0
        else:
            state.dissolve_counter += 1

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_FAILED",
    "SUB_RULE_WATCH",
    "detect_dense_breakout_events",
]
