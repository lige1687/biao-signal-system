"""宽度择时参数扫描：网格构建、批量执行（全窗口+前后半窗口）、稳健性筛选。

过拟合防护：一组参数必须「全窗口与两个半窗口的超额年化都 > 0，且回撤不劣于基准」
才进入稳健 Top；报告明示历史最优不等于未来最优。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from lei_signal.timing_backtest.data import (
    INSTRUMENTS,
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.service import compute_run

LADDER_N_BANDS = (3, 5, 9)
LADDER_EDGE_MODES = ("fixed", "preq")
LADDER_DIRECTIONS = ("contrarian", "momentum")
REVERSAL_EXTREMES = ((10.0, 90.0), (20.0, 80.0), (30.0, 70.0))
REVERSAL_CONFIRMS = (5.0,)
REVERSAL_BATCH_MODES = ("time", "band")
REVERSAL_BATCHES = (3, 5, 8)
GATES = ("off", "ma200")


def build_grid(symbols: list[str], indicators: list[str]) -> list[dict]:
    grid: list[dict] = []
    for symbol in symbols:
        if symbol not in INSTRUMENTS:
            raise ValueError(f"未知标的 {symbol}")
        for indicator in indicators:
            for n_bands in LADDER_N_BANDS:
                for edge_mode in LADDER_EDGE_MODES:
                    for direction in LADDER_DIRECTIONS:
                        for gate in GATES:
                            grid.append(
                                {
                                    "symbol": symbol,
                                    "strategy": "ladder",
                                    "indicator": indicator,
                                    "n_bands": n_bands,
                                    "edge_mode": edge_mode,
                                    "direction": direction,
                                    "gate_mode": gate,
                                    "gate_cap": 0.0,
                                }
                            )
            for low, high in REVERSAL_EXTREMES:
                for confirm in REVERSAL_CONFIRMS:
                    for batch_mode in REVERSAL_BATCH_MODES:
                        for batches in REVERSAL_BATCHES:
                            for gate in GATES:
                                grid.append(
                                    {
                                        "symbol": symbol,
                                        "strategy": "reversal",
                                        "indicator": indicator,
                                        "low_extreme": low,
                                        "high_extreme": high,
                                        "confirm": confirm,
                                        "batch_mode": batch_mode,
                                        "batches": batches,
                                        "gate_mode": gate,
                                        "gate_cap": 0.0,
                                    }
                                )
    return grid


def _window_bounds(symbol: str, cache_dir: Path) -> tuple[str, str]:
    spec = INSTRUMENTS[symbol]
    aligned = align_index_breadth(
        load_index_bars(symbol, cache_dir=cache_dir),
        load_breadth(spec.breadth, cache_dir=cache_dir),
    )
    return aligned.index[0].strftime("%Y-%m-%d"), aligned.index[-1].strftime("%Y-%m-%d")


def _metrics_prefix(run: dict) -> dict:
    m = run["metrics"]
    return {
        "cagr": m["strategy_cagr"],
        "bh_cagr": m["benchmark_cagr"],
        "excess": m["excess_cagr"],
        "mdd": m["strategy_mdd"],
        "bh_mdd": m["benchmark_mdd"],
        "calmar": m["calmar"],
        "sharpe": m["sharpe"],
        "n_trades": m["n_trades"],
        "avg_weight": m["avg_weight"],
    }


def run_sweep(grid: list[dict], cache_dir: Path | None = None) -> pd.DataFrame:
    """逐组执行：全窗口 + 前半 + 后半，各取核心指标（前缀 full/h1/h2）。"""
    cache = cache_dir or TIMING_CACHE_DIR
    bounds: dict[str, tuple[str, str]] = {}
    rows: list[dict] = []
    for cfg in grid:
        symbol = cfg["symbol"]
        if symbol not in bounds:
            bounds[symbol] = _window_bounds(symbol, cache)
        start, end = bounds[symbol]
        mid = (pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2).strftime(
            "%Y-%m-%d"
        )
        try:
            full = _metrics_prefix(compute_run({**cfg}, cache_dir=cache))
            h1 = _metrics_prefix(
                compute_run({**cfg, "end": mid}, cache_dir=cache)
            )
            h2 = _metrics_prefix(
                compute_run({**cfg, "start": mid}, cache_dir=cache)
            )
        except Exception:
            continue  # 数据缺失/窗口过短等：跳过该组，不中断扫描
        row = {
            "symbol": symbol,
            "strategy": cfg["strategy"],
            "indicator": cfg["indicator"],
            "gate": cfg.get("gate_mode", "off"),
            "params": str({k: v for k, v in cfg.items() if k not in ("symbol", "gate_mode")}),
        }
        for prefix, m in (("full", full), ("h1", h1), ("h2", h2)):
            for k, v in m.items():
                row[f"{prefix}_{k}"] = v
        row["score"] = row["full_excess"] * 0.6 + min(row["full_calmar"], 5.0) * 0.4
        rows.append(row)
    return pd.DataFrame(rows)


def robust_mask(df: pd.DataFrame) -> pd.Series:
    """稳健条件：全窗/两半窗超额>0，且全窗回撤优于基准。"""
    return (
        (df["full_excess"] > 0)
        & (df["h1_excess"] > 0)
        & (df["h2_excess"] > 0)
        & (df["full_mdd"] >= df["full_bh_mdd"])
    )


def robust_top(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """每标的取稳健组中 score 最高 top_n。"""
    if df.empty:
        return df
    mask = robust_mask(df)
    out = df[mask].sort_values("score", ascending=False)
    return out.groupby("symbol", group_keys=False).head(top_n)
