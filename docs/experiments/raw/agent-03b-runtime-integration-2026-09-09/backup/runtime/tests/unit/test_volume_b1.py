"""修复 7：量能拆分为 volume_up_surge / breakout_volume，B1 真实两年窗口。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.features.indicators import compute_features
from lei_signal.rules.resistance_b1 import _lookback_days, find_b1
from lei_signal.rules.volume import compute_volume_labels, detect_volume_events


def _bars(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.0, rows),
            "low": close - rng.uniform(0.3, 1.0, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=rows),
    )


def test_volume_up_surge_does_not_require_neckline() -> None:
    """修复 7.1：volume_up_surge 不要求结构颈线；breakout_volume 必须有结构颈线。"""
    bars = _bars(300, seed=7)
    # 注入放量上行：先改 close 让 rising 成立
    bars.iloc[150, bars.columns.get_loc("close")] = 120.0
    bars.iloc[149, bars.columns.get_loc("close")] = 110.0
    high_vol = bars["volume"].copy()
    high_vol.iloc[150] = bars["volume"].iloc[150] * 5
    bars["volume"] = high_vol

    frame = compute_features(bars)
    frame = compute_volume_labels(frame)
    assert frame["volume_up_surge"].iloc[150], "放量上行应被识别"

    events = detect_volume_events(frame, "TEST", structure_necklines={})
    sub_rules = {e.evidence["sub_rule"] for e in events}
    assert "breakout_volume" not in sub_rules, "无结构颈线时不应产生 breakout_volume"
    assert "volume_up_surge" in sub_rules


def test_breakout_volume_requires_neckline() -> None:
    """修复 7.1：breakout_volume 必须有结构颈线 + 量比阈值。"""
    bars = _bars(300, seed=7)
    bars.iloc[200, bars.columns.get_loc("close")] = 120.0
    bars.iloc[199, bars.columns.get_loc("close")] = 110.0
    high_vol = bars["volume"].copy()
    high_vol.iloc[200] = bars["volume"].iloc[200] * 5
    bars["volume"] = high_vol

    frame = compute_features(bars)
    frame = compute_volume_labels(frame)
    ts = frame.index[200]
    events = detect_volume_events(
        frame, "TEST",
        structure_necklines={ts: {"neckline": 119.0, "structure_id": "s-1"}},
    )
    brk = [e for e in events if e.evidence["sub_rule"] == "breakout_volume"]
    assert brk, "放量突破事件应被记录"
    assert brk[0].structure_id == "s-1"
    assert "颈线" in brk[0].reason_cn


def test_pullback_shrink_is_a_simple_rolling_proxy() -> None:
    """修复 7.2：pullback_shrink 是简单滚动代理，不是真正的趋势分段。"""
    bars = _bars(100, seed=11)
    # 强制下跌段 + 缩量
    bars.iloc[40:60, bars.columns.get_loc("close")] = 100 - np.arange(20) * 0.5
    bars.iloc[40:43, bars.columns.get_loc("volume")] = 2_000_000.0
    bars.iloc[57:60, bars.columns.get_loc("volume")] = 1_000_000.0
    frame = compute_features(bars)
    frame = compute_volume_labels(frame)
    assert "pullback_shrink" in frame.columns
    assert frame["pullback_shrink"].any()


def test_b1_uses_real_two_year_window() -> None:
    """修复 7.3：B1 默认窗口 = 真实过去两年（≈ 730 自然日）。"""
    days = _lookback_days()
    assert 365 * 2 <= days <= 366 * 2, f"B1 窗口必须约为 730 天，实际 {days}"
    assert get_rule("resistance_b1").param("lookback_years") == 2


def test_b1_excludes_pivots_older_than_two_years() -> None:
    """修复 7.3：早于两年前的摆动点不参与 B1 计算。"""
    from datetime import date, timedelta

    from lei_signal.domain.types import Pivot
    as_of = date(2025, 6, 30)
    recent_pivot = Pivot(
        kind="high", index=100, pivot_date=as_of - timedelta(days=400),
        price=120.0, confirmed_index=103,
        available_date=as_of - timedelta(days=395),
    )
    ancient_pivot = Pivot(
        kind="high", index=10, pivot_date=as_of - timedelta(days=800),
        price=125.0, confirmed_index=13,
        available_date=as_of - timedelta(days=795),
    )
    b1 = find_b1((ancient_pivot, recent_pivot), as_of=as_of, current_close=100.0)
    assert b1 is not None
    assert b1.pivot_date == as_of - timedelta(days=400)
    assert b1.price == 120.0


def test_b1_rule_ledger_lists_lookback_years() -> None:
    """规则账本与代码必须一致使用 lookback_years。"""
    assert get_rule("resistance_b1").param("lookback_years") == 2
