"""条件化场景回测的通用统计工具（P2 三项研究代理共用）。

与 first_ma_pullback_backtest 保持同一统计口径：固定周期 + 规则退出，均为重叠事件
研究而非单账户资金曲线；未完成样本单独计数，不进入收益/胜率/MFE/MAE。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SCENARIO_BACKTEST_HORIZONS = (5, 10, 20, 60, 120)


@dataclass(frozen=True)
class ScenarioPerformanceStats:
    key: str
    label_cn: str
    sample_count: int
    incomplete_count: int
    win_rate: float | None
    mean_return: float | None
    median_return: float | None
    mean_mfe: float | None
    mean_mae: float | None
    mean_holding_days: float | None


@dataclass(frozen=True)
class ScenarioBacktestSide:
    key: str
    title_cn: str
    entry_rule_cn: str
    exit_rule_cn: str
    total_signals: int
    open_trades: int
    stats: tuple[ScenarioPerformanceStats, ...]


@dataclass(frozen=True)
class ScenarioBacktestReport:
    start_date: str
    end_date: str
    total_bars: int
    research_disclaimer_cn: str
    sides: tuple[ScenarioBacktestSide, ...]


def safe_mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def safe_median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def path_metrics(
    frame: pd.DataFrame, entry_position: int, exit_position: int
) -> tuple[float, float, float, int]:
    """返回 (收益%, MFE%, MAE%, 持有根数)，只看 entry+1..exit 的未来区间。"""
    entry = float(frame["close"].iloc[entry_position])
    exit_close = float(frame["close"].iloc[exit_position])
    future = frame.iloc[entry_position + 1 : exit_position + 1]
    high = float(future["high"].astype(float).max())
    low = float(future["low"].astype(float).min())
    return (
        (exit_close / entry - 1.0) * 100.0,
        (high / entry - 1.0) * 100.0,
        (low / entry - 1.0) * 100.0,
        exit_position - entry_position,
    )


def summarize(
    *,
    key: str,
    label_cn: str,
    rows: list[tuple[float, float, float, int]],
    incomplete_count: int,
) -> ScenarioPerformanceStats:
    returns = [row[0] for row in rows]
    return ScenarioPerformanceStats(
        key=key,
        label_cn=label_cn,
        sample_count=len(rows),
        incomplete_count=incomplete_count,
        win_rate=(sum(value > 0 for value in returns) / len(returns) if returns else None),
        mean_return=safe_mean(returns),
        median_return=safe_median(returns),
        mean_mfe=safe_mean([row[1] for row in rows]),
        mean_mae=safe_mean([row[2] for row in rows]),
        mean_holding_days=safe_mean([float(row[3]) for row in rows]),
    )


def fixed_horizon_stats(
    frame: pd.DataFrame, entries: list[int]
) -> list[ScenarioPerformanceStats]:
    stats: list[ScenarioPerformanceStats] = []
    total = len(frame)
    for horizon in SCENARIO_BACKTEST_HORIZONS:
        eligible = [position for position in entries if position + horizon < total]
        rows = [
            path_metrics(frame, entry_position=position, exit_position=position + horizon)
            for position in eligible
        ]
        stats.append(
            summarize(
                key=f"day_{horizon}",
                label_cn=f"{horizon}日",
                rows=rows,
                incomplete_count=len(entries) - len(eligible),
            )
        )
    return stats


def rule_exit_position(
    frame: pd.DataFrame, entry_position: int, predicate,  # noqa: ANN001
) -> int | None:
    """从 entry+1 起，第一个满足 predicate(row) 的位置；始终不满足返回 None。"""
    for position in range(entry_position + 1, len(frame)):
        if predicate(frame.iloc[position]):
            return position
    return None


def rule_exit_stats(
    frame: pd.DataFrame, entries: list[int], predicate  # noqa: ANN001
) -> tuple[ScenarioPerformanceStats, int]:
    rows: list[tuple[float, float, float, int]] = []
    open_trades = 0
    for entry in entries:
        exit_position = rule_exit_position(frame, entry, predicate)
        if exit_position is None:
            open_trades += 1
            continue
        rows.append(path_metrics(frame, entry_position=entry, exit_position=exit_position))
    return (
        summarize(
            key="rule_exit",
            label_cn="规则退出",
            rows=rows,
            incomplete_count=open_trades,
        ),
        open_trades,
    )


RESEARCH_DISCLAIMER = (
    "研究代理事件统计，不是单账户资金曲线；未计手续费、滑点、涨跌停、停牌、"
    "流动性和融券约束。固定周期未完成样本与规则退出未平仓样本均单独计数，"
    "不进入收益、胜率、MFE 或 MAE。"
)


__all__ = [
    "SCENARIO_BACKTEST_HORIZONS",
    "ScenarioBacktestReport",
    "ScenarioBacktestSide",
    "ScenarioPerformanceStats",
    "fixed_horizon_stats",
    "path_metrics",
    "rule_exit_position",
    "rule_exit_stats",
    "safe_mean",
    "safe_median",
    "summarize",
    "RESEARCH_DISCLAIMER",
]
