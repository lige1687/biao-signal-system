"""市场波动体制（Round 4 环境层扩展，research_proxy）。

设计要点：

- 口径：市场成分股**等权日收益**（当日有效成分均值，与宽度分母同思想）
  → 20 日已实现波动率年化 → 近 756 日（≈3 年，最少 252 日）滚动百分位。
- 体制阈值：分位 ≥0.8 高波 / ≤0.2 低波 / 其余中波。阈值不是 LEI 原始规则，
  来自 2026-08-27 本地实证（``docs/research-factor-backtest.md`` F 节）：
  LEI 信号对账 3755 条——市场低波期信号前向 60 日均值 4.98% vs 高波期 0.73%。
- 只做**独立分组研究与展示**，不硬挡任何单标的技术信号（Round 4 红线）。
- 历史不足（<252 个有效交易日）显式返回 None，绝不冒充。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

RV_WINDOW = 20
RV_RANK_WINDOW = 756
RV_RANK_MIN_PERIODS = 252
HIGH_THRESHOLD = 0.8
LOW_THRESHOLD = 0.2

_EVENT_VERSION = "research_market_vol.v1"
_PROVENANCE = (
    "research_proxy: 等权成分日收益口径；阈值来自 2026-08-27 LEI 信号对账"
    "（市场高波期信号 60 日均值 4.98%→0.73%，3755 条样本）"
)


@dataclass(frozen=True, slots=True)
class MarketVolRegime:
    """一个市场一个交易日的波动体制读数。"""

    rv20_ann: float            # 年化已实现波动率
    rv_pct: float              # 3 年滚动分位（0~1）
    regime: str                # "high" | "mid" | "low"
    valid_days: int            # 有效成分日数（对账用）
    provenance: str = _PROVENANCE


def compute_market_vol_regime(
    bars_by_symbol: dict[str, pd.DataFrame],
    sessions: pd.DatetimeIndex,
    as_of: date,
    *,
    rv_window: int = RV_WINDOW,
    rank_window: int = RV_RANK_WINDOW,
    min_periods: int = RV_RANK_MIN_PERIODS,
) -> MarketVolRegime | None:
    """等权成分日收益 → RV20 → 滚动分位 → 体制。

    返回 None 的情形：无成分数据 / 有效日 < min_periods / as_of 不在
    sessions 内（数据未到，不冒充）。
    """
    if not bars_by_symbol or sessions is None or len(sessions) == 0:
        return None

    closes: dict[str, pd.Series] = {}
    for sym, df in bars_by_symbol.items():
        if df is None or df.empty or "close" not in df.columns:
            continue
        s = df["close"].astype(float)
        s = s[~s.index.duplicated(keep="last")]
        closes[sym] = s
    if not closes:
        return None

    wide = pd.DataFrame(closes).reindex(sessions).ffill()
    valid = wide.notna()
    if valid.sum().max() < rv_window + 1:
        return None

    # 等权市场日收益：分母 = 当日有效成分数（NaN 自动排除，不用固定分母）
    ret = wide.pct_change()
    daily = ret.where(valid).mean(axis=1, skipna=True).dropna()
    if len(daily) < min_periods:
        return None

    as_of_ts = pd.Timestamp(as_of)
    if len(sessions) > 0 and as_of_ts not in set(sessions):
        # as_of 非交易日或未到：用 sessions 内 ≤ as_of 的最后一天（宽度同思想）。
        prior = sessions[sessions <= as_of_ts]
        if len(prior) == 0:
            return None
        as_of_ts = prior[-1]

    rv_hist = daily.rolling(rv_window).std() * np.sqrt(252.0)
    rank = rv_hist.rolling(rank_window, min_periods=min_periods).rank(pct=True)
    rv_now = rv_hist.asof(as_of_ts)
    pct_now = rank.asof(as_of_ts)
    if pd.isna(rv_now) or pd.isna(pct_now):
        return None

    if pct_now >= HIGH_THRESHOLD:
        regime = "high"
    elif pct_now <= LOW_THRESHOLD:
        regime = "low"
    else:
        regime = "mid"

    return MarketVolRegime(
        rv20_ann=float(rv_now),
        rv_pct=float(pct_now),
        regime=regime,
        valid_days=int(valid.loc[:as_of_ts].any(axis=1).sum()),
    )


def vol_event_type(regime: str) -> str | None:
    """高/低波体制 → 事件类型；中波不发事件。"""
    if regime == "high":
        return "high_vol_regime"
    if regime == "low":
        return "low_vol_regime"
    return None


__all__ = [
    "MarketVolRegime",
    "RV_RANK_MIN_PERIODS",
    "RV_RANK_WINDOW",
    "RV_WINDOW",
    "compute_market_vol_regime",
    "vol_event_type",
]
