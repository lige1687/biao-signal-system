"""盈亏比分桶回测（规格第 10 节，研究代理，只算不强制）。

对模块 A/D 做多入场确认事件计算 R/R，再按 R/R≥3、R/R≥5、目标不可计算三桶
分别统计固定周期表现，检验“高盈亏比样本是否表现更好”。重叠事件研究口径，
未完成样本单独计数，不进入收益统计。不做硬过滤。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import Pivot, SignalEvent
from lei_signal.research.scenario_backtest_common import (
    RESEARCH_DISCLAIMER,
    ScenarioBacktestReport,
    ScenarioBacktestSide,
    fixed_horizon_stats,
)
from lei_signal.rules.reward_risk_filter import (
    compute_reward_risk_for_entries,
)

RR_MIN_IDEAL = 3.0
RR_MIN_STRONG = 5.0


def _entry_positions(
    frame: pd.DataFrame, results: list, predicate  # noqa: ANN001
) -> list[int]:
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    positions = [
        by_day[result.available_date]
        for result in results
        if predicate(result) and result.available_date in by_day
    ]
    return sorted(set(positions))


def build_reward_risk_backtest(
    frame: pd.DataFrame,
    events: list[SignalEvent],
    pivots: tuple[Pivot, ...],
) -> ScenarioBacktestReport | None:
    """按 R/R 分桶统计入场后固定周期表现。"""
    required = {"open", "high", "low", "close"}
    if frame.empty or not required.issubset(frame.columns):
        return None

    results = compute_reward_risk_for_entries(frame, events, pivots)
    if not results:
        return None

    buckets = (
        (
            "rr_ge3",
            f"R/R≥{RR_MIN_IDEAL:g}",
            "模块A/D做多入场确认当日，以当时可见收盘价计入；R/R≥3 的样本",
            lambda r: r.computable and r.reward_risk is not None and r.reward_risk >= RR_MIN_IDEAL,
        ),
        (
            "rr_ge5",
            f"R/R≥{RR_MIN_STRONG:g}",
            "模块A/D做多入场确认当日，以当时可见收盘价计入；R/R≥5 的样本",
            lambda r: r.computable and r.reward_risk is not None and r.reward_risk >= RR_MIN_STRONG,
        ),
        (
            "rr_unknown",
            "目标不可计算",
            "模块A/D做多入场确认当日，以当时可见收盘价计入；无法客观确定目标的样本",
            lambda r: not r.computable,
        ),
    )

    sides: list[ScenarioBacktestSide] = []
    for key, title_cn, entry_rule_cn, predicate in buckets:
        entries = _entry_positions(frame, results, predicate)
        sides.append(
            ScenarioBacktestSide(
                key=key,
                title_cn=title_cn,
                entry_rule_cn=entry_rule_cn,
                exit_rule_cn="仅固定周期统计（5/10/20/60/120日），不接规则退出；R/R 只算不强制",
                total_signals=len(entries),
                open_trades=0,
                stats=tuple(fixed_horizon_stats(frame, entries)),
            )
        )

    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=RESEARCH_DISCLAIMER,
        sides=tuple(sides),
    )


__all__ = ["RR_MIN_IDEAL", "RR_MIN_STRONG", "build_reward_risk_backtest"]
