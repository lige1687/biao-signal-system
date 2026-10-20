"""严格 ISO8601 时间解析（newsfeed 私有辅助，2026-09-17 S1）。

规则（与计划 §4 及主控 S1 复核 R1 对齐）：
- 必须带时区偏移；无时区视为不合法（返回 None），不默默按本地时间解释；
- 语法错误返回 None；
- 「未来时间」严格判定（``is_future``）：dt 晚于 now 即未来，不设任何
  未批准的宽限——宽限曾把未来 4 分钟的记录当成正常并产出负年龄。
"""
from __future__ import annotations

from datetime import datetime


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
    """dt 晚于 now 即视为未来时间（严格，无容差；主控复核 R1）。"""
    return dt > now


__all__ = ["parse_iso_ts", "is_future"]
