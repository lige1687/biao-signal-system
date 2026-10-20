"""FastAPI 应用工厂。

开发态：vite dev server (localhost:5173) 代理 /api 到本服务。
生产态（可选）：若仓库 web/dist 存在，则挂载为静态站并对非 /api 路径
回退到 index.html（SPA 路由）。
"""
from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lei_signal.api import config
from lei_signal.api.factor_service import FactorPanelService
from lei_signal.api.market_context_service import MarketContextService
from lei_signal.api.preheat import default_symbols_fn, start_preheat
from lei_signal.api.routes import (
    agent,
    backtest,
    copilot,
    dailybrief,
    dashboard,
    experiments,
    factors,
    feishu_webhook,
    fundamentals,
    learning,
    news,
    opportunities,
    plans,
    portfolio,
    sectors,
    sentiment,
    signals,
    symbols,
    timing_backtest,
    upgrades,
    watch_subscriptions,
    watchlist,
)
from lei_signal.api.sectors_service import SectorsService
from lei_signal.api.services import AnalysisService
from lei_signal.env import load_env
from lei_signal.fundamentals.service import FundamentalsService
from lei_signal.newsfeed.service import NewsfeedService

# 本地/launchd 运行前把 .env 注入 os.environ（不覆盖已设变量）。
load_env()


def _build_market_context_service() -> MarketContextService:
    return MarketContextService()


def _warm_a_share_breadth() -> None:
    """后台预热真全A宽度缓存，首次打开页面不必现场等几秒拉数据。

    daemon 线程不阻塞启动；测试环境（pytest 已导入）跳过，避免单测发网络请求。
    """
    if "pytest" in sys.modules:
        return

    def _run() -> None:
        try:
            from lei_signal.market_context.a_share_breadth import get_a_share_breadth

            get_a_share_breadth(include_ma=False)
        except Exception as e:  # noqa: BLE001 - 预热失败不影响服务
            logging.getLogger(__name__).warning("A股宽度预热失败: %s", e)

    threading.Thread(target=_run, daemon=True, name="a-share-breadth-warmup").start()

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WEB_DIST = _REPO_ROOT / "web" / "dist"


def _install_validation_error_handler(app: FastAPI) -> None:
    """04B（2026-09-08）：请求校验错误的 input 含 NaN/Infinity 时，默认处理器
    序列化 422 响应自身会崩（starlette JSONResponse 拒绝非有限值）→ 500。
    把 errors 里的非有限浮点替换为字符串标记，保证非法价格等输入得到结构化
    422 而不是 500；有限输入的行为与默认处理器完全一致。
    """
    from fastapi.exceptions import RequestValidationError  # noqa: PLC0415
    from fastapi.responses import JSONResponse  # noqa: PLC0415

    def _sanitize_non_finite(obj):  # noqa: ANN001
        import math as _math

        if isinstance(obj, float) and not _math.isfinite(obj):
            return repr(obj)
        if isinstance(obj, list):
            return [_sanitize_non_finite(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _sanitize_non_finite(v) for k, v in obj.items()}
        return obj

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request, exc):  # noqa: ANN001
        from fastapi.encoders import jsonable_encoder  # noqa: PLC0415

        return JSONResponse(
            status_code=422,
            content={"detail": _sanitize_non_finite(
                jsonable_encoder(exc.errors()))},
        )


def create_app(*, analysis_service: AnalysisService | None = None) -> FastAPI:
    app = FastAPI(title="LEI 看盘系统", version="0.1.0")
    _install_validation_error_handler(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        # 放行局域网 origin：手机/平板同 WiFi 经 http://<局域网IP>:8000 直连
        # 静态站或 :5173 dev server 访问 API（IPv4 私网段，任意端口）。
        allow_origin_regex=(
            r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}"
            r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
        ),
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.state.analysis_service = analysis_service or AnalysisService(max_workers=8)
    app.state.watchlist_db_path = config.sqlite_path()
    app.state.plans_db_path = config.sqlite_path()
    app.state.portfolio_db_path = config.sqlite_path()
    app.state.market_context_service = _build_market_context_service()
    app.state.fundamentals_service = FundamentalsService()
    app.state.sectors_service = SectorsService()
    app.state.factor_service = FactorPanelService()
    app.state.newsfeed_service = NewsfeedService()

    app.include_router(dashboard.router)
    app.include_router(symbols.router)
    app.include_router(dailybrief.router)
    app.include_router(opportunities.router)
    app.include_router(watchlist.router)
    app.include_router(watch_subscriptions.router)
    app.include_router(plans.router)
    app.include_router(portfolio.router)
    app.include_router(signals.router)
    app.include_router(agent.router)
    app.include_router(copilot.router)
    app.include_router(feishu_webhook.router)
    app.include_router(fundamentals.router)
    app.include_router(sectors.router)
    app.include_router(sentiment.router)
    app.include_router(backtest.router)
    app.include_router(timing_backtest.router)
    app.include_router(factors.router)
    app.include_router(news.router)
    app.include_router(experiments.router)
    # 文献学习库：只读学习目录（learning-seed.json），不参与交易判定
    app.include_router(learning.router)
    app.include_router(upgrades.router)

    _warm_a_share_breadth()
    # 看盘缓存后台预热：按用户时效性要求定时强刷（盘中 12 分钟 / 收盘补一次 /
    # 夜间仅指数组 / 基本面每日），页面打开永远命中内存缓存。规则见 preheat.py。
    app.state.preheat_stop = start_preheat(
        app.state.analysis_service,
        app.state.fundamentals_service,
        default_symbols_fn(app.state.watchlist_db_path),
    )

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
            # HTML 不缓存（避免引用旧 hash 的 assets）；assets 文件名带内容
            # hash 可长缓存，部署后浏览器必然拿到新入口。
            return FileResponse(_WEB_DIST / "index.html", headers={
                "Cache-Control": "no-cache, must-revalidate",
            })

    return app


app = create_app()
