"""EMA20 早期转强的**分档结构绑定**。

背景与口径（round 2 语义收尾）
------------------------------------------------
旧实现只把 EMA20 早期转强绑定到已 ``confirmed`` 的底部结构，候选期的转强
一律丢弃。实测（8 组独立序列 × 800 根日线）显示：31.5% 的底部结构从未
进入 confirmed，其转强信号被整段丢弃；即便最终确认的结构，也平均延迟
6.5 个自然日（P90 18 天）才被看见——与规则名「早期转强」自相矛盾。

现行口径：

1. **candidate 期底部即可绑定**，但只进入 ``early_watch`` 档。
   early_watch **不视为结构确认，也不视为买入信号**：状态机不会因此把
   机会阶段抬升到 ``Stage.EARLY_STRENGTH``（那一档排在「结构确认」之上，
   让候选越级是错误语义）。
2. 后续「结构确认 → 双均线共同确认 → 长周期改善」沿用**同一
   structure_id 的同一条观察实例**逐级升级：升级事件与开启事件共享
   ``lifecycle_id``，不重开实例。
3. 升级严格单调，只升不降。同一档不重复发事件。
4. **触及 C 永久失效** → 观察实例随结构一起终止，之后不再复活。
5. **颜色转黑只关闭转强生命周期**，不使底部结构失效；转黑之后若再次出现
   EMA20 转强，开启的是一条**新的**观察实例（新 ``lifecycle_id``）。

为什么每一档都是独立 ``sub_rule``
------------------------------------------------
研究层的分组键是 ``f"{rule_id}:{sub_rule}"``。给每一档独立 sub_rule 后，
前向收益统计天然按档分开，候选期样本不会污染已确认档的胜率基线。这是
「放开候选绑定」可被接受的前提条件——否则就是拿噪声稀释已有统计。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import (
    Direction,
    Provenance,
    Severity,
    SignalEvent,
    StructureInstance,
)
from lei_signal.events.log import make_event

RULE_ID = "ema20_reclaim_rising"

TIER_EARLY_WATCH = "early_watch"
TIER_STRUCTURE_CONFIRMED = "structure_confirmed"
TIER_JOINT_CONFIRMED = "joint_confirmed"
TIER_LONG_TREND_IMPROVED = "long_trend_improved"

#: 升级阶梯。序列顺序即档位顺序，只允许沿此序列单调上行。
TIER_LADDER: tuple[str, ...] = (
    TIER_EARLY_WATCH,
    TIER_STRUCTURE_CONFIRMED,
    TIER_JOINT_CONFIRMED,
    TIER_LONG_TREND_IMPROVED,
)
TIER_RANK: dict[str, int] = {tier: index + 1 for index, tier in enumerate(TIER_LADDER)}
SUB_RULE_BY_TIER: dict[str, str] = {tier: f"{RULE_ID}_{tier}" for tier in TIER_LADDER}
TIER_BY_SUB_RULE: dict[str, str] = {
    sub_rule: tier for tier, sub_rule in SUB_RULE_BY_TIER.items()
}

#: early_watch 是「观察」不是「买入」。任何把事件当作机会升级依据的下游都
#: 必须显式排除本集合。集合化而不是散落的字符串比较，是为了让排除点可被
#: grep 找全、可被测试锁定。
EARLY_WATCH_SUB_RULES = frozenset({SUB_RULE_BY_TIER[TIER_EARLY_WATCH]})

#: 各档强度。early_watch 明显低于确认档，避免在任何按 strength 排序的
#: 界面里与真正的确认信号混为一谈。
TIER_STRENGTH: dict[str, int] = {
    TIER_EARLY_WATCH: 35,
    TIER_STRUCTURE_CONFIRMED: 60,
    TIER_JOINT_CONFIRMED: 75,
    TIER_LONG_TREND_IMPROVED: 85,
}
TIER_SEVERITY: dict[str, Severity] = {
    TIER_EARLY_WATCH: Severity.WATCH,
    TIER_STRUCTURE_CONFIRMED: Severity.IMPORTANT,
    TIER_JOINT_CONFIRMED: Severity.IMPORTANT,
    TIER_LONG_TREND_IMPROVED: Severity.IMPORTANT,
}
TIER_LABEL_CN: dict[str, str] = {
    TIER_EARLY_WATCH: "候选观察档",
    TIER_STRUCTURE_CONFIRMED: "结构确认档",
    TIER_JOINT_CONFIRMED: "共同确认档",
    TIER_LONG_TREND_IMPROVED: "长周期改善档",
}


def tier_on(
    structure: StructureInstance,
    day: date,
    *,
    joint_now: bool,
    long_improved: bool,
) -> str:
    """当日该结构应处的观察档位。

    阶梯是**累积**的：高档必然同时满足所有低档条件。没有「跳过结构确认
    直接共同确认」这种档位——那会让 candidate 结构凭双均线状态越级。
    """
    confirmed = structure.confirmed_date
    if confirmed is None or day < confirmed:
        return TIER_EARLY_WATCH
    if not joint_now:
        return TIER_STRUCTURE_CONFIRMED
    if not long_improved:
        return TIER_JOINT_CONFIRMED
    return TIER_LONG_TREND_IMPROVED


def long_improved_series(frame: pd.DataFrame) -> pd.Series:
    """长周期改善逐日布尔。

    直接复用 ``compute_long_trend`` 已产出的两列，不在此处另算一套阈值：
    同一口径在两个地方各实现一次，迟早会漂移。
    """
    improving = frame.get("long_is_improving")
    supportive = frame.get("long_is_supportive")
    if improving is None and supportive is None:
        return pd.Series(False, index=frame.index)
    if improving is None:
        improving = pd.Series(False, index=frame.index)
    if supportive is None:
        supportive = pd.Series(False, index=frame.index)
    combined = improving.fillna(False).astype(bool) | supportive.fillna(False).astype(bool)
    return combined


def _black_series(frame: pd.DataFrame) -> pd.Series:
    if "signal_color" not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame["signal_color"].astype(str).eq("black")


def detect_structure_bound_ema_reclaim(
    frame: pd.DataFrame,
    symbol: str,
    bottoms: list[StructureInstance],
) -> list[SignalEvent]:
    """为每个底部结构生成**结构关联 + 分档**的 EMA 早期转强事件。

    不产生任何「全局」转强事件：全局事件无法回答「转强属于哪个底部」，
    在多结构并存时会把不同结构的胜率搅在一起。
    """
    spec = get_rule(RULE_ID)
    reclaim = _reclaim_state(frame)
    joint = _joint_state(frame)
    long_improved = long_improved_series(frame)
    is_black = _black_series(frame)

    events: list[SignalEvent] = []
    sorted_bottoms = sorted(bottoms, key=lambda s: (s.detected_date, s.structure_id))
    for structure in sorted_bottoms:
        events.extend(
            _observe_one_structure(
                frame,
                symbol,
                structure,
                spec_rule_id=spec.rule_id,
                spec_version=spec.version,
                provenance=spec.provenance,
                reclaim=reclaim,
                joint=joint,
                long_improved=long_improved,
                is_black=is_black,
            )
        )
    return events


def _reclaim_state(frame: pd.DataFrame) -> pd.Series:
    from lei_signal.rules.dual_ma import ema20_reclaim_state

    return ema20_reclaim_state(frame)


def _joint_state(frame: pd.DataFrame) -> pd.Series:
    from lei_signal.rules.dual_ma import dual_ma_bull_state

    required = ("close", "ema20", "sma20", "signal_color")
    if any(column not in frame.columns for column in required):
        return pd.Series(False, index=frame.index)
    return dual_ma_bull_state(frame)


def _observe_one_structure(
    frame: pd.DataFrame,
    symbol: str,
    structure: StructureInstance,
    *,
    spec_rule_id: str,
    spec_version: str,
    provenance: Provenance,
    reclaim: pd.Series,
    joint: pd.Series,
    long_improved: pd.Series,
    is_black: pd.Series,
) -> list[SignalEvent]:
    """单个底部结构的观察实例推进。

    严格按时间单调推进，任一日的判断只依赖当日及更早的数据。
    """
    events: list[SignalEvent] = []
    detected = structure.detected_date
    invalidated = structure.invalidated_date

    lifecycle_id: str | None = None
    opened_on: date | None = None
    current_rank = 0

    for position, timestamp in enumerate(frame.index):
        day = timestamp.date()
        if day < detected:
            continue
        if invalidated is not None and day >= invalidated:
            # 触及 C 永久失效：结构死亡，观察实例一并终止，不再复活
            break
        if bool(is_black.loc[timestamp]):
            # 转黑只关闭转强生命周期；结构本身继续存活，之后可重新开启新实例
            lifecycle_id = None
            opened_on = None
            current_rank = 0
            continue

        tier = tier_on(
            structure,
            day,
            joint_now=bool(joint.loc[timestamp]),
            long_improved=bool(long_improved.loc[timestamp]),
        )
        rank = TIER_RANK[tier]

        if lifecycle_id is None:
            if not bool(reclaim.loc[timestamp]):
                continue
            lifecycle_id = f"{spec_rule_id}:{structure.structure_id}:{day.isoformat()}"
            opened_on = day
            current_rank = rank
            events.append(
                _make_tier_event(
                    frame=frame,
                    position=position,
                    symbol=symbol,
                    structure=structure,
                    day=day,
                    tier=tier,
                    opened_on=day,
                    lifecycle_id=lifecycle_id,
                    is_upgrade=False,
                    spec_rule_id=spec_rule_id,
                    spec_version=spec_version,
                    provenance=provenance,
                )
            )
            continue

        if rank > current_rank and opened_on is not None:
            current_rank = rank
            events.append(
                _make_tier_event(
                    frame=frame,
                    position=position,
                    symbol=symbol,
                    structure=structure,
                    day=day,
                    tier=tier,
                    opened_on=opened_on,
                    lifecycle_id=lifecycle_id,
                    is_upgrade=True,
                    spec_rule_id=spec_rule_id,
                    spec_version=spec_version,
                    provenance=provenance,
                )
            )
    return events


def _make_tier_event(
    *,
    frame: pd.DataFrame,
    position: int,
    symbol: str,
    structure: StructureInstance,
    day: date,
    tier: str,
    opened_on: date,
    lifecycle_id: str,
    is_upgrade: bool,
    spec_rule_id: str,
    spec_version: str,
    provenance: Provenance,
) -> SignalEvent:
    row = frame.iloc[position]
    previous = frame.iloc[position - 1] if position > 0 else row
    label = TIER_LABEL_CN[tier]
    c_price = structure.c_price
    c_text = f" C={c_price:.4f}" if c_price is not None else ""

    if is_upgrade:
        reason = (
            f"EMA 早期转强升级 → {label}：同一底部 {structure.structure_type}"
            f"{c_text} 的观察实例（自 {opened_on.isoformat()} 起）逐级升级，"
            f"未新开观察"
        )
    elif tier == TIER_EARLY_WATCH:
        reason = (
            f"EMA 早期转强（{label}）：收盘价重新站上 EMA20 且 EMA20 向上；"
            f"关联底部 {structure.structure_type}{c_text} 尚未确认，"
            f"仅作观察，不构成结构确认或买入"
        )
    else:
        reason = (
            f"EMA 早期转强（{label}）：收盘价重新站上 EMA20 且 EMA20 向上，"
            f"关联底部 {structure.structure_type}{c_text}"
        )

    return make_event(
        event_id=make_event_id(
            rule_id=spec_rule_id,
            rule_version=spec_version,
            symbol=symbol,
            timeframe="1d",
            available_date=day,
            source_id=f"structure:{structure.structure_id}:{tier}",
        ),
        symbol=symbol,
        event_date=day,
        available_date=day,
        rule_id=spec_rule_id,
        rule_version=spec_version,
        direction=Direction.BULLISH,
        severity=TIER_SEVERITY[tier],
        strength=TIER_STRENGTH[tier],
        reason_cn=reason,
        provenance=provenance,
        structure_id=structure.structure_id,
        lifecycle_id=lifecycle_id,
        evidence={
            "sub_rule": SUB_RULE_BY_TIER[tier],
            "tier": tier,
            "tier_rank": TIER_RANK[tier],
            "is_upgrade": is_upgrade,
            # 显式布尔，避免下游各自去推断「这算不算买入」
            "is_buy_signal": tier != TIER_EARLY_WATCH,
            "structure_status_at_event": (
                "candidate" if tier == TIER_EARLY_WATCH else "confirmed"
            ),
            "opened_on": opened_on.isoformat(),
            "close": float(row["close"]),
            "ema20": float(row["ema20"]),
            "previous_close": float(previous["close"]),
            "previous_ema20": float(previous["ema20"]),
        },
        invalidation={
            "condition": "关联底部触及 C 永久失效；颜色转黑仅关闭本条转强生命周期",
        },
    )


__all__ = [
    "EARLY_WATCH_SUB_RULES",
    "RULE_ID",
    "SUB_RULE_BY_TIER",
    "TIER_BY_SUB_RULE",
    "TIER_EARLY_WATCH",
    "TIER_JOINT_CONFIRMED",
    "TIER_LABEL_CN",
    "TIER_LADDER",
    "TIER_LONG_TREND_IMPROVED",
    "TIER_RANK",
    "TIER_SEVERITY",
    "TIER_STRENGTH",
    "TIER_STRUCTURE_CONFIRMED",
    "detect_structure_bound_ema_reclaim",
    "long_improved_series",
    "tier_on",
]
