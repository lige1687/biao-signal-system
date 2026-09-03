"""newsfeed API 路由单元测试（TestClient + 临时库，管线 mock）。"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.watchlist import upsert_watchlist
from lei_signal.newsfeed.service import NewsfeedService
from lei_signal.storage.sqlite_store import connect


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lei_signal.newsfeed.service.run_pipeline",
        lambda db_path, **k: {"run_id": 1, "status": "ok", "inserted": 0,
                              "per_source": {}, "scored": 0, "digest": False,
                              "errors": []},
    )
    app = create_app()
    app.state.newsfeed_service = NewsfeedService(db_path=str(tmp_path / "api.db"))
    # watchlist 与 newsfeed 同库：路由从这里读自选（隔离测试库）
    app.state.watchlist_db_path = str(tmp_path / "api.db")
    # 预置两条数据
    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(tmp_path / "api.db")
    store.insert_items([
        {"source": "eastmoney", "source_name": "东财快讯", "url": None,
         "category": "macro", "title": "央行降准", "summary": "降准0.5pct",
         "content": None, "published_at": "2026-08-27T10:00:00+08:00",
         "dedupe_key": "a1"},
        {"source": "bilibili", "source_name": "趋势天哥", "url": "https://b23.tv/x",
         "category": "blogger", "title": "英伟达指引大超预期", "summary": "视频简介",
         "content": None, "published_at": "2026-08-27T20:00:00+08:00",
         "dedupe_key": "a2"},
    ])
    store.apply_scores([
        {"id": 1, "category": "macro", "importance": 8, "direction": "bullish",
         "symbols": [], "note": "宽松信号"},
    ])
    store.save_digest("2026-08-27", {"sections": [{"category": "macro",
                                                   "headline": "h", "bullets": ["b"]}],
                                   "top_events": []})
    store.close()
    return TestClient(app)


def test_items_query_and_search(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.get("/api/news/items")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    # 已评分（importance=8）在前
    assert body["items"][0]["title"] == "央行降准"
    assert body["items"][0]["symbols"] == []
    # 中文 LIKE 搜索
    resp = client.get("/api/news/items", params={"q": "英伟达"})
    body = resp.json()
    assert body["total"] == 1 and body["items"][0]["source"] == "bilibili"
    # 类别过滤
    resp = client.get("/api/news/items", params={"category": "blogger"})
    assert resp.json()["total"] == 1
    # symbol 过滤（标题命中，未评分条目也算）
    resp = client.get("/api/news/items", params={"symbol": "英伟达"})
    assert resp.json()["total"] == 1
    # direction 过滤
    resp = client.get("/api/news/items", params={"direction": "bullish"})
    body = resp.json()
    assert body["total"] == 1 and body["items"][0]["title"] == "央行降准"


def test_watchlist_brief(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    db = str(tmp_path / "api.db")
    with closing(connect(db)) as conn:
        upsert_watchlist(conn, symbol="NVDA", display_name=None,
                         market="us", note=None, group_id=None)
        upsert_watchlist(conn, symbol="512890.SS", display_name="红利ETF",
                         market="cn_sh", note=None, group_id=None)

    from lei_signal.newsfeed.store import NewsStore

    fresh = datetime.now().astimezone().isoformat(timespec="seconds")
    store = NewsStore(db)
    store.insert_items([
        {"source": "eastmoney", "source_name": "东财快讯", "url": None,
         "category": "industry", "title": "英伟达新品发布", "summary": None,
         "content": None, "published_at": fresh, "dedupe_key": "w1"},
        {"source": "sina", "source_name": "新浪7x24", "url": None,
         "category": "industry", "title": "红利ETF 规模缩水", "summary": None,
         "content": None, "published_at": fresh, "dedupe_key": "w2"},
    ])
    ids = {r["title"]: r["id"] for r in store.fetch_unscored()}
    store.apply_scores([
        {"id": ids["英伟达新品发布"], "category": "industry", "importance": 8,
         "direction": "bullish", "symbols": ["NVDA"], "note": "新品周期"},
        {"id": ids["红利ETF 规模缩水"], "category": "industry", "importance": 6,
         "direction": "bearish", "symbols": [], "note": "资金流出"},
    ])
    store.close()

    resp = client.get("/api/news/watchlist-brief", params={"days": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == 3
    # 只有命中消息的自选标的返回
    syms = {i["symbol"]: i for i in body["items"]}
    assert set(syms) == {"NVDA", "512890.SS"}
    assert syms["NVDA"]["bullish"] == 1 and syms["NVDA"]["count"] == 1
    assert syms["NVDA"]["top"]["title"] == "英伟达新品发布"
    assert syms["512890.SS"]["bearish"] == 1
    # 全局多空温度 + 重点事件（importance>=6）
    assert body["mood"]["bullish"] >= 1 and body["mood"]["bearish"] >= 1
    assert body["mood"]["top_bullish"][0]["title"] == "英伟达新品发布"
    assert body["mood"]["top_bearish"][0]["title"] == "红利ETF 规模缩水"


def test_digests_and_status_and_run(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.get("/api/news/digests")
    assert resp.status_code == 200
    body = resp.json()
    assert body["digests"][0]["payload"]["sections"][0]["category"] == "macro"

    resp = client.get("/api/news/status")
    assert resp.status_code == 200
    assert resp.json()["counts"]["total"] == 2

    resp = client.post("/api/news/run")
    assert resp.status_code == 200
    assert resp.json()["run"] in ("started", "already_running")
