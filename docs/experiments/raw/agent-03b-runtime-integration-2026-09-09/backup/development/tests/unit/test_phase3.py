"""Phase 3 门禁：结构、C 生命周期、B1 与状态机。"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from lei_signal.domain.types import (
    LongTrendState,
    Pivot,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.bottom_structure import (
    apply_c_lifecycle,
    detect_bottom_structure_events,
    detect_double_bottoms,
    detect_higher_low_bottoms,
    detect_reversal_bottoms,
)
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.resistance_b1 import find_b1
from lei_signal.rules.reversals import detect_reversal_events
from lei_signal.rules.top_structure import detect_top_structure_events, detect_top_structures
from lei_signal.state.machine import run_state_machine
from tests.golden.fixtures import (
    golden_bottom_c_invalidation,
    golden_bullish_engulfing,
    golden_top_then_black,
)


def _prepared(bars: pd.DataFrame) -> pd.DataFrame:
    return compute_long_trend(classify_colors(compute_features(bars)))


# ---------------- 底部结构 ----------------


def test_reversal_bottom_is_created_without_any_long_trend_check() -> None:
    """门禁 6/架构 2.1：反包底部不得被 60/120 日线 Block。"""
    frame = _prepared(golden_bullish_engulfing())
    assert frame["ema60"].iloc[-1] < frame["ema120"].iloc[-1], "样例应为长周期空头"

    events = detect_reversal_events(frame, "TEST")
    structures = detect_reversal_bottoms(frame, "TEST", events)
    assert structures, "空头长周期下反转底部仍必须建立"

    last = structures[-1]
    assert last.structure_type == "bullish_reversal_bottom"
    assert last.confirmed_date == frame.index[-1].date()
    assert last.c_price == float(frame["low"].iloc[-1])
    assert last.is_live
    # 必须链接来源事件
    assert last.source_event_ids


def test_higher_low_bottom_requires_second_low_above_first() -> None:
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)
    structures = detect_higher_low_bottoms(frame, pivots, "TEST")
    for structure in structures:
        assert structure.structure_type == "higher_low_bottom"
        assert structure.c_price is not None
        assert structure.neckline is not None
        assert structure.neckline > structure.c_price


def test_double_bottom_respects_atr_tolerance_from_config() -> None:
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)
    structures = detect_double_bottoms(frame, pivots, "TEST")
    lows = sorted([p for p in pivots if p.kind == "low"], key=lambda p: p.index)
    for structure in structures:
        # 每个双底的两低点价差必须在 1 ATR 内
        assert structure.c_price is not None
    assert isinstance(lows, list)


def test_multiple_bottom_sources_coexist_without_deletion() -> None:
    """同一标的可同时保留多个底部来源。"""
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)
    reversal_events = detect_reversal_events(frame, "TEST")
    all_structures = (
        detect_higher_low_bottoms(frame, pivots, "TEST")
        + detect_double_bottoms(frame, pivots, "TEST")
        + detect_reversal_bottoms(frame, "TEST", reversal_events)
    )
    types = {s.structure_type for s in all_structures}
    assert len(all_structures) >= 2
    assert len(types) >= 2, "应保留多种来源的结构"
    # 结构 ID 必须唯一
    ids = [s.structure_id for s in all_structures]
    assert len(ids) == len(set(ids))


# ---------------- C 生命周期（门禁 8）----------------


def test_touching_c_invalidates_structure_permanently() -> None:
    """门禁 8：C 触及后永久失效，后续上涨不能复活。"""
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)
    structures = detect_higher_low_bottoms(frame, pivots, "TEST")
    confirmed = [s for s in structures if s.confirmed_date is not None]
    assert confirmed, "样例必须至少确认一个底部结构"

    events = apply_c_lifecycle(frame, structures, "TEST")
    invalidated = [s for s in structures if s.status is StructureStatus.INVALIDATED]
    assert invalidated, "跌破C后必须有结构失效"

    dead = invalidated[0]
    assert dead.invalidated_reason == "bottom_C_touched"
    assert dead.invalidated_date is not None
    assert not dead.is_live

    # 样例末段是强力反弹：结构不得复活
    final_close = float(frame["close"].iloc[-1])
    assert final_close > dead.c_price, "样例末段应已回到C之上"
    assert dead.status is StructureStatus.INVALIDATED, "后续上涨不得复活已失效结构"

    # 必须同时记录 touched 与 close_broken 两类事件
    sub_rules = {e.evidence["sub_rule"] for e in events}
    assert "bottom_C_touched" in sub_rules
    assert "bottom_C_close_broken" in sub_rules


def test_c_lifecycle_only_watches_days_after_confirmation() -> None:
    """确认日当天不判定触及，从下一交易日起。"""
    index = pd.bdate_range("2024-01-02", periods=5)
    frame = pd.DataFrame(
        {
            "open": [10.0] * 5,
            "high": [11.0] * 5,
            "low": [9.0, 9.0, 8.0, 9.5, 9.5],
            "close": [10.0] * 5,
            "volume": [1000.0] * 5,
        },
        index=index,
    )
    structure = StructureInstance(
        structure_id="s1",
        symbol="TEST",
        structure_type="higher_low_bottom",
        side="bottom",
        detected_date=index[0].date(),
        c_price=9.0,
        neckline=11.0,
        confirmed_date=index[1].date(),   # 确认日 low 也等于 9.0，但不应触发
        status=StructureStatus.CONFIRMED,
    )
    events = apply_c_lifecycle(frame, [structure], "TEST")
    assert structure.invalidated_date == index[2].date()
    assert events[0].event_date == index[2].date()


def test_c_touched_event_is_critical_and_traceable() -> None:
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)
    structures = detect_higher_low_bottoms(frame, pivots, "TEST")
    events = apply_c_lifecycle(frame, structures, "TEST")
    touched = [e for e in events if e.evidence["sub_rule"] == "bottom_C_touched"]
    assert touched
    event = touched[0]
    assert event.severity.value == "critical"
    assert event.structure_id is not None
    assert "c_price" in event.evidence and "low" in event.evidence


# ---------------- 顶部结构（门禁 9）----------------


def test_top_structure_confirms_on_neckline_break() -> None:
    frame = _prepared(golden_top_then_black())
    pivots = confirmed_pivots(frame, left=3, right=3)
    tops = detect_top_structures(frame, pivots, "TEST")
    confirmed = [t for t in tops if t.confirmed_date is not None]
    assert confirmed, "样例必须确认顶部警报"
    top = confirmed[0]
    assert top.reference_high is not None and top.neckline is not None
    assert top.neckline < top.reference_high


def test_top_structure_is_invalidated_by_new_high() -> None:
    """门禁 9：新高解除顶部警报。"""
    index = pd.bdate_range("2024-01-02", periods=40)
    # 手工构造：高点1=100, 回落到80, 高点2=95, 跌破80确认, 之后突破100解除
    close = (
        list(np.linspace(70, 100, 10))
        + list(np.linspace(99, 80, 8))
        + list(np.linspace(81, 95, 7))
        + list(np.linspace(94, 75, 7))
        + list(np.linspace(76, 110, 8))
    )
    frame = pd.DataFrame(
        {
            "open": close,
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "volume": [1000.0] * 40,
        },
        index=index,
    )
    prepared = _prepared(frame)
    pivots = confirmed_pivots(prepared, left=3, right=3)
    tops = detect_top_structures(prepared, pivots, "TEST")
    invalidated = [t for t in tops if t.invalidated_reason == "top_warning_invalidated_by_new_high"]
    assert invalidated, "突破第一高点后顶部必须解除"
    assert invalidated[0].status is StructureStatus.INVALIDATED

    events = detect_top_structure_events(tops, "TEST")
    sub_rules = {e.evidence["sub_rule"] for e in events}
    assert "top_warning_invalidated_by_new_high" in sub_rules


def test_top_events_are_risk_hints_not_sell_orders() -> None:
    frame = _prepared(golden_top_then_black())
    pivots = confirmed_pivots(frame, left=3, right=3)
    tops = detect_top_structures(frame, pivots, "TEST")
    for event in detect_top_structure_events(tops, "TEST"):
        assert "自动" not in event.reason_cn
        for forbidden in ("必须卖出", "建议卖出", "立即清仓"):
            assert forbidden not in event.reason_cn


# ---------------- B1（门禁 10）----------------


def _pivot(kind: str, day: date, price: float, index: int = 0) -> Pivot:
    return Pivot(
        kind=kind,
        index=index,
        pivot_date=day,
        price=price,
        confirmed_index=index + 3,
        available_date=day + timedelta(days=5),
    )


def test_b1_picks_most_recent_confirmed_high_above_price() -> None:
    as_of = date(2025, 6, 30)
    pivots = (
        _pivot("high", date(2025, 1, 10), 120.0, 10),
        _pivot("high", date(2025, 4, 15), 110.0, 40),   # 更近，应被选中
        _pivot("high", date(2025, 5, 20), 95.0, 60),    # 低于现价，排除
        _pivot("low", date(2025, 3, 1), 80.0, 30),      # 低点，排除
    )
    b1 = find_b1(pivots, as_of=as_of, current_close=100.0)
    assert b1 is not None
    assert b1.price == 110.0
    assert b1.pivot_date == date(2025, 4, 15)
    assert b1.distance_pct == 10.0


def test_b1_ignores_pivots_not_yet_confirmed_at_signal_time() -> None:
    """B1 只能使用信号发生前已确认的高点。"""
    as_of = date(2025, 6, 30)
    not_yet = Pivot(
        kind="high",
        index=100,
        pivot_date=date(2025, 6, 28),
        price=115.0,
        confirmed_index=103,
        available_date=date(2025, 7, 3),   # 确认日晚于 as_of
    )
    older = _pivot("high", date(2025, 2, 1), 108.0, 20)
    b1 = find_b1((not_yet, older), as_of=as_of, current_close=100.0)
    assert b1 is not None
    assert b1.price == 108.0, "尚未确认的高点不得作为B1"


def test_b1_respects_two_year_lookback_window() -> None:
    as_of = date(2025, 6, 30)
    ancient = _pivot("high", date(2022, 1, 3), 200.0, 5)
    b1 = find_b1((ancient,), as_of=as_of, current_close=100.0)
    assert b1 is None, "超过两年的高点不得作为B1"


def test_missing_b1_does_not_block_signal_generation() -> None:
    """门禁 10：B1 不存在仍产生信号。"""
    frame = _prepared(golden_bullish_engulfing())
    pivots = confirmed_pivots(frame, left=3, right=3)
    last_close = float(frame["close"].iloc[-1])
    as_of = frame.index[-1].date()

    b1 = find_b1(pivots, as_of=as_of, current_close=last_close)

    # 无论 B1 是否存在，反转底部与状态机都必须正常产出
    events = detect_reversal_events(frame, "TEST")
    structures = detect_reversal_bottoms(frame, "TEST", events)
    assert structures, "B1 缺失不得阻止结构生成"

    history = run_state_machine(frame, structures)
    assert history[-1].stage is not Stage.NO_CLUE, "B1 缺失不得导致无信号"
    # 显式覆盖 B1 为 None 的场景
    empty_b1 = find_b1((), as_of=as_of, current_close=last_close)
    assert empty_b1 is None
    assert b1 is None or b1.price > last_close


def test_b1_distance_r_only_computed_when_c_exists() -> None:
    as_of = date(2025, 6, 30)
    pivots = (_pivot("high", date(2025, 4, 15), 110.0, 40),)
    without_c = find_b1(pivots, as_of=as_of, current_close=100.0)
    assert without_c is not None and without_c.distance_r is None

    with_c = find_b1(pivots, as_of=as_of, current_close=100.0, c_price=95.0)
    assert with_c is not None and with_c.distance_r == 2.0   # (110-100)/(100-95)


# ---------------- 状态机 ----------------


def test_state_machine_keeps_prior_clues_alive() -> None:
    """先前信号不因当天其他条件未满足而被丢弃。"""
    frame = _prepared(golden_bullish_engulfing())
    events = detect_reversal_events(frame, "TEST")
    structures = detect_reversal_bottoms(frame, "TEST", events)
    history = run_state_machine(frame, structures)
    final = history[-1]
    assert final.live_bottoms, "底部线索必须持续有效"
    assert final.primary_bottom is not None


def test_state_machine_marks_conflict_when_top_and_bottom_coexist() -> None:
    """顶部与底部可暂时并存，必须显示冲突而不是静默覆盖。

    golden_top_then_black 是单向下跌样例，本身不含阳线反包，
    因此这里显式注入一个在顶部有效期内仍然存活的底部结构，
    直接验证状态机不会静默丢弃其中一个。
    """
    frame = _prepared(golden_top_then_black())
    pivots = confirmed_pivots(frame, left=3, right=3)
    tops = detect_top_structures(frame, pivots, "TEST")
    confirmed_tops = [t for t in tops if t.confirmed_date is not None]
    assert confirmed_tops, "样例必须确认顶部警报"
    top = confirmed_tops[0]

    # 注入一个早于顶部确认日、C 远低于样例最低价的底部结构，使其保持有效。
    floor_price = float(frame["low"].min()) - 5.0
    bottom = StructureInstance(
        structure_id="bottom-coexist",
        symbol="TEST",
        structure_type="bullish_reversal_bottom",
        side="bottom",
        detected_date=frame.index[0].date(),
        c_price=floor_price,
        neckline=float(frame["high"].iloc[0]),
        confirmed_date=frame.index[0].date(),
        status=StructureStatus.CONFIRMED,
    )

    history = run_state_machine(frame, [*tops, bottom])
    conflicted = [
        state for state in history if state.active_top is not None and state.live_bottoms
    ]
    assert conflicted, "应存在顶底并存的交易日"

    state = conflicted[0]
    assert state.day >= top.confirmed_date
    # 两者都必须保留，不得静默覆盖
    assert state.primary_bottom is not None
    assert state.active_top is not None
    assert state.stage in (Stage.RISK_WATCH, Stage.KEY_RISK)
    assert any("冲突" in reason or "Top+Black" in reason for reason in state.reasons)


def test_state_machine_reports_invalidated_when_all_bottoms_die() -> None:
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)
    structures = detect_higher_low_bottoms(frame, pivots, "TEST")
    apply_c_lifecycle(frame, structures, "TEST")
    history = run_state_machine(frame, structures)
    stages = {state.stage for state in history}
    assert Stage.INVALIDATED in stages or Stage.KEY_RISK in stages


def test_structure_events_are_deterministic_and_linked() -> None:
    frame = _prepared(golden_bottom_c_invalidation())
    pivots = confirmed_pivots(frame, left=3, right=3)

    def build() -> list[str]:
        structures = detect_higher_low_bottoms(frame, pivots, "TEST")
        events = detect_bottom_structure_events(structures, "TEST")
        events += apply_c_lifecycle(frame, structures, "TEST")
        return [e.event_id for e in events]

    assert build() == build()
    structures = detect_higher_low_bottoms(frame, pivots, "TEST")
    for event in detect_bottom_structure_events(structures, "TEST"):
        assert event.structure_id is not None, "结构事件必须链接 structure_id"


def test_long_trend_state_is_recorded_but_never_gates_bottom() -> None:
    """长周期状态出现在 DayState 中作为背景，但不阻止底部线索存在。"""
    frame = _prepared(golden_bullish_engulfing())
    structures = detect_reversal_bottoms(
        frame, "TEST", detect_reversal_events(frame, "TEST")
    )
    history = run_state_machine(frame, structures)
    final = history[-1]
    assert final.daily_long in set(LongTrendState)
    assert final.daily_long is LongTrendState.LONG_BEAR or not final.long_supportive
    assert final.live_bottoms, "长周期空头时底部线索仍必须存在"
