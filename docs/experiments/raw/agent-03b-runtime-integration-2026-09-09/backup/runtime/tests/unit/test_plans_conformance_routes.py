"""草稿符合性核对路由：/conformance + /confirm 硬阻断 + PUT /draft。"""
from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.store import confirm_plan, create_plan, get_plan
from lei_signal.storage.sqlite_store import connect

SYMBOL = "000001.SS"
RULESET = "1.3.0"


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    index = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    price_data = PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame, report=report, info=info,
    )
    return analyze_bars(symbol, frame, price_data=price_data)


def _make_client(tmp_path, *, plan_kwargs: dict | None = None, confirm: bool = False):
    """建一个 draft（或 confirm 后的 armed）计划，返回 (client, plan_id)。"""
    db_path = str(tmp_path / "conf.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False

    kw = dict(
        symbol=SYMBOL, module="A", direction="long", ruleset_version=RULESET,
        reason="测试", valid_until="2026-12-31", entry_rule_id="first_ma_pullback",
        entry_lifecycle_id="lc1", entry_trigger_cn="首次回撤确认",
        entry_price_ref=100.0, invalidation_price=100.0, target_b_price=115.0,
        target_b_source="swing_high", reward_risk_at_plan=3.5, thesis_cn="测试假设",
        invalidation_criteria_cn="跌破 100", drawdown_playbook_cn="回踩 SMA60",
        take_profit_plan_cn="分批止盈", stop_plan_cn="结构止损",
    )
    kw.update(plan_kwargs or {})
    conn = connect(db_path)
    try:
        plan = create_plan(conn, **kw)
        if confirm:
            confirm_plan(conn, plan.plan_id)
        plan_id = plan.plan_id
    finally:
        conn.close()
    client = TestClient(app)
    client.plan_id = plan_id  # type: ignore[attr-defined]
    return client


def test_conformance_returns_structure(tmp_path) -> None:  # noqa: ANN001
    client = _make_client(tmp_path)
    resp = client.get(f"/api/plans/{client.plan_id}/conformance")  # type: ignore[attr-defined]
    assert resp.status_code == 200
    body = resp.json()
    assert "can_confirm" in body
    assert isinstance(body["hard_issues"], list)
    assert isinstance(body["soft_issues"], list)
    assert isinstance(body["system_detected"], dict)


def test_confirm_hard_blocks_on_missing_invalidation(tmp_path) -> None:  # noqa: ANN001
    # 缺失效价 -> 硬阻断，confirm 422
    client = _make_client(tmp_path, plan_kwargs={"invalidation_price": None})
    resp = client.post(f"/api/plans/{client.plan_id}/confirm")  # type: ignore[attr-defined]
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    codes = {i["code"] for i in detail.get("hard_issues", [])}
    assert "MISSING_INVALIDATION" in codes


def test_confirm_hard_blocks_on_module_mismatch(tmp_path) -> None:  # noqa: ANN001
    # module=A 但 rule 属 D -> 硬阻断
    client = _make_client(
        tmp_path, plan_kwargs={"module": "A", "entry_rule_id": "false_breakout_reclaim"}
    )
    resp = client.post(f"/api/plans/{client.plan_id}/confirm")  # type: ignore[attr-defined]
    assert resp.status_code == 422
    codes = {i["code"] for i in resp.json()["detail"].get("hard_issues", [])}
    assert "MODULE_RULE_MISMATCH" in codes


def test_draft_put_updates_field(tmp_path) -> None:  # noqa: ANN001
    client = _make_client(tmp_path)
    resp = client.put(
        f"/api/plans/{client.plan_id}/draft",  # type: ignore[attr-defined]
        json={"invalidation_price": 98.5, "entry_rule_id": None},
    )
    assert resp.status_code == 200
    conn = connect(str(tmp_path / "conf.db"))
    try:
        plan = get_plan(conn, client.plan_id)  # type: ignore[attr-defined]
        assert plan.invalidation_price == 98.5
        assert plan.entry_rule_id is None  # null 清空
        assert plan.state == "draft"  # 仍 draft
    finally:
        conn.close()


def test_draft_put_409_when_not_draft(tmp_path) -> None:  # noqa: ANN001
    client = _make_client(tmp_path, confirm=True)  # armed
    resp = client.put(
        f"/api/plans/{client.plan_id}/draft",  # type: ignore[attr-defined]
        json={"invalidation_price": 99.0},
    )
    assert resp.status_code == 409


def test_conformance_404_unknown_plan(tmp_path) -> None:  # noqa: ANN001
    client = _make_client(tmp_path)
    resp = client.get("/api/plans/no-such-plan/conformance")
    assert resp.status_code == 404


def _holding_watch_body(**extra) -> dict:
    body = {
        "symbol": SYMBOL, "direction": "long", "ruleset_version": RULESET,
        "valid_until": "2026-12-31", "take_profit_plan_cn": "到 150 分批",
        "stop_plan_cn": "跌破 130 出", "take_profit_price": 150.0,
        "stop_price": 130.0, "watch_signal_rule_ids": [], "module": "", "reason": "持仓",
    }
    body.update(extra)
    return body


def test_holding_watch_creates_draft_then_confirms(tmp_path) -> None:  # noqa: ANN001
    """holding-watch 不再一步 confirm：建 draft -> 核对 -> confirm -> entered。

    holding_watch 不查可交易性，TP/SL 方向合理即可 can_confirm（快乐路径）。
    """
    db_path = str(tmp_path / "conf.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    client = TestClient(app)

    resp = client.post("/api/plans/holding-watch", json=_holding_watch_body())
    assert resp.status_code == 201
    plan_id = resp.json()["plan_id"]
    assert resp.json()["state"] == "draft"  # 不再一步 entered

    conf = client.get(f"/api/plans/{plan_id}/conformance").json()
    assert conf["can_confirm"] is True

    confirmed = client.post(f"/api/plans/{plan_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["state"] == "entered"


def test_holding_watch_confirm_blocks_on_insane_tp(tmp_path) -> None:  # noqa: ANN001
    db_path = str(tmp_path / "conf.db")
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    client = TestClient(app)

    # long 止盈价 100 <= 当前价 ~139.5 -> 方向错，硬阻断
    resp = client.post(
        "/api/plans/holding-watch",
        json=_holding_watch_body(take_profit_price=100.0),
    )
    plan_id = resp.json()["plan_id"]
    confirmed = client.post(f"/api/plans/{plan_id}/confirm")
    assert confirmed.status_code == 422
    codes = {i["code"] for i in confirmed.json()["detail"].get("hard_issues", [])}
    assert "TP_SL_DIRECTION_INSANE" in codes
