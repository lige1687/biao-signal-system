"""回测工作台 API（web 前端参数化回测 + 记录留存）。

- GET  /api/backtest/options        可调参数与术语表（悬浮提示的唯一文案来源）
- POST /api/backtest/runs           发起回测（后台线程），返回 run_id
- GET  /api/backtest/runs           历史记录列表
- GET  /api/backtest/runs/{run_id}  单次结果（总览/分组/逐笔明细）
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lei_signal.backtest.engine import (
    ENTRY_EARLY,
    EXIT_COSTBASIS,
    EXIT_STRUCTURE_STOP,
    EXIT_TOP_PLUS_KEYWAVE,
    EXIT_VARIANT_CN,
)
from lei_signal.backtest.service import (
    ENTRY_VARIANT_CN,
    FEE_LABEL_CN,
    GLOSSARY,
    MODULE_CN,
    MODULE_VARIANT_CN,
    OVERRIDE_SPECS,
    RR_LEVELS,
    BacktestParams,
    klines,
    list_runs,
    load_run,
    run_status,
    start_run,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class RunRequest(BaseModel):
    symbols: list[str] | None = None       # None = 全池
    module: str = "A"
    rr_min: float | None = 3.0
    entry_variant: str | None = None       # None = 该模块默认变体
    exit_variant: str = EXIT_COSTBASIS
    fee_label: str = "standard"
    limit_guard: bool = True
    overrides: dict[str, float] | None = None
    # 入场确认过滤器（第四轮，默认全关）：
    volume_confirm: bool = False
    volume_confirm_window: int = 5
    profile_filter: str = "none"           # none/poc_support/vacuum/both
    gap_target: bool = False
    gap_momentum: bool = False
    gap_momentum_lookback: int = 10
    # 缩量回调确认（第四轮补充验证，默认关）：
    volume_filter: str = "none"             # none / shrink
    shrink_recent: int | None = None        # None = 账本默认（3）
    shrink_prior: int | None = None         # None = 账本默认（3）
    volume_filter_vr_max: float | None = None  # 叠加严格档：信号日量比 < 此值
    # 深乖离增强（BCD 重测，默认关；负值如 -0.15 = 信号日低于 EMA120 15%）：
    bias_filter: float | None = None
    # 深乖离增强（BCD 重测轮，默认关）：
    bias_filter: float | None = None        # None=关；-0.15 = 低于 EMA120 15% 以上才入


@router.get("/options")
def backtest_options() -> dict[str, Any]:
    return {
        "rr_levels": [
            {
                "value": level,
                "label": (
                    "不设门槛（能算出目标即可）"
                    if level is None
                    else f"盈亏比 ≥ {level:g}"
                ),
            }
            for level in RR_LEVELS
        ],
        "entry_variants": [
            {"value": value, "label": label} for value, label in ENTRY_VARIANT_CN.items()
        ],
        "exit_variants": [
            {"value": EXIT_COSTBASIS, "label": EXIT_VARIANT_CN[EXIT_COSTBASIS]},
            {"value": EXIT_TOP_PLUS_KEYWAVE, "label": EXIT_VARIANT_CN[EXIT_TOP_PLUS_KEYWAVE]},
            {"value": EXIT_STRUCTURE_STOP, "label": EXIT_VARIANT_CN[EXIT_STRUCTURE_STOP]},
            {"value": "b3_dual", "label": EXIT_VARIANT_CN["b3_dual"]},
        ],
        "fee_labels": [
            {"value": value, "label": label} for value, label in FEE_LABEL_CN.items()
        ],
        "volume_confirm_windows": [
            {"value": 1, "label": "开（仅信号日）"},
            {"value": 5, "label": "开（近 5 日）"},
        ],
        "profile_filters": [
            {"value": "none", "label": "关"},
            {"value": "poc_support", "label": "踩峰买（价下 1×ATR 内有 POC）"},
            {"value": "vacuum", "label": "上方无套牢（overhead ≤ 30%）"},
            {"value": "both", "label": "两者同时"},
        ],
        "volume_filters": [
            {"value": "none", "label": "关"},
            {"value": "shrink", "label": "开（近3日均量 < 前3日均量）"},
        ],
        "bias_filters": [
            {"value": 0, "label": "关"},
            {"value": -0.15, "label": "开（低于 EMA120 ≥ 15%）"},
            {"value": -0.25, "label": "开（低于 EMA120 ≥ 25%，极端档）"},
        ],
        "bias_filters": [
            {"value": None, "label": "关"},
            {"value": -0.15, "label": "-15%（深乖离档一）"},
            {"value": -0.25, "label": "-25%（深乖离档二）"},
        ],
        "modules": [
            {"value": m, "label": label, "variants": MODULE_VARIANT_CN[m]}
            for m, label in MODULE_CN.items()
        ],
        "defaults": {
            "module": "A",
            "rr_min": 3.0,
            "entry_variant": ENTRY_EARLY,
            "exit_variant": EXIT_COSTBASIS,
            "fee_label": "standard",
        },
        "glossary": GLOSSARY,
        "param_specs": OVERRIDE_SPECS,
    }


@router.post("/runs")
def create_run(request: RunRequest) -> dict[str, str]:
    params = BacktestParams(
        symbols=tuple(request.symbols) if request.symbols else None,
        module=request.module,
        rr_min=request.rr_min,
        entry_variant=request.entry_variant,
        exit_variant=request.exit_variant,
        fee_label=request.fee_label,
        limit_guard=request.limit_guard,
        overrides=tuple(sorted((request.overrides or {}).items())),
        volume_confirm=request.volume_confirm,
        volume_confirm_window=request.volume_confirm_window,
        profile_filter=request.profile_filter,
        volume_filter=request.volume_filter,
        shrink_recent=request.shrink_recent,
        shrink_prior=request.shrink_prior,
        volume_filter_vr_max=request.volume_filter_vr_max,
        bias_filter=request.bias_filter,
        gap_target=request.gap_target,
        gap_momentum=request.gap_momentum,
        gap_momentum_lookback=request.gap_momentum_lookback,
    )
    try:
        params.validate()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run_id = start_run(params)
    return {"run_id": run_id}


@router.get("/runs")
def get_runs() -> list[dict[str, Any]]:
    return list_runs()


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    status = run_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"回测记录不存在: {run_id}")
    if status["status"] != "done":
        return status
    result = load_run(run_id)
    if result is None:
        raise HTTPException(status_code=500, detail=f"回测记录读取失败: {run_id}")
    return result


@router.get("/klines/{symbol}")
def get_klines(symbol: str, limit: int = 3000) -> dict[str, Any]:
    try:
        return klines(symbol, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
