#!/usr/bin/env python3
"""宽度择时参数扫描入口：批量网格 → CSV + Markdown 报告（每标的稳健 Top15）。

用法：
  python3 scripts/sweep_timing_backtest.py                       # 4 标的 × B200/B50
  python3 scripts/sweep_timing_backtest.py --symbols 000300      # 单标的
  python3 scripts/sweep_timing_backtest.py --indicators b200     # 单指标
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import pandas as pd  # noqa: E402

from lei_signal.timing_backtest.data import INSTRUMENTS  # noqa: E402
from lei_signal.timing_backtest.sweep import build_grid, robust_top, run_sweep  # noqa: E402

PCT = lambda v: f"{v * 100:+.2f}%" if pd.notna(v) else "—"  # noqa: E731


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="000300,399006,^GSPC,^IXIC")
    ap.add_argument("--indicators", default="b200,b50")
    ap.add_argument("--out", default="docs/timing-sweep")
    args = ap.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    indicators = [i.strip() for i in args.indicators.split(",") if i.strip()]
    grid = build_grid(symbols, indicators)
    print(f"网格：{len(grid)} 组（{symbols} × {indicators}）")

    df = run_sweep(grid)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    csv_path = out_dir / f"sweep_{today}.csv"
    df.to_csv(csv_path, index=False)

    top = robust_top(df)
    md = [
        f"# 宽度择时参数扫描报告 {today}",
        "",
        (
            f"- 网格 {len(grid)} 组，成功 {len(df)} 组；"
            f"稳健组（全窗/两半窗超额>0且回撤不劣于基准）{len(top)} 组"
        ),
        f"- 完整数据：`{csv_path}`",
        (
            "- ⚠️ 历史最优不等于未来最优：Top 表按全窗口+前后半窗口一致占优筛选，"
            "仍存在过拟合风险，仅供研究"
        ),
        "",
    ]
    if top.empty:
        md.append("无参数组满足稳健条件。")
    for symbol, group in top.groupby("symbol"):
        name = INSTRUMENTS[symbol].name
        md.append(f"## {name}（{symbol}）Top{len(group)}")
        md.append("")
        md.append(
            "| 策略 | 指标 | 闸门 | 参数 | 全窗年化 | 基准年化 | 超额 | 回撤 | "
            "前半超额 | 后半超额 | Calmar | 调仓 |"
        )
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for _, r in group.iterrows():
            md.append(
                f"| {r['strategy']} | {r['indicator']} | {r['gate']} | {r['params']} "
                f"| {PCT(r['full_cagr'])} | {PCT(r['full_bh_cagr'])} | {PCT(r['full_excess'])} "
                f"| {PCT(r['full_mdd'])} | {PCT(r['h1_excess'])} | {PCT(r['h2_excess'])} "
                f"| {r['full_calmar']:.2f} | {int(r['full_n_trades'])} |"
            )
        md.append("")
    report_path = out_dir / f"report_{today}.md"
    report_path.write_text("\n".join(md), encoding="utf-8")
    print(f"完成：{csv_path} / {report_path}")


if __name__ == "__main__":
    main()
