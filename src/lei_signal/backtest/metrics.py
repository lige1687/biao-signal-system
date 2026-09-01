"""§16 全量指标与分组统计。

即使不计算真实仓位，也把每笔交易标准化成 R（规格 §16）。至少输出：
交易次数、胜率、平均盈利 R、平均亏损 R、每笔平均期望 R、盈利因子、
最大连续亏损笔数、固定 1R 累计的最大回撤、平均持仓时间——以及分年份、
牛/熊/横盘、模块/退出方式、时钟类型、大周期同向/逆向、样本内外、
含/不含费用的分组。不只报总收益或胜率。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from lei_signal.backtest.engine import Trade
from lei_signal.rules.clock_classifier import (
    TYPE1_ACCELERATING_UP,
    TYPE2_STEADY_UP,
    TYPE3_SIDEWAYS,
    TYPE4_STEADY_DOWN,
    TYPE5_ACCELERATING_DOWN,
)

REGIME_BULL = "bull"
REGIME_BEAR = "bear"
REGIME_SIDEWAYS = "sideways"
REGIME_UNKNOWN = "unknown"
REGIME_CN = {
    REGIME_BULL: "牛市（基准时钟一/二类）",
    REGIME_BEAR: "熊市（基准时钟四/五类）",
    REGIME_SIDEWAYS: "横盘（基准时钟三类）",
    REGIME_UNKNOWN: "基准不可得",
}


def regime_from_clock(clock_type: int) -> str:
    if clock_type in (TYPE1_ACCELERATING_UP, TYPE2_STEADY_UP):
        return REGIME_BULL
    if clock_type in (TYPE4_STEADY_DOWN, TYPE5_ACCELERATING_DOWN):
        return REGIME_BEAR
    if clock_type == TYPE3_SIDEWAYS:
        return REGIME_SIDEWAYS
    return REGIME_UNKNOWN


@dataclass(frozen=True, slots=True)
class Metrics:
    """一组交易的 §16 指标（net=True 为含费用，False 为不含费用）。"""

    label: str
    trade_count: int
    open_count: int
    win_rate: float | None
    avg_win_r: float | None
    avg_loss_r: float | None
    expectancy_r: float | None
    profit_factor: float | None
    max_consecutive_losses: int
    max_drawdown_1r: float
    avg_holding_bars: float | None
    total_r: float | None

    def as_row(self) -> str:
        def fmt(value: float | None, digits: int = 2) -> str:
            return "-" if value is None else f"{value:.{digits}f}"

        return (
            f"| {self.label} | {self.trade_count} | {self.open_count} | "
            f"{fmt(self.win_rate)} | {fmt(self.avg_win_r)} | {fmt(self.avg_loss_r)} | "
            f"{fmt(self.expectancy_r)} | {fmt(self.profit_factor)} | "
            f"{self.max_consecutive_losses} | {fmt(self.max_drawdown_1r)} | "
            f"{fmt(self.avg_holding_bars, 1)} | {fmt(self.total_r)} |"
        )


METRICS_HEADER = (
    "| 分组 | 笔数 | 未平 | 胜率 | 均盈R | 均亏R | 期望R | 盈利因子 | "
    "最大连亏 | 1R最大回撤 | 平均持仓(根) | 累计R |"
    "\n|---|---|---|---|---|---|---|---|---|---|---|---|"
)


def compute_metrics(trades: list[Trade], *, label: str = "all", net: bool = True) -> Metrics:
    closed = [
        t for t in trades
        if not t.is_open
        and t.exit_reason not in ("invalid_nonpositive_risk", "skipped_limit_up_at_entry")
    ]
    values = [
        (t.r_net if net else t.r_gross) or 0.0 for t in closed
    ]
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    max_consecutive = 0
    streak = 0
    for value in values:
        if value <= 0:
            streak += 1
            max_consecutive = max(max_consecutive, streak)
        else:
            streak = 0

    drawdown = 0.0
    peak = 0.0
    cumulative = 0.0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = max(drawdown, peak - cumulative)

    return Metrics(
        label=label,
        trade_count=len(closed),
        open_count=len(trades) - len(closed),
        win_rate=(len(wins) / len(values)) if values else None,
        avg_win_r=(sum(wins) / len(wins)) if wins else None,
        avg_loss_r=(sum(losses) / len(losses)) if losses else None,
        expectancy_r=(sum(values) / len(values)) if values else None,
        profit_factor=(gross_profit / gross_loss) if gross_loss > 0 else None,
        max_consecutive_losses=max_consecutive,
        max_drawdown_1r=drawdown,
        avg_holding_bars=(
            sum(t.holding_bars for t in closed) / len(closed) if closed else None
        ),
        total_r=sum(values) if values else None,
    )


def _by(trades: list[Trade], key_fn) -> dict[str, list[Trade]]:  # noqa: ANN001
    groups: dict[str, list[Trade]] = {}
    for trade in trades:
        groups.setdefault(str(key_fn(trade)), []).append(trade)
    return dict(sorted(groups.items()))


def full_group_metrics(
    trades: list[Trade],
    *,
    net: bool,
    sample_split: date | None = None,
) -> dict[str, list[Metrics]]:
    """§16 全部分组维度。sample_split 非空时按信号日切样本内/外。"""
    result: dict[str, list[Metrics]] = {}
    result["总览"] = [compute_metrics(trades, label="全部", net=net)]

    def year_of(t: Trade) -> str:
        return str(t.signal_date.year)

    result["分年份"] = [
        compute_metrics(group, label=year, net=net)
        for year, group in _by(trades, year_of).items()
    ]
    result["牛/熊/横盘（基准时钟）"] = [
        compute_metrics(group, label=f"{regime}｜{REGIME_CN[regime]}", net=net)
        for regime, group in _by(
            trades, lambda t: regime_from_clock(t.benchmark_clock_type)
        ).items()
    ]
    result["退出方式（A6 三版）"] = [
        compute_metrics(group, label=variant, net=net)
        for variant, group in _by(trades, lambda t: t.exit_variant).items()
    ]
    result["入场版本（A4）"] = [
        compute_metrics(group, label=variant, net=net)
        for variant, group in _by(trades, lambda t: t.entry_variant).items()
    ]
    result["首次 vs 非首次回撤"] = [
        compute_metrics(group, label="首次" if key == "True" else "非首次", net=net)
        for key, group in _by(trades, lambda t: str(t.is_first_touch)).items()
    ]
    result["回调均线组"] = [
        compute_metrics(group, label=f"SMA{period}", net=net)
        for period, group in _by(trades, lambda t: t.ma_period).items()
    ]
    result["标的时钟类型（入场时）"] = [
        compute_metrics(group, label=f"clock_{key}", net=net)
        for key, group in _by(trades, lambda t: t.clock_type).items()
    ]
    result["大周期（周线环境）"] = [
        compute_metrics(group, label="同向" if key == "True" else "非同向", net=net)
        for key, group in _by(trades, lambda t: str(t.weekly_bull_env)).items()
    ]
    result["趋势五步（入场时 stage）"] = [
        compute_metrics(
            group,
            label=f"stage_{key}" + ("（未起步）" if key == "0" else ""),
            net=net,
        )
        for key, group in _by(trades, lambda t: str(getattr(t, "trend_stage", 0))).items()
    ]
    result["按标的"] = [
        compute_metrics(group, label=symbol, net=net)
        for symbol, group in _by(trades, lambda t: t.symbol).items()
    ]
    if sample_split is not None:
        result["样本内外"] = [
            compute_metrics(group, label=label, net=net)
            for label, group in (
                ("样本内（<= 切分日）", [t for t in trades if t.signal_date < sample_split]),
                ("样本外（> 切分日）", [t for t in trades if t.signal_date >= sample_split]),
            )
        ]
    return result


__all__ = [
    "METRICS_HEADER",
    "Metrics",
    "REGIME_BEAR",
    "REGIME_BULL",
    "REGIME_CN",
    "REGIME_SIDEWAYS",
    "REGIME_UNKNOWN",
    "compute_metrics",
    "full_group_metrics",
    "regime_from_clock",
]
