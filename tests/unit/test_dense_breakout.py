"""均线密集区突破前向状态机门禁（规格 §9 模块 B）。"""
from __future__ import annotations

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.dense_breakout import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_FAILED,
    SUB_RULE_WATCH,
    detect_dense_breakout_events,
)
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.volume import compute_volume_labels


def _feature_frame(scenario: str = "breakout", rows: int = 200) -> pd.DataFrame:
    """构造带全特征的帧。

    scenario:
      "breakout"  -- 前 150 根围绕 100 窄幅横盘（六线密集），之后突破上行成多头排列；
      "fallback"  -- 在 breakout 基础上，突破后快速砸回密集区上沿下方且 SMA20 下弯；
      "trend"     -- 单边上行，从不横盘，不应触发。
    """
    idx = pd.bdate_range("2024-01-02", periods=rows)
    close = pd.Series(100.0, index=idx, dtype=float)
    # 横盘段：围绕 100 极窄震荡，使六线纠缠度远低于 cluster_threshold(0.02)。
    for i in range(150):
        close.iloc[i] = 100.0 + (i % 7 - 3) * 0.04

    if scenario == "trend":
        # 单边上行，无横盘密集区。
        for i in range(rows):
            close.iloc[i] = 100.0 + i * 0.3
    else:
        # 突破上行段，建立完整多头排列。
        for i in range(150, rows):
            close.iloc[i] = 100.0 + (i - 150) * 0.9
        if scenario == "fallback":
            # 突破后快速砸回密集区上沿下方，并持续下行让 SMA20 下弯。
            peak = 100.0 + (180 - 150) * 0.9
            for i in range(180, rows):
                close.iloc[i] = max(96.0, peak - (i - 180) * 1.5)

    high = close + 0.25
    low = close - 0.25
    op = close - 0.05
    bars = pd.DataFrame(
        {"open": op, "high": high, "low": low, "close": close, "volume": 1_000_000.0},
        index=idx,
    )
    return compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_consolidation_then_breakout_confirms() -> None:
    frame = _feature_frame("breakout", 200)
    events = detect_dense_breakout_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    # 必须先 watch（密集区识别）后 confirmed（突破 + 完整多头排列）。
    assert SUB_RULE_WATCH in subs
    assert SUB_RULE_CONFIRMED in subs
    assert subs.index(SUB_RULE_WATCH) < subs.index(SUB_RULE_CONFIRMED)
    confirmed = next(e for e in events if _sub(e) == SUB_RULE_CONFIRMED)
    assert confirmed.evidence["arrangement_holds"] is True
    assert confirmed.evidence["close"] > confirmed.evidence["reference_price"]
    # 突破参考位在确认时被锁定。
    assert confirmed.evidence["breakout_reference"] == confirmed.evidence["reference_price"]


def test_breakout_then_fall_back_fails() -> None:
    frame = _feature_frame("fallback", 200)
    events = detect_dense_breakout_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_CONFIRMED in subs
    assert SUB_RULE_FAILED in subs
    assert subs.index(SUB_RULE_CONFIRMED) < subs.index(SUB_RULE_FAILED)
    failed = next(e for e in events if _sub(e) == SUB_RULE_FAILED)
    assert failed.evidence["close"] < failed.evidence["breakout_reference"]
    assert failed.evidence["sma20_slope"] < 0
    assert "跌回密集区" in str(failed.evidence["failure_reason"])


def test_steady_trend_without_consolidation_does_not_trigger() -> None:
    frame = _feature_frame("trend", 200)
    events = detect_dense_breakout_events(frame, "TEST")
    # 单边上行无横盘密集区，不应产出任何密集区突破事件。
    assert events == []


def test_one_confirmation_per_zone_lifecycle() -> None:
    """每个密集区生命周期内只允许一次突破确认（consumed 语义）。"""
    frame = _feature_frame("breakout", 200)
    events = detect_dense_breakout_events(frame, "TEST")
    confirmed = [e for e in events if _sub(e) == SUB_RULE_CONFIRMED]
    # 单一密集区生命周期 -> 至多一次确认。
    assert len(confirmed) == 1


def test_appending_future_bars_does_not_change_past_events() -> None:
    frame = _feature_frame("breakout", 200)
    cutoff = 170
    early = detect_dense_breakout_events(frame.iloc[:cutoff], "TEST")
    full = detect_dense_breakout_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]


def test_event_ids_are_deterministic() -> None:
    frame = _feature_frame("breakout", 200)
    a = detect_dense_breakout_events(frame, "TEST")
    b = detect_dense_breakout_events(frame, "TEST")
    assert [e.event_id for e in a] == [e.event_id for e in b]


def test_research_proxy_evidence_flag() -> None:
    frame = _feature_frame("breakout", 200)
    events = detect_dense_breakout_events(frame, "TEST")
    assert events  # 确保有事件
    for event in events:
        assert event.evidence.get("research_proxy") is True
        assert event.provenance.value == "research_proxy"
