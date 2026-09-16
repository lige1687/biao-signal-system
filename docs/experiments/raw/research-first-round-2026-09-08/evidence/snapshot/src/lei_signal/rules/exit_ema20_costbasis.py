"""抵扣价退出研究代理（规格 A6①）。

严格前向状态机：收盘同时跌破 EMA20 与 20 日抵扣价（close_lag20）即触发退出事件，
仅在条件由不成立转为成立的当日（上升沿）产出事件。任何一天结论只依赖当日及此前数据，
追加未来行情不改变历史触发点。该条件与 LEI 黑色定义同构，但作为独立退出规则单独成
事件、可回测、可展示，不冒充 LEI 原始规则。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Direction, Severity, SignalEvent
from lei_signal.events.log import make_event

RULE_ID = "exit_ema20_costbasis"
SUB_RULE_TRIGGERED = "exit_ema20_costbasis_triggered"


def _params(spec: RuleSpec) -> int:
    period = int(spec.param("costbasis_period", 20))
    if period <= 0:
        raise ValueError("exit_ema20_costbasis 的 costbasis_period 必须为正")
    return period


def _condition(row: pd.Series, costbasis_col: str) -> bool:
    """收盘同时跌破 EMA20 与抵扣价；任一缺失即为不成立。"""
    close = row.get("close")
    ema20 = row.get("ema20")
    costbasis = row.get(costbasis_col)
    if close is None or ema20 is None or costbasis is None:
        return False
    if pd.isna(close) or pd.isna(ema20) or pd.isna(costbasis):
        return False
    return bool(float(close) < float(ema20) and float(close) < float(costbasis))


def _make_event(
    *,
    spec: RuleSpec,
    symbol: str,
    day: date,
    close: float,
    ema20: float,
    costbasis: float,
    costbasis_period: int,
) -> SignalEvent:
    distance_to_ema20_pct = (close / ema20 - 1.0) * 100.0 if ema20 else 0.0
    distance_to_costbasis_pct = (close / costbasis - 1.0) * 100.0 if costbasis else 0.0
    reason = (
        "抵扣价退出触发：收盘同时跌破 EMA20 与 "
        f"{costbasis_period} 日抵扣价（{costbasis_period} 周期前收盘），下一交易日开盘退出"
    )
    return make_event(
        event_id=make_event_id(
            rule_id=spec.rule_id,
            rule_version=spec.version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"{RULE_ID}:{day.isoformat()}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec.rule_id,
        rule_version=spec.version,
        direction=Direction.BEARISH,
        severity=Severity.IMPORTANT,
        strength=70,
        reason_cn=reason,
        provenance=spec.provenance,
        evidence={
            "sub_rule": SUB_RULE_TRIGGERED,
            "research_proxy": True,
            "costbasis_period": costbasis_period,
            "close": close,
            "ema20": ema20,
            "close_lag": costbasis,
            "distance_to_ema20_pct": distance_to_ema20_pct,
            "distance_to_costbasis_pct": distance_to_costbasis_pct,
            "break_basis": "close",
        },
        invalidation={
            "condition": (
                "退出触发为单次事件：条件当日成立即触发，下一交易日开盘执行；"
                "不因后续价格回升而回溯改写"
            )
        },
    )


def detect_exit_ema20_costbasis_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]:
    """识别抵扣价退出触发事件（上升沿）。"""
    spec = get_rule(RULE_ID)
    costbasis_period = _params(spec)
    costbasis_col = f"close_lag{costbasis_period}"
    required = {"close", "ema20", costbasis_col}
    if frame.empty or not required.issubset(frame.columns):
        return []

    events: list[SignalEvent] = []
    prev_condition = False
    for position, timestamp in enumerate(frame.index):
        row = frame.iloc[position]
        condition = _condition(row, costbasis_col)
        # 上升沿：前一日不成立、当日成立。首根无前向对比，不触发。
        if position > 0 and condition and not prev_condition:
            day = timestamp.date()
            events.append(
                _make_event(
                    spec=spec,
                    symbol=symbol,
                    day=day,
                    close=float(row["close"]),
                    ema20=float(row["ema20"]),
                    costbasis=float(row[costbasis_col]),
                    costbasis_period=costbasis_period,
                )
            )
        prev_condition = condition

    return events


__all__ = [
    "RULE_ID",
    "SUB_RULE_TRIGGERED",
    "detect_exit_ema20_costbasis_events",
]
