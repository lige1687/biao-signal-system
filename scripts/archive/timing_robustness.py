#!/usr/bin/env python3
"""宽度择时胜出组稳健性套件：滚动窗 / 参数邻域 / 费用 / 起始日偏移 / 现金利率 / ETF 交叉。

用法：
  python3 scripts/timing_robustness.py --configs docs/timing-sweep/winners_v3.json
  python3 scripts/timing_robustness.py --demo   # 用内置默认胜出组
输出：docs/timing-sweep/robustness_<date>.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import pandas as pd  # noqa: E402

from lei_signal.timing_backtest.service import compute_run  # noqa: E402
from lei_signal.timing_backtest.sweep import _window_bounds  # noqa: E402

ETF_MAP = {"000300": "510300", "399006": "159915", "^GSPC": "SPY", "^IXIC": "QQQ"}


def _excess(cfg: dict) -> float:
    return compute_run(cfg)["metrics"]["excess_cagr"]


def _full(cfg: dict) -> dict:
    return compute_run(cfg)["metrics"]


def rolling_excess(cfg: dict, years: int = 5, step_days: int = 252) -> dict:
    start, end = _window_bounds(cfg["symbol"], Path.home() / ".lei_signal_lab/cache/timing")
    dates = pd.bdate_range(start, end)
    wins: list[float] = []
    spans = []
    win_len = pd.Timedelta(days=int(years * 365.25))
    for i in range(0, len(dates), step_days):
        s = dates[i]
        e = s + win_len
        if e > dates[-1]:
            break
        c = {**cfg, "start": s.strftime("%Y-%m-%d"), "end": e.strftime("%Y-%m-%d")}
        try:
            wins.append(_excess(c))
            spans.append(f"{s.year}-{e.year}")
        except Exception:
            continue
    se = pd.Series(wins)
    return {
        "windows": len(wins),
        "positive_pct": float((se > 0).mean()) if len(se) else float("nan"),
        "median": float(se.median()) if len(se) else float("nan"),
        "worst": float(se.min()) if len(se) else float("nan"),
        "best": float(se.max()) if len(se) else float("nan"),
        "spans": spans,
    }


def neighborhood(cfg: dict) -> dict:
    """单维扰动：每个维度 ±1 步，检验胜出是高原还是孤峰。"""
    variants: list[dict] = []
    num_step = {
        "gamma": 0.15, "vol_target": 0.05, "min_weight": 0.1, "batch_ratio": 0.1,
        "confirm": 5.0, "low_edge": 5.0, "high_edge": -5.0,
        "low_extreme": 5.0, "high_extreme": -5.0, "band_step": 5.0,
    }
    int_step = {"n_bands": 2, "batches": 2, "sell_batches": 1}
    for key, step in num_step.items():
        if cfg.get(key) is None:
            continue
        for d in (+step, -step):
            v = {**cfg, key: float(cfg[key]) + d}
            variants.append(v)
    for key, step in int_step.items():
        if cfg.get(key) is None:
            continue
        for d in (+step, -step):
            v = int(cfg[key]) + d
            if v > 0:
                variants.append({**cfg, key: v})
    results = []
    for v in variants:
        try:
            results.append(_excess(v))
        except Exception:
            continue
    se = pd.Series(results)
    return {
        "neighbors": len(results),
        "positive_pct": float((se > 0).mean()) if len(se) else float("nan"),
        "median": float(se.median()) if len(se) else float("nan"),
        "worst": float(se.min()) if len(se) else float("nan"),
    }


def fee_sensitivity(cfg: dict) -> dict:
    return {f"{bp}bp": _excess({**cfg, "fee_bps": float(bp)}) for bp in (0, 5, 10, 20, 30)}


def start_shift(cfg: dict) -> dict:
    base = pd.Timestamp(cfg.get("start") or _window_bounds(
        cfg["symbol"], Path.home() / ".lei_signal_lab/cache/timing")[0])
    out = {}
    for shift in (-120, -60, 0, 60, 120):
        s = (base + pd.Timedelta(days=int(shift * 1.45))).strftime("%Y-%m-%d")
        try:
            out[f"{shift:+d}d"] = _excess({**cfg, "start": s})
        except Exception:
            continue
    return out


def cash_sensitivity(cfg: dict) -> dict:
    return {f"{r*100:.0f}%": _excess({**cfg, "cash_rate": float(r)}) for r in (0.0, 0.02, 0.04)}


def etf_cross(cfg: dict) -> dict | None:
    etf = ETF_MAP.get(cfg["symbol"])
    if etf is None:
        return None
    try:
        m = _full({**cfg, "symbol": etf})
        return {"etf": etf, "excess": m["excess_cagr"], "cagr": m["strategy_cagr"],
                "mdd": m["strategy_mdd"]}
    except Exception as e:
        return {"etf": etf, "error": str(e)[:80]}


PCT = lambda v: ("—" if v != v else f"{v*100:+.2f}%")  # noqa: E731


def analyze(cfg: dict, label: str) -> list[str]:
    lines = [f"### {label}", "", f"```json\n{json.dumps(cfg, ensure_ascii=False)}\n```", ""]
    m = _full(cfg)
    lines.append(
        f"- 基准：年化 {PCT(m['benchmark_cagr'])} 回撤 {PCT(m['benchmark_mdd'])}；"
        f"策略年化 {PCT(m['strategy_cagr'])} 回撤 {PCT(m['strategy_mdd'])} "
        f"超额 {PCT(m['excess_cagr'])}"
    )
    roll = rolling_excess(cfg)
    lines.append(
        f"- 5年滚动窗（{roll['windows']} 个）：正超额占比 {roll['positive_pct']*100:.0f}%，"
        f"中位 {PCT(roll['median'])}，最差 {PCT(roll['worst'])}，最好 {PCT(roll['best'])}"
    )
    nb = neighborhood(cfg)
    lines.append(
        f"- 参数邻域（{nb['neighbors']} 个单维扰动）：正超额占比 {nb['positive_pct']*100:.0f}%，"
        f"中位 {PCT(nb['median'])}，最差 {PCT(nb['worst'])}"
    )
    fees = fee_sensitivity(cfg)
    lines.append("- 费用敏感性：" + "，".join(f"{k} {PCT(v)}" for k, v in fees.items()))
    shifts = start_shift(cfg)
    se = pd.Series([v for v in shifts.values()])
    lines.append(
        f"- 起始日偏移（{len(shifts)} 档）：超额区间 [{PCT(se.min())}, {PCT(se.max())}]"
    )
    cash = cash_sensitivity(cfg)
    lines.append("- 现金利率：" + "，".join(f"{k} {PCT(v)}" for k, v in cash.items()))
    etf = etf_cross(cfg)
    if etf and "error" not in etf:
        lines.append(
            f"- ETF 交叉（{etf['etf']}，可交易口径）：年化 {PCT(etf['cagr'])}，"
            f"超额 {PCT(etf['excess'])}，回撤 {PCT(etf['mdd'])}"
        )
    elif etf:
        lines.append(f"- ETF 交叉失败：{etf['error']}")
    lines.append("")
    return lines


DEMO_CONFIGS = [
    ("创业板·三轮候选（占位，正式由 v3 结果替换）",
     {"symbol": "399006", "strategy": "ladder", "indicator": "b200", "n_bands": 3,
      "direction": "contrarian", "low_edge": 25.0, "high_edge": 75.0, "gamma": 0.7}),
    ("纳指·防守（二轮王）",
     {"symbol": "^IXIC", "strategy": "ladder", "indicator": "b200", "n_bands": 5,
      "direction": "momentum", "low_edge": 25.0, "high_edge": 75.0, "gamma": 0.7,
      "vol_target": 0.15, "gate_mode": "ma200"}),
    ("沪深300·攻守兼备（一轮王）",
     {"symbol": "000300", "strategy": "reversal", "indicator": "b200",
      "low_extreme": 10.0, "high_extreme": 90.0, "confirm": 5.0,
      "batch_mode": "time", "batches": 8, "gate_mode": "ma200"}),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=None, help="JSON: [[label, cfg], ...]")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    if args.configs:
        raw = json.loads(Path(args.configs).read_text(encoding="utf-8"))
        configs = [(str(k), v) for k, v in raw]
    else:
        configs = DEMO_CONFIGS

    md = [
        f"# 宽度择时胜出组稳健性套件 {date.today():%Y%m%d}",
        "",
        "检验项：5年滚动超额 / 参数邻域（孤峰检验）/ 费用 0-30bp / 起始日偏移 ±120 日 /"
        " 现金利率 0-4% / ETF 可交易口径交叉。",
        "",
    ]
    for label, cfg in configs:
        print(f"分析 {label} …", flush=True)
        md.extend(analyze(cfg, label))
    out = Path("docs/timing-sweep") / f"robustness_{date.today():%Y%m%d}.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"完成：{out}")


if __name__ == "__main__":
    main()
