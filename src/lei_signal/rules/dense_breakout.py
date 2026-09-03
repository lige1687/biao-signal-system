"""均线密集区突破（规格 §9 模块 B / 手册 3.2、3.5，V2 重写版）。

B1 环境（V2 口径，2.0.0 起生效）：时钟三类（|s60| < 10%，clock_classifier）
**叠加** §4.6 密集两条件——①整理时间不少于 6 个月：时钟三类（横盘趋势状态）
寿命 ≥ minimum_consolidation_bars≈126 根（允许 zone_exit_bars 根的间歇，
横盘不是天天打卡）；②当下高度密集：六线带宽 max/min − 1 < cluster_threshold（2%）
（即时条件，不要求连续达标——收敛过程本身可能耗时数月）。
（v1 的纠缠度 + 20 日均纠缠附加条件已替换；v1 把均量纠缠等杂项一并弃用。）

B2 多头触发（两版分别出事件，evidence.variant 区分）：
- 埋伏版【原系统原则】：密集区内**均线刚形成双组多头排列**时提前入场埋伏，
  等突破（手册 3.5「突破前埋伏」）；埋伏单底线 = 多头排列被破坏（B3 附加）。
- 突破版【回测代理】：收盘突破密集区上沿（生命周期内最高 high 的动态上沿），
  下一根开盘入场；**不要求多头排列**（规格 §9 B2：均线依次拐头是加仓/持有
  条件，不作首进入条件——v1 的 require_full_alignment 已按此移除）。

B3 失效（两动作不分先后、必须**全部**满足，手册 3.5）：
1. 收盘跌回密集区上沿下方（close < breakout_reference）；
2. 跌破 20 均线组且 20 组向下弯曲（close < SMA20 且 close < close_lag20 抵扣价判据）。
埋伏单附加底线：双组多头排列破坏（SMA20 ≤ SMA60）即失效。

「真突破给人追不上的感觉」为定性特征，仅作后验记录，不作入场条件。
严格前向：一切判定只用当日及此前已完成日 K；每个密集区生命周期内
埋伏/突破各只允许一次确认（consumed 语义）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.rules.clock_classifier import TYPE3_SIDEWAYS, clock_series

RULE_ID = "dense_breakout"
SUB_RULE_WATCH = "dense_breakout_watch"
SUB_RULE_CONFIRMED = "dense_breakout_confirmed"
SUB_RULE_FAILED = "dense_breakout_failed"

VARIANT_AMBUSH = "ambush"
VARIANT_BREAKOUT = "breakout"
VARIANT_CN = {
    VARIANT_AMBUSH: "埋伏版（多头排列刚形成）",
    VARIANT_BREAKOUT: "突破版（收盘破密集区上沿）",
}

#: 借用 tradability_gate 的密集参数（单一来源，避免双写阈值）。
_TRADABILITY_PARAMS = ("cluster_threshold", "minimum_consolidation_bars")


@dataclass(slots=True)
class _ZoneState:
    active: bool = False
    lifecycle_id: str | None = None
    zone_high_water: float | None = None   # 密集区内最高 high（动态，上沿）
    zone_low_water: float | None = None    # 密集区内最低 low（动态，埋伏止损参照）
    ambush_done: bool = False
    breakout_done: bool = False
    ambush_open: bool = False              # 埋伏单持有中（排列未破坏、B3 未触发）
    breakout_reference: float | None = None
    dissolve_counter: int = 0


def _params(spec: RuleSpec) -> tuple[float, int, int]:
    tradability = get_rule("tradability_gate")
    cluster_threshold = float(tradability.param("cluster_threshold", 0.02))
    min_bars = int(tradability.param("minimum_consolidation_bars", 126))
    dissolve_bars = int(spec.param("dissolve_bars", 20))
    if min_bars <= 0 or dissolve_bars <= 0:
        raise ValueError("dense_breakout 的窗口参数必须为正")
    return cluster_threshold, min_bars, dissolve_bars


def _required_columns() -> set[str]:
    return {
        "open", "high", "low", "close",
        "sma20", "sma60", "sma120", "ema20", "ema60", "ema120",
        "close_lag20",
    }


def _dual_alignment(row: pd.Series) -> bool:
    """双组多头排列（规格 §4.5）：SMA20>SMA60>SMA120 且 EMA20>EMA60>EMA120。"""
    return bool(
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and float(row["ema20"]) > float(row["ema60"]) > float(row["ema120"])
    )


_LINE_COLUMNS = ("sma20", "sma60", "sma120", "ema20", "ema60", "ema120")


def _bandwidth_condition(frame: pd.DataFrame, cluster_threshold: float) -> pd.Series:
    """§4.6 密集带宽条件：六线 max/min − 1 < cluster_threshold（向量化）。"""
    lines = frame[list(_LINE_COLUMNS)].astype(float)
    valid = (lines > 0).all(axis=1)
    ratio = lines.max(axis=1) / lines.min(axis=1) - 1.0
    return (valid & (ratio < cluster_threshold)).fillna(False)


def _state_age_series(condition: pd.Series, *, exit_bars: int) -> pd.Series:
    """横盘状态寿命：时钟三类开始计数，短暂离开（<= exit_bars 根）后回来
    寿命延续，离开超过 exit_bars 根才归零。规格 §4.6 的「整理时间」由
    横盘趋势状态（时钟三类）的持续时长承担，带宽只做「当下密集」判定。"""
    age = 0
    away = 0
    out: list[int] = []
    for flag in condition.astype(bool).tolist():
        if flag:
            age += 1
            away = 0
        else:
            away += 1
            if away > exit_bars:
                age = 0
                away = 0
            else:
                age += 1
        out.append(age)
    return pd.Series(out, index=condition.index, dtype=int)


def _recent_dense_upper_bound(
    frame: pd.DataFrame, lookback_days: int
) -> float | None:
    """最近 ``lookback_days`` 个交易日 high 的滚动上沿（场景卡视觉口径）。

    供 API 场景卡层把陈旧的 B1 锁定上沿刷新为「当前平台顶部」；
    非回测判定口径（回测用 zone_high_water 严格前移一日）。
    """
    if lookback_days <= 0 or frame.empty or "high" not in frame.columns:
        return None
    window = frame.iloc[-lookback_days:] if len(frame) >= lookback_days else frame
    if window.empty:
        return None
    upper = float(window["high"].max())
    return upper if upper > 0 else None


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    sub_rule: str,
    variant: str | None,
    reference: float,
    close: float,
    zone_low: float | None = None,
    alignment_holds: bool = False,
    stop_price: float | None = None,
    failure_reason: str | None = None,
) -> SignalEvent:
    distance_pct = (close / reference - 1.0) * 100.0 if reference else 0.0
    if sub_rule == SUB_RULE_WATCH:
        reason = (
            "均线密集区观察（B1）：时钟三类 + 密集两条件成立（≥6 个月 + 六线带宽<2%），"
            "等待埋伏（多头排列形成）或突破（收盘破密集区上沿）"
        )
        severity = Severity.WATCH
        strength = 55
        direction = Direction.NEUTRAL
    elif sub_rule == SUB_RULE_CONFIRMED:
        if variant == VARIANT_AMBUSH:
            reason = (
                "密集区埋伏入场（B2 埋伏版）：双组多头排列刚形成，提前埋伏等突破；"
                "底线 = 多头排列破坏或 B3 两动作齐备"
            )
        else:
            reason = (
                "密集区突破入场（B2 突破版）：收盘突破密集区上沿，下一根开盘入场；"
                "失效 = 跌回密集区且跌破 20 组下弯（B3 两动作齐备）"
            )
        severity = Severity.IMPORTANT
        strength = 75
        direction = Direction.BULLISH
    else:
        reason = f"均线密集区突破失败：{failure_reason or '条件未成立'}"
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
            source_id=f"{lifecycle_id}:{sub_rule}:{variant or ''}",
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
            "variant": variant,
            "research_proxy": True,
            "reference_price": reference,
            "breakout_reference": reference if variant == VARIANT_BREAKOUT else None,
            "zone_low": zone_low,
            "close": close,
            "distance_to_reference_pct": distance_pct,
            "alignment_holds": alignment_holds,
            "stop_price": stop_price,
            "failure_reason": failure_reason,
        },
        invalidation={
            "condition": (
                "B3 两动作不分先后、必须全部满足：收盘跌回密集区上沿下方，且 "
                "跌破 20 均线组（close<SMA20）且 20 组向下弯曲（close<close_lag20）；"
                "埋伏单附加底线：双组多头排列破坏（SMA20<=SMA60）"
            )
        },
    )


def detect_dense_breakout_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别均线密集区突破事件（B1 时钟三类+密集两条件 / B2 埋伏+突破 / B3 失效）。"""
    spec = get_rule(RULE_ID)
    cluster_threshold, min_bars, dissolve_bars = _params(spec)
    if frame.empty or not _required_columns().issubset(frame.columns):
        return []

    clock = clock_series(frame)
    clock3 = clock == TYPE3_SIDEWAYS
    bandwidth_cond = _bandwidth_condition(frame, cluster_threshold)
    zone_age = _state_age_series(
        clock3, exit_bars=int(spec.param("zone_exit_bars", 20))
    )

    events: list[SignalEvent] = []
    state = _ZoneState()

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        row = frame.iloc[position]
        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])
        dense_now = (
            bool(clock3.iloc[position])
            and bool(bandwidth_cond.iloc[position])
            and int(zone_age.iloc[position]) >= min_bars
        )

        if not state.active:
            # B1：时钟三类 + 密集两条件（带宽持续>=min_bars）同时成立 -> 生命周期开启。
            if bool(clock3.iloc[position]) and dense_now:
                state = _ZoneState(
                    active=True,
                    lifecycle_id=f"{RULE_ID}:{symbol}:{day.isoformat()}",
                    zone_high_water=high,
                    zone_low_water=low,
                )
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day,
                        lifecycle_id=state.lifecycle_id, sub_rule=SUB_RULE_WATCH,
                        variant=None, reference=high, close=close, zone_low=low,
                        alignment_holds=_dual_alignment(row),
                    )
                )
            continue

        assert state.lifecycle_id is not None
        # 突破判定用截至昨日的水位（防当根自我抬升：当日 high 不参与当日判定，
        # 否则 close 永远追不上含当日高点的水位——真实数据全池 0 突破的根因）。
        prev_high_water = state.zone_high_water
        prev_low_water = state.zone_low_water

        alignment = _dual_alignment(row)
        # 20 组下弯：close < SMA20 且 close < close_lag20（抵扣价判据）。
        ma20_down = close < float(row["sma20"]) and close < float(row["close_lag20"])

        # ---- B2 埋伏版：密集区内双组多头排列 false -> true 切换。 ----
        if (
            not state.ambush_done
            and state.breakout_reference is None
            and alignment
            and not state.ambush_open
        ):
            state.ambush_done = True
            state.ambush_open = True
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day,
                    lifecycle_id=state.lifecycle_id, sub_rule=SUB_RULE_CONFIRMED,
                    variant=VARIANT_AMBUSH,
                    reference=float(prev_high_water or high),
                    close=close, zone_low=float(prev_low_water or low),
                    alignment_holds=True,
                    stop_price=float(state.zone_low_water or low),
                )
            )

        # ---- B2 突破版：收盘突破密集区上沿（不要求排列）。 ----
        if (
            not state.breakout_done
            and state.breakout_reference is None
            and prev_high_water is not None
            and close > float(prev_high_water)
        ):
            state.breakout_done = True
            state.breakout_reference = float(prev_high_water)  # 锁定昨日上沿
            # 止损 = 密集区下沿（跌穿整个密集区 = 突破彻底失败）。
            # 突破后回踩上沿是常见确认动作，不能作价格止损（B3 是双条件语义）。
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day,
                    lifecycle_id=state.lifecycle_id, sub_rule=SUB_RULE_CONFIRMED,
                    variant=VARIANT_BREAKOUT,
                    reference=state.breakout_reference,
                    close=close, zone_low=float(prev_low_water or low),
                    alignment_holds=alignment,
                    stop_price=float(prev_low_water or low),
                )
            )

        # ---- B3 失效（已入场后逐日判定）。 ----
        if state.breakout_reference is not None:
            fall_back = close < float(state.breakout_reference)
            if fall_back and ma20_down:
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day,
                        lifecycle_id=state.lifecycle_id, sub_rule=SUB_RULE_FAILED,
                        variant=VARIANT_BREAKOUT,
                        reference=float(state.breakout_reference), close=close,
                        failure_reason="跌回密集区且跌破 20 均线组下弯（B3 两动作齐备）",
                    )
                )
                state = _ZoneState()
                continue
        if state.ambush_open and float(row["sma20"]) <= float(row["sma60"]):
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day,
                    lifecycle_id=state.lifecycle_id, sub_rule=SUB_RULE_FAILED,
                    variant=VARIANT_AMBUSH,
                    reference=float(state.zone_high_water or high), close=close,
                    failure_reason="埋伏单底线：双组多头排列破坏（SMA20<=SMA60）",
                )
            )
            state.ambush_open = False

        # ---- 水位更新（当日高低参与明日判定） ----
        if state.breakout_reference is None:
            state.zone_high_water = max(state.zone_high_water or high, high)
            state.zone_low_water = min(state.zone_low_water or low, low)

        # ---- 生命周期消散：带宽条件持续 dissolve_bars 根不成立 -> 静默结束。 ----
        if not bool(bandwidth_cond.iloc[position]):
            state.dissolve_counter += 1
            if state.dissolve_counter >= dissolve_bars and not state.ambush_open:
                state = _ZoneState()
        else:
            state.dissolve_counter = 0

        # 埋伏单还开着、突破也确认了：埋伏逻辑随突破确认自然升级，关闭埋伏持有态。
        if state.ambush_open and state.breakout_reference is not None:
            state.ambush_open = False

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_FAILED",
    "SUB_RULE_WATCH",
    "VARIANT_AMBUSH",
    "VARIANT_BREAKOUT",
    "VARIANT_CN",
    "detect_dense_breakout_events",
    "_bandwidth_condition",
    "_recent_dense_upper_bound",
    "_state_age_series",
]
