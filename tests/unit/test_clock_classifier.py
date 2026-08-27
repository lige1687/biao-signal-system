"""clock_classifier 单元测试（规格 §4.4 / 账本 clock_classifier 参数）。

直接构造带精确几何斜率的 sma20/sma60 列：s = ln(m_t/m_{t-窗口})/窗口*252
= k*252，其中 m_t = exp(k*t)。覆盖五类分箱、加速分支、预热期与负值镜像。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.rules.clock_classifier import (
    TYPE1_ACCELERATING_UP,
    TYPE2_STEADY_UP,
    TYPE3_SIDEWAYS,
    TYPE4_STEADY_DOWN,
    TYPE5_ACCELERATING_DOWN,
    TYPE_INSUFFICIENT,
    classify_clock,
    clock_series,
    is_entry_allowed,
)


def _frame(k60: float, k20: float, bars: int = 200) -> pd.DataFrame:
    t = np.arange(bars, dtype=float)
    return pd.DataFrame(
        {
            "sma60": np.exp(k60 * t),
            "sma20": np.exp(k20 * t),
        },
        index=pd.bdate_range("2020-01-01", periods=bars),
    )


def test_type2_steady_up() -> None:
    # s60 = k*252 = 0.30（30% 年化）落在 [10%, 100%]
    frame = _frame(k60=0.30 / 252, k20=0.25 / 252)
    series = clock_series(frame)
    assert series.iloc[-1] == TYPE2_STEADY_UP
    assert classify_clock(frame, len(frame) - 1) == TYPE2_STEADY_UP


def test_type1_by_s60_threshold() -> None:
    frame = _frame(k60=1.20 / 252, k20=0.80 / 252)
    assert clock_series(frame).iloc[-1] == TYPE1_ACCELERATING_UP


def test_type1_by_acceleration_branch() -> None:
    # s60=50%（二类区间），但 s20=120% >= 2 x 50% 且 s60 > 40% -> 一类
    frame = _frame(k60=0.50 / 252, k20=1.20 / 252)
    assert clock_series(frame).iloc[-1] == TYPE1_ACCELERATING_UP


def test_acceleration_branch_requires_s60_floor() -> None:
    # s60=30% 未过 40% 门槛：即使 s20 陡峭也保持二类
    frame = _frame(k60=0.30 / 252, k20=1.20 / 252)
    assert clock_series(frame).iloc[-1] == TYPE2_STEADY_UP


def test_type3_sideways() -> None:
    frame = _frame(k60=0.05 / 252, k20=0.02 / 252)
    assert clock_series(frame).iloc[-1] == TYPE3_SIDEWAYS


def test_type4_steady_down() -> None:
    frame = _frame(k60=-0.30 / 252, k20=-0.25 / 252)
    assert clock_series(frame).iloc[-1] == TYPE4_STEADY_DOWN


def test_type5_by_threshold_and_acceleration() -> None:
    assert clock_series(_frame(k60=-1.20 / 252, k20=-0.80 / 252)).iloc[-1] == (
        TYPE5_ACCELERATING_DOWN
    )
    # s60=-50%，s20=-120% <= 2 x s60 = -100% 且 s60 < -40% -> 五类（镜像加速）
    assert clock_series(_frame(k60=-0.50 / 252, k20=-1.20 / 252)).iloc[-1] == (
        TYPE5_ACCELERATING_DOWN
    )


def test_warmup_returns_insufficient() -> None:
    frame = _frame(k60=0.30 / 252, k20=0.25 / 252, bars=60)
    series = clock_series(frame)
    assert (series == TYPE_INSUFFICIENT).all()


def test_entry_allowed_only_for_type2() -> None:
    assert is_entry_allowed(TYPE2_STEADY_UP)
    for clock_type in (
        TYPE_INSUFFICIENT,
        TYPE1_ACCELERATING_UP,
        TYPE3_SIDEWAYS,
        TYPE4_STEADY_DOWN,
        TYPE5_ACCELERATING_DOWN,
    ):
        assert not is_entry_allowed(clock_type)


def test_empty_frame() -> None:
    empty = pd.DataFrame()
    assert len(clock_series(empty)) == 0
    assert classify_clock(empty, 0) == TYPE_INSUFFICIENT


def test_params_come_from_ledger() -> None:
    from lei_signal.domain.rules_config import get_rule

    spec = get_rule("clock_classifier")
    assert float(spec.param("type2_min_s60")) == pytest.approx(0.10)
    assert float(spec.param("type1_min_s60")) == pytest.approx(1.00)
