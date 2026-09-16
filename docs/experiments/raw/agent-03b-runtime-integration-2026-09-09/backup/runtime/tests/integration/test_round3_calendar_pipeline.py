"""Round 3 修复 D5：生产路径接入交易日历。

被锁定的缺陷
------------
``aggregate_weekly()`` 与 ``build_snapshot()`` 都已支持 ``calendar`` 参数，
但 ``analyze()`` / ``analyze_bars()`` 不透传，生产路径永远退回无节假日的
周一至周五日历。属于「底层可测但生产不可用」。

本文件锁定四条要求（任务书第七节）：
  1. 默认日历不得提前完成未知的节假日短周；
  2. 注入 A 股休市日历后，短周最后交易日收盘即完成；
  3. ``analyze_bars(calendar=...)`` 的周线结果与直接
     ``aggregate_weekly(calendar=...)`` 完全一致；
  4. 追加未来行情不得改变过去 as_of 时点的周线状态。
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze, analyze_bars
from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, weekday_calendar
from lei_signal.data.point_in_time import aggregate_weekly


def _bars(rows: int, seed: int = 3, start: str = "2024-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.2, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.2, 1.0, rows),
            "low": close - rng.uniform(0.2, 1.0, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 4_000_000, rows).astype(float),
        },
        index=pd.bdate_range(start, periods=rows),
    )


def _fixed_provider(bars: pd.DataFrame):
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import ValidationReport

    class Fixed:
        name = "fixed"

        def fetch(self, symbol, *, min_rows=21):  # noqa: ANN001, ANN202
            info = resolve_symbol(symbol)
            return PriceData(
                symbol=info.symbol,
                display_name=info.symbol,
                bars=bars,
                report=ValidationReport(
                    rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
                    adjusted=True, provider="fixed", duplicates_removed=0, warnings=(),
                ),
                info=info,
            )

    return Fixed()


# ==========================================================================
# 要求 3：analyze_bars(calendar=...) 与 aggregate_weekly(calendar=...) 一致
# ==========================================================================


def test_analyze_bars_weekly_matches_direct_aggregate_with_same_calendar() -> None:
    """注入同一日历时，管线周线必须与直接聚合逐行完全一致。

    这条断言是 D5 的核心：如果 ``analyze_bars`` 忽略了 ``calendar`` 参数，
    两边的周线索引（available_date）会不同，测试立即红。
    """
    bars = _bars(200, seed=11)
    # 2024 年 A 股部分休市日（春节、清明、劳动节等），仅取样例中覆盖到的
    holidays = frozenset({
        date(2024, 2, 12), date(2024, 2, 13), date(2024, 2, 14),
        date(2024, 2, 15), date(2024, 2, 16),
        date(2024, 4, 4), date(2024, 4, 5),
        date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3),
    })
    calendar = weekday_calendar(holidays)

    direct = aggregate_weekly(bars, calendar=calendar)
    piped = analyze_bars("SYN", bars, calendar=calendar).weekly_trend

    # 周线 available_date 索引必须一致
    assert list(piped.index) == list(direct.index), (
        "analyze_bars 必须把 calendar 透传给 aggregate_weekly；"
        "索引不一致说明参数被忽略"
    )
    # OHLC 逐列一致
    for column in ("open", "high", "low", "close", "volume", "bar_count"):
        assert list(piped[column]) == list(direct[column]), f"{column} 列不一致"


def test_analyze_bars_default_calendar_matches_default_aggregate() -> None:
    """不传 calendar 时两边都应退回 DEFAULT_TRADING_CALENDAR，结果同样一致。"""
    bars = _bars(150, seed=13)
    direct = aggregate_weekly(bars, calendar=DEFAULT_TRADING_CALENDAR)
    piped = analyze_bars("SYN", bars).weekly_trend
    assert list(piped.index) == list(direct.index)


# ==========================================================================
# 要求 1 + 2：默认日历保守；注入休市日历后短周立即完成
# ==========================================================================


def test_default_calendar_does_not_complete_unknown_holiday_short_week() -> None:
    """默认日历不知道节假日 → 短周最后交易日收盘时**不得**判为完成。

    构造：2024-05-01~03 为 A 股休市，当周只有 4/29(一)、4/30(二) 两个交易日。
    默认日历认为「本周最后交易日是 5/3(五)」，而数据里 4/30 就结束了，
    因此 cutoff(4/30) < calendar_last(5/3) → 该周不完成（保守）。
    """
    # 只到 4/30 为止：当周（4/29~5/5）只有两根 K 线
    index = pd.DatetimeIndex([
        pd.Timestamp("2024-04-22"), pd.Timestamp("2024-04-23"),
        pd.Timestamp("2024-04-24"), pd.Timestamp("2024-04-25"),
        pd.Timestamp("2024-04-26"),
        pd.Timestamp("2024-04-29"), pd.Timestamp("2024-04-30"),
    ])
    frame = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [101.0] * len(index),
            "low": [99.0] * len(index),
            "close": [100.5] * len(index),
            "volume": [1_000_000.0] * len(index),
        },
        index=index,
    )
    weekly = aggregate_weekly(frame, calendar=DEFAULT_TRADING_CALENDAR)
    week_starts = [pd.Timestamp(value).date() for value in weekly["week_start"]]
    assert date(2024, 4, 29) not in week_starts, (
        "默认日历不知道 5/1-5/3 休市，不得把 4/29 那一周判为已完成"
    )
    # 前一整周（4/22~4/26）应当已完成
    assert date(2024, 4, 22) in week_starts


def test_injected_holiday_calendar_completes_short_week_at_last_trading_day() -> None:
    """注入 A 股休市日历后，4/30 收盘即可完成该短周。"""
    index = pd.DatetimeIndex([
        pd.Timestamp("2024-04-22"), pd.Timestamp("2024-04-23"),
        pd.Timestamp("2024-04-24"), pd.Timestamp("2024-04-25"),
        pd.Timestamp("2024-04-26"),
        pd.Timestamp("2024-04-29"), pd.Timestamp("2024-04-30"),
    ])
    frame = pd.DataFrame(
        {
            "open": [100.0] * len(index),
            "high": [101.0] * len(index),
            "low": [99.0] * len(index),
            "close": [100.5] * len(index),
            "volume": [1_000_000.0] * len(index),
        },
        index=index,
    )
    calendar = weekday_calendar({
        date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3),
    })
    weekly = aggregate_weekly(frame, calendar=calendar)
    week_starts = [pd.Timestamp(value).date() for value in weekly["week_start"]]
    assert date(2024, 4, 29) in week_starts, (
        "注入休市日历后，短周最后交易日 4/30 收盘即应完成"
    )
    # 该周的 available_date 必须正好是 4/30（最后一个交易日），不得延后
    row = weekly[weekly["week_start"] == pd.Timestamp("2024-04-29")]
    assert row.index[0].date() == date(2024, 4, 30), (
        f"available_date 应为 4/30，实际 {row.index[0].date()}"
    )
    assert int(row["bar_count"].iloc[0]) == 2


# ==========================================================================
# 要求 4：追加未来行情不得改变过去 as_of 的周线状态
# ==========================================================================


def test_appending_future_bars_does_not_change_past_weekly_state() -> None:
    """同一 as_of 下的周线结论必须与是否存在未来数据无关。"""
    full = _bars(200, seed=17)
    cutoff = full.index[120]
    calendar = weekday_calendar({date(2024, 4, 4), date(2024, 4, 5)})

    # A) 只有截止 cutoff 的数据
    truncated = full.loc[full.index <= cutoff]
    weekly_a = aggregate_weekly(truncated, calendar=calendar)
    # B) 拥有全部数据但显式裁剪到同一 as_of
    weekly_b = aggregate_weekly(full, as_of=cutoff, calendar=calendar)

    assert list(weekly_a.index) == list(weekly_b.index), (
        "追加未来行情改变了过去 as_of 的周线索引（未来函数）"
    )
    for column in ("open", "high", "low", "close", "bar_count"):
        assert list(weekly_a[column]) == list(weekly_b[column]), (
            f"{column} 在两种数据范围下不一致"
        )


def test_analyze_passes_calendar_through_to_weekly(tmp_path) -> None:  # noqa: ANN001
    """``analyze()``（含 provider / 缓存 / SQLite 的完整入口）必须透传 calendar。

    与 ``analyze_bars`` 分开测：D5 的病灶正是「有的入口能注入、有的不能」。

    行情必须**真的缺少节假日那几根 K 线**，否则
    ``available_date = max(日历判定的最后交易日, 本周已观测最后一根)``
    会让注入日历与默认日历给出相同答案，测试就失去区分力。
    """
    holidays = {
        date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3),
    }
    # 构造：连续工作日，但**剔除**休市日，并让序列在 4/30 收盘结束
    all_days = pd.bdate_range("2024-01-01", "2024-04-30")
    index = pd.DatetimeIndex([d for d in all_days if d.date() not in holidays])
    rng = np.random.default_rng(19)
    close = 100 + np.cumsum(rng.normal(0.05, 1.2, len(index)))
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.2, 1.0, len(index)),
            "low": close - rng.uniform(0.2, 1.0, len(index)),
            "close": close,
            "volume": rng.integers(1_000_000, 4_000_000, len(index)).astype(float),
        },
        index=index,
    )
    calendar = weekday_calendar(holidays)

    result = analyze(
        "QQQ",
        provider=_fixed_provider(bars),
        calendar=calendar,
        cache_root=str(tmp_path / "cache"),
    )
    direct = aggregate_weekly(bars, calendar=calendar)
    assert list(result.weekly_trend.index) == list(direct.index), (
        "analyze() 必须把 calendar 透传到周线聚合"
    )

    # 区分力守卫：默认日历（不知道 5/1-5/3 休市）下，4/29 那一周不应完成，
    # 因此两种口径的周线**条数必须不同**。若相同，说明本测试无法区分是否透传。
    default_weekly = aggregate_weekly(bars, calendar=DEFAULT_TRADING_CALENDAR)
    assert len(direct) != len(default_weekly), (
        "样例必须让两种日历给出不同结果，否则本测试无区分力"
    )
    last_week_start = pd.Timestamp("2024-04-29")
    assert last_week_start in list(direct["week_start"]), (
        "注入休市日历后 4/29 短周应完成"
    )
    assert last_week_start not in list(default_weekly["week_start"]), (
        "默认日历下 4/29 短周不应完成"
    )
    # 生产入口的结果必须站在「注入日历」这一侧
    assert last_week_start in list(result.weekly_trend["week_start"]), (
        "analyze() 忽略了 calendar：4/29 短周未完成"
    )
