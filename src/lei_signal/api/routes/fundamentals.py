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


@router.get("/rates")
def rates(request: Request, refresh: bool = False) -> dict:
    """利率 + 资金面板：中美国债收益率 + 中美利差 + VIX + 两融余额。"""
    return _service(request).rates(refresh=refresh)


@router.get("/rates-history")
def rates_history(request: Request, lookback_days: int = 730) -> dict:
    """宏观利率/VIX/两融 历史时间序列，供趋势图。lookback_days 默认 730。"""
    return _service(request).rates_history(lookback_days=lookback_days)


@router.get("/macro-history")
def macro_history(request: Request, page_size: int = 60) -> dict:
    """PMI/CPI/PPI 月度历史序列，供趋势图。page_size 默认 60 期（约 5 年）。"""
    return _service(request).macro_history(page_size=page_size)


@router.get("/overlay-history")
def overlay_history(request: Request, years: int = 20) -> dict:
    """长周期叠加序列：国债/两融 × 股指（20 年级），供带 dataZoom 的大图。

    首次加载需翻页拉全史（约 20s），之后 12 小时内走缓存。
    """
    return _service(request).overlay_history(years=years)


@router.get("/commodities")
def commodities(request: Request, refresh: bool = False) -> dict:
    """全球商品代理：铜金比 / 油金比（yfinance）。"""
    return _service(request).commodities(refresh=refresh)


@router.get("/etf-strength")
def etf_strength(request: Request, refresh: bool = False) -> dict:
    """11 行业 ETF 相对强度（risk on/off，yfinance）。"""
    return _service(request).etf_strength(refresh=refresh)


@router.get("/us-macro")
def us_macro(request: Request, refresh: bool = False) -> dict:
    """美国宏观（FRED 公开 CSV）：就业/房产/汽车/WEI/物价/订单/高收益债利差。

    首次加载逐序列拉 FRED（约 15 秒，序列间限速），之后 6 小时走缓存。
    """
    return _service(request).us_macro(refresh=refresh)


@router.get("/industry/{code}/flow")
def industry_flow(request: Request, code: str, days: int = 20) -> dict:
    """单个行业板块资金流历史（日级，主力/超大/大/中/小单，单位亿元）。"""
    if not code.startswith("BK"):
        raise HTTPException(status_code=400, detail="行业代码须为东财 BK 代码")
    try:
        return _service(request).industry_flow(code, days=days)
    except sources.FundamentalsSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
