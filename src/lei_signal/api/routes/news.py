"""资讯流 · 路由。

前缀 ``/api/news``。数据来自 SQLite（迁移 016），由 launchd 每日 20:30 或
``POST /run`` 写入；本路由只读 + 触发，不做抓取（抓取在管线线程里）。
参考层红线：排序/归类是 LLM 的结构化工序，不是交易信号。
"""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, Request

from lei_signal.api.watchlist import list_watchlist
from lei_signal.newsfeed.service import NewsfeedService
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/news", tags=["news"])


def _service(request: Request) -> NewsfeedService:
    return request.app.state.newsfeed_service


@router.get("/items")
def items(
    request: Request,
    category: str | None = None,
    q: str | None = None,
    source: str | None = None,
    symbol: str | None = None,
    direction: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    scored: str = "all",
    min_importance: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """条目列表：默认已评分按重要性降序在前，未评分垫底按时间倒序。

    symbol/direction 是把消息对齐到自选与多空视角的结构化过滤，仍属参考层。
    """
    return _service(request).items(
        {
            "category": category,
            "q": q,
            "source": source,
            "symbol": symbol,
            "direction": direction,
            "from": date_from,
            "to": date_to,
            "scored": scored,
            "min_importance": min_importance,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/watchlist-brief")
def watchlist_brief(request: Request, days: int = 3) -> dict:
    """自选标的 × 近 N 天消息聚合：每标的多空计数 + 最新一条 + 全局多空温度。

    自选来自 watchlist 表（与 newsfeed 同库）；零消息标的不返回（零噪音）。
    """
    with closing(connect(request.app.state.watchlist_db_path)) as conn:
        watch = [
            {
                "symbol": w.symbol,
                "display_name": w.display_name,
                "market": w.market,
            }
            for w in list_watchlist(conn)
        ]
    return _service(request).watchlist_brief(watch, days=days)


@router.get("/digests")
def digests(request: Request, limit: int = 7) -> dict:
    """最近 N 天整合简报（时间倒序）。"""
    return {"digests": _service(request).digests(limit)}


@router.post("/run")
def run(request: Request, full: bool = False) -> dict:
    """手动触发整条管线（后台线程）。已在跑时返回 already_running。"""
    return _service(request).trigger_run(full=full)


@router.get("/status")
def status(request: Request) -> dict:
    """最近一次 run + 计数（前端刷新按钮轮询用）。"""
    return _service(request).status()
