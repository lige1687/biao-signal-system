"""宽度择时回测 API。

- GET  /api/timing-backtest/options  标的/指标/策略参数/预设/数据声明
- POST /api/timing-backtest/runs     同步执行一次回测，返回全结果并落盘
- GET  /api/timing-backtest/runs     历史运行列表（参数+核心指标）
"""
from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lei_signal.timing_backtest.service import (
    TimingDataUnavailable,
    build_options,
    build_portfolio,
    build_signals,
    execute_run,
    list_runs,
    load_run,
)

router = APIRouter(prefix="/api/timing-backtest", tags=["timing-backtest"])


class TimingRunRequest(BaseModel):
    symbol: str = "000300"
    strategy: str = "ladder"          # ladder | reversal
    indicator: str = "b200"           # b20 | b50 | b200
    n_bands: int = 5
    edge_mode: str = "fixed"          # fixed | preq
    direction: str = "contrarian"     # contrarian | momentum
    low_extreme: float = 20.0
    high_extreme: float = 80.0
    confirm: float = 5.0
    batch_mode: str = "time"          # time | band
    batches: int = 5
    gate_mode: str = "off"            # off | ma200
    gate_cap: float = 0.0
    min_weight: float = 0.0           # 阶梯底仓（空仓档位也保留的最小仓位）
    gamma: float = 1.0                # 阶梯陡度：>1 深极值才重仓，<1 浅极值就重仓
    low_edge: float = 0.0             # 阶梯边界下沿（满仓侧）
    high_edge: float = 100.0          # 阶梯边界上沿（空仓侧）
    batch_ratio: float = 1.0          # 批次资金比：>1 首批重(金字塔)，<1 递增
    band_step: float = 10.0           # band 分批的宽度步长
    sell_batches: int | None = None   # 卖出批数（None=同买入）
    sell_ratio: float | None = None   # 卖出批次比（None=同买入）
    trigger_mode: str = "rebound"     # rebound | immediate | extreme_confirm | linger
    breadth: str | None = None        # 宽度来源覆盖（如 cn_cyb / cn_csi300）
    min_trade: float = 0.0            # 最小调仓阈值（目标变化小于此值不执行）
    vol_target: float = 0.0           # 年化波动率目标（0=关闭，如 0.15）
    cash_rate: float = 0.0            # 空仓现金年化利率（如 0.02 = 2%）
    fee_bps: float | None = None      # None = 标的默认（A股 5bp / 美股 1bp）
    start: str | None = None          # YYYY-MM-DD
    end: str | None = None


@router.get("/signals")
def timing_signals() -> list[dict[str, Any]]:
    return build_signals()


@router.get("/portfolio")
def timing_portfolio() -> dict[str, Any]:
    return build_portfolio()


@router.get("/portfolio-equity")
def timing_portfolio_equity() -> dict[str, Any]:
    """A 股组合三档净值（持有/冠军三档/协同=冠军×MA20），8 指数 sleeve 等权。"""

    from lei_signal.timing_backtest.data import (
        align_index_breadth,
        load_breadth,
        load_index_bars,
    )
    from lei_signal.timing_backtest.engine import simulate
    from lei_signal.timing_backtest.metrics import compute_performance
    from lei_signal.timing_backtest.strategies import (
        LadderParams,
        TrendGate,
        build_target,
    )

    sleeves = ["399006", "399975", "399976", "399997", "000819", "399986", "980030", "000300"]
    ladder = LadderParams(
        indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
        min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
    )
    champ_r, syn_r, hold_r = [], [], []
    for sym in sleeves:
        aligned = align_index_breadth(load_index_bars(sym), load_breadth("cn_all"))
        budget = build_target(aligned, ladder, None, TrendGate(), aligned.iloc[:0])
        tech = (aligned["close"] > aligned["close"].rolling(20).mean()).astype(float)
        r1 = simulate(aligned, budget, fee_bps=10.0, cash_rate=0.0,
                      min_trade=0.05).daily["equity"].pct_change().fillna(0)
        r2 = simulate(aligned, budget * tech, fee_bps=10.0, cash_rate=0.0,
                      min_trade=0.05).daily["equity"].pct_change().fillna(0)
        r3 = simulate(aligned, pd.Series(1.0, index=aligned.index), fee_bps=10.0,
                      cash_rate=0.0, min_trade=0.05).daily["equity"].pct_change().fillna(0)
        champ_r.append(r1)
        syn_r.append(r2)
        hold_r.append(r3)
    out = {}
    for name, lst in [("champion", champ_r), ("synergy", syn_r), ("hold", hold_r)]:
        eq = (1 + pd.concat(lst, axis=1).mean(axis=1)).cumprod()
        out[name] = eq
    dates = [d.strftime("%Y-%m-%d") for d in out["hold"].index]
    step = 5
    stats = {
        n: {
            "cagr": compute_performance(eq)["cagr"],
            "mdd": compute_performance(eq)["mdd"],
        }
        for n, eq in out.items()
    }
    return {
        "dates": dates[::step],
        "champion": [round(float(v), 4) for v in out["champion"].values[::step]],
        "synergy": [round(float(v), 4) for v in out["synergy"].values[::step]],
        "hold": [round(float(v), 4) for v in out["hold"].values[::step]],
        "stats": stats,
    }


@router.get("/etf-defense")
def timing_etf_defense(symbol: str = "QQQ") -> dict[str, Any]:
    """美股 ETF 保险对比：防守版（40/80+vol0.15+MA200 闸）净值 vs 持有净值。"""
    from lei_signal.timing_backtest.service import compute_run

    cfg = dict(
        symbol=symbol, strategy="ladder", indicator="b200", n_bands=3,
        direction="momentum", low_edge=40.0, high_edge=80.0, gamma=1.5,
        vol_target=0.15, gate_mode="ma200", min_trade=0.05, fee_bps=10,
        breadth="sp500",
    )
    try:
        run = compute_run(cfg)
    except (ValueError, Exception) as e:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"{type(e).__name__}: {e}") from e
    m = run["metrics"]
    daily = run["daily"]
    return {
        "symbol": symbol,
        "name": run.get("name", symbol),
        "start": daily["date"][0],
        "end": daily["date"][-1],
        "dates": daily["date"][::5],
        "defense": [round(v, 4) for v in daily["equity"][::5]],
        "hold": [round(v, 4) for v in daily["benchmark"][::5]],
        "metrics": {
            "defense_cagr": m["strategy_cagr"], "defense_mdd": m["strategy_mdd"],
            "hold_cagr": m["benchmark_cagr"], "hold_mdd": m["benchmark_mdd"],
            "n_trades": int(m["n_trades"]),
        },
    }


@router.get("/options")
def timing_options() -> dict[str, Any]:
    return build_options()


@router.post("/runs")
def timing_run(req: TimingRunRequest) -> dict[str, Any]:
    try:
        return execute_run(req.model_dump())
    except TimingDataUnavailable as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/runs/{run_id}")
def timing_run_detail(run_id: str) -> dict[str, Any]:
    run = load_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"运行记录不存在：{run_id}")
    return run


@router.get("/runs")
def timing_runs(limit: int = 50) -> list[dict[str, Any]]:
    return list_runs(limit=limit)
