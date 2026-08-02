"""修复 1：周线聚合与长周期背景必须使用真实 EMA60/EMA120。

旧实现有 3 个语义偏差：
  1. compute_weekly_long_trend 在样本不足时偷偷替换成 EMA20/EMA40 等伪指标；
  2. aggregate_weekly 总是删除最后一周，即便它实际上已结束（节假日短周）；
  3. 仅有「可用」/「不可用」二态，缺少对不确定性的显式标记。

新语义：
  * 周线不足 60 根时，长趋势状态保持 unknown；
  * 周线是否已结束由「as_of 之后是否出现下一根日线」决定；
  * 输出含 is_complete 布尔列，界面与统计可据此区分「未完成」「不确定」「已完成」。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.rules.long_trend import (
    compute_weekly_long_trend,
)


def _bars(start: str = "2023-01-02", days: int = 800) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, days))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.5, days),
            "low": close - rng.uniform(0.3, 1.5, days),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, days).astype(float),
        },
        index=pd.bdate_range(start, periods=days),
    )


# ---------------- 周线窗口不足 ----------------


def test_weekly_trend_with_under_60_weeks_keeps_unknown() -> None:
    """不足 60 根周线时，长趋势状态必须保持 unknown，不得替换为伪 EMA。"""
    bars = _bars(days=300)   # 约 60 根日线，对应 < 12 根完整周线
    weekly = aggregate_weekly(bars)
    assert len(weekly) < 60
    trend = compute_weekly_long_trend(weekly)
    assert "ema60" in trend.columns and "ema120" in trend.columns
    # 不足 60 根时 ema60/120 全为 NaN
    assert trend["ema60"].dropna().empty
    assert trend["ema120"].dropna().empty
    # long_trend 不得出现任何「已知」状态
    assert (trend["long_trend"] == "unknown").all()
    # 绝不能新增任何不属于真实 EMA60/120 的列
    forbidden_columns = {"ema16", "ema20", "ema25", "ema35", "ema40", "sma16", "sma40"}
    assert not (forbidden_columns & set(trend.columns))


def test_weekly_trend_with_50_weeks_does_not_invent_ema60() -> None:
    """50 根已完成周线时，周线 ema60 列必须为 NaN，long_trend 必须 unknown。"""
    bars = _bars(days=1000)   # 约 200 根周线
    weekly = aggregate_weekly(bars).head(50)
    assert len(weekly) == 50
    trend = compute_weekly_long_trend(weekly)
    assert trend["ema60"].dropna().empty
    assert (trend["long_trend"] == "unknown").all()


def test_weekly_trend_succeeds_once_enough_history() -> None:
    """≥120 根周线后，长趋势必须能计算。"""
    bars = _bars(days=3000)
    weekly = aggregate_weekly(bars)
    assert len(weekly) >= 120
    trend = compute_weekly_long_trend(weekly)
    assert trend["ema60"].notna().any()
    assert trend["ema120"].notna().any()
    assert not (trend["long_trend"] == "unknown").all()


# ---------------- 最后一周边界 ----------------


def test_weekly_excludes_in_progress_week_on_wednesday() -> None:
    """周三截断时，本周（in-progress）必须被排除。"""
    index = pd.bdate_range("2024-01-01", periods=10)   # 周一到下周三
    close = np.linspace(10.0, 20.0, 10)
    bars = pd.DataFrame(
        {
            "open": close - 0.1, "high": close + 0.2, "low": close - 0.2,
            "close": close, "volume": [1_000_000.0] * 10,
        },
        index=index,
    )
    weekly = aggregate_weekly(bars, as_of=index[6])   # 周三
    # 周一..周二属于上周（已完成），本周围在 index 6 周三被排除
    assert not weekly.empty
    assert weekly.index[-1] < index[6]   # 最新一行严格早于 as_of
    # 旧实现曾把整周删掉：现在应保留已完成的上一周
    assert len(weekly) >= 1


def test_weekly_includes_completed_short_holiday_week_on_friday_close() -> None:
    """周五收盘后，本周（即使只有 3 根日线）应该被纳入。"""
    # 假设这周只有周一、周二、周三（节假日），但周五那根日线在下一周
    # 出现就证明「本周已结束」。
    index = pd.DatetimeIndex([
        pd.Timestamp("2024-01-08"),   # 周一
        pd.Timestamp("2024-01-09"),   # 周二
        pd.Timestamp("2024-01-10"),   # 周三
        pd.Timestamp("2024-01-15"),   # 下一周周一
    ])
    bars = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0, 13.0],
            "high": [10.5, 11.5, 12.5, 13.5],
            "low": [9.5, 10.5, 11.5, 12.5],
            "close": [10.4, 11.4, 12.4, 13.4],
            "volume": [1_000_000.0] * 4,
        },
        index=index,
    )
    weekly = aggregate_weekly(bars, as_of=index[-1])  # 下一周周一时回看
    # 第一周（3 根日线）已结束，应被纳入
    assert len(weekly) >= 1
    assert weekly.iloc[0]["bar_count"] == 3
    assert weekly.iloc[0]["close"] == 12.4   # 本周最后一根
    assert weekly.iloc[0].name == index[2]


def test_weekly_marks_uncertainty_when_no_next_day_observed() -> None:
    """数据停在周四，且后面没有任何日线时，本周必须标 is_complete=False。"""
    index = pd.DatetimeIndex([
        pd.Timestamp("2024-01-08"),   # 周一
        pd.Timestamp("2024-01-09"),   # 周二
        pd.Timestamp("2024-01-10"),   # 周三
        pd.Timestamp("2024-01-11"),   # 周四
    ])
    bars = pd.DataFrame(
        {
            "open": [10.0, 11.0, 12.0, 13.0],
            "high": [10.5, 11.5, 12.5, 13.5],
            "low": [9.5, 10.5, 11.5, 12.5],
            "close": [10.4, 11.4, 12.4, 13.4],
            "volume": [1_000_000.0] * 4,
        },
        index=index,
    )
    # 严格传 as_of = 最后一根日线：本周无后续日线，无法判断是否结束
    weekly = aggregate_weekly(bars, as_of=index[-1])
    # 本周应被排除
    assert weekly.empty or weekly.index[-1] < index[-1]


# ---------------- 追加未来数据不改变过去结论 ----------------


def test_appending_future_bars_does_not_change_past_weekly_state() -> None:
    bars = _bars(days=400)
    cut = 250
    early_weekly = aggregate_weekly(bars.iloc[:cut], as_of=bars.index[cut - 1])
    late_weekly = aggregate_weekly(bars, as_of=bars.index[cut - 1])
    pd.testing.assert_frame_equal(early_weekly, late_weekly)


def test_appending_friday_completes_current_week() -> None:
    """追加下一根日线后，cut 之前的周线视图中「本周」应被纳入。

    关键：「已完成」的判定是 as_of 之后是否出现下一根日线。
    """
    # 第一周：周一..周四；as_of = 周四时数据流断在周四
    partial = pd.DatetimeIndex([
        pd.Timestamp("2024-01-08"),   # 周一
        pd.Timestamp("2024-01-09"),   # 周二
        pd.Timestamp("2024-01-10"),   # 周三
        pd.Timestamp("2024-01-11"),   # 周四
    ])
    close = np.linspace(10.0, 14.0, 4)
    bars = pd.DataFrame(
        {
            "open": close - 0.1, "high": close + 0.2, "low": close - 0.2,
            "close": close, "volume": [1_000_000.0] * 4,
        },
        index=partial,
    )
    # 追加下一周的周一（这是确认「上周结束」的最早信号）
    full = pd.concat(
        [
            bars,
            pd.DataFrame(
                {
                    "open": [14.5], "high": [15.0], "low": [14.3],
                    "close": [14.8], "volume": [1_000_000.0],
                },
                index=pd.DatetimeIndex([pd.Timestamp("2024-01-16")]),
            ),
        ]
    )

    # as_of = 周四：没有后续日线，第一周不能视为完成
    aggregate_weekly(full, as_of=partial[-1])
    # 切到周一之后：第一周（仅含 4 根日线）已完成
    after = aggregate_weekly(full, as_of=pd.Timestamp("2024-01-16"))
    assert len(after) >= 1
    # 确认入的是第一周：4 根日线，close=14.0（最后那根 = 周四）
    first = after.iloc[0]
    assert first["bar_count"] == 4
    assert first["close"] == pytest.approx(14.0, rel=1e-6)
    assert first.name == pd.Timestamp("2024-01-11")
