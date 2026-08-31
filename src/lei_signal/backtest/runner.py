"""第一轮最小系统回测运行器（规格 §15 第一轮 + §16 输出）。

跑法：对回测深池每个标的，用与 live pipeline 同一份检测器生成模块 A
入场事件（A4 早期版/确认版），按 A6 三版退出 × 费用三档（0/5/10bp）×
盈亏比过滤（>=3 与不过滤对照）组合模拟，输出 §16 全量指标与分组。

数据：默认读回测深池 ``~/.lei_signal_lab/backtest_pool``（10 年回填、与
live 缓存隔离，见 docs/data-sufficiency-audit-2026-08-24.md）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from lei_signal.backtest.engine import (
    ENTRY_CONFIRMED,
    ENTRY_EARLY,
    EXIT_VARIANT_CN,
    EXIT_VARIANTS,
    FeeModel,
    Trade,
    entry_specs_from_events,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.metrics import (
    METRICS_HEADER,
    Metrics,
    full_group_metrics,
)
from lei_signal.data.cache import ParquetCache
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.clock_classifier import clock_series
from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events
from lei_signal.rules.lei_color import classify_colors

#: 回测深池根目录。LEI_BACKTEST_POOL_ROOT 可隔离出独立池（如美股校准池），
#: 避免把美股标的混进默认 A 股全池回测。
DEFAULT_POOL_ROOT = Path(
    os.environ.get("LEI_BACKTEST_POOL_ROOT", str(Path.home() / ".lei_signal_lab" / "backtest_pool"))
)

#: 市场基准（牛/熊/横盘分组用）：A股→沪深300，美股→标普500，港股→恒生。
BENCHMARK_BY_MARKET = {"cn": "000300.SS", "us": "^GSPC", "hk": "^HSI"}

RESEARCH_DISCLAIMER = (
    "研究回测（规格 §16）：固定 1R 风险口径的 R 化统计，不是账户资金曲线；"
    "未建模涨跌停、停牌、流动性冲击与融券约束；费用为账本 fees_and_slippage"
    "〔标定 V2.1〕档位。"
)


def market_of(symbol: str) -> str:
    if symbol.startswith("TH") or symbol.endswith((".SS", ".SZ")):
        return "cn"
    if symbol.startswith("^HS") or symbol.endswith(".HK"):
        return "hk"
    return "us"


@dataclass(frozen=True, slots=True)
class Round1Config:
    entry_variants: tuple[str, ...] = (ENTRY_EARLY, ENTRY_CONFIRMED)
    exit_variants: tuple[str, ...] = EXIT_VARIANTS
    fee_labels: tuple[str, ...] = ("none", "standard", "conservative")
    rr_min: float | None = 3.0            # §10 盈亏比过滤（None=不过滤对照）
    out_of_sample_start: date | None = None  # 样本外起点（决策点 3：留最近 2 年）
    benchmark: bool = True


@dataclass(slots=True)
class SymbolResult:
    symbol: str
    bars: int
    events_touched: int = 0
    events_confirmed: int = 0
    filtered_by_rr: int = 0
    filtered_no_target: int = 0


@dataclass(slots=True)
class Round1Report:
    config: Round1Config
    start_date: str = ""
    end_date: str = ""
    symbols: list[SymbolResult] = field(default_factory=list)
    # (entry_variant, exit_variant, fee_label) -> trades
    runs: dict[tuple[str, str, str], list[Trade]] = field(default_factory=dict)
    # (entry_variant, exit_variant, fee_label, net) -> 分组指标
    metrics: dict[tuple[str, str, str, bool], dict[str, list[Metrics]]] = field(
        default_factory=dict
    )
    disclaimer: str = RESEARCH_DISCLAIMER


def load_pool_frames(root: Path | str = DEFAULT_POOL_ROOT) -> dict[str, pd.DataFrame]:
    """读深池全部可信标的并计算特征（classify_colors 提供 signal_color）。"""
    cache = ParquetCache(root)
    frames: dict[str, pd.DataFrame] = {}
    for path in sorted(Path(root).glob("*.bars.parquet")):
        symbol = path.name[: -len(".bars.parquet")]
        bars = cache.read(symbol)
        if bars is None or len(bars) < 300:
            continue
        frames[symbol] = classify_colors(compute_features(bars))
    return frames


def _benchmark_clock(frames: dict[str, pd.DataFrame]) -> dict[str, dict[date, int]]:
    """每市场的基准时钟：{交易日: 时钟类型}（date 键查找稳定，无 DatetimeIndex 陷阱）。"""
    result: dict[str, dict[date, int]] = {}
    for market, symbol in BENCHMARK_BY_MARKET.items():
        frame = frames.get(symbol)
        if frame is not None:
            series = clock_series(frame)
            result[market] = {
                timestamp.date(): int(value)
                for timestamp, value in series.items()
            }
    return result


def run_round1(
    frames: dict[str, pd.DataFrame], config: Round1Config
) -> Round1Report:
    report = Round1Report(config=config)
    all_dates = [frame.index[0] for frame in frames.values()] + [
        frame.index[-1] for frame in frames.values()
    ]
    if all_dates:
        report.start_date = min(all_dates).date().isoformat()
        report.end_date = max(all_dates).date().isoformat()

    benchmarks = _benchmark_clock(frames) if config.benchmark else {}

    for symbol, frame in sorted(frames.items()):
        prepared = prepare_frame(frame)
        events = detect_first_ma_pullback_events(frame, symbol)
        touched = sum(
            1 for e in events if e.evidence.get("sub_rule") == "first_ma_pullback_touched"
        )
        confirmed = sum(
            1 for e in events if e.evidence.get("sub_rule") == "first_ma_pullback_confirmed"
        )
        symbol_result = SymbolResult(
            symbol=symbol, bars=len(frame),
            events_touched=touched, events_confirmed=confirmed,
        )
        pivots = confirmed_pivots(frame)
        market = market_of(symbol)
        bench = benchmarks.get(market)

        for entry_variant in config.entry_variants:
            specs, filtered_rr, filtered_no_target = entry_specs_from_events(
                frame, events, symbol,
                entry_variant=entry_variant, rr_min=config.rr_min, pivots=pivots,
            )
            symbol_result.filtered_by_rr += filtered_rr
            symbol_result.filtered_no_target += filtered_no_target
            for exit_variant in config.exit_variants:
                for fee_label in config.fee_labels:
                    fee = FeeModel.from_ledger(fee_label)
                    trades: list[Trade] = []
                    for spec in specs:
                        trade = simulate_trade(
                            frame, spec,
                            exit_variant=exit_variant, fee=fee, prepared=prepared,
                        )
                        if bench is not None:
                            trade.benchmark_clock_type = bench.get(spec.signal_date, 0)
                        trades.append(trade)
                    # 跨标的累加（每个组合 key 覆盖会丢掉前面标的的全部交易）
                    report.runs.setdefault(
                        (entry_variant, exit_variant, fee_label), []
                    ).extend(trades)
        report.symbols.append(symbol_result)

    for key, trades in report.runs.items():
        for net in (True, False):
            report.metrics[(*key, net)] = full_group_metrics(
                trades, net=net, sample_split=config.out_of_sample_start
            )
    return report


def format_markdown(report: Round1Report) -> str:
    config = report.config
    lines = [
        "# V2 第一轮最小系统回测报告（模块 A，规格 §15/§16）",
        "",
        f"- 数据区间：{report.start_date} ~ {report.end_date}；"
        f"标的 {len(report.symbols)} 个（回测深池）",
        f"- A4 入场版本：{'/'.join(config.entry_variants)}；"
        f"A6 退出：{'/'.join(config.exit_variants)}",
        f"- 盈亏比过滤：{'R/R >= ' + str(config.rr_min) if config.rr_min else '不过滤（对照）'}",
        f"- 样本外起点：{config.out_of_sample_start or '未设置'}",
        f"- 费用档：{'/'.join(config.fee_labels)}（none=0bp，standard=5bp，"
        "conservative=10bp，账本 fees_and_slippage）",
        f"- 免责：{report.disclaimer}",
        "",
    ]
    total_touched = sum(s.events_touched for s in report.symbols)
    total_confirmed = sum(s.events_confirmed for s in report.symbols)
    total_rr = sum(s.filtered_by_rr for s in report.symbols)
    total_no_target = sum(s.filtered_no_target for s in report.symbols)
    lines += [
        "## 事件漏斗（全池合计）",
        "",
        f"- 回撤触碰事件 {total_touched} 个；入场事件 {total_confirmed} 个"
        "（含早期版+确认版两口径）；",
        f"- 盈亏比过滤剔除 {total_rr} 个；目标不可计算 {total_no_target} 个（§13 条 4）。",
        "",
    ]

    for net in (False, True):
        fee_title = "不含费用" if not net else "含费用"
        lines += [f"## {fee_title}", ""]
        for (entry_variant, exit_variant, fee_label), _trades in sorted(
            report.runs.items()
        ):
            key = (entry_variant, exit_variant, fee_label, net)
            groups = report.metrics.get(key)
            if not groups:
                continue
            lines += [
                f"### A4={entry_variant} × {EXIT_VARIANT_CN.get(exit_variant, exit_variant)}"
                f" × 费用={fee_label}",
                "",
            ]
            for section, metric_list in groups.items():
                lines += [f"**{section}**", "", METRICS_HEADER]
                lines += [m.as_row() for m in metric_list]
                lines.append("")
    return "\n".join(lines)


__all__ = [
    "BENCHMARK_BY_MARKET",
    "DEFAULT_POOL_ROOT",
    "Round1Config",
    "Round1Report",
    "SymbolResult",
    "format_markdown",
    "load_pool_frames",
    "market_of",
    "run_round1",
]
