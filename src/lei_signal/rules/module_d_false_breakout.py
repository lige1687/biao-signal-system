"""模块 D：假突破反向交易（规格 §9 模块 D / 手册 3.5，V2 填实版）。

D1 多头假跌破（两动作**不分先后、必须全部满足**）：
1. 价格跌破密集成交区**最近一个波谷的最低价**后，快速反弹回到突破点上方；
2. 价格站上 20 均线组，且 20 均线组向上弯曲。

- 「密集成交区」与「波谷参照」复用 dense_breakout 的密集区生命周期
  （时钟三类寿命 + 当下带宽达标）与 confirmed_pivots（已确认摆动低点），
  不重复实现（单一真相源）；
- 「快速反弹」窗口 reclaim_window（默认 5，对齐 C2 收复窗口〔标定〕）；
- 「站上 20 均线组且上弯」= close > SMA20 且 close > close_lag20（抵扣价判据）；
- D3 失效：收盘跌破假跌破低点（破位期间最低 low）。

D2 空头假突破：本版仅做多，空头仅记录——当前不实现空头事件（规格
direction 已定（拍板）仅做多）。与 v1 近似件 false_breakout_reclaim
（向上突破前高被打回再收回）结构相似但方向相反、参照不同，**分组对比、
不合并**（audit 第 8 条）。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Pivot, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.features.pivots import confirmed_pivots, swing_lows
from lei_signal.rules.clock_classifier import TYPE3_SIDEWAYS, clock_series
from lei_signal.rules.dense_breakout import _bandwidth_condition, _state_age_series

RULE_ID = "module_d_false_breakout"
SUB_RULE_CONFIRMED = "module_d_long_confirmed"
SUB_RULE_FAILED = "module_d_failed"


def _params(spec: RuleSpec) -> tuple[int, float, int, int]:
    tradability = get_rule("tradability_gate")
    return (
        int(spec.param("reclaim_window", 5)),
        float(tradability.param("cluster_threshold", 0.02)),
        int(tradability.param("minimum_consolidation_bars", 126)),
        int(spec.param("zone_exit_bars", 20)),
    )


def _required_columns() -> set[str]:
    return {"open", "high", "low", "close", "sma20", "close_lag20"}


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    lifecycle_id: str,
    confirmed: bool,
    valley_price: float,
    false_low: float | None,
    close: float,
    breakdown_date: date | None = None,
    reclaim_date: date | None = None,
    bars_to_reclaim: int | None = None,
    failure_reason: str | None = None,
) -> SignalEvent:
    if confirmed:
        reason = (
            f"假跌破反转确认（D1 两动作齐备）：跌破密集区波谷({valley_price:.4f})后 "
            f"{bars_to_reclaim} 根内收回，且站上 20 均线组并上弯；"
            f"失效线 = 假跌破低点({false_low:.4f})"
        )
        severity = Severity.IMPORTANT
        strength = 75
        direction = Direction.BULLISH
        evidence = {
            "sub_rule": SUB_RULE_CONFIRMED,
            "research_proxy": True,
            "close": close,
            "stop_price": false_low,
            "valley_price": valley_price,
            "false_low": false_low,
            "breakdown_date": breakdown_date.isoformat() if breakdown_date else None,
            "reclaim_date": reclaim_date.isoformat() if reclaim_date else None,
            "bars_to_reclaim": bars_to_reclaim,
        }
        invalidation = {
            "condition": f"收盘跌破假跌破低点({false_low:.4f})，反转逻辑失效（D3）"
        }
    else:
        reason = f"假跌破反转失败：{failure_reason or '条件未成立'}"
        severity = Severity.INFO
        strength = 35
        direction = Direction.NEUTRAL
        evidence = {
            "sub_rule": SUB_RULE_FAILED,
            "research_proxy": True,
            "close": close,
            "valley_price": valley_price,
            "false_low": false_low,
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
            source_id=lifecycle_id,
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


def _zone_intervals(
    frame: pd.DataFrame, cluster_threshold: float, min_bars: int, exit_bars: int
) -> list[tuple[int, int]]:
    """密集区生命周期区间 [start, end)（位置下标）：复用 B1 判定口径。"""
    clock3 = clock_series(frame) == TYPE3_SIDEWAYS
    bandwidth = _bandwidth_condition(frame, cluster_threshold)
    age = _state_age_series(clock3, exit_bars=exit_bars)
    active = (clock3 & bandwidth & (age >= min_bars)).to_numpy()
    intervals: list[tuple[int, int]] = []
    start: int | None = None
    loose = 0
    for position, flag in enumerate(active):
        if flag:
            if start is None:
                start = position
            loose = 0
        elif start is not None:
            loose += 1
            if loose > exit_bars:
                intervals.append((start, position - loose + 1))
                start = None
                loose = 0
    if start is not None:
        intervals.append((start, len(frame)))
    return intervals


def _scan_zone(
    frame: pd.DataFrame,
    symbol: str,
    spec: RuleSpec,
    *,
    reclaim_window: int,
    valley: Pivot,
    start_position: int,
) -> list[SignalEvent]:
    """单个波谷参照的假跌破循环：跌破 -> 创新低 -> 双动作齐备 -> 确认/失效。"""
    events: list[SignalEvent] = []
    lifecycle_id = (
        f"{RULE_ID}:{symbol}:{valley.available_date.isoformat()}"
    )
    valley_price = float(valley.price)
    start = start_position

    broken_down = False
    breakdown_position: int | None = None
    false_low: float | None = None
    action_reclaim = False
    reclaim_date: date | None = None
    bars_to_reclaim: int | None = None
    done = False

    for position in range(start, len(frame)):
        row = frame.iloc[position]
        close = float(row["close"])
        low = float(row["low"])
        day = frame.index[position].date()

        if false_low is not None and close < false_low:
            # D3：假跌破低点失守 -> 彻底失效。
            if not done:
                events.append(
                    _make_event(
                        spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                        confirmed=False, valley_price=valley_price,
                        false_low=false_low, close=close,
                        breakdown_date=(
                            frame.index[breakdown_position].date()
                            if breakdown_position is not None
                            else None
                        ),
                        failure_reason="收盘跌破假跌破低点，反转逻辑失效",
                    )
                )
                done = True
            break

        if not broken_down:
            if close < valley_price:
                broken_down = True
                breakdown_position = position
                false_low = low
            continue

        assert breakdown_position is not None and false_low is not None
        false_low = min(false_low, low)

        # 动作 1：快速反弹回突破点上方（收复窗口内）。
        if not action_reclaim:
            bars_since = position - breakdown_position
            if bars_since > reclaim_window:
                if not done:
                    events.append(
                        _make_event(
                            spec=spec, symbol=symbol, day=day,
                            lifecycle_id=lifecycle_id, confirmed=False,
                            valley_price=valley_price, false_low=false_low,
                            close=close,
                            breakdown_date=frame.index[breakdown_position].date(),
                            failure_reason=(
                                f"跌破波谷后 {reclaim_window} 根内未收回（窗口耗尽）"
                            ),
                        )
                    )
                    done = True
                break
            if close >= valley_price:
                action_reclaim = True
                reclaim_date = day
                bars_to_reclaim = bars_since

        # 动作 2：站上 20 均线组且上弯。
        above_ma20_rising = (
            close > float(row["sma20"]) and close > float(row["close_lag20"])
        )
        if action_reclaim and above_ma20_rising and not done:
            events.append(
                _make_event(
                    spec=spec, symbol=symbol, day=day, lifecycle_id=lifecycle_id,
                    confirmed=True, valley_price=valley_price, false_low=false_low,
                    close=close,
                    breakdown_date=frame.index[breakdown_position].date(),
                    reclaim_date=reclaim_date, bars_to_reclaim=bars_to_reclaim,
                )
            )
            done = True
            break

    return events


def detect_module_d_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别假跌破反转事件（D1 双动作 / D3 失效；空头仅记录，未实现）。"""
    spec = get_rule(RULE_ID)
    reclaim_window, cluster_threshold, min_bars, exit_bars = _params(spec)
    if frame.empty or not _required_columns().issubset(frame.columns):
        return []

    by_day = {ts.date(): pos for pos, ts in enumerate(frame.index)}
    pivots = confirmed_pivots(frame)
    valleys = sorted(swing_lows(pivots), key=lambda p: p.index)

    events: list[SignalEvent] = []
    for zone_start, zone_end in _zone_intervals(
        frame, cluster_threshold, min_bars, exit_bars
    ):
        # 密集区期间已确认的波谷（参照）；无波谷则跳过该密集区。
        for valley in valleys:
            start_position = by_day.get(valley.available_date)
            if start_position is None or not (zone_start <= start_position < zone_end):
                continue
            events.extend(
                _scan_zone(
                    frame, symbol, spec,
                    reclaim_window=reclaim_window, valley=valley,
                    start_position=start_position,
                )
            )
    events.sort(key=lambda e: (e.available_date, e.event_id))
    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_CONFIRMED",
    "SUB_RULE_FAILED",
    "detect_module_d_events",
]
