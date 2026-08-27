"""strict_structure 单元测试（规格 §7.1–§7.3 / 手册 2.6）。

覆盖：包含合并、正常三根构造、极端构造（两根情形仍需第三根确认）、
确认时点（第三根收盘当根生效）、失效（新高/新低破坏）、底部镜像、
前缀不变性（防未来泄漏）。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.rules.strict_structure import (
    SIDE_BOTTOM,
    SIDE_TOP,
    detect_strict_structure_events,
    detect_strict_structures,
    merge_contained_bars,
)


def _bars(ohlc: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """ohlc = [(open, high, low, close), ...]，按交易日排列。"""
    return pd.DataFrame(
        ohlc,
        columns=["open", "high", "low", "close"],
        index=pd.bdate_range("2024-01-01", periods=len(ohlc)),
    )


def test_containment_merge() -> None:
    bars = _bars(
        [
            (10, 12, 9, 11),    # 大包含
            (10.5, 11.5, 9.5, 11),  # 被包含 -> 合并
            (11, 13, 10.8, 12.5),   # 非包含
        ]
    )
    merged = merge_contained_bars(bars)
    assert len(merged) == 2
    assert merged[0].high == 12 and merged[0].low == 9
    assert merged[0].source_bars == 2
    assert merged[0].completed_date == bars.index[1].date()


def test_simple_three_bar_top() -> None:
    # 三根互不包含：M2 向下突破 M1.low（此后必然 LH），M3 再破 M2.low 确认。
    # 注意：若 M2 完全落在 M1 区间内则被包含剔除、视为不存在（手册 2.6）。
    bars = _bars(
        [
            (9, 10, 9.0, 9.8),     # M1：高点 10、低点 9.0
            (9.4, 9.5, 8.7, 9.0),   # M2：破 M1.low（8.7 < 9.0），high 9.5 < 10
            (8.9, 9.2, 8.3, 8.5),   # M3：破 M2.low（8.3 < 8.7）-> 确认
        ]
    )
    structures = detect_strict_structures(bars)
    tops = [s for s in structures if s.side == SIDE_TOP]
    assert len(tops) == 1
    top = tops[0]
    assert top.reference_price == 10
    assert top.trigger_price == 8.7
    assert top.final_price == 8.3
    # 第三根收盘当根生效
    assert top.confirmed_date == bars.index[2].date()
    assert top.is_valid


def test_extreme_construct_needs_third_bar() -> None:
    """创新高 K 线直接杀出 LL（两根情形）：仍需第三根创新低确认（§7.3）。"""
    bars = _bars(
        [
            (10, 11, 10.2, 10.8),   # M1：创新高 11
            (10.0, 10.5, 9.8, 9.9),  # M2：LH + LL（9.8 < 10.2）两根同时完成
            (9.7, 9.9, 9.0, 9.1),    # M3：创低于 M2.low 的新低 -> 确认
        ]
    )
    structures = detect_strict_structures(bars)
    tops = [s for s in structures if s.side == SIDE_TOP]
    assert len(tops) == 1
    assert tops[0].confirmed_date == bars.index[2].date()
    assert tops[0].final_price == 9.0


def test_top_invalidated_by_new_high() -> None:
    bars = _bars(
        [
            (9, 10, 9.0, 9.8),
            (9.4, 9.5, 8.7, 9.0),   # LH（破 M1.low）
            (8.9, 9.2, 8.3, 8.5),   # 顶部确认
            (9.5, 10.5, 9.4, 10.4),  # 突破 10 -> 失效
        ]
    )
    structures = detect_strict_structures(bars)
    top = next(s for s in structures if s.side == SIDE_TOP)
    assert top.invalidated_date == bars.index[3].date()
    events = detect_strict_structure_events(bars, "TEST")
    sub_rules = [e.evidence["sub_rule"] for e in events]
    assert "top_structure_strict_confirmed" in sub_rules
    assert "top_structure_strict_invalidated" in sub_rules
    # 确认事件在失效事件之前
    confirmed = next(e for e in events if "confirmed" in e.evidence["sub_rule"])
    invalidated = next(e for e in events if "invalidated" in e.evidence["sub_rule"])
    assert confirmed.available_date <= invalidated.available_date


def test_bottom_mirror() -> None:
    bars = _bars(
        [
            (9.2, 9.8, 9.0, 9.4),    # M1：低点 9、高点 9.8
            (9.9, 10.3, 9.3, 10.2),  # M2：破 M1.high（10.3 > 9.8），low 9.3 > 9 -> HL
            (10.2, 10.8, 9.7, 10.6),  # M3：破 M2.high（10.8 > 10.3）-> 确认
            (9.9, 10.2, 8.8, 9.0),   # 跌破 9 -> 失效
        ]
    )
    structures = detect_strict_structures(bars)
    bottom = next(s for s in structures if s.side == SIDE_BOTTOM)
    assert bottom.reference_price == 9.0
    assert bottom.trigger_price == 10.3
    assert bottom.final_price == 10.8
    assert bottom.confirmed_date == bars.index[2].date()
    assert bottom.invalidated_date == bars.index[3].date()


def test_pending_top_cancelled_by_new_high_before_confirmation() -> None:
    bars = _bars(
        [
            (9, 10, 8.6, 9.8),
            (9.4, 9.5, 8.3, 9.0),    # LH 候选（破 M1.low）
            (9.8, 10.8, 9.7, 10.6),  # 未创 LL 先创新高 -> 候选作废
        ]
    )
    structures = detect_strict_structures(bars)
    assert [s for s in structures if s.side == SIDE_TOP] == []


def test_prefix_invariance() -> None:
    """截断重算不改变已确认事件（防未来泄漏）。"""
    bars = _bars(
        [
            (9, 10, 9.0, 9.8),
            (9.4, 9.5, 8.7, 9.0),
            (8.9, 9.2, 8.3, 8.5),
            (9.5, 10.5, 9.4, 10.4),
            (10.2, 10.6, 9.9, 10.1),
        ]
    )
    full = detect_strict_structure_events(bars, "TEST")
    for cut in (3, 4):
        prefix = detect_strict_structure_events(bars.iloc[:cut], "TEST")
        for event in prefix:
            assert event.available_date <= bars.index[cut - 1].date()
        # 截断日之前可用的事件与全量一致
        full_prefix = [e for e in full if e.available_date <= bars.index[cut - 1].date()]
        assert [e.event_id for e in prefix] == [e.event_id for e in full_prefix]


def test_empty_frame() -> None:
    assert detect_strict_structure_events(pd.DataFrame(), "TEST") == []
    assert detect_strict_structures(pd.DataFrame(columns=["high", "low"])) == []


def test_structure_id_deterministic() -> None:
    bars = _bars(
        [
            (9, 10, 9.0, 9.8),
            (9.4, 9.5, 8.7, 9.0),
            (8.9, 9.2, 8.3, 8.5),
        ]
    )
    again = detect_strict_structure_events(bars, "TEST")
    first = detect_strict_structure_events(bars, "TEST")
    assert [e.event_id for e in again] == [e.event_id for e in first]
    top = next(s for s in detect_strict_structures(bars) if s.side == SIDE_TOP)
    assert top.structure_id == "strict_top:2024-01-03"
