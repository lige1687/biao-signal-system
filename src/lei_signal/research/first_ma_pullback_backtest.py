"""首次 SMA20/60/120 回撤确认事件的固定周期与规则退出研究。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import SignalEvent
from lei_signal.rules.first_ma_pullback import RULE_ID, SUB_RULE_CONFIRMED

PULLBACK_BACKTEST_HORIZONS = (5, 10, 20, 60, 120)


@dataclass(frozen=True)
class PullbackPerformanceStats:
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
class PullbackBacktestSide:
    ma_period: int
    title_cn: str
    entry_rule_cn: str
    exit_rule_cn: str
    total_signals: int
    open_trades: int
    stats: tuple[PullbackPerformanceStats, ...]


@dataclass(frozen=True)
class PullbackBacktestReport:
    start_date: str
    end_date: str
    total_bars: int
    research_disclaimer_cn: str
    sides: tuple[PullbackBacktestSide, ...]


def _safe_mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _safe_median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def _path_row(
    frame: pd.DataFrame,
    *,
    entry_position: int,
    exit_position: int,
) -> tuple[float, float, float, int]:
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


def _summarize(
    *,
    key: str,
    label_cn: str,
    rows: list[tuple[float, float, float, int]],
    incomplete_count: int,
) -> PullbackPerformanceStats:
    returns = [row[0] for row in rows]
    return PullbackPerformanceStats(
        key=key,
        label_cn=label_cn,
        sample_count=len(rows),
        incomplete_count=incomplete_count,
        win_rate=(sum(value > 0 for value in returns) / len(returns) if returns else None),
        mean_return=_safe_mean(returns),
        median_return=_safe_median(returns),
        mean_mfe=_safe_mean([row[1] for row in rows]),
        mean_mae=_safe_mean([row[2] for row in rows]),
        mean_holding_days=_safe_mean([float(row[3]) for row in rows]),
    )


def _confirmation_positions(
    frame: pd.DataFrame,
    events: list[SignalEvent],
    ma_period: int,
) -> list[int]:
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    positions: list[int] = []
    for event in events:
        if event.rule_id != RULE_ID:
            continue
        if event.evidence.get("sub_rule") != SUB_RULE_CONFIRMED:
            continue
        if int(event.evidence.get("ma_period", 0)) != ma_period:
            continue
        position = by_day.get(event.available_date)
        if position is not None:
            positions.append(position)
    return sorted(set(positions))


def _fixed_horizon_stats(
    frame: pd.DataFrame,
    entries: list[int],
) -> list[PullbackPerformanceStats]:
    stats: list[PullbackPerformanceStats] = []
    total = len(frame)
    for horizon in PULLBACK_BACKTEST_HORIZONS:
        eligible = [position for position in entries if position + horizon < total]
        rows = [
            _path_row(frame, entry_position=position, exit_position=position + horizon)
            for position in eligible
        ]
        stats.append(
            _summarize(
                key=f"day_{horizon}",
                label_cn=f"{horizon}日",
                rows=rows,
                incomplete_count=len(entries) - len(eligible),
            )
        )
    return stats


def _rule_exit_position(
    frame: pd.DataFrame,
    *,
    entry_position: int,
    ma_period: int,
    tolerance_pct: float,
    tolerance_atr: float,
) -> int | None:
    ma_column = f"sma{ma_period}"
    slope_column = f"sma{ma_period}_slope"
    for position in range(entry_position + 1, len(frame)):
        row = frame.iloc[position]
        ma_value = float(row[ma_column])
        atr = float(row["atr14"])
        tolerance = max(ma_value * tolerance_pct, atr * tolerance_atr)
        if str(row["signal_color"]) == "black":
            return position
        if float(row[slope_column]) <= 0:
            return position
        if float(row["close"]) < ma_value - tolerance:
            return position
    return None


def _rule_exit_stats(
    frame: pd.DataFrame,
    entries: list[int],
    ma_period: int,
    tolerance_pct: float,
    tolerance_atr: float,
) -> tuple[PullbackPerformanceStats, int]:
    rows: list[tuple[float, float, float, int]] = []
    open_trades = 0
    for entry in entries:
        exit_position = _rule_exit_position(
            frame,
            entry_position=entry,
            ma_period=ma_period,
            tolerance_pct=tolerance_pct,
            tolerance_atr=tolerance_atr,
        )
        if exit_position is None:
            open_trades += 1
            continue
        rows.append(_path_row(frame, entry_position=entry, exit_position=exit_position))
    return (
        _summarize(
            key="rule_exit",
            label_cn="规则退出",
            rows=rows,
            incomplete_count=open_trades,
        ),
        open_trades,
    )


def build_first_ma_pullback_backtest(
    frame: pd.DataFrame,
    events: list[SignalEvent],
) -> PullbackBacktestReport | None:
    """按 MA20/60/120 分组研究确认事件后的价格路径。"""
    required = {
        "close",
        "high",
        "low",
        "atr14",
        "signal_color",
        "sma20",
        "sma60",
        "sma120",
        "sma20_slope",
        "sma60_slope",
        "sma120_slope",
    }
    if frame.empty or not required.issubset(frame.columns):
        return None

    spec = get_rule(RULE_ID)
    periods = tuple(int(value) for value in spec.param("ma_periods"))
    tolerance_pct = float(spec.param("touch_tolerance_pct"))
    tolerance_atr = float(spec.param("touch_tolerance_atr"))
    sides: list[PullbackBacktestSide] = []
    for period in periods:
        entries = _confirmation_positions(frame, events, period)
        fixed_stats = _fixed_horizon_stats(frame, entries)
        exit_stat, open_trades = _rule_exit_stats(
            frame,
            entries,
            period,
            tolerance_pct,
            tolerance_atr,
        )
        sides.append(
            PullbackBacktestSide(
                ma_period=period,
                title_cn=f"首次回撤 SMA{period}",
                entry_rule_cn="首次回撤确认事件当日，以当时可见收盘价计入",
                exit_rule_cn=(
                    f"首次出现转黑、SMA{period} 方向不再向上，或收盘跌破均线容差时退出"
                ),
                total_signals=len(entries),
                open_trades=open_trades,
                stats=tuple([*fixed_stats, exit_stat]),
            )
        )

    if not any(side.total_signals for side in sides):
        return None
    return PullbackBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=(
            "研究代理事件统计，不是单账户资金曲线；未计手续费、滑点、涨跌停、停牌、"
            "流动性和融券约束。固定周期未完成样本与规则退出未平仓样本均单独计数，"
            "不进入收益、胜率、MFE 或 MAE。"
        ),
        sides=tuple(sides),
    )


__all__ = [
    "PULLBACK_BACKTEST_HORIZONS",
    "PullbackBacktestReport",
    "PullbackBacktestSide",
    "PullbackPerformanceStats",
    "build_first_ma_pullback_backtest",
]
