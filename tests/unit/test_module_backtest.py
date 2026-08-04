"""按 A/B/C/D 交易模块分别统计（规格第 12 节）门禁。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.types import Direction, Provenance, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.research.module_backtest import (
    MODULE_MAP,
    build_module_backtest,
    module_of,
)
from lei_signal.rules.false_breakout_reclaim import (
    RULE_ID as FO_ID,
    SUB_RULE_CONFIRMED as FO_CONFIRMED,
)
from lei_signal.rules.first_ma_pullback import (
    RULE_ID as PB_ID,
    SUB_RULE_CONFIRMED as PB_CONFIRMED,
)


def _frame(rows: int = 80) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-02", periods=rows)
    close = pd.Series(100.0 + pd.Series(range(rows)) * 0.1, index=idx)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=idx,
    )


def _entry(rule_id: str, sub_rule: str, frame: pd.DataFrame, position: int) -> SignalEvent:
    day = frame.index[position].date()
    return make_event(
        event_id=make_event_id(
            rule_id=rule_id, rule_version="1.0.0", symbol="TEST",
            timeframe="1d", available_date=day, source_id=f"{rule_id}:{position}:confirmed",
        ),
        symbol="TEST", event_date=day, available_date=day,
        rule_id=rule_id, rule_version="1.0.0",
        direction=Direction.BULLISH, severity=Severity.IMPORTANT, strength=75,
        reason_cn="x", provenance=Provenance.RESEARCH_PROXY,
        evidence={"sub_rule": sub_rule},
    )


def test_module_attribution() -> None:
    assert module_of("first_ma_pullback") == "A"
    assert module_of("false_breakout_reclaim") == "D"
    assert module_of("not_a_rule") is None
    # B/C 待实现，不在映射中
    assert "dense_breakout" not in MODULE_MAP
    assert "two_b_reversal" not in MODULE_MAP


def test_module_backtest_groups_by_module_and_category() -> None:
    frame = _frame(80)
    # 模块 A 两个入场、模块 D 一个入场
    events = [
        _entry(PB_ID, PB_CONFIRMED, frame, 30),
        _entry(PB_ID, PB_CONFIRMED, frame, 50),
        _entry(FO_ID, FO_CONFIRMED, frame, 60),
    ]
    report = build_module_backtest(frame, events)
    assert report is not None
    by_key = {side.key: side for side in report.sides}
    # 模块级分桶
    assert by_key["module_A"].total_signals == 2
    assert by_key["module_D"].total_signals == 1
    # 大类汇总：趋势跟随=A（B 空），逆势反转=D（C 空）
    assert by_key["category_trend_following"].total_signals == 2
    assert by_key["category_reversal"].total_signals == 1
    # 每个分桶都带固定周期统计
    for side in report.sides:
        assert any(s.key.startswith("day_") for s in side.stats)


def test_module_separation_no_cross_rewrite() -> None:
    """A 回调与 D 假突破分桶隔离，不在同一笔交易中改写理由（规格12）。"""
    frame = _frame(80)
    events = [
        _entry(PB_ID, PB_CONFIRMED, frame, 30),
        _entry(FO_ID, FO_CONFIRMED, frame, 60),
    ]
    report = build_module_backtest(frame, events)
    assert report is not None
    by_key = {side.key: side for side in report.sides}
    # A 桶只含 A，D 桶只含 D，互不串写
    assert by_key["module_A"].total_signals == 1
    assert by_key["module_D"].total_signals == 1
    assert "改写理由" in report.research_disclaimer_cn


def test_module_backtest_returns_none_without_entries() -> None:
    frame = _frame(80)
    assert build_module_backtest(frame, []) is None
