"""绿灰黑状态翻转的固定持有期与状态退出研究。

本模块只研究信号出现后的客观价格路径，不模拟资金曲线：
- 做多：非绿 -> 绿，以信号日收盘计入；状态退出为首次转灰或转黑的收盘。
- 做空：非黑 -> 黑，以信号日收盘计入；每个信号独立跟踪到首次重新转绿的收盘，
  灰色期间不退出。不同信号的观察窗口可以重叠，因此这不是单账户资金曲线。
- 固定观察期：5/10/20/60/120 个交易日。

全部价格都按当时可见的收盘价计算，不使用未来数据决定入场；未完成的观察期或
尚未触发退出的交易不进入对应统计，并单独报告数量。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

COLOR_BACKTEST_HORIZONS = (5, 10, 20, 60, 120)


@dataclass(frozen=True)
class ColorPerformanceStats:
    """一个固定观察期或状态退出策略的汇总。"""

    key: str
    label_cn: str
    sample_count: int
    win_rate: float | None
    mean_return: float | None
    median_return: float | None
    mean_mfe: float | None
    mean_mae: float | None
    mean_holding_days: float | None


@dataclass(frozen=True)
class ColorBacktestSide:
    """单一方向（做多或做空）的回测汇总。"""

    side: str
    title_cn: str
    entry_rule_cn: str
    exit_rule_cn: str
    total_signals: int
    open_trades: int
    stats: tuple[ColorPerformanceStats, ...]


@dataclass(frozen=True)
class ColorBacktestReport:
    """一个标的的绿灰黑信号回测报告。"""

    start_date: str
    end_date: str
    total_bars: int
    long: ColorBacktestSide
    short: ColorBacktestSide


def _safe_mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _safe_median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def _summarize(
    *,
    key: str,
    label_cn: str,
    rows: list[tuple[float, float, float, int]],
) -> ColorPerformanceStats:
    returns = [row[0] for row in rows]
    return ColorPerformanceStats(
        key=key,
        label_cn=label_cn,
        sample_count=len(rows),
        win_rate=(sum(value > 0 for value in returns) / len(returns) if returns else None),
        mean_return=_safe_mean(returns),
        median_return=_safe_median(returns),
        mean_mfe=_safe_mean([row[1] for row in rows]),
        mean_mae=_safe_mean([row[2] for row in rows]),
        mean_holding_days=_safe_mean([float(row[3]) for row in rows]),
    )


def _path_row(
    frame: pd.DataFrame,
    *,
    entry_position: int,
    exit_position: int,
    side: str,
) -> tuple[float, float, float, int]:
    """计算一笔方向调整后的收益、MFE、MAE 与持有日数。"""
    entry = float(frame["close"].iloc[entry_position])
    exit_close = float(frame["close"].iloc[exit_position])
    future = frame.iloc[entry_position + 1 : exit_position + 1]
    high = float(future["high"].astype(float).max())
    low = float(future["low"].astype(float).min())

    if side == "long":
        strategy_return = (exit_close / entry - 1.0) * 100.0
        mfe = (high / entry - 1.0) * 100.0
        mae = (low / entry - 1.0) * 100.0
    else:
        # 做空方向收益采用价格跌幅取正：(entry-exit)/entry。
        strategy_return = (1.0 - exit_close / entry) * 100.0
        mfe = (1.0 - low / entry) * 100.0
        mae = (1.0 - high / entry) * 100.0
    return strategy_return, mfe, mae, exit_position - entry_position


def _entry_positions(colors: pd.Series, target: str) -> list[int]:
    previous = colors.shift(1)
    mask = colors.eq(target) & colors.ne(previous)
    return [int(position) for position in np.flatnonzero(mask.to_numpy())]


def _fixed_horizon_stats(
    frame: pd.DataFrame,
    *,
    entries: list[int],
    side: str,
) -> list[ColorPerformanceStats]:
    stats: list[ColorPerformanceStats] = []
    total = len(frame)
    for horizon in COLOR_BACKTEST_HORIZONS:
        rows = [
            _path_row(frame, entry_position=position, exit_position=position + horizon, side=side)
            for position in entries
            if position + horizon < total
        ]
        stats.append(
            _summarize(key=f"day_{horizon}", label_cn=f"{horizon}日", rows=rows)
        )
    return stats


def _long_signal_exit_rows(
    frame: pd.DataFrame, entries: list[int]
) -> tuple[list[tuple[float, float, float, int]], int]:
    colors = frame["signal_color"].astype(str)
    rows: list[tuple[float, float, float, int]] = []
    open_trades = 0
    for position in entries:
        future = colors.iloc[position + 1 :]
        exits = np.flatnonzero(future.isin(("gray", "black")).to_numpy())
        if len(exits) == 0:
            open_trades += 1
            continue
        exit_position = position + 1 + int(exits[0])
        rows.append(
            _path_row(frame, entry_position=position, exit_position=exit_position, side="long")
        )
    return rows, open_trades


def _short_signal_exit_rows(
    frame: pd.DataFrame, entries: list[int]
) -> tuple[list[tuple[float, float, float, int]], int]:
    """每次转黑独立跟踪到下一次绿色；灰色不触发退出。"""
    colors = frame["signal_color"].astype(str)
    rows: list[tuple[float, float, float, int]] = []
    open_trades = 0
    for position in entries:
        future = colors.iloc[position + 1 :]
        exits = np.flatnonzero(future.eq("green").to_numpy())
        if len(exits) == 0:
            open_trades += 1
            continue
        exit_position = position + 1 + int(exits[0])
        rows.append(
            _path_row(frame, entry_position=position, exit_position=exit_position, side="short")
        )
    return rows, open_trades


def build_color_backtest(frame: pd.DataFrame) -> ColorBacktestReport | None:
    """构建绿灰黑信号回测摘要；数据不足或缺列时返回 None。"""
    required = {"close", "high", "low", "signal_color"}
    if frame.empty or not required.issubset(frame.columns):
        return None

    clean = frame.loc[frame["signal_color"].astype(str).ne("unknown")].copy()
    if len(clean) < 2:
        return None

    colors = clean["signal_color"].astype(str)
    long_entries = _entry_positions(colors, "green")
    short_entries = _entry_positions(colors, "black")

    long_exit_rows, long_open = _long_signal_exit_rows(clean, long_entries)
    short_exit_rows, short_open = _short_signal_exit_rows(clean, short_entries)

    long_stats = _fixed_horizon_stats(clean, entries=long_entries, side="long")
    long_stats.append(_summarize(key="signal_exit", label_cn="信号退出", rows=long_exit_rows))

    short_stats = _fixed_horizon_stats(clean, entries=short_entries, side="short")
    short_stats.append(_summarize(key="signal_exit", label_cn="信号退出", rows=short_exit_rows))

    return ColorBacktestReport(
        start_date=clean.index[0].date().isoformat(),
        end_date=clean.index[-1].date().isoformat(),
        total_bars=len(clean),
        long=ColorBacktestSide(
            side="long",
            title_cn="转绿 · 做多",
            entry_rule_cn="非绿转绿，以信号日可见收盘价计入",
            exit_rule_cn="首次绿转灰或绿转黑时，以当日收盘价退出",
            total_signals=len(long_entries),
            open_trades=long_open,
            stats=tuple(long_stats),
        ),
        short=ColorBacktestSide(
            side="short",
            title_cn="转黑 · 做空",
            entry_rule_cn="每次非黑转黑都作为独立信号，以当日可见收盘价计入",
            exit_rule_cn="每个信号独立跟踪至首次重新转绿；灰色期间不退出",
            total_signals=len(short_entries),
            open_trades=short_open,
            stats=tuple(short_stats),
        ),
    )


__all__ = [
    "COLOR_BACKTEST_HORIZONS",
    "ColorBacktestReport",
    "ColorBacktestSide",
    "ColorPerformanceStats",
    "build_color_backtest",
]
