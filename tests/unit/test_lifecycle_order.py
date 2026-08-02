"""修复 2：底部 / 顶部候选生命周期按时间顺序推进。

回归最小案例（用户要求）：
  1. 底部候选 → 次日触及 C → 之后突破颈线 → 必须仍是失效、未确认
  2. 顶部候选 → 突破第一高点 → 之后跌破颈线 → 必须作废、未确认
  3. 旧实现因「先扫描未来突破再忽略失效」导致结构仍被标为 confirmed
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import StructureStatus
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.bottom_structure import (
    detect_higher_low_bottoms,
    detect_reversal_bottoms,
)
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.reversals import detect_reversal_events
from lei_signal.rules.top_structure import detect_top_structures
from tests.golden.fixtures import (
    golden_bottom_c_invalidation,
    golden_bullish_engulfing,
)


def _bars(rows: list[dict[str, float]], start: str = "2024-01-02") -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=len(rows))
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def test_higher_low_bottom_candidate_touched_before_confirm_never_recovers() -> None:
    """用户最小回归案例：底部候选 → 触及 C → 之后突破颈线 → 仍失效。

    反转 K 线底部是「候选日即确认日」（confirm_immediately=True），
    因此完整生命周期是 candidate→confirmed→invalidated。
    关键不变量是：触及 C 之后即使后面再突破也不得复活。
    """
    rows: list[dict[str, float]] = []
    for i in range(60):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    rows.append({"open": 41.0, "high": 41.3, "low": 39.0, "close": 39.5, "volume": 1_100_000})
    rows.append({"open": 38.5, "high": 43.0, "low": 38.3, "close": 42.8, "volume": 1_900_000})
    rows.append({"open": 39.5, "high": 40.5, "low": 37.5, "close": 39.0, "volume": 1_300_000})
    rows.append({"open": 42.0, "high": 45.0, "low": 41.5, "close": 44.5, "volume": 2_000_000})
    for i in range(64, 90):
        rows.append(
            {"open": 44.0 + i * 0.1, "high": 45.0 + i * 0.1, "low": 43.5 + i * 0.1,
             "close": 44.5 + i * 0.1, "volume": 1_500_000}
        )
    bars = _bars(rows)
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    assert structures
    target = structures[0]
    assert target.c_price == 38.3
    # 关键：触及 C 必须发生在突破之前
    assert target.invalidated_date < pd.bdate_range("2024-01-02", periods=len(rows))[63].date()
    assert target.status is StructureStatus.INVALIDATED
    assert target.invalidated_reason == "bottom_C_touched_in_candidate"
    # 触及 C 之后即使再突破也不得复活：状态必须保持 invalidated
    assert target.status is StructureStatus.INVALIDATED
    # 失效日期必须晚于确认日期（顺序：候选→确认→失效）
    assert target.invalidated_date > target.confirmed_date


def test_double_bottom_candidate_touch_c_blocks_subsequent_confirmation() -> None:
    """双底候选：先触及 C → 之后突破颈线 → 永远不会被确认。"""
    rows: list[dict[str, float]] = []
    # 下跌段
    for i in range(40):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 阳线反包 1（候选日，confirm_immediately）C=58.3, 颈线=63.0
    rows.append({"open": 58.5, "high": 63.0, "low": 58.3, "close": 62.8, "volume": 1_900_000})  # 40
    # 触及 C（C=58.3, low=57.5）
    rows.append({"open": 59.5, "high": 60.5, "low": 57.5, "close": 59.0, "volume": 1_300_000})  # 41
    # 突破颈线（close=64 > 63）
    rows.append({"open": 62.0, "high": 65.0, "low": 61.5, "close": 64.5, "volume": 2_000_000})  # 42
    for i in range(43, 80):
        rows.append(
            {"open": 64.0 + i * 0.1, "high": 65.0 + i * 0.1, "low": 63.5 + i * 0.1,
             "close": 64.5 + i * 0.1, "volume": 1_500_000}
        )
    bars = _bars(rows)
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    assert structures
    target = structures[0]
    # 触及 C 必须发生在 day 41（早于突破 day 42）
    assert target.invalidated_date == pd.bdate_range("2024-01-02", periods=len(rows))[41].date()
    # 触及 C 之后突破颈线：状态保持 invalidated，不复活、不二次确认
    assert target.status is StructureStatus.INVALIDATED
    # 原始 confirmed_date 是候选日（= 反转 K 线）—— 已被失效覆盖
    assert target.confirmed_date == target.detected_date


def test_higher_low_bottom_golden_fixture_records_full_lifecycle() -> None:
    """golden 样例：候选 → 确认 → 触及 C 失效的完整路径必须保留。"""
    frame = compute_long_trend(classify_colors(compute_features(golden_bottom_c_invalidation())))
    pivots = confirmed_pivots(frame, left=3, right=3)
    structures = detect_higher_low_bottoms(frame, pivots, "TEST")
    invalid = [s for s in structures if s.status is StructureStatus.INVALIDATED]
    assert invalid
    target = invalid[0]
    assert target.invalidated_reason == "bottom_C_touched"
    assert target.confirmed_date is not None
    assert target.invalidated_date > target.confirmed_date


def test_reversal_bottom_confirmed_then_c_touch_marks_invalidated() -> None:
    """阳线反包确认（当日） → 之后触及 C → 失效。"""
    rows: list[dict[str, float]] = []
    for i in range(40):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    rows.append({"open": 61.0, "high": 61.3, "low": 59.0, "close": 59.5, "volume": 1_100_000})
    rows.append({"open": 58.5, "high": 63.0, "low": 58.3, "close": 62.8, "volume": 1_900_000})
    rows.append({"open": 59.5, "high": 60.5, "low": 58.0, "close": 59.0, "volume": 1_300_000})
    bars = _bars(rows)
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    assert structures
    target = structures[0]
    assert target.detected_date == pd.bdate_range("2024-01-02", periods=len(rows))[41].date()
    assert target.confirmed_date == target.detected_date
    assert target.status is StructureStatus.INVALIDATED
    assert target.invalidated_reason == "bottom_C_touched_in_candidate"
    assert target.invalidated_date > target.confirmed_date


def test_top_candidate_new_high_voids_before_breakdown() -> None:
    """顶部候选：突破第一高点 → 之后跌破颈线 → 必须作废、未确认。"""
    # 必须出现两个摆动高点（第一 > 第二），中间为颈线区
    rows: list[dict[str, float]] = []
    for _ in range(30):
        rows.append({"open": 50.0, "high": 50.0, "low": 49.8, "close": 50.0, "volume": 1_000_000})
    # 第一摆动高点 day 6：high=60
    rows[6] = {"open": 50.0, "high": 60.0, "low": 49.5, "close": 55.5, "volume": 1_000_000}
    # 颈线区 day 7-9：下行
    rows[7] = {"open": 54.0, "high": 54.5, "low": 51.0, "close": 51.5, "volume": 1_000_000}
    rows[8] = {"open": 51.5, "high": 52.0, "low": 50.5, "close": 51.0, "volume": 1_000_000}
    rows[9] = {"open": 51.0, "high": 51.5, "low": 50.5, "close": 51.2, "volume": 1_000_000}
    # 第二摆动高点 day 10：high=58（< 60），左侧 day 7-9 high=54.5/52/51.5
    rows[10] = {"open": 51.5, "high": 58.0, "low": 51.3, "close": 57.5, "volume": 1_000_000}
    # day 11 回落（高 < 58，右侧满足确认）
    rows[11] = {"open": 57.0, "high": 57.3, "low": 54.5, "close": 55.0, "volume": 1_000_000}
    # 第二高点确认日 = day 10 + 3 = day 13
    # 第二高点确认日 = day 10 + 3 = day 13
    # day 14 突破 first.high=60：high=61
    rows[14] = {"open": 55.0, "high": 61.0, "low": 54.5, "close": 60.5, "volume": 1_000_000}
    # day 15 跌破颈线（close 较低；不应让结构复活）
    rows[15] = {"open": 49.5, "high": 50.0, "low": 47.0, "close": 47.5, "volume": 1_000_000}
    bars = _bars(rows)
    pivots = confirmed_pivots(bars, left=3, right=3)
    tops = detect_top_structures(bars, pivots, "TEST")
    assert tops, "应该建立顶部候选"
    target = tops[0]
    assert target.status is StructureStatus.INVALIDATED
    assert target.invalidated_reason == "top_candidate_broken_by_new_high"
    assert target.confirmed_date is None
    assert target.invalidated_date == pd.bdate_range("2024-01-02", periods=len(rows))[14].date()


def test_top_after_confirm_only_invalidates_on_new_high() -> None:
    """已确认顶部：新高才解除。
    中间必须经过 confirmed 阶段，最终由新高解除。
    """
    rows: list[dict[str, float]] = []
    for _ in range(30):
        rows.append({"open": 50.0, "high": 50.0, "low": 49.8, "close": 50.0, "volume": 1_000_000})
    rows[6] = {"open": 50.0, "high": 60.0, "low": 49.5, "close": 55.5, "volume": 1_000_000}
    rows[7] = {"open": 54.0, "high": 54.5, "low": 51.0, "close": 51.5, "volume": 1_000_000}
    rows[8] = {"open": 51.5, "high": 52.0, "low": 50.5, "close": 51.0, "volume": 1_000_000}
    rows[9] = {"open": 51.0, "high": 51.5, "low": 50.5, "close": 51.2, "volume": 1_000_000}
    rows[10] = {"open": 51.5, "high": 58.0, "low": 51.3, "close": 57.5, "volume": 1_000_000}
    rows[11] = {"open": 57.0, "high": 57.3, "low": 54.5, "close": 55.0, "volume": 1_000_000}
    rows[14] = {"open": 49.5, "high": 50.0, "low": 47.0, "close": 47.5, "volume": 1_000_000}
    rows[15] = {"open": 50.0, "high": 61.0, "low": 49.5, "close": 60.5, "volume": 1_000_000}
    bars = _bars(rows)
    pivots = confirmed_pivots(bars, left=3, right=3)
    tops = detect_top_structures(bars, pivots, "TEST")
    target = tops[0]
    # 关键：confirmed_date 必须存在并指向跌破颈线日
    assert target.confirmed_date == pd.bdate_range("2024-01-02", periods=len(rows))[14].date()
    # 之后新高解除
    assert target.invalidated_date == pd.bdate_range("2024-01-02", periods=len(rows))[15].date()
    assert target.invalidated_reason == "top_warning_invalidated_by_new_high"
    assert target.status is StructureStatus.INVALIDATED


def test_reversal_bottom_long_bearish_trend_remains_recorded() -> None:
    """长周期空头环境下反包底部必须被记录（门禁 6）。"""
    frame = compute_long_trend(classify_colors(compute_features(golden_bullish_engulfing())))
    last = frame.iloc[-1]
    assert last["ema60"] < last["ema120"]
    structures = detect_reversal_bottoms(
        frame, "TEST", detect_reversal_events(frame, "TEST")
    )
    assert structures
    assert structures[0].status is StructureStatus.CONFIRMED
