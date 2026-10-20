"""2B/破底翻前向状态机门禁（规格 §9 模块 C，V2 重写版 C1 结构）。

V2 C1：L1 = 前低（已确认摆动低点），跌破 L1 创新低 L2（无需摆动确认），
two_b_reclaim_bars 根内收回 L1 上方 = 破底翻；收盘跌破 L2 彻底失效。

夹具：上行 -> 回踩形成摆动低点 L1（左3右3 确认）-> 跌破 L1 创新低 -> 收回。
scenario：reclaim（收回+三版本）/ timeout（窗口耗尽）/ l2_break（跌破新低）/
downtrend（单边下行无收回机会）。
"""
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


def _feature_frame(scenario: str = "reclaim", rows: int = 240) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=rows)
    p = np.zeros(rows)

    if scenario == "downtrend":
        for i in range(rows):
            p[i] = 200.0 - i * 0.4
    else:
        # 上行段
        for i in range(140):
            p[i] = 100 + i * 0.2
        # 回踩形成 L1（低点后反弹 6+ 根，左3右3 可确认）
        for i in range(140, 150):
            p[i] = 128.0 - (i - 140) * 1.0
        p[150] = 118.0  # L1 摆动低点
        for i in range(151, 162):
            p[i] = 118.0 + (i - 150) * 0.8
        if scenario == "reclaim":
            # 浅坑跌破 L1（新低但不收盘穿坑底），3 根内收回，随后走强。
            p[162] = 117.0   # close < L1(low 117.8) -> 破位（low 116.8）
            p[163] = 117.2   # 回稳（收盘不低于昨日坑底）
            p[164] = 118.5   # 收回 L1 上方 -> v1 确认
            for i in range(165, rows):
                p[i] = p[i - 1] + 0.7
        elif scenario == "timeout":
            # 跌破后长期低位徘徊（>5 根不收回、不穿坑底）。
            for i in range(162, rows):
                p[i] = 117.0 + ((i - 162) % 3) * 0.2
        elif scenario == "l2_break":
            # 跌破后收盘穿过坑底（跌破 L2）。
            p[162] = 117.0
            p[163] = 116.0
            for i in range(164, rows):
                p[i] = 116.0 - (i - 164) * 0.8

    close = pd.Series(p, index=idx, dtype=float)
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


def test_reclaim_confirms_v1_then_v2_v3() -> None:
    frame = _feature_frame("reclaim", 240)
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = _subs(events)
    assert SUB_RULE_V1 in subs
    v1 = next(e for e in events if str(e.evidence["sub_rule"]) == SUB_RULE_V1)
    # C1：L2 是破位期间新低（无需摆动确认），作为失效线与止损。
    assert v1.evidence["l2_price"] < v1.evidence["l1_price"]
    assert v1.evidence["stop_price"] == v1.evidence["l2_price"]
    assert 0 < v1.evidence["bars_to_reclaim"] <= 5
    # 走强后 v2/v3 后置确认。
    assert SUB_RULE_V2 in subs
    assert SUB_RULE_V3 in subs


def test_timeout_fails() -> None:
    frame = _feature_frame("timeout", 240)
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = _subs(events)
    assert SUB_RULE_FAILED in subs
    assert subs.count(SUB_RULE_V1) == 0


def test_l2_break_fails() -> None:
    frame = _feature_frame("l2_break", 240)
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = _subs(events)
    assert SUB_RULE_FAILED in subs
    failed = next(e for e in events if str(e.evidence["sub_rule"]) == SUB_RULE_FAILED)
    assert "L2" in str(failed.evidence.get("failure_reason"))


def test_downtrend_no_confirmations() -> None:
    frame = _feature_frame("downtrend", 240)
    events = detect_two_b_reversal_events(frame, "TEST")
    subs = _subs(events)
    assert SUB_RULE_V1 not in subs


def test_each_l1_consumed_once() -> None:
    frame = _feature_frame("reclaim", 240)
    events = detect_two_b_reversal_events(frame, "TEST")
    v1_events = [e for e in events if str(e.evidence["sub_rule"]) == SUB_RULE_V1]
    lifecycles = [e.lifecycle_id for e in v1_events]
    assert len(lifecycles) == len(set(lifecycles)), "同一 L1 生命周期只允许一次 v1 确认"


def test_appending_future_bars_preserves_history() -> None:
    full = _feature_frame("reclaim", 240)
    cut = 200
    prefix = detect_two_b_reversal_events(full.iloc[:cut], "TEST")
    whole = detect_two_b_reversal_events(full, "TEST")
    by_id = {e.event_id: e for e in whole}
    for event in prefix:
        assert event.event_id in by_id
        assert event.available_date <= full.index[cut - 1].date()
