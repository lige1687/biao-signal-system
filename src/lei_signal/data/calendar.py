"""交易日历：判定「某自然周的最后一个交易日」，支撑周线「收盘后运行」完成语义。

为什么需要它
------------
周线是否「已完成」，本质问题是：**当前这一天是不是本周最后一个交易日？**

这个问题无法从「已观测到的日线」推断出来——周三时你不可能从周一到周三的
K 线里知道周五是不是节假日。它只能来自**交易所提前公布的日历**，而交易所
日历属于合法的 point-in-time 信息（提前一年公布），不构成未来函数。

旧实现绕开了这个问题，改用「下一根日线出现了才算上周结束」。这个规则虽然
安全，却把周线**系统性延迟一个交易日**：正常周五收盘、节假日短周最后一个
交易日收盘，周线都还不可用。属于口径错误。

设计取舍
--------
* 默认日历 ``WeekdayCalendar()`` 只认「周一至周五」，**不内置任何节假日表**。
  这是刻意的保守选择：内置一份手写的节假日表一旦写错日期，会把某周的
  「最后交易日」提前，导致周线在真正收盘前就被判定完成——那是**错误结论**，
  比「晚一天」严重得多。默认日历只会「假设这周有完整的周一至周五」，
  因此永远不会提前完成，最坏情况是退化回旧的延迟行为。
* 调用方可以注入真实的交易所休市日集合（``holidays``），注入后节假日短周
  也能在其最后一个交易日收盘时立即完成。
* ``aggregate_weekly`` 在日历判定不出交易日时（例如整周休市）仍保留
  「下一根日线兜底」，保证任何情况下都能收敛。
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd

#: 周六 = 5、周日 = 6（``pd.Timestamp.weekday()`` 口径）。
_SATURDAY = 5


@runtime_checkable
class TradingCalendar(Protocol):
    """交易日历协议。实现者必须是纯函数式的（不依赖被观测的行情数据）。"""

    def is_trading_day(self, day: date | pd.Timestamp) -> bool:
        """``day`` 是否为交易日。"""
        ...

    def last_trading_day_in_range(
        self,
        start: date | pd.Timestamp,
        end: date | pd.Timestamp,
    ) -> pd.Timestamp | None:
        """``[start, end]`` 闭区间内最后一个交易日；区间内无交易日时返回 ``None``。"""
        ...

    def next_trading_day(self, day: date | pd.Timestamp) -> pd.Timestamp:
        """``day`` 之后的下一个交易日（严格晚于 ``day``）。

        用于监督员算 ``actionable_from``：信号在 ``day`` 收盘后生成，最早
        ``next_trading_day(day)`` 开盘执行（红线 1，无未来泄漏）。
        默认日历不含节假日表，返回值是「未扣节假日的最早可执行日」。
        """
        ...


@dataclass(frozen=True)
class WeekdayCalendar:
    """周一至周五为交易日，可选扣除显式休市日。

    ``holidays`` 为交易所休市日（``datetime.date``）集合。留空即「假设每周
    都是完整的周一至周五」——保守但绝不会提前完成周线。
    """

    holidays: frozenset[date] = frozenset()

    def is_trading_day(self, day: date | pd.Timestamp) -> bool:
        timestamp = pd.Timestamp(day).normalize()
        if timestamp.weekday() >= _SATURDAY:
            return False
        return timestamp.date() not in self.holidays

    def last_trading_day_in_range(
        self,
        start: date | pd.Timestamp,
        end: date | pd.Timestamp,
    ) -> pd.Timestamp | None:
        first = pd.Timestamp(start).normalize()
        cursor = pd.Timestamp(end).normalize()
        while cursor >= first:
            if self.is_trading_day(cursor):
                return cursor
            cursor -= pd.Timedelta(days=1)
        return None

    def next_trading_day(self, day: date | pd.Timestamp) -> pd.Timestamp:
        """``day`` 之后的下一个交易日（严格晚于 ``day``）。

        默认日历不含节假日表，返回「未扣节假日的最早可执行日」。
        加 400 天上限防止「全部未来日都是节假日」的病态输入死循环。
        """
        cursor = pd.Timestamp(day).normalize() + pd.Timedelta(days=1)
        for _ in range(400):
            if self.is_trading_day(cursor):
                return cursor
            cursor += pd.Timedelta(days=1)
        raise ValueError(f"{day} 之后 400 天内无交易日（节假日配置异常）")


def weekday_calendar(holidays: Iterable[date] = ()) -> WeekdayCalendar:
    """构造一个周一至周五日历，扣除给定休市日。"""
    return WeekdayCalendar(frozenset(holidays))


#: 默认日历：周一至周五，无内置节假日（保守，永不提前完成）。
DEFAULT_TRADING_CALENDAR: TradingCalendar = WeekdayCalendar()


__all__ = [
    "DEFAULT_TRADING_CALENDAR",
    "TradingCalendar",
    "WeekdayCalendar",
    "weekday_calendar",
]
