"""假突破快速收回确认事件的固定周期与规则退出研究。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.rules_config import get_rule
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
from lei_signal.rules.false_breakout_reclaim import (
    RULE_ID,
    SUB_RULE_CONFIRMED,
)


def _confirmation_positions(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> list[tuple[int, float]]:
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    out: list[tuple[int, float]] = []
    for event in events:
        if event.rule_id != RULE_ID or event.evidence.get("sub_rule") != SUB_RULE_CONFIRMED:
            continue
        position = by_day.get(event.available_date)
        ref = float(event.evidence.get("reference_price", 0.0) or 0.0)
        if position is not None and ref > 0:
            out.append((position, ref))
    return out


def build_false_breakout_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """研究假突破快速收回确认后的价格路径。"""
    required = {
        "open",
        "high",
        "low",
        "close",
        "atr14",
        "signal_color",
        "sma20",
        "sma60",
        "sma120",
    }
    if frame.empty or not required.issubset(frame.columns):
        return None

    spec = get_rule(RULE_ID)
    fail_pct = float(spec.param("fail_breakdown_pct"))
    require_green = bool(spec.param("require_green"))

    entries = _confirmation_positions(frame, events)
    if not entries:
        return None

    def exit_predicate(ref: float):
        def predicate(row: pd.Series) -> bool:  # noqa: ANN001
            if float(row["close"]) < ref * (1.0 - fail_pct):
                return True
            if not (float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])):
                return True
            return require_green and str(row["signal_color"]) == "black"

        return predicate

    rows: list[tuple[float, float, float, int]] = []  # noqa: F841
    open_trades = 0
    for position, ref in entries:
        exit_position = rule_exit_position(frame, position, exit_predicate(ref))
        if exit_position is None:
            open_trades += 1
            continue
        rows.append(path_metrics(frame, entry_position=position, exit_position=exit_position))
    exit_stat, open_trades = summarize(
        key="rule_exit",
        label_cn="规则退出",
        rows=rows,
        incomplete_count=open_trades,
    ), open_trades

    side = ScenarioBacktestSide(
        key="false_breakout_reclaim",
        title_cn="假突破快速收回",
        entry_rule_cn="确认事件当日，以当时可见收盘价计入",
        exit_rule_cn="首次真跌破参考位、完整多头排列破坏或转黑时退出",
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


__all__ = ["build_false_breakout_backtest"]
