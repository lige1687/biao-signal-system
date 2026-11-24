"""Expose existing research readers on the main API, without worker lifecycles."""
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from urllib.parse import urlsplit


def _local_research_request(request: Request) -> None:
    # These modules previously listened only on loopback. Keep that boundary
    # when mounting them in the main API, which also supports LAN clients.
    if request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403, "研究资料接口仅供本机工作台读取")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(403, "请从本机工作台访问研究资料")


def install_research_surfaces(app: FastAPI) -> None:
    from lei_signal.factor_workbench.app import app as factors
    from lei_signal.market_style_observation.app import app as market
    from lei_signal.strategy_portfolios import readonly

    def get_dashboard():
        return readonly.dashboard()

    # The standalone portfolio app starts a collector in its lifespan. Register
    # only its existing reader here; page access must never start that worker.
    app.add_api_route("/api/strategy-portfolios", get_dashboard, methods=["GET"], dependencies=[Depends(_local_research_request)])
    for surface in (factors, market):
        routes = [route for route in surface.routes
                  if isinstance(route, APIRoute) and route.path.startswith("/api/")]
        app.include_router(APIRouter(routes=routes), dependencies=[Depends(_local_research_request)])
