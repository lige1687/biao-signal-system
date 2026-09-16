"""完整均线排列成立事件（多头/空头）的固定周期与规则退出研究。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import SignalEvent
from lei_signal.research.scenario_backtest_common import (
    RESEARCH_DISCLAIMER,
    ScenarioBacktestReport,
    ScenarioBacktestSide,
    fixed_horizon_stats,
    rule_exit_stats,
)
from lei_signal.rules.ma_full_alignment import (
    RULE_ID,
    SUB_RULE_BEARISH_START,
    SUB_RULE_BULLISH_START,
)


def _start_positions(
    frame: pd.DataFrame, events: list[SignalEvent], sub_rule: str
) -> list[int]:
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    out: list[int] = []
    for event in events:
        if event.rule_id != RULE_ID or event.evidence.get("sub_rule") != sub_rule:
            continue
        position = by_day.get(event.available_date)
        if position is not None:
            out.append(position)
    return sorted(set(out))


def _bullish_predicate(row: pd.Series) -> bool:  # noqa: ANN001
    return not (
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and float(row["sma20_slope"]) > 0
        and float(row["sma60_slope"]) > 0
        and float(row["sma120_slope"]) > 0
    )


def _bearish_predicate(row: pd.Series) -> bool:  # noqa: ANN001
    return not (
        float(row["sma20"]) < float(row["sma60"]) < float(row["sma120"])
        and float(row["sma20_slope"]) < 0
        and float(row["sma60_slope"]) < 0
        and float(row["sma120_slope"]) < 0
    )


def build_alignment_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """按方向研究完整均线排列成立后的价格路径。"""
    required = {
        "close",
        "high",
        "low",
        "sma20",
        "sma60",
        "sma120",
        "sma20_slope",
        "sma60_slope",
        "sma120_slope",
    }
    if frame.empty or not required.issubset(frame.columns):
        return None

    sides: list[ScenarioBacktestSide] = []
    for sub_rule, key, title, predicate in (
        (SUB_RULE_BULLISH_START, "bullish", "完整多头排列", _bullish_predicate),
        (SUB_RULE_BEARISH_START, "bearish", "完整空头排列", _bearish_predicate),
    ):
        entries = _start_positions(frame, events, sub_rule)
        if not entries:
            continue
        exit_stat, open_trades = rule_exit_stats(frame, entries, predicate)
        sides.append(
            ScenarioBacktestSide(
                key=key,
                title_cn=title,
                entry_rule_cn="完整排列成立当日，以当时可见收盘价计入",
                exit_rule_cn="完整排列方向不再满足（均线相对位置或方向破坏）时退出",
                total_signals=len(entries),
                open_trades=open_trades,
                stats=tuple([*fixed_horizon_stats(frame, entries), exit_stat]),
            )
        )

    if not sides:
        return None
    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=RESEARCH_DISCLAIMER,
        sides=tuple(sides),
    )


__all__ = ["build_alignment_backtest"]
