"""收盘价状态研究适配（factor_unit，B0 隔离模块）。

定位：只依赖收盘价的双均线共同确认状态计算，服务真实输入研究的
close-only 输入合同。不修改、不包装 factor_lab v1.2.0 合成原型；
公式完全复用生产函数，不复制第二套实现。

R1 裁定边界：全量 ``compute_features`` 需要 OHLCV，但共同确认状态实际只依赖
close/EMA20/SMA20/滞后收盘/颜色——本模块只剥离与该状态无关的 ATR、MACD、
成交量计算，**不是删减策略条件**（完整共同确认仍调用 ``dual_ma_bull_state``）。
也不构成"任何因子都不需要成交量"的许可。

R3 等价解释（仅解释，不改公式）：同一完整窗口、EMA 过种子后以 0<α<1 递推时，
EMA 上升与 C_t>EMA_t 同号；SMA 当日变化=(C_t−C_t−20)/20。故非浮点临界处
state ⟺ (signal_color==green 且 close>sma20)。数学冗余不产生预测价值结论。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.features.indicators import seeded_ema
from lei_signal.rules.dual_ma import dual_ma_bull_state
from lei_signal.rules.lei_color import classify_colors

__all__ = ["compute_close_state"]


def _validate_close(close: pd.Series) -> pd.Series:
    if not isinstance(close, pd.Series):
        raise ValueError("close 必须是 pandas Series")
    if not close.index.is_unique:
        raise ValueError("close 日期必须唯一（禁止重复日期静默计算）")
    if not close.index.is_monotonic_increasing:
        raise ValueError("close 日期必须递增（禁止乱序静默排序）")
    values = close.astype(float)
    finite = values.dropna()
    if ((finite <= 0) | ~np.isfinite(finite)).any():
        raise ValueError("价格必须为正的有限值；缺失必须显式 NaN（禁止零/负/无穷）")
    return values


def compute_close_state(close: pd.Series) -> pd.DataFrame:
    """返回 close/ema20/sma20/close_lag20/signal_color/state/missing_reason。

    - ``state`` 为可空布尔（pd.BooleanDtype）：True/False/缺失；
    - ``missing_reason``：``price_missing``（当日缺价）/ ``warmup_not_ready``
      （任一必需输入未就绪；含前导预热与内部 NaN 污染后的 EMA 永久不可用）；
    - 索引原样保留；禁止排序、去重或补价后静默计算（违反即报错）；
    - 前导 NaN 按旧 ``seeded_ema`` 语义跳过；内部 NaN 使旧 EMA 递推污染后
      **诚实传播为持续不可用**，不跳过、不重启；
    - 只有当前与前一日均线、lag、颜色全部就绪才产生有效布尔；为 False
      不等于看空，未就绪不混入 False。
    """
    close = _validate_close(close)
    frame = pd.DataFrame(index=close.index)
    frame["close"] = close
    frame["ema20"] = seeded_ema(close, 20)
    frame["sma20"] = close.rolling(20, min_periods=20).mean()
    frame["close_lag20"] = close.shift(20)
    colored = classify_colors(frame)  # 需要 close/ema20/close_lag20

    prev_ema = colored["ema20"].shift(1)
    prev_sma = colored["sma20"].shift(1)
    rising_ready = prev_ema.notna() & prev_sma.notna()
    color_ready = colored["color_ready"].fillna(False).astype(bool)

    state = dual_ma_bull_state(colored)  # 需要 close/ema20/sma20/signal_color

    missing_reason = np.full(len(close), "warmup_not_ready", dtype=object)
    close_missing = close.isna().to_numpy()
    missing_reason[close_missing] = "price_missing"
    ready = (
        color_ready.to_numpy()
        & colored["sma20"].notna().to_numpy()
        & rising_ready.to_numpy()
        & ~close_missing
    )
    state_out = pd.array([None] * len(close), dtype="boolean")
    idx_ready = np.flatnonzero(ready)
    for i in idx_ready:
        state_out[i] = bool(state.iloc[i])
        missing_reason[i] = "" if bool(state.iloc[i]) else ""
    # 有效行的 missing_reason 置 None（就绪且已判定）
    for i in idx_ready:
        missing_reason[i] = None

    return pd.DataFrame(
        {
            "close": close,
            "ema20": colored["ema20"],
            "sma20": colored["sma20"],
            "close_lag20": colored["close_lag20"],
            "signal_color": colored["signal_color"],
            "state": state_out,
            "missing_reason": missing_reason,
        },
        index=close.index,
    )
