"""可交易性门禁与趋势类型分类（规格第 13 节，研究代理）门禁。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.rules.tradability_gate import (
    EXHAUSTION,
    INSUFFICIENT_DATA,
    RANGING,
    TRENDING,
    classify_trend_type,
    evaluate_tradability,
)


def _base_frame(rows: int = 160) -> pd.DataFrame:
    idx = pd.bdate_range("2023-01-02", periods=rows)
    i = np.arange(rows, dtype=float)
    return pd.DataFrame(
        {
            "open": 100.0 + i * 0.1,
            "high": 101.0 + i * 0.1,
            "low": 99.0 + i * 0.1,
            "close": 100.0 + i * 0.1,
            "volume": 1_000_000.0,
            "atr14": 2.0,
            "signal_color": "green",
            "volume_ratio20": 1.0,
        },
        index=idx,
    )


def _trending_frame(rows: int = 160) -> pd.DataFrame:
    """完整多头排列、均线展开（纠缠度>2%）、斜率向上 -> 趋势。"""
    df = _base_frame(rows)
    close = df["close"]
    df["sma20"] = close - 1.0
    df["sma60"] = close - 3.0
    df["sma120"] = close - 6.0
    df["ema20"] = close - 0.8
    df["ema60"] = close - 2.5
    df["ema120"] = close - 5.5
    df["ema20_slope"] = 0.3
    return df


def _ranging_frame(rows: int = 160) -> pd.DataFrame:
    """均线高度纠缠（<2%）、ATR 未压缩 -> 横盘反复。"""
    df = _base_frame(rows)
    df["close"] = 100.0  # 平台
    df["sma20"] = 99.95
    df["sma60"] = 100.0
    df["sma120"] = 100.05
    df["ema20"] = 99.96
    df["ema60"] = 100.0
    df["ema120"] = 100.04
    df["ema20_slope"] = 0.0
    df["atr14"] = 2.0  # 恒定 -> ATR 分位高，非压缩 -> 横盘反复（非末期）
    return df


def _exhaustion_frame(rows: int = 160) -> pd.DataFrame:
    """强加速 + 极端乖离（close 远高于 ema120）-> 加速衰竭。"""
    df = _base_frame(rows)
    close = 100.0 + np.arange(rows) * 0.7  # 陡升
    df["close"] = close
    df["sma20"] = close - 2.0
    df["sma60"] = close - 8.0
    df["sma120"] = 100.0  # 远低于 close -> 极端乖离
    df["ema20"] = close - 1.5
    df["ema60"] = close - 7.0
    df["ema120"] = 100.0
    df["ema20_slope"] = 7.0  # 大斜率 -> ema20_slope_pct >= 加速阈值
    return df


def test_trending_is_tradable() -> None:
    df = _trending_frame()
    pos = len(df) - 1
    assert classify_trend_type(df, pos) == TRENDING
    result = evaluate_tradability(df, pos)
    assert result.tradable
    assert result.blocking_reasons == []


def test_ranging_blocks_with_no_signature_action() -> None:
    df = _ranging_frame()
    pos = len(df) - 1
    assert classify_trend_type(df, pos) == RANGING
    result = evaluate_tradability(df, pos)
    assert not result.tradable
    assert any("横盘反复" in r for r in result.blocking_reasons)


def test_exhaustion_blocks() -> None:
    df = _exhaustion_frame()
    pos = len(df) - 1
    assert classify_trend_type(df, pos) == EXHAUSTION
    result = evaluate_tradability(df, pos)
    assert not result.tradable
    assert any("极端加速" in r for r in result.blocking_reasons)


def test_insufficient_data_blocks() -> None:
    df = _trending_frame(rows=160)
    pos = 50  # < 120
    assert classify_trend_type(df, pos) == INSUFFICIENT_DATA
    result = evaluate_tradability(df, pos)
    assert not result.tradable
    assert any("数据不足" in r or "趋势类型" in r for r in result.blocking_reasons)


def test_nine_conditions_all_present() -> None:
    df = _trending_frame()
    result = evaluate_tradability(df, len(df) - 1)
    codes = [c.code for c in result.condition_checks]
    assert len(codes) == 9


def test_appending_future_bars_does_not_change_past_tradability() -> None:
    df = _trending_frame(160)
    pos = 130
    early = evaluate_tradability(df.iloc[: pos + 1], pos)
    full = evaluate_tradability(df, pos)
    assert early.trend_type == full.trend_type
    assert early.tradable == full.tradable
    assert early.blocking_reasons == full.blocking_reasons
