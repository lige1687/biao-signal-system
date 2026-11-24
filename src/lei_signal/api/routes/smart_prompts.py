"""全站通用大白话智能提示 API 路由（smart_prompts）。

提供三个通用实时接口，随日期、行情、财报、持仓与用户买进价动态计算：
1. GET /api/smart-prompts/symbol/{symbol}?entry_price=...
   任意股票、场内基金、美股或场外基金的【排雷底色 + 当前能不能买/补 + 两步拿住保护线】
2. GET /api/smart-prompts/portfolio
   当前持仓的【必须动手红黄灯提醒 + 本月新工资投向 + 每只持仓动态健康灯】
3. GET /api/smart-prompts/one-page?top=8
   【一页看全】完整数据：顶栏大盘极端警报 + 左屏持仓健康灯 + 右屏今日基金与真龙头尖子生
"""
from __future__ import annotations

from pathlib import Path
import time
from fastapi import APIRouter, HTTPException, Query, Request

from lei_signal.strategy_lab.data_portal import DataPortal
from lei_signal.strategy_lab.universal_prompts import (
    build_one_page_overview,
    evaluate_portfolio_smart_prompts,
    evaluate_symbol_smart_prompt,
)

router = APIRouter(prefix="/api/smart-prompts", tags=["smart-prompts"])

_CACHE: dict[str, tuple[float, dict]] = {}
_TTL_SEC = 90.0


def _make_portal(request: Request) -> DataPortal:
    db_path = getattr(request.app.state, "portfolio_db_path", None)
    if db_path:
        p = Path(db_path)
        if p.name == "lab.db":
            return DataPortal(lab_home=p.parent)
    return DataPortal()


@router.get("/symbol/{symbol}")
def get_symbol_smart_prompt(
    symbol: str,
    request: Request,
    entry_price: float | None = Query(default=None, gt=0.0, description="可选：用户买进成本价，用于动态切换两步拿牛保护线"),
) -> dict[str, object]:
    portal = _make_portal(request)
    try:
        return evaluate_symbol_smart_prompt(portal, symbol, entry_price=entry_price)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"计算提示失败：{exc}") from exc


@router.get("/portfolio")
def get_portfolio_smart_prompts(
    request: Request,
    force: bool = Query(default=False, description="强制重新计算而不走短缓存"),
) -> dict[str, object]:
    portal = _make_portal(request)
    cache_key = f"portfolio:{portal.lab_home}"
    now = time.monotonic()
    if not force and cache_key in _CACHE and (now - _CACHE[cache_key][0]) < _TTL_SEC:
        return _CACHE[cache_key][1]
    res = evaluate_portfolio_smart_prompts(portal)
    _CACHE[cache_key] = (now, res)
    return res


@router.get("/one-page")
def get_one_page_overview(
    request: Request,
    top: int = Query(default=8, ge=3, le=20),
    force: bool = Query(default=False),
) -> dict[str, object]:
    portal = _make_portal(request)
    cache_key = f"onepage:{portal.lab_home}:{top}"
    now = time.monotonic()
    if not force and cache_key in _CACHE and (now - _CACHE[cache_key][0]) < _TTL_SEC:
        return _CACHE[cache_key][1]
    res = build_one_page_overview(portal, top_n=top)
    _CACHE[cache_key] = (now, res)
    return res
