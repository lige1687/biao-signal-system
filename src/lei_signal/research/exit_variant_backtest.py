"""模块 A 持仓退出的三版本研究（规格 A6①②③）。

以首次均线回撤确认事件为模块 A 入场样本（SMA20/60/120 全部合并、按日去重），
分别统计三种退出方式在相同样本上的表现，便于横向比较哪种退出更优：

① 抵扣价退出（A6①）：收盘同时跌破 EMA20 与 20 日抵扣价；
② 顶部构造 + 反向关键性波动（A6②）：Top+Black 组合状态当日；
③ 结构止损（A6③）：底部结构 C 被触及/跌破当日。

重叠事件研究口径，非单账户资金曲线；未平仓样本单独计数，不进入收益统计。
三版本必须分别统计，不得只保留表现较好的版本（规格第 8.3 节）。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.types import SignalEvent
from lei_signal.research.scenario_backtest_common import (
    RESEARCH_DISCLAIMER,
    ScenarioBacktestReport,
    ScenarioBacktestSide,
    fixed_horizon_stats,
    rule_exit_stats,
)
from lei_signal.rules.first_ma_pullback import (
    RULE_ID as PULLBACK_RULE_ID,
)
from lei_signal.rules.first_ma_pullback import (
    SUB_RULE_CONFIRMED as PULLBACK_CONFIRMED,
)

KEY_WAVE_RULE_ID = "key_wave_black"
C_LIFECYCLE_RULE_ID = "bottom_c_lifecycle"
TOP_PLUS_BLACK_START = "top_plus_black"
TOP_PLUS_BLACK_END = "top_plus_black_ended"
C_TOUCHED_SUBS = ("bottom_C_touched", "bottom_C_close_broken")


def _module_a_entry_positions(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> list[int]:
    """模块 A 入场 = 首次均线回撤确认事件，按日去重。"""
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    positions: list[int] = []
    for event in events:
        if event.rule_id != PULLBACK_RULE_ID:
            continue
        if event.evidence.get("sub_rule") != PULLBACK_CONFIRMED:
            continue
        position = by_day.get(event.available_date)
        if position is not None:
            positions.append(position)
    return sorted(set(positions))


def _active_dates_from_state_events(
    events: list[SignalEvent],
    rule_id: str,
    start_sub: str,
    end_sub: str,
    frame: pd.DataFrame,
) -> set[date]:
    """从状态型事件（start/end）重建逐日"活跃日期"集合。

    同一天若同时出现 end 与 start（顶部轮换），先处理 end 再 start，使当天仍计为活跃。
    end 当天条件已不成立，不计入；start 当天条件成立，计入。
    """
    by_date: dict[date, list[str]] = {}
    for event in events:
        if event.rule_id != rule_id:
            continue
        sub = event.evidence.get("sub_rule")
        if sub in (start_sub, end_sub):
            by_date.setdefault(event.available_date, []).append(sub)
    active: set[date] = set()
    is_active = False
    for timestamp in frame.index:
        day = timestamp.date()
        subs = by_date.get(day, [])
        if end_sub in subs:
            is_active = False
        if start_sub in subs:
            is_active = True
        if is_active:
            active.add(day)
    return active


def _point_dates_from_events(
    events: list[SignalEvent], rule_id: str, sub_rules: tuple[str, ...]
) -> set[date]:
    """单次事件（如 C 点触及）的 available_date 集合。"""
    return {
        event.available_date
        for event in events
        if event.rule_id == rule_id and event.evidence.get("sub_rule") in sub_rules
    }


def build_exit_variant_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """模块 A 三种退出方式的分别统计。"""
    required = {"open", "high", "low", "close", "ema20", "close_lag20"}
    if frame.empty or not required.issubset(frame.columns):
        return None

    entries = _module_a_entry_positions(frame, events)
    if not entries:
        return None

    top_black_days = _active_dates_from_state_events(
        events,
        rule_id=KEY_WAVE_RULE_ID,
        start_sub=TOP_PLUS_BLACK_START,
        end_sub=TOP_PLUS_BLACK_END,
        frame=frame,
    )
    c_broken_days = _point_dates_from_events(
        events, rule_id=C_LIFECYCLE_RULE_ID, sub_rules=C_TOUCHED_SUBS
    )

    def costbasis_predicate(row: pd.Series) -> bool:  # noqa: ANN001
        close = row.get("close")
        ema20 = row.get("ema20")
        lag = row.get("close_lag20")
        if close is None or ema20 is None or lag is None:
            return False
        if pd.isna(close) or pd.isna(ema20) or pd.isna(lag):
            return False
        return bool(float(close) < float(ema20) and float(close) < float(lag))

    def top_black_predicate(row: pd.Series) -> bool:  # noqa: ANN001
        return bool(pd.Timestamp(row.name).date() in top_black_days)

    def structure_stop_predicate(row: pd.Series) -> bool:  # noqa: ANN001
        return bool(pd.Timestamp(row.name).date() in c_broken_days)

    variants = (
        (
            "exit_costbasis",
            "①抵扣价退出（A6①）",
            "首次均线回撤确认当日，以当时可见收盘价计入",
            "收盘同时跌破 EMA20 与 20 日抵扣价（下一交易日退出）",
            costbasis_predicate,
        ),
        (
            "exit_top_plus_black",
            "②顶部+关键波动（A6②）",
            "首次均线回撤确认当日，以当时可见收盘价计入",
            "Top+Black 组合状态成立当日退出（顶部警报 + 转黑）",
            top_black_predicate,
        ),
        (
            "exit_structure_stop",
            "③结构止损（A6③）",
            "首次均线回撤确认当日，以当时可见收盘价计入",
            "底部结构 C 被触及/跌破当日退出（任意存活结构）",
            structure_stop_predicate,
        ),
    )

    sides: list[ScenarioBacktestSide] = []
    for key, title_cn, entry_rule_cn, exit_rule_cn, predicate in variants:
        fixed = fixed_horizon_stats(frame, entries)
        exit_stat, open_trades = rule_exit_stats(frame, entries, predicate)
        sides.append(
            ScenarioBacktestSide(
                key=key,
                title_cn=title_cn,
                entry_rule_cn=entry_rule_cn,
                exit_rule_cn=exit_rule_cn,
                total_signals=len(entries),
                open_trades=open_trades,
                stats=tuple([*fixed, exit_stat]),
            )
        )

    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=RESEARCH_DISCLAIMER,
        sides=tuple(sides),
    )


__all__ = ["build_exit_variant_backtest"]
