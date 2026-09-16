"""AnalysisResult → CardDTO 纯函数映射。

本模块不做任何 IO，方便单测覆盖卡片上每个字段的推导规则。
"""
from __future__ import annotations

from datetime import UTC, date, datetime, tzinfo
from zoneinfo import ZoneInfo

from lei_signal.api import labels
from lei_signal.api.config import KEY_CHANGE_LOOKBACK_DAYS, SPARKLINE_BARS
from lei_signal.api.explanations import Explanation, lookup
from lei_signal.api.schemas import (
    CardDTO,
    EventDTO,
    ExplanationDTO,
    SparkPoint,
    StructureBriefDTO,
)
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.domain.types import (
    COLOR_CN,
    STAGE_CN,
    Severity,
    SignalEvent,
    StructureInstance,
)

_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.WATCH: 1,
    Severity.IMPORTANT: 2,
    Severity.CRITICAL: 3,
}

_LIVE_STATUSES = {"candidate", "confirmed", "active"}


def to_explanation_dto(exp: Explanation | None) -> ExplanationDTO | None:
    if exp is None:
        return None
    return ExplanationDTO(
        title=exp.get("title", ""),
        definition=exp.get("definition", ""),
        formula=exp.get("formula", ""),
        usage=exp.get("usage", ""),
        invalidation=exp.get("invalidation", ""),
        next_step=exp.get("next_step", ""),
        caveat=exp.get("caveat", ""),
    )


def color_duration(result: AnalysisResult) -> tuple[str | None, int | None]:
    """当前颜色持续交易日数与起始日（frame 末尾向前数连续等值）。"""
    colors = [str(c) for c in result.frame.get("signal_color", [])]
    if not colors:
        return None, None
    current = colors[-1]
    days = 0
    since: str | None = None
    index = result.frame.index
    for i in range(len(colors) - 1, -1, -1):
        if colors[i] != current:
            break
        days += 1
        since = index[i].strftime("%Y-%m-%d")
    return since, days


def key_change(result: AnalysisResult) -> tuple[str | None, str | None]:
    """最近关键变化（文本, 日期）。回退链：

    1. assessment.stage_change_reason_cn（昨日→今日阶段/风险跃迁的现成中文句）
    2. 今日新事件中 severity 最高者
    3. 近 KEY_CHANGE_LOOKBACK_DAYS 天内最近的 important/critical 事件
    4. 都没有 → (None, None)，前端显示「近期无关键变化」
    """
    assessment = result.assessment
    if assessment.stage_change_reason_cn:
        return assessment.stage_change_reason_cn, assessment.as_of.isoformat()

    if assessment.new_events:
        event = max(
            assessment.new_events,
            key=lambda e: (_SEVERITY_RANK.get(e.severity, 0), e.available_date),
        )
        return event.reason_cn, event.available_date.isoformat()

    last_date = result.price_data.report.last_date
    if last_date is not None:
        cutoff = last_date.date().toordinal() - KEY_CHANGE_LOOKBACK_DAYS
        important = [
            e
            for e in result.events
            if e.severity in (Severity.IMPORTANT, Severity.CRITICAL)
            and e.available_date.toordinal() >= cutoff
        ]
        if important:
            event = max(important, key=lambda e: e.available_date)
            return event.reason_cn, event.available_date.isoformat()

    return None, None


def structure_brief(
    structure: StructureInstance,
    *,
    close: float | None,
) -> StructureBriefDTO:
    distance: float | None = None
    if (
        structure.side == "bottom"
        and structure.c_price is not None
        and structure.status.value in _LIVE_STATUSES
        and structure.invalidated_date is None
        and close
    ):
        distance = (close - structure.c_price) / close * 100
    return StructureBriefDTO(
        structure_id=structure.structure_id,
        structure_type=structure.structure_type,
        structure_type_cn=labels.STRUCTURE_TYPE_CN.get(
            structure.structure_type, structure.structure_type
        ),
        side=structure.side,
        status=structure.status.value,
        status_cn=labels.STRUCTURE_STATUS_CN.get(structure.status.value, structure.status.value),
        c_price=structure.c_price,
        neckline=structure.neckline,
        detected_date=structure.detected_date.isoformat(),
        confirmed_date=structure.confirmed_date.isoformat() if structure.confirmed_date else None,
        invalidated_date=(
            structure.invalidated_date.isoformat() if structure.invalidated_date else None
        ),
        invalidated_reason=structure.invalidated_reason,
        distance_to_c_pct=distance,
        explanation=to_explanation_dto(
            lookup(structure_type=structure.structure_type)
        ),
    )


def event_dto(event: SignalEvent, *, as_of: date | None = None) -> EventDTO:
    sub_rule = event.evidence.get("sub_rule") if event.evidence else None
    return EventDTO(
        event_id=event.event_id,
        rule_id=event.rule_id,
        rule_cn=labels.RULE_CN.get(event.rule_id, event.rule_id),
        sub_rule=sub_rule,
        sub_rule_cn=labels.SUB_RULE_CN.get(sub_rule) if sub_rule else None,
        direction=event.direction.value,
        direction_cn=labels.DIRECTION_CN.get(event.direction.value, event.direction.value),
        severity=event.severity.value,
        severity_cn=labels.SEVERITY_CN.get(event.severity.value, event.severity.value),
        reason_cn=event.reason_cn,
        event_date=event.event_date.isoformat(),
        available_date=event.available_date.isoformat(),
        structure_id=event.structure_id,
        lifecycle_id=event.lifecycle_id,
        is_new_today=as_of is not None and event.available_date == as_of,
        evidence=dict(event.evidence or {}),
        invalidation=dict(event.invalidation or {}),
        explanation=to_explanation_dto(
            lookup(rule_id=event.rule_id, sub_rule=sub_rule)
        ),
    )


def is_intraday_forming(result: AnalysisResult, *, now: datetime | None = None) -> bool:
    """最后一根 bar 是否为交易所当日（盘中形成中）。"""
    last_date = result.price_data.report.last_date
    if last_date is None:
        return False
    tz_name = result.price_data.info.timezone
    try:
        tz: tzinfo = ZoneInfo(tz_name)
    except Exception:  # 时区名异常时按 UTC 处理，不阻断卡片
        tz = UTC
    today = (now or datetime.now(UTC)).astimezone(tz).date()
    return last_date.date() == today


def build_card(
    *,
    symbol: str,
    display_name: str,
    market_cn: str,
    group: str,
    result: AnalysisResult | None,
    error: str | None,
    data_time: datetime,
    persist_warning: str | None = None,
) -> CardDTO:
    """组装单张卡片。result 与 error 必有其一（成功/降级）。"""
    card = CardDTO(
        symbol=symbol,
        display_name=display_name,
        market_cn=market_cn,
        group=group,
        data_time=data_time.isoformat(),
        error=error,
        persist_warning=persist_warning,
    )
    if result is None:
        return card

    frame = result.frame
    close = float(frame["close"].iloc[-1]) if len(frame) else None
    prev_close = float(frame["close"].iloc[-2]) if len(frame) >= 2 else None
    card.price = close
    card.prev_close = prev_close
    if close is not None and prev_close:
        card.change_pct = (close / prev_close - 1) * 100
    report = result.price_data.report
    card.last_bar_date = report.last_date.strftime("%Y-%m-%d") if report.last_date else None
    card.is_intraday_forming = is_intraday_forming(result)
    card.provider = report.provider
    card.stale = result.cache_fallback_used

    assessment = result.assessment
    card.color = assessment.color.value
    card.color_cn = COLOR_CN.get(assessment.color.value, assessment.color.value)
    card.color_since, card.color_days = color_duration(result)
    card.key_change_cn, card.key_change_date = key_change(result)
    card.stage = assessment.stage.value
    card.stage_cn = STAGE_CN.get(assessment.stage.value, assessment.stage.value)
    card.risk_state = assessment.risk_state.value
    card.risk_state_cn = labels.RISK_STATE_CN.get(
        assessment.risk_state.value, assessment.risk_state.value
    )

    structure = assessment.primary_structure
    if structure is None and assessment.all_live_structures:
        structure = assessment.all_live_structures[0]
    if structure is not None and structure.is_live:
        card.primary_structure = structure_brief(structure, close=close)

    card.b1_price = assessment.b1_price
    card.distance_to_b1_pct = assessment.distance_to_b1_pct

    tail = frame.tail(SPARKLINE_BARS)
    card.sparkline = [
        SparkPoint(date=idx.strftime("%Y-%m-%d"), close=round(float(row["close"]), 4))
        for idx, row in tail.iterrows()
    ]
    return card
