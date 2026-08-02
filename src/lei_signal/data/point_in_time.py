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
) -> pd.DataFrame:
    """把日线聚合为周线（Round 2 修复 1：周线完成语义）。

    严格语义（必须满足）：
      * as_of 之前「下一交易日已经出现」是「上一周已结束」的必要条件，
        但**不是**充分条件——必须严格避免「下一交易日」是用未来数据回填。
      * **可用周线的判定**：当且仅当 as_of 严格晚于该周最后一根日线所在日期
        **并且**数据中确实存在该日期之后的一根日线（这是「下一交易日出现」的可信信号）。
        这两条同时满足时，本周视为「已结束」。注意：必须是数据帧中存在的下一日，
        不是日历上的下一日。
      * 短周识别：节假日短周（如周一 + 周二）依然可以视为完整周；
        短周不要求 5 根 K 线——只要求「as_of 之后出现了下一根日线」。
      * 若无法识别（如数据流断在周一至周四，as_of 落在当周），
        显式标 `is_complete=False`，**绝不**用日历猜测补全。
      * `available_date` = 该周第一次真正可知的日期，即「数据中下一交易日」的日期。
      * 追加未来数据不得改变历史 `as_of` 时的结论。
      * 不得利用「下一周数据」却把当周周线事件回填到上一周五，造成隐性回看偏差。
      * 不足 60/120 根周线时 long_trend 保持 `unknown`，禁止任何伪指标兜底。

    返回 DataFrame 索引为 `available_date`，并附 `is_complete` 标识；
    `is_complete=False` 的行已被过滤掉（未完成周不进入周线）。
    """
    if daily.empty:
        return empty_weekly()

    frame = daily if as_of is None else crop_daily(daily, as_of)
    if frame.empty:
        return empty_weekly()

    # 按自然周（W-SUN: 周一..周日）分组
    week_key = frame.index.to_period("W-SUN")
    grouped = frame.groupby(week_key)

    cutoff = (
        pd.Timestamp(as_of).normalize()
        if as_of is not None
        else frame.index[-1]
    )

    # 对每个分组，判定「本周是否已结束」：
    #   - cutoff > 本周最后一日（as_of 严格晚于本周最后一日）
    #   - 后续是否出现新的日线
    completed_records: list[dict[str, object]] = []
    for period, group in grouped:
        last_ts = group.index[-1]
        if cutoff <= last_ts:
            # as_of 还在本周内部或当天：本周不结束（周一至周四、节假日短周未到末尾）
            continue
        # as_of 严格晚于本周最后一日；下一根日线是否真实出现在 frame 中？
        later = frame.index[frame.index > last_ts]
        if len(later) == 0:
            # 数据流断在最后一根；无「下一交易日」信号，本周不能视为完成
            continue
        # available_date 必须是「数据中下一交易日」，不是日历上的下一日
        next_bar = later[0]
        completed_records.append(
            {
                "open": float(group["open"].iloc[0]),
                "high": float(group["high"].max()),
                "low": float(group["low"].min()),
                "close": float(group["close"].iloc[-1]),
                "volume": float(group["volume"].sum()),
                "bar_count": int(len(group)),
                "available_date": next_bar,
                "is_complete": True,
                "week_start": period.start_time.tz_localize(None),
                "week_end": period.end_time.tz_localize(None),
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


__all__ = [
    "WEEKLY_COLUMNS",
    "MarketSnapshot",
    "aggregate_weekly",
    "build_snapshot",
    "crop_daily",
    "empty_weekly",
]
