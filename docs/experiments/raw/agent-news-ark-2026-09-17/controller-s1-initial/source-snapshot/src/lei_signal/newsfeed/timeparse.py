"""严格 ISO8601 时间解析（newsfeed 私有辅助，2026-09-17 S1）。

规则（与计划 §4 对齐）：
- 必须带时区偏移；无时区视为不合法（返回 None），不默默按本地时间解释；
- 语法错误返回 None；
- 是否「未来时间」由调用方按自己的容差判断（``is_future``）。
"""
from __future__ import annotations

from datetime import datetime, timedelta

#: 容忍的微小未来漂移（机器时钟差），超过即视为未来时间。
_FUTURE_TOLERANCE = timedelta(seconds=300)


def parse_iso_ts(value: object) -> datetime | None:
    """解析 ISO8601 字符串为带时区 datetime；无时区或语法错误返回 None。"""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt


def is_future(dt: datetime, now: datetime) -> bool:
    """dt 比 now 晚超过容差即视为未来时间（不合法记录）。"""
    return dt - now > _FUTURE_TOLERANCE


__all__ = ["parse_iso_ts", "is_future"]
