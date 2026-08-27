"""宽度择时回测 API。

- GET  /api/timing-backtest/options  标的/指标/策略参数/预设/数据声明
- POST /api/timing-backtest/runs     同步执行一次回测，返回全结果并落盘
- GET  /api/timing-backtest/runs     历史运行列表（参数+核心指标）
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lei_signal.timing_backtest.service import (
    TimingDataUnavailable,
    build_options,
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
