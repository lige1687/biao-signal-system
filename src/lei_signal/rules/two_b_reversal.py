"""2B / 破底翻反转研究代理（规格 §9 模块 C）。

严格前向状态机：用 confirmed_pivots 识别 L2（更低确认低点）/ L1（更高确认低点）结构，
自 L1 确认日起向前扫描「跌破 L1 -> 快速收回」的破底翻动作，分三版本确认入场；
跌破 L2 或快速收复窗口耗尽则失效。每个 L1/L2 结构只允许一次 2B 确认。

规格原文未提供 2B 具体结构定义（[原文未提供]），L1/L2 量化口径为研究代理，
必须标 research_proxy。EMA20/双均线确认复用 dual_ma 既有状态机，不另算阈值。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Pivot, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.features.pivots import confirmed_pivots, swing_highs, swing_lows
from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state

RULE_ID = "two_b_reversal"
SUB_RULE_V1 = "two_b_reversal_v1_confirmed"
SUB_RULE_V2 = "two_b_reversal_v2_confirmed"
SUB_RULE_V3 = "two_b_reversal_v3_confirmed"
SUB_RULE_FAILED = "two_b_reversal_failed"

#: 三版本入场：v1=收盘站上 L1；v2=+EMA20 拐头向上；v3=+EMA20 与 SMA20 共同向上。
VERSIONS: tuple[tuple[str, str, str], ...] = (
    (SUB_RULE_V1, "v1", "收盘站上 L1"),
    (SUB_RULE_V2, "v2", "站上 L1 且 EMA20 拐头向上"),
    (SUB_RULE_V3, "v3", "站上 L1 且 EMA20 与 SMA20 共同向上"),
)


def _params(spec: RuleSpec) -> int:
    reclaim_bars = int(spec.param("two_b_reclaim_bars", 3))
    if reclaim_bars <= 0:
        raise ValueError("two_b_reversal 的 two_b_reclaim_bars 必须为正")
    return reclaim_bars


def _required_columns() -> set[str]:
    return {"open", "high", "low", "close", "ema20", "ema120", "sma20", "signal_color"}


def _bias_ema120(frame: pd.DataFrame, position: int) -> float | None:
    row = frame.iloc[position]
    ema120 = row.get("ema120")
    close = row.get("close")
    if ema120 is None or close is None or pd.isna(ema120) or pd.isna(close) or float(ema120) == 0:
        return None
    return float(close) / float(ema120) - 1.0


def _make_confirmed(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    sub_rule: str,
    version: str,
    version_cn: str,
    l1_price: float,
    l2_price: float,
    neckline: float | None,
    close: float,
    reclaim_date: date,
    breakdown_date: date,
    bars_to_reclaim: int,
    ema20_state: bool,
    dual_ma_state: bool,
    bias_ema120: float | None,
) -> SignalEvent:
    reason = (
        f"2B/破底翻 {version} 确认：跌破 L1({l1_price:.4f}) 后 {bars_to_reclaim} 根内收回其上方"
        f"（{version_cn}）；L2={l2_price:.4f} 为结构失效线"
    )
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
        direction=Direction.BULLISH,
        severity=Severity.IMPORTANT,
        strength=75,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": sub_rule,
            "research_proxy": True,
            "version": version,
            "version_cn": version_cn,
            "l1_price": l1_price,
            "l2_price": l2_price,
            "neckline": neckline,
            "close": close,
            "breakdown_date": breakdown_date.isoformat(),
            "reclaim_date": reclaim_date.isoformat(),
            "bars_to_reclaim": bars_to_reclaim,
            "ema20_reclaim_state": ema20_state,
            "dual_ma_bull_state": dual_ma_state,
            "bias_ema120": bias_ema120,
            "bias_enhancement_only": True,  # 大幅负乖离仅作增强记录，不单独触发
        },
        invalidation={
            "condition": f"收盘跌破 L2({l2_price:.4f})，2B 结构彻底失效",
        },
    )


def _make_failed(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    l1_price: float,
    l2_price: float,
    close: float,
    failure_reason: str,
) -> SignalEvent:
    reason = f"2B/破底翻失败：{failure_reason}"
    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{lifecycle_id}:{SUB_RULE_FAILED}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.NEUTRAL,
        severity=Severity.INFO,
        strength=35,
        reason_cn=reason,
        provenance=spec.provenance,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": SUB_RULE_FAILED,
            "research_proxy": True,
            "l1_price": l1_price,
            "l2_price": l2_price,
            "close": close,
            "failure_reason": failure_reason,
        },
        invalidation={"condition": "失败事件是历史事实，不会被后续上涨改写"},
    )


def _scan_structure(
    frame: pd.DataFrame,
    symbol: str,
    spec: RuleSpec,
    *,
    l2: Pivot,
    l1: Pivot,
    neckline_pivot: Pivot,
    reclaim_bars: int,
    reclaim_state: pd.Series,
    joint_state: pd.Series,
    start_position: int,
) -> list[SignalEvent]:
    """单个 L1/L2 结构的前向扫描：跌破 L1 -> 收回 -> 三版本确认 / 失效。"""
    events: list[SignalEvent] = []
    lifecycle_id = f"{RULE_ID}:{symbol}:{l1.available_date.isoformat()}"
    l2_price = float(l2.price)
    l1_price = float(l1.price)
    neckline = float(neckline_pivot.price)

    broken_down = False
    breakdown_position: int | None = None
    breakdown_date: date | None = None
    reclaimed = False
    reclaim_position: int | None = None
    v_done = {SUB_RULE_V1: False, SUB_RULE_V2: False, SUB_RULE_V3: False}
    consumed = False

    for position in range(start_position, len(frame)):
        row = frame.iloc[position]
        close = float(row["close"])
        day = frame.index[position].date()
        bias = _bias_ema120(frame, position)

        # C3：收盘跌破 L2 -> 2B 彻底失效（最高优先级，任何阶段）。
        if close < l2_price:
            if not consumed:
                events.append(
                    _make_failed(
                        spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                        l1_price=l1_price, l2_price=l2_price, close=close,
                        failure_reason="收盘跌破 L2，2B 结构彻底失效",
                    )
                )
                consumed = True
            break

        if consumed:
            break

        if not broken_down:
            # 等待跌破 L1（假跌破/破底）。
            if close < l1_price:
                broken_down = True
                breakdown_position = position
                breakdown_date = day
            continue

        assert breakdown_position is not None and breakdown_date is not None
        if not reclaimed:
            bars_since = position - breakdown_position
            # 快速收复窗口耗尽（未收回 L1 上方）-> 本轮 2B 消耗。
            if bars_since > reclaim_bars:
                events.append(
                    _make_failed(
                        spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                        l1_price=l1_price, l2_price=l2_price, close=close,
                        failure_reason=f"跌破 L1 后 {reclaim_bars} 根内未收回（快速收复窗口耗尽）",
                    )
                )
                consumed = True
                break
            # 收回 L1 上方 -> 破底翻确认。
            if close >= l1_price:
                reclaimed = True
                reclaim_position = position
                bars_to_reclaim = bars_since
                ema20_now = bool(reclaim_state.iloc[position])
                dual_ma_now = bool(joint_state.iloc[position])
                # v1 当日确认；v2/v3 若当日条件也满足则同日确认。
                for sub_rule, version, version_cn in VERSIONS:
                    if sub_rule == SUB_RULE_V1:
                        cond = True
                    elif sub_rule == SUB_RULE_V2:
                        cond = ema20_now
                    else:
                        cond = dual_ma_now
                    if cond and not v_done[sub_rule]:
                        events.append(
                            _make_confirmed(
                                spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                                sub_rule=sub_rule, version=version, version_cn=version_cn,
                                l1_price=l1_price, l2_price=l2_price, neckline=neckline,
                                close=close, reclaim_date=day, breakdown_date=breakdown_date,
                                bars_to_reclaim=bars_to_reclaim, ema20_state=ema20_now,
                                dual_ma_state=dual_ma_now, bias_ema120=bias,
                            )
                        )
                        v_done[sub_rule] = True
            continue

        # 已收回：继续等待 v2/v3 条件（L2 失效在循环顶部判定）。
        assert reclaim_position is not None
        ema20_now = bool(reclaim_state.iloc[position])
        dual_ma_now = bool(joint_state.iloc[position])
        common = dict(
            spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
            l1_price=l1_price, l2_price=l2_price, neckline=neckline, close=close,
            reclaim_date=frame.index[reclaim_position].date(),
            breakdown_date=breakdown_date,
            bars_to_reclaim=reclaim_position - breakdown_position,
            bias_ema120=bias,
        )
        if not v_done[SUB_RULE_V2] and ema20_now:
            events.append(
                _make_confirmed(
                    **common, sub_rule=SUB_RULE_V2, version="v2",
                    version_cn="站上 L1 且 EMA20 拐头向上",
                    ema20_state=True, dual_ma_state=dual_ma_now,
                )
            )
            v_done[SUB_RULE_V2] = True
        if not v_done[SUB_RULE_V3] and dual_ma_now:
            events.append(
                _make_confirmed(
                    **common, sub_rule=SUB_RULE_V3, version="v3",
                    version_cn="站上 L1 且 EMA20 与 SMA20 共同向上",
                    ema20_state=ema20_now, dual_ma_state=True,
                )
            )
            v_done[SUB_RULE_V3] = True

    return events


def detect_two_b_reversal_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别 2B/破底翻反转事件（C1 结构 / C2 三版本入场 / C3 失效）。"""
    spec = get_rule(RULE_ID)
    reclaim_bars = _params(spec)
    if frame.empty or not _required_columns().issubset(frame.columns):
        return []

    pivots = confirmed_pivots(frame)
    lows = sorted(swing_lows(pivots), key=lambda p: p.index)
    highs = sorted(swing_highs(pivots), key=lambda p: p.index)
    if len(lows) < 2:
        return []

    reclaim_state = ema20_reclaim_state(frame)
    joint_state = dual_ma_bull_state(frame)
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}

    events: list[SignalEvent] = []
    # 连续摆动低点对：L2（更低、更早）-> L1（更高、更晚），中间需有确认摆动高点（颈线）。
    for first, second in zip(lows, lows[1:], strict=False):
        if second.price <= first.price:
            continue
        l2, l1 = first, second
        neckline_pivot = next(
            (h for h in highs if l2.index < h.index < l1.index), None
        )
        if neckline_pivot is None:
            continue
        start_position = by_day.get(l1.available_date)
        if start_position is None:
            continue
        events.extend(
            _scan_structure(
                frame, symbol, spec,
                l2=l2, l1=l1, neckline_pivot=neckline_pivot,
                reclaim_bars=reclaim_bars,
                reclaim_state=reclaim_state, joint_state=joint_state,
                start_position=start_position,
            )
        )
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
