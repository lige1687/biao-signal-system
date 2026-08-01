"""Phase 1 门禁：指标、三色、复权校验与代码标准化。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.data.symbols import Market, eastmoney_secid, normalize_symbol, resolve_symbol
from lei_signal.data.validation import DataUnavailableError, detect_unadjusted_gaps, validate_bars
from lei_signal.features.indicators import (
    average_true_range,
    compute_features,
    seeded_ema,
    true_range,
)
from lei_signal.rules.lei_color import (
    REASON_BLACK,
    REASON_GRAY,
    REASON_GREEN,
    REASON_UNKNOWN,
    classify_colors,
    color_runs,
)

# ---------------- 代码标准化 ----------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" qqq ", "QQQ"),
        ("aapl", "AAPL"),
        ("159915", "159915.SZ"),
        ("510300", "510300.SS"),
        ("600519", "600519.SS"),
        ("000001", "000001.SZ"),
        ("0700.hk", "0700.HK"),
        ("159915.SZ", "159915.SZ"),
    ],
)
def test_normalize_symbol(raw: str, expected: str) -> None:
    assert normalize_symbol(raw) == expected


def test_empty_symbol_is_rejected_with_chinese_message() -> None:
    with pytest.raises(ValueError, match="请输入股票或ETF代码"):
        normalize_symbol("  ")


def test_market_and_timezone_are_resolved() -> None:
    assert resolve_symbol("159915").market is Market.CN_SZ
    assert resolve_symbol("510300").market is Market.CN_SH
    assert resolve_symbol("QQQ").timezone == "America/New_York"
    assert resolve_symbol("0700.HK").timezone == "Asia/Hong_Kong"
    assert resolve_symbol("159915").market_cn == "深市"


def test_eastmoney_secid_maps_exchange_prefix() -> None:
    """沪市 market=1，深市 market=0。"""
    assert eastmoney_secid(resolve_symbol("510300")) == "1.510300"
    assert eastmoney_secid(resolve_symbol("159915")) == "0.159915"
    with pytest.raises(ValueError, match="不是 A 股"):
        eastmoney_secid(resolve_symbol("QQQ"))


# ---------------- EMA / SMA ----------------


def test_seeded_ema_uses_first_window_sma_then_recursive_formula() -> None:
    close = pd.Series([float(i) for i in range(1, 22)])
    ema = seeded_ema(close, period=20)
    seed = sum(range(1, 21)) / 20
    expected_next = (2 / 21) * 21 + (19 / 21) * seed
    assert ema.iloc[:19].isna().all()
    assert ema.iloc[19] == pytest.approx(seed)
    assert ema.iloc[20] == pytest.approx(expected_next)


def test_features_need_21_bars_for_color_inputs() -> None:
    frame = pd.DataFrame(
        {
            "open": range(1, 22),
            "high": range(1, 22),
            "low": range(1, 22),
            "close": range(1, 22),
            "volume": [1000] * 21,
        },
        index=pd.bdate_range("2024-01-02", periods=21),
    )
    result = compute_features(frame)
    assert result["sma20"].iloc[19] == pytest.approx(10.5)
    assert pd.isna(result["close_lag20"].iloc[19])
    assert result["close_lag20"].iloc[20] == 1


# ---------------- ATR（移植旧测试向量）----------------


def _atr_frame(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    """(high, low, close) -> DataFrame。"""
    data = [
        {"open": float(low), "high": float(high), "low": float(low),
         "close": float(close), "volume": 1000.0}
        for high, low, close in rows
    ]
    return pd.DataFrame(data, index=pd.bdate_range("2024-01-02", periods=len(rows)))


def test_true_range_and_atr_match_ported_vectors() -> None:
    """移植向量来源：licai@a25eae9 tests/unit/indicators/test_core_indicators.py

    原向量为 Decimal：true_ranges == (None, 3, 4.5)，ATR(period=2) == (None, None, 3.75)。
    新实现使用 float，因此以 approx 比较。
    """
    frame = _atr_frame([("11", "9", "10"), ("13", "11", "12"), ("12.5", "8", "9")])
    ranges = true_range(frame)
    assert pd.isna(ranges.iloc[0])
    assert ranges.iloc[1] == pytest.approx(3.0)
    assert ranges.iloc[2] == pytest.approx(4.5)

    atr = average_true_range(frame, period=2)
    assert pd.isna(atr.iloc[0])
    assert pd.isna(atr.iloc[1])
    assert atr.iloc[2] == pytest.approx(3.75)


def test_atr_rejects_invalid_bars_and_period() -> None:
    bad = pd.DataFrame(
        {"open": [9.5], "high": [9.0], "low": [10.0], "close": [9.5], "volume": [1.0]},
        index=pd.bdate_range("2024-01-02", periods=1),
    )
    with pytest.raises(ValueError, match="high < low"):
        true_range(bad)
    with pytest.raises(ValueError, match="必须为正"):
        average_true_range(_atr_frame([("11", "9", "10")]), period=0)


# ---------------- 三色 ----------------


def _color_frame(rows: list[tuple[float, float | None, float | None]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["close", "ema20", "close_lag20"],
        index=pd.bdate_range("2024-01-02", periods=len(rows)),
    )


def test_classifies_green_black_gray_and_unknown() -> None:
    frame = _color_frame(
        [
            (10.0, None, None),   # 数据不足
            (12.0, 11.0, 9.0),    # 绿
            (8.0, 9.0, 10.0),     # 黑
            (10.0, 9.0, 11.0),    # 灰：高于EMA20但低于20日前
            (10.0, 10.0, 10.0),   # 灰：相等
        ]
    )
    result = classify_colors(frame)
    assert result["signal_color"].tolist() == ["unknown", "green", "black", "gray", "gray"]
    assert result["signal_reason"].iloc[0] == REASON_UNKNOWN
    assert result["signal_reason"].iloc[1] == REASON_GREEN
    assert result["signal_reason"].iloc[2] == REASON_BLACK
    assert result["signal_reason"].iloc[3] == REASON_GRAY


def test_equal_values_are_gray_not_green_or_black() -> None:
    """严格不等号：相等必须落入灰色。"""
    frame = _color_frame([(10.0, 10.0, 9.0), (10.0, 9.0, 10.0), (10.0, 10.0, 10.0)])
    assert classify_colors(frame)["signal_color"].tolist() == ["gray", "gray", "gray"]


def test_first_20_bars_are_unknown_not_gray() -> None:
    """门禁 4：前 20 根三色状态必须为未知，不得误标灰色。"""
    frame = pd.DataFrame(
        {
            "open": np.arange(1.0, 41.0),
            "high": np.arange(1.0, 41.0) + 0.5,
            "low": np.arange(1.0, 41.0) - 0.5,
            "close": np.arange(1.0, 41.0),
            "volume": [1000.0] * 40,
        },
        index=pd.bdate_range("2024-01-02", periods=40),
    )
    result = classify_colors(compute_features(frame))
    assert result["signal_color"].iloc[:20].tolist() == ["unknown"] * 20
    assert "unknown" not in result["signal_color"].iloc[20:].tolist()


def test_black_matches_strict_formula_day_by_day() -> None:
    """门禁 5：黑色必须逐日等价于 Close < EMA20 and Close < Close(t-20)。"""
    rng = np.random.default_rng(20260801)
    close = 100 + np.cumsum(rng.normal(0, 1.5, 300))
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": rng.integers(1_000, 10_000, 300).astype(float),
        },
        index=pd.bdate_range("2023-01-02", periods=300),
    )
    result = classify_colors(compute_features(frame))
    ready = result[["close", "ema20", "close_lag20"]].notna().all(axis=1)
    expected_black = ready & (result["close"] < result["ema20"]) & (
        result["close"] < result["close_lag20"]
    )
    actual_black = result["signal_color"].eq("black")
    assert actual_black.tolist() == expected_black.tolist()
    # 绿色同样逐日核对
    expected_green = ready & (result["close"] > result["ema20"]) & (
        result["close"] > result["close_lag20"]
    )
    assert result["signal_color"].eq("green").tolist() == expected_green.tolist()


def test_color_runs_compress_consecutive_days() -> None:
    """连续同色压缩为一个区段，供「连续绿色只算一次」使用。"""
    frame = _color_frame(
        [
            (12.0, 11.0, 9.0),
            (13.0, 11.5, 9.5),
            (8.0, 9.0, 10.0),
            (7.0, 9.0, 10.0),
            (7.5, 9.0, 10.0),
        ]
    )
    runs = color_runs(classify_colors(frame))
    assert runs["color"].tolist() == ["green", "black"]
    assert runs["bars"].tolist() == [2, 3]


# ---------------- 行情校验 ----------------


def _valid_bars(rows: int = 30) -> pd.DataFrame:
    close = np.linspace(10.0, 20.0, rows)
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": [1_000_000.0] * rows,
        },
        index=pd.bdate_range("2024-01-02", periods=rows),
    )


def test_validate_bars_sorts_and_deduplicates() -> None:
    frame = _valid_bars(25)
    shuffled = pd.concat([frame.iloc[10:], frame.iloc[:10], frame.iloc[[5]]])
    bars, report = validate_bars(shuffled, symbol="TEST", provider="fake", adjusted=True)
    assert bars.index.is_monotonic_increasing
    assert not bars.index.has_duplicates
    assert report.duplicates_removed == 1
    assert report.adjusted is True
    assert report.is_sufficient_for_color


def test_validate_bars_rejects_illegal_ohlc_instead_of_silently_dropping() -> None:
    """数据错误不得静默处理为「无信号」。"""
    frame = _valid_bars(25)
    frame.iloc[5, frame.columns.get_loc("high")] = 0.5   # high < low
    with pytest.raises(DataUnavailableError, match="非法 OHLC"):
        validate_bars(frame, symbol="TEST", provider="fake", adjusted=True)


def test_validate_bars_reports_data_unavailable_for_empty_and_short() -> None:
    with pytest.raises(DataUnavailableError, match="没有找到"):
        validate_bars(pd.DataFrame(), symbol="TEST", provider="fake", adjusted=True)
    with pytest.raises(DataUnavailableError, match="至少需要 21 根"):
        validate_bars(_valid_bars(5), symbol="TEST", provider="fake", adjusted=True, min_rows=21)
    assert DataUnavailableError.code == "DATA_UNAVAILABLE"


def test_unadjusted_data_produces_explicit_warning() -> None:
    _, report = validate_bars(_valid_bars(25), symbol="T", provider="fake", adjusted=False)
    assert any("未复权" in warning for warning in report.warnings)


def test_detect_unadjusted_gaps_flags_dividend_like_jumps() -> None:
    """复权校验：无量配合的大跳空视为疑似除权。"""
    frame = _valid_bars(60)
    position = frame.columns.get_loc("close")
    frame.iloc[40:, position] = frame.iloc[40:, position] * 0.6
    suspicious = detect_unadjusted_gaps(frame)
    assert len(suspicious) >= 1
