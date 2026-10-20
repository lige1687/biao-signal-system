"""盈亏比门槛敏感性（规格 §10/§16 参数敏感性；手册 5.2 原则值 3）。

对回测深池一次性检测模块 A 事件，然后按不同 R/R 门槛过滤入场信号，
分别模拟 A6①/② 两版退出（含 5bp 费用），输出 §16 指标对照与样本内外分组。

档位设定：
- 2.0 / 2.5：敏感性下探（超出手册「<3 不参与」原则，仅作对照，不改默认）；
- 3.0：账本与规格默认（已定（原则））；
- 5.0：作者案例倾向的严格档（手册 5.2「>= 5 才值得做」）；
- none：不设门槛，但仍要求「目标可计算」（§13 条 4 是无交易条件，与门槛无关）。
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.backtest.engine import (  # noqa: E402
    ENTRY_EARLY,
    EXIT_COSTBASIS,
    EXIT_TOP_PLUS_KEYWAVE,
    FeeModel,
    entry_specs_from_events,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.metrics import compute_metrics  # noqa: E402
from lei_signal.backtest.runner import (  # noqa: E402
    DEFAULT_POOL_ROOT,
    _benchmark_clock,
    load_pool_frames,
)
from lei_signal.features.pivots import confirmed_pivots  # noqa: E402
from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events  # noqa: E402

RR_LEVELS: tuple[float | None, ...] = (None, 2.0, 2.5, 3.0, 4.0, 5.0)


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_POOL_ROOT)
    frames = load_pool_frames(root)
    if not frames:
        raise SystemExit(f"回测池为空：{root}")
    last_date = max(frame.index[-1] for frame in frames.values()).date()
    oos_start = last_date - timedelta(days=365 * 2)
    benchmarks = _benchmark_clock(frames)
    fee = FeeModel.from_ledger("standard")

    # 一次性检测；specs 全量（rr_min=None 但目标必须可计算 -> entry_specs 用
    # rr_min=None 放行无目标信号，这里再按「目标可计算」统一过滤，保证各档可比）
    all_specs: list[tuple[str, pd.DataFrame, dict, object]] = []
    for symbol, frame in sorted(frames.items()):
        events = detect_first_ma_pullback_events(frame, symbol)
        prepared = prepare_frame(frame)
        pivots = confirmed_pivots(frame)
        specs, _frr, _fnt = entry_specs_from_events(
            frame, events, symbol,
            entry_variant=ENTRY_EARLY, rr_min=None, pivots=pivots,
        )
        for spec in specs:
            if spec.reward_risk is not None:
                all_specs.append((symbol, frame, prepared, spec))

    def run(level: float | None, exit_variant: str) -> list:
        threshold = float(level) if level is not None else 0.0
        trades = []
        for symbol, frame, prepared, spec in all_specs:
            if spec.reward_risk < threshold:
                continue
            trade = simulate_trade(
                frame, spec, exit_variant=exit_variant, fee=fee, prepared=prepared,
            )
            bench = benchmarks.get("cn" if symbol.endswith((".SS", ".SZ")) or symbol.startswith("TH") else ("hk" if symbol.startswith("^HS") else "us"))
            if bench is not None:
                trade.benchmark_clock_type = bench.get(spec.signal_date, 0)
            trades.append(trade)
        return trades

    header = (
        "| R/R 门槛 | 笔数 | 未平 | 胜率 | 均盈R | 均亏R | 期望R | 盈利因子 | "
        "最大连亏 | 1R回撤 | 平均持仓 | 累计R | 样本内期望R | 样本外期望R |"
    )
    lines = [
        "# 盈亏比门槛敏感性（模块 A，A4 早期版，含 5bp 费用）",
        "",
        f"- 数据：{len(frames)} 标的（回测深池）；样本外起点 {oos_start}（最近 2 年）；"
        "生成 " + date.today().isoformat(),
        "- 档位：none=不设门槛（仍要求目标可计算，§13 条 4）；3.0=规格已定（原则）默认；"
        "2.0/2.5=敏感性下探（超出手册原则，仅对照）；5.0=作者案例严格档",
        "- 纪律：账本 rr_min_ideal=3 不变；本表为 §16 参数敏感性输出，"
        "选档以样本外稳健性为准，不按总收益挑最好看。",
        "",
        "## A6① 抵扣价退出",
        "",
        header,
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for exit_variant, title in ((EXIT_COSTBASIS, "A6① 抵扣价退出"), (EXIT_TOP_PLUS_KEYWAVE, "A6② 顶部构造+关键性波动")):
        if exit_variant != EXIT_COSTBASIS:
            lines += ["", f"## {title}", "", header, "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for level in RR_LEVELS:
            trades = run(level, exit_variant)
            m = compute_metrics(trades, label=str(level), net=True)  # noqa: FBT003
            inside = [t for t in trades if not t.is_open and t.signal_date < oos_start]
            outside = [t for t in trades if not t.is_open and t.signal_date >= oos_start]
            mi = compute_metrics(inside, label="in", net=True)  # noqa: FBT003
            mo = compute_metrics(outside, label="out", net=True)  # noqa: FBT003

            def fmt(v: float | None, digits: int = 2) -> str:
                return "-" if v is None else f"{v:.{digits}f}"

            lines.append(
                f"| {level if level is not None else 'none'} | {m.trade_count} | {m.open_count} | "
                f"{fmt(m.win_rate)} | {fmt(m.avg_win_r)} | {fmt(m.avg_loss_r)} | "
                f"{fmt(m.expectancy_r)} | {fmt(m.profit_factor)} | {m.max_consecutive_losses} | "
                f"{fmt(m.max_drawdown_1r)} | {fmt(m.avg_holding_bars, 1)} | {fmt(m.total_r)} | "
                f"{fmt(mi.expectancy_r)} (n={mi.trade_count}) | {fmt(mo.expectancy_r)} (n={mo.trade_count}) |"
            )

    out = (
        Path(__file__).resolve().parents[1] / "docs"
        / f"backtest-rr-sensitivity-{date.today().isoformat()}.md"
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n已写入 {out}")


if __name__ == "__main__":
    main()
