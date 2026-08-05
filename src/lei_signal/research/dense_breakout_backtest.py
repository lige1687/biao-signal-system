"""均线密集区突破确认事件的固定周期与规则退出研究（规格 §9 模块 B）。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import SignalEvent
from lei_signal.research.scenario_backtest_common import (
    RESEARCH_DISCLAIMER,
    ScenarioBacktestReport,
    ScenarioBacktestSide,
    fixed_horizon_stats,
    path_metrics,
    rule_exit_position,
    summarize,
)
from lei_signal.rules.dense_breakout import RULE_ID, SUB_RULE_CONFIRMED


def _confirmation_positions(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> list[tuple[int, float]]:
    """返回 (行情位置, 突破时锁定的密集区上沿)。"""
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    out: list[tuple[int, float]] = []
    for event in events:
        if event.rule_id != RULE_ID or event.evidence.get("sub_rule") != SUB_RULE_CONFIRMED:
            continue
        position = by_day.get(event.available_date)
        ref = float(
            event.evidence.get("breakout_reference")
            or event.evidence.get("reference_price")
            or 0.0
        )
        if position is not None and ref > 0:
            out.append((position, ref))
    return out


def build_dense_breakout_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """研究均线密集区突破确认后的价格路径。"""
    required = {
        "open", "high", "low", "close", "atr14", "signal_color",
        "sma20", "sma60", "sma120", "sma20_slope",
    }
    if frame.empty or not required.issubset(frame.columns):
        return None

    entries = _confirmation_positions(frame, events)
    if not entries:
        return None

    # 规则退出 = B3 失效：收盘跌回密集区上沿下方且 SMA20 方向向下弯曲。
    def exit_predicate(breakout_reference: float):
        def predicate(row: pd.Series) -> bool:  # noqa: ANN001
            if float(row["close"]) < breakout_reference and float(row["sma20_slope"]) < 0:
                return True
            # 完整多头排列破坏或转黑同样视为趋势逻辑退出。
            if not (float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])):
                return True
            return str(row["signal_color"]) == "black"

        return predicate

    rows: list[tuple[float, float, float, int]] = []
    open_trades = 0
    for position, ref in entries:
        exit_position = rule_exit_position(frame, position, exit_predicate(ref))
        if exit_position is None:
            open_trades += 1
            continue
        rows.append(path_metrics(frame, entry_position=position, exit_position=exit_position))
    exit_stat = summarize(
        key="rule_exit",
        label_cn="规则退出",
        rows=rows,
        incomplete_count=open_trades,
    )

    side = ScenarioBacktestSide(
        key="dense_breakout",
        title_cn="均线密集区突破",
        entry_rule_cn="确认事件当日，以当时可见收盘价计入",
        exit_rule_cn="首次跌回密集区上沿下方且 SMA20 下弯、完整多头排列破坏或转黑时退出",
        total_signals=len(entries),
        open_trades=open_trades,
        stats=tuple([*fixed_horizon_stats(frame, [p for p, _ in entries]), exit_stat]),
    )
    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=RESEARCH_DISCLAIMER,
        sides=(side,),
    )


__all__ = ["build_dense_breakout_backtest"]
