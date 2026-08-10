"""A 股交易时段判定：为收盘后缓存提供「下一开盘前数据不变」的 TTL 依据。

为什么需要它
------------
看盘页的详情（K 线 + 牛熊）与买点分析都走 ``AnalysisService.get``，默认
TTL 900s。A 股收盘后（15:00 之后、周末、节假日）行情不再更新，但默认
TTL 仍会每 15 分钟触发一次重算——用户每次刷新都要等抓取 + 分析 + LLM，
而结果其实没变。

本模块把 TTL 变成**时段感知**：

* 开盘中（交易日 09:30–15:00，含午休）：用短 TTL，盘中持续刷新。
* 收盘后：只要缓存条目是在「最近一次收盘之后」取到的，它就持有当日的最终
  数据，缓存一直新鲜到下一次开盘。这样 18:00 刷新一次后，到次日 09:30 前
  都命中缓存、瞬时返回。

设计取舍
--------
* 午休（11:30–13:00）归入「开盘中」区间——午休时数据也不变，但把它当短
  TTL 处理最多多算几次，远比「午休误判为收盘、把上午数据缓存到次日」安全。
* 时区固定 ``Asia/Shanghai``：A 股交易所统一北京时间，无需按 symbol 推断。
* 仅服务于 A 股标的；海外指数有各自的缓存优先链路（见 services.py）。
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from lei_signal.data.calendar import TradingCalendar

#: A 股所在时区（北京时间）。
SHANGHAI = ZoneInfo("Asia/Shanghai")

#: 上午开盘 09:30。
OPEN = time(9, 30)
#: 下午收盘 15:00。
CLOSE = time(15, 0)

#: 收盘后回溯「上一交易日」的窗口（足够覆盖最长假期）。
_LOOKBACK_DAYS = 30


def _shanghai_now(now: datetime | None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(SHANGHAI)


def is_open(calendar: TradingCalendar, *, now: datetime | None = None) -> bool:
    """A 股当前是否处于「当日数据还在变动」的区间。

    判定为真的区间是交易日的 09:30–15:00（含午休）。收盘后、非交易日一律
    为假——这些时段当日 bar 已固定，适合长缓存。
    """
    sh = _shanghai_now(now)
    if not calendar.is_trading_day(sh.date()):
        return False
    t = sh.time()
    return OPEN <= t < CLOSE


def last_close(calendar: TradingCalendar, *, now: datetime | None = None) -> datetime:
    """最近一次 A 股收盘时刻（UTC）。

    若今日是交易日且已过 15:00，返回今日收盘；否则回溯到上一交易日的收盘。
    用于判断缓存条目是否「取于收盘之后」（即持有当日最终数据）。
    """
    sh = _shanghai_now(now)
    today = sh.date()
    if calendar.is_trading_day(today) and sh.time() >= CLOSE:
        close_day = today
    else:
        prev = calendar.last_trading_day_in_range(
            today - timedelta(days=_LOOKBACK_DAYS), today - timedelta(days=1)
        )
        # 默认日历认定周一至周五都是交易日，回溯 30 天必能命中；兜底退一日。
        close_day = prev.date() if prev is not None else today - timedelta(days=1)
    return datetime.combine(close_day, CLOSE, tzinfo=SHANGHAI).astimezone(UTC)


def next_open(calendar: TradingCalendar, *, now: datetime | None = None) -> datetime:
    """下一次 A 股开盘时刻（UTC）。

    收盘后缓存的有效期上限：到这一刻为止。若今日是交易日且尚未到 09:30
    （例如清晨 08:00），下一开盘就是今日 09:30；否则顺延到下一交易日。
    """
    sh = _shanghai_now(now)
    today = sh.date()
    if calendar.is_trading_day(today) and sh.time() < OPEN:
        open_day = today
    else:
        open_day = calendar.next_trading_day(today).date()
    return datetime.combine(open_day, OPEN, tzinfo=SHANGHAI).astimezone(UTC)


def is_cache_fresh(
    calendar: TradingCalendar,
    fetched_at: datetime,
    *,
    now: datetime | None = None,
    open_ttl: float,
) -> bool:
    """A 股标的的时段感知新鲜度判定。

    * 开盘中：``now - fetched_at < open_ttl``（沿用原短 TTL，盘中持续刷新）。
    * 收盘后：条目取于最近收盘之后、且尚未到下一开盘即为新鲜——把当日最终
      数据缓存到次日开盘前。

    ``open_ttl`` 由调用方传入（默认 quote TTL），保持错误条目短 TTL 的逻辑
    在调用方处理（错误条目不进这里）。
    """
    now = now or datetime.now(UTC)
    if is_open(calendar, now=now):
        return (now - fetched_at).total_seconds() < open_ttl
    return fetched_at >= last_close(calendar, now=now) and now < next_open(calendar, now=now)


__all__ = ["is_open", "last_close", "next_open", "is_cache_fresh"]
