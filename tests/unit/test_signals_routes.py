"""/api/signals/today 路由 + 红点 today_signal_total 门禁。"""
from __future__ import annotations

from contextlib import closing
from types import SimpleNamespace

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import today_date, upsert_scan_results
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    upsert_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect


def _app(tmp_path):
    app = create_app(analysis_service=SimpleNamespace())  # GET 不触分析服务
    db = str(tmp_path / "lab.db")
    app.state.plans_db_path = db
    return app, db


def _write_today(db: str, *, sell_rows=(), unavailable=(), as_of="close") -> None:
    with closing(connect(db)) as conn:
        upsert_scan_results(conn, today_date(), [
            ScanItemDTO(symbol="600519.SS", verdict="actionable", verdict_cn="条件已成立"),
            ScanItemDTO(symbol="000001.SZ", verdict="waiting", verdict_cn="等待条件成立"),
        ])
        upsert_signal_alerts(conn, today_date(), as_of, [
            *sell_rows, *unavailable,
        ])


def _sell(symbol="600519.SS", tier="hard", kind="exit_proxy") -> SignalAlertRow:
    return SignalAlertRow(
        scan_date=today_date(), symbol=symbol, display_name=symbol,
        side=SIDE_SELL, tier=tier, kind=kind, kind_cn="退出代理",
        title="收盘同破 EMA20 与 20 日抵扣价", reason_cn="x（研究代理）",
        is_new=True, key_prices={"ema20": 10.5}, provenance="research_proxy",
        available_date=today_date(),
    )


def test_today_signals_merges_buy_and_sell(tmp_path) -> None:
    app, db = _app(tmp_path)
    _write_today(db, sell_rows=[_sell(), _sell("300750.SZ", "warn", "key_wave_black"),
                                _sell("000858.SZ", "soft", "color_black")],
                 unavailable=[SignalAlertRow(
                     scan_date=today_date(), symbol="bad.SS", display_name="bad.SS",
                     side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
                     title="数据不可用", error="DATA_UNAVAILABLE: x",
                 )])
    with TestClient(app) as client:
        resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of"] == "close"
    assert len(body["actionable"]) == 1 and len(body["waiting"]) == 1
    assert (
        len(body["sell_hard"]) == 1
        and len(body["sell_warn"]) == 1
        and len(body["sell_soft"]) == 1
    )
    assert body["sell_hard"][0]["provenance"] == "research_proxy"
    assert len(body["unavailable"]) == 1 and "DATA_UNAVAILABLE" in body["unavailable"][0]["error"]


def test_today_signals_empty_when_no_scan(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of"] is None
    assert body["actionable"] == [] and body["sell_hard"] == []


def test_refresh_rejects_bad_as_of(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.post("/api/signals/today/refresh?as_of=whatever")
    assert resp.status_code == 422


def test_plans_summary_includes_signal_total(tmp_path) -> None:
    app, db = _app(tmp_path)
    _write_today(db, sell_rows=[_sell(), _sell("300750.SZ", "soft", "color_black")])
    with TestClient(app) as client:
        resp = client.get("/api/plans/summary")
    assert resp.status_code == 200
    body = resp.json()
    # 买点 2 (actionable+waiting) + 卖点 hard 1（soft 不计）= 3
    assert body["today_signal_total"] == 3
    assert body["today_opportunities"] == 2
