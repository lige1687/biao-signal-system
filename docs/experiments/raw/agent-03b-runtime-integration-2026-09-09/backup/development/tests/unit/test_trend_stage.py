"""趋势五步状态机测试（src/lei_signal/rules/trend_stage.py）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.trend_stage import trend_stage_series


def _row_frame(**overrides: float) -> pd.DataFrame:
    """单行 frame，指标列直接给定（trend_stage 只读列，不重算指标）。

    默认值构造出 stage=4（排列成立、乖离未极端）；覆盖任意列可制造
    每一步的成败组合。bias 默认 0.2（< 账本 bias_extreme=0.5）。
    """
    base = {
        "close": 100.0,
        "ema20": 99.0,     # 破线成立
        "ema60": 97.0,
        "ema120": 95.0,
        "sma20": 98.0,
        "sma60": 96.0,
        "sma120": 94.0,
        "close_lag20": 97.0,   # 拐头（抵扣价）成立
        "ema20_slope": 0.5,    # EMA 上行成立
    }
    base.update(overrides)
    index = pd.bdate_range("2024-01-01", periods=1)
    frame = pd.DataFrame({k: [v] for k, v in base.items()}, index=index)
    frame["ema120"] = frame["ema120"]  # bias = close/ema120 - 1
    return frame


def test_stage_four_when_aligned_without_extreme_bias() -> None:
    stage = trend_stage_series(_row_frame())
    # close/ema120 - 1 = 100/95 - 1 ≈ 5.3% < 50% -> 不进第 5 步
    assert stage.iloc[0] == 4


def test_stage_five_when_extreme_bias() -> None:
    # 100/60 - 1 ≈ 67% >= 50%：但 ema120=60 破坏排列（ema60>ema120 仍可成立，
    # ema120 只是最低位）--排列要求 ema60>ema120，60<97 不成立。
    # 用整体抬高的排列 + close 远超 ema120 构造：close=150, ema120=95。
    frame = _row_frame(close=150.0)
    stage = trend_stage_series(frame)
    assert stage.iloc[0] == 5  # 150/95 - 1 ≈ 58% >= 50%，排列仍成立


def test_stage_zero_when_break_fails() -> None:
    stage = trend_stage_series(_row_frame(close=98.0))  # close < ema20
    assert stage.iloc[0] == 0


def test_stage_one_when_turn_fails() -> None:
    stage = trend_stage_series(_row_frame(ema20_slope=-0.5))
    assert stage.iloc[0] == 1


def test_stage_one_when_dikou_fails() -> None:
    stage = trend_stage_series(_row_frame(close_lag20=101.0))  # close <= close_lag20
    assert stage.iloc[0] == 1


def test_stage_two_when_cross_fails() -> None:
    stage = trend_stage_series(_row_frame(sma20=95.0))  # sma20 < sma60
    assert stage.iloc[0] == 2


def test_cross_gap_does_not_count_cumulatively() -> None:
    """交叉成立但拐头失败 -> stage 1（累进合取，不许跳步）。"""
    frame = _row_frame(ema20_slope=-0.5, sma20=98.0)
    assert trend_stage_series(frame).iloc[0] == 1


def test_stage_three_when_alignment_fails() -> None:
    stage = trend_stage_series(_row_frame(ema60=99.5))  # ema20 > ema60 不成立
    assert stage.iloc[0] == 3


def test_cross_basis_ema_uses_ema20_vs_sma60() -> None:
    # sma 口径下不交叉（sma20<sma60），ema 口径下交叉（ema20>sma60）
    frame = _row_frame(sma20=95.0)
    assert trend_stage_series(frame).iloc[0] == 2
    assert trend_stage_series(frame, cross_basis="ema").iloc[0] == 3


def test_unknown_cross_basis_rejected() -> None:
    import pytest

    with pytest.raises(ValueError, match="交叉口径"):
        trend_stage_series(_row_frame(), cross_basis="close")


def test_warmup_all_zero_then_progresses_on_rally() -> None:
    """真实指标列：预热期全 0；足够陡的指数拉升最终走到第 5 步。"""
    closes = [100.0 * 1.01**i for i in range(320)]
    close = pd.Series(closes, index=pd.bdate_range("2020-01-01", periods=len(closes)))
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": 1e6,
        },
        index=close.index,
    )
    frame = compute_features(bars)
    stage = trend_stage_series(frame)
    # 前 10 根 EMA20 未预热 -> 0（120 线未预热时只影响步骤 4/5，不挡 1..3）
    assert stage.iloc[:10].max() == 0
    # 指数拉升 1%/日：bias、排列、交叉、拐头、破线最终全部成立
    assert stage.iloc[-1] == 5
    assert stage.max() == 5


def test_crash_below_ema20_resets_to_zero() -> None:
    closes = [100.0 * 1.01**i for i in range(200)]
    closes += [closes[-1] * 0.90**k for k in range(1, 12)]  # 急跌
    close = pd.Series(closes, index=pd.bdate_range("2020-01-01", periods=len(closes)))
    bars = pd.DataFrame(
        {
            "open": close,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": 1e6,
        },
        index=close.index,
    )
    frame = compute_features(bars)
    stage = trend_stage_series(frame)
    assert stage.iloc[-1] == 0  # 收盘跌回 EMA20 之下 -> 破线失败即 0
    assert int(stage.max()) >= 3  # 拉升段确实走到过高阶段


def test_missing_columns_returns_zero() -> None:
    frame = pd.DataFrame({"close": [100.0]})
    stage = trend_stage_series(frame)
    assert list(stage) == [0]
    assert bool(np.all(stage.to_numpy() == 0))
