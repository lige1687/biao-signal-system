"""因子观测台 · 路由。

前缀 ``/api/factors``。所有响应来自磁盘冻结快照，本路由不重算、不出买卖点；
评级为研究留痕（见 ``factor_panel.FACTOR_META``），前端不得另造评级。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.factor_service import FactorPanelService

router = APIRouter(prefix="/api/factors", tags=["factors"])

_NOT_PRECOMPUTED = "尚未运行预计算，请先跑 scripts/precompute_factor_panel.py"


def _service(request: Request) -> FactorPanelService:
    return request.app.state.factor_service


@router.get("/panel")
def panel(request: Request, refresh: bool = False) -> dict:
    """因子面板快照（评级卡 + 标的因子表 + 板块 12-1 排名）。miss → 404 提示先跑预计算。"""
    data = _service(request).panel(refresh=refresh)
    if data is None:
        raise HTTPException(status_code=404, detail=_NOT_PRECOMPUTED)
    return data
