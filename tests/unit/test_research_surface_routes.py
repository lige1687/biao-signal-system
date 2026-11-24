"""The daily entry must serve research pages without starting research workers."""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_installs_research_routes_without_workers_or_duplicate_docs(monkeypatch):
    from lei_signal.api.research_surfaces import install_research_surfaces
    from lei_signal.factor_workbench import app as factors
    from lei_signal.market_style_observation import app as market
    from lei_signal.strategy_portfolios import server
    from lei_signal.strategy_portfolios import readonly

    monkeypatch.setattr(readonly, "dashboard", lambda: {"markets": [], "run": {"status": "fixture"}})
    monkeypatch.setattr(factors, "build_progress", lambda _: {"cases": []})
    monkeypatch.setattr(factors, "extend_progress", lambda _, x: x)
    monkeypatch.setattr(factors, "extend_intake", lambda _, x: x)
    monkeypatch.setattr(market, "get_history", lambda: {"fixture": True})
    monkeypatch.setattr(market, "build_window", lambda history, days: {"days": days})
    def forbidden(*args, **kwargs):
        raise AssertionError("Reading a page must not launch collection or interpretation")
    monkeypatch.setattr(server.subprocess, "Popen", forbidden)
    monkeypatch.setattr(factors, "invoke_selection", forbidden)
    monkeypatch.setattr(market, "invoke_selection", forbidden)
    app = FastAPI()
    install_research_surfaces(app)
    with TestClient(app) as client:
        assert client.get("/api/factor-workbench/progress").json() == {"cases": []}
        assert client.get("/api/market-style/daily-history?days=90").json() == {"days": 90}
        assert client.get("/api/strategy-portfolios").json()["run"]["status"] == "fixture"
        assert client.get("/api/market-style/daily-history?days=1").status_code == 422
        assert client.get("/api/factor-workbench/progress", headers={"Origin": "https://unrelated.example"}).status_code == 403
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert len(paths) == len(set(paths))
    assert paths.count("/docs") == 1
    assert "/api/factor-workbench/progress" in app.openapi()["paths"]
    assert "/api/market-style/daily-history" in app.openapi()["paths"]
