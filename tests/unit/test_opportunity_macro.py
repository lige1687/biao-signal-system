"""Local macro context keeps source dates and avoids duplicate per-product reads."""

from __future__ import annotations

import importlib.util
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

MODULE = Path(__file__).resolve().parents[2] / "src/lei_signal/api/opportunity_macro.py"
spec = importlib.util.spec_from_file_location("opportunity_macro_under_test", MODULE)
macro = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(macro)


def _request(tmp_path, service):
    state = SimpleNamespace(plans_db_path=str(tmp_path / "plans.db"), fundamentals_service=service)
    return SimpleNamespace(app=SimpleNamespace(state=state))


def _item(day: str, *, value=2.5, source_access="public_web", published_at=None):
    return {
        "metric_id": "real_yield_10y",
        "label": "美国10年实际利率",
        "market": "us",
        "value": value,
        "unit": "%",
        "observation_date": day,
        "published_at": published_at,
        "source_name": "FRED / 美国财政部",
        "source_url": "https://fred.stlouisfed.org/series/DFII10",
        "source_access": source_access,
        "quality_status": "time_unverified",
        "reading": "观察实际利率水平。",
        "limitations": ["非交易信号"],
    }


class Service:
    def __init__(self, payload, *, economy=None, treasury=None):
        self.payload = payload
        self.economy = economy or {"items": [], "series": {}, "errors": []}
        self.treasury = treasury or {"cn": {}, "us": {}}
        self.calls = []
        self._cache = self

    def observations(self, market):
        self.calls.append(f"observations:{market}")
        return self.payload

    def macro_history(self, *, page_size):
        self.calls.append(f"macro_history:{page_size}")
        return self.economy

    def us_macro(self):
        self.calls.append("us_macro")
        return self.economy

    def get_or_load(self, key, ttl, loader):
        self.calls.append(f"cache:{key}")
        return self.treasury, True


def test_prepare_once_per_market_and_read_never_fetches(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    observation = {
        **_item((today - timedelta(days=1)).isoformat()),
        "fetched_at": "2026-10-14T12:00:00+00:00",
    }
    service = Service({"items": [observation], "errors": []})
    request = _request(tmp_path, service)
    first = macro.prepare_macro(request, ["US", "us", "HK", "unknown"])
    second = macro.prepare_macro(request, ["us"])
    assert sorted(service.calls) == ["cache:treasury", "observations:us", "us_macro"]
    assert first["HK"]["status"] == "unsupported"
    assert first["unknown"]["rows"] == []
    assert first["us"] == second["us"]
    row = first["us"]["rows"][0]
    assert row["date"] == row["report_date"] == (today - timedelta(days=1)).isoformat()
    assert row["published_at"] is None
    assert row["fetched_at"] == "2026-10-14T12:00:00+00:00"
    assert row["quality_status"] == "time_unverified"
    assert row["checked_at"] and row["source_ref"].startswith("https://")
    assert row["scope"] == "narrative" and row["narrative_kind"] == "macro"
    assert row["relevance"] == "market_context" and row["public"] is True
    assert any("不代表" in x for x in row["limitations"])
    assert any("首次公开时间未核实" in x for x in row["limitations"])
    assert macro.read_macro(request, "us", datetime.now(UTC))["rows"] == [row]
    assert len(service.calls) == 3


def test_rejects_future_missing_private_and_invalid_sources(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    items = [
        _item((today + timedelta(days=1)).isoformat()),
        _item(today.isoformat(), value=None),
        _item(today.isoformat(), source_access="local_source_claim_unverified"),
        {**_item(today.isoformat()), "source_url": "http://unverified.test"},
    ]
    request = _request(tmp_path, Service({"items": items, "errors": ["source failed"]}))
    result = macro.prepare_macro(request, ["us"])["us"]
    assert result["status"] == "unavailable" and result["rows"] == []
    assert "source failed" in result["error"]


def test_failed_source_is_bounded_and_reused_for_day(tmp_path, monkeypatch):
    service = Service({"items": []})
    request = _request(tmp_path, service)
    monkeypatch.setattr(macro, "_fetch_bounded", lambda *_: ({}, ["timeout"]))
    assert macro.prepare_macro(request, ["cn"])["cn"]["status"] == "unavailable"
    assert macro.prepare_macro(request, ["cn"])["cn"]["error"] == "timeout"
    assert service.calls == []


def test_old_daily_snapshot_not_read_as_today(tmp_path):
    service = Service({"items": [_item("2026-01-01")], "errors": []})
    request = _request(tmp_path, service)
    result = macro.prepare_macro(request, ["us"])["us"]
    assert result["rows"] == []
    assert result["stale_rows"][0]["date"] == "2026-01-01"
    future = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(days=1)
    assert macro.read_macro(request, "us", future)["status"] == "missing"
    assert len(service.calls) == 3


def test_cn_economy_and_treasury_from_existing_services(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    month = (today - timedelta(days=25)).isoformat()
    economy = {
        "series": {
            key: {"dates": [month], "values": [value]}
            for key, value in (("pmi", 49.7), ("cpi", 0.3), ("ppi", -1.2))
        },
        "errors": [],
    }
    treasury = {
        "cn": {"cn_10y": 1.9},
        "us": {"us_10y": 4.2},
        "as_of_cn": (today - timedelta(days=1)).isoformat(),
    }
    service = Service({"items": [], "errors": []}, economy=economy, treasury=treasury)
    result = macro.prepare_macro(_request(tmp_path, service), ["CN"])["cn"]
    assert result["status"] == "ready"
    assert {row["metric_id"] for row in result["rows"]} == {"pmi", "cpi", "ppi", "cn_10y"}
    assert all(row["published_at"] is None and row["fetched_at"] is None for row in result["rows"])
    assert all(row["quality_status"] == "time_unverified" for row in result["rows"])
    assert sorted(service.calls) == ["cache:treasury", "macro_history:60", "observations:cn"]


def test_us_economy_and_inflation_with_partial_source_failure(tmp_path):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    economy = {
        "items": [
            {"key": "wei", "date": (today - timedelta(days=5)).isoformat(), "value": 1.1},
            {"key": "cpiaucsl_yoy", "date": (today - timedelta(days=35)).isoformat(), "value": 2.4},
        ],
        "errors": ["美国宏观 耐用品订单: 限流"],
    }
    service = Service({"items": [], "errors": []}, economy=economy)
    result = macro.prepare_macro(_request(tmp_path, service), ["US"])["us"]
    assert result["status"] == "ready"
    assert {row["metric_id"] for row in result["rows"]} == {"wei", "cpiaucsl_yoy"}
    assert "限流" in result["error"]


def test_interrupted_running_lease_does_not_trigger_retry(tmp_path):
    request = _request(tmp_path, Service({"items": []}))
    with sqlite3.connect(request.app.state.plans_db_path) as conn:
        macro._ensure_table(conn)
        conn.execute(
            "INSERT INTO opportunity_macro_observations "
            "(market,checked_on,status,rows_json,started_at) VALUES (?,?, 'running', '[]', ?)",
            (
                "cn",
                datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
                "2026-01-01T00:00:00+00:00",
            ),
        )
    assert macro.read_macro(request, "cn", datetime.now(UTC))["status"] == "unavailable"
    assert "中断" in macro.prepare_macro(request, ["cn"])["cn"]["error"]
    assert request.app.state.fundamentals_service.calls == []


def test_total_fetch_deadline_preserves_completed_sources_and_late_worker_cannot_write(
    tmp_path, monkeypatch
):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()

    class SlowService(Service):
        def us_macro(self):
            time.sleep(0.15)
            return self.economy

        def get_or_load(self, key, ttl, loader):
            time.sleep(0.15)
            return self.treasury, True

    service = SlowService({"items": [_item(today.isoformat())], "errors": []})
    request = _request(tmp_path, service)
    monkeypatch.setattr(macro, "_FETCH_WAIT_SECONDS", 0.02)
    start = time.monotonic()
    result = macro.prepare_macro(request, ["us"])["us"]
    assert time.monotonic() - start < 0.12
    assert result["status"] == "ready" and len(result["rows"]) == 1
    assert "超过" in result["error"]
    time.sleep(0.18)
    assert macro.read_macro(request, "us", datetime.now(UTC)) == result


def test_cn_macro_read_preserves_shared_history_cache_scope(tmp_path):
    service = Service({"items": [], "errors": []})
    macro.prepare_macro(_request(tmp_path, service), ["cn"])
    assert "macro_history:60" in service.calls
    assert "macro_history:2" not in service.calls


def test_us_macro_preserves_transformed_series_label_without_item_label():
    now = datetime.now(UTC)
    day = now.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat()
    # The production service puts the transformation label in series, not items.
    payload = {
        "items": [{"key": "icwa", "name_cn": "初请失业金", "date": day, "value": 198500}],
        "series": {"icwa": {"label": "初请失业金（4 周均值）"}},
    }
    row = macro._economy_rows(payload, "us", now)[0]
    assert "初请失业金（4 周均值）" in row["text"]
    assert "198500人" in row["text"]
    payload.pop("series")
    assert "4 周均值" in macro._economy_rows(payload, "us", now)[0]["text"]
