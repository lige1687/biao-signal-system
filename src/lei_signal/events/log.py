"""只追加事件日志。

不变量：
  1. 同一 event_id 重复写入被忽略（幂等），不覆盖已有事件。
  2. 事件不可回写；状态变化通过新事件记录。
  3. 事件按 (available_date, rule_id) 稳定排序，使输出可复现。

幂等模式参考 Plan Guardian 的事件 DTO 与幂等键设计
(licai-wt-pg-integration@2ee7fdc)，但只定义 SignalEvent，
不引入账本、订单、通知等执行域事件。
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import date

import pandas as pd

from lei_signal.domain.types import Direction, Provenance, Severity, SignalEvent


class EventLog:
    """内存中的只追加事件日志。"""

    def __init__(self) -> None:
        self._events: dict[str, SignalEvent] = {}
        self._duplicate_count = 0

    def append(self, event: SignalEvent) -> bool:
        """追加事件。返回 True 表示新写入，False 表示幂等忽略。"""
        if event.event_id in self._events:
            self._duplicate_count += 1
            return False
        self._events[event.event_id] = event
        return True

    def extend(self, events: Iterable[SignalEvent]) -> int:
        return sum(1 for event in events if self.append(event))

    @property
    def duplicate_count(self) -> int:
        return self._duplicate_count

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[SignalEvent]:
        return iter(self.events())

    def __contains__(self, event_id: object) -> bool:
        return event_id in self._events

    def events(self) -> list[SignalEvent]:
        """稳定排序：先按 available_date，再按 rule_id、event_date、event_id。"""
        return sorted(
            self._events.values(),
            key=lambda e: (e.available_date, e.rule_id, e.event_date, e.event_id),
        )

    def by_rule(self, rule_id: str) -> list[SignalEvent]:
        return [event for event in self.events() if event.rule_id == rule_id]

    def on_date(self, target: date) -> list[SignalEvent]:
        """某天新增的事件（按 available_date）。"""
        return [event for event in self.events() if event.available_date == target]

    def available_through(self, cutoff: date) -> list[SignalEvent]:
        """截止 cutoff（含）已经可用的事件。研究与状态机只能读取这一视图。"""
        return [event for event in self.events() if event.available_date <= cutoff]

    def to_frame(self) -> pd.DataFrame:
        """导出为 DataFrame，供界面时间轴与 CSV 下载使用。"""
        rows = [
            {
                "event_id": event.event_id,
                "symbol": event.symbol,
                "timeframe": event.timeframe,
                "event_date": event.event_date,
                "available_date": event.available_date,
                "rule_id": event.rule_id,
                "rule_version": event.rule_version,
                "direction": event.direction.value,
                "severity": event.severity.value,
                "strength": event.strength,
                "reason_cn": event.reason_cn,
                "provenance": event.provenance.value,
                "structure_id": event.structure_id,
                "evidence": event.evidence,
                "invalidation": event.invalidation,
            }
            for event in self.events()
        ]
        if not rows:
            return pd.DataFrame(
                columns=[
                    "event_id", "symbol", "timeframe", "event_date", "available_date",
                    "rule_id", "rule_version", "direction", "severity", "strength",
                    "reason_cn", "provenance", "structure_id", "evidence", "invalidation",
                ]
            )
        return pd.DataFrame(rows)


def make_event(
    *,
    event_id: str,
    symbol: str,
    event_date: date,
    available_date: date,
    rule_id: str,
    rule_version: str,
    direction: Direction,
    severity: Severity,
    strength: int,
    reason_cn: str,
    provenance: Provenance,
    evidence: dict | None = None,
    invalidation: dict | None = None,
    structure_id: str | None = None,
    timeframe: str = "1d",
    run_id: str | None = None,
) -> SignalEvent:
    """构造事件，强制 available_date >= event_date。"""
    if available_date < event_date:
        raise ValueError(
            f"{rule_id}: available_date({available_date}) 不得早于 event_date({event_date})"
        )
    if not 0 <= strength <= 100:
        raise ValueError(f"{rule_id}: strength 必须在 0..100，得到 {strength}")
    return SignalEvent(
        event_id=event_id,
        symbol=symbol,
        timeframe=timeframe,
        event_date=event_date,
        available_date=available_date,
        rule_id=rule_id,
        rule_version=rule_version,
        direction=direction,
        severity=severity,
        strength=strength,
        reason_cn=reason_cn,
        provenance=provenance,
        evidence=evidence or {},
        invalidation=invalidation or {},
        structure_id=structure_id,
        run_id=run_id,
    )


__all__ = ["EventLog", "make_event"]
