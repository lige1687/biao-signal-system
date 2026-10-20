"""净值对比取数路由测试（fetch 全量注入，不打网络）。

覆盖：窗口裁剪 / 单只失败收集不拖垮整批 / 代码校验与数量上限 /
缓存命中（同一进程内第二次取数不再触发抓取）。
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import portfolio as portfolio_routes
from lei_signal.portfolio import funddata
from lei_signal.portfolio.funddata import FundNavFull


def _nav_full(code: str, dates: list[str], unit: list[float]) -> FundNavFull:
    return FundNavFull(
        code=code, name=f"基金{code}", dates=dates,
        unit_nav=unit, acc_nav=[v * 1.01 for v in unit],
        day_pct=[0.5] * len(dates),
    )


@pytest.fixture()
def app(tmp_path, monkeypatch):
    a = FastAPI()
    a.state.analysis_service = None
    a.state.portfolio_db_path = str(tmp_path / "t.db")
    a.include_router(portfolio_routes.router)
    portfolio_routes._NAV_CACHE.clear()

    calls: list[str] = []

    def fake_fetch(code: str):
        calls.append(code)
        if code == "000000":
            raise RuntimeError("boom")
        if code == "999999":
            return None
        return _nav_full(
            code,
            dates=["2024-01-02", "2024-06-03", "2025-01-02", "2026-01-05", "2026-09-01"],
            unit=[1.0, 1.1, 0.9, 1.2, 1.3],
        )

    monkeypatch.setattr(portfolio_routes, "fetch_nav_full", fake_fetch)
    a.state.nav_fetch_calls = calls
    return a


def test_window_trim_and_series_shape(app):
    body = TestClient(app).get(
        "/api/portfolio/nav-series", params={"codes": "005827", "days": 800}
    ).json()
    assert body["days"] == 800
    assert len(body["items"]) == 1 and body["errors"] == []
    item = body["items"][0]
    # 800 天窗口起点约 2024-11 月 → 只剩 2025 起 3 个点，累计净值同步对齐
    assert item["dates"][0] == "2025-01-02"
    assert all(
        len(item[k]) == len(item["dates"])
        for k in ("unit_nav", "acc_nav", "day_pct")
    )
    assert item["acc_nav"][0] == pytest.approx(0.9 * 1.01)


def test_days_zero_keeps_full_history(app):
    item = TestClient(app).get(
        "/api/portfolio/nav-series", params={"codes": "005827", "days": 0}
    ).json()["items"][0]
    assert item["dates"][0] == "2024-01-02"


def test_single_failure_collected_not_fatal(app):
    body = TestClient(app).get(
        "/api/portfolio/nav-series", params={"codes": "005827,000000,999999", "days": 0}
    ).json()
    assert [i["code"] for i in body["items"]] == ["005827"]
    assert [e["code"] for e in body["errors"]] == ["000000", "999999"]
    assert "取数失败" in body["errors"][0]["reason_cn"]
    assert "没有返回" in body["errors"][1]["reason_cn"]


def test_bad_code_and_too_many_codes_rejected(app):
    client = TestClient(app)
    assert client.get(
        "/api/portfolio/nav-series", params={"codes": "AAPL", "days": 30}
    ).status_code == 400
    many = ",".join(f"00{i:04d}" for i in range(9))
    assert client.get(
        "/api/portfolio/nav-series", params={"codes": many, "days": 30}
    ).status_code == 400


def test_cache_second_call_skips_fetch(app):
    client = TestClient(app)
    client.get("/api/portfolio/nav-series", params={"codes": "005827", "days": 0})
    client.get("/api/portfolio/nav-series", params={"codes": "005827", "days": 30})
    assert app.state.nav_fetch_calls == ["005827"]


def test_parse_pingzhong_body():
    raw = (
        'var fS_name = "测试增长混合";\n'
        'var Data_netWorthTrend = '
        '[{"x":1536076800000,"y":1.0,"equityReturn":0,"unitMoney":""},'
        '{"x":1536163200000,"y":1.05,"equityReturn":5.0,"unitMoney":""},'
        '{"x":1536249600000,"y":"","equityReturn":"","unitMoney":""}];\n'
        'var Data_ACWorthTrend = [[1536076800000,1.0],[1536163200000,1.05],[1536249600000,1.05]];'
    )
    full = funddata.parse_pingzhong_body("000001", raw)
    assert full is not None
    assert full.name == "测试增长混合"
    assert full.dates == ["2018-09-05", "2018-09-06"]
    assert full.unit_nav == [1.0, 1.05]
    assert full.acc_nav == [1.0, 1.05]
    assert full.day_pct == [0.0, 5.0]
    # 缺关键变量的响应体 → None，不猜
    assert funddata.parse_pingzhong_body("000001", "var something_else = 1;") is None
