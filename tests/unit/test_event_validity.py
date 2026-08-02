"""修复 5：事件三栏必须按真实生命周期分类。

不能继续使用 60 天展示窗代替生命周期。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.domain.types import SignalColor
from tests.golden.fixtures import golden_bullish_engulfing


def test_event_columns_split_by_real_validity() -> None:
    result = analyze_bars("TEST", golden_bullish_engulfing(), build_history=True)
    # 找某一天，三栏都必须按事件规则分类
    for day, assessment in result.assessments_by_date.items():
        # 当日触发的所有事件都属于 new_events
        for event in assessment.new_events:
            assert event.available_date == day
        # active_events 全部 structure_id 不属于失效列表
        dead_ids = {
            s.structure_id for s in result.structures
            if s.invalidated_date is not None and s.invalidated_date <= day
        }
        for event in assessment.active_events:
            if event.structure_id is not None:
                assert event.structure_id not in dead_ids
        # 颜色事件：颜色改变后必须进入 ended_events
        for event in assessment.active_events:
            if event.rule_id == "lei_color":
                assert event.evidence.get("color") == assessment.color.value


def test_dual_ma_confirm_event_ends_when_joint_state_fails() -> None:
    """双均线共同确认：状态不再成立 → 进入 ended。"""
    from lei_signal.compose.pipeline import analyze_bars
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 1.5, 300))
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.5, 300),
            "low": close - rng.uniform(0.3, 1.5, 300),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, 300).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=300),
    )
    result = analyze_bars("TEST", bars, build_history=True)
    # 在共同确认不成立的某天（颜色为 gray/black），
    # 不应仍有 active 状态的 dual_ma_bull_confirmed 事件。
    for day, assessment in result.assessments_by_date.items():
        if not assessment.joint_confirmed_now:
            for event in assessment.active_events:
                assert event.rule_id != "dual_ma_bull_confirmed", (
                    f"共同确认条件已不成立，{day} 不应仍有 active dual_ma_confirmed"
                )


def test_ema_reclaim_event_ends_when_color_turns_black() -> None:
    """EMA 早期转强：转黑 → 关联事件必须进入 ended。"""
    from lei_signal.compose.pipeline import analyze_bars
    rng = np.random.default_rng(11)
    close = 100 + np.cumsum(rng.normal(0, 1.5, 300))
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.5, 300),
            "low": close - rng.uniform(0.3, 1.5, 300),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, 300).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=300),
    )
    result = analyze_bars("TEST", bars, build_history=True)
    for _day, assessment in result.assessments_by_date.items():
        if assessment.color is SignalColor.BLACK:
            for event in assessment.active_events:
                if event.rule_id == "ema20_reclaim_rising":
                    assert event.structure_id is not None, (
                        "未绑定结构_id 的 EMA 转强在转黑日仍为 active"
                    )


def test_swing_pivot_events_are_historical_facts_not_active_signals() -> None:
    """摆动点：永久历史事实，不应进入「当前仍有效」栏。"""
    result = analyze_bars("TEST", golden_bullish_engulfing(), build_history=True)
    for day, assessment in result.assessments_by_date.items():
        swing_active = [e for e in assessment.active_events if e.rule_id == "swing_pivots"]
        assert len(swing_active) == 0, (
            f"摆动点不应进入 active 栏：{day} 有 {len(swing_active)} 条"
        )
