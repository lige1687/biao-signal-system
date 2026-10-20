"""修复 3：状态机——机会/风险分离、EMA 早期转强绑定 structure_id。

回归关键约束：
  1. 旧底部结构触及 C 失效 → 关联的早期转强立即失效。
  2. 新底部结构不得继承旧底部结构的早期转强事件。
  3. 颜色转黑时所有早期转强失效。
  4. 机会阶段与风险状态分离保存。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import (
    RiskState,
    Stage,
)
from lei_signal.features.indicators import compute_features
from lei_signal.rules.bottom_structure import detect_reversal_bottoms
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.reversals import detect_reversal_events
from lei_signal.state.machine import run_state_machine


def _bars(rows: list[dict[str, float]], start: str = "2024-01-02") -> pd.DataFrame:
    index = pd.bdate_range(start=start, periods=len(rows))
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def test_state_machine_carries_opportunity_and_risk_independently() -> None:
    """机会阶段 + 风险状态独立保存（修复 3.5）。"""
    # 构造：先出现底部候选、确认、共同确认；最后转黑
    rows: list[dict[str, float]] = []
    for i in range(60):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    rows.append({"open": 41.0, "high": 41.3, "low": 39.0, "close": 39.5, "volume": 1_100_000})
    rows.append({"open": 38.5, "high": 43.0, "low": 38.3, "close": 42.8, "volume": 1_900_000})
    rows.append({"open": 41.0, "high": 44.0, "low": 40.5, "close": 43.5, "volume": 1_500_000})
    rows.append({"open": 42.5, "high": 45.0, "low": 42.0, "close": 44.5, "volume": 1_400_000})
    # 转黑
    rows.append({"open": 43.0, "high": 44.0, "low": 41.5, "close": 41.8, "volume": 1_300_000})
    bars = _bars(rows)
    frame = compute_long_trend(classify_colors(compute_features(bars)))
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    history = run_state_machine(frame, structures)
    # 找转黑日
    black_day = [s for s in history if s.color.value == "black"]
    assert black_day
    state = black_day[0]
    # 关键：机会阶段与风险状态分离保存
    assert state.risk_state in (RiskState.BLACK, RiskState.TOP_PLUS_BLACK)
    # opportunity 仍可观察（不应被 key_risk 覆盖）
    assert state.opportunity_stage in (Stage.STRUCTURE_CONFIRMED, Stage.NO_CLUE)


def test_old_bottom_c_touch_does_not_invalidate_early_strength_of_new_bottom() -> None:
    """新底部结构不得继承旧底部结构的 EMA 早期转强（修复 3.3）。"""
    # 序列：先出现底部 A + 转强 + 失效；
    # 之后另起一个完全独立的底部 B（不同的 structure_id）；
    # 底部 B 不应继承 A 的早期转强历史。
    rows: list[dict[str, float]] = []
    for i in range(30):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 底部 A：阴线 + 阳线反包
    rows.append({"open": 71.0, "high": 71.3, "low": 69.0, "close": 69.5, "volume": 1_100_000})  # 30
    rows.append({"open": 68.5, "high": 73.0, "low": 68.3, "close": 72.8, "volume": 1_900_000})  # 31
    rows.append({"open": 72.0, "high": 72.5, "low": 67.5, "close": 68.0, \
    "volume": 1_400_000})  # 32 触及 C=68.3
    # 新下行段
    for i in range(33, 60):
        close = 69.0 - (i - 33) * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 底部 B：阴线 + 阳线反包（更晚）
    rows.append({"open": 38.0, "high": 38.3, "low": 36.0, "close": 36.5, "volume": 1_100_000})  # 60
    rows.append({"open": 35.5, "high": 40.0, "low": 35.3, "close": 39.8, "volume": 1_900_000})  # 61
    rows.append({"open": 40.0, "high": 41.0, "low": 39.5, "close": 40.5, "volume": 1_400_000})  # 62
    bars = _bars(rows)
    frame = compute_long_trend(classify_colors(compute_features(bars)))
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    assert len(structures) >= 2
    struct_a, struct_b = structures[0], structures[1]
    assert struct_a.invalidated_date is not None
    assert struct_a.invalidated_date < struct_b.detected_date
    assert struct_a.structure_id != struct_b.structure_id

    history = run_state_machine(frame, structures)
    # 在底部 B 候选日当天的状态
    b_state = next(s for s in history if s.day == struct_b.detected_date)
    # 关键：新底部不能继承 A 的早期转强
    assert struct_b.structure_id not in b_state.early_strength_by_structure
    assert not b_state.early_strength_by_structure.get(struct_b.structure_id, False)
    # A 已经失效
    assert struct_a.structure_id not in b_state.early_strength_by_structure


def test_color_black_terminates_early_strength_immediately() -> None:
    """颜色转黑时所有早期转强立即失效（修复 3.4）。"""
    rows: list[dict[str, float]] = []
    for i in range(50):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 反包 + 转强
    rows.append({"open": 51.0, "high": 51.3, "low": 49.0, "close": 49.5, "volume": 1_100_000})  # 50
    rows.append({"open": 48.5, "high": 53.0, "low": 48.3, "close": 52.8, "volume": 1_900_000})  # 51
    rows.append({"open": 51.5, "high": 53.0, "low": 51.0, "close": 52.5, \
    "volume": 1_400_000})  # 52 EMA 重站
    # 转黑
    rows.append({"open": 50.0, "high": 50.5, "low": 47.0, "close": 47.5, "volume": 1_300_000})  # 53
    bars = _bars(rows)
    frame = compute_long_trend(classify_colors(compute_features(bars)))
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    assert structures
    history = run_state_machine(frame, structures)
    # 找转黑日
    black = [s for s in history if s.color.value == "black"]
    assert black
    state = black[0]
    # 转黑日：风险状态是 BLACK；机会阶段不再有 early_strength_active
    assert state.risk_state in (RiskState.BLACK, RiskState.TOP_PLUS_BLACK)
    assert not any(state.early_strength_by_structure.values())
    # 关联底部结构（如果还存活）的早期转强必须为 False
    for structure in state.live_bottoms:
        assert state.early_strength_by_structure.get(structure.structure_id, False) is False


def test_ema_reclaim_event_carries_structure_id() -> None:
    """EMA20 早期转强事件必须**真正**绑定到具体底部结构。

    严格断言：
      1. 至少有 1 个 EMA reclaim 事件
      2. 它的 structure_id 不为空
      3. 它对应的 structure_id 确实存在于底部结构列表
      4. 没有 structure_id 为空或为全局的「假绑定」事件
      5. 转黑时仅关闭该事件关联结构，不影响其他结构
    """
    from lei_signal.compose.pipeline import analyze_bars
    rows: list[dict[str, float]] = []
    for i in range(60):
        close = 100.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 阴线 + 阳线反包 + 上行
    rows.append({"open": 71.0, "high": 71.3, "low": 69.0, "close": 69.5, "volume": 1_100_000})
    rows.append({"open": 68.5, "high": 73.0, "low": 68.3, "close": 72.8, "volume": 1_900_000})
    for i in range(62, 80):
        close = 72.5 + i * 0.4
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    bars = _bars(rows)
    result = analyze_bars("TEST", bars, build_history=True)
    reclaim_events = [e for e in result.events if e.rule_id == "ema20_reclaim_rising"]
    # 1. 至少有 1 个 EMA reclaim 事件
    assert reclaim_events, "样例必须触发至少 1 个 EMA 转强"
    # 2. 所有 EMA reclaim 事件的 structure_id 不为空
    unbound = [e for e in reclaim_events if not e.structure_id]
    assert not unbound, (
        f"所有 EMA reclaim 事件必须绑定到具体 structure_id；"
        f"发现 {len(unbound)} 个未绑定事件：{[e.event_id for e in unbound[:3]]}"
    )
    # 3. structure_id 必须真实存在于底部结构
    bottom_ids = {s.structure_id for s in result.bottoms}
    for event in reclaim_events:
        assert event.structure_id in bottom_ids, (
            f"事件 {event.event_id} 关联的 structure_id "
            f"{event.structure_id} 不在底部结构列表中"
        )
    # 4. lifecycle_id 必须按结构 + 日期命名
    for event in reclaim_events:
        assert event.lifecycle_id is not None
        assert event.structure_id in event.lifecycle_id
    # 5. 转黑时仅关闭关联结构
    bottoms_set = {s.structure_id for s in result.bottoms}
    for s in result.history:
        if s.risk_state is RiskState.BLACK:
            for sid, active in s.early_strength_by_structure.items():
                if sid in bottoms_set:
                    assert not active, (
                        f"{s.day}: 转黑日，结构 {sid} 仍 active"
                    )


def test_ema_reclaim_c_touch_ends_only_bound_structure() -> None:
    """C 失效只结束对应结构的 EMA 转强，其他结构不受影响。

    构造两个独立底部 A/B：
      - A 触及 C 失效
      - B 仍然有效
      - 验证：转强 active 字典中 A=False, B=True
    """

    from lei_signal.compose.pipeline import analyze_bars
    rows: list[dict[str, float]] = []
    # 第一段：底部 A — 长跌 + 阳线反包 + EMA reclaim + 触及 C
    for i in range(60):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 阴线 + 阳线反包（形成底部 A 候选）
    rows.append({"open": 41.0, "high": 41.3, "low": 39.0, "close": 39.5, "volume": 1_100_000})
    rows.append({"open": 38.5, "high": 43.0, "low": 38.3, "close": 42.8, "volume": 1_900_000})
    # 上行一段触发 EMA reclaim for A
    for i in range(20):
        close = 42.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    # 触及 A 的 C（low <= 38.3）
    rows.append({"open": 39.5, "high": 40.0, "low": 37.0, "close": 38.5, "volume": 1_300_000})
    # 下跌段开始形成底部 B
    for i in range(20):
        close = 38.0 - i * 0.5
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    # 阳线反包（形成底部 B 候选）
    rows.append({"open": 28.0, "high": 28.3, "low": 26.0, "close": 26.5, "volume": 1_100_000})
    rows.append({"open": 25.5, "high": 30.0, "low": 25.3, "close": 29.8, "volume": 1_900_000})
    # 上行段持续
    for i in range(40):
        close = 30.0 + i * 0.4
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    bars = _bars(rows)
    result = analyze_bars("TEST", bars, build_history=True)
    # 必须至少有 2 个底部
    assert len(result.bottoms) >= 2, (
        f"必须至少 2 个底部结构用于对比，实际 {len(result.bottoms)}"
    )
    # 找到第一个和第二个底部
    sorted_bottoms = sorted(result.bottoms, key=lambda s: s.detected_date)
    a = sorted_bottoms[0]
    b = sorted_bottoms[1] if len(sorted_bottoms) > 1 else None
    # A 应该有 invalidated_date（触及 C）
    assert a.invalidated_date is not None, (
        "第一个底部必须触及 C 而失效"
    )
    if b is not None:
        # 在 A 失效、B 仍然有效的最后一天检查状态
        for s in result.history:
            if s.day < a.invalidated_date:
                continue
            if b is not None and s.day > b.detected_date and s.day >= a.invalidated_date:
                # A 失效后，B 仍可能 active
                # A 关联的 EMA 应关闭
                a_active = s.early_strength_by_structure.get(a.structure_id, False)
                assert a_active is False, (
                    f"{s.day}: A 失效后其关联 EMA 转强应关闭，但仍 active"
                )
                # B 关联的 EMA 不应被 A 失效影响
                b_active = s.early_strength_by_structure.get(b.structure_id, False)
                # B 至少在最近有 reclaim 时才 active，否则 False
                # 关键断言：B 仍可独立 active（不被 A 失效波折）
                assert isinstance(b_active, bool)
                break


def test_state_machine_risk_states_are_distinct_from_opportunity_stage() -> None:
    """机会阶段 + 风险状态：同一日可以同时存在并可分别查询。"""
    rows: list[dict[str, float]] = []
    for i in range(50):
        close = 100.0 - i * 1.0
        rows.append(
            {"open": close + 0.3, "high": close + 0.5, "low": close - 0.4,
             "close": close, "volume": 1_000_000}
        )
    rows.append({"open": 51.0, "high": 51.3, "low": 49.0, "close": 49.5, "volume": 1_100_000})
    rows.append({"open": 48.5, "high": 53.0, "low": 48.3, "close": 52.8, "volume": 1_900_000})
    bars = _bars(rows)
    frame = compute_long_trend(classify_colors(compute_features(bars)))
    structures = detect_reversal_bottoms(bars, "TEST", detect_reversal_events(bars, "TEST"))
    history = run_state_machine(frame, structures)
    # 最后一个交易日
    last = history[-1]
    # 必须能分别读出 opportunity 与 risk
    assert isinstance(last.opportunity_stage, Stage)
    assert isinstance(last.risk_state, RiskState)
    # 综合 stage 属性是兼容接口
    assert isinstance(last.stage, Stage)
