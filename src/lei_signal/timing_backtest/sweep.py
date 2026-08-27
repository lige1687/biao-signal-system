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

# 第二轮（资金管理维度）：档位范围收缩 / 陡度 / 批次比例 / 卖出独立分批 / 波动率目标
LADDER_EDGES = ((0.0, 100.0), (15.0, 85.0), (25.0, 75.0))
LADDER_GAMMAS = (0.7, 1.0, 1.5)
VOL_TARGETS = (0.0, 0.15)
REVERSAL_EXTREMES_V2 = ((10.0, 90.0), (15.0, 85.0), (20.0, 80.0), (30.0, 70.0))
REVERSAL_BATCH_RATIOS = (0.6, 1.0, 1.6)
REVERSAL_BATCHES_V2 = (3, 8)
SELL_OVERRIDES = (None, 1)

# 第三轮（终审深化）：胜出邻域细化
V3_EDGES = ((20.0, 80.0), (25.0, 75.0), (30.0, 70.0))
V3_GAMMAS_CN = (0.5, 0.7, 1.0)
V3_GAMMAS_US = (0.7, 1.0, 1.5)
V3_VOLS_CN = (0.0, 0.15, 0.20)
V3_VOLS_US = (0.10, 0.15, 0.20)
V3_MIN_W_CN = (0.0, 0.2)
V3_MIN_W_US = (0.0, 0.3)
V3_REV_EXTREMES = ((15.0, 85.0), (20.0, 80.0))
V3_REV_BATCHES = (5, 8)
V3_REV_RATIOS = (0.5, 0.6, 0.8)
V3_REV_SELL = (1, 2)
V3_REV_CONFIRMS = (5.0, 10.0)

# 第四轮（阶段性顶底波段）：中等宽度水平的反转 + B20 快指标
V4_MID_EXTREMES = ((30.0, 70.0), (35.0, 65.0), (40.0, 60.0), (45.0, 55.0))
V4_CONFIRMS = (3.0, 5.0, 8.0)


def build_grid_v4(symbols: list[str], indicators: list[str]) -> list[dict]:
    """阶段性顶底网格：中等极值反转（不等极端值，吃中线波段）× 全指标。"""
    grid: list[dict] = []
    for symbol in symbols:
        if symbol not in INSTRUMENTS:
            raise ValueError(f"未知标的 {symbol}")
        market = INSTRUMENTS[symbol].market
        for indicator in ("b20", "b50", "b200"):
            for low, high in V4_MID_EXTREMES:
                for confirm in V4_CONFIRMS:
                    for batch_mode in ("time", "band"):
                        for batches in (3, 5):
                            for gate in ("off", "ma200"):
                                grid.append({
                                    "symbol": symbol, "strategy": "reversal",
                                    "indicator": indicator, "low_extreme": low,
                                    "high_extreme": high, "confirm": confirm,
                                    "batch_mode": batch_mode, "batches": batches,
                                    "gate_mode": gate, "gate_cap": 0.0,
                                })
        # 快指标阶梯小臂（仅 A 股逆势 / 美股顺势，与终版同构）
        for indicator in ("b20", "b50"):
            for lo, hi in ((30.0, 70.0), (40.0, 60.0)):
                grid.append({
                    "symbol": symbol, "strategy": "ladder", "indicator": indicator,
                    "n_bands": 3, "direction": "contrarian" if market == "cn" else "momentum",
                    "edge_mode": "fixed", "low_edge": lo, "high_edge": hi,
                    "gate_mode": "off", "gate_cap": 0.0,
                })
    return grid


def build_grid_v3(symbols: list[str], indicators: list[str]) -> list[dict]:
    """终审网格：A股=逆势阶梯细化+反转防守族；美股=顺势+波动率目标族。"""
    grid: list[dict] = []
    cn = [x for x in symbols if INSTRUMENTS[x].market == "cn"]
    us = [x for x in symbols if INSTRUMENTS[x].market == "us"]
    for symbol in symbols:
        if symbol not in INSTRUMENTS:
            raise ValueError(f"未知标的 {symbol}")
    for symbol in cn:
        for indicator in ("b200",):
            for n_bands in (3, 5):
                for lo, hi in V3_EDGES:
                    for gamma in V3_GAMMAS_CN:
                        for vol in V3_VOLS_CN:
                            for gate in ("off", "ma200"):
                                for mw in V3_MIN_W_CN:
                                    grid.append({
                                        "symbol": symbol, "strategy": "ladder",
                                        "indicator": indicator, "n_bands": n_bands,
                                        "direction": "contrarian", "edge_mode": "fixed",
                                        "low_edge": lo, "high_edge": hi, "gamma": gamma,
                                        "vol_target": vol, "min_weight": mw,
                                        "gate_mode": gate, "gate_cap": 0.0,
                                    })
        for indicator in ("b200", "b50"):
            for low, high in V3_REV_EXTREMES:
                for batches in V3_REV_BATCHES:
                    for ratio in V3_REV_RATIOS:
                        for sell in V3_REV_SELL:
                            for confirm in V3_REV_CONFIRMS:
                                grid.append({
                                    "symbol": symbol, "strategy": "reversal",
                                    "indicator": indicator, "low_extreme": low,
                                    "high_extreme": high, "confirm": confirm,
                                    "batch_mode": "band", "batches": batches,
                                    "batch_ratio": ratio, "sell_batches": sell,
                                    "gate_mode": "ma200", "gate_cap": 0.0,
                                })
    for symbol in us:
        for n_bands in (3, 5):
            for lo, hi in V3_EDGES:
                for gamma in V3_GAMMAS_US:
                    for vol in V3_VOLS_US:
                        for mw in V3_MIN_W_US:
                            grid.append({
                                "symbol": symbol, "strategy": "ladder",
                                "indicator": "b200", "n_bands": n_bands,
                                "direction": "momentum", "edge_mode": "fixed",
                                "low_edge": lo, "high_edge": hi, "gamma": gamma,
                                "vol_target": vol, "min_weight": mw,
                                "gate_mode": "ma200", "gate_cap": 0.0,
                            })
    return grid


def build_grid_v2(symbols: list[str], indicators: list[str]) -> list[dict]:
    """资金管理维度网格：档位范围 × 陡度 × 批次比例 × 卖出独立 × 闸门 × 波动率目标。"""
    grid: list[dict] = []
    for symbol in symbols:
        if symbol not in INSTRUMENTS:
            raise ValueError(f"未知标的 {symbol}")
        for indicator in indicators:
            for n_bands in LADDER_N_BANDS:
                for lo, hi in LADDER_EDGES:
                    for gamma in LADDER_GAMMAS:
                        for direction in LADDER_DIRECTIONS:
                            for gate in GATES:
                                for vol in VOL_TARGETS:
                                    grid.append(
                                        {
                                            "symbol": symbol,
                                            "strategy": "ladder",
                                            "indicator": indicator,
                                            "n_bands": n_bands,
                                            "edge_mode": "fixed",
                                            "direction": direction,
                                            "low_edge": lo,
                                            "high_edge": hi,
                                            "gamma": gamma,
                                            "vol_target": vol,
                                            "gate_mode": gate,
                                            "gate_cap": 0.0,
                                        }
                                    )
            for low, high in REVERSAL_EXTREMES_V2:
                for batch_mode in REVERSAL_BATCH_MODES:
                    for batches in REVERSAL_BATCHES_V2:
                        for ratio in REVERSAL_BATCH_RATIOS:
                            for sell_n in SELL_OVERRIDES:
                                for gate in GATES:
                                    grid.append(
                                        {
                                            "symbol": symbol,
                                            "strategy": "reversal",
                                            "indicator": indicator,
                                            "low_extreme": low,
                                            "high_extreme": high,
                                            "confirm": 5.0,
                                            "batch_mode": batch_mode,
                                            "batches": batches,
                                            "batch_ratio": ratio,
                                            "sell_batches": sell_n,
                                            "gate_mode": gate,
                                            "gate_cap": 0.0,
                                        }
                                    )
    return grid


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
