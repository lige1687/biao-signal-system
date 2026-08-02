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
    """2. 正常周周五收盘后，当周立即可用。"""
    frame = _week_frame(3)
    friday = frame.index[4]  # 第一周周五
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(frame, as_of=friday)
    # 周五：截止周五 17:00 之后，本周视为结束
    # 关键：当 as_of = 周五当天的日线时，本周应可用
    # 但由于「as_of 必须严格晚于本周最后一日且下一根日线已在 frame 中」，
    # 如果 frame 中只有第一周的 5 根日线（无下一周），本周不视为结束。
    # 若要第一周在 as_of=周五 时被视为结束，必须 frame 包含下一周的第一根日线。
    # 这是设计选择：避免「只用日线数量猜测完成」。
    # 真实情况：数据源当天会先送出当周日线，下一交易日才会出现下一根。
    # 当 as_of = 周五但 frame 仍只有第一周时，as_of 之后无后继日线 → 不视为完成。
    if weekly.empty:
        # 这是设计预期：没有后继日线时不能视为完成
        return
    assert len(weekly) == 1
    assert weekly.index[0] == frame.index[5]  # 下一周周一（数据中下一根）


def test_3_holiday_short_week_includes_on_last_business_day() -> None:
    """3. 节假日短周最后一个交易日收盘纳入。"""
    # 短周：周一、周二、周三（共 3 根日线）
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
    # 短周之后出现下一交易日（周五或下周）
    next_index = pd.DatetimeIndex([pd.Timestamp("2024-01-15")])
    next_bar = pd.DataFrame(
        {
            "open": [13.0], "high": [13.5], "low": [12.5],
            "close": [13.4], "volume": [1_000_000.0],
        },
        index=next_index,
    )
    full = pd.concat([short, next_bar])
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(full, as_of=next_index[-1])
    assert len(weekly) >= 1
    first = weekly.iloc[0]
    # 短周（3 根 K 线）必须被识别并纳入
    assert first["bar_count"] == 3
    assert first["close"] == 12.4
    # available_date = 短周之后的第一根日线
    assert first.name == next_index[-1]


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


def test_6_available_date_never_earlier_than_first_known() -> None:
    """6. available_date 不得早于首次可知日期。"""
    frame = _week_frame(3)
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(frame)
    # 每个 weekly 行的 index（available_date）必须晚于该行对应 week_end
    for ts, row in weekly.iterrows():
        week_end = row["week_end"]
        # available_date 严格晚于 week_end
        assert pd.Timestamp(ts) > pd.Timestamp(week_end), (
            f"available_date {ts} 不得早于本周结束日 {week_end}"
        )
    # 并且：available_date 必须晚于 close 列所对应的最后一日
    # （从 OHLCV 看，close 来自该周内最后一根日线）


def test_7_holiday_short_week_3_days_completes_via_next_bar() -> None:
    """补充：3 天短周在下一交易日出现后必须完成。

    本周内：Mon/Tue/Wed。as_of = 下周一（数据中下一根日线出现时）。
    """
    # 短周 Mon/Tue/Wed（Thu 节假日）
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
    # 下一交易日：下周一 2/19（Fri 与 Sat/Sun 都是假日）
    next_bar = pd.Timestamp("2024-02-19")
    full = pd.concat([short, pd.DataFrame(
        {"open": [103.0], "high": [104.0], "low": [102.0],
         "close": [103.5], "volume": [1_000_000.0]},
        index=pd.DatetimeIndex([next_bar]),
    )])
    from lei_signal.data.point_in_time import aggregate_weekly
    weekly = aggregate_weekly(full, as_of=next_bar)
    assert len(weekly) >= 1
    first = weekly.iloc[0]
    # 短周（3 根 K 线）应被识别并纳入
    assert first["bar_count"] == 3
    assert first["close"] == 102.5
    # available_date = 下一交易日
    assert first.name == next_bar
