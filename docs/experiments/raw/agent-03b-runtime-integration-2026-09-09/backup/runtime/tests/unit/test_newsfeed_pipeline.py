"""管线编排单元测试：mock 各源，验证粗筛/幂等/降级/LLM 步骤。"""
from __future__ import annotations

from datetime import datetime

from lei_signal.newsfeed import pipeline
from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.pipeline import run_pipeline
from lei_signal.newsfeed.sources import NewsSourceError

_CFG = {
    "bili_ups": [{"mid": 1, "name": "测试UP"}],
    "rss_feeds": [],
    "gnews_queries": ["q1"],
    "symbols": ["NVDA"],
    "flash_keywords": {
        "macro": ["央行"],
        "risk": ["危机"],
        "policy": ["国务院"],
        "industry": ["财报"],
    },
    "lookback_days": 30,
}


def _em_items() -> list[NewsItem]:
    # 简报只收"当天"条目，日期必须动态生成，否则测试第二天起必挂
    t = datetime.now().astimezone().isoformat(timespec="seconds")
    return [
        NewsItem(source="eastmoney", title="央行降准", summary="央行宣布降准",
                 published_at=t, dedupe_key="em1"),
        NewsItem(source="eastmoney", title="公司更换审计机构", summary="无关键词噪音",
                 published_at=t, dedupe_key="em2"),
    ]


def _patch_sources(monkeypatch, *, em=None, sina=None, gnews=None, bili=None):
    em_items = _em_items() if em is None else em
    monkeypatch.setattr(pipeline, "collect_eastmoney",
                        lambda since: (list(em_items), "1000"))
    monkeypatch.setattr(pipeline, "collect_sina",
                        lambda since: (list(sina or []), None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: (list(gnews or []), None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda client, mid, name, since, lookback_iso=None, **kw: (
                            list(bili or []), None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())


def test_pipeline_filters_flash_noise_and_scores(monkeypatch, tmp_path):
    _patch_sources(monkeypatch)
    scored_calls = []

    def fake_score(rows, config=None):
        scored_calls.append(rows)
        return [
            {"id": r["id"], "category": "macro", "importance": 7,
             "direction": "bullish", "symbols": [], "note": "n"}
            for r in rows
        ]

    monkeypatch.setattr(pipeline, "score_items", fake_score)
    monkeypatch.setattr(pipeline, "generate_digest", lambda rows, config=None: None)

    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["status"] == "ok"
    # 噪音被粗筛丢弃
    assert result["per_source"]["eastmoney"] == 1
    assert result["scored"] == 1
    assert scored_calls and scored_calls[0][0]["title"] == "央行降准"

    # 二跑幂等：水位推进 + dedupe，不再入库
    result2 = run_pipeline(db, config=_CFG, no_llm=True)
    assert result2["inserted"] == 0


def test_pipeline_partial_when_one_source_fails(monkeypatch, tmp_path):
    def boom(since):
        raise NewsSourceError("风控")

    monkeypatch.setattr(pipeline, "collect_eastmoney", boom)
    monkeypatch.setattr(pipeline, "collect_sina", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: ([], None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda c, mid, name, since, lookback_iso=None, **kw: ([], None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())

    result = run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=True)
    assert result["status"] == "partial"
    assert result["errors"] == [{"source": "eastmoney", "error": "风控"}]


def test_pipeline_no_llm_skips_scoring(monkeypatch, tmp_path):
    _patch_sources(monkeypatch)
    called = {"score": False, "digest": False}
    monkeypatch.setattr(pipeline, "score_items",
                        lambda *a, **k: called.__setitem__("score", True) or [])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda *a, **k: called.__setitem__("digest", True) or None)
    run_pipeline(tmp_path / "p.db", config=_CFG, no_llm=True)
    assert not called["score"] and not called["digest"]


def test_pipeline_saves_digest(monkeypatch, tmp_path):
    _patch_sources(monkeypatch, bili=[NewsItem(
        source="bilibili", source_name="趋势天哥", url="https://b23.tv/z",
        category="blogger", title="天哥视频",
        summary=None, content=None,
        published_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        dedupe_key="bt1")])
    monkeypatch.setattr(pipeline, "score_items",
                        lambda rows, config=None: [
                            {"id": r["id"], "category": "blogger", "importance": 6,
                             "direction": "bearish", "symbols": [], "note": "偏空观点"}
                            for r in rows])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda rows, config=None: {"sections": [], "top_events": []})
    monkeypatch.setattr(pipeline, "generate_blogger_summaries",
                        lambda rows, config=None: [
                            {"name": "趋势天哥", "stance": "bearish", "summary": "偏空观望"}])
    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["digest"] is True
    import json

    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(db)
    d = store.digests()
    assert len(d) == 1
    payload = json.loads(d[0]["payload_json"])
    assert payload["bloggers"] == [{"name": "趋势天哥", "stance": "bearish", "summary": "偏空观望"}]
    store.close()


def test_pipeline_blogger_summary_failure_does_not_block_digest(monkeypatch, tmp_path):
    """博主小结 LLM 失败：简报照常保存（不带 bloggers 字段）。"""
    _patch_sources(monkeypatch)
    monkeypatch.setattr(pipeline, "score_items",
                        lambda rows, config=None: [
                            {"id": r["id"], "category": "macro", "importance": 7,
                             "direction": "neutral", "symbols": [], "note": "n"}
                            for r in rows])
    monkeypatch.setattr(pipeline, "generate_digest",
                        lambda rows, config=None: {"sections": [], "top_events": []})
    monkeypatch.setattr(pipeline, "generate_blogger_summaries",
                        lambda rows, config=None: None)
    db = tmp_path / "p.db"
    result = run_pipeline(db, config=_CFG, no_llm=False)
    assert result["digest"] is True
    import json

    from lei_signal.newsfeed.store import NewsStore

    store = NewsStore(db)
    payload = json.loads(store.digests()[0]["payload_json"])
    assert "bloggers" not in payload
    store.close()


def test_blogger_category_restricted_to_blogger_sources(monkeypatch, tmp_path):
    """gnews 的英文股评被 LLM 判成 blogger 时，回落预分类 industry。"""
    monkeypatch.setattr(
        pipeline, "collect_eastmoney", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_sina", lambda since: ([], None))
    monkeypatch.setattr(pipeline, "collect_rss",
                        lambda q, *, is_gnews, since_iso: ([], None))
    monkeypatch.setattr(pipeline, "fetch_new_up_items",
                        lambda c, mid, name, since, lookback_iso=None, **kw: ([], None))
    monkeypatch.setattr(pipeline, "BilibiliClient", lambda *a, **k: object())
    monkeypatch.setattr(pipeline, "generate_digest", lambda rows, config=None: None)

    def fake_score(rows, config=None):
        out = []
        for r in rows:
            # 模拟 LLM：所有条目都判成 blogger
            out.append({"id": r["id"], "category": "blogger", "importance": 5,
                        "direction": "neutral", "symbols": [], "note": "n"})
        return out

    monkeypatch.setattr(pipeline, "score_items", fake_score)

    from lei_signal.newsfeed.store import NewsStore

    db = tmp_path / "cat.db"
    store = NewsStore(db)
    store.insert_items([
        {"source": "gnews", "source_name": "Reuters", "url": "http://x/1",
         "category": "industry", "title": "NVIDIA remains a buy", "summary": "opinion",
         "content": None, "published_at": "2026-08-27T10:00:00+08:00",
         "dedupe_key": "g1"},
        {"source": "bilibili", "source_name": "UP", "url": "http://x/2",
         "category": "blogger", "title": "例行更新", "summary": "s",
         "content": None, "published_at": "2026-08-27T11:00:00+08:00",
         "dedupe_key": "g2"},
    ])
    store.close()

    run_pipeline(db, config=_CFG, no_llm=False)
    store = NewsStore(db)
    cats = {r["title"]: r["category"] for r in store.query_items(limit=10)[0]}
    store.close()
    assert cats["NVIDIA remains a buy"] == "industry"  # 回落
    assert cats["例行更新"] == "blogger"  # 博主源保留
