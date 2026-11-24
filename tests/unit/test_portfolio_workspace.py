"""Holding workspace identity and read/write boundary on disposable databases."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from lei_signal.api.portfolio_workspace import build_workspace, link_plan
from lei_signal.plans.store import create_plan
from lei_signal.portfolio.models import PortfolioGroup, PortfolioHolding
from lei_signal.portfolio.store import set_meta, upsert_group, upsert_holding
from lei_signal.storage.sqlite_store import connect


def _request(path) -> Request:
    app = FastAPI()
    app.state.portfolio_db_path = str(path)
    app.state.plans_db_path = str(path)
    app.state.watchlist_db_path = str(path)
    app.state.analysis_service = SimpleNamespace(_entries={})
    return Request({"type": "http", "app": app})


def _fixture_db(tmp_path):
    path = tmp_path / "workspace.db"
    conn = connect(path)
    upsert_group(conn, PortfolioGroup("g", "基金", "cn", 1, "观察"))
    set_meta(conn, "as_of", "2026-09-30")
    for hid, name, code in (
        ("etf", "红利低波ETF华泰柏瑞", "512890"),
        ("wrong_share", "红利低波ETF华泰柏瑞联接A", "512890"),
        ("index", "上证指数", "000001"),
        ("off_exchange", "红利低波联接C", "016139"),
    ):
        upsert_holding(conn, PortfolioHolding(
            hid, "g", name, code, 100.0, 1.0, as_of="2026-09-30"
        ))
    conn.execute(
        "INSERT INTO watchlist_items (symbol,display_name,market,note,sort_order,added_at) "
        "VALUES (?,?,?,?,?,?)",
        ("512890.SS", "红利低波ETF", "cn", None, 1, "2026-09-01"),
    )
    conn.execute(
        "INSERT INTO portfolio_holdings_nav "
        "(holding_id,code,snapshot_nav,snapshot_nav_date,implied_shares,cost_value,"
        "latest_nav,latest_nav_date,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("etf", "512890", 1.0, "2026-09-29", 100.0, 100.0,
         1.1, "2026-09-30", "2026-10-02T08:00:00+08:00"),
    )
    conn.commit()
    return path, conn


def _plan(conn, symbol="512890.SS", state="entered"):
    plan = create_plan(
        conn, symbol=symbol, module="A", direction="long",
        ruleset_version="1.3.0", reason="原定持仓理由",
        valid_until="2026-12-31", take_profit_plan_cn="到目标区复核",
        stop_plan_cn="原失效位跌破后复核",
    )
    conn.execute("UPDATE trade_plans SET state=? WHERE plan_id=?", (state, plan.plan_id))
    conn.commit()
    return plan.plan_id


def test_identity_gaps_nav_dates_and_read_is_read_only(tmp_path):
    path, conn = _fixture_db(tmp_path)
    try:
        plan_id = _plan(conn)
        before = set(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        request = _request(path)
        out = build_workspace(request)
        items = {x["holding_id"]: x for x in out["items"]}
        assert out["coverage"]["total"] == 4
        assert out["as_of"] == "2026-09-30"
        assert items["etf"]["symbol"] == "512890.SS"
        assert items["etf"]["nav"] == {
            "value": 1.1, "date": "2026-09-30",
            "updated_at": "2026-10-02T08:00:00+08:00",
        }
        assert items["etf"]["plan"] is None
        assert [p["plan_id"] for p in items["etf"]["plan_candidates"]] == [plan_id]
        assert items["etf"]["status"] == "incomplete"
        assert all(items[x]["symbol"] is None for x in ("wrong_share", "index", "off_exchange"))
        assert all(items[x]["status"] == "incomplete" for x in items)
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='portfolio_holding_plan_links'"
        ).fetchone()
        assert set(conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()) == before
    finally:
        conn.close()


def test_explicit_link_keeps_history_and_rejects_wrong_identity(tmp_path):
    path, conn = _fixture_db(tmp_path)
    try:
        plan_id = _plan(conn)
        bad_id = _plan(conn, "QQQ")
        request = _request(path)
        with pytest.raises(HTTPException) as bad:
            link_plan(request, "etf", bad_id)
        assert bad.value.status_code == 422
        with pytest.raises(HTTPException) as wrong_share:
            link_plan(request, "wrong_share", plan_id)
        assert wrong_share.value.status_code == 422
        with pytest.raises(HTTPException) as missing:
            link_plan(request, "missing", plan_id)
        assert missing.value.status_code == 404
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='portfolio_holding_plan_links'"
        ).fetchone()
        first = link_plan(request, "etf", plan_id)
        second = link_plan(request, "etf", plan_id)
        assert first == second
        assert conn.execute(
            "SELECT COUNT(*) FROM portfolio_holding_plan_link_history"
        ).fetchone()[0] == 1
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["plan"]["plan_id"] == plan_id
        assert item["plan"]["linked_at"] == first["linked_at"]
        assert item["status"] == "incomplete"  # missing technical evidence
        conn.execute(
            "UPDATE trade_plans SET symbol='QQQ' WHERE plan_id=?", (plan_id,)
        )
        conn.commit()
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["plan"] is None
        assert build_workspace(request)["coverage"]["with_plan"] == 0
    finally:
        conn.close()


def test_only_linked_plan_alert_can_require_action(tmp_path, monkeypatch):
    from lei_signal.api import portfolio_workspace as workspace
    from lei_signal.api import card_mapper
    from lei_signal.api.routes import symbols as symbol_routes

    path, conn = _fixture_db(tmp_path)
    try:
        plan_id = _plan(conn)
        request = _request(path)
        result = SimpleNamespace(cache_fallback_used=False)
        monkeypatch.setattr(workspace, "_cached_result", lambda *_: result)
        monkeypatch.setattr(
            symbol_routes, "_assessment_dto",
            lambda _: SimpleNamespace(model_dump=lambda **_: {"stage": "up"}),
        )
        monkeypatch.setattr(
            workspace, "context_from_result",
            lambda *_args, **_kwargs: SimpleNamespace(
                last_bar_date=workspace._expected_bar_date("512890.SS", workspace._now())
            ),
        )
        monkeypatch.setattr(card_mapper, "is_intraday_forming", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(
            workspace, "evaluate_plan",
            lambda *_: [SimpleNamespace(
                code="INVALIDATION_BREACHED", severity="block", rule_id="plan_discipline_guard",
                data_as_of="2026-09-30", actionable_from="2026-10-01",
                action_kind="EXIT", next_step_cn="按原失效位退出",
                caveat_cn="研究代理", evidence={"close": 1.0},
            )],
        )
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["status"] == "incomplete"
        assert item["technical"]["assessment"]["stage"] == "up"
        link_plan(request, "etf", plan_id)
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["status"] == "action_required"
        assert "按原失效位退出" in item["next_step_cn"]
        assert item["alerts"][0]["data_as_of"] == "2026-09-30"
        monkeypatch.setattr(card_mapper, "is_intraday_forming", lambda *_args, **_kwargs: True)
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["status"] == "waiting"
    finally:
        conn.close()


def test_real_assessment_and_context_are_usable(tmp_path, monkeypatch):
    from lei_signal.api import portfolio_workspace as workspace
    from lei_signal.api import card_mapper
    from lei_signal.api.services import AnalysisEntry
    from lei_signal.compose.pipeline import analyze_bars
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import validate_bars

    path, conn = _fixture_db(tmp_path)
    try:
        plan_id = _plan(conn)
        request = _request(path)
        link_plan(request, "etf", plan_id)
        dates = pd.bdate_range(end="2026-10-02", periods=90)
        bars = pd.DataFrame(
            [{
                "open": 1 + i * 0.002, "high": 1.01 + i * 0.002,
                "low": 0.99 + i * 0.002, "close": 1 + i * 0.002,
                "volume": 1_000_000,
            } for i in range(len(dates))], index=dates
        )
        frame, report = validate_bars(
            bars, symbol="512890.SS", provider="fixture", adjusted=True
        )
        price_data = PriceData(
            symbol="512890.SS", display_name="红利低波ETF", bars=frame,
            report=report, info=resolve_symbol("512890.SS")
        )
        result = analyze_bars("512890.SS", frame, price_data=price_data)
        fetched_at = datetime(2026, 10, 2, 16, tzinfo=ZoneInfo("Asia/Shanghai"))
        monkeypatch.setattr(workspace, "_now", lambda: fetched_at)
        request.app.state.analysis_service._entries["512890.SS"] = AnalysisEntry(
            result=result, error=None, fetched_at=fetched_at
        )
        monkeypatch.setattr(card_mapper, "is_intraday_forming", lambda *_args, **_kwargs: False)
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["technical"] is not None
        assert item["technical"]["assessment"]["stage"]
        assert item["technical"]["meta"]["last_bar_date"] == "2026-10-02"
        assert item["status"] in {"action_required", "no_trigger"}
        conn.execute(
            "UPDATE portfolio_holdings_nav SET code='159999' WHERE holding_id='etf'"
        )
        conn.commit()
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["nav"] is None
        assert "缺少基金净值" in item["gaps"]
        assert item["status"] in {"action_required", "no_trigger"}
        old_bars = bars.copy()
        old_bars.index = pd.bdate_range(end="2026-08-03", periods=len(old_bars))
        old_frame, old_report = validate_bars(
            old_bars, symbol="512890.SS", provider="fixture", adjusted=True
        )
        old_data = PriceData(
            symbol="512890.SS", display_name="红利低波ETF", bars=old_frame,
            report=old_report, info=resolve_symbol("512890.SS")
        )
        old_result = analyze_bars("512890.SS", old_frame, price_data=old_data)
        request.app.state.analysis_service._entries["512890.SS"] = AnalysisEntry(
            result=old_result, error=None, fetched_at=fetched_at
        )
        old_item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert old_item["status"] == "incomplete"
        assert "技术行情日期早于最近应有的收盘日" in old_item["gaps"]
    finally:
        conn.close()


def test_same_day_bar_waits_until_post_close_fetch(monkeypatch):
    from lei_signal.api import card_mapper
    from lei_signal.api.portfolio_workspace import _forming

    monkeypatch.setattr(card_mapper, "is_intraday_forming", lambda *_args, **_kwargs: True)
    tz = ZoneInfo("Asia/Shanghai")
    before_close = datetime(2026, 9, 29, 14, 30, tzinfo=tz)
    after_close = datetime(2026, 9, 29, 16, 0, tzinfo=tz)
    result = SimpleNamespace()
    early = SimpleNamespace(fetched_at=before_close)
    final = SimpleNamespace(fetched_at=after_close)
    assert _forming(result, "512890.SS", early, before_close)
    assert _forming(result, "512890.SS", early, after_close)
    assert not _forming(result, "512890.SS", final, after_close)


@pytest.mark.parametrize("bar_date", ["2026-10-01", "not-a-date", "2026-09-99"])
def test_future_or_invalid_bar_date_never_evaluates_plan(tmp_path, monkeypatch, bar_date):
    from lei_signal.api import portfolio_workspace as workspace
    from lei_signal.api.routes import symbols as symbol_routes

    path, conn = _fixture_db(tmp_path)
    try:
        request = _request(path)
        link_plan(request, "etf", _plan(conn))
        monkeypatch.setattr(workspace, "_now", lambda: datetime(2026, 9, 30, 16, tzinfo=ZoneInfo("Asia/Shanghai")))
        monkeypatch.setattr(workspace, "_cached_result", lambda *_: SimpleNamespace(cache_fallback_used=False))
        monkeypatch.setattr(symbol_routes, "_assessment_dto", lambda _: SimpleNamespace(model_dump=lambda **_: {"stage": "up"}))
        monkeypatch.setattr(workspace, "context_from_result", lambda *_a, **_kw: SimpleNamespace(last_bar_date=bar_date))
        monkeypatch.setattr(workspace, "_forming", lambda *_: False)
        monkeypatch.setattr(workspace, "evaluate_plan", lambda *_: pytest.fail("Invalid/future data reached the plan evaluator"))
        item = next(x for x in build_workspace(request)["items"] if x["holding_id"] == "etf")
        assert item["status"] == "incomplete"
        assert any("日期" in gap for gap in item["gaps"])
        assert item["alerts"] == []
    finally:
        conn.close()
