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
    若输入存在前导 NaN（如 MACD 的 DIF：前 slow-1 根为 NaN），自动跳过
    前导 NaN，从首个有效值起以 SMA 作种子再递推--对无前导 NaN 的序列
    （如收盘价）行为完全不变。
    """
    if period <= 0:
        raise ValueError("period 必须为正")
    values = close.astype(float).to_numpy()
    result = np.full(len(values), np.nan, dtype=float)
    # 跳过前导 NaN：MACD DIF 等派生序列会带前导 NaN，直接以首窗口 SMA
    # 作种子会让 seed=NaN 并污染全段，因此先定位首个有效值。
    first_valid = 0
    n = len(values)
    while first_valid < n and np.isnan(values[first_valid]):
        first_valid += 1
    valid = values[first_valid:]
    if len(valid) < period:
        return pd.Series(result, index=close.index, name=f"ema{period}")

    seed_index = period - 1
    result[first_valid + seed_index] = valid[:period].mean()
    alpha = 2.0 / (period + 1.0)
    for index in range(seed_index + 1, len(valid)):
        result[first_valid + index] = (
            alpha * valid[index] + (1.0 - alpha) * result[first_valid + index - 1]
        )
    return pd.Series(result, index=close.index, name=f"ema{period}")


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD：DIF = EMA(fast) - EMA(slow)，DEA = EMA(signal, DIF)，hist = 2*(DIF-DEA)。

    复用 ``seeded_ema``：DIF 前 slow-1 根为 NaN，DEA 在 DIF 首个有效值后
    signal 根起算，追加未来数据不改变旧值（因果/增量）。

    只计算数值，不给出买卖含义。MACD 表达均线扩散/密集=乖离率=**强度**，
    不是转折趋势节点（解读口径见 ``configs/rules.v1.yaml`` 的 ``macd_strength``）。
    """
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("fast/slow/signal 必须为正")
    if fast >= slow:
        raise ValueError("fast 必须小于 slow")
    ema_fast = seeded_ema(close, fast)
    ema_slow = seeded_ema(close, slow)
    dif = (ema_fast - ema_slow).rename("macd_dif")
    dea = seeded_ema(dif, signal).rename("macd_dea")
    hist = ((dif - dea) * 2.0).rename("macd_hist")
    return dif, dea, hist


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
    各均线方向、量能均值与量比、spread、macd_dif/dea/hist。
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

    # MACD（研究代理强度指标）：DIF/DEA/hist，作乖离/强度解读，非转折
    macd_fast = int(settings.get("macd_fast", 12))
    macd_slow = int(settings.get("macd_slow", 26))
    macd_signal = int(settings.get("macd_signal", 9))
    macd_dif, macd_dea, macd_hist = macd(close, macd_fast, macd_slow, macd_signal)
    result["macd_dif"] = macd_dif
    result["macd_dea"] = macd_dea
    result["macd_hist"] = macd_hist

    return result


__all__ = ["average_true_range", "compute_features", "macd", "seeded_ema", "true_range"]
