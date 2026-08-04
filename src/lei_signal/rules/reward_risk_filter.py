"""盈亏比计算（规格第 10 节，研究代理，只算不强制）。

入场前用信号时已存在的目标 B 计算盈亏比 R/R = (B - A) / (A - S)：
  A = 入场价（信号确认日收盘）；
  S = 失效价（入场依据的支撑/结构位被破坏的位置）；
  B = 目标价，优先级：已确认摆动高点(B1) > 筹码峰VAH/POC > 区间另一侧高点；
     无法客观确定 B 时标记“目标不可计算”，不事后选最优目标。

严格前向：目标 B 只用信号日及此前已确认的数据；追加未来行情不改变历史 R/R。
本模块只计算，不做硬过滤（已确认）。不向主事件日志写事件——R/R 是入场信号的
派生属性，由回测与界面按需读取，避免污染只追加事件日志的计数不变量。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.domain.rules_config import RuleSpec, get_rule
from lei_signal.domain.types import Pivot, SignalEvent
from lei_signal.features.volume_profile import compute_volume_profile
from lei_signal.rules.resistance_b1 import find_b1

RULE_ID = "reward_risk_filter"

#: 参与 R/R 计算的入场确认子规则（模块 A / 模块 D 做多入场）。
ENTRY_RULE_IDS = ("first_ma_pullback", "false_breakout_reclaim")
ENTRY_CONFIRMED_SUBS = (
    "first_ma_pullback_confirmed",
    "false_breakout_reclaim_confirmed",
)

TARGET_SWING_HIGH = "swing_high"
TARGET_VOLUME_PROFILE = "volume_profile"
TARGET_RANGE_HIGH = "range_high"
TARGET_UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class RewardRiskResult:
    """单笔入场信号的盈亏比计算结果。"""

    entry_event_id: str
    entry_rule_id: str
    available_date: date
    entry_price: float
    stop_price: float | None
    target_b: float | None
    target_source: str | None  # swing_high | volume_profile | range_high | None
    reward_risk: float | None  # None = 不可计算（无目标或风险非正）
    computable: bool
    reason_cn: str


def _params(spec: RuleSpec) -> int:
    lookback = int(spec.param("range_lookback", 60))
    if lookback <= 0:
        raise ValueError("reward_risk_filter 的 range_lookback 必须为正")
    return lookback


def _stop_price(frame: pd.DataFrame, entry_event: SignalEvent) -> float | None:
    """入场依据的失效价。按入场规则取客观支撑位，不事后调整。"""
    rule_id = entry_event.rule_id
    evidence = entry_event.evidence or {}
    if rule_id == "false_breakout_reclaim":
        ref = evidence.get("reference_price")
        return float(ref) if ref is not None else None
    if rule_id == "first_ma_pullback":
        touch_date_raw = evidence.get("touch_date")
        if touch_date_raw:
            try:
                touch_day = date.fromisoformat(str(touch_date_raw))
            except ValueError:
                touch_day = None
            if touch_day is not None:
                try:
                    return float(frame.loc[pd.Timestamp(touch_day), "low"])
                except KeyError:
                    pass
        ma_value = evidence.get("ma_value")
        return float(ma_value) if ma_value is not None else None
    return None


def _target_b(
    frame: pd.DataFrame,
    *,
    position: int,
    entry_price: float,
    pivots: tuple[Pivot, ...],
    as_of: date,
    range_lookback: int,
) -> tuple[float | None, str | None]:
    """按优先级确定目标 B，只用信号日及此前已确认数据。"""
    # 1) 已确认摆动高点（B1 第一阻力）
    b1 = find_b1(pivots, as_of=as_of, current_close=entry_price)
    if b1 is not None and b1.price > entry_price:
        return float(b1.price), TARGET_SWING_HIGH

    # 2) 筹码分布代理 VAH/POC（高于入场价者，逐点计算避免未来泄漏）
    profile = compute_volume_profile(frame.iloc[: position + 1])
    if profile is not None:
        for candidate in (profile.vah, profile.poc):
            if candidate is not None and candidate > entry_price:
                return float(candidate), TARGET_VOLUME_PROFILE

    # 3) 区间另一侧：近 range_lookback 根已完成 K 线的最高 high
    start = max(0, position - range_lookback)
    window = frame["high"].iloc[start:position]
    if not window.empty:
        range_high = float(window.max())
        if range_high > entry_price:
            return range_high, TARGET_RANGE_HIGH

    return None, None


def compute_reward_risk(
    frame: pd.DataFrame,
    entry_event: SignalEvent,
    pivots: tuple[Pivot, ...],
) -> RewardRiskResult:
    """计算单笔入场的盈亏比。严格前向，无未来泄漏。"""
    spec = get_rule(RULE_ID)
    range_lookback = _params(spec)

    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    position = by_day.get(entry_event.available_date)
    evidence = entry_event.evidence or {}
    entry_price_raw = evidence.get("close")
    if position is None or entry_price_raw is None:
        return RewardRiskResult(
            entry_event_id=entry_event.event_id,
            entry_rule_id=entry_event.rule_id,
            available_date=entry_event.available_date,
            entry_price=0.0,
            stop_price=None,
            target_b=None,
            target_source=TARGET_UNAVAILABLE,
            reward_risk=None,
            computable=False,
            reason_cn="入场事件缺少收盘价或不在行情区间内，目标不可计算",
        )
    entry_price = float(entry_price_raw)
    stop_price = _stop_price(frame, entry_event)
    target_b, target_source = _target_b(
        frame,
        position=position,
        entry_price=entry_price,
        pivots=pivots,
        as_of=entry_event.available_date,
        range_lookback=range_lookback,
    )

    if stop_price is None or stop_price >= entry_price:
        return RewardRiskResult(
            entry_event_id=entry_event.event_id,
            entry_rule_id=entry_event.rule_id,
            available_date=entry_event.available_date,
            entry_price=entry_price,
            stop_price=stop_price,
            target_b=target_b,
            target_source=target_source,
            reward_risk=None,
            computable=False,
            reason_cn="失效价不可用或不低于入场价，风险非正，R/R 不可计算",
        )
    if target_b is None or target_b <= entry_price:
        return RewardRiskResult(
            entry_event_id=entry_event.event_id,
            entry_rule_id=entry_event.rule_id,
            available_date=entry_event.available_date,
            entry_price=entry_price,
            stop_price=stop_price,
            target_b=target_b,
            target_source=TARGET_UNAVAILABLE,
            reward_risk=None,
            computable=False,
            reason_cn="信号时无可客观确定的目标 B，标记为“目标不可计算”",
        )

    risk = entry_price - stop_price
    reward = target_b - entry_price
    rr = reward / risk if risk > 0 else None
    return RewardRiskResult(
        entry_event_id=entry_event.event_id,
        entry_rule_id=entry_event.rule_id,
        available_date=entry_event.available_date,
        entry_price=entry_price,
        stop_price=stop_price,
        target_b=target_b,
        target_source=target_source,
        reward_risk=rr,
        computable=True,
        reason_cn=(
            f"R/R={rr:.2f}（目标 {target_source}，"
            f"入场 {entry_price:.2f}，失效 {stop_price:.2f}）"
        ),
    )


def compute_reward_risk_for_entries(
    frame: pd.DataFrame,
    events: list[SignalEvent],
    pivots: tuple[Pivot, ...],
) -> list[RewardRiskResult]:
    """对所有模块 A/D 做多入场确认事件计算 R/R。"""
    entries = [
        event
        for event in events
        if event.rule_id in ENTRY_RULE_IDS
        and (event.evidence or {}).get("sub_rule") in ENTRY_CONFIRMED_SUBS
    ]
    return [compute_reward_risk(frame, event, pivots) for event in entries]


TARGET_SOURCE_CN: dict[str | None, str] = {
    TARGET_SWING_HIGH: "已确认摆动高点（B1）",
    TARGET_VOLUME_PROFILE: "筹码分布代理 VAH/POC",
    TARGET_RANGE_HIGH: "区间另一侧高点",
    TARGET_UNAVAILABLE: "目标不可计算",
    None: "目标不可计算",
}


__all__ = [
    "ENTRY_CONFIRMED_SUBS",
    "ENTRY_RULE_IDS",
    "RULE_ID",
    "TARGET_RANGE_HIGH",
    "TARGET_SOURCE_CN",
    "TARGET_SWING_HIGH",
    "TARGET_UNAVAILABLE",
    "TARGET_VOLUME_PROFILE",
    "RewardRiskResult",
    "compute_reward_risk",
    "compute_reward_risk_for_entries",
]
