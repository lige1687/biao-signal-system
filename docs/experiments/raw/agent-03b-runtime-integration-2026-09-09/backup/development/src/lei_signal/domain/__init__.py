"""领域层：类型、规则账本与确定性哈希。"""
from lei_signal.domain.canonical import canonical_json, canonical_sha256, make_event_id
from lei_signal.domain.rules_config import get_rule, ruleset_version
from lei_signal.domain.types import (
    COLOR_CN,
    LONG_TREND_CN,
    STAGE_CN,
    STAGE_RANK,
    DailyAssessment,
    Direction,
    Factor,
    LongTrendState,
    Pivot,
    Provenance,
    RiskAlert,
    Severity,
    SignalColor,
    SignalEvent,
    Stage,
    StructureInstance,
    StructureStatus,
)

__all__ = [
    "COLOR_CN", "LONG_TREND_CN", "STAGE_CN", "STAGE_RANK",
    "DailyAssessment", "Direction", "Factor", "LongTrendState", "Pivot",
    "Provenance", "RiskAlert", "Severity", "SignalColor", "SignalEvent",
    "Stage", "StructureInstance", "StructureStatus",
    "canonical_json", "canonical_sha256", "make_event_id",
    "get_rule", "ruleset_version",
]
