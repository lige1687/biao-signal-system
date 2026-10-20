"""B 突破版细网格批跑：补全 40/63/90/126/180 × 2%/3%/4%/5% 缺失点。

调用方式（全局串行，避免账本并发污染）：
  cd /Users/yongbiaoli/Desktop/lei-signal-lab && PYTHONPATH=src python3 \\
      scripts/run_backtest_grid.py B
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw"


def _summary_one(result: dict) -> dict:
    """从完整 result 抽出实验报告用的核心指标。"""
    g = result["groups"]["True"]
    overview = g["总览"][0]
    inout = {s["label"]: s for s in g.get("样本内外", [])}
    by_year = {
        s["label"]: {
            "expectancy_r": s["expectancy_r"],
            "profit_factor": s["profit_factor"],
            "trade_count": s["trade_count"],
            "total_r": s["total_r"],
        }
        for s in g.get("分年份", [])
    }
    by_symbol = sorted(
        g.get("按标的", []),
        key=lambda s: -(s["total_r"] or 0),
    )
    top3_r = sum((s["total_r"] or 0) for s in by_symbol[:3])
    total_r = overview["total_r"] or 0.0
    by_regime = {
        s["label"].split("｜")[0]: {
            "expectancy_r": s["expectancy_r"],
            "profit_factor": s["profit_factor"],
            "trade_count": s["trade_count"],
        }
        for s in g.get("牛/熊/横盘（基准时钟）", [])
    }
    return {
        "params": result["params"],
        "data_range": result["data_range"],
        "funnel": result["funnel"],
        "overview": {
            "trade_count": overview["trade_count"],
            "expectancy_r": overview["expectancy_r"],
            "profit_factor": overview["profit_factor"],
            "win_rate": overview["win_rate"],
            "avg_win_r": overview["avg_win_r"],
            "avg_loss_r": overview["avg_loss_r"],
            "max_consecutive_losses": overview["max_consecutive_losses"],
            "max_drawdown_1r": overview["max_drawdown_1r"],
            "avg_holding_bars": overview["avg_holding_bars"],
            "total_r": overview["total_r"],
        },
        "in_sample": inout.get("样本内（<= 切分日）", {}).get("expectancy_r"),
        "out_of_sample": inout.get("样本外（> 切分日）", {}).get("expectancy_r"),
        "oos_trade_count": inout.get("样本外（> 切分日）", {}).get("trade_count"),
        "is_trade_count": inout.get("样本内（<= 切分日）", {}).get("trade_count"),
        "is_expectancy": inout.get("样本内（<= 切分日）", {}).get("expectancy_r"),
        "oos_expectancy": inout.get("样本外（> 切分日）", {}).get("expectancy_r"),
        "by_year": by_year,
        "by_regime": by_regime,
        "by_symbol": [
            {
                "symbol": s["label"],
                "trade_count": s["trade_count"],
                "expectancy_r": s["expectancy_r"],
                "total_r": s["total_r"],
            }
            for s in by_symbol
        ],
        "top3_symbol_share": (top3_r / total_r) if total_r else None,
        "top1_symbol": by_symbol[0]["label"] if by_symbol else None,
        "top1_total_r": by_symbol[0]["total_r"] if by_symbol else None,
    }


def run_b_grid(consolidations: list[int], clusters: list[float]) -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    out_dir = RAW / "B_breakout_matrix"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for cb in consolidations:
        for cl in clusters:
            tag = f"cb{cb}_cl{int(cl * 100):02d}"
            fp = out_dir / f"{tag}.json"
            if fp.exists():
                print(f"[skip] {tag} 已有落盘")
                rj = json.loads(fp.read_text(encoding="utf-8"))
                rows.append(rj)
                continue
            t0 = time.time()
            res = execute_run(
                BacktestParams(
                    module="B",
                    symbols=None,
                    rr_min=None,
                    entry_variant="breakout",
                    exit_variant="a6_1_costbasis",
                    fee_label="standard",
                    limit_guard=True,
                    overrides=(("consolidation_bars", cb), ("cluster_threshold", cl)),
                )
            )
            s = _summary_one(res)
            fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
            rows.append(s)
            ov = s["overview"]
            is_exp = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
            oos_exp = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
            top1 = s["top1_symbol"] or "-"
            top1r = s["top1_total_r"] or 0.0
            print(
                f"[done] {tag}  trades={ov['trade_count'] or 0:>3}  "
                f"expR={(ov['expectancy_r'] if ov['expectancy_r'] is not None else float('nan')):+.3f}  "
                f"PF={ov['profit_factor']}  "
                f"IS={is_exp:+.3f}({s['is_trade_count'] or 0})  "
                f"OOS={oos_exp:+.3f}({s['oos_trade_count'] or 0})  "
                f"top1={top1}({top1r:+.1f})  "
                f"{time.time()-t0:.1f}s"
            )
    # 写汇总表（CSV-like JSON 方便后处理）
    grid = {
        "consolidations": consolidations,
        "clusters": clusters,
        "cells": rows,
    }
    (out_dir / "_grid.json").write_text(
        json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: run_backtest_grid.py B|a_round2|cross_check|by_symbol")
        return
    mode = sys.argv[1]
    if mode == "B":
        run_b_grid([40, 63, 90, 126, 180], [0.02, 0.03, 0.04, 0.05])
    else:
        raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
