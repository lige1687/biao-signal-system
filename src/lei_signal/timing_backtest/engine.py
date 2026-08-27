"""宽度择时回测引擎：T 日收盘信号 → T+1 开盘成交的单标的仓位模拟。

规则：
- desired[i] = target[i-1]：T 日收盘数据只影响 T+1 开盘的调仓（无未来函数）
- 调仓按 T+1 开盘价再平衡到目标权重；费用 = |调仓市值| × fee_bps×1e-4
- 现金按 cash_rate 年化逐日计息（默认 0）
- daily.weight 记录「当日执行的决策权重」（非市值漂移权重）
- benchmark 与策略同口径：首个可执行日开盘全仓买入（扣一次费用）后持有
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TimingResult:
    daily: pd.DataFrame  # equity, benchmark, weight + open/close/b20/b50/b200
    trades: list[dict]   # date, prev_weight, new_weight, price, fee, turnover


def simulate(
    aligned: pd.DataFrame, target: pd.Series, fee_bps: float, cash_rate: float = 0.0
) -> TimingResult:
    open_ = aligned["open"].to_numpy(dtype=float)
    close = aligned["close"].to_numpy(dtype=float)
    tgt = target.reindex(aligned.index).to_numpy(dtype=float)
    fee_rate = fee_bps * 1e-4
    n = len(aligned)

    cash, units, weight = 1.0, 0.0, 0.0
    equity = np.empty(n)
    weights = np.empty(n)
    trades: list[dict] = []

    for i in range(n):
        if i > 0 and not np.isnan(tgt[i - 1]) and not np.isnan(open_[i]):
            desired = float(tgt[i - 1])
            delta = desired - weight
            if abs(delta) > 1e-9:
                eq_open = cash + units * open_[i]
                fee = eq_open * abs(delta) * fee_rate
                eq_after = eq_open - fee
                invest = eq_after * desired
                units = invest / open_[i]
                cash = eq_after - invest
                trades.append(
                    {
                        "date": aligned.index[i].strftime("%Y-%m-%d"),
                        "prev_weight": round(weight, 6),
                        "new_weight": round(desired, 6),
                        "price": round(float(open_[i]), 4),
                        "fee": round(fee, 8),
                        "turnover": round(abs(delta), 6),
                    }
                )
                weight = desired
        equity[i] = cash + units * close[i]
        weights[i] = weight
        if cash_rate != 0.0 and cash > 0:
            cash *= 1.0 + cash_rate / 252.0  # 空仓部分按年化 cash_rate 逐日计息

    if n > 1:
        bh_units = (1.0 - fee_rate) / open_[1]
        benchmark = np.where(np.arange(n) >= 1, bh_units * close, 1.0)
    else:
        benchmark = np.ones(n)

    passthrough = [
        c for c in ("open", "high", "low", "close", "b20", "b50", "b200")
        if c in aligned.columns
    ]
    daily = aligned[passthrough].copy()
    daily["equity"] = equity
    daily["benchmark"] = benchmark
    daily["weight"] = weights
    return TimingResult(daily=daily, trades=trades)
