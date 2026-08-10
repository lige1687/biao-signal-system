"""基本面参考层端点：宏观指标 + 行业板块全景 + 行业资金流历史。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from lei_signal.fundamentals import sources
from lei_signal.fundamentals.service import FundamentalsService

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])


def _service(request: Request) -> FundamentalsService:
    return request.app.state.fundamentals_service


@router.get("/overview")
def overview(request: Request, refresh: bool = False) -> dict:
    """宏观卡片 + 行业板块全景。TTL 缓存；refresh=true 强制重拉。"""
    return _service(request).overview(refresh=refresh)


@router.get("/industry/{code}/flow")
def industry_flow(request: Request, code: str, days: int = 20) -> dict:
    """单个行业板块资金流历史（日级，主力/超大/大/中/小单，单位亿元）。"""
    if not code.startswith("BK"):
        raise HTTPException(status_code=400, detail="行业代码须为东财 BK 代码")
    try:
        return _service(request).industry_flow(code, days=days)
    except sources.FundamentalsSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
