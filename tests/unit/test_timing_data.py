"""timing_backtest.data 宽度重算与对齐纯函数测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.data import (
    INSTRUMENTS,
    align_index_breadth,
    compute_breadth_from_close_matrix,
    data_unavailable_detail,
    load_breadth,
    load_index_bars,
)


def _wide() -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=250)
    up1 = pd.Series(np.linspace(10, 30, 250), index=idx)
    up2 = pd.Series(np.linspace(5, 25, 250), index=idx)
    flat = pd.Series(np.full(250, 100.0), index=idx)
    late = pd.Series(np.linspace(1, 2, 250), index=idx)
    late.iloc[:199] = np.nan  # 只有 51 根，不够 MA200
    return pd.DataFrame({"UP1": up1, "UP2": up2, "FLAT": flat, "LATE": late})


def test_breadth_values_and_eligibility():
    out = compute_breadth_from_close_matrix(_wide(), min_eligible=3)
    # MA20：UP1/UP2/LATE（末段上升）在上方，FLAT close==MA 不算上方 → 3/4
    assert out["b20"].iloc[-1] == pytest.approx(75.0)
    assert out["n20"].iloc[-1] == 4
    # MA200：LATE 只有 51 根不 eligible；UP1/UP2 在上方、FLAT 不在 → 2/3
    assert out["n200"].iloc[-1] == 3
    assert out["b200"].iloc[-1] == pytest.approx(200.0 / 3.0)
    # 前 199 根没有 MA200 eligible → NaN
    assert np.isnan(out["b200"].iloc[0])


def test_min_eligible_guard():
    idx = pd.bdate_range("2024-01-01", periods=250)
    tiny = pd.DataFrame({"A": np.linspace(1, 2, 250)}, index=idx)
    out = compute_breadth_from_close_matrix(tiny, min_eligible=30)
    assert out["b20"].isna().all()


def test_align_intersection_and_cache_roundtrip(tmp_path):
    idx = pd.bdate_range("2025-01-01", periods=10)
    bars = pd.DataFrame(
        {
            "open": np.arange(10.0),
            "high": np.arange(10.0) + 2,
            "low": np.arange(10.0) - 2,
            "close": np.arange(10.0) + 1,
        },
        index=idx,
    )
    br = pd.DataFrame(
        {"b20": np.arange(7.0), "b50": np.arange(7.0), "b200": np.arange(7.0)},
        index=idx[:-3],
    )
    bars.to_parquet(tmp_path / "X.parquet")
    br.to_parquet(tmp_path / "breadth_cn_all.parquet")
    loaded = load_index_bars("X", cache_dir=tmp_path)
    pd.testing.assert_frame_equal(loaded, bars, check_freq=False)
    merged = align_index_breadth(bars, load_breadth("cn_all", cache_dir=tmp_path))
    assert len(merged) == 7
    assert list(merged.columns) == ["open", "high", "low", "close", "b20", "b50", "b200"]


def test_load_synthesizes_high_low_from_open_close(tmp_path):
    idx = pd.bdate_range("2025-01-01", periods=5)
    df = pd.DataFrame({"open": [10, 12, 9, 11, 13], "close": [11, 10, 13, 10, 12]}, index=idx)
    df.to_parquet(tmp_path / "Y.parquet")
    loaded = load_index_bars("Y", cache_dir=tmp_path)
    assert list(loaded["high"]) == [11, 12, 13, 11, 13]
    assert list(loaded["low"]) == [10, 10, 9, 10, 12]


def test_registry_covers_eight_instruments_with_breadth_pairing():
    assert set(INSTRUMENTS) == {"000300", "399006", "^GSPC", "^IXIC", "SPY", "QQQ", "510300", "159915"}
    for spec in INSTRUMENTS.values():
        assert spec.breadth in ("cn_all", "sp500")
        assert spec.market in ("cn", "us")
        assert spec.fee_default_bps > 0
    assert INSTRUMENTS["399006"].breadth == "cn_all"
    assert INSTRUMENTS["^IXIC"].breadth == "sp500"


def test_data_unavailable_detail_mentions_script():
    msg = data_unavailable_detail("000300")
    assert "DATA_UNAVAILABLE" in msg and "backfill_timing_data" in msg
    assert "NOPE" not in msg or data_unavailable_detail("NOPE") == "未知标的 NOPE"


def test_compute_ad_breadth_and_align_passthrough():
    from lei_signal.timing_backtest.data import compute_ad_breadth

    idx = pd.bdate_range("2024-01-01", periods=30)
    up_stock = pd.Series(np.linspace(10, 40, 30), index=idx)      # 天天涨
    down_stock = pd.Series(np.linspace(40, 10, 30), index=idx)    # 天天跌
    flat_stock = pd.Series(np.full(30, 100.0), index=idx)         # 平
    wide = pd.DataFrame({"UP": up_stock, "DOWN": down_stock, "FLAT": flat_stock})
    out = compute_ad_breadth(wide, smooth=5, min_eligible=2)
    # UP 涨、DOWN 跌、FLAT 平：首日无前值不计分母 → ad 首日 NaN，之后 = 1/3
    assert np.isnan(out["ad"].iloc[0])
    assert out["ad"].iloc[-1] == pytest.approx(100.0 / 3.0)
    assert out["ad20"].iloc[-1] == pytest.approx(100.0 / 3.0)  # 平滑不改变常值
    # ad 列能通过 align 透传
    bars = pd.DataFrame(
        {"open": np.arange(30.0), "high": np.arange(30.0) + 1,
         "low": np.arange(30.0) - 1, "close": np.arange(30.0) + 0.5},
        index=idx,
    )
    merged = align_index_breadth(bars, out)
    assert list(merged.columns) == ["open", "high", "low", "close", "ad", "ad20"]
