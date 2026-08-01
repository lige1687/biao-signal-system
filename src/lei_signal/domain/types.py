"""领域类型：颜色、事件、结构、评估。

本模块只定义数据形状与枚举，不含任何指标、规则或界面逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class SignalColor(StrEnum):
    """LEI 三色 + 数据不足。"""

    GREEN = "green"
    GRAY = "gray"
    BLACK = "black"
    UNKNOWN = "unknown"


class Provenance(StrEnum):
    """规则来源。research_proxy 必须在界面标注「研究代理」。"""

    LEI_EXPLICIT = "lei_explicit"
    LEI_INFERRED = "lei_inferred"
    EXISTING_BACKTEST = "existing_backtest"
    RESEARCH_PROXY = "research_proxy"
    USER_CONFIG = "user_config"


class Direction(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Severity(StrEnum):
    INFO = "info"
    WATCH = "watch"
    IMPORTANT = "important"
    CRITICAL = "critical"


class Stage(StrEnum):
    """机会阶段。顺序即升级顺序（invalidated 除外）。"""

    NO_CLUE = "no_clue"
    BOTTOM_WATCH = "bottom_watch"
    STRUCTURE_CONFIRMED = "structure_confirmed"
    EARLY_STRENGTH = "early_strength"
    JOINT_CONFIRMED = "joint_confirmed"
    TREND_REINFORCED = "trend_reinforced"
    RISK_WATCH = "risk_watch"
    KEY_RISK = "key_risk"
    INVALIDATED = "invalidated"


STAGE_CN: dict[str, str] = {
    "no_clue": "无线索",
    "bottom_watch": "底部观察",
    "structure_confirmed": "结构确认",
    "early_strength": "早期转强",
    "joint_confirmed": "共同确认",
    "trend_reinforced": "趋势增强",
    "risk_watch": "风险关注",
    "key_risk": "关键风险",
    "invalidated": "失效",
}

# 机会阶段排序权重。风险阶段不参与「升级」比较，单独处理。
STAGE_RANK: dict[str, int] = {
    "no_clue": 0,
    "bottom_watch": 1,
    "structure_confirmed": 2,
    "early_strength": 3,
    "joint_confirmed": 4,
    "trend_reinforced": 5,
}

COLOR_CN: dict[str, str] = {
    "green": "绿色",
    "gray": "灰色",
    "black": "黑色",
    "unknown": "数据不足",
}


class StructureStatus(StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


class LongTrendState(StrEnum):
    LONG_BULL = "long_bull"
    LONG_BEAR = "long_bear"
    LONG_IMPROVING = "long_improving"
    LONG_STABLE_BULL = "long_stable_bull"
    LONG_DETERIORATING = "long_deteriorating"
    UNKNOWN = "unknown"


LONG_TREND_CN: dict[str, str] = {
    "long_bull": "多头",
    "long_bear": "空头",
    "long_improving": "改善中",
    "long_stable_bull": "稳定多头",
    "long_deteriorating": "恶化中",
    "unknown": "数据不足",
}


@dataclass(frozen=True, slots=True)
class SignalEvent:
    """一次客观技术事件。只追加，不回写。

    event_date     形态实际发生的日期
    available_date 系统最早能确认它的日期（研究统计必须使用此列）
    """

    event_id: str
    symbol: str
    timeframe: str
    event_date: date
    available_date: date
    rule_id: str
    rule_version: str
    direction: Direction
    severity: Severity
    strength: int
    reason_cn: str
    provenance: Provenance
    evidence: dict[str, Any] = field(default_factory=dict)
    invalidation: dict[str, Any] = field(default_factory=dict)
    structure_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class Pivot:
    """摆动点。区分实际拐点日与确认（最早可用）日。"""

    kind: str  # "high" | "low"
    index: int
    pivot_date: date
    price: float
    confirmed_index: int
    available_date: date


@dataclass
class StructureInstance:
    """底部/顶部结构，是有生命周期的实体，不是布尔字段。"""

    structure_id: str
    symbol: str
    structure_type: str
    side: str  # "bottom" | "top"
    detected_date: date
    c_price: float | None = None
    neckline: float | None = None
    reference_high: float | None = None  # 顶部：第一高点，用于新高解除
    confirmed_date: date | None = None
    status: StructureStatus = StructureStatus.CANDIDATE
    invalidated_date: date | None = None
    invalidated_reason: str | None = None
    source_event_ids: tuple[str, ...] = ()
    provenance: Provenance = Provenance.RESEARCH_PROXY

    @property
    def is_live(self) -> bool:
        """是否仍在生命周期内（候选或已确认，未失效/未过期）。"""
        return self.status in (
            StructureStatus.CANDIDATE,
            StructureStatus.CONFIRMED,
            StructureStatus.ACTIVE,
        )


@dataclass(frozen=True, slots=True)
class Factor:
    """支持或冲突因素，必须可追溯到规则与数值。"""

    dimension: str
    label_cn: str
    detail_cn: str
    rule_id: str
    rule_version: str
    provenance: Provenance
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RiskAlert:
    priority: int
    code: str
    label_cn: str
    detail_cn: str
    rule_id: str
    rule_version: str


@dataclass
class DailyAssessment:
    """每日解释快照。界面每条提示都要能追溯到此结构中的字段。"""

    symbol: str
    as_of: date
    stage: Stage
    color: SignalColor
    new_events: list[SignalEvent] = field(default_factory=list)
    active_events: list[SignalEvent] = field(default_factory=list)
    invalidated_events: list[SignalEvent] = field(default_factory=list)
    supports: list[Factor] = field(default_factory=list)
    conflicts: list[Factor] = field(default_factory=list)
    risks: list[RiskAlert] = field(default_factory=list)
    primary_structure: StructureInstance | None = None
    all_live_structures: list[StructureInstance] = field(default_factory=list)
    active_top: StructureInstance | None = None
    b1_price: float | None = None
    b1_pivot_date: date | None = None
    b1_available_date: date | None = None
    distance_to_b1_pct: float | None = None
    distance_to_b1_r: float | None = None
    dimensions: dict[str, str] = field(default_factory=dict)
    stage_change_reason_cn: str = ""
    previous_stage: Stage | None = None
    data_status: str = "OK"
    rule_ruleset_version: str = ""
    last_data_date: date | None = None


__all__ = [
    "COLOR_CN",
    "LONG_TREND_CN",
    "STAGE_CN",
    "STAGE_RANK",
    "DailyAssessment",
    "Direction",
    "Factor",
    "LongTrendState",
    "Pivot",
    "Provenance",
    "RiskAlert",
    "Severity",
    "SignalColor",
    "SignalEvent",
    "Stage",
    "StructureInstance",
    "StructureStatus",
]
