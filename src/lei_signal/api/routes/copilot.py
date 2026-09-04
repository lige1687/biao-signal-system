"""Agent 超级入口路由：确定性流水线的 HTTP 壳（判定权在流水线与既有规则层）。

本文件不做任何新判定；推荐/档位/台账/复盘全部来自 copilot 包的纯函数与
既有 DTO。LLM 讲解只在 explain 类端点出现，且输出过接地校验、失败降级模板。
"""
from __future__ import annotations

import logging
from contextlib import closing
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import RecommendCardDTO, SizingAdviceDTO
from lei_signal.copilot import journal
from lei_signal.copilot.recommend import build_recommendation
from lei_signal.storage.sqlite_store import connect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["copilot"])


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _service(request: Request):
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    return service


def _sector_rows(request: Request) -> list[dict] | None:
    """板块阶段快照（容错：服务缺失/未预计算时返回 None，推荐照常出）。"""
    svc = getattr(request.app.state, "sectors_service", None)
    if svc is None:
        return None
    try:
        data = svc.trend(refresh=False, level="l1")
    except Exception:  # noqa: BLE001  快照缺席不阻断推荐
        return None
    if not isinstance(data, dict):
        return None
    for key in ("sectors", "rows", "items"):
        rows = data.get(key)
        if isinstance(rows, list):
            return rows
    return None


def _news_brief(request: Request) -> dict | None:
    """自选×近3天消息面简报（容错适配在 recommend.extract_news_heat）。"""
    svc = getattr(request.app.state, "newsfeed_service", None)
    if svc is None:
        return None
    try:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(
            connect(
                getattr(request.app.state, "watchlist_db_path", "")
                or _db_path(request)
            )
        ) as conn:
            watch = [
                {"symbol": w.symbol, "display_name": w.display_name, "market": w.market}
                for w in list_watchlist(conn)
            ]
        return svc.watchlist_brief(watch, days=3)
    except Exception:  # noqa: BLE001
        return None


def _recommend_card(request: Request, *, refresh: bool = False) -> RecommendCardDTO:
    """今日推荐组装（路由/脚本共用）：当日扫描表优先，空表或 refresh 现场扫。"""
    from lei_signal.api.opportunity_scan import (  # noqa: PLC0415
        list_scan,
        today_date,
        upsert_scan_results,
    )
    from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
        _row_to_scan_item,
        run_opportunity_scan,
    )

    db = _db_path(request)
    scan_date = today_date()
    scan_items = None
    if not refresh:
        with closing(connect(db)) as conn:
            rows = list_scan(conn, scan_date)
        if rows:
            scan_items = [_row_to_scan_item(r) for r in rows]
    if scan_items is None:
        response = run_opportunity_scan(_service(request), db, refresh=refresh)
        scan_items = list(response.items)
        with closing(connect(db)) as conn:
            upsert_scan_results(conn, scan_date, scan_items)
            conn.commit()
    return build_recommendation(
        scan_items,
        run_date=scan_date,
        sector_rows=_sector_rows(request),
        news_brief=_news_brief(request),
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get("/copilot/recommend", response_model=RecommendCardDTO)
def get_recommend(
    request: Request, refresh: bool = False, save: bool = True
) -> RecommendCardDTO:
    """今日推荐（确定性，零 LLM）。save=true 时按 run_date 存证进推荐账本。"""
    card = _recommend_card(request, refresh=refresh)
    if save and card.items:
        with closing(connect(_db_path(request))) as conn:
            journal.save_recommendation(conn, card)
            conn.commit()
    return card


@router.get("/copilot/position-advice/{symbol}", response_model=SizingAdviceDTO)
def position_advice(request: Request, symbol: str) -> SizingAdviceDTO:
    """仓位档位建议：盈亏比取该标的买点审阅最优候选，只建议档位不算金额。"""
    from lei_signal.api.routes.opportunities import buy_point_review  # noqa: PLC0415
    from lei_signal.copilot.sizing import build_sizing_advice  # noqa: PLC0415

    review = buy_point_review(request, symbol)
    best = review.candidates[0] if review.candidates else None
    if best is None and review.resonance_groups:
        best = review.resonance_groups[0].candidates[0]
    rr = best.reward_risk_ratio if best else None
    return build_sizing_advice(
        symbol,
        rr,
        rr_computable=bool(best.reward_risk_computable) if best else False,
    )
