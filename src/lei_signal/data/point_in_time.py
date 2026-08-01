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


def aggregate_weekly(
    daily: pd.DataFrame,
    *,
    as_of: date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """把日线聚合为周线，只保留「已经结束」的周。

    无未来泄漏的关键：一周只有在其最后一个交易日已经出现在数据中之后才可用。
    实现方式是——若最后一根日线所属的周尚未跨越到下一周，则丢弃该周。
    这样周一至周四不会看到本周（含周五）的最终值。

    索引使用每周最后一个已完成交易日的日期，即该周线的 available_date。
    """
    if daily.empty:
        return daily.iloc[0:0].copy()

    frame = daily if as_of is None else crop_daily(daily, as_of)
    if frame.empty:
        return frame.iloc[0:0].copy()

    # 以自然周（周一为起点）分组
    week_key = frame.index.to_period("W-SUN")
    grouped = frame.groupby(week_key)
    weekly = pd.DataFrame(
        {
            "open": grouped["open"].first(),
            "high": grouped["high"].max(),
            "low": grouped["low"].min(),
            "close": grouped["close"].last(),
            "volume": grouped["volume"].sum(),
            "available_date": grouped.apply(lambda g: g.index[-1]),
            "bar_count": grouped.size(),
        }
    )

    # 最后一周是否已经结束：数据中最后一根日线所在周即为「进行中」的周。
    last_week = frame.index[-1].to_period("W-SUN")
    weekly = weekly[weekly.index != last_week]

    if weekly.empty:
        return weekly.reset_index(drop=True).iloc[0:0]

    weekly = weekly.set_index("available_date")
    weekly.index.name = "date"
    return weekly[["open", "high", "low", "close", "volume", "bar_count"]]


def build_snapshot(
    symbol: str,
    bars: pd.DataFrame,
    as_of: date | pd.Timestamp | None = None,
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
        weekly=aggregate_weekly(daily),
    )


__all__ = ["MarketSnapshot", "aggregate_weekly", "build_snapshot", "crop_daily"]
