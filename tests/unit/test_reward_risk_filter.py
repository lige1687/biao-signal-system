"""盈亏比计算（规格第 10 节，研究代理，只算不强制）门禁。"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lei_signal.domain.canonical import make_event_id
from lei_signal.domain.types import Direction, Pivot, Provenance, Severity, SignalEvent
from lei_signal.events.log import make_event
from lei_signal.research.reward_risk_backtest import build_reward_risk_backtest
from lei_signal.rules.first_ma_pullback import RULE_ID as PB_ID, SUB_RULE_CONFIRMED as PB_CONFIRMED
from lei_signal.rules.false_breakout_reclaim import (
    RULE_ID as FO_ID,
    SUB_RULE_CONFIRMED as FO_CONFIRMED,
)
from lei_signal.rules.reward_risk_filter import (
    TARGET_SWING_HIGH,
    TARGET_UNAVAILABLE,
    compute_reward_risk,
)


def _frame(rows: int = 100) -> pd.DataFrame:
    """先升后撤再创新高的路径，便于构造有目标/无目标两种入场。"""
    idx = pd.bdate_range("2025-01-02", periods=rows)
    n_up1 = 40
    n_down = 20
    n_up2 = rows - n_up1 - n_down
    close = np.concatenate([
        np.linspace(100.0, 130.0, n_up1),          # 0..39 升至 130（摆动高点）
        np.linspace(130.0, 95.0, n_down + 1)[1:],  # 40..59 回撤到 95（拉回底部）
        np.linspace(100.0, 140.0, n_up2 + 1)[1:],  # 60..99 升至 140（新高）
    ])
    close = close[:rows]
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=idx,
    )


def _swing_high_pivot(frame: pd.DataFrame, position: int, price: float) -> Pivot:
    day = frame.index[position].date()
    confirmed_day = frame.index[position + 3].date()
    return Pivot(
        kind="high",
        index=position,
        pivot_date=day,
        price=price,
        confirmed_index=position + 3,
        available_date=confirmed_day,
    )


def _pullback_entry(frame: pd.DataFrame, position: int, close: float, touch_position: int) -> SignalEvent:
    day = frame.index[position].date()
    return make_event(
        event_id=make_event_id(
            rule_id=PB_ID, rule_version="1.0.0", symbol="TEST",
            timeframe="1d", available_date=day, source_id=f"lc:{position}:confirmed",
        ),
        symbol="TEST", event_date=day, available_date=day,
        rule_id=PB_ID, rule_version="1.0.0",
        direction=Direction.BULLISH, severity=Severity.IMPORTANT, strength=75,
        reason_cn="x", provenance=Provenance.RESEARCH_PROXY,
        evidence={
            "sub_rule": PB_CONFIRMED, "ma_period": 20, "ma_value": 98.0,
            "close": close, "touch_date": frame.index[touch_position].date().isoformat(),
        },
    )


def _fo_entry(frame: pd.DataFrame, position: int, close: float, reference: float) -> SignalEvent:
    day = frame.index[position].date()
    return make_event(
        event_id=make_event_id(
            rule_id=FO_ID, rule_version="1.0.0", symbol="TEST",
            timeframe="1d", available_date=day, source_id=f"fo:{position}:confirmed",
        ),
        symbol="TEST", event_date=day, available_date=day,
        rule_id=FO_ID, rule_version="1.0.0",
        direction=Direction.BULLISH, severity=Severity.IMPORTANT, strength=75,
        reason_cn="x", provenance=Provenance.RESEARCH_PROXY,
        evidence={"sub_rule": FO_CONFIRMED, "reference_price": reference, "close": close},
    )


def test_swing_high_target_computes_reward_risk() -> None:
    frame = _frame()
    # 摆动高点在 position=39, price≈130，确认日 position=42 <= 入场日 60。
    pivots = (_swing_high_pivot(frame, 39, 130.0),)
    entry = _pullback_entry(frame, 60, close=100.0, touch_position=59)
    # touch 日(low≈94)作为失效价；目标 130；R/R=(130-100)/(100-94)=5
    result = compute_reward_risk(frame, entry, pivots)
    assert result.computable
    assert result.target_source == TARGET_SWING_HIGH
    assert result.target_b == 130.0
    assert result.reward_risk is not None and result.reward_risk > 0


def test_no_target_above_entry_is_not_computable() -> None:
    frame = _frame()
    # 入场在最后一天（全周期最高价），其上无任何已确认摆动高点/区间高点。
    last = len(frame) - 1
    entry_close = float(frame["close"].iloc[last])
    pivots = (_swing_high_pivot(frame, 39, 130.0),)  # 130 < entry_close
    entry = _fo_entry(frame, last, close=entry_close, reference=entry_close - 5.0)
    result = compute_reward_risk(frame, entry, pivots)
    assert not result.computable
    assert result.target_source == TARGET_UNAVAILABLE
    assert result.reward_risk is None


def test_stop_not_below_entry_is_not_computable() -> None:
    """失效价不低于入场价时风险非正，R/R 不可计算。"""
    frame = _frame()
    pivots = (_swing_high_pivot(frame, 39, 130.0),)
    # 失效价(105) > 入场价(100) -> 风险非正
    entry = _fo_entry(frame, 60, close=100.0, reference=105.0)
    result = compute_reward_risk(frame, entry, pivots)
    assert not result.computable
    assert result.reward_risk is None


def test_appending_future_bars_does_not_change_past_rr() -> None:
    """目标 B 只用信号日及此前已确认数据；追加未来行情不改变历史 R/R。"""
    frame = _frame(120)
    pivots = (_swing_high_pivot(frame, 39, 130.0),)
    entry = _pullback_entry(frame, 60, close=100.0, touch_position=59)
    cutoff = 80
    early = compute_reward_risk(frame.iloc[:cutoff], entry, pivots)
    full = compute_reward_risk(frame, entry, pivots)
    assert early.computable == full.computable
    assert early.reward_risk == full.reward_risk
    assert early.target_b == full.target_b
    assert early.target_source == full.target_source


def test_reward_risk_backtest_buckets() -> None:
    frame = _frame()
    pivots = (_swing_high_pivot(frame, 39, 130.0),)
    # 入场 A：close=100，touch low≈94，目标 130 -> R/R≈5（≥5，也 ≥3）
    entry_a = _pullback_entry(frame, 60, close=100.0, touch_position=59)
    # 入场 B：在全周期最高价，无目标 -> 不可计算
    last = len(frame) - 1
    entry_b = _fo_entry(frame, last, close=float(frame["close"].iloc[last]),
                        reference=float(frame["close"].iloc[last]) - 5.0)
    report = build_reward_risk_backtest(frame, [entry_a, entry_b], pivots)
    assert report is not None
    by_key = {side.key: side for side in report.sides}
    assert set(by_key) == {"rr_ge3", "rr_ge5", "rr_unknown"}
    assert by_key["rr_ge3"].total_signals == 1  # entry_a
    assert by_key["rr_ge5"].total_signals == 1  # entry_a
    assert by_key["rr_unknown"].total_signals == 1  # entry_b


def test_reward_risk_backtest_returns_none_without_entries() -> None:
    frame = _frame()
    assert build_reward_risk_backtest(frame, [], ()) is None
