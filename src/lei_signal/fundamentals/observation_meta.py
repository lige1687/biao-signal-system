"""市场观察数据的来源与时点元数据；不参与交易判定。"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Any


def observation_item(
    *, metric_id: str, label: str, market: str, universe: str, unit: str,
    source_name: str, source_url: str | None, source_access: str,
    value: float | None = None, change: float | None = None, change_unit: str | None = None,
    comparison_period: str | None = None, observation_date: str | None = None,
    published_at: str | None = None, publication_precision: str = "unknown",
    fetched_at: str | None = None, history_start: str | None = None,
    history_end: str | None = None, observation_count: int | None = None,
    valid_count: int | None = None, eligible_count: int | None = None,
    reading: str = "", limitations: list[str] | None = None,
    evidence_refs: list[str] | None = None, quality_reason: str | None = None,
) -> dict[str, Any]:
    """保留已知事实；缺交易日历或发布时间时不声称已核实时效。"""
    def finite(number: float | None) -> bool:
        try:
            return number is not None and math.isfinite(float(number))
        except (TypeError, ValueError, OverflowError):
            return False

    if value is not None and not finite(value):
        value = None
        change = None
        quality_reason = "观测数值不是有限数字，拒绝显示"
    elif change is not None and not finite(change):
        change = None
        quality_reason = "变化数值不是有限数字，已隐藏变化；观测值仅供核对"
    if value is None:
        change = None
    status = "missing" if value is None else "time_unverified"
    if value is not None and observation_date:
        try:
            age = (datetime.now(UTC).date() - date.fromisoformat(observation_date)).days
            if age < 0:
                value = None
                change = None
                status = "missing"
                quality_reason = "观测日期在未来，拒绝显示数值"
        except ValueError:
            value = None
            change = None
            status = "missing"
            quality_reason = "观测日期不是有效 ISO 日期，拒绝显示数值"
    if value is None and quality_reason is None:
        quality_reason = "没有可显示的合格观测值"
    elif value is not None and quality_reason is None:
        quality_reason = "未核实发布时点与交易日历，不能据此判定实时性"
    return {
        "metric_id": metric_id, "label": label, "market": market,
        "universe": universe, "value": value, "unit": unit, "change": change,
        "change_unit": change_unit or ("百分点" if unit == "%" else unit),
        "comparison_period": comparison_period, "observation_date": observation_date,
        "published_at": published_at, "publication_precision": publication_precision,
        "fetched_at": fetched_at, "source_name": source_name,
        "source_url": source_url, "source_access": source_access,
        "definition_version": "market-observations/1", "quality_status": status,
        "quality_reason": quality_reason, "history_start": history_start,
        "history_end": history_end, "observation_count": observation_count,
        "valid_count": valid_count, "eligible_count": eligible_count,
        "reading": reading, "limitations": limitations or [],
        "evidence_refs": evidence_refs or [],
    }
