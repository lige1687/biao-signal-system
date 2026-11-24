"""B3-b 候选 1：trend.ma_cluster_width（六均线密集宽度）最小计算实现。

定义来源：B1 表单 4（fa-20260919-b1-ma-cluster-width，trading-spec
§4.6 均线密集 / §9 模块 B 密集区突破），版本化草案见
docs/experiments/raw/factor-b3b-2026-09-20/ma-cluster-width/definition-draft.md。

边界（G2 重点核查项，实现不得越界）：
- 均线集合锁定为 {EMA20, SMA20, EMA60, SMA60, EMA120, SMA120}，不开放参数；
- 宽度公式 (max−min)/min，分母固定为最小均线值；
- 不引入任何"多窄算密集"的阈值——2% 参考值属 rules.v1.yaml，不进因子；
- 缺失处理：任一均线当日 NaN → 宽度 NaN；序列中部 close 缺失会污染
  EMA 递推（与系统 seeded_ema 同口径），此后宽度持续 NaN，不插值不填 0。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.features.indicators import seeded_ema

WINDOWS = (20, 60, 120)
MA_KEYS = ("ema20", "sma20", "ema60", "sma60", "ema120", "sma120")


def trailing_sma(close: pd.Series, window: int) -> pd.Series:
    """窗口内任一缺失即 NaN 的简单均线（min_periods=window）。"""
    return close.rolling(window, min_periods=window).mean().rename(f"sma{window}")


def six_moving_averages(close: pd.Series) -> pd.DataFrame:
    """锁定六均线：EMA 用系统 seeded_ema（首窗口 SMA 种子），SMA 用满窗均值。"""
    out = {}
    for window in WINDOWS:
        out[f"ema{window}"] = seeded_ema(close, window)
        out[f"sma{window}"] = trailing_sma(close, window)
    return pd.DataFrame(out, columns=list(MA_KEYS))


def ma_cluster_width(close: pd.Series) -> pd.Series:
    """宽度序列：(max−min)/min；任一均线 NaN 或 min≤0 时该日 NaN。"""
    mas = six_moving_averages(close)
    # skipna=False：任一均线 NaN 则极差 NaN（NaN 政策：不部分计算）
    row_max = mas.max(axis=1, skipna=False)
    row_min = mas.min(axis=1, skipna=False)
    width = (row_max - row_min) / row_min
    width[row_min <= 0] = float("nan")
    return width.rename("ma_cluster_width")
