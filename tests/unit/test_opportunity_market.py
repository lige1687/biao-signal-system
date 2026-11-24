"""Exact holding identity, bounded NAV reuse and honest missing-history state."""

from __future__ import annotations

import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api import opportunity_market as market
from lei_signal.api.routes import opportunity_reviews

_ID = "5045587e5cff"


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    market._CACHE.clear()
    market._IN_FLIGHT.clear()
    monkeypatch.setattr(
        market, "_now", lambda: datetime(2026, 10, 15, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    )
    yield
    market._CACHE.clear()
    market._IN_FLIGHT.clear()


def _holding():
    # Public fields copied from /api/portfolio/workspace for 001513 on 2026-10-15.
    return {
        "holding_id": _ID,
        "name": "易方达信息产业混合A",
        "code": "001513",
        "nav": {"date": "2026-10-14", "value": 6.723},
        "disclosure": {
            "fund_code": "001513",
            "fund_name": "易方达信息产业混合A",
            "report_date": "2026-06-30",
            "published_at": "2026-08-31",
            "coverage_pct": 43.49,
            "source_recheck_required": True,
        },
        "industry_reference": {
            "references": [
                {
                    "symbol": "515880.SS",
                    "name": "通信ETF国泰",
                    "technical": {"as_of": "2026-10-15"},
                },
                {
                    "symbol": "512480.SS",
                    "name": "半导体ETF国联安",
                    "technical": {"as_of": "2026-10-15"},
                },
            ]
        },
    }


def _client(monkeypatch, items=None):
    monkeypatch.setattr(
        market,
        "build_workspace",
        lambda request: {"items": [_holding()] if items is None else items},
    )
    app = FastAPI()
    app.include_router(opportunity_reviews.router)
    return TestClient(app)


def test_exact_identity_and_one_fund_only(monkeypatch):
    calls = []
    monkeypatch.setattr(
        market,
        "_fetch_nav_180",
        lambda code: (
            calls.append(code)
            or (
                [
                    SimpleNamespace(date="2026-10-14", unit_nav=6.723),
                    SimpleNamespace(date="2026-10-13", unit_nav=6.7),
                ],
                None,
            )
        ),
    )
    client = _client(
        monkeypatch, [_holding(), {**_holding(), "holding_id": "abcdef123456", "code": "009999"}]
    )
    assert client.get("/api/opportunity-reviews/market/holdings/not-an-id").status_code == 422
    assert client.get("/api/opportunity-reviews/market/holdings/aaaaaaaaaaaa").status_code == 404
    assert calls == []
    response = client.get(f"/api/opportunity-reviews/market/holdings/{_ID}")
    assert response.status_code == 200
    body = response.json()
    assert calls == ["001513"]
    assert body["subject_key"] == f"holding:{_ID}"
    assert body["nav"]["status"] == "available"
    assert body["nav"]["latest"] == {"date": "2026-10-14", "value": 6.723}
    assert body["references"] == [
        {
            "symbol": "515880.SS",
            "name": "通信ETF国泰",
            "relation": "已披露持仓业务的行业ETF参照，不能代替本基金买卖信号",
            "as_of": "2026-10-15",
        },
        {
            "symbol": "512480.SS",
            "name": "半导体ETF国联安",
            "relation": "已披露持仓业务的行业ETF参照，不能代替本基金买卖信号",
            "as_of": "2026-10-15",
        },
    ]
    assert body["disclosure"] == {
        "report_date": "2026-06-30",
        "published_at": "2026-08-31",
        "coverage_pct": 43.49,
    }


def test_invalid_duplicate_and_future_points_are_removed(monkeypatch):
    monkeypatch.setattr(
        market,
        "_fetch_nav_180",
        lambda code: (
            [
                SimpleNamespace(date="2026-10-16", unit_nav=9),
                SimpleNamespace(date="2026-10-14", unit_nav=6.723),
                SimpleNamespace(date="2026-10-14", unit_nav=99),
                SimpleNamespace(date="2026-10-13", unit_nav=6.7),
                SimpleNamespace(date="2026-10-12", unit_nav=float("nan")),
                SimpleNamespace(date="2026-10-11", unit_nav=-1),
                SimpleNamespace(date="2026-10-10x", unit_nav=6),
            ],
            None,
        ),
    )
    body = _client(monkeypatch).get(f"/api/opportunity-reviews/market/holdings/{_ID}").json()
    assert body["nav"]["points"] == [
        {"date": "2026-10-13", "value": 6.7},
        {"date": "2026-10-14", "value": 6.723},
    ]


def test_failure_cached_until_explicit_refresh_and_single_nav_is_stale(monkeypatch):
    calls = []

    def failing(code):
        calls.append(code)
        raise TimeoutError("private provider details")

    monkeypatch.setattr(market, "_fetch_nav_180", failing)
    client = _client(monkeypatch)
    url = f"/api/opportunity-reviews/market/holdings/{_ID}"
    first = client.get(url).json()["nav"]
    second = client.get(url).json()["nav"]
    assert calls == ["001513"]
    assert first == second
    assert first["status"] == "stale"
    assert first["points"] == [{"date": "2026-10-14", "value": 6.723}]
    assert first["error"] == "净值来源读取失败：TimeoutError"
    assert first["source_ref"].endswith("fundCode=001513")
    client.get(url + "?refresh=true")
    assert calls == ["001513", "001513"]


def test_failed_refresh_preserves_prior_series_with_error(monkeypatch):
    calls = [0]

    def fetch(code):
        calls[0] += 1
        if calls[0] == 2:
            raise TimeoutError
        return (
            [
                SimpleNamespace(date="2026-10-14", unit_nav=6.723),
                SimpleNamespace(date="2026-10-13", unit_nav=6.7),
            ],
            None,
        )

    monkeypatch.setattr(market, "_fetch_nav_180", fetch)
    client = _client(monkeypatch)
    url = f"/api/opportunity-reviews/market/holdings/{_ID}"
    assert client.get(url).json()["nav"]["status"] == "available"
    nav = client.get(url + "?refresh=true").json()["nav"]
    assert nav["status"] == "stale"
    assert len(nav["points"]) == 2
    assert nav["error"] == "净值来源读取失败：TimeoutError"


def test_no_verified_code_stops_before_provider(monkeypatch):
    item = {**_holding(), "code": ""}
    client = _client(monkeypatch, [item])
    monkeypatch.setattr(
        market, "_fetch_nav_180", lambda *args, **kwargs: pytest.fail("unexpected fetch")
    )
    assert client.get(f"/api/opportunity-reviews/market/holdings/{_ID}").status_code == 422


def test_provider_page_cap_is_completed_without_other_funds(monkeypatch):
    start = date(2026, 10, 15)
    monkeypatch.setattr(market.time, "sleep", lambda seconds: None)
    pages = []

    def fetch_page(code, page, timeout):
        assert code == "001513"
        pages.append(page)
        return [
            SimpleNamespace(date=(start - timedelta(days=i)).isoformat(), unit_nav=6.0)
            for i in range((page - 1) * 20 + 1, page * 20 + 1)
        ]

    monkeypatch.setattr(market, "_fetch_page", fetch_page)
    points, error = market._fetch_nav_180("001513")
    assert len(points) == 180
    assert error is None
    assert pages == list(range(1, 10))


def test_first_page_uses_the_same_https_source_and_nav_fields(monkeypatch):
    def open_page(request, timeout):
        assert request.full_url == (
            "https://api.fund.eastmoney.com/f10/lsjz?fundCode=001513&pageIndex=1&pageSize=20"
        )
        assert timeout == 20
        return io.BytesIO(
            json.dumps(
                {
                    "ErrCode": 0,
                    "Data": {
                        "LSJZList": [
                            {"FSRQ": "2026-10-14", "DWJZ": "6.723"},
                        ]
                    },
                }
            ).encode()
        )

    monkeypatch.setattr(market.urllib.request, "urlopen", open_page)
    assert market._fetch_page("001513", 1, 20) == [market.NavPoint("2026-10-14", 6.723)]


def test_provider_history_older_than_recorded_nav_is_stale(monkeypatch):
    monkeypatch.setattr(
        market,
        "_fetch_nav_180",
        lambda code: (
            [
                SimpleNamespace(date="2026-10-13", unit_nav=6.7),
                SimpleNamespace(date="2026-10-12", unit_nav=6.6),
            ],
            None,
        ),
    )
    nav = _client(monkeypatch).get(f"/api/opportunity-reviews/market/holdings/{_ID}").json()["nav"]
    assert nav["status"] == "stale"
    assert nav["latest"] == {"date": "2026-10-13", "value": 6.7}
    assert "早于持仓台账已记录的2026-10-14" in nav["error"]


def test_same_code_concurrent_refresh_does_not_duplicate_fetch(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    calls = []

    def fetch(code):
        calls.append(code)
        entered.set()
        assert release.wait(timeout=2)
        return (
            [
                SimpleNamespace(date="2026-10-14", unit_nav=6.723),
                SimpleNamespace(date="2026-10-13", unit_nav=6.7),
            ],
            None,
        )

    monkeypatch.setattr(market, "_fetch_nav_180", fetch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(market._fetch, "001513", market._now(), refresh=True)
        assert entered.wait(timeout=2)
        busy = market._fetch("001513", market._now(), refresh=True)
        release.set()
        ready = first.result(timeout=2)
    assert calls == ["001513"]
    assert busy["error"] == "同一基金净值正在读取，请稍后重试"
    assert ready["error"] is None
