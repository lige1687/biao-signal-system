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

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from lei_signal.data.calendar import (
    DEFAULT_TRADING_CALENDAR,
    CalendarCoverageError,
    CoveredCalendar,
    TradingCalendar,
)


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """截止 as_of（含）的行情视图。

    任何规则只能读取本快照，因此「追加未来数据不改变旧日期结论」由构造方式保证。
    """

    symbol: str
    as_of: pd.Timestamp
    daily: pd.DataFrame
    weekly: pd.DataFrame
    observation_date: pd.Timestamp | None = None
    weekly_quality: dict[str, object] = field(default_factory=dict)

    @property
    def last_date(self) -> pd.Timestamp:
        return self.last_price_date

    @property
    def last_price_date(self) -> pd.Timestamp:
        """Date of the last included, completed daily price bar."""
        return self.daily.index[-1]

    @property
    def complete_bar(self) -> bool:
        """Whether a completed daily bar exists on the observation date.

        This is not the weekly is_complete flag; holidays may have no daily bar.
        """
        observation = self.as_of if self.observation_date is None else self.observation_date
        return observation in self.daily.index


def validate_session_date(value: date | pd.Timestamp) -> pd.Timestamp:
    """Validate the original observation label before any crop/normalization."""
    stamp = pd.Timestamp(value)
    if pd.isna(stamp) or stamp.tz is not None or stamp != stamp.normalize():
        raise ValueError("Observation requires a non-NaT, timezone-naive, normalized session date")
    return stamp


def _finite_numeric_bars(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["open", "high", "low", "close", "volume"]
    missing = set(columns) - set(frame.columns)
    if missing:
        raise IncompleteWeeklyData(f"Missing required OHLCV fields: {sorted(missing)}")
    if any(not is_numeric_dtype(frame[c].dtype) or is_bool_dtype(frame[c].dtype)
           or is_complex_dtype(frame[c].dtype) for c in columns):
        raise IncompleteWeeklyData("OHLCV must have real numeric dtypes; strings are not converted")
    values = frame[columns].to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(values).all():
        raise IncompleteWeeklyData("Nonfinite OHLCV in observed daily bars")
    checked = frame.copy()
    checked[columns] = values
    return checked


def completed_daily_view(
    bars: pd.DataFrame, *, as_of: date | pd.Timestamp | None = None,
    complete_bar: bool = True, calendar: TradingCalendar | None = None,
) -> pd.DataFrame:
    """Crop once before daily consumers; explicitly exclude unfinished observation day."""
    if not isinstance(complete_bar, bool):
        raise TypeError("complete_bar must explicitly be True or False")
    observation = validate_session_date(as_of) if as_of is not None else None
    if bars.empty:
        return bars
    if observation is None:
        observation = (
            validate_session_date(bars.index[-1]) if isinstance(calendar, CoveredCalendar)
            else pd.Timestamp(bars.index[-1]).normalize()
        )
    frame = bars.loc[bars.index <= observation] if as_of is not None else bars
    if not complete_bar:
        frame = frame.loc[frame.index < observation]
    if isinstance(calendar, CoveredCalendar) and not frame.empty:
        index = frame.index
        if (not isinstance(index, pd.DatetimeIndex) or index.tz is not None
                or not index.equals(index.normalize()) or index.hasnans
                or not index.is_unique or not index.is_monotonic_increasing):
            raise IncompleteWeeklyData("Daily index must be unique, ordered, naive session dates")
        frame = _finite_numeric_bars(frame)
    return frame


def weekly_input_quality(
    daily: pd.DataFrame, weekly: pd.DataFrame, *, as_of: date | pd.Timestamp | None = None,
    complete_bar: bool = True, calendar: TradingCalendar | None = None,
) -> dict[str, object]:
    """Expose coverage and last known week without choosing a trading policy."""
    observation = (validate_session_date(as_of) if as_of is not None else
                   None if daily.empty else pd.Timestamp(daily.index[-1]).normalize())
    current_covered = None
    if isinstance(calendar, CoveredCalendar) and observation is not None:
        period = observation.to_period("W-SUN")
        current_covered = calendar.covers(period.start_time, period.end_time.normalize())
    return {
        "observation_date": None if observation is None else observation.isoformat(),
        "last_price_date": None if daily.empty else daily.index[-1].isoformat(),
        "complete_bar": complete_bar,
        "calendar_mode": (
            "explicit_coverage" if isinstance(calendar, CoveredCalendar) else "legacy_unqualified"
        ),
        "current_week_calendar_covered": current_covered,
        "last_complete_week": None if weekly.empty else weekly.index[-1].isoformat(),
        "environment_policy": "last_known_background; no expiry or trading permission inferred",
    }


def require_weekly_qualification(quality: dict[str, object], required: bool) -> None:
    if not isinstance(required, bool):
        raise TypeError("require_qualified_weekly must explicitly be True or False")
    if required and quality["current_week_calendar_covered"] is not True:
        raise CalendarCoverageError(
            "Requested observation has no qualified full-week calendar coverage"
        )


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



class IncompleteWeeklyData(ValueError):
    """A closed, covered week has unresolved missing or invalid daily data."""


def _validate_covered_week(group: pd.DataFrame, start: pd.Timestamp,
                           end: pd.Timestamp, calendar: CoveredCalendar) -> None:
    expected = pd.DatetimeIndex([
        day for day in pd.date_range(start, end) if calendar.is_trading_day(day)
    ])
    if not expected.equals(group.index):
        raise IncompleteWeeklyData(f"Daily bars do not match declared sessions: {start.date()}")
    _finite_numeric_bars(group)

def aggregate_weekly(
    daily: pd.DataFrame,
    *,
    as_of: date | pd.Timestamp | None = None,
    calendar: TradingCalendar | None = None,
    complete_bar: bool = True,
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

    CoveredCalendar 显式声明整个自然周的覆盖范围；范围外不以后一根行情兜底。
    已结束且已覆盖的周若缺交易日、整周资料或有限 OHLCV，抛 IncompleteWeeklyData，
    不推断为休市、不补行情，也不把异常翻成环境 False。未包装的日历保留旧口径。
    complete_bar=False 表示观察日尚未收盘：排除该日行，最晚使用前一日的完成信息。

    返回 DataFrame 索引为 `available_date`，并附 `is_complete` 标识；
    `is_complete=False` 的行已被过滤掉（未完成周不进入周线）。
    """
    frame = completed_daily_view(daily, as_of=as_of, complete_bar=complete_bar, calendar=calendar)
    if frame.empty:
        return empty_weekly()
    observation = (validate_session_date(as_of) if as_of is not None else
                   pd.Timestamp(daily.index[-1]).normalize())

    trading_calendar = calendar if calendar is not None else DEFAULT_TRADING_CALENDAR
    guarded = isinstance(trading_calendar, CoveredCalendar)

    # 按自然周（W-SUN: 周一..周日）分组
    week_key = frame.index.to_period("W-SUN")
    grouped = frame.groupby(week_key)

    cutoff = observation if complete_bar else observation - pd.Timedelta(days=1)
    if guarded:
        # Include absent whole weeks: grouping observed bars alone would silently skip them.
        periods = pd.period_range(week_key.min(), cutoff.to_period("W-SUN"), freq="W-SUN")
        grouped = ((period, frame.loc[week_key == period]) for period in periods)

    completed_records: list[dict[str, object]] = []
    for period, group in grouped:
        week_start = period.start_time.tz_localize(None)
        week_end = period.end_time.tz_localize(None)
        if isinstance(trading_calendar, CoveredCalendar) and not trading_calendar.covers(
            week_start, week_end.normalize()
        ):
            # Unknown calendar tail/start is not a holiday and cannot use the later-bar fallback.
            continue

        # 1) 日历判定：本周最后一个交易日是否已经收盘？
        calendar_last = trading_calendar.last_trading_day_in_range(
            week_start, week_end.normalize()
        )
        if isinstance(trading_calendar, CoveredCalendar):
            if calendar_last is None and group.empty:
                continue  # covered, genuinely all-closed week has no price bar
            if calendar_last is None:
                raise IncompleteWeeklyData("Price bars conflict with an all-closed calendar week")
            if cutoff < calendar_last:
                continue
            _validate_covered_week(group, week_start, week_end.normalize(), trading_calendar)
        last_observed = group.index[-1]
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
    if guarded and not np.isfinite(
        completed[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    ).all():
        raise IncompleteWeeklyData("Nonfinite aggregate OHLCV")
    completed.index.name = "date"
    return completed[list(WEEKLY_COLUMNS)]


def build_snapshot(
    symbol: str,
    bars: pd.DataFrame,
    as_of: date | pd.Timestamp | None = None,
    *,
    calendar: TradingCalendar | None = None,
    complete_bar: bool = True,
    preserve_observation_date: bool = False,
    require_qualified_weekly: bool = False,
) -> MarketSnapshot:
    """Expose observation_date separately; legacy as_of remains last price by default.

    complete_bar=False excludes any bar dated as_of (observation before close).
    CoveredCalendar uses the explicit observation for qualification. Other calendars
    retain legacy weekly aggregation at the last included price date.
    preserve_observation_date=True explicitly migrates snapshot.as_of to requested date.
    require_qualified_weekly=True rejects unknown coverage instead of choosing a policy.
    """
    daily = completed_daily_view(bars, as_of=as_of, complete_bar=complete_bar, calendar=calendar)
    if not isinstance(preserve_observation_date, bool):
        raise TypeError("preserve_observation_date must explicitly be True or False")
    if daily.empty:
        raise ValueError(f"{symbol} 在 {as_of} 之前没有行情")
    resolved = validate_session_date(as_of if as_of is not None else bars.index[-1])
    weekly = aggregate_weekly(
        daily, calendar=calendar, as_of=resolved if isinstance(calendar, CoveredCalendar) else None,
        complete_bar=complete_bar if isinstance(calendar, CoveredCalendar) else True,
    )
    quality = weekly_input_quality(
        daily, weekly, as_of=resolved, calendar=calendar, complete_bar=complete_bar
    )
    require_weekly_qualification(quality, require_qualified_weekly)
    return MarketSnapshot(
        symbol=symbol,
        as_of=resolved if preserve_observation_date else daily.index[-1],
        daily=daily,
        weekly=weekly,
        observation_date=resolved,
        weekly_quality=quality,
    )


__all__ = [
    "DEFAULT_TRADING_CALENDAR",
    "WEEKLY_COLUMNS",
    "IncompleteWeeklyData",
    "MarketSnapshot",
    "TradingCalendar",
    "aggregate_weekly",
    "build_snapshot",
    "completed_daily_view",
    "crop_daily",
    "empty_weekly",
    "require_weekly_qualification",
    "validate_session_date",
    "weekly_input_quality",
]
