"""Exercise only the history HTTP route, without app startup or database writes."""
from __future__ import annotations

import copy
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes.symbols import market_context_breadth_history
from lei_signal.market_context import a_share_breadth, us_breadth


@pytest.fixture()
def client():
    app = FastAPI()
    app.add_api_route("/api/market-context/breadth-history", market_context_breadth_history)
    return TestClient(app)


@pytest.mark.parametrize("market", ["CN_ALL_A", "SP500"])
def test_observation_is_opt_in_and_preserves_original_history(client, monkeypatch, market):
    row = {"date": "2026-10-30", "ma20_pct": 40.0, "ma50_pct": 45.0,
           "ma200_pct": 60.0, "breadth_20": 40.0, "breadth_50": 45.0,
           "breadth_200": 60.0}
    original = copy.deepcopy(row)
    module, getter = (a_share_breadth, "get_ma_breadth_history") if market == "CN_ALL_A" else (
        us_breadth, "get_sp500_breadth_history")
    monkeypatch.setattr(module, getter, lambda **kwargs: [row])
    base = f"/api/market-context/breadth-history?market_id={market}&lookback_days=365"
    legacy = client.get(base)
    observed = client.get(base + "&include_observation=true")
    assert legacy.status_code == observed.status_code == 200
    legacy_data, observed_data = legacy.json(), observed.json()
    assert "observation" not in legacy_data
    assert "observation" in observed_data
    assert {key: value for key, value in observed_data.items() if key != "observation"} == (
        legacy_data)
    assert observed_data["observation"]["latest"]["date"] == row["date"]
    assert row == original


def test_bad_date_does_not_turn_optional_reader_into_500(client, monkeypatch):
    monkeypatch.setattr(us_breadth, "get_sp500_breadth_history", lambda **kwargs: [
        {"date": "bad-date", "breadth_20": 20.0, "breadth_50": 30.0, "breadth_200": 50.0}])
    response = client.get(
        "/api/market-context/breadth-history?market_id=SP500&include_observation=true")
    assert response.status_code == 200
    assert response.json()["history"][0]["date"] == "bad-date"
    assert response.json().get("observation", {}).get("error") == "invalid_date_axis"


def test_unknown_market_preserves_legacy_error(client):
    response = client.get(
        "/api/market-context/breadth-history?market_id=NO_SUCH_MARKET&include_observation=true")
    assert response.status_code == 200
    assert response.json() == {
        "market_id": "NO_SUCH_MARKET", "error": "unknown_market", "history": []}


@pytest.mark.parametrize("market", ["CN_ALL_A", "SP500"])
def test_lookback_only_limits_observation_transport(client, monkeypatch, market):
    rows = [
        {"date": (date(2020, 1, 1) + timedelta(days=i)).isoformat(),
         "ma20_pct": float(i % 101), "ma50_pct": 50.0, "ma200_pct": 60.0,
         "breadth_20": float(i % 101), "breadth_50": 50.0, "breadth_200": 60.0}
        for i in range(300)
    ]
    module, getter = (a_share_breadth, "get_ma_breadth_history") if market == "CN_ALL_A" else (
        us_breadth, "get_sp500_breadth_history")
    monkeypatch.setattr(module, getter, lambda **kwargs: rows)
    base = f"/api/market-context/breadth-history?market_id={market}&include_observation=true"
    short = client.get(base + "&lookback_days=10").json()
    long = client.get(base + "&lookback_days=300").json()
    assert short["history"] == long["history"]
    assert len(short["history"]) == 300
    assert short["observation"]["history"] == long["observation"]["history"][-10:]
    assert short["observation"]["latest"] == long["observation"]["latest"]
    assert short["observation"]["total_observations"] == 300
    assert short["observation"]["returned_observations"] == 10
