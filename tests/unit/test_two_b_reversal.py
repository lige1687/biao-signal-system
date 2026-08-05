"""2B/破底翻前向状态机门禁（规格 §9 模块 C）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.two_b_reversal import (
    SUB_RULE_FAILED,
    SUB_RULE_V1,
    SUB_RULE_V2,
    SUB_RULE_V3,
    detect_two_b_reversal_events,
)
from lei_signal.rules.volume import compute_volume_labels


def _feature_frame(scenario: str = "reclaim", rows: int = 210) -> pd.DataFrame:
    """构造带全特征的 2B 结构帧。

    结构：L2=110 @130 -> 颈线 128 @145 -> L1=115 @160（更高低点）-> 破底 -> 收回。
    scenario:
      "reclaim"     -- 破底后 3 根内收回 L1（v1 确认，v2/v3 后续满足时确认）；
      "timeout"     -- 破底后持续低于 L1 超过 two_b_reclaim_bars 根，不收回（窗口耗尽）；
      "l2_break"    -- 破底后直接跌破 L2（C3 失效）；
      "no_structure"-- 单边下行（更低低点），无 L1/L2 更高低点结构；
      "downtrend"   -- 单边下行 + 大幅负乖离，但无 2B 结构。
    """
    idx = pd.bdate_range("2024-01-02", periods=rows)
    p = np.zeros(rows)

    if scenario in ("no_structure", "downtrend"):
        # 单边下行：持续创新低，无更高低点结构；downtrend 加速以产生大幅负乖离。
        step = 0.4 if scenario == "downtrend" else 0.25
        for i in range(rows):
            p[i] = 200.0 - i * step
        close = pd.Series(p, index=idx, dtype=float)
        high = close + 0.2
        low = close - 0.2
        op = close - 0.05
        bars = pd.DataFrame(
            {"open": op, "high": high, "low": low, "close": close, "volume": 1_000_000.0},
            index=idx,
        )
        return compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))

    for i in range(126):
        p[i] = 100 + i * 0.2
    for i in range(126, 130):
        p[i] = 125 - (i - 126) * 3.0
    p[130] = 110  # L2
    for i in range(131, 136):
        p[i] = 110 + (i - 130) * 3.0
    for i in range(136, 145):
        p[i] = 125 + (i - 136) * 0.3
    p[145] = 128  # 颈线 swing high
    for i in range(146, 160):
        p[i] = 128 - (i - 145) * 0.8
    p[160] = 115  # L1（更高低点）
    for i in range(161, 164):
        p[i] = 115 + (i - 160) * 1.0  # 161=116,162=117,163=118（L1 右确认）

    if scenario == "reclaim":
        p[164] = 113  # 跌破 L1
        p[165] = 113
        p[166] = 113
        p[167] = 116  # 收回 L1 上方（bars_to_reclaim=3）
        for i in range(168, rows):
            p[i] = 116 + (i - 168) * 0.3
    elif scenario == "timeout":
        # 破底后持续低于 L1=115 但高于 L2=110，超过 3 根不收回。
        for i in range(164, rows):
            p[i] = 113.0
    elif scenario == "l2_break":
        # 破底后直接跌破 L2=110。
        p[164] = 113
        p[165] = 109  # 跌破 L2
        for i in range(166, rows):
            p[i] = 108.0

    close = pd.Series(p, index=idx, dtype=float)
    high = close + 0.2
    low = close - 0.2
    op = close - 0.05
    bars = pd.DataFrame(
        {"open": op, "high": high, "low": low, "close": close, "volume": 1_000_000.0},
        index=idx,
    )
    return compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_l1_l2_structure_and_v1_reclaim_confirms() -> None:
    frame = _feature_frame("reclaim")
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    # v1 在收回当日确认。
    assert SUB_RULE_V1 in subs
    v1 = next(e for e in events if _sub(e) == SUB_RULE_V1)
    assert v1.evidence["l1_price"] > v1.evidence["l2_price"]  # L1 > L2
    assert v1.evidence["close"] >= v1.evidence["l1_price"]  # 收回 L1 上方
    assert v1.evidence["bars_to_reclaim"] <= 3  # 快速收复窗口内
    # 每个版本至多一次确认。
    for sub in (SUB_RULE_V1, SUB_RULE_V2, SUB_RULE_V3):
        assert subs.count(sub) <= 1


def test_v2_and_v3_fire_when_ma_conditions_hold() -> None:
    frame = _feature_frame("reclaim")
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    # 收回后持续上行，EMA20/双均线相继转强，v2/v3 应触发。
    assert SUB_RULE_V2 in subs
    assert SUB_RULE_V3 in subs
    v1 = next(e for e in events if _sub(e) == SUB_RULE_V1)
    v2 = next(e for e in events if _sub(e) == SUB_RULE_V2)
    v3 = next(e for e in events if _sub(e) == SUB_RULE_V3)
    # v1 <= v2 <= v3（按可用日非递减）。
    assert v1.available_date <= v2.available_date <= v3.available_date


def test_window_timeout_consumes_structure() -> None:
    frame = _feature_frame("timeout")
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_FAILED in subs
    assert SUB_RULE_V1 not in subs  # 未收回，无确认
    failed = next(e for e in events if _sub(e) == SUB_RULE_FAILED)
    assert "快速收复窗口耗尽" in str(failed.evidence["failure_reason"])


def test_l2_break_fails() -> None:
    frame = _feature_frame("l2_break")
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_FAILED in subs
    failed = next(e for e in events if _sub(e) == SUB_RULE_FAILED)
    assert "跌破 L2" in str(failed.evidence["failure_reason"])
    assert failed.evidence["close"] < failed.evidence["l2_price"]


def test_no_higher_low_structure_does_not_trigger() -> None:
    frame = _feature_frame("no_structure")
    events = detect_two_b_reversal_events(frame, "TEST")
    # 单边下行无更高低点结构，不应产出任何 2B 事件。
    assert events == []


def test_negative_bias_alone_does_not_trigger() -> None:
    """大幅负乖离仅作增强，不单独触发交易（规格 §4.7 / C1）。"""
    frame = _feature_frame("downtrend")
    events = detect_two_b_reversal_events(frame, "TEST")
    assert events == []


def test_bias_recorded_as_enhancement_only() -> None:
    """有 2B 结构时，负乖离只进 evidence，不产生额外触发。"""
    frame = _feature_frame("reclaim")
    events = detect_two_b_reversal_events(frame, "TEST")
    confirmed = [e for e in events if _sub(e) in (SUB_RULE_V1, SUB_RULE_V2, SUB_RULE_V3)]
    assert confirmed
    for event in confirmed:
        assert event.evidence.get("bias_enhancement_only") is True
        # bias_ema120 被记录（可能为正或负，但一定存在键）。
        assert "bias_ema120" in event.evidence


def test_appending_future_bars_does_not_change_past_events() -> None:
    frame = _feature_frame("reclaim")
    cutoff = 180
    early = detect_two_b_reversal_events(frame.iloc[:cutoff], "TEST")
    full = detect_two_b_reversal_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]


def test_event_ids_are_deterministic() -> None:
    frame = _feature_frame("reclaim")
    a = detect_two_b_reversal_events(frame, "TEST")
    b = detect_two_b_reversal_events(frame, "TEST")
    assert [e.event_id for e in a] == [e.event_id for e in b]


def test_research_proxy_evidence_flag() -> None:
    frame = _feature_frame("reclaim")
    events = detect_two_b_reversal_events(frame, "TEST")
    assert events
    for event in events:
        assert event.evidence.get("research_proxy") is True
        assert event.provenance.value == "research_proxy"
