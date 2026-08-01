"""无未来函数门禁（架构第 13 节 1/2/10）。

1. 追加未来行情后，旧日期的特征、事件与状态保持不变。
2. 摆动点只在确认日可用。
10. 周线信号不会把周五数据泄漏到周一至周四。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.data.point_in_time import aggregate_weekly, build_snapshot, crop_daily
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots, pivots_available_on
from lei_signal.rules.lei_color import classify_colors


def _series(rows: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.4, rows))
    high = close + rng.uniform(0.2, 1.5, rows)
    low = close - rng.uniform(0.2, 1.5, rows)
    return pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.3, rows),
            "high": np.maximum.reduce([high, close]),
            "low": np.minimum.reduce([low, close]),
            "close": close,
            "volume": rng.integers(500_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=rows),
    )


# ---------------- 门禁 1：追加未来数据不改变旧结论 ----------------


def test_appending_future_bars_does_not_change_past_features_or_colors() -> None:
    bars = _series(400)
    full = classify_colors(compute_features(bars))

    for cut in (150, 200, 250, 300, 350):
        truncated = classify_colors(compute_features(bars.iloc[:cut]))
        common = truncated.index

        # 颜色必须完全一致，不允许容差。
        assert truncated["signal_color"].tolist() == full.loc[common, "signal_color"].tolist(), (
            f"截断到 {cut} 根后颜色发生变化"
        )
        # 指标数值只允许极小浮点容差。
        for column in ("ema20", "ema60", "ema120", "sma20", "close_lag20", "atr14"):
            pd.testing.assert_series_equal(
                truncated[column],
                full.loc[common, column],
                rtol=1e-12,
                check_names=False,
            )


def test_ten_historical_cutoffs_reproduce_identical_colors() -> None:
    """计划 Task 7 Step 3：10 个不同历史截断日逐一核对。"""
    bars = _series(500, seed=11)
    full = classify_colors(compute_features(bars))
    cutoffs = np.linspace(130, 499, 10).astype(int)
    for cut in cutoffs:
        as_of = bars.index[cut]
        truncated = classify_colors(compute_features(crop_daily(bars, as_of)))
        assert truncated["signal_color"].tolist() == (
            full.loc[:as_of, "signal_color"].tolist()
        ), f"截断日 {as_of.date()} 颜色不一致"


# ---------------- 门禁 2：摆动点只在确认日可用 ----------------


def test_pivot_is_not_visible_until_right_side_bars_complete() -> None:
    """移植向量来源：licai@a25eae9 tests/unit/indicators/test_pivots.py

    原测试使用 window=5（五左五右）；LEI 默认三左三右，因此这里用 left=right=3，
    中心峰值在 index=5，确认索引为 8。
    """
    highs = [1, 2, 3, 4, 5, 10, 5, 4, 3, 2, 1]
    lows = [value - 2 for value in highs]
    frame = pd.DataFrame(
        {
            "open": [float(h) for h in highs],
            "high": [float(h) for h in highs],
            "low": [float(low) for low in lows],
            "close": [float(h) for h in highs],
            "volume": [1000.0] * len(highs),
        },
        index=pd.bdate_range("2024-01-01", periods=len(highs)),
    )

    # 右侧第三根尚未完成 -> 不可用
    assert confirmed_pivots(frame, left=3, right=3, confirmed_through=7) == ()

    pivots = confirmed_pivots(frame, left=3, right=3, confirmed_through=8)
    highs_found = [p for p in pivots if p.kind == "high"]
    assert len(highs_found) == 1
    pivot = highs_found[0]
    assert pivot.index == 5
    assert pivot.confirmed_index == 8
    assert pivot.pivot_date == frame.index[5].date()
    assert pivot.available_date == frame.index[8].date()
    # 拐点日严格早于确认日：研究必须使用确认日
    assert pivot.pivot_date < pivot.available_date


def test_pivots_require_strict_extremes() -> None:
    """并列最高不构成摆动点，避免把平台整理误判为拐点。"""
    highs = [1, 2, 3, 4, 5, 10, 10, 4, 3, 2, 1]
    lows = [9, 8, 7, 6, 5, 0, 0, 6, 7, 8, 9]
    frame = pd.DataFrame(
        {
            "open": [float(h) for h in highs],
            "high": [float(h) for h in highs],
            "low": [float(low) for low in lows],
            "close": [float(h) for h in highs],
            "volume": [1000.0] * len(highs),
        },
        index=pd.bdate_range("2024-01-01", periods=len(highs)),
    )
    assert confirmed_pivots(frame, left=3, right=3) == ()


def test_pivot_set_is_stable_when_future_bars_are_appended() -> None:
    """已确认的摆动点不因后续数据而改变。"""
    bars = _series(300, seed=13)
    early_cut = 200
    early = confirmed_pivots(bars.iloc[:early_cut], left=3, right=3)
    full = confirmed_pivots(bars, left=3, right=3)
    as_of = bars.index[early_cut - 1]
    full_visible = pivots_available_on(full, as_of)
    assert [(p.kind, p.pivot_date, p.available_date) for p in early] == [
        (p.kind, p.pivot_date, p.available_date) for p in full_visible
    ]


# ---------------- 门禁 10：周线无未来泄漏 ----------------


def test_weekly_excludes_the_in_progress_week() -> None:
    """周线只能在本周最后一个已完成交易日之后生效。"""
    # 2024-01-01 是周一，构造整整三周（含最后一周部分交易日）
    index = pd.bdate_range("2024-01-01", periods=13)  # 周一..第三周周三
    frame = pd.DataFrame(
        {
            "open": np.arange(1.0, 14.0),
            "high": np.arange(1.0, 14.0) + 1,
            "low": np.arange(1.0, 14.0) - 1,
            "close": np.arange(1.0, 14.0),
            "volume": [1000.0] * 13,
        },
        index=index,
    )
    weekly = aggregate_weekly(frame)
    # 最后一周仍在进行中，必须被排除
    assert len(weekly) == 2
    assert weekly.index[-1] == pd.Timestamp("2024-01-12")  # 第二周周五
    assert weekly["bar_count"].tolist() == [5, 5]


def test_weekly_does_not_leak_friday_data_into_monday_through_thursday() -> None:
    """逐日推进：周一至周四看到的最新周线必须仍是上一周。"""
    index = pd.bdate_range("2024-01-01", periods=15)
    close = np.arange(1.0, 16.0)
    frame = pd.DataFrame(
        {
            "open": close, "high": close + 1, "low": close - 1,
            "close": close, "volume": [1000.0] * 15,
        },
        index=index,
    )
    # 第三周：周一=1/15, 周二=1/16, 周三=1/17, 周四=1/18, 周五=1/19
    third_week = pd.bdate_range("2024-01-15", periods=5)
    friday_close = 100.0  # 只在周五出现的极端值

    for day_offset in range(4):  # 周一至周四
        as_of = third_week[day_offset]
        partial = frame.loc[frame.index <= as_of].copy()
        weekly = aggregate_weekly(partial)
        assert len(weekly) == 2, f"{as_of.date()} 不应看到进行中的第三周"
        assert weekly.index[-1] == pd.Timestamp("2024-01-12")
        # 周五的值不可能出现在周一至周四的周线中
        assert friday_close not in weekly["close"].tolist()

    # 周五收盘后，第三周才可用
    full = frame.loc[frame.index <= third_week[4]].copy()
    full.loc[third_week[4], "close"] = friday_close
    # 再追加下一周的一根，使第三周成为「已结束」
    next_monday = pd.Timestamp("2024-01-22")
    full.loc[next_monday] = {"open": 20.0, "high": 21.0, "low": 19.0,
                             "close": 20.0, "volume": 1000.0}
    weekly_after = aggregate_weekly(full)
    assert pd.Timestamp("2024-01-19") in weekly_after.index
    assert weekly_after.loc[pd.Timestamp("2024-01-19"), "close"] == friday_close


def test_snapshot_crops_daily_and_weekly_consistently() -> None:
    bars = _series(200, seed=17)
    as_of = bars.index[120]
    snapshot = build_snapshot("TEST", bars, as_of=as_of)
    assert snapshot.daily.index[-1] == as_of
    assert (snapshot.weekly.index <= as_of).all()
    # 快照必须与直接截断一致
    direct = build_snapshot("TEST", bars.iloc[:121])
    pd.testing.assert_frame_equal(snapshot.daily, direct.daily)
    pd.testing.assert_frame_equal(snapshot.weekly, direct.weekly)


def test_snapshot_rejects_dates_before_first_bar() -> None:
    bars = _series(50)
    with pytest.raises(ValueError, match="之前没有行情"):
        build_snapshot("TEST", bars, as_of=pd.Timestamp("2020-01-01"))
