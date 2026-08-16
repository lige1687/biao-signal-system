"""行业板块趋势工作台 · 路由（P2.1）。

前缀 ``/api/sectors``（**不**注册裸 ``/api/sectors``，该路径已被 watchlist 占用）。
判定标 ``research_proxy``，所有响应均来自磁盘冻结快照，本路由不重算、不出买卖点。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.sectors_service import SectorsService

router = APIRouter(prefix="/api/sectors", tags=["sectors"])

_NOT_PRECOMPUTED = "尚未运行预计算，请先跑 scripts/precompute_sector_trend.py"


def _service(request: Request) -> SectorsService:
    return request.app.state.sectors_service


@router.get("/trend")
def trend(request: Request, refresh: bool = False, level: str = "all") -> dict:
    """板块趋势快照（等权指数/RS/宽度/阶段/MACD）。miss → 404 提示先跑预计算。

    ``level=all|l1|l2|l3``：过滤层级（同产业链父子去重在前端用 parent 字段做）。
    """
    data = _service(request).trend(refresh=refresh, level=level)
    if data is None:
        raise HTTPException(status_code=404, detail=_NOT_PRECOMPUTED)
    return data


@router.get("/{code}/history")
def history(request: Request, code: str, days: int = 250) -> dict:
    """单个板块历史序列（close / b50 / rs_pctile / stage），供趋势图与 RRG 尾迹。"""
    return _service(request).history(code, days=days)


@router.get("/{code}/members")
def members(request: Request, code: str, limit: int = 50) -> dict:
    """板块成分股（当日行情 + 是否在 K线缓存）。miss → 404。"""
    data = _service(request).members(code, limit=limit)
    if data is None:
        raise HTTPException(status_code=404, detail="板块成分股缓存缺失，请先跑预计算脚本")
    return data
