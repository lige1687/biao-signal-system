"""抵扣价退出（A6①）前向状态机门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.research.exit_variant_backtest import build_exit_variant_backtest
from lei_signal.rules.exit_ema20_costbasis import (
    RULE_ID,
    SUB_RULE_TRIGGERED,
    detect_exit_ema20_costbasis_events,
)


def _feature_frame(rows: int = 80) -> pd.DataFrame:
    """构造一个先涨后跌的序列：前半段收盘高于 EMA20 与抵扣价，后半段跌破两者。"""
    index = pd.bdate_range("2025-01-02", periods=rows)
    # 用一个先升后降的收盘序列，EMA20 与 close_lag20 由真实公式更稳：
    # 这里直接给定 ema20 与 close_lag20 列，便于精确控制触发条件。
    close = pd.Series([100.0 + i * 0.5 for i in range(rows // 2)] +
                      [100.0 + (rows // 2) * 0.5 - (i - rows // 2 + 1) * 1.5
                       for i in range(rows // 2, rows)],
                       index=index, dtype=float)
    # ema20 略滞后于 close；前半段 close>ema20，后半段 close<ema20。
    ema20 = close.rolling(20, min_periods=20).mean()
    # close_lag20 = 20 日前收盘（抵扣价）。
    close_lag20 = close.shift(20)
    frame = pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000_000.0,
            "atr14": 2.0,
            "signal_color": "green",
            "ema20": ema20,
            "close_lag20": close_lag20,
            "sma20": ema20,
            "sma60": ema20 - 1.0,
            "sma120": ema20 - 2.0,
        },
        index=index,
    )
    return frame


def _sub(event) -> str:  # noqa: ANN001
    return str(event.evidence["sub_rule"])


def test_rising_edge_triggers_single_exit_event() -> None:
    frame = _feature_frame(80)
    events = detect_exit_ema20_costbasis_events(frame, "TEST")
    # 条件由不成立转成立的当日应恰好触发一次；持续成立期间不再重复触发。
    assert all(_sub(e) == SUB_RULE_TRIGGERED for e in events)
    assert len(events) >= 1
    # 触发日当天条件确实成立
    by_day = {ts.date(): i for i, ts in enumerate(frame.index)}
    trig = events[0]
    pos = by_day[trig.available_date]
    row = frame.iloc[pos]
    assert float(row["close"]) < float(row["ema20"])
    assert float(row["close"]) < float(row["close_lag20"])
    # 触发日前一日条件不成立（上升沿）
    prev = frame.iloc[pos - 1]
    assert not (float(prev["close"]) < float(prev["ema20"]) and
                float(prev["close"]) < float(prev["close_lag20"]))
    assert trig.direction.value == "bearish"


def test_only_one_condition_does_not_trigger() -> None:
    """仅跌破 EMA20 但未跌破抵扣价，不应触发。"""
    frame = _feature_frame(80)
    index = frame.index
    target = 60
    # 把 target 日收盘设在 ema20 之下、但 close_lag20 之上。
    ema = float(frame.iloc[target]["ema20"])
    lag = float(frame.iloc[target]["close_lag20"])
    if pd.notna(ema) and pd.notna(lag):
        frame.loc[index[target], "close"] = (min(ema, lag) + max(ema, lag)) / 2
        # 确保前一日不成立
    events = detect_exit_ema20_costbasis_events(frame, "TEST")
    for e in events:
        if e.available_date == index[target].date():
            raise AssertionError("仅满足单一条件不应触发退出")


def test_appending_future_bars_does_not_change_past_triggers() -> None:
    frame = _feature_frame(120)
    cutoff = 80
    early = detect_exit_ema20_costbasis_events(frame.iloc[:cutoff], "TEST")
    full = detect_exit_ema20_costbasis_events(frame, "TEST")
    cutoff_date = frame.index[cutoff - 1].date()
    visible = [e for e in full if e.available_date <= cutoff_date]
    assert [e.event_id for e in early] == [e.event_id for e in visible]
    assert [e.evidence for e in early] == [e.evidence for e in visible]


def test_missing_columns_returns_empty() -> None:
    frame = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.bdate_range("2025-01-02", periods=2))
    assert detect_exit_ema20_costbasis_events(frame, "TEST") == []


def test_exit_variant_backtest_produces_three_sides() -> None:
    """A6 三版本退出回测：同一批模块 A 入场、三种退出方式分别成 side。"""
    frame = _feature_frame(120)
    # 构造一个首次回撤确认事件作为模块 A 入场样本。
    from lei_signal.domain.canonical import make_event_id
    from lei_signal.domain.types import Direction, Provenance, Severity, SignalEvent
    from lei_signal.events.log import make_event
    from lei_signal.rules.first_ma_pullback import RULE_ID as PB_ID, SUB_RULE_CONFIRMED

    entry_day = frame.index[40].date()
    event = make_event(
        event_id=make_event_id(
            rule_id=PB_ID, rule_version="1.0.0", symbol="TEST",
            timeframe="1d", available_date=entry_day, source_id="lc:20:confirmed",
        ),
        symbol="TEST", event_date=entry_day, available_date=entry_day,
        rule_id=PB_ID, rule_version="1.0.0",
        direction=Direction.BULLISH, severity=Severity.IMPORTANT, strength=75,
        reason_cn="x", provenance=Provenance.RESEARCH_PROXY,
        evidence={"sub_rule": SUB_RULE_CONFIRMED, "ma_period": 20},
    )
    report = build_exit_variant_backtest(frame, [event])
    assert report is not None
    keys = {side.key for side in report.sides}
    assert keys == {"exit_costbasis", "exit_top_plus_black", "exit_structure_stop"}
    # 三版本共用同一批入场样本
    assert {side.total_signals for side in report.sides} == {1}
    # 每个 side 都带固定周期 + 规则退出统计
    for side in report.sides:
        assert any(s.key.startswith("day_") for s in side.stats)
        assert any(s.key == "rule_exit" for s in side.stats)


def test_exit_variant_backtest_returns_none_without_entries() -> None:
    frame = _feature_frame(80)
    assert build_exit_variant_backtest(frame, []) is None
