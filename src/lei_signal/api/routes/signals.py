"""今日自选信号：统一买/卖点面板（看盘主页横幅）的数据源。

GET 只读库（买点 daily_opportunity_scan + 卖点 signal_alerts 合并）；
POST refresh 现场重扫并落两表。不推通知（用户决策：只面板+红点）。
"""
from contextlib import closing

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.opportunity_scan import list_scan, today_date
from lei_signal.api.routes.opportunities import _row_to_scan_item
from lei_signal.api.schemas import (
    ScanItemDTO,
    SignalAlertDTO,
    SignalsTodayResponse,
    UnavailableItemDTO,
)
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["signals"])

_TIER_GROUPS = {"hard": "sell_hard", "warn": "sell_warn", "soft": "sell_soft"}


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _service(request: Request):
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    return service


def _build_response(db_path: str) -> SignalsTodayResponse:
    scan_date = today_date()
    with closing(connect(db_path)) as conn:
        buy_rows = list_scan(conn, scan_date)
        sell_rows = list_signal_alerts(conn, scan_date, side=SIDE_SELL)
        unavailable_rows = list_signal_alerts(conn, scan_date, side=SIDE_UNAVAILABLE)
        as_of = get_scan_as_of(conn, scan_date)
    all_rows = buy_rows + sell_rows + unavailable_rows
    response = SignalsTodayResponse(
        scan_date=scan_date,
        as_of=as_of,
        generated_at=max((r.generated_at for r in all_rows), default=""),
        scanned=len({r.symbol for r in all_rows if r.symbol}),
    )
    for row in buy_rows:
        item: ScanItemDTO = _row_to_scan_item(row)
        if item.verdict == "actionable":
            response.actionable.append(item)
        elif item.verdict == "waiting":
            response.waiting.append(item)
        elif item.verdict == "blocked":
            response.blocked.append(item)
    for row in sell_rows:
        dto = SignalAlertDTO(
            symbol=row.symbol, display_name=row.display_name, tier=row.tier,
            kind=row.kind, kind_cn=row.kind_cn, title=row.title,
            reason_cn=row.reason_cn, is_new=row.is_new,
            key_prices=dict(row.key_prices), provenance=row.provenance,
            available_date=row.available_date or None,
        )
        group = _TIER_GROUPS.get(row.tier)
        if group is not None:
            getattr(response, group).append(dto)
    for row in unavailable_rows:
        response.unavailable.append(
            UnavailableItemDTO(symbol=row.symbol, error=row.error)
        )
    return response


@router.get("/signals/today", response_model=SignalsTodayResponse)
def today_signals(request: Request) -> SignalsTodayResponse:
    """今日自选信号（读库）：看盘主页横幅 + 顶栏红点合计的数据源。"""
    return _build_response(_db_path(request))


@router.post("/signals/today/refresh", response_model=SignalsTodayResponse)
def refresh_today_signals(request: Request, as_of: str = "close") -> SignalsTodayResponse:
    """立即重扫自选（买+卖）并整体重写当日两表。as_of: intraday | close。"""
    from lei_signal.api.signal_scan import (  # noqa: PLC0415
        AS_OF_CLOSE,
        AS_OF_INTRADAY,
        run_signal_scan,
    )

    if as_of not in (AS_OF_INTRADAY, AS_OF_CLOSE):
        raise HTTPException(status_code=422, detail="as_of 只能是 intraday 或 close")
    run_signal_scan(_service(request), _db_path(request), as_of=as_of, refresh=True)
    return _build_response(_db_path(request))


__all__ = ["refresh_today_signals", "router", "today_signals"]
