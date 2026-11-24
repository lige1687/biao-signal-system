"""周线环境层（规格 §6 简化版：周线定环境，日线触发退出）。

V2 §15 第一轮落地：模块 A 的 A1 环境条件之一是「周线多头环境」。本模块把
日线聚合为已完成周线（复用 ``aggregate_weekly`` 的收盘后完成语义与交易所
日历，见 ``data/point_in_time.py``），在周线上计算与日线同参数（20/60/120）
的 SMA/EMA 双组多头排列，再映射回每个交易日：

- 对交易日 d，只使用 ``available_date <= d`` 的周线（该周最后一个交易日
  收盘后该周线才可用，规格 §3.2 防未来泄漏）；
- ``bull_alignment`` = WSMA20>WSMA60>WSMA120 且 WEMA20>WEMA60>WEMA120
  （规格 §4.5 回测代理口径，镜像到周线）；
- 周线不足 120 根时对应均线为 NaN -> 排列不可判定 -> False（宁缺勿假，
  与 long_trend「禁止伪指标兜底」同一纪律）。
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lei_signal.data.calendar import CoveredCalendar
from lei_signal.data.point_in_time import (
    TradingCalendar,
    aggregate_weekly,
    completed_daily_view,
    require_weekly_qualification,
    weekly_input_quality,
)
from lei_signal.features.indicators import seeded_ema

PERIODS = (20, 60, 120)


def weekly_alignment(weekly: pd.DataFrame) -> pd.DataFrame:
    """在已完成周线上计算 20/60/120 双组排列。

    输入必须来自 ``aggregate_weekly``（已排除进行中的周），索引 = 每周最后
    一个已完成交易日 = 该周线的 available_date。
    """
    frame = weekly.copy()
    close = frame["close"].astype(float)
    for period in PERIODS:
        frame[f"wsma{period}"] = close.rolling(period, min_periods=period).mean()
        frame[f"wema{period}"] = seeded_ema(close, period)
    frame["bull_alignment"] = (
        (frame["wsma20"] > frame["wsma60"])
        & (frame["wsma60"] > frame["wsma120"])
        & (frame["wema20"] > frame["wema60"])
        & (frame["wema60"] > frame["wema120"])
    )
    frame["bear_alignment"] = (
        (frame["wsma20"] < frame["wsma60"])
        & (frame["wsma60"] < frame["wsma120"])
        & (frame["wema20"] < frame["wema60"])
        & (frame["wema60"] < frame["wema120"])
    )
    return frame


def weekly_env_series(
    daily: pd.DataFrame, *, calendar: TradingCalendar | None = None,
    as_of: date | pd.Timestamp | None = None, complete_bar: bool = True,
    require_qualified_weekly: bool = False,
) -> pd.Series:
    """每个交易日的周线多头环境（只用已完成周，无未来泄漏）。"""
    source = daily
    daily = completed_daily_view(daily, as_of=as_of, calendar=calendar, complete_bar=complete_bar)
    observation = as_of if as_of is not None else (None if source.empty else source.index[-1])
    protected_clock = isinstance(calendar, CoveredCalendar) or not complete_bar
    weekly = weekly_alignment(aggregate_weekly(
        daily, calendar=calendar,
        as_of=observation if protected_clock else None, complete_bar=complete_bar,
    ))
    quality = weekly_input_quality(daily, weekly, as_of=observation,
                                   calendar=calendar, complete_bar=complete_bar)
    require_weekly_qualification(quality, require_qualified_weekly)
    result = pd.Series(False, index=daily.index, name="weekly_bull_env")
    result.attrs["weekly_quality"] = quality
    if weekly.empty:
        return result
    week_ends = weekly.index
    bull = np.asarray(weekly["bull_alignment"], dtype=bool)
    positions = np.atleast_1d(np.searchsorted(week_ends, daily.index, side="right")) - 1
    result[:] = [bool(bull[i]) if i >= 0 else False for i in positions]
    return result


__all__ = ["PERIODS", "weekly_alignment", "weekly_env_series"]
