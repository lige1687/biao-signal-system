"""模块 A（V2 重写版）状态机测试（规格 §9 / 账本 first_ma_pullback 3.x）。

夹具：几何上行日线（日增速 g=0.0012 -> s60 年化约 30%，时钟二类；
周线 20/60/120 双组多头排列在 120 个已完成周后成立），随后注入一段
受控回撤：跌破 EMA20、贴近 SMA20、再收复——覆盖 A1 门禁、A2 触碰
（1 x ATR(20) 口径）、A3（EMA20 收复 / 严格底部构造）、A4 两版入场、
首次 vs 非首次、A5 结构失效与生命周期重置。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.first_ma_pullback import (
    ENTRY_CONFIRMED,
    ENTRY_EARLY,
    SUB_RULE_CONFIRMED,
    SUB_RULE_FAILED,
    SUB_RULE_TOUCHED,
    detect_first_ma_pullback_events,
)
from lei_signal.rules.lei_color import classify_colors


def _uptrend_bars(
    pre_bars: int = 640,
    g: float = 0.0012,
    dip_depth: float = 0.05,
    dip_len: int = 8,
    recover_len: int = 4,
    crash_after: int | None = None,
) -> pd.DataFrame:
    closes = [100.0 * (1.0 + g) ** i for i in range(pre_bars)]
    base = closes[-1]
    for k in range(dip_len):
        factor = 1.0 - dip_depth * (k + 1) / dip_len
        closes.append(base * (1.0 + g) ** (k + 1) * factor)
    if recover_len > 0:
        closes.append(closes[-1] * 1.006)
        for _ in range(recover_len - 1):
            closes.append(closes[-1] * 1.004)
    if crash_after is not None:
        closes = closes[:crash_after]
        for _ in range(30):
            closes.append(closes[-1] * 0.94)  # 深跌：跌破 SMA120、排列破坏
    index = pd.bdate_range("2014-01-01", periods=len(closes))
    close = pd.Series(closes, index=index)
    return pd.DataFrame(
        {
            "open": close * 1.0005,
            "high": close * 1.004,
            "low": close * 0.996,
            "close": close,
            "volume": np.full(len(closes), 1e6),
        },
        index=index,
    )


def _frame(**kwargs) -> pd.DataFrame:
    return classify_colors(compute_features(_uptrend_bars(**kwargs)))


def _of(events: list, sub_rule: str, *, period: int | None = None, variant: str | None = None):
    return [
        e
        for e in events
        if e.evidence.get("sub_rule") == sub_rule
        and (period is None or e.evidence.get("ma_period") == period)
        and (variant is None or e.evidence.get("entry_variant") == variant)
    ]


def test_gate_and_first_touch_then_early_and_confirmed_entries() -> None:
    frame = _frame()
    events = detect_first_ma_pullback_events(frame, "TEST")
    touched = _of(events, SUB_RULE_TOUCHED, period=20)
    assert touched, "SMA20 应产生触碰事件"
    first = [e for e in touched if e.evidence["is_first_touch"]]
    assert first, "首个触碰必须标记 is_first=True"
    # 触碰口径：Low <= SMA20 + 1 x ATR(20)（evidence 记录带宽数值）
    first_event = first[0]
    band = first_event.evidence["band"]
    ma_value = first_event.evidence["ma_value"]
    assert band == ma_value + 1.0 * first_event.evidence["atr20"]

    early = _of(events, SUB_RULE_CONFIRMED, period=20, variant=ENTRY_EARLY)
    confirmed = _of(events, SUB_RULE_CONFIRMED, period=20, variant=ENTRY_CONFIRMED)
    assert early, "A4 早期版入场事件应产生"
    assert confirmed, "A4 确认版入场事件应产生"
    assert early[0].available_date <= confirmed[0].available_date
    # A3 来源应至少含 EMA20 收复或底部构造之一
    assert early[0].evidence["a3_source"] in ("ema20_reclaim", "bottom_structure")
    # A5：入场事件携带结构低点失效价，且不高于触碰日 low
    touch_low = float(frame.loc[pd.Timestamp(first_event.evidence["touch_date"]), "low"])
    assert early[0].evidence["stop_price"] <= touch_low


def test_non_first_touches_are_flagged_separately() -> None:
    events = detect_first_ma_pullback_events(_frame(), "TEST")
    touched = _of(events, SUB_RULE_TOUCHED, period=20)
    flags = [e.evidence["is_first_touch"] for e in touched]
    assert flags[0] is True
    assert False in flags, "同一生命周期内后续触碰应标记 is_first=False"


def test_first_flag_resets_per_ma() -> None:
    """SMA20 的首次与 SMA60 的首次相互独立（每条均线各自计数）。"""
    events = detect_first_ma_pullback_events(_frame(), "TEST")
    for period in (20, 60):
        firsts = [
            e
            for e in _of(events, SUB_RULE_TOUCHED, period=period)
            if e.evidence["is_first_touch"]
        ]
        assert len(firsts) >= 1


def test_lifecycle_reset_emits_failed_for_open_cycles() -> None:
    frame = _frame(crash_after=660)
    events = detect_first_ma_pullback_events(frame, "TEST")
    failed = _of(events, SUB_RULE_FAILED)
    assert failed, "深跌导致生命周期重置时，未完结回撤应出 failed 事件"
    assert any("生命周期重置" in str(e.evidence.get("failure_reason")) for e in failed)
    # 重置判据：收盘跌破 SMA120
    assert float(frame["close"].iloc[-1]) < float(frame["sma120"].iloc[-1])


def test_structure_failure_on_close_below_pullback_low() -> None:
    # 回撤后不反弹、继续创收盘新低：A5 结构低点被破坏
    frame = _frame(dip_depth=0.12, dip_len=20, recover_len=0)
    events = detect_first_ma_pullback_events(frame, "TEST")
    failed = _of(events, SUB_RULE_FAILED)
    assert any("结构低点" in str(e.evidence.get("failure_reason")) for e in failed)


def test_clock_type1_blocks_module_a() -> None:
    # 日增速 0.6% -> s60 年化约 150%，时钟一类（加速段）：无持仓不参与
    frame = _frame(g=0.006)
    assert detect_first_ma_pullback_events(frame, "TEST") == []


def test_appending_future_bars_does_not_change_past_events() -> None:
    full_frame = _frame()
    cut = len(full_frame) - 3
    prefix_frame = full_frame.iloc[:cut].copy()
    prefix_events = detect_first_ma_pullback_events(prefix_frame, "TEST")
    full_events = detect_first_ma_pullback_events(full_frame, "TEST")
    by_id = {e.event_id: e for e in full_events}
    for event in prefix_events:
        assert event.event_id in by_id
        assert event.available_date <= prefix_frame.index[-1].date()


def test_event_ids_deterministic() -> None:
    frame = _frame()
    again = detect_first_ma_pullback_events(frame, "TEST")
    first = detect_first_ma_pullback_events(frame, "TEST")
    assert [e.event_id for e in again] == [e.event_id for e in first]


def test_insufficient_columns_returns_empty() -> None:
    frame = pd.DataFrame({"close": [1.0, 2.0]})
    assert detect_first_ma_pullback_events(frame, "TEST") == []
