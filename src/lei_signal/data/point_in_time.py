"""Point-in-time 行情快照：按 available_date 裁剪，用于无未来函数测试与信号回放。

移植来源
--------
旧路径 : /Users/yongbiaoli/Desktop/licai
          src/trading_v11/engine/point_in_time_view.py
旧commit: a25eae9266f066e3a94ccf058add089e4c130366
改造原因:
  1. 旧实现裁剪 PriceHistory / NavHistory 并依赖 FundID、ProxyID、FrozenEntry
     等执行域类型；新项目只需要按日期裁剪 pandas 时间序列。
  2. 新增周线聚合边界：周线只能由「已经结束」的周产生，防止把周五数据
     泄漏给周一至周四（旧实现没有这个概念）。
  3. 不移植 StrategyEngine 及其决策入口。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, TradingCalendar


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """截止 as_of（含）的行情视图。

    任何规则只能读取本快照，因此「追加未来数据不改变旧日期结论」由构造方式保证。
    """

    symbol: str
    as_of: pd.Timestamp
    daily: pd.DataFrame
    weekly: pd.DataFrame

    @property
    def last_date(self) -> pd.Timestamp:
        return self.daily.index[-1]


def crop_daily(bars: pd.DataFrame, as_of: date | pd.Timestamp) -> pd.DataFrame:
    """裁剪到 as_of（含）为止的日线。"""
    cutoff = pd.Timestamp(as_of).normalize()
    return bars.loc[bars.index <= cutoff]


#: 周线输出的列顺序。空结果与非空结果必须完全一致，
#: 否则下游 concat / 列位置访问会在「本周尚未结束」时静默错位。
WEEKLY_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "bar_count",
    "is_complete",
    "week_start",
    "week_end",
)

_WEEKLY_DTYPES: dict[str, str] = {
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "volume": "float64",
    "bar_count": "int64",
    "is_complete": "bool",
    "week_start": "datetime64[ns]",
    "week_end": "datetime64[ns]",
}


def empty_weekly() -> pd.DataFrame:
    """没有任何「已结束周」时的空周线，列与索引契约与正常结果一致。"""
    frame = pd.DataFrame(
        {name: pd.Series(dtype=_WEEKLY_DTYPES[name]) for name in WEEKLY_COLUMNS}
    )
    frame.index = pd.DatetimeIndex([], name="date")
    return frame


def aggregate_weekly(
    daily: pd.DataFrame,
    *,
    as_of: date | pd.Timestamp | None = None,
    calendar: TradingCalendar | None = None,
) -> pd.DataFrame:
    """把日线聚合为周线（Round 2 修复 1：周线完成语义 —— 收盘后运行）。

    严格语义（必须满足）：
      * **收盘后运行语义**：当 as_of 到达「当周最后一个交易日」（含）时，该周
        周线即视为完成可用——当日收盘的 OHLC 已经完整，无需等待下一交易日。
      * 「当周最后一个交易日」由**交易所日历**判定（``calendar``），**不是**
        「已观测到的最后一根日线」。后者会在周三就把当周误判为完成（周三是
        截断数据里的最后一根），属于提前完成，必须避免。
      * 兜底：日历在本周内判不出任何交易日（例如整周休市）时，退回旧规则
        ——「本周之后已经出现下一根日线」即视为本周结束，``available_date``
        取那根日线。保证任何情况下都能收敛。
      * ``available_date`` = 最早可知日 = ``max(日历判定的当周最后交易日,
        本周内已观测到的最后一根日线)``。取 max 是为了防止「日历说周五是交易日
        但当天停牌无 K 线」时把可知日回溯到周四——那天我们并不知道本周已结束。
      * 旧实现要求「下一交易日已经出现」才完成，会把周线系统性延迟一个交易日，
        导致正常周五收盘、节假日短周最后交易日收盘时周线仍不可用——口径错误，已修正。
      * 追加未来数据不得改变历史 as_of 时的结论（由裁剪 + 日历纯函数性保证）。
      * 不足 60/120 根周线时 long_trend 保持 `unknown`，禁止任何伪指标兜底。

    参数
    ----
    calendar:
        交易所日历。默认 :data:`DEFAULT_TRADING_CALENDAR`（周一至周五、无节假日），
        保守且永不提前完成；传入含真实休市日的日历后，节假日短周也能在其最后一个
        交易日收盘时立即完成。

    返回 DataFrame 索引为 `available_date`，并附 `is_complete` 标识；
    `is_complete=False` 的行已被过滤掉（未完成周不进入周线）。
    """
    if daily.empty:
        return empty_weekly()

    frame = daily if as_of is None else crop_daily(daily, as_of)
    if frame.empty:
        return empty_weekly()

    trading_calendar = calendar if calendar is not None else DEFAULT_TRADING_CALENDAR

    # 按自然周（W-SUN: 周一..周日）分组
    week_key = frame.index.to_period("W-SUN")
    grouped = frame.groupby(week_key)

    cutoff = (
        pd.Timestamp(as_of).normalize()
        if as_of is not None
        else frame.index[-1]
    )

    completed_records: list[dict[str, object]] = []
    for period, group in grouped:
        week_start = period.start_time.tz_localize(None)
        week_end = period.end_time.tz_localize(None)
        last_observed = group.index[-1]

        # 1) 日历判定：本周最后一个交易日是否已经收盘？
        calendar_last = trading_calendar.last_trading_day_in_range(
            week_start, week_end.normalize()
        )
        if calendar_last is not None and cutoff >= calendar_last:
            available_date = max(calendar_last, last_observed)
        else:
            # 2) 兜底：本周之后已经出现下一根日线 => 本周必然已结束。
            later = frame.index[frame.index > week_end]
            if len(later) == 0:
                continue
            available_date = later[0]

        completed_records.append(
            {
                "open": float(group["open"].iloc[0]),
                "high": float(group["high"].max()),
                "low": float(group["low"].min()),
                "close": float(group["close"].iloc[-1]),
                "volume": float(group["volume"].sum()),
                "bar_count": int(len(group)),
                "available_date": available_date,
                "is_complete": True,
                "week_start": week_start,
                "week_end": week_end,
            }
        )

    if not completed_records:
        return empty_weekly()

    completed = pd.DataFrame(completed_records).set_index("available_date")
    completed.index.name = "date"
    return completed[list(WEEKLY_COLUMNS)]


def build_snapshot(
    symbol: str,
    bars: pd.DataFrame,
    as_of: date | pd.Timestamp | None = None,
    *,
    calendar: TradingCalendar | None = None,
) -> MarketSnapshot:
    """构造截止 as_of 的快照。as_of 为空表示使用全部数据。"""
    if bars.empty:
        raise ValueError(f"{symbol} 没有行情，无法构造快照")
    daily = bars if as_of is None else crop_daily(bars, as_of)
    if daily.empty:
        raise ValueError(f"{symbol} 在 {as_of} 之前没有行情")
    resolved = daily.index[-1]
    return MarketSnapshot(
        symbol=symbol,
        as_of=resolved,
        daily=daily,
        weekly=aggregate_weekly(daily, calendar=calendar),
    )


__all__ = [
    "DEFAULT_TRADING_CALENDAR",
    "WEEKLY_COLUMNS",
    "MarketSnapshot",
    "TradingCalendar",
    "aggregate_weekly",
    "build_snapshot",
    "crop_daily",
    "empty_weekly",
]
