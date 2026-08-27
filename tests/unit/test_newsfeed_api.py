"""newsfeed API 路由单元测试（TestClient + 临时库，管线 mock）。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.newsfeed.service import NewsfeedService


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lei_signal.newsfeed.service.run_pipeline",
        lambda db_path, **k: {"run_id": 1, "status": "ok", "inserted": 0,
                              "per_source": {}, "scored": 0, "digest": False,
                              "errors": []},
    )
    app = create_app()
    app.state.newsfeed_service = NewsfeedService(db_path=str(tmp_path / "api.db"))
    # 预置两条数据
    svc = app.state.newsfeed_service
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
