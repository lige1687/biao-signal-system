"""T4 多周期确认的时点计算（参考实现，draft；只用注入的交易所配置与日历，不读机器本地日期）。

核心字段（见 T4/field-contract.md）：
  bar_start/bar_end（交易所时区）→ complete_at（该 bar 所属时段确实结束的时刻）
  → known_at = max(complete_at, source_available_at)（来源时间未知则 known_at 只有下界）
  → decidable_at = 所需全部输入的 known_at 的最大值（任一输入 unknown 则不可决定）
  → earliest_execution_at = 按执行节奏取 decidable_at 之后第一个允许成交时刻
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Exchange:
    tz: str = "Asia/Shanghai"
    sessions: tuple[tuple[dt.time, dt.time], ...] = ((dt.time(9, 30), dt.time(11, 30)),
                                                     (dt.time(13, 0), dt.time(15, 0)))
    hourly_ends: tuple[dt.time, ...] = (dt.time(10, 30), dt.time(11, 30), dt.time(14, 0), dt.time(15, 0))


@dataclass(frozen=True)
class Calendar:
    """日历只回答覆盖范围内的日子；范围外为 unknown，不回退为工作日。"""
    trading: frozenset[dt.date]
    covered_from: dt.date
    covered_to: dt.date

    def status(self, d: dt.date) -> str:
        if not (self.covered_from <= d <= self.covered_to):
            return "unknown"
        return "trading" if d in self.trading else "closed"

    def next_trading(self, d: dt.date) -> dt.date | None:
        x = d + dt.timedelta(days=1)
        while x <= self.covered_to:
            if x in self.trading:
                return x
            x += dt.timedelta(days=1)
        return None

    def last_trading_of_week(self, d: dt.date) -> dt.date | None:
        monday = d - dt.timedelta(days=d.weekday())
        days = [monday + dt.timedelta(days=i) for i in range(7)]
        if any(self.status(x) == "unknown" for x in days):
            return None
        tr = [x for x in days if x in self.trading]
        return tr[-1] if tr else None

    def last_trading_of_month(self, d: dt.date) -> dt.date | None:
        x = d.replace(day=28) + dt.timedelta(days=4)
        last = x - dt.timedelta(days=x.day)
        days = [d.replace(day=i) for i in range(1, last.day + 1)]
        if any(self.status(y) == "unknown" for y in days):
            return None
        tr = [y for y in days if y in self.trading]
        return tr[-1] if tr else None


@dataclass
class Fact:
    """一个可用于确认的价格条目。"""
    item: str
    timeframe: str  # 60m | 1d | 1w
    bar_end: dt.datetime | None  # 交易所时区，带时区
    source_available_at: dt.datetime | None = None
    revisions: list[tuple[dt.datetime, str]] = field(default_factory=list)  # (revised_at, version)
    missing: bool = False


def localize(ex: Exchange, d: dt.date, t: dt.time) -> dt.datetime:
    return dt.datetime.combine(d, t, tzinfo=ZoneInfo(ex.tz))


def complete_at(ex: Exchange, cal: Calendar, f: Fact) -> dt.datetime | None:
    if f.missing or f.bar_end is None:
        return None
    d = f.bar_end.astimezone(ZoneInfo(ex.tz)).date()
    if cal.status(d) != "trading":
        return None
    return f.bar_end


def known_at(ex: Exchange, cal: Calendar, f: Fact) -> tuple[dt.datetime | None, str]:
    c = complete_at(ex, cal, f)
    if c is None:
        return None, "unknown"
    if f.source_available_at is None:
        return c, "lower_bound_only"  # 来源到达时间未记录：只知道不早于完成时刻
    return max(c, f.source_available_at), "exact"


def version_at(f: Fact, when: dt.datetime) -> str:
    v = "v0"
    for revised_at, version in sorted(f.revisions):
        if revised_at <= when:
            v = version
    return v


def decidable_at(ex: Exchange, cal: Calendar, facts: list[Fact], observed_at: dt.datetime) -> dict:
    """observed_at 时刻能否作出依赖 facts 的决定。"""
    obs = observed_at.astimezone(ZoneInfo(ex.tz))
    times, quality = [], []
    for f in facts:
        k, q = known_at(ex, cal, f)
        if k is None:
            return {"status": "unknown", "reason": f"{f.item}: not complete or missing"}
        if k > obs:
            return {"status": "not_yet", "reason": f"{f.item}: known only at {k.isoformat()}"}
        times.append(k)
        quality.append(q)
    return {"status": "decidable", "at": max(times).isoformat(),
            "timing_quality": "exact" if all(q == "exact" for q in quality) else "lower_bound_only",
            "versions": {f.item: version_at(f, obs) for f in facts}}


def next_open(ex: Exchange, cal: Calendar, after: dt.datetime, *, intraday: bool) -> dt.datetime | None:
    """after 之后第一个允许成交时刻。intraday=False：下一交易日开盘（日线参考）；True：本交易日下一时段开始。"""
    a = after.astimezone(ZoneInfo(ex.tz))
    d = a.date()
    if intraday and cal.status(d) == "trading":
        for s, e in ex.sessions:
            start, end = localize(ex, d, s), localize(ex, d, e)
            if a < start:
                return start
            if start <= a < end:
                return a  # 时段内：从这一刻起可成交（研究上取下一根 bar 开始）
    nd = cal.next_trading(d) if not (cal.status(d) == "trading" and a < localize(ex, d, ex.sessions[0][0])) else d
    return localize(ex, nd, ex.sessions[0][0]) if nd else None


def execution(ex: Exchange, cal: Calendar, decided: dt.datetime, cadence: str) -> dict:
    """执行节奏：daily_reference（原文 §3.2）| weekly_action | month_end_action。"""
    d = decided.astimezone(ZoneInfo(ex.tz)).date()
    if cadence == "daily_reference":
        return {"evaluate_at": decided.isoformat(), "execute_at": _iso(next_open(ex, cal, decided, intraday=False))}
    anchor = cal.last_trading_of_week(d) if cadence == "weekly_action" else cal.last_trading_of_month(d)
    if anchor is None:
        return {"evaluate_at": None, "execute_at": None, "reason": "calendar unknown for the period"}
    if anchor < d:
        anchor = cal.last_trading_of_week(cal.next_trading(d)) if cadence == "weekly_action" else \
            cal.last_trading_of_month(cal.next_trading(d))
    evaluate = localize(ex, anchor, ex.sessions[-1][1])
    return {"evaluate_at": evaluate.isoformat(), "execute_at": _iso(next_open(ex, cal, evaluate, intraday=False)),
            "note": "conditions must be re-checked at evaluate_at with data known then; not the earlier signal"}


def _iso(x):
    return x.isoformat() if x else None
