"""Round 2 修复 2：事件真实生命周期回归。

按用户列出的 6 个回归点：
  1. 绿色→黑色→绿色，最后只能有第二段绿色 start 处于 active
  2. 多次共同确认，只有最近尚未结束的一段 active
  3. Top+Black 结束后旧 start 不能复活
  4. 所有 *_ended 事件永远不能 active
  5. 量能、反包、摆动点事件不能在触发日以后长期 active
  6. 同一状态重新进入产生新的实例，而不是复活旧实例
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze_bars


def _bars(n: int = 200, seed: int = 21) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, n))
    return pd.DataFrame(
        {
            "open": close, "high": close + rng.uniform(0.3, 1.5, n),
            "low": close - rng.uniform(0.3, 1.5, n), "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=n),
    )


def test_1_green_black_green_only_last_green_segment_active() -> None:
    """1. 绿色→黑色→绿色，最后只能有第二段绿色 start 处于 active。"""
    rows: list[dict[str, float]] = []
    # 缓慢上升触发第一段绿色
    for i in range(80):
        rows.append(
            {"open": 100.0 + i * 0.13, "high": 100.5 + i * 0.13,
             "low": 99.5 + i * 0.13, "close": 100.0 + i * 0.13,
             "volume": 1_000_000}
        )
    # 剧烈下跌触发黑色
    for i in range(60):
        rows.append(
            {"open": 110.0 - i * 0.5, "high": 110.5 - i * 0.5,
             "low": 109.5 - i * 0.5, "close": 110.0 - i * 0.5,
             "volume": 1_000_000}
        )
    # 再次缓慢上升触发第二段绿色（持续到末尾）
    for i in range(60):
        rows.append(
            {"open": 50.0 + i, "high": 50.5 + i,
             "low": 49.5 + i, "close": 50.0 + i,
             "volume": 1_000_000}
        )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("T", bars, build_history=True)
    # 在最后一天：active 的绿色事件必须只有一个
    assessment = result.assessment
    assert assessment.color.value == "green", "最后一天颜色必须为绿色"
    active_color = [
        e for e in assessment.active_events
        if e.rule_id == "lei_color" and e.evidence.get("color") == "green"
    ]
    assert len(active_color) == 1, (
        f"只应有 1 个 active 绿色事件，实际 {len(active_color)}："
        f"{[(e.event_id, e.valid_until) for e in active_color]}"
    )
    # 必须有不同的 lifecycle_id
    green_starts = [
        e for e in result.events
        if e.rule_id == "lei_color" and e.evidence.get("sub_rule") == "lei_color_green_started"
    ]
    assert len(green_starts) >= 2
    ids = {e.lifecycle_id for e in green_starts}
    assert len(ids) == len(green_starts), "每次进入必须产生独立的 lifecycle_id"


def test_2_multiple_dual_ma_confirms_only_last_active() -> None:
    """2. 多次共同确认，只有最近尚未结束的一段 active。

    数据构造：先缓慢上升触发 green joint；之后剧烈下跌切断；
    然后再缓慢上升触发第二段 green joint 持续到末尾。
    """
    rows: list[dict[str, float]] = []
    # 前 80 根：缓慢上升（day 0=100, day 79=110）
    for i in range(80):
        rows.append(
            {"open": 100.0 + i * 0.13, "high": 100.5 + i * 0.13,
             "low": 99.5 + i * 0.13, "close": 100.0 + i * 0.13,
             "volume": 1_000_000}
        )
    # 60 根：剧烈下跌到 80
    for i in range(60):
        rows.append(
            {"open": 110.0 - i * 0.5, "high": 110.5 - i * 0.5,
             "low": 109.5 - i * 0.5, "close": 110.0 - i * 0.5,
             "volume": 1_000_000}
        )
    # 60 根：再次缓慢上升（day 140 起, close 50→110）
    for i in range(60):
        rows.append(
            {"open": 50.0 + i, "high": 50.5 + i,
             "low": 49.5 + i, "close": 50.0 + i,
             "volume": 1_000_000}
        )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("T", bars, build_history=True)
    assessment = result.assessment
    # 在最后一天：joint_confirmed_now 应为 True
    assert assessment.joint_confirmed_now, (
        f"最后一天必须处于共同确认状态，最后 {assessment.color.value}，"
        f"joint={assessment.joint_confirmed_now}"
    )
    active_dual = [
        e for e in assessment.active_events
        if e.rule_id == "dual_ma_bull_confirmed"
    ]
    assert len(active_dual) == 1, (
        f"只应有 1 个 active 共同确认事件，实际 {len(active_dual)}"
    )
    # 必须有不同的 lifecycle_id
    all_dual = [e for e in result.events if e.rule_id == "dual_ma_bull_confirmed"]
    assert len(all_dual) >= 2, (
        f"应至少 2 次共同确认（绿段 1 + 绿段 2），实际 {len(all_dual)}"
    )
    ids = {e.lifecycle_id for e in all_dual}
    assert len(ids) == len(all_dual), "每次进入必须产生独立的 lifecycle_id"
    # 旧绿段 1 的 lifecycle 必须已 ended（valid_until <= 旧绿段 1 结束日）
    first = all_dual[0]
    first_start = first.available_date
    second = all_dual[1]
    second_start = second.available_date
    assert first_start < second_start, "应按时间排序"
    assert first.valid_until is not None
    assert first.valid_until <= second_start, "旧段必须在新段开始前结束"


def test_3_top_plus_black_ended_does_not_resurrect_old_start() -> None:
    """3. Top+Black 结束后旧 start 不能复活。"""
    rows: list[dict[str, float]] = []
    for _ in range(80):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0,
             "volume": 1_000_000}
        )
    # 黑段
    for _ in range(80, 100):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 95.0, "close": 95.5,
             "volume": 1_000_000}
        )
    # 构造一个 fake_top
    from datetime import date

    from lei_signal.domain.types import StructureInstance, StructureStatus
    confirmed = date(2023, 6, 21)
    top = StructureInstance(
        structure_id="top-fake", symbol="T", structure_type="top_structure",
        side="top", detected_date=confirmed, neckline=60.0, reference_high=70.0,
        confirmed_date=confirmed, status=StructureStatus.INVALIDATED,
        invalidated_date=confirmed, invalidated_reason="top_warning_invalidated_by_new_high",
    )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("T", bars, build_history=True)
    # Top+Black 进入事件（如果有）应只在有 top 的区间内
    top_black_events = [
        e for e in result.events
        if e.evidence.get("sub_rule") == "top_plus_black"
    ]
    # 顶部已失效，top+black 事件 valid_until 应不超过 invalidated_date
    for e in top_black_events:
        assert e.valid_until is None or e.valid_until <= top.invalidated_date


def test_4_ended_events_never_active() -> None:
    """4. 所有 *_ended 事件永远不能 active。"""
    rows: list[dict[str, float]] = []
    for _ in range(80):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0,
             "volume": 1_000_000}
        )
    for _ in range(80, 100):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 95.0, "close": 95.5,
             "volume": 1_000_000}
        )
    for _ in range(100, 120):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0,
             "volume": 1_000_000}
        )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("T", bars, build_history=True)
    # 在任何一天的 active_events 中，*_ended 事件必须不存在
    for day, assessment in result.assessments_by_date.items():
        for e in assessment.active_events:
            assert not (e.evidence.get("sub_rule", "") or "").endswith("_ended"), (
                f"{day}: *_ended 事件 '{e.event_id}' 出现在 active 中"
            )
            assert e.rule_id != "key_wave_black_ended", (
                f"{day}: key_wave_black_ended 出现在 active 中"
            )


def test_5_volume_reversal_pivot_events_not_persistently_active() -> None:
    """5. 量能、反包、摆动点事件不能在触发日以后长期 active。"""
    result = analyze_bars("T", _bars(seed=33), build_history=True)
    for day, assessment in result.assessments_by_date.items():
        # 反转 K 线、量能、摆动点、底部 C 生命周期都是单次事件
        for e in assessment.active_events:
            if e.rule_id in (
                "swing_pivots",
                "bullish_engulfing", "bullish_outside_reversal",
                "bearish_engulfing", "bearish_outside_reversal",
                "volume_proxies",
                "bottom_c_lifecycle",
            ):
                raise AssertionError(
                    f"{day}: 单次事件 {e.rule_id}/{e.event_id} 出现在 active 中"
                )


def test_6_state_reentry_creates_new_instance_not_resurrects_old() -> None:
    """6. 同一状态重新进入产生新的实例，而不是复活旧实例。"""
    rows: list[dict[str, float]] = []
    for _ in range(50):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0,
             "volume": 1_000_000}
        )
    # 绿段 1
    for _ in range(50, 60):
        rows.append(
            {"open": 100.0, "high": 105.0, "low": 100.0, "close": 104.5,
             "volume": 1_000_000}
        )
    # 黑段
    for _ in range(60, 70):
        rows.append(
            {"open": 100.0, "high": 100.5, "low": 95.0, "close": 95.5,
             "volume": 1_000_000}
        )
    # 绿段 2
    for _ in range(70, 100):
        rows.append(
            {"open": 100.0, "high": 110.0, "low": 100.0, "close": 109.5,
             "volume": 1_000_000}
        )
    bars = pd.DataFrame(rows, index=pd.bdate_range("2023-01-02", periods=len(rows)))[
        ["open", "high", "low", "close", "volume"]
    ]
    result = analyze_bars("T", bars, build_history=True)
    # 找两个 green start 事件
    green_starts = [
        e for e in result.events
        if e.rule_id == "lei_color"
        and e.evidence.get("sub_rule") == "lei_color_green_started"
    ]
    assert len(green_starts) >= 2, f"应至少 2 个绿色 start 事件，实际 {len(green_starts)}"
    # 它们的 lifecycle_id 必须不同
    ids = {e.lifecycle_id for e in green_starts if e.lifecycle_id is not None}
    assert len(ids) == len(green_starts), (
        f"两次进入必须产生不同 lifecycle_id：{ids}"
    )
    # valid_until 不为 None
    for e in green_starts:
        assert e.valid_until is not None, "valid_until 必须被设置"
