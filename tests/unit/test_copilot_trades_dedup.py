"""基金成交确认的重复记账修复（2026-09-17 合同 G2）。

覆盖：同ID重试返原笔、同ID异载荷冲突、异ID合法两笔、旧客户端无ID不
受保护（明确行为，不假装受保护）、并发竞争走唯一索引兜底、首次已落库
但定价/响应失败后的重试、迁移对既有成交零改动且可重复执行。
全部使用临时 SQLite + 合成数据，fetch_nav 注入假数据，不打网络、
不触碰真实数据库。
"""
from __future__ import annotations

import sqlite3
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.copilot import trades
from lei_signal.copilot import trades as trades_mod
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import apply_migrations, connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _rows(conn):
    return conn.execute(
        "SELECT trade_id, request_id, request_payload FROM fund_trades "
        "ORDER BY created_at"
    ).fetchall()


def _trade_kwargs(**over):
    base = dict(fund_code="012414", fund_name="测试基金", side="buy",
                amount=10000.0, trade_date="2026-09-10")
    base.update(over)
    return base


# ---------------- 同ID重试：返回原笔，只记一笔 ----------------

def test_same_request_id_same_payload_returns_original(conn):
    first = trades.create_trade(conn, request_id="req-aaa", **_trade_kwargs())
    conn.commit()
    second = trades.create_trade(conn, request_id="req-aaa", **_trade_kwargs())
    conn.commit()
    assert second.trade_id == first.trade_id
    assert len(_rows(conn)) == 1


def test_same_request_id_after_pricing_failure_retry_no_new_trade(conn):
    """首次落库成功但定价失败（响应丢失场景）：同ID重试返回原成交，
    定价补跑成功，全程只有一笔。"""
    def broken_fetch(code, page_size=40):
        raise OSError("网络不可用")

    trades.create_trade(conn, request_id="req-bbb", **_trade_kwargs())
    trades.price_pending_trades(conn, fetch_nav=broken_fetch)  # 定价失败 → pending
    conn.commit()
    assert trades.list_trades(conn)[0].price_status == "pending"

    def good_fetch(code, page_size=40):
        return [NavPoint(date="2026-09-10", unit_nav=1.23)]

    retry = trades.create_trade(conn, request_id="req-bbb", **_trade_kwargs())
    trades.price_pending_trades(conn, fetch_nav=good_fetch)
    conn.commit()
    rows = trades.list_trades(conn)
    assert len(rows) == 1
    assert rows[0].trade_id == retry.trade_id
    assert rows[0].price_status == "priced"
    assert rows[0].priced_nav == pytest.approx(1.23)


# ---------------- 同ID异载荷：显式冲突，零新增 ----------------

def test_same_request_id_different_amount_conflicts(conn):
    trades.create_trade(conn, request_id="req-ccc", **_trade_kwargs())
    conn.commit()
    with pytest.raises(trades.TradeRequestConflict):
        trades.create_trade(conn, request_id="req-ccc",
                            **_trade_kwargs(amount=20000.0))
    assert len(_rows(conn)) == 1


def test_same_request_id_any_persisted_field_change_conflicts(conn):
    trades.create_trade(conn, request_id="req-ddd", **_trade_kwargs())
    conn.commit()
    for changed in (
        _trade_kwargs(side="sell"),
        _trade_kwargs(fund_code="000001"),
        _trade_kwargs(trade_date="2026-09-11"),
        _trade_kwargs(note="改备注"),
    ):
        with pytest.raises(trades.TradeRequestConflict):
            trades.create_trade(conn, request_id="req-ddd", **changed)
    assert len(_rows(conn)) == 1


def test_conflict_against_legacy_row_without_payload(conn):
    """历史行 request_id/payload 为 NULL：若客户端复用了与历史行相同的
    ID（异常客户端），载荷无法核对 → 一律冲突，不静默复用。"""
    conn.execute(
        "INSERT INTO fund_trades (trade_id, fund_code, fund_name, side, amount,"
        " trade_date, price_status, note, created_at, updated_at, request_id)"
        " VALUES ('ft_old', '012414', '旧', 'buy', 1.0, '2026-09-01',"
        " 'pending', '', '2026-09-01T00:00:00+00:00',"
        " '2026-09-01T00:00:00+00:00', 'req-legacy')"
    )
    conn.commit()
    with pytest.raises(trades.TradeRequestConflict):
        trades.create_trade(conn, request_id="req-legacy",
                            **_trade_kwargs(amount=1.0))


# ---------------- 规范化：写入口径一致才算同一载荷 ----------------

def test_canonicalization_strips_and_floats(conn):
    first = trades.create_trade(conn, request_id="req-eee", **_trade_kwargs())
    conn.commit()
    retry = trades.create_trade(
        conn, request_id="req-eee",
        **_trade_kwargs(fund_name=" 测试基金 ", amount=10000),
    )
    conn.commit()
    assert retry.trade_id == first.trade_id
    assert len(_rows(conn)) == 1


def test_canonical_request_payload_shape():
    a = trades.canonical_request_payload(
        fund_code="012414", fund_name=" X ", side="buy",
        amount=100.0, trade_date="2026-09-10", note="")
    b = trades.canonical_request_payload(
        fund_code="012414", fund_name="X", side="buy",
        amount=100, trade_date="2026-09-10", note="")
    assert a == b
    assert '"fund_code"' in a and '"amount": 100.0' in a


# ---------------- 异ID同载荷：合法两笔 ----------------

def test_different_request_ids_same_fields_two_trades(conn):
    trades.create_trade(conn, request_id="req-1", **_trade_kwargs())
    trades.create_trade(conn, request_id="req-2", **_trade_kwargs())
    conn.commit()
    rows = _rows(conn)
    assert len(rows) == 2
    assert rows[0]["trade_id"] != rows[1]["trade_id"]


def test_missing_request_id_legacy_client_unprotected(conn):
    """无ID（旧客户端）明确不受重试保护：两次调用两笔——这是兼容行为，
    不是缺陷，也不得宣称旧调用受保护。"""
    trades.create_trade(conn, **_trade_kwargs())
    trades.create_trade(conn, **_trade_kwargs())
    conn.commit()
    assert len(_rows(conn)) == 2
    assert all(r["request_id"] is None for r in _rows(conn))


# ---------------- 并发：唯一索引兜底，两连接只落一笔 ----------------

def test_concurrent_same_request_id_single_row(tmp_path):
    db = str(tmp_path / "conc.db")
    results: dict[str, str] = {}
    barrier = threading.Barrier(2)
    # 主线程先建库一次（schema/WAL/迁移就位后关闭）：全新库首次 connect 的
    # WAL 切换有短暂独占段且不遵守 busy_timeout（connect() 已知特性）。
    # 线程内再各自 connect，只并发写入——这正是要验证的竞争点。
    seed = connect(db)
    seed.close()

    def worker(tag: str):
        c = connect(db)
        try:
            barrier.wait(timeout=10)
            dto = trades.create_trade(
                c, request_id="req-conc",
                fund_code="012414", fund_name="测试基金", side="buy",
                amount=10000.0, trade_date="2026-09-10",
            )
            c.commit()
            results[tag] = dto.trade_id
        finally:
            c.close()

    t1, t2 = threading.Thread(target=worker, args=("a",)), \
        threading.Thread(target=worker, args=("b",))
    t1.start(); t2.start(); t1.join(30); t2.join(30)
    assert results["a"] == results["b"], results
    check = connect(db)
    try:
        assert len(_rows(check)) == 1
    finally:
        check.close()


# ---------------- 迁移：旧行零改动、可重复执行 ----------------

def _make_legacy_db(path) -> None:
    """按 031 之前的旧表结构建库并写入一笔历史成交。"""
    raw = sqlite3.connect(path)
    raw.execute(
        "CREATE TABLE fund_trades ("
        " trade_id TEXT PRIMARY KEY, fund_code TEXT NOT NULL,"
        " fund_name TEXT NOT NULL, side TEXT NOT NULL CHECK(side IN ('buy','sell')),"
        " amount REAL NOT NULL, trade_date TEXT NOT NULL, priced_nav REAL,"
        " price_status TEXT NOT NULL DEFAULT 'pending', plan_id TEXT,"
        " source TEXT NOT NULL DEFAULT 'web', note TEXT NOT NULL DEFAULT '',"
        " created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    raw.execute(
        "INSERT INTO fund_trades VALUES ('ft_hist', '012414', '历史基金', 'buy',"
        " 5000.0, '2026-08-01', 1.5, 'priced', NULL, 'web', '',"
        " '2026-08-01T00:00:00+00:00', '2026-08-01T00:00:00+00:00')"
    )
    raw.commit()
    raw.close()


def test_migration_preserves_legacy_rows_and_is_repeatable(tmp_path):
    db = str(tmp_path / "legacy.db")
    _make_legacy_db(db)
    c = connect(db)  # 首次连接即触发 031 迁移
    try:
        row = c.execute("SELECT * FROM fund_trades WHERE trade_id='ft_hist'").fetchone()
        assert row["request_id"] is None and row["request_payload"] is None
        assert row["amount"] == 5000.0 and row["price_status"] == "priced"
        assert c.execute(
            "SELECT COUNT(*) FROM fund_trades").fetchone()[0] == 1
        # 迁移重复执行安全：显式重跑 + 再开一次连接，均不报错不改数据
        apply_migrations(c)
    finally:
        c.close()
    c2 = connect(db)
    try:
        assert c2.execute(
            "SELECT COUNT(*) FROM fund_trades").fetchone()[0] == 1
        assert "idx_fund_trades_request_id" in {
            r["name"] for r in c2.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")
        }
        # 迁移后新调用仍可用：历史行不影响新确认身份
        trades.create_trade(c2, request_id="req-after-mig", **_trade_kwargs())
        c2.commit()
        assert len(_rows(c2)) == 2
    finally:
        c2.close()


# ---------------- 路由层：200 幂等 / 409 冲突 / 无ID不受保护 ----------------

@pytest.fixture()
def app(tmp_path, monkeypatch):
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = str(tmp_path / "route.db")
    a.state.watchlist_db_path = a.state.plans_db_path
    a.include_router(copilot_routes.router)

    def fake_fetch(code, page_size=40):
        return [NavPoint(date="2026-09-10", unit_nav=1.10)]

    monkeypatch.setattr(trades_mod, "fetch_nav_history", fake_fetch)
    return a


def _post(client, request_id, **over):
    payload = dict(fund_code="012414", fund_name="测试基金", side="buy",
                   amount=10000.0, trade_date="2026-09-10")
    payload.update(over)
    if request_id is not None:
        payload["request_id"] = request_id
    return client.post("/api/copilot/trades", json=payload)


def test_route_same_request_id_idempotent(app):
    client = TestClient(app)
    r1 = _post(client, "req-route-1")
    r2 = _post(client, "req-route-1")
    assert r1.status_code == r2.status_code == 200
    assert r2.json()["trade_id"] == r1.json()["trade_id"]
    assert len(client.get("/api/copilot/trades").json()["trades"]) == 1


def test_route_same_request_id_different_payload_409_zero_new(app):
    client = TestClient(app)
    assert _post(client, "req-route-2").status_code == 200
    r = _post(client, "req-route-2", amount=999.0)
    assert r.status_code == 409
    assert "不能复用同一确认身份" in r.json()["detail"]
    assert len(client.get("/api/copilot/trades").json()["trades"]) == 1


def test_route_blank_request_id_treated_as_missing(app):
    client = TestClient(app)
    assert _post(client, "   ").status_code == 200
    assert _post(client, None).status_code == 200
    assert len(client.get("/api/copilot/trades").json()["trades"]) == 2


def test_route_different_ids_same_fields_two_trades(app):
    client = TestClient(app)
    assert _post(client, "req-x").status_code == 200
    assert _post(client, "req-y").status_code == 200
    body = client.get("/api/copilot/trades").json()
    assert len(body["trades"]) == 2


def test_route_request_id_over_length_rejected(app):
    client = TestClient(app)
    r = _post(client, "r" * 129)
    assert r.status_code == 422
