"""weekly_context 单元测试（规格 §6 简化版 / §3.2 周线完成语义）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.features.weekly_context import weekly_alignment, weekly_env_series


def _uptrend_bars(weeks: int = 130, g: float = 0.004) -> pd.DataFrame:
    """weeks 个完整周的几何上行（周内 5 个交易日）。"""
    days = weeks * 5
    close = pd.Series(
        100.0 * (1.0 + g) ** np.arange(days),
        index=pd.bdate_range("2018-01-01", periods=days),
    )
    return pd.DataFrame(
        {
            "open": close * 1.0005,
            "high": close * 1.004,
            "low": close * 0.996,
            "close": close,
            "volume": np.full(days, 1e6),
        },
        index=close.index,
    )


def test_bull_alignment_true_after_warmup() -> None:
    from lei_signal.data.point_in_time import aggregate_weekly

    weekly = weekly_alignment(aggregate_weekly(_uptrend_bars()))
    # 严格几何上行：WSMA 与 WEMA 双组都满足 20>60>120
    assert bool(weekly["bull_alignment"].iloc[-1])
    # 不足 120 根周线时均线为 NaN -> 排列 False（宁缺勿假）
    early = weekly_alignment(aggregate_weekly(_uptrend_bars(weeks=100)))
    assert not bool(early["bull_alignment"].iloc[-1])


def test_weekly_env_series_true_for_uptrend_daily() -> None:
    bars = _uptrend_bars()
    env = weekly_env_series(bars)
    assert bool(env.iloc[-1])
    # 前 120 个已完成周为预热期（排列不可判定 -> False），最后约 10 周为 True
    assert 0 < int(env.sum()) < len(bars) * 0.2


def test_prefix_invariance_no_future_leak() -> None:
    """截断在任何一日重算，历史结论不变（防未来泄漏的强性质）。"""
    bars = _uptrend_bars()
    full = weekly_env_series(bars)
    for cut in (len(bars) - 13, len(bars) - 7, len(bars) - 1):
        prefix = weekly_env_series(bars.iloc[:cut])
        assert (prefix == full.iloc[:cut]).all()


def test_empty_input() -> None:
    env = weekly_env_series(pd.DataFrame(columns=["open", "high", "low", "close"]))
    assert len(env) == 0
