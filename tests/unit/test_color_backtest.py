"""绿灰黑固定周期与状态退出回测口径。"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.research.color_backtest import (
    COLOR_BACKTEST_HORIZONS,
    build_color_backtest,
)


def _frame() -> pd.DataFrame:
    # 价格路径：
    # 绿入场 100 -> 灰退出 110（多头 +10%）
    # 黑入场 90 -> 灰 -> 再次转黑 78，各自作为独立研究交易；两笔都在转绿 72 时平空。
    colors = ["gray", "green", "green", "gray", "black", "gray", "black", "green"]
    close = [95.0, 100.0, 108.0, 110.0, 90.0, 82.0, 78.0, 72.0]
    return pd.DataFrame(
        {
            "open": close,
            "high": [value + 2.0 for value in close],
            "low": [value - 2.0 for value in close],
            "close": close,
            "volume": [1_000.0] * len(close),
            "signal_color": colors,
        },
        index=pd.bdate_range("2026-01-05", periods=len(close)),
    )


def test_horizons_include_120_days() -> None:
    assert COLOR_BACKTEST_HORIZONS == (5, 10, 20, 60, 120)


def test_long_exits_on_first_gray_or_black() -> None:
    report = build_color_backtest(_frame())
    assert report is not None
    exit_stat = next(stat for stat in report.long.stats if stat.key == "signal_exit")
    assert report.long.total_signals == 2  # 最后一日又转绿，但尚无退出
    assert report.long.open_trades == 1
    assert exit_stat.sample_count == 1
    assert exit_stat.mean_return == pytest.approx(10.0)
    assert exit_stat.mean_holding_days == pytest.approx(2.0)


def test_short_holds_through_gray_and_exits_on_green() -> None:
    report = build_color_backtest(_frame())
    assert report is not None
    exit_stat = next(stat for stat in report.short.stats if stat.key == "signal_exit")
    assert report.short.total_signals == 2, "每次转黑均作为独立研究信号"
    assert report.short.open_trades == 0
    assert exit_stat.sample_count == 2
    first_return = 20.0
    second_return = (1.0 - 72.0 / 78.0) * 100.0
    assert exit_stat.mean_return == pytest.approx((first_return + second_return) / 2)
    assert exit_stat.median_return == pytest.approx((first_return + second_return) / 2)
    assert exit_stat.mean_holding_days == pytest.approx(2.0)
    assert exit_stat.mean_mfe is not None and exit_stat.mean_mfe > 0
    # 第一笔空单入场后从未反向浮亏，方向调整后的最差路径仍可为正，不截断到 0。
    assert exit_stat.mean_mae is not None


def test_incomplete_fixed_horizon_is_excluded() -> None:
    report = build_color_backtest(_frame())
    assert report is not None
    for side in (report.long, report.short):
        by_key = {stat.key: stat for stat in side.stats}
        assert by_key["day_120"].sample_count == 0
        assert by_key["day_120"].mean_return is None


def test_empty_or_missing_columns_returns_none() -> None:
    assert build_color_backtest(pd.DataFrame()) is None
    assert build_color_backtest(pd.DataFrame({"close": [1.0]})) is None
