"""2B/破底翻确认事件的固定周期与规则退出研究（规格 §9 模块 C）。

三版本（v1/v2/v3）分别统计：v1=收盘站上 L1；v2=+EMA20 拐头向上；v3=+EMA20 与 SMA20
共同向上。规则退出 = C3 失效（收盘跌破 L2）。未完成/未平仓样本单独计数，不进收益统计。
"""
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
from lei_signal.rules.two_b_reversal import (
    RULE_ID,
    SUB_RULE_V1,
    SUB_RULE_V2,
    SUB_RULE_V3,
)

#: 三版本入场子规则 -> 中文标题。
_VERSIONS: tuple[tuple[str, str, str], ...] = (
    (SUB_RULE_V1, "v1", "2B·v1 收盘站上 L1"),
    (SUB_RULE_V2, "v2", "2B·v2 站上 L1+EMA20 拐头"),
    (SUB_RULE_V3, "v3", "2B·v3 站上 L1+双均线共同向上"),
)


def _confirmation_positions(
    frame: pd.DataFrame, events: list[SignalEvent], sub_rule: str
) -> list[tuple[int, float]]:
    """返回 (行情位置, L2 失效价)。"""
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    out: list[tuple[int, float]] = []
    for event in events:
        if event.rule_id != RULE_ID or event.evidence.get("sub_rule") != sub_rule:
            continue
        position = by_day.get(event.available_date)
        l2 = float(event.evidence.get("l2_price") or 0.0)
        if position is not None and l2 > 0:
            out.append((position, l2))
    return out


def build_two_b_reversal_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """研究 2B/破底翻三版本确认后的价格路径。"""
    required = {"open", "high", "low", "close", "ema20", "sma20", "signal_color"}
    if frame.empty or not required.issubset(frame.columns):
        return None

    sides: list[ScenarioBacktestSide] = []
    any_signals = False
    for sub_rule, version, title_cn in _VERSIONS:
        entries = _confirmation_positions(frame, events, sub_rule)
        if entries:
            any_signals = True

        # 规则退出 = C3：收盘跌破 L2（结构失效线）。
        def exit_predicate(l2_price: float):
            def predicate(row: pd.Series) -> bool:  # noqa: ANN001
                return float(row["close"]) < l2_price

            return predicate

        rows: list[tuple[float, float, float, int]] = []
        open_trades = 0
        for position, l2 in entries:
            exit_position = rule_exit_position(frame, position, exit_predicate(l2))
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
        sides.append(
            ScenarioBacktestSide(
                key=f"two_b_{version}",
                title_cn=title_cn,
                entry_rule_cn="确认事件当日，以当时可见收盘价计入",
                exit_rule_cn="首次收盘跌破 L2（结构失效线）时退出",
                total_signals=len(entries),
                open_trades=open_trades,
                stats=tuple([*fixed_horizon_stats(frame, [p for p, _ in entries]), exit_stat]),
            )
        )

    if not any_signals:
        return None
    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=RESEARCH_DISCLAIMER,
        sides=tuple(sides),
    )


__all__ = ["build_two_b_reversal_backtest"]
