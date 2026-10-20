"""信号含金量统计：路牌与触发事件的历史胜率 / 赔率 vs 无条件基准。

方法论来源（2026-09-05 文主任调研增量，任务书 #1）：任何信号先算历史账——
该状态出现后固定持有期的收益分布、胜率、赔率，再与「无条件基准」（不看信号
随便挑一天做的同口径统计）比较，高出基准的幅度才是信号的真实含金量。

定位：纯研究/展示层，给规则配「含金量说明书」，不改变任何判定逻辑，
不许把统计结果写成新的过滤器（红线）。

统计口径：复用 ``scenario_backtest_common`` 的固定周期口径（``path_metrics``
+ 同一套胜率/均值定义，5/10/20/60 日四档；模块 A/B/C/D 的入场子规则映射
复用 ``module_backtest.ENTRY_CONFIRMED_SUBS``，不另造）。跨标的时把各标的
的逐事件收益行汇成池（pooled），基准同样按各标的全样本日池化，保证
「信号 vs 基准」在同一个标的集合上比较。
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lei_signal.domain.types import SignalEvent
from lei_signal.research.module_backtest import ENTRY_CONFIRMED_SUBS
from lei_signal.research.scenario_backtest_common import (
    path_metrics,
)

#: 含金量表展示的固定持有期（日）。取 SCENARIO_BACKTEST_HORIZONS 的子集。
SIGNPOST_HORIZONS: tuple[int, ...] = (5, 10, 20, 60)

_C_ENTRY_SUBS = ENTRY_CONFIRMED_SUBS["two_b_reversal"]  # v1/v2/v3 三版本


@dataclass(frozen=True)
class SignpostSpec:
    """含金量表的一行：一个可统计的事件类型。"""

    key: str
    label_cn: str
    group: str            # trigger（入场触发）| signpost（预警路牌）
    rule_id: str
    sub_rules: tuple[str, ...]
    direction_cn: str     # 偏多 / 偏空 / 中性预警——帮助读表方向


#: 事件目录：四个入场触发 + 主要预警路牌。子规则名与检测器实际产出的
#: evidence["sub_rule"] 一致（key_wave.py / top_structure.py / lei_color.py /
#: volume.py / 各模块检测器）。
SIGNPOST_CATALOG: tuple[SignpostSpec, ...] = (
    SignpostSpec(
        key="module_a_entry", label_cn="模块A·稳定趋势回调入场",
        group="trigger", rule_id="first_ma_pullback",
        sub_rules=(ENTRY_CONFIRMED_SUBS["first_ma_pullback"],),
        direction_cn="偏多",
    ),
    SignpostSpec(
        key="module_b_entry", label_cn="模块B·均线密集区突破入场",
        group="trigger", rule_id="dense_breakout",
        sub_rules=(ENTRY_CONFIRMED_SUBS["dense_breakout"],),
        direction_cn="偏多",
    ),
    SignpostSpec(
        key="module_c_entry", label_cn="模块C·2B破底翻入场",
        group="trigger", rule_id="two_b_reversal",
        sub_rules=tuple(_C_ENTRY_SUBS),
        direction_cn="偏多",
    ),
    SignpostSpec(
        key="module_d_entry", label_cn="模块D·假突破快速收回入场",
        group="trigger", rule_id="false_breakout_reclaim",
        sub_rules=(ENTRY_CONFIRMED_SUBS["false_breakout_reclaim"],),
        direction_cn="偏多",
    ),
    SignpostSpec(
        key="top_structure_confirmed", label_cn="路牌·顶部构造确认",
        group="signpost", rule_id="top_structure",
        sub_rules=("top_structure_confirmed",),
        direction_cn="偏空预警",
    ),
    SignpostSpec(
        key="key_wave_black_started", label_cn="路牌·反向关键性波动(黑)",
        group="signpost", rule_id="key_wave_black",
        sub_rules=("key_wave_black_started",),
        direction_cn="偏空预警",
    ),
    SignpostSpec(
        key="top_plus_black", label_cn="路牌·顶部构造+黑色共振",
        group="signpost", rule_id="key_wave_black",
        sub_rules=("top_plus_black",),
        direction_cn="偏空预警",
    ),
    SignpostSpec(
        key="lei_color_gray_started", label_cn="路牌·颜色转灰",
        group="signpost", rule_id="lei_color",
        sub_rules=("lei_color_gray_started",),
        direction_cn="中性预警",
    ),
    SignpostSpec(
        key="volume_up_surge", label_cn="路牌·放量上行(量能异常)",
        group="signpost", rule_id="volume_proxies",
        sub_rules=("volume_up_surge",),
        direction_cn="中性预警",
    ),
    SignpostSpec(
        key="bearish_expansion", label_cn="路牌·放量下跌(量能异常)",
        group="signpost", rule_id="volume_proxies",
        sub_rules=("bearish_expansion",),
        direction_cn="偏空预警",
    ),
)

_CATALOG_BY_RULE: dict[str, list[SignpostSpec]] = {}
for _spec in SIGNPOST_CATALOG:
    _CATALOG_BY_RULE.setdefault(_spec.rule_id, []).append(_spec)


@dataclass(frozen=True)
class HorizonEdge:
    """单个事件类型在单个持有期上的含金量行。"""

    horizon: int                 # 持有期（日）
    sample_count: int            # 完成样本数（事件日 + horizon 在数据内）
    incomplete_count: int        # 未完成样本（不进胜率/收益）
    win_rate: float | None       # 事件后 horizon 日内上涨的比例 (0~1)
    baseline_win_rate: float | None   # 无条件基准胜率（同标的集合全样本日）
    excess_win_rate: float | None     # 超额胜率 = win_rate - baseline
    mean_return: float | None    # 平均收益 %（固定持有期末 vs 事件日收盘）
    baseline_mean_return: float | None
    excess_mean_return: float | None
    payoff: float | None         # 盈亏比 = 平均盈利幅度 / |平均亏损幅度|
    baseline_payoff: float | None


@dataclass(frozen=True)
class SignalEdgeRow:
    """含金量表一行：一个事件类型跨全部持有期。"""

    key: str
    label_cn: str
    group: str
    direction_cn: str
    total_signals: int           # 全部历史出现次数（含未完成）
    horizons: tuple[HorizonEdge, ...]


@dataclass(frozen=True)
class SignalEdgeReport:
    rows: tuple[SignalEdgeRow, ...]
    n_symbols: int
    start_date: str
    end_date: str
    disclaimer_cn: str


SIGNAL_EDGE_DISCLAIMER = (
    "研究代理统计：事件出现后固定持有期的重叠事件研究，不是单账户资金曲线；"
    "未计手续费、滑点、涨跌停与停牌。胜率=出现后持有N日上涨的比例；"
    "基准=同一批标的上不看信号随便挑一天做的胜率；超额=信号减基准，"
    "才是信号自己的含金量。路牌类事件只预警不必然反向，统计结果"
    "不得反写为过滤器。"
)


def _positions_for(
    frame: pd.DataFrame,
    events: list[SignalEvent],
    rule_id: str,
    sub_rules: tuple[str, ...],
) -> list[int]:
    """收集匹配 (rule_id, sub_rule) 的确认日行情位置，按日去重。

    与 module_backtest._entry_positions_by_rule 同口径：available_date
    （系统最早能确认的日期）对齐到行情 index。
    """
    by_day = {timestamp.date(): position for position, timestamp in enumerate(frame.index)}
    wanted = set(sub_rules)
    positions: set[int] = set()
    for event in events:
        if event.rule_id != rule_id:
            continue
        if event.evidence.get("sub_rule") not in wanted:
            continue
        position = by_day.get(event.available_date)
        if position is not None:
            positions.add(position)
    return sorted(positions)


def _horizon_rows(
    frames: list[pd.DataFrame], positions_per_frame: list[list[int]], horizon: int
) -> tuple[list[tuple[float, float, float, int]], int]:
    """池化各标的在 horizon 上的逐事件收益行（复用 path_metrics 口径）。"""
    rows: list[tuple[float, float, float, int]] = []
    incomplete = 0
    for frame, positions in zip(frames, positions_per_frame, strict=True):
        total = len(frame)
        for position in positions:
            if position + horizon < total:
                rows.append(path_metrics(frame, position, position + horizon))
            else:
                incomplete += 1
    return rows, incomplete


def _win_rate(rows: list[tuple[float, float, float, int]]) -> float | None:
    if not rows:
        return None
    return sum(1 for row in rows if row[0] > 0) / len(rows)


def _mean_return(rows: list[tuple[float, float, float, int]]) -> float | None:
    if not rows:
        return None
    return sum(row[0] for row in rows) / len(rows)


def _payoff(rows: list[tuple[float, float, float, int]]) -> float | None:
    """盈亏比 = 平均盈利幅度 / |平均亏损幅度|；任一侧无样本则 None。"""
    wins = [row[0] for row in rows if row[0] > 0]
    losses = [row[0] for row in rows if row[0] < 0]
    if not wins or not losses:
        return None
    mean_win = sum(wins) / len(wins)
    mean_loss = sum(losses) / len(losses)
    if mean_loss == 0:
        return None
    return mean_win / abs(mean_loss)


def _baseline_positions(frame: pd.DataFrame, horizon: int) -> list[int]:
    """无条件基准：该标的全部可完成 horizon 持有的交易日。"""
    return list(range(max(0, len(frame) - horizon)))


def build_signal_edge_report(
    samples: list[tuple[pd.DataFrame, list[SignalEvent]]],
) -> SignalEdgeReport | None:
    """跨标的池化计算目录内全部事件的含金量表。

    samples: [(行情 frame, 该标的全部 SignalEvent)]。frame 需要
    open/high/low/close 列（与 fixed_horizon_stats 相同）。
    任一有效样本都没有时返回 None。
    """
    required = {"open", "high", "low", "close"}
    usable = [
        (frame, events)
        for frame, events in samples
        if not frame.empty and required.issubset(frame.columns)
    ]
    if not usable:
        return None
    frames = [frame for frame, _ in usable]

    rows: list[SignalEdgeRow] = []
    for spec in SIGNPOST_CATALOG:
        positions_per_frame = [
            _positions_for(frame, events, spec.rule_id, spec.sub_rules)
            for frame, events in usable
        ]
        total_signals = sum(len(p) for p in positions_per_frame)
        horizon_edges: list[HorizonEdge] = []
        for horizon in SIGNPOST_HORIZONS:
            rows_sig, incomplete = _horizon_rows(frames, positions_per_frame, horizon)
            baseline_positions = [_baseline_positions(frame, horizon) for frame in frames]
            rows_base, _ = _horizon_rows(frames, baseline_positions, horizon)
            win, base_win = _win_rate(rows_sig), _win_rate(rows_base)
            ret, base_ret = _mean_return(rows_sig), _mean_return(rows_base)
            horizon_edges.append(
                HorizonEdge(
                    horizon=horizon,
                    sample_count=len(rows_sig),
                    incomplete_count=incomplete,
                    win_rate=win,
                    baseline_win_rate=base_win,
                    excess_win_rate=(
                        win - base_win
                        if win is not None and base_win is not None
                        else None
                    ),
                    mean_return=ret,
                    baseline_mean_return=base_ret,
                    excess_mean_return=(
                        ret - base_ret
                        if ret is not None and base_ret is not None
                        else None
                    ),
                    payoff=_payoff(rows_sig),
                    baseline_payoff=_payoff(rows_base),
                )
            )
        rows.append(
            SignalEdgeRow(
                key=spec.key,
                label_cn=spec.label_cn,
                group=spec.group,
                direction_cn=spec.direction_cn,
                total_signals=total_signals,
                horizons=tuple(horizon_edges),
            )
        )

    start = min(frame.index[0] for frame in frames)
    end = max(frame.index[-1] for frame in frames)
    return SignalEdgeReport(
        rows=tuple(rows),
        n_symbols=len(frames),
        start_date=start.date().isoformat(),
        end_date=end.date().isoformat(),
        disclaimer_cn=SIGNAL_EDGE_DISCLAIMER,
    )


__all__ = [
    "SIGNPOST_CATALOG",
    "SIGNPOST_HORIZONS",
    "HorizonEdge",
    "SignalEdgeReport",
    "SignalEdgeRow",
    "SignpostSpec",
    "build_signal_edge_report",
]
