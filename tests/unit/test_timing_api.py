"""timing_backtest API 路由测试（TestClient + tmp 缓存/运行目录）。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import lei_signal.timing_backtest.service as timing_service
from lei_signal.api.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    idx = pd.bdate_range("2022-01-03", periods=600)
    rng = np.random.default_rng(11)
    close = pd.Series(3000 * np.exp(rng.normal(0.0002, 0.012, 600).cumsum()), index=idx)
    pd.DataFrame({"open": close * 0.999, "close": close}).to_parquet(tmp_path / "000300.parquet")
    b = pd.Series(np.clip(50 + rng.normal(0, 8, 600).cumsum(), 1, 99), index=idx)
    pd.DataFrame({"b20": b, "b50": b, "b200": b}).to_parquet(tmp_path / "breadth_cn_all.parquet")
    monkeypatch.setattr(timing_service, "TIMING_CACHE_DIR", tmp_path)
    monkeypatch.setattr(timing_service, "RUNS_DIR", tmp_path / "runs")
    return TestClient(create_app())


@pytest.fixture()
def empty_client(tmp_path, monkeypatch):
    monkeypatch.setattr(timing_service, "TIMING_CACHE_DIR", tmp_path)
    monkeypatch.setattr(timing_service, "RUNS_DIR", tmp_path / "runs")
    return TestClient(create_app())


def test_options(client):
    r = client.get("/api/timing-backtest/options")
    assert r.status_code == 200
    body = r.json()
    assert len(body["disclaimers"]) >= 3
    assert len(body["instruments"]) >= 11
    assert {p["key"] for p in body["presets"]} >= {"cn_b200_ladder5", "us_b200_ladder5"}


def test_run_sync_roundtrip(client):
    r = client.post("/api/timing-backtest/runs", json={"symbol": "000300"})
    assert r.status_code == 200
    body = r.json()
    assert body["metrics"]["strategy_cagr"] is not None
    assert len(body["daily"]["date"]) > 500
    assert body["symbol"] == "000300"

    r2 = client.get("/api/timing-backtest/runs")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_run_unknown_symbol_400(client):
    r = client.post("/api/timing-backtest/runs", json={"symbol": "NOPE"})
    assert r.status_code == 400


def test_run_data_unavailable_409(empty_client):
    r = empty_client.post("/api/timing-backtest/runs", json={"symbol": "^GSPC"})
    assert r.status_code == 409
    assert "DATA_UNAVAILABLE" in r.json()["detail"]


def test_run_detail_404_and_roundtrip(client):
    r = client.post("/api/timing-backtest/runs", json={"symbol": "000300"})
    run_id = r.json()["run_id"]
    detail = client.get(f"/api/timing-backtest/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["daily"]["equity"]
    assert client.get("/api/timing-backtest/runs/nope").status_code == 404


def test_signals_endpoint(client):
    r = client.get("/api/timing-backtest/signals")
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 5
    ok = [s for s in body if "error" not in s]
    for s in ok:
        assert {"label", "as_of", "breadth_now", "weight_now", "trigger"} <= set(s.keys())
