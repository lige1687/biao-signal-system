"""均线、滞后收盘与 ATR。只计算数值，不给出买卖含义。

增量性质：所有指标都是因果的（只用当日及此前数据），
因此追加未来数据不会改变旧日期已经算出的值。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import indicator_config


def seeded_ema(close: pd.Series, period: int = 20) -> pd.Series:
    """TradingView 风格 EMA：以首窗口 SMA 作为种子，alpha = 2/(period+1)。

    前 period-1 根为 NaN，第 period 根等于 SMA，其后递推。
    """
    if period <= 0:
        raise ValueError("period 必须为正")
    values = close.astype(float).to_numpy()
    result = np.full(len(values), np.nan, dtype=float)
    if len(values) < period:
        return pd.Series(result, index=close.index, name=f"ema{period}")

    seed_index = period - 1
    result[seed_index] = values[:period].mean()
    alpha = 2.0 / (period + 1.0)
    for index in range(seed_index + 1, len(values)):
        result[index] = alpha * values[index] + (1.0 - alpha) * result[index - 1]
    return pd.Series(result, index=close.index, name=f"ema{period}")


def true_range(frame: pd.DataFrame) -> pd.Series:
    """逐根真实波幅。首根为 NaN，因为公式需要前一日收盘。

    移植说明：三路取最大值的公式与
    licai@a25eae9 src/trading_v11/indicators/atr.py::true_ranges 一致；
    此处改为 pandas 向量化并返回 float 而非 Decimal。
    """
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    previous_close = frame["close"].astype(float).shift(1)
    if (high < low).any():
        raise ValueError("行情存在 high < low 的非法记录")
    candidates = pd.concat(
        [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    )
    result = candidates.max(axis=1)
    result.iloc[0] = np.nan
    return result.rename("true_range")


def average_true_range(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    """简单平均 ATR（非 Wilder 平滑）。

    与旧回测 spec 8.9 保持一致：ATR14 定义为最近 14 个 TR 的简单平均。
    第一个 TR 为 NaN，因此第 period+1 根才产生第一个 ATR 值。
    """
    if period <= 0:
        raise ValueError("period 必须为正")
    ranges = true_range(frame)
    return (
        ranges.rolling(period, min_periods=period)
        .mean()
        .rename(f"atr{period}")
    )


def compute_features(bars: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    """计算全部基础特征。

    产出列：sma{20,60,120}、ema{20,60,120}、close_lag{20,60,120}、atr14、
    各均线方向、量能均值与量比、spread。
    """
    if "close" not in bars.columns:
        raise ValueError("行情缺少 close 列")

    settings = config or indicator_config()
    ema_periods = settings.get("ema_periods", [20, 60, 120])
    sma_periods = settings.get("sma_periods", [20, 60, 120])
    lag_periods = settings.get("lag_periods", [20, 60, 120])
    atr_period = int(settings.get("atr_period", 14))
    volume_window = 20

    result = bars.copy()
    close = result["close"].astype(float)

    for period in sma_periods:
        result[f"sma{period}"] = close.rolling(period, min_periods=period).mean()
    for period in ema_periods:
        result[f"ema{period}"] = seeded_ema(close, period)
    for period in lag_periods:
        result[f"close_lag{period}"] = close.shift(period)

    result[f"atr{atr_period}"] = average_true_range(result, atr_period)

    # 均线方向：与前一日比较，NaN 保持 NaN 语义（用 "unknown"）
    for period in sorted({*ema_periods, *sma_periods}):
        for prefix in ("ema", "sma"):
            column = f"{prefix}{period}"
            if column in result.columns:
                result[f"{column}_slope"] = result[column].diff()

    # 双均线开口（EMA20 vs SMA20）
    if "ema20" in result.columns and "sma20" in result.columns:
        result["ma_spread"] = (result["ema20"] - result["sma20"]).abs() / close
        result["ma_spread_change"] = result["ma_spread"].diff()
        result["ema20_above_sma20"] = result["ema20"] > result["sma20"]

    # 量能
    volume = result["volume"].astype(float)
    result[f"volume_mean{volume_window}"] = volume.rolling(
        volume_window, min_periods=volume_window
    ).mean()
    result["volume_ratio20"] = volume / result[f"volume_mean{volume_window}"]

    return result


__all__ = ["average_true_range", "compute_features", "seeded_ema", "true_range"]
