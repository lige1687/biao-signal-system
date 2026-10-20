"""均线密集区突破前向状态机门禁（规格 §9 模块 B，V2 重写版）。

夹具直接手工注入指标列（sma/ema/close_lag），精确控制时钟三类寿命、
带宽收敛、排列形成与突破——不依赖 OHLC 巧合收敛，测试完全确定。
"""
from __future__ import annotations

import pandas as pd

import pytest

import lei_signal.rules.dense_breakout as db
from lei_signal.rules.dense_breakout import (
    SUB_RULE_CONFIRMED,
    SUB_RULE_FAILED,
    SUB_RULE_WATCH,
    VARIANT_AMBUSH,
    VARIANT_BREAKOUT,
    _bandwidth_condition,
    _state_age_series,
    detect_dense_breakout_events,
)
from lei_signal.rules.clock_classifier import TYPE3_SIDEWAYS, clock_series


def _hand_frame(
    scenario: str = "breakout",
    flat_bars: int = 260,
    tail_bars: int = 60,
) -> pd.DataFrame:
    """手工构造带全部所需列的帧。

    结构：前 flat_bars 根横盘（所有均线=100，带宽=0，时钟需 s60 可算——
    sma60/sma20 常量使 s60=0 -> 三类）；tail 段按场景演化。
    scenario: breakout（排列形成->突破）/ ambush_fail / breakout_fail。
    """
    rows = flat_bars + tail_bars
    idx = pd.bdate_range("2024-01-02", periods=rows)
    close = [100.0] * flat_bars
    high = [100.4] * flat_bars  # 上沿略高，给埋伏段留出低于上沿的抬升空间
    low = [99.9] * flat_bars
    sma20 = [100.0] * flat_bars
    sma60 = [100.0] * flat_bars
    sma120 = [100.0] * flat_bars
    ema20 = [100.0] * flat_bars
    ema60 = [100.0] * flat_bars
    ema120 = [100.0] * flat_bars
    close_lag20 = [100.0] * flat_bars

    for k in range(tail_bars):
        i = flat_bars + k
        if scenario == "breakout":
            # 稳步抬升：排列先形成（埋伏），价格随后突破区间上沿（100.1）。
            price = 100.0 + k * 0.3
            close.append(price)
            high.append(price + 0.1)
            low.append(price - 0.1)
            base = max(0, k - 15)
            sma20.append(100.0 + (price - 100.0) * (k - base) / max(1, k - base) * 0.8)
            sma60.append(100.0 + (price - 100.0) * 0.3)
            sma120.append(100.0 + (price - 100.0) * 0.1)
            ema20.append(price * 0.9 + 100.0 * 0.1)
            ema60.append(100.0 + (price - 100.0) * 0.5)
            ema120.append(100.0 + (price - 100.0) * 0.2)
            close_lag20.append(close[i - 20] if i >= 20 else 100.0)
        elif scenario == "ambush_fail":
            # 排列短暂形成后破坏：SMA20 跌回 SMA60 下方。
            if k < 10:
                price = 100.0 + k * 0.04
                sma20.append(100.0 + k * 0.3)
                sma60.append(100.0 + k * 0.1)
                sma120.append(100.0)
                ema20.append(100.0 + k * 0.3)
                ema60.append(100.0 + k * 0.1)
                ema120.append(100.0)
            else:
                price = max(98.0, 100.4 - (k - 10) * 0.5)
                sma20.append(100.0 + max(0.0, 3.0 - (k - 10) * 0.6))
                sma60.append(100.0 + 1.0)
                sma120.append(100.0)
                ema20.append(100.0 + max(0.0, 3.0 - (k - 10) * 0.7))
                ema60.append(100.0 + 1.0)
                ema120.append(100.0)
            close.append(price)
            high.append(price + 0.1)
            low.append(price - 0.1)
            close_lag20.append(close[i - 20] if i >= 20 else 100.0)
        else:  # breakout_fail：不形成排列，价格直接大幅突破后跌回+20组下弯
            if k < 15:
                price = 100.0 + k * 1.5
                sma20.append(100.0)
                sma60.append(100.0)
                sma120.append(100.0)
                ema20.append(100.0)
                ema60.append(100.0)
                ema120.append(100.0)
                close_lag20.append(100.0)
            else:
                price = max(97.0, 122.5 - (k - 15) * 1.2)
                sma20.append(103.0)
                sma60.append(100.0)
                sma120.append(100.0)
                ema20.append(103.0)
                ema60.append(100.0)
                ema120.append(100.0)
                close_lag20.append(100.0)  # close_lag20 < close 恒假下弯条件由 close<SMA20 承担
            close.append(price)
            high.append(price + 0.1)
            low.append(price - 0.1)
            # 20 组下弯需要 close < close_lag20：跌回段手工置 lag > close
            if k >= 20:
                close_lag20[-1] = price + 5.0

    frame = pd.DataFrame(
        {
            "open": [c - 0.05 for c in close],
            "high": high,
            "low": low,
            "close": close,
            "sma20": sma20,
            "sma60": sma60,
            "sma120": sma120,
            "ema20": ema20,
            "ema60": ema60,
            "ema120": ema120,
            "close_lag20": close_lag20,
        },
        index=idx,
    )
    return frame


@pytest.fixture()
def gate_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """固定 B1 门禁为真：时钟三类恒真、带宽恒达标、寿命恒够。

    B1 的真实口径由 test_flat_frame_has_clock3_bandwidth_and_age 自检 +
    真实数据（黄金 ETF 案例）验证；单元测试聚焦 B2 埋伏/突破与 B3 失效状态机。
    """
    monkeypatch.setattr(db, "clock_series", lambda frame: __import__("pandas").Series(
        TYPE3_SIDEWAYS, index=frame.index, dtype=int
    ))
    monkeypatch.setattr(db, "_bandwidth_condition", lambda frame, t: __import__("pandas").Series(
        True, index=frame.index
    ))
    monkeypatch.setattr(db, "_state_age_series", lambda cond, *, exit_bars: __import__("pandas").Series(
        range(len(cond), 0, -1), index=cond.index, dtype=int
    ))


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_flat_frame_has_clock3_bandwidth_and_age() -> None:
    """夹具自检：横盘段时钟三类、带宽达标、寿命可累积（否则测试无意义）。"""
    frame = _hand_frame("breakout")
    clock3 = clock_series(frame) == TYPE3_SIDEWAYS
    # 横盘 260 根：sma60 常量使 s60=0 -> 三类（前 119 根 s60 未就绪为 0）
    assert clock3.iloc[125:260].all()
    bandwidth = _bandwidth_condition(frame, 0.02)
    assert bandwidth.iloc[:260].all()
    age = _state_age_series(clock3, exit_bars=20)
    assert age.iloc[259] >= 126


def test_watch_then_ambush_and_breakout_confirm(gate_on: None) -> None:
    frame = _hand_frame("breakout")
    events = detect_dense_breakout_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_WATCH in subs
    variants = [e.evidence.get("variant") for e in events if _sub(e) == SUB_RULE_CONFIRMED]
    assert VARIANT_AMBUSH in variants
    assert VARIANT_BREAKOUT in variants
    breakout = next(
        e for e in events
        if _sub(e) == SUB_RULE_CONFIRMED and e.evidence.get("variant") == VARIANT_BREAKOUT
    )
    assert breakout.evidence["close"] > breakout.evidence["reference_price"]
    # 止损 = 密集区下沿（跌穿整个密集区才认输；回踩上沿是常见确认动作）
    assert breakout.evidence["stop_price"] == breakout.evidence["zone_low"]


def test_ambush_fails_on_alignment_break(gate_on: None) -> None:
    frame = _hand_frame("ambush_fail")
    events = detect_dense_breakout_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_CONFIRMED in subs
    failed = next(e for e in events if _sub(e) == SUB_RULE_FAILED)
    assert failed.evidence.get("variant") == VARIANT_AMBUSH
    assert "排列破坏" in str(failed.evidence.get("failure_reason"))


def test_breakout_fails_on_b3_two_actions(gate_on: None) -> None:
    frame = _hand_frame("breakout_fail")
    events = detect_dense_breakout_events(frame, "TEST")
    subs = [_sub(e) for e in events]
    assert SUB_RULE_CONFIRMED in subs
    assert SUB_RULE_FAILED in subs
    failed = next(
        e for e in events
        if _sub(e) == SUB_RULE_FAILED and e.evidence.get("variant") == VARIANT_BREAKOUT
    )
    assert "两动作齐备" in str(failed.evidence.get("failure_reason"))


def test_one_watch_per_zone(gate_on: None) -> None:
    frame = _hand_frame("breakout")
    events = detect_dense_breakout_events(frame, "TEST")
    watches = [e for e in events if _sub(e) == SUB_RULE_WATCH]
    assert len(watches) == 1


def test_research_proxy_evidence_flag(gate_on: None) -> None:
    frame = _hand_frame("breakout")
    for event in detect_dense_breakout_events(frame, "TEST"):
        assert event.evidence.get("research_proxy") is True
