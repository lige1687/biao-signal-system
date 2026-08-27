"""缺口事件测试（src/lei_signal/rules/gap_events.py）。"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lei_signal.rules.gap_events import (
    DIRECTION_DOWN,
    DIRECTION_UP,
    GapEvent,
    detect_gaps,
    recent_unfilled_up_gap,
    unfilled_gap_target,
)


def _flat_frame(days: int = 25, high: float = 101.0, low: float = 99.0) -> pd.DataFrame:
    """平坦行情（high/low 恒定），ATR20 ≈ 2.0，gap_min_atr=0.25 阈值 ≈ 0.5。"""
    close = pd.Series([100.0] * days, index=pd.bdate_range("2024-01-01", periods=days))
    return pd.DataFrame(
        {
            "open": [100.0] * days,
            "high": [high] * days,
            "low": [low] * days,
            "close": close,
            "volume": [1e6] * days,
        },
        index=close.index,
    )


def test_up_gap_detected_with_zone() -> None:
    frame = _flat_frame()
    # 最后一根跳空：low=105 > 前 high=101，幅度 4 >= 0.25*ATR
    frame.iloc[-1, frame.columns.get_loc("high")] = 106.0
    frame.iloc[-1, frame.columns.get_loc("low")] = 105.0
    gaps = detect_gaps(frame)
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.direction == DIRECTION_UP
    assert gap.zone_low == pytest.approx(101.0)
    assert gap.zone_high == pytest.approx(105.0)
    assert gap.size_atr == pytest.approx(4.0 / 2.2)  # 缺口日 TR=6 计入 ATR20：(19x2+6)/20
    assert gap.filled_date is None


def test_small_gap_below_atr_threshold_ignored() -> None:
    frame = _flat_frame()
    # 幅度 0.3 < 0.25*ATR(≈0.5)：不构成缺口
    frame.iloc[-1, frame.columns.get_loc("high")] = 101.31
    frame.iloc[-1, frame.columns.get_loc("low")] = 101.3
    assert detect_gaps(frame) == []


def test_down_gap_detected_and_filled() -> None:
    frame = _flat_frame(days=26)
    # 倒数第 3 根向下缺口：high=95 < 前 low=99，幅度 4
    frame.iloc[-3, frame.columns.get_loc("high")] = 95.0
    frame.iloc[-3, frame.columns.get_loc("low")] = 94.0
    # 倒数第 2 根拉回区间（high=95.5 >= 区间下沿 95）-> 回补；
    # 其 low=94.5 < 前 high=95，不再构成向上缺口
    frame.iloc[-2, frame.columns.get_loc("high")] = 95.5
    frame.iloc[-2, frame.columns.get_loc("low")] = 94.5
    # 最后一根同样压在区间内，不制造新缺口
    frame.iloc[-1, frame.columns.get_loc("high")] = 96.0
    frame.iloc[-1, frame.columns.get_loc("low")] = 94.8
    gaps = detect_gaps(frame)
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.direction == DIRECTION_DOWN
    assert gap.zone_low == pytest.approx(95.0)
    assert gap.zone_high == pytest.approx(99.0)
    assert gap.filled_date == frame.index[-2].date()


def test_up_gap_filled_when_price_returns_to_zone() -> None:
    frame = _flat_frame(days=26)
    frame.iloc[-3, frame.columns.get_loc("high")] = 106.0
    frame.iloc[-3, frame.columns.get_loc("low")] = 105.0
    # 后一根 low=105 触及区间上沿（=缺口日 low）-> 回补
    frame.iloc[-2, frame.columns.get_loc("high")] = 107.0
    frame.iloc[-2, frame.columns.get_loc("low")] = 105.0
    gaps = detect_gaps(frame)
    assert gaps[0].filled_date == frame.index[-2].date()


def test_unfilled_gap_target_picks_nearest_above_entry() -> None:
    day1 = date(2024, 1, 10)
    day2 = date(2024, 2, 10)
    as_of = date(2024, 3, 1)
    gaps = [
        GapEvent("up", day1, zone_low=110.0, zone_high=115.0, size_atr=2.0, filled_date=None),
        GapEvent("up", day2, zone_low=130.0, zone_high=136.0, size_atr=2.5, filled_date=None),
        GapEvent("down", day2, zone_low=90.0, zone_high=95.0, size_atr=2.0, filled_date=None),
    ]
    target = unfilled_gap_target(gaps, as_of=as_of, entry_price=100.0)
    # 两个上方未回补缺口取价格最近者（zone_low=110），返回其上沿
    assert target == (115.0, day1)


def test_unfilled_gap_target_excludes_filled_and_future_and_below() -> None:
    as_of = date(2024, 3, 1)
    gaps = [
        # 已回补（回补日 <= as_of）
        GapEvent("up", date(2024, 1, 10), 110.0, 115.0, 2.0, filled_date=date(2024, 2, 1)),
        # 缺口日 > as_of（未来，不可用）
        GapEvent("up", date(2024, 3, 5), 120.0, 125.0, 2.0, filled_date=None),
        # 不在入场价上方
        GapEvent("up", date(2024, 1, 15), 95.0, 99.0, 2.0, filled_date=None),
    ]
    assert unfilled_gap_target(gaps, as_of=as_of, entry_price=100.0) is None


def test_unfilled_gap_target_as_of_before_fill_counts_unfilled() -> None:
    """回补发生在 as_of 之后 -> as_of 视角仍是未回补（前向无泄漏）。"""
    gaps = [
        GapEvent("up", date(2024, 1, 10), 110.0, 115.0, 2.0,
                 filled_date=date(2024, 2, 15)),
    ]
    assert unfilled_gap_target(gaps, as_of=date(2024, 2, 1), entry_price=100.0) == (
        115.0, date(2024, 1, 10),
    )


def test_recent_unfilled_up_gap_window() -> None:
    bar_dates = [date(2024, 3, d) for d in range(1, 11)]
    gaps = [
        GapEvent("up", date(2024, 3, 3), 110.0, 115.0, 2.0, filled_date=None),
        GapEvent("up", date(2024, 3, 8), 118.0, 120.0, 1.5, filled_date=None),
    ]
    # as_of=3/10、lookback=5 -> 窗口 3/6..3/10，只含 3/8 的缺口
    gap = recent_unfilled_up_gap(
        gaps, as_of=date(2024, 3, 10), lookback_bars=5, bar_dates=bar_dates
    )
    assert gap is not None and gap.gap_date == date(2024, 3, 8)
    # lookback=10 -> 窗口含 3/3，取最近者仍是 3/8
    gap = recent_unfilled_up_gap(
        gaps, as_of=date(2024, 3, 10), lookback_bars=10, bar_dates=bar_dates
    )
    assert gap is not None and gap.gap_date == date(2024, 3, 8)
    # 已回补的缺口不算
    filled = [
        GapEvent("up", date(2024, 3, 8), 118.0, 120.0, 1.5,
                 filled_date=date(2024, 3, 9)),
    ]
    assert recent_unfilled_up_gap(
        filled, as_of=date(2024, 3, 10), lookback_bars=5, bar_dates=bar_dates
    ) is None
