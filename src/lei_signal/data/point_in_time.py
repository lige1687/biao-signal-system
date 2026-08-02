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
    """把日线聚合为周线。

    语义（架构第 4.1 节 + 用户修复要求）：
      * 一周必须由其**自然周结束**之后的下一根日线确认才可使用，
        否则视为「进行中」并排除——避免周一至周四看到本周含周五的最终值。
      * 如果数据流断在周一至周四，则**不能**确定这一周是否已经结束
        （可能是节假日导致的短周，也可能是数据未到）。遇到这种情况，
        不应提前标记为「完成」也不应延后一周；唯一安全的做法是
        在该周内**排除**所有未完成周，并在数据中**明确标记**。
      * 索引使用「该周最后一个已完成交易日的日期」即
        ``available_date``；下一根日线出现之前这一行**不可用**。

    该函数在原始日线 DataFrame 之外返回一行状态列 ``is_complete``，
    供 `compute_weekly_long_trend` 与界面明确区分「已结束」与「不确定」。
    """
    if daily.empty:
        return daily.iloc[0:0].copy()

    frame = daily if as_of is None else crop_daily(daily, as_of)
    if frame.empty:
        return frame.iloc[0:0].copy()

    # 按自然周（W-SUN: 周一..周日）分组
    week_key = frame.index.to_period("W-SUN")
    grouped = frame.groupby(week_key)
    weekly = pd.DataFrame(
        {
            "open": grouped["open"].first(),
            "high": grouped["high"].max(),
            "low": grouped["low"].min(),
            "close": grouped["close"].last(),
            "volume": grouped["volume"].sum(),
            "bar_count": grouped.size(),
        }
    )

    # 计算每周 last_date 与 is_complete
    last_dates: list[pd.Timestamp] = []
    is_complete_flags: list[bool] = []
    for _, group in grouped:
        last_ts = group.index[-1]
        last_dates.append(last_ts)
        # 周是否结束：必须等到**下一根日线**出现。
        # 由于此处只看到了最后一根，无法仅凭「本周内有多少根日线」判断
        # 是否假期短周（例如 3 根日线也可能是真的短周）。
        # 因此唯一稳健的判断是：本函数外部传入的 as_of 比本周末（周日）
        # 更晚，才能确定本周结束；否则一律标 False。
        is_complete_flags.append(False)  # 后续按 as_of 重新判断

    weekly["available_date"] = last_dates
    weekly["is_complete"] = is_complete_flags

    # 按 as_of 与「本周末」关系重算 is_complete。
    # 周末 = 该周周日 23:59:59；只有当 as_of >= 周末时才认为该周已结束。
    if as_of is not None:
        cutoff = pd.Timestamp(as_of).normalize()
    else:
        cutoff = frame.index[-1]  # as_of 为 None 时，按最后一根日线为基准
    for period, group in grouped:
        week_end = period.end_time.tz_localize(None)  # 本周日结束
        # pandas Period.end_time 返回本地时区时间戳
        pd.Timestamp(week_end).normalize()
        # 严格：as_of 必须严格**晚于**本周最后一根日线所在日期
        # 才能视为下一周已经开始，进而本周已完成。
        next_day_in_frame = (frame.index > group.index[-1]).any()
        complete = (cutoff > group.index[-1]) and next_day_in_frame
        weekly.loc[period, "is_complete"] = complete

    # 仅保留已完成的周
    completed = weekly[weekly["is_complete"]].copy()
    if completed.empty:
        return completed.reset_index(drop=True).iloc[0:0]

    completed = completed.set_index("available_date")
    completed.index.name = "date"
    return completed[["open", "high", "low", "close", "volume", "bar_count", "is_complete"]]


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
