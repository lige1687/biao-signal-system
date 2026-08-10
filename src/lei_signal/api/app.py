"""FastAPI 应用工厂。

开发态：vite dev server (localhost:5173) 代理 /api 到本服务。
生产态（可选）：若仓库 web/dist 存在，则挂载为静态站并对非 /api 路径
回退到 index.html（SPA 路由）。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lei_signal.api import config
from lei_signal.api.market_context_service import MarketContextService
from lei_signal.api.routes import (
    agent,
    dashboard,
    feishu_webhook,
    fundamentals,
    opportunities,
    plans,
    symbols,
    watch_subscriptions,
    watchlist,
)
from lei_signal.api.services import AnalysisService
from lei_signal.env import load_env
from lei_signal.fundamentals.service import FundamentalsService

# 本地/launchd 运行前把 .env 注入 os.environ（不覆盖已设变量）。
load_env()


def _build_market_context_service() -> MarketContextService:
    return MarketContextService()

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WEB_DIST = _REPO_ROOT / "web" / "dist"


def create_app(*, analysis_service: AnalysisService | None = None) -> FastAPI:
    app = FastAPI(title="LEI 看盘系统", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.state.analysis_service = analysis_service or AnalysisService(max_workers=8)
    app.state.watchlist_db_path = config.sqlite_path()
    app.state.plans_db_path = config.sqlite_path()
    app.state.market_context_service = _build_market_context_service()
    app.state.fundamentals_service = FundamentalsService()

    app.include_router(dashboard.router)
    app.include_router(symbols.router)
    app.include_router(opportunities.router)
    app.include_router(watchlist.router)
    app.include_router(watch_subscriptions.router)
    app.include_router(plans.router)
    app.include_router(agent.router)
    app.include_router(feishu_webhook.router)
    app.include_router(fundamentals.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if _WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=_WEB_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            candidate = _WEB_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(_WEB_DIST / "index.html")

    return app


app = create_app()
