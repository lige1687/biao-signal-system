#!/usr/bin/env python3
"""生成 2026-08-31 探索回合交互式报告页（单文件 HTML + 内嵌 ECharts）。

数据源（全部为本日已落盘 raw）：
- ultimate/ultimate_curves.csv   权益曲线 7 臂
- ultimate/ultimate_results.json 指标
模板：scripts/round_report_template.html（占位符 __ECHARTS__ / __DATA__）
输出：docs/reports/round-2026-08-31.html
复现：PYTHONHASHSEED=0 python3 scripts/render_round_20260831.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
OUT = REPO / "docs/reports/round-2026-08-31.html"
ECHARTS = REPO / "web/node_modules/echarts/dist/echarts.min.js"
TPL = Path(__file__).resolve().parent / "round_report_template.html"


def main() -> None:
    df = pd.read_csv(SRC / "ultimate/ultimate_curves.csv",
                     index_col=0, parse_dates=True)
    weekly = df.resample("W").last().dropna(how="all")
    dates = [d.strftime("%Y-%m-%d") for d in weekly.index]
    series = {k: [round(float(v), 4) for v in weekly[k].fillna(1.0)]
              for k in df.columns}

    res = json.loads((SRC / "ultimate/ultimate_results.json").read_text())
    opt = json.loads((SRC / "ultimate/optimize_results.json").read_text())
    opt_curves = pd.read_csv(SRC / "ultimate/optimize_curves.csv",
                             index_col=0, parse_dates=True)

    # 优化臂曲线对齐到主周频日期（ffill）
    opt_map = {"opt_rebal": "rebal_g15_s30", "opt_rebal10": "rebal_g10_s30"}
    arms = dict(res["arms"])
    for new_key, csv_key in opt_map.items():
        s = (opt_curves[csv_key] / opt_curves[csv_key].iloc[0])
        s_week = s.resample("W").last().reindex(weekly.index).ffill()
        series[new_key] = [round(float(v), 4) for v in s_week]
        arms[new_key] = opt["arms"][csv_key]

    # 分年收益
    yearly: dict[str, dict[str, float]] = {}
    for c in df.columns:
        y = df[c].resample("YE").last()
        prev = pd.concat([pd.Series([1.0], index=[df.index[0]]), y])
        yearly[c] = {str(k.year): round((v / prev.iloc[i] - 1) * 100, 1)
                     for i, (k, v) in enumerate(y.items())}
    for new_key, csv_key in opt_map.items():
        s = opt_curves[csv_key]
        y = s.resample("YE").last()
        prev = pd.concat([pd.Series([1.0], index=[s.index[0]]), y])
        yearly[new_key] = {str(k.year): round((v / prev.iloc[i] - 1) * 100, 1)
                           for i, (k, v) in enumerate(y.items())}
    years = sorted(yearly["ultimate"].keys())

    # 回撤序列
    dd: dict[str, list[float]] = {}
    for c in ["ultimate", "opt_rebal", "b9", "hold"]:
        s = weekly[c] if c in weekly.columns else pd.Series(
            series[c], index=weekly.index)
        s = s.fillna(1.0)
        dd[c] = [round((float(v) / float(m) - 1) * 100, 2)
                 for v, m in zip(s, s.cummax(), strict=True)]

    # 散点：各臂（key 与模板端 CN/COLOR 映射对齐）
    cn = {"hold": "持有基准(9池等权)", "b9": "B9 宽度主仓", "b9_cash": "B9+现金腿",
          "main_ult": "主仓终极(+黄金10%)", "lei": "LEI 卫星腿(单腿)",
          "combo20": "合体 80/20", "ultimate": "★ 终极组合",
          "opt_rebal": "✦ 优化后(再平衡 金15% 卫30%)",
          "opt_rebal10": "优化后(再平衡 金10% 卫30%)"}
    points = [{"name": cn[k], "x": v["maxdd_pct"], "y": v["ann_pct"],
               "calmar": v["calmar"], "key": k}
              for k, v in arms.items()]

    data = {"dates": dates, "series": series, "dd": dd, "yearly": yearly,
            "years": years, "arms": arms, "points": points,
            "opt_scan": opt}

    html = (TPL.read_text(encoding="utf-8")
            .replace("__ECHARTS__", ECHARTS.read_text(encoding="utf-8"))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("已生成:", OUT, f"({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
