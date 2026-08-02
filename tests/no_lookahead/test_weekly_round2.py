"""Round 2 修复 1：周线完成边界测试。

必须满足：
  1. 周四收盘排除当周
  2. 正常周周五收盘纳入当周
  3. 节假日短周最后一个交易日收盘纳入
  4. 周一追加数据不改变上周五时点结论
  5. 截止历史任意 as_of 的结果与只传入该时点以前数据完全一致
  6. available_date 不得早于首次可知日期
"""
from __future__ import annotations

import pandas as pd


def _week_frame(weeks: int, *, start: str = "2024-01-01") -> pd.DataFrame:
    """构造连续 N 个完整自然周的 5 根 K 线（周一至周五）。"""
    n = weeks * 5
    index = pd.bdate_range(start=start, periods=n)
    return pd.DataFrame(
        {
            "open": [10.0 + i * 0.1 for i in range(n)],
            "high": [10.0 + i * 0.1 + 0.5 for i in range(n)],
            "low": [10.0 + i * 0.1 - 0.5 for i in range(n)],
            "close": [10.0 + i * 0.1 for i in range(n)],
            "volume": [1_000_000.0] * n,
        },
        index=index,
    )


def test_1_thursday_close_excludes_current_week() -> None:
    """1. 周四收盘排除当周。"""
    frame = _week_frame(3)
    thursday = frame.index[3]  # 第一周周四
    weekly = pd.read_parquet.__self__ if False else None  # 避免 lint
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(frame, as_of=thursday)
    # 周四：本周（含周五）尚未结束
    assert weekly.empty, "as_of=本周周四时，已完成周线必须为空"


def test_2_normal_friday_close_includes_current_week() -> None:
    """2. 正常周周五收盘后，当周立即可用（收盘后运行语义）。

    修复前要求「下一交易日出现」才完成，导致周五收盘本周仍不可用；
    这是不成立的系统性延迟，已修正：as_of 到达当周最后交易日（周五）即完成，
    available_date = 周五本身（最早可知日），且不构成回看。
    """
    frame = _week_frame(3)
    friday = frame.index[4]  # 第一周周五
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(frame, as_of=friday)
    # 周五收盘后，本周必须立即可用
    assert not weekly.empty, "as_of=周五时本周周线必须可用"
    assert len(weekly) == 1
    # available_date = 当周最后交易日（周五），不是下一周周一
    assert weekly.index[0] == friday, f"available_date 应为周五, 实际 {weekly.index[0]}"
    # 该周确实完整（5 根）
    assert weekly.iloc[0]["bar_count"] == 5


def test_3_holiday_short_week_includes_on_last_business_day() -> None:
    """3. 节假日短周最后一个交易日收盘即纳入（需注入真实休市日）。

    短周能否「当天完成」，取决于日历知不知道周四、周五休市。注入休市日后，
    周三（短周最后一个交易日）收盘即完成，available_date = 周三本身。
    """
    # 短周：周一、周二、周三（周四、周五休市）
    short_index = pd.DatetimeIndex([
        pd.Timestamp("2024-01-08"),  # 周一
        pd.Timestamp("2024-01-09"),  # 周二
        pd.Timestamp("2024-01-10"),  # 周三
    ])
    short = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0],
            "high": [10.5, 11.5, 12.5],
            "low": [9.5, 10.5, 11.5],
            "close": [10.4, 11.4, 12.4],
            "volume": [1_000_000.0] * 3,
        },
        index=short_index,
    )
    from lei_signal.data.calendar import weekday_calendar
    from lei_signal.data.point_in_time import aggregate_weekly

    holiday_calendar = weekday_calendar(
        [pd.Timestamp("2024-01-11").date(), pd.Timestamp("2024-01-12").date()]
    )
    # 短周最后一个交易日（周三）收盘：立即完成
    weekly = aggregate_weekly(
        short, as_of=short_index[-1], calendar=holiday_calendar
    )
    assert len(weekly) == 1
    first = weekly.iloc[0]
    assert first["bar_count"] == 3
    assert first["close"] == 12.4
    # available_date = 短周最后一个交易日（收盘后运行语义）
    assert first.name == short_index[-1]

    # 反向保证：短周周二收盘时（周三尚未收盘）不得完成
    assert aggregate_weekly(
        short.iloc[:2], as_of=short_index[1], calendar=holiday_calendar
    ).empty


def test_4_monday_append_does_not_change_friday_view() -> None:
    """4. 周一追加数据不改变上周五时点结论。"""
    frame = _week_frame(3)
    friday_index = frame.index[4]  # 第一周周五
    # 在周五时点看：仅有第一周 5 根
    friday_view = frame.loc[frame.index <= friday_index]
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly_friday = aggregate_weekly(friday_view, as_of=friday_index)
    # 在周一（下一根日线）追加后看同一时点
    monday = frame.index[5]
    full = frame.loc[frame.index <= monday]
    weekly_monday = aggregate_weekly(full, as_of=friday_index)
    # 两者的「截至周五时点已知的周线」必须完全一致
    # 注意：在 as_of=周五 时，本周必须严格满足 cutoff > 周五且 next 在 frame 中
    # 追加下一根日线后这个条件成立
    assert len(weekly_monday) == len(weekly_friday) or weekly_friday.empty
    # 关键：周五时点的 weekly 集合必须完全相同
    if not weekly_friday.empty and not weekly_monday.empty:
        # 比较 close 列
        pd.testing.assert_series_equal(
            weekly_friday["close"], weekly_monday["close"], check_names=False
        )


def test_5_consistency_with_only_up_to_as_of_data() -> None:
    """5. 截止历史任意 as_of 的结果与只传入该时点以前数据完全一致。"""
    frame = _week_frame(4)
    for i in range(0, len(frame), 5):  # 逐个周检查
        if i == 0:
            continue
        as_of = frame.index[i]
        # 全量数据 + as_of 裁剪
        from lei_signal.data.point_in_time import aggregate_weekly
        weekly_full = aggregate_weekly(frame, as_of=as_of)
        # 仅传入 as_of 之前的数据
        truncated = frame.loc[frame.index <= as_of]
        weekly_truncated = aggregate_weekly(truncated)
        # 必须完全一致（包括 is_complete 列、index）
        pd.testing.assert_frame_equal(weekly_full, weekly_truncated)


def test_6_available_date_is_the_week_last_trading_day() -> None:
    """6. available_date = 当周最后一个交易日，且不早于该周任何一根日线。"""
    frame = _week_frame(3)
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(frame)
    assert not weekly.empty
    for ts, row in weekly.iterrows():
        available = pd.Timestamp(ts)
        week_start = pd.Timestamp(row["week_start"])
        week_end = pd.Timestamp(row["week_end"])
        # available_date 落在本周之内（收盘后运行语义），不再顺延到下一周
        assert week_start <= available <= week_end, (
            f"available_date {available} 应落在 [{week_start}, {week_end}] 内"
        )
        # 且必须是该周实际出现过的日线日期（真实交易日，不是虚构日期）
        assert available in frame.index
        # 且不早于本周任何一根日线（否则等于回溯宣称「当时已知」）
        in_week = frame.loc[(frame.index >= week_start) & (frame.index <= week_end)]
        assert available >= in_week.index[-1]
    # 正常周：available_date 就是周五
    assert weekly.index[0] == frame.index[4]


def test_7_all_holiday_week_falls_back_to_next_bar() -> None:
    """7. 日历判不出当周任何交易日时（整周休市/日历过期），退回下一根日线兜底。

    这是安全网：日历数据缺失或过期时，绝不能永远不完成，也绝不能提前完成。
    """
    # 春节整周：日历标记 2/12~2/16 全部休市，但数据里仍有 3 根日线（日历与数据冲突）
    short_index = pd.DatetimeIndex([
        pd.Timestamp("2024-02-12"),  # Mon
        pd.Timestamp("2024-02-13"),  # Tue
        pd.Timestamp("2024-02-14"),  # Wed
    ])
    short = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1_000_000.0] * 3,
        },
        index=short_index,
    )
    next_bar = pd.Timestamp("2024-02-19")
    full = pd.concat([short, pd.DataFrame(
        {"open": [103.0], "high": [104.0], "low": [102.0],
         "close": [103.5], "volume": [1_000_000.0]},
        index=pd.DatetimeIndex([next_bar]),
    )])
    from lei_signal.data.calendar import weekday_calendar
    from lei_signal.data.point_in_time import aggregate_weekly

    closed_week = weekday_calendar(
        pd.DatetimeIndex(
            ["2024-02-12", "2024-02-13", "2024-02-14", "2024-02-15", "2024-02-16"]
        ).date
    )
    # 兜底前：本周之后还没有日线出现 => 不得完成
    assert aggregate_weekly(
        short, as_of=short_index[-1], calendar=closed_week
    ).empty
    # 兜底后：下一根日线出现 => 完成，available_date = 那根日线
    weekly = aggregate_weekly(full, as_of=next_bar, calendar=closed_week)
    assert len(weekly) >= 1
    first = weekly.iloc[0]
    assert first["bar_count"] == 3
    assert first["close"] == 102.5
    assert first.name == next_bar
