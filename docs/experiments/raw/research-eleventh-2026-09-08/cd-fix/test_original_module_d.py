"""模块 D：假跌破反转前向状态机门禁（规格 §9 模块 D，V2 正式口径）。"""
from __future__ import annotations

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.module_d_false_breakout import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_FAILED,
    detect_module_d_events,
)
from lei_signal.rules.volume import compute_volume_labels


def _feature_frame(scenario: str = "confirm", rows: int = 400) -> pd.DataFrame:
    """夹具：横盘密集区（时钟三类寿命+带宽）内自然形成摆动波谷 -> 假跌破 -> 走向。

    scenario:
      confirm  -- 跌破近期波谷后快速收回，且站上 SMA20 与抵扣价（两动作齐备）；
      fail     -- 跌破后继续新低（假跌破低点失守）；
      trend    -- 单边上行，无密集区。
    """
    idx = pd.bdate_range("2024-01-02", periods=rows)
    close = pd.Series(100.0, index=idx, dtype=float)
    # 横盘 170 根，波幅略大以形成可确认摆动波谷（左3右3 严格最低）。
    pattern = [100.0, 100.3, 100.5, 100.3, 99.8, 99.5, 99.8, 100.2, 100.5, 100.3]
    for i in range(280):
        close.iloc[i] = pattern[i % len(pattern)]
    trough = 99.5 - 0.2  # 摆动波谷的盘中 low（参照价）

    if scenario == "trend":
        for i in range(rows):
            close.iloc[i] = 100.0 + i * 0.3
    elif scenario == "confirm":
        # 跌破波谷（close < 99.3），3 根内收回并冲高站上 SMA20 与抵扣价。
        close.iloc[280] = 99.2
        close.iloc[281] = 99.0
        close.iloc[282] = 99.9
        for i in range(283, rows):
            close.iloc[i] = close.iloc[i - 1] + 0.3
    elif scenario == "fail":
        # 跌破波谷后持续新低。
        close.iloc[280] = 99.0
        for i in range(281, rows):
            close.iloc[i] = max(80.0, close.iloc[i - 1] - 0.4)

    high = close + 0.2
    low = close - 0.2
    op = close - 0.05
    bars = pd.DataFrame(
        {"open": op, "high": high, "low": low, "close": close, "volume": 1_000_000.0},
        index=idx,
    )
    return compute_volume_labels(compute_long_trend(classify_colors(compute_features(bars))))


def _subs(events: list) -> list[str]:  # noqa: ANN001
    return [str(e.evidence["sub_rule"]) for e in events]


def test_confirm_emits_long_event_with_stop() -> None:
    frame = _feature_frame("confirm", 400)
    events = detect_module_d_events(frame, "TEST")
    subs = _subs(events)
    assert SUB_RULE_CONFIRMED in subs, f"应产生确认事件，实际 {subs}"
    confirmed = next(e for e in events if str(e.evidence["sub_rule"]) == SUB_RULE_CONFIRMED)
    # 止损 = 假跌破低点（D3）
    assert confirmed.evidence["stop_price"] == confirmed.evidence["false_low"]
    assert confirmed.evidence["false_low"] < confirmed.evidence["valley_price"]


def test_fail_on_new_low_below_false_low() -> None:
    frame = _feature_frame("fail", 400)
    events = detect_module_d_events(frame, "TEST")
    subs = _subs(events)
    assert SUB_RULE_FAILED in subs
    assert SUB_RULE_CONFIRMED not in subs


def test_trend_no_events() -> None:
    frame = _feature_frame("trend", 400)
    events = detect_module_d_events(frame, "TEST")
    assert events == []


def test_research_proxy_flag() -> None:
    frame = _feature_frame("confirm", 400)
    for event in detect_module_d_events(frame, "TEST"):
        assert event.evidence.get("research_proxy") is True
