"""2B / 破底翻反转（规格 §9 模块 C / 手册 2.6、3.4，V2 重写版）。

C1 结构（V2 §9 C1 填实，3.0.0 起生效）：
- L1 = **前低**（最后一个已确认的 swing low，左3右3 确认日可用）；
- 价格**跌破 L1 创出新低 L2**（假跌破；L2 = 破位期间最低 low，**无需摆动确认**）；
- 随后 **two_b_reclaim_bars（默认 5）根内收盘收回 L1 上方** = 破底翻 / 多头 2B。

与 v1 口径（2.0.0 之前）的根本差异：v1 要求 L2/L1 都是被三左三右确认的摆动低点对
（L2 更早更低、L1 更晚更高）；V2 只要求 L1 是已确认前低，L2 是跌破它之后的任意新低
——「挖坑」不需要走出一个可确认的摆动结构，这正是 2B 与 M 底的区别
（2B 不需要完整回撤波段，只是原波段的延续，规格 §9 C1【原系统原则】）。

C2 入场（三版本分别出事件）：v1 = 收回 L1 当日；v2 = 收回后 EMA20 拐头向上；
v3 = 收回后 EMA20 与 SMA20 共同向上（SMA 用抵扣价判据）。
C3 失效：收盘跌破 L2（假跌破新低），2B 逻辑彻底失效；收复窗口耗尽亦失败。
每个 L1 只允许一次 2B 循环（consumed 语义）。

增强条件（不单独触发）：周线+日线同时 2B、大幅负乖离（§4.7）仅作 evidence。
严格前向：L1 在确认日之后才可用；一切判定只用当日及此前已完成日 K。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Pivot, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.features.pivots import confirmed_pivots, swing_lows
from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state

RULE_ID = "two_b_reversal"
SUB_RULE_V1 = "two_b_reversal_v1_confirmed"
SUB_RULE_V2 = "two_b_reversal_v2_confirmed"
SUB_RULE_V3 = "two_b_reversal_v3_confirmed"
SUB_RULE_FAILED = "two_b_reversal_failed"

#: 三版本入场：v1=收盘收回 L1；v2=+EMA20 拐头向上；v3=+EMA20 与 SMA20 共同向上。
VERSIONS: tuple[tuple[str, str, str], ...] = (
    (SUB_RULE_V1, "v1", "收盘收回 L1 上方"),
    (SUB_RULE_V2, "v2", "收回 L1 且 EMA20 拐头向上"),
    (SUB_RULE_V3, "v3", "收回 L1 且 EMA20 与 SMA20 共同向上"),
)


def _params(spec: RuleSpec) -> int:
    reclaim_bars = int(spec.param("two_b_reclaim_bars", 5))
    if reclaim_bars <= 0:
        raise ValueError("two_b_reversal 的 two_b_reclaim_bars 必须为正")
    return reclaim_bars


def _required_columns() -> set[str]:
    return {"open", "high", "low", "close", "ema20", "ema120", "sma20", "signal_color"}


def _bias_ema120(row: pd.Series) -> float | None:
    ema120, close = row.get("ema120"), row.get("close")
    if ema120 is None or close is None or pd.isna(ema120) or float(ema120) == 0:
        return None
    return float(close) / float(ema120) - 1.0


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    sub_rule: str,
    confirmed: bool,
    l1_price: float,
    l2_price: float | None,
    close: float,
    breakdown_date: date | None = None,
    reclaim_date: date | None = None,
    bars_to_reclaim: int | None = None,
    ema20_state: bool = False,
    dual_ma_state: bool = False,
    bias_ema120: float | None = None,
    stop_price: float | None = None,
    failure_reason: str | None = None,
) -> SignalEvent:
    if confirmed:
        version_cn = next(vc for sr, _v, vc in VERSIONS if sr == sub_rule)
        reason = (
            f"2B/破底翻确认（{version_cn}）：跌破前低 L1({l1_price:.4f}) 创新低后 "
            f"{bars_to_reclaim} 根内收回上方；失效线 = 假跌破新低 L2({l2_price:.4f})"
        )
        severity = Severity.IMPORTANT
        strength = 75
        direction = Direction.BULLISH
        evidence = {
            "sub_rule": sub_rule,
            "research_proxy": True,
            "version": sub_rule.replace("two_b_reversal_", "").replace("_confirmed", ""),
            "close": close,
            "stop_price": stop_price,
            "l1_price": l1_price,
            "l2_price": l2_price,
            "breakdown_date": breakdown_date.isoformat() if breakdown_date else None,
            "reclaim_date": reclaim_date.isoformat() if reclaim_date else None,
            "bars_to_reclaim": bars_to_reclaim,
            "ema20_reclaim_state": ema20_state,
            "dual_ma_bull_state": dual_ma_state,
            "bias_ema120": bias_ema120,
            "bias_enhancement_only": True,
        }
        invalidation = {
            "condition": f"收盘跌破 L2({l2_price:.4f})（假跌破新低），2B 彻底失效"
        }
    else:
        reason = f"2B/破底翻失败：{failure_reason or '条件未成立'}"
        severity = Severity.INFO
        strength = 35
        direction = Direction.NEUTRAL
        evidence = {
            "sub_rule": sub_rule,
            "research_proxy": True,
            "close": close,
            "l1_price": l1_price,
            "l2_price": l2_price,
            "failure_reason": failure_reason,
        }
        invalidation = {"condition": "失败事件是历史事实，不会被后续上涨改写"}

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
        evidence=evidence,
        invalidation=invalidation,
    )


def _scan_l1(
    frame: pd.DataFrame,
    symbol: str,
    spec: RuleSpec,
    *,
    l1: Pivot,
    reclaim_bars: int,
    reclaim_state: pd.Series,
    joint_state: pd.Series,
    start_position: int,
) -> list[SignalEvent]:
    """单个前低 L1 的 2B 循环：跌破 -> 创新低 L2 -> 收回 -> 三版本 / 失效。"""
    events: list[SignalEvent] = []
    lifecycle_id = f"{RULE_ID}:{symbol}:{l1.available_date.isoformat()}"
    l1_price = float(l1.price)

    broken_down = False
    breakdown_position: int | None = None
    breakdown_date: date | None = None
    l2_price: float | None = None          # 破位期间最低 low（动态下移）
    reclaimed = False
    reclaim_position: int | None = None
    v_done = {SUB_RULE_V1: False, SUB_RULE_V2: False, SUB_RULE_V3: False}

    for position in range(start_position, len(frame)):
        row = frame.iloc[position]
        close = float(row["close"])
        low = float(row["low"])
        day = frame.index[position].date()
        bias = _bias_ema120(row)

        if not broken_down:
            if close < l1_price:
                broken_down = True
                breakdown_position = position
                breakdown_date = day
                l2_price = low  # L2 起点 = 破位日盘中低点
            continue

        assert breakdown_position is not None and breakdown_date is not None
        assert l2_price is not None

        # C3：收盘跌破 L2（假跌破新低）-> 彻底失效。
        if close < l2_price:
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                    sub_rule=SUB_RULE_FAILED, confirmed=False,
                    l1_price=l1_price, l2_price=l2_price, close=close,
                    breakdown_date=breakdown_date,
                    failure_reason="收盘跌破假跌破新低 L2，2B 结构彻底失效",
                )
            )
            return events

        # 未收回前：L2 随新低下移（取盘中 low）。
        if not reclaimed:
            l2_price = min(l2_price, low)
            bars_since = position - breakdown_position
            if bars_since > reclaim_bars:
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                        sub_rule=SUB_RULE_FAILED, confirmed=False,
                        l1_price=l1_price, l2_price=l2_price, close=close,
                        breakdown_date=breakdown_date,
                        failure_reason=(
                            f"跌破 L1 后 {reclaim_bars} 根内未收回（快速收复窗口耗尽）"
                        ),
                    )
                )
                return events
            if close >= l1_price:
                reclaimed = True
                reclaim_position = position
                ema20_now = bool(reclaim_state.iloc[position])
                dual_ma_now = bool(joint_state.iloc[position])
                for sub_rule, _version, _vc in VERSIONS:
                    if sub_rule == SUB_RULE_V1:
                        cond = True
                    elif sub_rule == SUB_RULE_V2:
                        cond = ema20_now
                    else:
                        cond = dual_ma_now
                    if cond and not v_done[sub_rule]:
                        events.append(
                            _make_event(
                                spec=spec, symbol=symbol, day=day,
                                lifecycle_id=lifecycle_id, sub_rule=sub_rule,
                                confirmed=True, l1_price=l1_price, l2_price=l2_price,
                                close=close, breakdown_date=breakdown_date,
                                reclaim_date=day,
                                bars_to_reclaim=bars_since,
                                ema20_state=ema20_now, dual_ma_state=dual_ma_now,
                                bias_ema120=bias, stop_price=l2_price,
                            )
                        )
                        v_done[sub_rule] = True
            continue

        # 已收回：等待 v2/v3 后置条件（L2 失效在循环顶部判定）。
        assert reclaim_position is not None
        ema20_now = bool(reclaim_state.iloc[position])
        dual_ma_now = bool(joint_state.iloc[position])
        common = dict(
            spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
            l1_price=l1_price, l2_price=l2_price, close=close,
            breakdown_date=breakdown_date,
            reclaim_date=frame.index[reclaim_position].date(),
            bars_to_reclaim=reclaim_position - breakdown_position,
            bias_ema120=bias, stop_price=l2_price,
        )
        if not v_done[SUB_RULE_V2] and ema20_now:
            events.append(
                _make_event(
                    **common, sub_rule=SUB_RULE_V2, confirmed=True,
                    ema20_state=True, dual_ma_state=dual_ma_now,
                )
            )
            v_done[SUB_RULE_V2] = True
        if not v_done[SUB_RULE_V3] and dual_ma_now:
            events.append(
                _make_event(
                    **common, sub_rule=SUB_RULE_V3, confirmed=True,
                    ema20_state=ema20_now, dual_ma_state=True,
                )
            )
            v_done[SUB_RULE_V3] = True
        if all(v_done.values()):
            return events

    return events


def detect_two_b_reversal_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别 2B/破底翻事件（V2 C1 结构 / C2 三版本入场 / C3 失效）。"""
    spec = get_rule(RULE_ID)
    reclaim_bars = _params(spec)
    if frame.empty or not _required_columns().issubset(frame.columns):
        return []

    pivots = confirmed_pivots(frame)
    lows = sorted(swing_lows(pivots), key=lambda p: p.index)
    if not lows:
        return []

    reclaim_state = ema20_reclaim_state(frame)
    joint_state = dual_ma_bull_state(frame)
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}

    events: list[SignalEvent] = []
    for l1 in lows:
        start_position = by_day.get(l1.available_date)
        if start_position is None:
            continue
        events.extend(
            _scan_l1(
                frame, symbol, spec,
                l1=l1, reclaim_bars=reclaim_bars,
                reclaim_state=reclaim_state, joint_state=joint_state,
                start_position=start_position,
            )
        )
    events.sort(key=lambda e: (e.available_date, e.event_id))
    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_FAILED",
    "SUB_RULE_V1",
    "SUB_RULE_V2",
    "SUB_RULE_V3",
    "VERSIONS",
    "detect_two_b_reversal_events",
]
