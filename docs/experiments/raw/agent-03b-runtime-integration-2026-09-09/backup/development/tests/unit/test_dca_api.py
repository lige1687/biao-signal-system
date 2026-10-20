"""定投模块接口测试：预设/计划 CRUD → 每周清单 → 状态/触发看板（合成行情注入）。"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app


def _crash_bars() -> pd.DataFrame:
    """前 200 根 100 → 后 100 根跌到 70（距年线 −30%：深超跌 + 底部区域形态）。"""
    n = 300
    idx = pd.bdate_range("2025-01-01", periods=n)
    close = np.concatenate([np.full(200, 100.0), np.linspace(100.0, 70.0, 100)])
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    return pd.DataFrame({"open": open_, "close": close}, index=idx)


def _flat_bars() -> pd.DataFrame:
    n = 300
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame({"open": np.full(n, 100.0), "close": np.full(n, 100.0)},
                        index=idx)


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    ev = tmp_path / "evidence.json"
    ev.write_text(json.dumps({
        "version": "test",
        "state_expectations": {
            "deep20": {"label": "深超跌", "horizon_stats": {"6m": "中位+12.8%"},
                       "source": "test-src"},
            "bottom_zone": {"label": "底部区域", "horizon_stats": {"12m": "中位+4.6%"},
                            "source": "test-src"},
            "tier_low": {"label": "惨档", "horizon_stats": {"12m": "中位+2.0%"},
                         "source": "test-src"},
        },
        "ambush_template": {"entry": "底部区域或惨档触发", "source": "test-src"},
    }, ensure_ascii=False), encoding="utf-8")
    app = create_app()
    app.state.dca_db_path = str(tmp_path / "dca_test.db")
    app.state.dca_evidence_path = ev
    app.state.dca_breadth_override = {"cn": 26.0, "us": 61.0}

    def loader(symbol: str):
        return _crash_bars() if symbol == "000300" else _flat_bars()

    app.state.dca_data_loader = loader
    return TestClient(app)


def test_plans_list_contains_presets(client: TestClient):
    r = client.get("/api/dca/plans")
    assert r.status_code == 200
    plans = {p["plan_id"]: p for p in r.json()["plans"]}
    assert "preset_standard" in plans and "preset_aggressive" in plans
    std = plans["preset_standard"]
    assert [l["code"] for l in std["legs"]] == ["510300", "159915", "518880",
                                                "513100"]
    assert std["rebalance"] == "quarterly"


def test_preset_weekly_list(client: TestClient):
    r = client.get("/api/dca/plans/preset_standard/weekly",
                   params={"base_amount": 2000})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 4
    assert all(i["amount"] == 500.0 for i in body["items"])
    assert "平投" in body["note"]
    assert isinstance(body["rebalance_hint"]["due"], bool)


def test_plan_crud_and_validation(client: TestClient):
    payload = {
        "name": "我的定投",
        "legs": [
            {"code": "510300", "name": "沪深300ETF"},
            {"code": "518880", "name": "黄金ETF"},
        ],
    }
    r = client.post("/api/dca/plans", json=payload)
    assert r.status_code == 201
    plan_id = r.json()["plan_id"]
    listed = {p["plan_id"] for p in client.get("/api/dca/plans").json()["plans"]}
    assert plan_id in listed
    weekly = client.get(f"/api/dca/plans/{plan_id}/weekly",
                        params={"base_amount": 100}).json()
    assert all(i["amount"] == 50.0 for i in weekly["items"])
    # 非法参数
    bad = dict(payload, frequency="daily")
    assert client.post("/api/dca/plans", json=bad).status_code == 400
    # 删除：预设只读、用户计划可删
    assert client.delete("/api/dca/plans/preset_standard").status_code == 400
    assert client.delete(f"/api/dca/plans/{plan_id}").status_code == 200
    assert client.get(f"/api/dca/plans/{plan_id}/weekly").status_code == 404


def test_state_board_with_synthetic_crash(client: TestClient):
    r = client.get("/api/dca/state", params={"symbols": "000300,^IXIC"})
    assert r.status_code == 200
    states = {s["symbol"]: s for s in r.json()["states"]}
    cn = states["000300"]
    assert cn["deep20"] is True          # 距年线 −30% ≤ −20%
    assert cn["bottom_zone"] is True     # 惨档(26<43.3) × 回撤≤−15% × 年线下
    assert cn["expectation"]["label"] == "深超跌"
    us = states["^IXIC"]
    assert us["deep20"] is False and us["tier"] == "high"  # b200_us=61>56.7
    assert client.get("/api/dca/state",
                      params={"symbols": "BOGUS"}).status_code == 400


def test_triggers_board(client: TestClient):
    r = client.get("/api/dca/triggers")
    assert r.status_code == 200
    body = r.json()
    assert "000300" in body["deep20_triggered"]
    assert body["template"]["entry"] == "底部区域或惨档触发"
    assert "门控判负" in body["note"]


def test_evidence_passthrough(client: TestClient):
    r = client.get("/api/dca/evidence")
    assert r.status_code == 200
    assert r.json()["version"] == "test"
