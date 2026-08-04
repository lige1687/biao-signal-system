"""回测按 A/B/C/D 交易模块分别统计（规格第 12 节）。

规格第 12 节要求：趋势跟随模块与逆势反转模块必须分别统计，不能让一个普通回调信号
与一个 2B 反转信号在同一笔交易中相互改写理由。本模块把入场确认事件按交易模块归属
分组，分别统计固定周期表现，并额外给出"趋势跟随(A+B)"与"逆势反转(C+D)"两大类汇总。

模块映射（B/C 待第二轮实现，框架已预留）：
  A = 首次均线回撤（first_ma_pullback）       —— 趋势跟随
  B = 均线密集区突破（待实现）                 —— 趋势跟随
  C = 2B/破底翻（待实现）                      —— 逆势反转
  D = 假突破快速收回（false_breakout_reclaim） —— 逆势反转

按模块分桶统计本身就结构性地保证了"不同模块信号不在同一笔交易中改写理由"：
A 的样本与 D 的样本物理隔离，互不串写。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.domain.types import SignalEvent
from lei_signal.research.scenario_backtest_common import (
    RESEARCH_DISCLAIMER,
    ScenarioBacktestReport,
    ScenarioBacktestSide,
    fixed_horizon_stats,
)

#: rule_id -> (模块, 大类, 中文名)。B/C 待实现，预留映射便于第二轮接入。
MODULE_MAP: dict[str, tuple[str, str, str]] = {
    "first_ma_pullback": ("A", "trend_following", "稳定上升趋势回调"),
    "false_breakout_reclaim": ("D", "reversal", "假突破反向"),
    # "dense_breakout": ("B", "trend_following", "均线密集区突破"),   # 待实现
    # "two_b_reversal": ("C", "reversal", "2B/破底翻"),               # 待实现
}

#: 每个模块的入场确认子规则。
ENTRY_CONFIRMED_SUBS: dict[str, str] = {
    "first_ma_pullback": "first_ma_pullback_confirmed",
    "false_breakout_reclaim": "false_breakout_reclaim_confirmed",
}

CATEGORY_CN: dict[str, str] = {
    "trend_following": "趋势跟随(A+B)",
    "reversal": "逆势反转(C+D)",
}


def module_of(rule_id: str) -> str | None:
    """返回 rule_id 所属模块（A/B/C/D），未映射返回 None。"""
    entry = MODULE_MAP.get(rule_id)
    return entry[0] if entry else None


def _entry_positions_by_rule(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> dict[str, list[int]]:
    """按 rule_id 收集各模块入场确认事件的行情位置（按日去重）。"""
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    out: dict[str, list[int]] = {rule_id: [] for rule_id in MODULE_MAP}
    for event in events:
        if event.rule_id not in MODULE_MAP:
            continue
        if event.evidence.get("sub_rule") != ENTRY_CONFIRMED_SUBS[event.rule_id]:
            continue
        position = by_day.get(event.available_date)
        if position is not None:
            out[event.rule_id].append(position)
    return {rule_id: sorted(set(positions)) for rule_id, positions in out.items()}


def build_module_backtest(
    frame: pd.DataFrame, events: list[SignalEvent]
) -> ScenarioBacktestReport | None:
    """按 A/B/C/D 模块 + 趋势跟随/逆势反转大类分别统计入场后固定周期表现。"""
    required = {"open", "high", "low", "close"}
    if frame.empty or not required.issubset(frame.columns):
        return None

    positions_by_rule = _entry_positions_by_rule(frame, events)
    if not any(positions_by_rule.values()):
        return None

    # 模块级分桶（A、D；B/C 待实现）
    sides: list[ScenarioBacktestSide] = []
    for rule_id, (module, _category, module_cn) in MODULE_MAP.items():
        entries = positions_by_rule[rule_id]
        sides.append(
            ScenarioBacktestSide(
                key=f"module_{module}",
                title_cn=f"模块{module}·{module_cn}",
                entry_rule_cn=f"{rule_id} 确认事件当日，以当时可见收盘价计入",
                exit_rule_cn="仅固定周期统计（5/10/20/60/120日）；模块分桶，不与其他模块混算",
                total_signals=len(entries),
                open_trades=0,
                stats=tuple(fixed_horizon_stats(frame, entries)),
            )
        )

    # 大类汇总：趋势跟随(A+B) / 逆势反转(C+D)
    for category, category_cn in CATEGORY_CN.items():
        entries = sorted(
            {
                pos
                for rule_id, (_, cat, _) in MODULE_MAP.items()
                if cat == category
                for pos in positions_by_rule[rule_id]
            }
        )
        sides.append(
            ScenarioBacktestSide(
                key=f"category_{category}",
                title_cn=category_cn,
                entry_rule_cn="该大类全部模块入场确认当日，以当时可见收盘价计入",
                exit_rule_cn="仅固定周期统计；趋势跟随与逆势反转分别统计，不互相改写理由（规格12）",
                total_signals=len(entries),
                open_trades=0,
                stats=tuple(fixed_horizon_stats(frame, entries)),
            )
        )

    return ScenarioBacktestReport(
        start_date=frame.index[0].date().isoformat(),
        end_date=frame.index[-1].date().isoformat(),
        total_bars=len(frame),
        research_disclaimer_cn=(
            RESEARCH_DISCLAIMER
            + " 模块 B（密集突破）/C（2B破底翻）待第二轮实现，当前仅统计 A 与 D。"
            " 趋势跟随与逆势反转分桶统计，不在同一笔交易中改写理由。"
        ),
        sides=tuple(sides),
    )


__all__ = [
    "CATEGORY_CN",
    "ENTRY_CONFIRMED_SUBS",
    "MODULE_MAP",
    "build_module_backtest",
    "module_of",
]
