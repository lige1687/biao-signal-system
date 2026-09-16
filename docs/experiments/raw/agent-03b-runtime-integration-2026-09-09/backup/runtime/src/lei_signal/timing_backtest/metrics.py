"""宽度择时绩效指标：年化/回撤/波动/Sharpe/Calmar/逐年收益/运行汇总。"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def compute_performance(equity: pd.Series) -> dict[str, float]:
    """净值序列 → 年化收益、最大回撤、年化波动、Sharpe(rf=0)、Calmar。"""
    eq = equity.dropna()
    n = len(eq)
    if n < 2 or eq.iloc[0] <= 0:
        return {"cagr": 0.0, "mdd": 0.0, "vol": 0.0, "sharpe": 0.0, "calmar": 0.0}
    years = (n - 1) / TRADING_DAYS  # 首末观测间只经过 n-1 个交易日
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0)
    drawdown = eq / eq.cummax() - 1.0
    mdd = float(drawdown.min())
    ret = eq.pct_change().dropna()
    std = float(ret.std(ddof=1)) if len(ret) > 1 else 0.0
    vol = std * float(np.sqrt(TRADING_DAYS))
    sharpe = float(ret.mean() / std * np.sqrt(TRADING_DAYS)) if std > 1e-12 else 0.0
    calmar = float(cagr / abs(mdd)) if mdd < 0 else 0.0
    return {"cagr": cagr, "mdd": mdd, "vol": vol, "sharpe": sharpe, "calmar": calmar}


def yearly_returns(equity: pd.Series) -> pd.Series:
    """按日历年分组的收益率；年初基准 = 上一年末净值（首年 = 首个净值）。"""
    eq = equity.dropna()
    if eq.empty:
        return pd.Series(dtype=float)
    year_end = eq.groupby(eq.index.year).last()
    year_start = year_end.shift(1)
    year_start.iloc[0] = eq.iloc[0]
    return year_end / year_start - 1.0


def summarize_run(daily: pd.DataFrame, trades: list[dict]) -> dict[str, float]:
    perf = compute_performance(daily["equity"])
    bench = compute_performance(daily["benchmark"])
    years = len(daily) / TRADING_DAYS
    return {
        "strategy_cagr": perf["cagr"],
        "benchmark_cagr": bench["cagr"],
        "excess_cagr": perf["cagr"] - bench["cagr"],
        "strategy_mdd": perf["mdd"],
        "benchmark_mdd": bench["mdd"],
        "calmar": perf["calmar"],
        "sharpe": perf["sharpe"],
        "vol": perf["vol"],
        "avg_weight": float(daily["weight"].mean()),
        "n_trades": float(len(trades)),
        "total_turnover": float(sum(t.get("turnover", 0.0) for t in trades)),
        "years": years,
    }
