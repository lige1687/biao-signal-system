"""机会雷达: migration 015 + store 模块 + today 端点 + plansSummary 扩展.

核心验证:
- daily_opportunity_scan 表建表 + 索引 (migration 015)
- upsert 整体重写语义 (二次写入删旧行)
- count_opportunities 只数 actionable+waiting (blocked 不计)
- GET /api/opportunities/today 读库分组, 空库返回 scanned=0
- POST /api/opportunities/today/refresh 重扫落库
- GET /api/plans/summary 含 today_opportunities 字段
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import (
    count_opportunities,
    has_scan,
    list_scan,
    today_date,
    upsert_scan_results,
)
from lei_signal.api.routes.opportunities import _group_today
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.storage.sqlite_store import connect

# ---- ScanItemDTO 工厂 ----


def _item(symbol: str, verdict: str, **kw) -> ScanItemDTO:
    cn = {
        "actionable": "条件已成立",
        "blocked": "环境阻断",
        "waiting": "等待条件成立",
        "none": "当前无机会",
    }[verdict]
    return ScanItemDTO(
        symbol=symbol,
        display_name=kw.get("display_name", symbol),
        verdict=verdict,
        verdict_cn=cn,
        best_scenario_cn=kw.get("best_scenario_cn"),
        best_state=kw.get("best_state"),
        reward_risk_ratio=kw.get("reward_risk_ratio"),
        reward_risk_computable=kw.get("reward_risk_computable", False),
        blocking_reasons=kw.get("blocking_reasons", []),
        missing_summary_cn=kw.get("missing_summary_cn", ""),
        has_active_plan=kw.get("has_active_plan", False),
        error=kw.get("error"),
    )


# ---- migration + store 模块 ----


def test_migration_015_creates_table(tmp_path) -> None:  # noqa: ANN001
    """connect 自动跑 migration, 表 + 索引存在。"""
    db = str(tmp_path / "opp.db")
    conn = connect(db)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "daily_opportunity_scan" in tables

    indexes = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
    }
    assert "idx_daily_scan_date_verdict" in indexes
    conn.close()


def test_upsert_and_list_roundtrip(tmp_path) -> None:  # noqa: ANN001
    """写入 -> 读回, verdict 优先级排序 (actionable -> waiting -> blocked)。"""
    db = str(tmp_path / "opp.db")
    conn = connect(db)
    scan_date = "2026-08-13"
    items = [
        _item("AAA.SS", "blocked"),
        _item("BBB.SS", "actionable", reward_risk_ratio=3.0),
        _item("CCC.SS", "waiting"),
        _item("DDD.SS", "actionable", reward_risk_ratio=5.0),
    ]
    n = upsert_scan_results(conn, scan_date, items)
    conn.commit()
    assert n == 4

    rows = list_scan(conn, scan_date)
    assert len(rows) == 4
    # actionable 排前 (R/R 降序), 然后 waiting, 最后 blocked
    assert [r.verdict for r in rows] == [
        "actionable", "actionable", "waiting", "blocked",
    ]
    assert rows[0].symbol == "DDD.SS"  # R/R 5.0 排前
    assert rows[1].symbol == "BBB.SS"  # R/R 3.0
    conn.close()


def test_upsert_rewrites_same_day(tmp_path) -> None:  # noqa: ANN001
    """二次写入当日: 删旧行, 整体重写。"""
    db = str(tmp_path / "opp.db")
    conn = connect(db)
    sd = "2026-08-13"
    upsert_scan_results(conn, sd, [_item("A.SS", "actionable"), _item("B.SS", "waiting")])
    conn.commit()
    assert has_scan(conn, sd) is True

    # 重写为更少标的
    upsert_scan_results(conn, sd, [_item("C.SS", "blocked")])
    conn.commit()
    rows = list_scan(conn, sd)
    assert len(rows) == 1
    assert rows[0].symbol == "C.SS"
    conn.close()


def test_has_scan_false_for_empty_date(tmp_path) -> None:  # noqa: ANN001
    db = str(tmp_path / "opp.db")
    conn = connect(db)
    assert has_scan(conn, "2099-01-01") is False
    conn.close()


def test_count_opportunities_excludes_blocked(tmp_path) -> None:  # noqa: ANN001
    """count_opportunities = actionable + waiting, blocked 不计。"""
    db = str(tmp_path / "opp.db")
    conn = connect(db)
    sd = "2026-08-13"
    upsert_scan_results(conn, sd, [
        _item("A.SS", "actionable"),
        _item("B.SS", "waiting"),
        _item("C.SS", "blocked"),
        _item("D.SS", "blocked"),
        _item("E.SS", "actionable"),
    ])
    conn.commit()
    assert count_opportunities(conn, sd) == 3  # 2 actionable + 1 waiting
    conn.close()


def test_blocking_reasons_serialized_as_json(tmp_path) -> None:  # noqa: ANN001
    """blocking_reasons 存 JSON 字符串, 读回为 list。"""
    db = str(tmp_path / "opp.db")
    conn = connect(db)
    sd = "2026-08-13"
    upsert_scan_results(conn, sd, [
        _item("A.SS", "blocked", blocking_reasons=["趋势不明", "多周期矛盾"]),
    ])
    conn.commit()
    rows = list_scan(conn, sd)
    assert rows[0].blocking_reasons == ["趋势不明", "多周期矛盾"]
    conn.close()


# ---- _group_today 分组 ----


def test_group_today_groups_by_verdict() -> None:
    """_group_today 按 verdict 分到 actionable/waiting/blocked。"""
    sd = "2026-08-13"
    # 构造 DailyScanRow 形态的 mock (duck typing)
    class _Row:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    rows = [
        _Row(symbol="A.SS", display_name="A", verdict="actionable",
             verdict_cn="条件已成立", best_scenario_cn="回踩",
             best_state="confirmed", reward_risk_ratio=3.0,
             reward_risk_computable=1, blocking_reasons="[]",
             missing_summary_cn="", has_active_plan=0, error=None,
             generated_at="2026-08-13T15:00:00"),
        _Row(symbol="B.SS", display_name="B", verdict="waiting",
             verdict_cn="等待", best_scenario_cn=None, best_state=None,
             reward_risk_ratio=None, reward_risk_computable=0,
             blocking_reasons="[]", missing_summary_cn="缺多头排列",
             has_active_plan=1, error=None, generated_at="2026-08-13T15:00:00"),
        _Row(symbol="C.SS", display_name="C", verdict="blocked",
             verdict_cn="阻断", best_scenario_cn=None, best_state=None,
             reward_risk_ratio=None, reward_risk_computable=0,
             blocking_reasons=json.dumps(["趋势不明"]),
             missing_summary_cn="", has_active_plan=0, error=None,
             generated_at="2026-08-13T15:00:00"),
    ]
    resp = _group_today(rows, sd)
    assert resp.scan_date == sd
    assert resp.scanned == 3
    assert len(resp.actionable) == 1
    assert len(resp.waiting) == 1
    assert len(resp.blocked) == 1
    assert resp.actionable[0].symbol == "A.SS"
    assert resp.waiting[0].missing_summary_cn == "缺多头排列"
    assert resp.blocked[0].blocking_reasons == ["趋势不明"]
    assert resp.generated_at == "2026-08-13T15:00:00"


def test_group_today_empty() -> None:
    resp = _group_today([], "2026-08-13")
    assert resp.scanned == 0
    assert resp.actionable == []
    assert resp.waiting == []
    assert resp.blocked == []


# ---- HTTP 端点 ----


def _bars(n: int = 80) -> "pd.DataFrame":
    import pandas as pd

    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
                     "close": close, "volume": 1_000_000})
    df = pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=n))
    return df[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info))


def _client(tmp_path) -> tuple[TestClient, str]:  # noqa: ANN001
    db = str(tmp_path / "opp_http.db")
    svc = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=svc)
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    return TestClient(app), db


def test_today_endpoint_empty(tmp_path) -> None:  # noqa: ANN001
    """空库 GET /today -> scanned=0, 三组空。"""
    client, _ = _client(tmp_path)
    r = client.get("/api/opportunities/today")
    assert r.status_code == 200
    data = r.json()
    assert data["scanned"] == 0
    assert data["actionable"] == []
    assert data["waiting"] == []
    assert data["blocked"] == []


def test_today_endpoint_reads_preinserted(tmp_path) -> None:  # noqa: ANN001
    """直接写库 -> GET /today 读回分组。"""
    client, db = _client(tmp_path)
    sd = today_date()
    conn = connect(db)
    upsert_scan_results(conn, sd, [
        _item("A.SS", "actionable", reward_risk_ratio=3.0, reward_risk_computable=True),
        _item("B.SS", "waiting", missing_summary_cn="缺多头排列"),
        _item("C.SS", "blocked", blocking_reasons=["趋势不明"]),
    ])
    conn.commit()
    conn.close()

    r = client.get("/api/opportunities/today")
    assert r.status_code == 200
    data = r.json()
    assert data["scan_date"] == sd
    assert data["scanned"] == 3
    assert len(data["actionable"]) == 1
    assert len(data["waiting"]) == 1
    assert len(data["blocked"]) == 1
    assert data["actionable"][0]["symbol"] == "A.SS"
    assert data["actionable"][0]["reward_risk_ratio"] == 3.0
    assert data["waiting"][0]["missing_summary_cn"] == "缺多头排列"
    assert data["blocked"][0]["blocking_reasons"] == ["趋势不明"]


def test_today_refresh_writes_and_returns(tmp_path) -> None:  # noqa: ANN001
    """POST /today/refresh 重扫落库, 返回分组结构 (单边上涨 -> 无候选 -> scanned=0)。"""
    client, db = _client(tmp_path)
    r = client.post("/api/opportunities/today/refresh")
    assert r.status_code == 200
    data = r.json()
    assert "scan_date" in data
    assert "scanned" in data
    assert "actionable" in data
    assert "waiting" in data
    assert "blocked" in data
    # _fake_analyze 产单边上涨 -> verdict=none -> only_with_candidates 过滤 -> 空结果
    assert data["scan_date"] == today_date()
    assert data["scanned"] == 0

    # 无候选时不写行 -> has_scan=False, count=0 (与"从未扫描"不可区分, 但都意味着无机会)
    conn = connect(db)
    assert count_opportunities(conn, today_date()) == 0
    conn.close()


def test_plans_summary_includes_today_opportunities(tmp_path) -> None:  # noqa: ANN001
    """GET /plans/summary 含 today_opportunities 字段。"""
    client, db = _client(tmp_path)
    # 先写机会数据
    sd = today_date()
    conn = connect(db)
    upsert_scan_results(conn, sd, [
        _item("A.SS", "actionable"),
        _item("B.SS", "waiting"),
        _item("C.SS", "blocked"),
    ])
    conn.commit()
    conn.close()

    r = client.get("/api/plans/summary")
    assert r.status_code == 200
    s = r.json()
    assert "today_opportunities" in s
    # actionable(1) + waiting(1) = 2, blocked 不计
    assert s["today_opportunities"] == 2


def test_plans_summary_zero_when_no_scan(tmp_path) -> None:  # noqa: ANN001
    """无扫描数据 -> today_opportunities=0。"""
    client, _ = _client(tmp_path)
    r = client.get("/api/plans/summary")
    assert r.status_code == 200
    assert r.json()["today_opportunities"] == 0
