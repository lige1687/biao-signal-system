"""状态延迟升级：本项目最重要的验收测试（架构第 15 节漏信号案例）。

要求（任务说明第七节）：
    Day A：底部候选成立、EMA20 重新站上、长周期趋势仍冲突
    Day B：没有新的 EMA20 交叉、双均线当前仍共同向上、长周期趋势变为改善
    预期：状态从早期转强/共同确认升级为趋势增强
          不得因为 Day B 没有新交叉而无信号
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import LongTrendState, Stage
from lei_signal.features.indicators import compute_features
from lei_signal.rules.bottom_structure import detect_reversal_bottoms
from lei_signal.rules.dual_ma import dual_ma_bull_state, ema20_reclaim_state
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.reversals import detect_reversal_events
from lei_signal.state.machine import run_state_machine
from tests.golden.fixtures import golden_delayed_upgrade

_IMPROVED = {
    LongTrendState.LONG_IMPROVING,
    LongTrendState.LONG_BULL,
    LongTrendState.LONG_STABLE_BULL,
}


def _run() -> tuple[pd.DataFrame, list]:
    frame = compute_long_trend(classify_colors(compute_features(golden_delayed_upgrade())))
    structures = detect_reversal_bottoms(frame, "TEST", detect_reversal_events(frame, "TEST"))
    history = run_state_machine(frame, structures)
    return frame, history


def test_day_a_records_early_strength_while_long_trend_still_conflicts() -> None:
    """Day A：短期转强被记录，长周期冲突只是标签，不得导致无信号。"""
    frame, history = _run()
    reclaim = ema20_reclaim_state(frame)
    reclaim_days = frame.index[reclaim]
    assert len(reclaim_days) > 0, "样例必须包含 EMA20 重新站上"

    first_reclaim = reclaim_days[0]
    state = next(s for s in history if s.day == first_reclaim.date())

    # 长周期此时仍不支持
    assert not state.long_supportive, "Day A 长周期应仍冲突"
    # 但短期转强必须被保留，且已进入机会阶段
    assert state.early_strength_active
    assert state.stage is not Stage.NO_CLUE, "长周期冲突不得使 Day A 无信号"


def test_day_b_upgrades_to_trend_reinforced_without_a_new_ema20_cross() -> None:
    """Day B：不再出现新的 EMA20 交叉，但长周期改善后必须升级为趋势增强。"""
    frame, history = _run()
    reclaim = ema20_reclaim_state(frame)
    reclaim_days = frame.index[reclaim]
    last_reclaim = reclaim_days[-1]

    # 找到最后一次交叉之后、长周期已改善且双均线仍共同向上的日子
    joint = dual_ma_bull_state(frame)
    upgraded = [
        state
        for state in history
        if state.day > last_reclaim.date()
        and state.stage is Stage.TREND_REINFORCED
    ]
    assert upgraded, "长周期改善后必须出现趋势增强阶段"

    day_b = upgraded[0]
    timestamp = pd.Timestamp(day_b.day)

    # 关键断言：Day B 当天没有新的 EMA20 交叉
    assert not bool(reclaim.loc[timestamp]), "Day B 不应存在新的 EMA20 交叉"
    # 双均线当前仍共同向上
    assert bool(joint.loc[timestamp])
    assert day_b.joint_confirmed_now
    # 长周期已转为改善/支持
    assert day_b.long_supportive
    assert day_b.daily_long in _IMPROVED or day_b.weekly_long in _IMPROVED
    # 升级理由必须可解释
    assert any("趋势增强" in reason for reason in day_b.reasons)


def test_upgrade_does_not_require_a_fresh_bottom_structure() -> None:
    """8 月升级使用的是 6 月已有的底部线索，不要求重新形成底部。"""
    frame, history = _run()
    upgraded = [s for s in history if s.stage is Stage.TREND_REINFORCED]
    assert upgraded

    day_b = upgraded[0]
    assert day_b.primary_bottom is not None
    # 主结构的确认日必须**早于** Day B，证明用的是旧结构
    assert day_b.primary_bottom.confirmed_date is not None
    assert day_b.primary_bottom.confirmed_date < day_b.day, (
        "趋势增强必须能够使用先前已有的底部结构"
    )


def test_stage_progression_reaches_joint_confirmed_before_reinforced() -> None:
    """阶段必须逐级出现，不能跳过共同确认直接到趋势增强。"""
    _, history = _run()
    stages = [state.stage for state in history]
    assert Stage.JOINT_CONFIRMED in stages
    assert Stage.TREND_REINFORCED in stages
    first_joint = stages.index(Stage.JOINT_CONFIRMED)
    first_reinforced = stages.index(Stage.TREND_REINFORCED)
    assert first_joint < first_reinforced


def test_no_signal_is_never_the_answer_when_clues_are_alive() -> None:
    """存在有效底部线索时，不得输出无线索。"""
    _, history = _run()
    for state in history:
        if state.live_bottoms:
            assert state.stage is not Stage.NO_CLUE, (
                f"{state.day} 存在有效底部线索却输出无线索"
            )


def test_full_history_is_reproducible() -> None:
    """同样数据重复运行，逐日阶段完全一致。"""
    _, first = _run()
    _, second = _run()
    assert [(s.day, s.stage) for s in first] == [(s.day, s.stage) for s in second]
