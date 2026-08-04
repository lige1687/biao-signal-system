"""次级别确认（日线代理）确认事件的固定周期与规则退出研究。"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import SignalEvent
from lei_signal.research.scenario_backtest_common import (
    ScenarioBacktestReport,
    ScenarioBacktestSide,
    fixed_horizon_stats,
    path_metrics,
    rule_exit_position,
    summarize,
)
from lei_signal.rules.low_level_confirmation import (
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


def _trigger_holds(row: pd.Series) -> bool:  # noqa: ANN001
    return bool(
        float(row["sma20"]) > float(row["sma60"]) > float(row["sma120"])
        and str(row["signal_color"]) == "green"
        and float(row["close"]) >= float(row["ema20"])
        and float(row["close"]) >= float(row["sma20"])
        and float(row["close"]) > float(row["open"])
        and float(row["sma20_slope"]) > 0
    )


def build_low_level_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """研究次级别确认（日线代理）后的价格路径。"""
    required = {
        "open",
        "high",
        "low",
        "close",
        "signal_color",
        "ema20",
        "sma20",
        "sma60",
        "sma120",
        "sma20_slope",
    }
    if frame.empty or not required.issubset(frame.columns):
        return None

    entries = _confirmation_positions(frame, events)
    if not entries:
        return None

    def exit_predicate(ref: float):
        def predicate(row: pd.Series) -> bool:  # noqa: ANN001
            if float(row["close"]) < ref:
                return True
            return not _trigger_holds(row)

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
        key="low_level_confirmation",
        title_cn="次级别确认（日线代理）",
        entry_rule_cn="次级别确认当日，以当时可见收盘价计入",
        exit_rule_cn="日线做多信号失效（完整多头排列/双均线共同确认不再成立）或收盘跌破参考支撑时退出",
        total_signals=len(entries),
        open_trades=open_trades,
        stats=tuple([*fixed_horizon_stats(frame, [p for p, _ in entries]), exit_stat]),
    )
    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=(
            "次级别确认（日线代理）事件统计，不是单账户资金曲线；以日线 OHLC 代理 60 分钟"
            "次级别确认，未接入真 60 分钟数据。未计手续费、滑点、涨跌停、停牌、流动性与融券约束；"
            "未完成样本与未平仓样本单独计数，不进入收益、胜率、MFE 或 MAE。"
        ),
        sides=(side,),
    )


__all__ = ["build_low_level_backtest"]
