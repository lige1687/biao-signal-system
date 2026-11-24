"""The GET endpoint is a read-only projection; old scorecard stays separate."""

import json
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes.fwd_ledger import router
from lei_signal.forward_observation import initialize, runner

BASE = datetime(2026, 10, 20, 1, 0, tzinfo=UTC)


def config():
    return {
        "group": {"symbol": "510300.SS", "name": "沪深300ETF"},
        "initial_cash": 100000,
        "accounts": [{"id": "buy", "kind": "buy_hold"}, {"id": "cash", "kind": "cash"}],
    }


def test_get_missing_then_frozen_without_creating_database(tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.state.forward_observation_db_path = tmp_path / "ledger.db"
    app.state.forward_observation_config_path = tmp_path / "config.json"
    app.state.forward_observation_config_path.write_text(json.dumps(config()), encoding="utf-8")
    client = TestClient(app)
    response = client.get("/api/fwd-ledger/strategies")
    assert response.status_code == 200
    assert response.json()["run"]["status"] == "not_started"
    assert not app.state.forward_observation_db_path.exists()

    initialize(app.state.forward_observation_db_path, config(), BASE.isoformat())
    response = client.get("/api/fwd-ledger/strategies?range=common")
    assert response.status_code == 200
    body = response.json()
    assert body["range"] == "common"
    assert body["run"]["frozen_at"] == BASE.isoformat()
    assert body["accounts"][0]["series"] == []
    assert client.get("/api/fwd-ledger/strategies?range=invalid").status_code == 422


def test_post_routes_to_explicit_runner_without_collecting_in_test(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(router)
    app.state.forward_observation_db_path = tmp_path / "ledger.db"
    app.state.forward_observation_config_path = tmp_path / "config.json"
    app.state.forward_observation_config_path.write_text(json.dumps(config()), encoding="utf-8")
    called = []

    def fake_runner(*, db_path, config_path, now):
        called.append((db_path, config_path, now))
        return {"run": {"status": "waiting_quote"}}

    monkeypatch.setattr(runner, "observe_once", fake_runner)
    response = TestClient(app).post("/api/fwd-ledger/strategies/observe")
    assert response.status_code == 200
    assert response.json()["run"]["status"] == "waiting_quote"
    assert called[0][:2] == (
        app.state.forward_observation_db_path,
        app.state.forward_observation_config_path,
    )
    assert not app.state.forward_observation_db_path.exists()
